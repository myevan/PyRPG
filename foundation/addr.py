import os

class Uri:
    _scheme_abs_paths = {}

    @classmethod
    def add(cls, scheme_name, scheme_abs_path):
        cls._scheme_abs_paths[scheme_name] = scheme_abs_path

    @classmethod
    def get(cls, scheme_name, asset_rel_path):
        scheme_abs_path = cls._scheme_abs_paths[scheme_name]
        return os.path.join(scheme_abs_path, asset_rel_path)
