import inspect

class Field:
    class Error(Exception):
        def __init__(self, name, value, memo):
            super(Field.Error, self).__init__(name)
            self.__value = value
            self.__memo = memo

        @property
        def value(self):
            return self.__value

        @property
        def memo(self):
            return self.__memo

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
