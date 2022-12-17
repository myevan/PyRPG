from .base import Field

class Integer(Field):
    def __init__(self, *args, **kwargs):
        super(Integer, self).__init__('i', 0, *args, **kwargs)
        self.min = -0x800000000000000
        self.max = +0x7FFFFFFFFFFFFFF

    def convert(self, value):
        ret_value = int(value)
        if ret_value < self.min: raise Field.Error('UNDERFLOW', ret_value, f"< {self.min}")
        if ret_value > self.max: raise Field.Error('OVERFLOW', ret_value, f"> {self.max}")
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
        if ret_value is None: raise Field.Error('UNKNOWN', ret_value, f"not in {self.mappings}")
        return ret_value

class Position(Field):
    def __init__(self, *args, **kwargs):
        super(Position, self).__init__('p', (0, 0, 0), *args, **kwargs)

class Rotation(Field):
    def __init__(self, *args, **kwargs):
        super(Rotation, self).__init__('d', 0, *args, **kwargs) # 0: x+
