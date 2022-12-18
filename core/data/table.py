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

ROW_IDX_HEADS = 0
ROW_IDX_TYPES = 1
ROW_IDX_BODYS = 2

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
    expr_to_convert = {
        'str:pk:hash64': lambda v, m, s: hash(v),
        'str:pk:hash32': lambda v, m, s: hash(v),
        'str:pk:adler32': lambda v, m, s: adler32(v.encode('utf8')),
        'str:pk:crc32': lambda v, m, s: crc32(v.encode('utf8')),
        'str:pk:md5': lambda v, m, s: md5(v.encode('utf8')).digest(),
        'str:pk:sha1': lambda v, m, s: sha1(v.encode('utf8')).digest(),
        'str:pk:sha256': lambda v, m, s: sha256(v.encode('utf8')).digest(),
        'str:ascii:ignore': lambda v, m, s: v.encode('ascii', 'ignore'),
        'str:ascii:replace': lambda v, m, s: v.encode('ascii', 'replace'),
    }

    py_type_opt_to_convert = {
        (int, 'bin'): lambda v, m, s: int(v, 2),
        (int, 'oct'): lambda v, m, s: int(v, 8),
        (int, 'hex'): lambda v, m, s: int(v, 16),
        (int, 'pk'): lambda v, m, s: int(v),
        (int, 'fk'): lambda v, m, s: int(v),
        (str, 'pk'): lambda v, m, s: adler32(v.encode('utf8')),
        (str, 'fk'): lambda v, m, s: adler32(v.encode('utf8')),
    }

    py_type_to_convert = {
        str: lambda v, m, s: v,
        int: lambda v, m, s: int(v, int(m)) if m else int(v),
        float: lambda v, m, s: float(v),
        date: lambda v, m, s: datetime.strptime(v, "%Y-%m-%d").date(),
        datetime: lambda v, m, s: datetime.strptime(v, "%Y-%m-%d %H:%M:%S"),
        timedelta: lambda v, m, s: datetime.strptime(v, "%H:%M:%S") - DATETIME_STRPTIME_DEFAULT,
        Enum: lambda v, m, s: FieldEnum.get(m, v),
    }

    type_pair_to_dump = {
        (date, bytes): lambda v: str(v).encode('utf8'),
        (datetime, bytes): lambda v: str(v).encode('utf8'),
        (timedelta, bytes): lambda v: str(v).encode('utf8'),
    }

    @classmethod
    def add(cls, data_type_name, py_type, c_type, convert):
        cls.expr_to_convert[data_type_name] = convert
        cls.data_type_name_to_type_pair[data_type_name] = (py_type, c_type)

    @classmethod
    def parse(cls, expr: str):
        mo = cls.ro_field_type_expr.match(expr)
        if mo:
            data_type_name = mo.group(1)
            main_attr = mo.group(3)
            sub_attr = mo.group(5)
            return cls(expr, data_type_name, main_attr, sub_attr)

    def __init__(self, expr, data_type_name, main_attr, sub_attr):
        type_pair = self.expr_to_type_pair.get(expr, None)
        if not type_pair:
            type_pair = self.data_type_name_to_type_pair.get(data_type_name, None)
            if not type_pair:
                raise ValueError(f"UNKNOWN_DATA_TYPE={data_type_name} EXPR={expr}")

        convert = self.expr_to_convert.get(expr)
        if not convert:
            py_type = type_pair[0]
            convert = self.py_type_opt_to_convert.get((py_type, main_attr), None)
            if not convert:
                convert = self.py_type_to_convert[py_type]

        c_type = type_pair[1]
        dump = self.type_pair_to_dump.get(type_pair, c_type)

        self._type_pair = type_pair
        self._sub_attr = sub_attr
        self._main_attr = main_attr
        self._data_type_name = data_type_name
        self._convert = convert
        self._dump = dump
        self._expr = expr

    def __repr__(self):
        return self._expr

    def convert(self, val):
        return self._convert(val, self._main_attr, self._sub_attr)

    def dump(self, val):
        return bytes(self._dump(val))

