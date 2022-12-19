import re
import json

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

class t_str(str): pass
class t_md5(str): pass
class t_sha1(str): pass
class t_sha256(str): pass
class t_json(str): pass
class t_int(int): pass
class t_uint(int): pass
class t_alder32(int): pass
class t_crc32(int): pass
class t_real(float): pass
class t_date(date): pass
class t_datetime(datetime): pass
class t_timedelta(timedelta): pass

class FieldType:
    """
    data_type:main_attr:sub_attr
    """
    ro_field_type_expr = re.compile(r"(\w+)(:([^:]+)(:(.+))?)?")

    data_type_name_to_type_pair = {
        'json':     (t_json, bytes),
        'str':      (t_str, bytes),
        'md5':      (t_md5, bytes),
        'sha1':     (t_sha1, bytes),
        'sha256':   (t_sha256, bytes),
        'int':      (t_int, c_int32),
        'int8':     (t_int, c_int8),
        'int16':    (t_int, c_int16),
        'int32':    (t_int, c_int32),
        'int64':    (t_int, c_int64),
        'uint':     (t_uint, c_uint32),
        'uint8':    (t_uint, c_uint8),
        'uint16':   (t_uint, c_uint16),
        'uint32':   (t_uint, c_uint32),
        'uint64':   (t_uint, c_uint64),
        'adler32':  (t_alder32, c_uint32),
        'crc32':    (t_crc32, c_uint32),
        'real':     (t_real, c_float),
        'real32':   (t_real, c_float),
        'real64':   (t_real, c_double),
        'date':     (t_date, bytes),
        'datetime': (t_datetime, bytes),
        'span':     (t_timedelta, bytes),
        'time':     (t_timedelta, bytes),
    }

    type_pair_to_convert = {
        (t_int, 'bin'): lambda v, m, s: int(v, 2),
        (t_int, 'oct'): lambda v, m, s: int(v, 8),
        (t_int, 'hex'): lambda v, m, s: int(v, 16),
        (t_int, 'pk'): lambda v, m, s: int(v),
        (t_int, 'fk'): lambda v, m, s: int(v),
        (t_int, 'enum'): lambda v, m, s: FieldEnum.get(s, v),
        (t_str, 'key'): lambda v, m, s: v,
    }

    type_to_convert = {
        t_json: lambda v, m, s: json.loads(v),
        t_str: lambda v, m, s: str(v),
        t_real: lambda v, m, s: float(v),
        t_int: lambda v, m, s: int(v, int(m)) if m else int(v),
        t_date: lambda v, m, s: datetime.strptime(v, "%Y-%m-%d").date(),
        t_datetime: lambda v, m, s: datetime.strptime(v, "%Y-%m-%d %H:%M:%S"),
        t_timedelta: lambda v, m, s: datetime.strptime(v, "%H:%M:%S") - DATETIME_STRPTIME_DEFAULT,
    }

    # https://www.sami-lehtinen.net/blog/python-hash-function-performance-comparison
    #  13: python hash
    #  49: zlib.alder32
    #  91: zlib.crc32
    # 180: hashlib.md5
    # 179: hashlib.sha1
    # 403: hashlib.sha256
    type_pair_to_dump = {
        (t_int, 'pk'): lambda v, m, s, c: bytes(c(v)),
        (t_int, 'fk'): lambda v, m, s, c: bytes(c(v)),
        (t_str, 'hash64'): lambda v, m, s, c: bytes(c_uint64(hash(v))),
        (t_str, 'hash32'): lambda v, m, s, c: bytes(c_uint32(hash(v))),
        (t_str, 'crc32'): lambda v, m, s, c: bytes(c_uint32(crc32(v.encode('utf8')))),
        (t_str, 'adler32'): lambda v, m, s, c: bytes(c_uint32(adler32(v.encode('utf8')))),
        (t_str, 'key'): lambda v, m, s, c: bytes(c_uint32(adler32(v.encode('utf8')))),
        (t_str, 'pk'): lambda v, m, s, c: v.encode('utf8'),
        (t_str, 'fk'): lambda v, m, s, c: v.encode('utf8'),
        (t_str, 'utf8'): lambda v, m, s, c: v.encode('utf8', s if s else 'strict'),
        (t_str, 'utf16'): lambda v, m, s, c: v.encode('utf16', s if s else 'strict'),
        (t_str, 'ascii'): lambda v, m, s, c: v.encode('ascii', s if s else 'strict'),
        (t_str, 'md5'): lambda v, m, s, c: md5(v.encode('utf8')).digest(),
        (t_str, 'sha1'): lambda v, m, s, c: sha1(v.encode('utf8')).digest(),
        (t_str, 'sha256'): lambda v, m, s, c: sha256(v.encode('utf8')).digest(),
    }

    type_to_dump = {
        t_str: lambda v, m, s, c: v.encode(m, s if s else 'strict') if m else v.encode('utf8'),
        t_date: lambda v, m, s, c: str(v).encode('utf8'),
        t_datetime: lambda v, m, s, c: str(v).encode('utf8'),
        t_timedelta: lambda v, m, s, c: str(v).encode('utf8'),
    }

    @classmethod
    def add(cls, data_type_name, t_type, c_type, convert):
        cls.data_type_name_to_type_pair[data_type_name] = (t_type, c_type)
        cls.type_to_convert[t_type] = convert

    @classmethod
    def parse(cls, expr: str):
        mo = cls.ro_field_type_expr.match(expr)
        if mo:
            data_type_name = mo.group(1)
            main_attr = mo.group(3)
            sub_attr = mo.group(5)
            return cls(data_type_name, main_attr, sub_attr, expr)

    def __init__(self, data_type_name, main_attr, sub_attr, expr):
        t_type, c_type = self.data_type_name_to_type_pair[data_type_name]

        if main_attr:
            convert = self.type_pair_to_convert.get((t_type, main_attr))
            dump = self.type_pair_to_dump.get((t_type, main_attr))
            if convert == None and dump == None:
                raise ValueError(f"UNKNONW_MAIN_ATTR: {main_attr}")
        else:
            convert = self.type_to_convert[t_type]
            dump = self.type_to_dump.get(t_type, lambda v, m, s, c: bytes(c(v)))

        self._c_type = c_type
        self._t_type = t_type
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
        return self._dump(val, self._main_attr, self._sub_attr, self._c_type)

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
        head_line = ', '.join(repr(fld_name) for fld_name in self._fld_names)
        type_line = ', '.join(repr(fld_type) for fld_type in self._fld_types)
        body_lines = [
            ', '.join(fld_val.hex() if type(fld_val) is bytes else repr(fld_val) for fld_val in rec)
                for rec in self._recs]
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


