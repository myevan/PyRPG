import os

MODULE_DIR_PATH = os.path.dirname(os.path.realpath(__file__))

if __name__ == '__main__':
    from framework.game import GameApplication
    app = GameApplication()
    app.add_config_dir_path(os.path.join(MODULE_DIR_PATH, 'configs'))
    app.run()
    