class Table:
    class Error(Exception):
        def __init__(self, name, row, col, memo):
            super(Table.Error, self).__init__(name)
            self.name = name
            self.col = col
            self.row = row
            self.memo = memo

        def __str__(self):
            return f"{self.name}<ROW={self.row} COL={self.col} {self.memo}>"

    @classmethod
    def create(cls, rows: list):
        rowi = iter(rows)
        fld_names = next(rowi)
        fld_types = next(rowi)
        recs = list(rowi)
        return cls(fld_names, fld_types, recs)

    def __init__(self, fld_names, fld_types, recs):
        self._fld_names = fld_names
        self._fld_types = fld_types
        self._recs = recs

    def __repr__(self):
        head_line = ', '.join(fld_name for fld_name in self._fld_names)
        type_line = ', '.join(repr(fld_type) for fld_type in self._fld_types)
        body_lines = [
            ', '.join(repr(fld_value) for fld_value in record)
                for record in self._recs]
        return '\n'.join([head_line, type_line] + body_lines)

    @property
    def field_names(self): return self._fld_names

    @property
    def field_types(self): return self._fld_types

    @property
    def records(self): return self._recs

    @property
    def rows(self):
        yield self._fld_names
        yield self._fld_types
        for rec in self._recs:
            yield rec

class PyTable(Table):
    @classmethod
    def create(cls, org_table):
        def gen_field_types(row_idx, exprs: list):
            for col_idx, expr in enumerate(exprs):
                try:
                    yield FieldType.parse(expr)
                except ValueError as exc:
                    raise cls.Error(f"FIELD_TYPE_EXPR_ERROR", row=row_idx, col=col_idx, memo=str(exc))

        def gen_field_values(fld_types, fld_vals):
            for col_idx, (fld_type, fld_val) in enumerate(zip(fld_types, fld_vals)):
                yield fld_type.convert(fld_val)

        def gen_records(fld_types, rowi):
            for row_idx, fld_vals in enumerate(rowi):
                yield list(gen_field_values(fld_types, fld_vals))

        fld_names = org_table.field_names
        fld_exprs = org_table.field_types
        fld_types = list(gen_field_types(ROW_IDX_TYPES, fld_exprs))
        recs = list(gen_records(fld_types, org_table.records))
        return cls(fld_names, fld_types, recs)


class L10NBinaryTable(Table):
    RO_FIELD_NAME = re.compile('\$(\w+)\[(\w+)\]')

    @classmethod
    def create(cls, org_table):
        rowi = cls.gen_rows(org_table.field_names, org_table.records)
        heads = next(rowi)
        types = next(rowi)
        return cls(heads, types, list(rowi))

    @classmethod
    def gen_rows(cls, field_names, records):
        mos = [cls.RO_FIELD_NAME.match(field_name) for field_name in field_names]

        key_head_text = 'key'
        key_head_hash = adler32(key_head_text.encode('utf8'))
        yield 'head', 'hash', 'text'
        yield 'int', 'int', 'str:utf8'
        yield 0, 0, 'adler32'
        yield 0, key_head_hash, key_head_text
        for val_idx, mo in enumerate(mos):
            if mo:
                field_name = mo.group(1)
                locale_head_text = mo.group(2)
                locale_head_hash = adler32(locale_head_text.encode('utf8'))
                yield 0, locale_head_hash, locale_head_text
                key_idx = field_names.index(field_name)
                for record in records:
                    key_text = record[key_idx]
                    locale_text = record[val_idx]
                    key_text_hash = adler32(key_text.encode('utf8'))
                    yield key_head_hash, key_text_hash, key_text
                    yield locale_head_hash, key_text_hash, locale_text

class L10NTextTable(Table):
    @classmethod
    def create(cls, org_table):
        rowi = cls.gen_rows(org_table.field_names, org_table.records)
        heads = next(rowi)
        types = next(rowi)
        return cls(heads, types, list(rowi))

    @classmethod
    def gen_rows(cls, field_names, records):
        rows = list(L10NBinaryTable.gen_rows(field_names, records))

        texts = defaultdict(OrderedDict)
        for head, hash, text in rows[ROW_IDX_BODYS:]:
            texts[head][hash] = text

        head_texts = list(text for text in texts[0].values())
        yield head_texts

        type_texts = ['int', 'str', 'str']
        yield type_texts

        head_hashes = list(texts[0].keys())
        head_items = [texts[head_hash].items() for head_hash in head_hashes[1:]]
        for pairs in zip(*head_items):
            hash = pairs[0][0]
            assert(all(pair[0] == hash for pair in pairs))
            yield [hash] + [pair[1] for pair in pairs]

