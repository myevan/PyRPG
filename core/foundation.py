import logging
import sys
import os

EXIT_CODE_OK = 0
EXIT_CODE_EXCEPTION = -1

CORE_MODULE_DIR_PATH = os.path.dirname(os.path.realpath(__file__))
CODE_PROJECT_DIR_PATH = os.path.realpath(os.path.join(CORE_MODULE_DIR_PATH, '..'))
CODE_DIR_PATH = os.path.realpath(os.path.join(CODE_PROJECT_DIR_PATH, '..'))
WORK_DIR_PATH = os.path.realpath(os.path.join(CODE_DIR_PATH, '..'))

class Uri:
    _scheme_abs_paths = {}

    @classmethod
    def add_scheme_path(cls, scheme_name, scheme_abs_path):
        cls._scheme_abs_paths[scheme_name] = scheme_abs_path

    @classmethod
    def get_scheme_path(cls, scheme_name):
        return cls._scheme_abs_paths.get(scheme_name)

    @classmethod
    def get_file_path(cls, scheme_name, file_name):
        scheme_abs_path = cls._scheme_abs_paths[scheme_name]
        return os.path.join(scheme_abs_path, file_name)

class StructuredLogger(logging.Logger):
    @classmethod
    def wrap(cls, func, key):
        wrapped_func = lambda *args, **kwargs: func(*args, extra={key: kwargs})
        setattr(logging.Logger, func.__name__, wrapped_func)

class Application:
    class Error(Exception):
        def __init__(self, code, name, message):
            super(Application.Error, self).__init__(self, name)
            self.code = code
            self.message = message

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
        
        Uri.add_scheme_path('code', CODE_DIR_PATH)
        Uri.add_scheme_path('work', WORK_DIR_PATH)

        self._exit_code = 0

    def run(self):
        self.logger.debug('initializing', sys_argv=sys.argv)
        self._on_initializing()

        self.logger.debug('running')

        try:
            self._on_running()

            self.logger.debug('exiting', exit_code=self._exit_code)
            self._on_exiting()
            sys.exit(EXIT_CODE_OK)
        except Application.Error as err:
            self.logger.error('Application.Error',
                err_code=err.code,
                err_name=err.name,
                err_mssage=err.message)

            self._on_exiting()
            sys.exit(err.code)
        except Exception as exc:
            if self.is_debugger_attached:
                raise exc

            self._on_exiting()
            sys.exit(EXIT_CODE_EXCEPTION)

    def _on_initializing(self):
        pass

    def _on_running(self) -> int:
        pass

    def _on_exiting(self):
        pass

    @property
    def is_debugger_attached(self):
        sys_gettrace = getattr(sys, 'gettrace', 'None')
        if sys_gettrace:
            if sys_gettrace():
                return True

        return False

