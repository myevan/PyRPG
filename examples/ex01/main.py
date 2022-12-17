import os

if __name__ == '__main__':
    from foundation.addr import Uri
    from framework.scheme import CFG
    MODULE_DIR_PATH = os.path.dirname(os.path.realpath(__file__))
    Uri.add(CFG, os.path.join(MODULE_DIR_PATH, 'cfg'))

    from framework.game import GameApplication
    app = GameApplication()
    app.run()
    