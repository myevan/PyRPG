from core.foundation import Application, Uri

from game.configs import EnvironConfig, GameConfig
from game.plugins.plugin_PyYAML import YamlConfigFileParser

class GameApplication(Application):
    def add_config_dir_path(self, config_dir_path):
        Uri.add_scheme_path('cfg', config_dir_path)

    def _on_initializing(self):
        env_cfg = EnvironConfig.get()

        GameConfig.add(YamlConfigFileParser(Uri.get_file_path('cfg', env_cfg.game_config_file_name)))
        GameConfig.load()

        game_cfg = GameConfig.get()
        self.logger.info("initialized", version=game_cfg.version, revision=game_cfg.revision)
