import logging
import yaml

from foundation.data import Config

TAG = 'cfg'

class YamlConfigFileParser(Config.Parser):
    logger = logging.getLogger(TAG)

    def __init__(self, file_path):
        self.file_path = file_path

    def deserialize(self):
        self.logger.debug('loading', file_path=self.file_path)
        return yaml.safe_load(open(self.file_path).read())