class L10NHashTable(Table):
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
        rows = list(L10NHashTable.gen_rows(field_names, records))

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
    def gen_rows(cls, fld_names, fld_types, recs):
        mos = [cls.RO_FIELD_NAME.match(name) for name in fld_names]
        idxs = [idx for idx, mo in enumerate(mos) if mo]

        yield [fld_names[idx] for idx in idxs]
        yield [fld_types[idx] for idx in idxs]

        for rec in recs:
            if not rec: continue
            if not rec[0].strip(): continue # empty
            if rec[0].startswith('#'): continue # comment

            vals = [rec[idx] for idx in idxs]
            if not vals[0].strip(): continue # empty
            if vals[0].startswith('#'): continue # comment

            yield vals

class BinaryTable(Table):
    @classmethod
    def create(cls, org_table):
        rowi = cls.gen_rows(org_table.field_names, org_table.field_types, org_table.records)
        heads = next(rowi)
        types = next(rowi)
        recs = list(rowi)
        return cls(heads, types, recs)

    @classmethod
    def gen_rows(cls, fld_names, fld_types, recs):
        yield [fld_name.encode('utf8') for fld_name in fld_names]
        yield [repr(fld_type).encode('utf8') for fld_type in fld_types]
        for rec in recs:
            yield [fld_type.dump(val) for fld_type, val in zip(fld_types, rec)]


if __name__ == '__main__':
    import logging
    FieldEnum.add("logging", lambda key: getattr(logging, key))

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
    str_md5_type = FieldType.parse("str:md5")
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
    enum_type = FieldType.parse("int:enum:logging")

    print(int_type.convert("10"))
    print(int_bin_type.convert("10"))
    print(int_oct_type.convert("10"))
    print(int_hex_type.convert("10"))
    print(real_type.convert("1.23"))
    print(enum_type.convert("ERROR"))
    print(str_type.convert("Hello"))
    print(repr(date_type.convert("2022-12-18")))
    print(repr(time_type.convert("11:50:07")))
    print(repr(span_type.convert("01:20:30")))
    print(repr(json_type.convert("[1, 2, 3]")))
    print(repr(yaml_type.convert("{a: 1, b: 2}")))

    print(int_type.dump(10).hex())
    print(int16_pk_type.dump(30000).hex())
    print(real_type.dump(1.23).hex())
    print(str_type.dump("TEST"))
    print(str_pk_type.dump("PK"))
    print(str_ascii_type.dump("Hello:ASCII"))
    print(str_ascii_replace_type.dump("Hello:ASCII:REPLACE:안녕하세요"))
    print(str_utf8_type.dump("안녕하세요").hex())
    print(str_utf16_type.dump("안녕하세요").hex())
    print(str_md5_type.dump("Hello:MD5"))
    print(date_type.dump(datetime.now()))
    print(time_type.dump(timedelta(hours=1, minutes=2, seconds=3)))

    org_rows = [
        ["id",      "name",     "$name[src]",   "desc",     "$desc[src]",  "ave_score", "duration", "#comment"],
        ["int:pk",  "str:key",  "str",          "str:key",  "str",         "real",      "span",     "str"],
        ["1",       "NAME_A",   "가 이름",      "DESC_A",   "가 설명",      7.2,        "00:01:01", "주석1"],
        ["2",       "NAME_B",   "나 이름",      "DESC_B",   "나 설명",      8.5,        "01:00:00", "주석2"],
    ]

    org_table = Table.create(org_rows)
    print(repr(org_table))
    print("---")

    l10n_hash_table = L10NHashTable.create(org_table)
    print(repr(l10n_hash_table))
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

    bin_table = BinaryTable.create(py_table)
    print(repr(bin_table))
    print("---")