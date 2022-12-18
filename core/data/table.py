import re

from ctypes import c_int8
from ctypes import c_int16
from ctypes import c_int32
from ctypes import c_int64
from ctypes import c_uint8
from ctypes import c_uint16
from ctypes import c_uint32
from ctypes import c_uint64
from ctypes import c_float
from ctypes import c_double

from enum import Enum

from datetime import date, datetime, timedelta

from hashlib import md5, sha1, sha256
from zlib import adler32, crc32

from collections import defaultdict, OrderedDict

DATETIME_STRPTIME_DEFAULT = datetime.strptime("00:00:00", "%H:%M:%S")

class FieldEnum:
    _ns_get = {}

    @classmethod
    def add(cls, ns, get):
        cls._ns_get[ns] = get

    @classmethod
    def get(cls, ns, key):
        get = cls._ns_get[ns]
        return get(key)

class FieldType:
    class Error(Exception):
        def __init__(self, name, col):
            super(FieldType.Error, self).__init__(name)
            self.col = col
    """
    data_type:main_attr:sub_attr
    """
    ro_field_type_expr = re.compile(r"(\w+)(:([^:]+)(:(.+))?)?")

    expr_to_type_pair = {
        'str:pk:hash64':    (int, c_uint64),
        'str:pk:hash32':    (int, c_uint32),
        'str:pk:adler32':   (int, c_uint32),
        'str:pk:crc32':     (int, c_uint32),
        'str:pk:md5':       (bytes, c_uint8 * 16),
        'str:pk:sha1':      (bytes, c_uint8 * 20),
        'str:pk:sha256':    (bytes, c_uint8 * 32),
    }

    data_type_name_to_type_pair = {
        'real':     (float, c_float),
        'real32':   (float, c_float),
        'real64':   (float, c_double),
        'enum':     (Enum, c_int32),
        'int':      (int, c_int32),
        'int8':     (int, c_int8),
        'int16':    (int, c_int16),
        'int32':    (int, c_int32),
        'int64':    (int, c_int64),
        'uint':     (int, c_uint32),
        'uint8':    (int, c_uint8),
        'uint16':   (int, c_uint16),
        'uint32':   (int, c_uint32),
        'uint64':   (int, c_uint64),
        'str':      (str, bytes),
        'span':     (timedelta, bytes),
        'time':     (timedelta, bytes),
        'date':     (date, bytes),
        'datetime': (datetime, bytes),
    }

    # https://www.sami-lehtinen.net/blog/python-hash-function-performance-comparison
    #  13: python hash
    #  49: zlib.alder32
    #  91: zlib.crc32
    # 180: hashlib.md5
    # 179: hashlib.sha1
    # 403: hashlib.sha256
    expr_to_parse_text = {
        'str:pk:hash64': lambda t, m, s: hash(t),
        'str:pk:hash32': lambda t, m, s: hash(t),
        'str:pk:adler32': lambda t, m, s: adler32(t.encode('utf8')),
        'str:pk:crc32': lambda t, m, s: crc32(t.encode('utf8')),
        'str:pk:md5': lambda t, m, s: md5(t.encode('utf8')).digest(),
        'str:pk:sha1': lambda t, m, s: sha1(t.encode('utf8')).digest(),
        'str:pk:sha256': lambda t, m, s: sha256(t.encode('utf8')).digest(),
        'str:ascii:ignore': lambda t, m, s: t.encode('ascii', 'ignore'),
        'str:ascii:replace': lambda t, m, s: t.encode('ascii', 'replace'),
    }

    py_type2_to_parse_text = {
        (int, 'bin'): lambda t, m, s: int(t, 2),
        (int, 'oct'): lambda t, m, s: int(t, 8),
        (int, 'hex'): lambda t, m, s: int(t, 16),
        (int, 'pk'): lambda t, m, s: int(t),
        (int, 'fk'): lambda t, m, s: int(t),
        (str, 'pk'): lambda t, m, s: adler32(t.encode('utf8')),
        (str, 'fk'): lambda t, m, s: adler32(t.encode('utf8')),
    }

    py_type_to_parse_text = {
        str: lambda t, m, s: t.encode(m) if m else t.encode('utf8'),
        int: lambda t, m, s: int(t, int(m)) if m else int(t),
        float: lambda t, m, s: float(t),
        date: lambda t, m, s: datetime.strptime(t, "%Y-%m-%d").date(),
        datetime: lambda t, m, s: datetime.strptime(t, "%Y-%m-%d %H:%M:%S"),
        timedelta: lambda t, m, s: datetime.strptime(t, "%H:%M:%S") - DATETIME_STRPTIME_DEFAULT,
        Enum: lambda t, m, s: FieldEnum.get(m, t),
    }

    type_pair_to_dump = {
        (date, bytes): lambda v: str(v).encode('utf8'),
        (datetime, bytes): lambda v: str(v).encode('utf8'),
        (timedelta, bytes): lambda v: str(v).encode('utf8'),
    }

    @classmethod
    def add(cls, data_type_name, py_type, c_type, parse_text):
        cls.expr_to_parse_text[data_type_name] = parse_text
        cls.data_type_name_to_type_pair[data_type_name] = (py_type, c_type)

    @classmethod
    def parse_expr(cls, expr: str):
        mo = cls.ro_field_type_expr.match(expr)
        if mo:
            data_type_name = mo.group(1)
            main_attr = mo.group(3)
            sub_attr = mo.group(5)
            return cls(expr, data_type_name, main_attr, sub_attr)

    @classmethod
    def gen_field_types(cls, exprs: list):
        for idx, expr in enumerate(exprs):
            try:
                yield cls.parse_expr(expr)
            except ValueError as exc:
                raise cls.Error(f"{str(exc)} COL: {idx}", col=idx)

    def __init__(self, expr, data_type_name, main_attr, sub_attr):
        type_pair = self.expr_to_type_pair.get(expr, None)
        if not type_pair:
            type_pair = self.data_type_name_to_type_pair.get(data_type_name, None)
            if not type_pair:
                raise ValueError(f"UNKNOWN_DATA_TYPE: {data_type_name} EXPR: {expr}")

        parse_text = self.expr_to_parse_text.get(expr)
        if not parse_text:
            py_type = type_pair[0]
            parse_text = self.py_type2_to_parse_text.get((py_type, main_attr), None)
            if not parse_text:
                parse_text = self.py_type_to_parse_text[py_type]

        c_type = type_pair[1]
        dump_value = self.type_pair_to_dump.get(type_pair, c_type)

        self._type_pair = type_pair
        self._sub_attr = sub_attr
        self._main_attr = main_attr
        self._data_type_name = data_type_name
        self._parse_text = parse_text
        self._dump_value = dump_value
        self._expr = expr

    def __repr__(self):
        return self._expr

    def parse_text(self, text):
        return self._parse_text(text, self._main_attr, self._sub_attr)

    def dump(self, value):
        return bytes(self._dump_value(value))

