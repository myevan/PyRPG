import logging
import yaml

from core.data import Config

class YamlConfigFileParser(Config.Parser):
    logger = logging.getLogger('cfg')

    def __init__(self, file_path):
        self.file_path = file_path

    def deserialize(self):
        self.logger.debug('loading', file_path=self.file_path)
        return yaml.safe_load(open(self.file_path).read())