class CompactTable(Table):
    RO_FIELD_NAME = re.compile("\w+")

    @classmethod
    def create(cls, org_table):
        rowi = cls.gen_rows(org_table.field_names, org_table.field_types, org_table.records)
        heads = next(rowi)
        types = next(rowi)
        recs = list(rowi)
        return cls(heads, types, recs)

    @classmethod
    def gen_rows(cls, fld_names, fld_types, records):
        mos = [cls.RO_FIELD_NAME.match(name) for name in fld_names]
        idxs = [idx for idx, mo in enumerate(mos) if mo]

        yield [fld_names[idx] for idx in idxs]
        yield [fld_types[idx] for idx in idxs]

        for record in records:
            if not record: continue
            if not record[0].strip(): continue # empty record
            if record[0].startswith('#'): continue # comment record

            row = [record[idx] for idx in idxs]
            if not row[0].strip(): continue # empty row
            if row[0].startswith('#'): continue # comment row

            yield row

if __name__ == '__main__':
    import logging
    FieldEnum.add("logging", lambda key: getattr(logging, key))

    import json
    FieldType.add("json", str, bytes, convert=lambda t, m, s: json.loads(t))

    import yaml
    FieldType.add("yaml", str, bytes, convert=lambda t, m, s: yaml.safe_load(t))

    int_type = FieldType.parse("int")
    int_bin_type = FieldType.parse("int:bin")
    int_oct_type = FieldType.parse("int:oct")
    int_hex_type = FieldType.parse("int:hex")
    int_pk_type = FieldType.parse("int:pk")
    int16_pk_type = FieldType.parse("int16:pk")
    int_fk_type = FieldType.parse("int:fk:User.id")
    str_pk_type = FieldType.parse("str:pk")
    str_pk_md5_type = FieldType.parse("str:pk:md5")
    str_type = FieldType.parse("str")
    str_ascii_type = FieldType.parse("str:ascii")
    str_ascii_replace_type = FieldType.parse("str:ascii:replace")
    str_utf8_type = FieldType.parse("str:utf8")
    str_utf16_type = FieldType.parse("str:utf16")
    date_type = FieldType.parse("date")
    time_type = FieldType.parse("time")
    span_type = FieldType.parse("span")
    json_type = FieldType.parse("json")
    yaml_type = FieldType.parse("yaml")
    real_type = FieldType.parse("real")
    enum_type = FieldType.parse("enum:logging")

    print(int_type.convert("10"))
    print(int_bin_type.convert("10"))
    print(int_oct_type.convert("10"))
    print(int_hex_type.convert("10"))
    print(int_pk_type.convert("100"))
    print(int16_pk_type.convert("30000"))
    print(int_fk_type.convert("10000000000"))
    print(str_pk_type.convert("Hello:PK"))
    print(str_pk_md5_type.convert("Hello:PK:MD5"))
    print(str_type.convert("Hello"))
    print(str_ascii_type.convert("Hello:ASCII"))
    print(str_ascii_replace_type.convert("Hello:ASCII:REPLACE:안녕하세요"))
    print(str_utf8_type.convert("안녕하세요"))
    print(str_utf16_type.convert("안녕하세요"))
    print(date_type.convert("2022-12-18"))
    print(time_type.convert("11:50:07"))
    print(span_type.convert("01:20:30"))
    print(json_type.convert("[1, 2, 3]"))
    print(yaml_type.convert("{a: 1, b: 2}"))
    print(real_type.convert("1.23"))
    print(enum_type.convert("ERROR"))

    print(int_type.dump(10).hex())
    print(real_type.dump(1.23).hex())
    print(str_type.dump(b"TEST"))
    print(date_type.dump(datetime.now()))
    print(time_type.dump(timedelta(hours=1, minutes=2, seconds=3)))

    org_rows = [
        ["id",      "name",     "$name[src]",   "desc",     "$desc[src]"   "ave_score",     "#comment"],
        ["int:pk",  "str",      "str:utf8",     "str",      "str:utf8",    "real",          "str:utf8"],
        ["1",       "NAME_A",   "가 이름",      "DESC_A",   "가 설명",      7.2,            "주석1"],
        ["2",       "NAME_B",   "나 이름",      "DESC_B",   "나 설명",      8.5,            "주석2"],
    ]

    org_table = Table.create(org_rows)
    print(repr(org_table))
    print("---")

    l10n_bin_table = L10NBinaryTable.create(org_table)
    print(repr(l10n_bin_table))
    print("---")

    l10n_txt_table = L10NTextTable.create(org_table)
    print(repr(l10n_txt_table))
    print("---")

    compact_table = CompactTable.create(org_table)
    print(repr(compact_table))
    print("---")

    py_table = PyTable.create(compact_table)
    print(repr(py_table))
    print("---")
