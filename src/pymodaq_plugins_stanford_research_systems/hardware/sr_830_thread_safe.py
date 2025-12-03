from threading import Lock

from pymeasure.instruments.srs.sr830 import SR830

from pymodaq.utils.logger import set_logger, get_module_name

lock = Lock()
logger = set_logger(get_module_name(__file__), add_to_console=False)

class SR830ThreadSafe(SR830):

    def read(self, **kwargs):
        value = None
        try:
            lock.acquire()
            value = super().read(**kwargs)
        except Exception as e:
            logger.debug(str(e))
        finally:
            lock.release()

        return value

    def write(self, command, **kwargs):
        try:
            lock.acquire()
            super().write(command, **kwargs)
        except Exception as e:
            logger.debug(str(e))
        finally:
            lock.release()
