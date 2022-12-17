from .base import Model

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