class Table:
    RO_L10N_FIELD_NAME = re.compile('\$(\w+)\[(\w+)\]')

    @classmethod
    def parse(cls, rows):
        row_idx = 0

        field_names = rows[0]
        field_types = list(FieldType.gen_field_types(rows[1]))

        def gen_records():
            def gen_values(texts):
                for col_idx, (field_type, text) in enumerate(zip(field_types, texts)):
                    yield field_type.parse_text(text)

            for row_idx in range(2, len(rows)):
                yield list(gen_values(rows[row_idx]))

        records = list(gen_records())
        return cls(field_names, field_types, rows[row_idx:])

    def __init__(self, field_names, field_types, records):
        self._field_names = field_names
        self._field_types = field_types
        self._records = records

    def __repr__(self):
        head_line = ', '.join(self._field_names)
        type_line = ', '.join(repr(field_type) for field_type in self._field_types)
        body_lines = [
            ', '.join(repr(field_value) for field_value in record)
                for record in self._records]
        return '\n'.join([head_line, type_line] + body_lines)

    def gen_l10n_bin_rows(self):
        mos = [self.RO_L10N_FIELD_NAME.match(field_name) for field_name in self._field_names]

        key_head_text = 'key'.encode('utf8')
        key_head_hash = adler32(key_head_text)
        yield b'head', b'hash', b'text'
        yield 0, 0, b'adler32'
        yield 0, key_head_hash, key_head_text
        for val_idx, mo in enumerate(mos):
            if mo:
                field_name = mo.group(1)
                locale_head_text = mo.group(2).encode('utf8')
                locale_head_hash = adler32(locale_head_text)
                yield 0, locale_head_hash, locale_head_text
                key_idx = self._field_names.index(field_name)
                for record in self._records[2:]:
                    key_text = record[key_idx].encode('utf8')
                    locale_text = record[val_idx].encode('utf8')
                    key_text_hash = adler32(key_text)
                    yield key_head_hash, key_text_hash, key_text
                    yield locale_head_hash, key_text_hash, locale_text

    def gen_l10n_text_rows(self):
        head_hash_bins = list(self.gen_l10n_bin_rows())

        texts = defaultdict(OrderedDict)
        for head, hash, bin in head_hash_bins[1:]:
            texts[head][hash] = bin.decode('utf8')

        head_texts = list(text for text in texts[0].values())
        yield head_texts

        head_hashes = list(texts[0].keys())
        head_items = [texts[head_hash].items() for head_hash in head_hashes[1:]]
        for pairs in zip(*head_items):
            hash = pairs[0][0]
            assert(all(pair[0] == hash for pair in pairs))
            yield [hash] + [pair[1] for pair in pairs]

