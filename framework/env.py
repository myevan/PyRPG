import os

from foundation.data import Config, String

from foundation import MODULE_DIR_PATH as FOUNDATION_DIR_PATH

class EnvironConfig(Config):
    CODE_PROJECT_DIR_PATH = os.path.realpath(os.path.join(FOUNDATION_DIR_PATH, '..'))
    CODE_DIR_PATH = os.path.realpath(os.path.join(FOUNDATION_DIR_PATH, '..', '..'))
    WORK_DIR_PATH = os.path.realpath(os.path.join(FOUNDATION_DIR_PATH, '..', '..', '..'))

    game_config_file_name = String(default='game.cfg.yaml')