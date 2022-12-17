from foundation.app import Application
from foundation.data import Config, String
from foundation.addr import Uri

from .env import EnvironConfig
from .res import YamlConfigFileParser

from .res import CFG

class GameConfig(Config):
    version = String(default="0.0.0")
    revision = String(default="0")

class GameApplication(Application):
    def _on_init(self):
        pass

    def add_config_dir_path(self, config_dir_path):
        Uri.add(CFG, config_dir_path)

    def _on_run(self):
        env_cfg = EnvironConfig.get()
        GameConfig.add(YamlConfigFileParser(Uri.get(CFG, 'game.cfg.yaml')))
        GameConfig.load()

        game_cfg = GameConfig.get()
        self.logger.info("initialized", version=game_cfg.version, revision=game_cfg.revision)
