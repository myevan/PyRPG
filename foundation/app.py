import logging
import sys

class StructuredLogger(logging.Logger):
    @classmethod
    def wrap(cls, func, key):
        wrapped_func = lambda *args, **kwargs: func(*args, extra={key: kwargs})
        setattr(logging.Logger, func.__name__, wrapped_func)

class Application:
    logger = logging.getLogger('app')

    def __init__(self, logging_level=None):
        logging_format = "%(asctime)s\t%(levelname)s\t%(name)s\t%(message)s %(context)s"
        if logging_level:
            logging.basicConfig(level=logging_level, format=logging_format)
        else:
            if '--debug' in sys.argv:
                logging.basicConfig(level=logging.DEBUG, format=logging_format)
            else:
                logging.basicConfig(level=logging.INFO, format=logging_format)

        for func in [
            logging.Logger.critical, 
            logging.Logger.error,
            logging.Logger.warning,
            logging.Logger.info,
            logging.Logger.debug]:
            StructuredLogger.wrap(func, 'context')

        self.logger.debug('initializing', sys_argv=sys.argv)
        self._on_init()

    def run(self):
        self.logger.debug('running')
        exit_code = self._on_run()
        self.exit(exit_code)

    def exit(self, code):
        self.logger.debug('exiting', code=code)
        self._on_exit()
        sys.exit(code if code else 0)

    def _on_init(self):
        pass

    def _on_run(self):
        pass

    def _on_exit(self):
        pass

