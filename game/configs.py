from core.data import Config, String

class EnvironConfig(Config):
    game_config_file_name = String(default='game.config.yaml')

class GameConfig(Config):
    version = String(default="0.0.0")
    revision = String(default="0")