if __name__ == '__main__':
    import logging
    FieldEnum.add("logging", lambda key: getattr(logging, key))

    import json
    FieldType.add("json", str, bytes, parse_text=lambda t, m, s: json.loads(t))

    import yaml
    FieldType.add("yaml", str, bytes, parse_text=lambda t, m, s: yaml.safe_load(t))

    int_type = FieldType.parse_expr("int")
    int_bin_type = FieldType.parse_expr("int:bin")
    int_oct_type = FieldType.parse_expr("int:oct")
    int_hex_type = FieldType.parse_expr("int:hex")
    int_pk_type = FieldType.parse_expr("int:pk")
    int16_pk_type = FieldType.parse_expr("int16:pk")
    int_fk_type = FieldType.parse_expr("int:fk:User.id")
    str_pk_type = FieldType.parse_expr("str:pk")
    str_pk_md5_type = FieldType.parse_expr("str:pk:md5")
    str_type = FieldType.parse_expr("str")
    str_ascii_type = FieldType.parse_expr("str:ascii")
    str_ascii_replace_type = FieldType.parse_expr("str:ascii:replace")
    str_utf8_type = FieldType.parse_expr("str:utf8")
    str_utf16_type = FieldType.parse_expr("str:utf16")
    date_type = FieldType.parse_expr("date")
    time_type = FieldType.parse_expr("time")
    span_type = FieldType.parse_expr("span")
    json_type = FieldType.parse_expr("json")
    yaml_type = FieldType.parse_expr("yaml")
    real_type = FieldType.parse_expr("real")
    enum_type = FieldType.parse_expr("enum:logging")

    print(int_type.parse_text("10"))
    print(int_bin_type.parse_text("10"))
    print(int_oct_type.parse_text("10"))
    print(int_hex_type.parse_text("10"))
    print(int_pk_type.parse_text("100"))
    print(int16_pk_type.parse_text("30000"))
    print(int_fk_type.parse_text("10000000000"))
    print(str_pk_type.parse_text("Hello:PK"))
    print(str_pk_md5_type.parse_text("Hello:PK:MD5"))
    print(str_type.parse_text("Hello"))
    print(str_ascii_type.parse_text("Hello:ASCII"))
    print(str_ascii_replace_type.parse_text("Hello:ASCII:REPLACE:안녕하세요"))
    print(str_utf8_type.parse_text("안녕하세요"))
    print(str_utf16_type.parse_text("안녕하세요"))
    print(date_type.parse_text("2022-12-18"))
    print(time_type.parse_text("11:50:07"))
    print(span_type.parse_text("01:20:30"))
    print(json_type.parse_text("[1, 2, 3]"))
    print(yaml_type.parse_text("{a: 1, b: 2}"))
    print(real_type.parse_text("1.23"))
    print(enum_type.parse_text("ERROR"))

    print(int_type.dump(10).hex())
    print(real_type.dump(1.23).hex())
    print(str_type.dump(b"TEST"))
    print(date_type.dump(datetime.now()))
    print(time_type.dump(timedelta(hours=1, minutes=2, seconds=3)))

    table = Table.parse([
        ['id', 'name', '$name[src]', 'desc', '$desc[src]'],
        ['int', 'str:fk:string.key', 'str:utf8', 'str:fk:string.key', 'str:utf8'],
        ['1', 'NAME_A', '가 이름', 'DESC_A', '가 설명'],
        ['2', 'NAME_B', '나 이름', 'DESC_B', '나 설명'],
    ])
    print(repr(table))

    for row in table.gen_l10n_bin_rows():
        head, hash, bin = row
        print(f"{head}:{hash}:{bin.decode('utf8')}")

    for row in table.gen_l10n_text_rows():
        print(row)
