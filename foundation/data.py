import inspect

class FieldError(Exception):
    def __init__(self, name, value, memo):
        super(FieldError, self).__init__(name)
        self.__value = value
        self.__memo = memo

    @property
    def value(self):
        return self.__value

    @property
    def memo(self):
        return self.__memo

class Field:
    __seq = 0

    @classmethod
    def alloc_sequence(cls):
        cls.__seq += 1
        return cls.__seq

    def __init__(self, builtin_code, builtin_value, count=None, pk=False, fk=None, default=None, name=None, code=None):
        self.__seq = Field.alloc_sequence()
        self.__count = count
        self.__pk = pk
        self.__fk = fk
        self.__code = code
        self.__code = builtin_code if code is None else code
        self.__value = builtin_value if default is None else default
        self.__name = name
        self.__model_cls = None

    def __repr__(self):
        def gen_attrs():
            if self.__count:
                yield str(self.__count)
            if self.__pk:
                yield 'pk=True'

        attrs = ', '.join(gen_attrs())
        if self.__model_cls:
            return f"{self.__class__.__name__}<{self.__model_cls.__name__}.{self.__name}>({attrs})"
        else:
            return f"{self.__class__.__name__}({attrs})"

    def bind(self, model_cls, name):
        self.__model_cls = model_cls
        self.__name = name

    def convert(self, value):
        return value

    @property
    def seq(self):
        return self.__seq

    @property
    def name(self):
        return self.__name

    @property
    def count(self):
        return self.__count

    @property
    def code(self):
        return self.__code

    @property
    def default_value(self):
        return self.__value

    @property
    def key_name(self):
        assert(self.__model_cls)
        return f"({self.__model_cls.__name__}.{self.__name})"

    @property
    def binding(self):
        return self.__model_cls

    @property
    def foreign_key(self):
        return self.__fk

    @property
    def is_primary_key(self):
        return self.__pk

class DeclMeta(type):
    def __new__(meta, name, bases, attrs):
        new_cls = type.__new__(meta, name, bases, attrs)

        field_pairs = inspect.getmembers(new_cls, lambda m:isinstance(m, Field))
        for field_name, field_type in field_pairs:
            field_type.bind(new_cls, field_name)

        if field_pairs:
            field_pairs.sort(key=lambda x: x[1].seq)
            new_cls._field_names, new_cls._field_types = list(zip(*field_pairs))
        else:
            new_cls._field_names = []
            new_cls._field_types = []

        new_cls._pk_names = [field_type.name for field_type in new_cls._field_types if field_type.is_primary_key]

        return new_cls

class Model(metaclass=DeclMeta):
    __repr_limit = 3

    @classmethod
    def get_field_names(cls):
        return cls._field_names

    @classmethod
    def get_field_types(cls):
        return cls._field_types

    @classmethod
    def get_primary_key_names(cls):
        return cls._pk_names

    def __init__(self, *args, **kwargs):
        total_field_names = self.get_field_names()
        for name, value in zip(total_field_names, args):
            setattr(self, name, value)

        total_field_types = self.get_field_types()
        input_count = len(args)
        extra_field_types = total_field_types[input_count:] 
        for field_type in extra_field_types:
            setattr(self, field_type.name, kwargs.get(field_type.name, field_type.default_value))

    def __repr__(self):
        info = ' '.join(f'{key}="{value}"' if type(value) is str else f'{key}={value}' for key, value in self.gen_field_pairs(limit=self.__repr_limit))
        return f"{self.__class__.__name__}({info})"

    def gen_field_pairs(self, limit=None):
        if limit is None:
            for name in self.get_field_names():
                yield (name, getattr(self, name))
        else:
            for name in self.get_field_names()[:limit]:
                yield (name, getattr(self, name))

    def get_primary_key_values(self):
        pk_names = self.get_primary_key_names()
        assert(pk_names)
        if len(pk_names) == 1:
            return getattr(self, pk_names[0])
        else:
            return tuple(getattr(self, name) for name in pk_names)

class Config(Model):
    class Parser:
        def deserialize(self):
            return dict()

    _inst = None
    _parsers = []

    @classmethod
    def get(cls):
        if not cls._inst:
            cls._inst = cls()

        return cls._inst

    @classmethod
    def add(cls, parser):
        cls._parsers.append(parser)

    @classmethod
    def load(cls):
        inst = cls.get()
        for parser in cls._parsers:
            data = parser.deserialize()
            assert(type(data) is dict)
            inst.set(data)

    def set(self, in_dict):
        total_field_names = self.get_field_names()
        total_field_types = self.get_field_types()
        for field_type, field_name in zip(total_field_types, total_field_names):
            org_val = in_dict[field_name]
            cnv_val = field_type.convert(org_val)
            setattr(self, field_name, cnv_val)

class Integer(Field):
    def __init__(self, *args, **kwargs):
        super(Integer, self).__init__('i', 0, *args, **kwargs)
        self.min = -0x800000000000000
        self.max = +0x7FFFFFFFFFFFFFF

    def convert(self, value):
        ret_value = int(value)
        if ret_value < self.min: raise FieldError('UNDERFLOW', ret_value, f"< {self.min}")
        if ret_value > self.max: raise FieldError('OVERFLOW', ret_value, f"> {self.max}")
        return ret_value

class Float(Field):
    def __init__(self, *args, **kwargs):
        super(Float, self).__init__('f', 0.0, *args, **kwargs)

    def convert(self, value):
        return float(value)
    
class String(Field):
    def __init__(self, *args, **kwargs):
        super(String, self).__init__('s', "", *args, **kwargs)

    def convert(self, value):
        return str(value)

class Enum(Field):
    def __init__(self, map, *args, **kwargs):
        super(Enum, self).__init__('e', 0, *args, **kwargs)
        self.map = map

    def convert(self, value):
        ret_value = getattr(self.map, value, None)
        if ret_value is None: raise FieldError('UNKNOWN', ret_value, f"not in {self.mappings}")
        return ret_value

class Position(Field):
    def __init__(self, *args, **kwargs):
        super(Position, self).__init__('p', (0, 0, 0), *args, **kwargs)

class Rotation(Field):
    def __init__(self, *args, **kwargs):
        super(Rotation, self).__init__('d', 0, *args, **kwargs) # 0: x+

if __name__ == '__main__':
    class User(Model):
        id = Integer(pk=True)
        name = String()

    class Profile(Model):
        id = Integer(pk=True)
        user_id = Integer(fk=User.id)

    print(User.id)
    user = User(id=1, name="a")
    print(user)
    print(Profile.user_id.foreign_key)

