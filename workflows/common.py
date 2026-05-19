from soc_one_dragon.device import adb_controller as ADBClass
from soc_one_dragon.services.logger import LoggerSingleton


LOG_PATH = './logs/log_test.txt'


def adb():
    return ADBClass.AdbSingleton.getInstance()


def log(message):
    LoggerSingleton.getInstance().info(LOG_PATH, message)


class SetupAdb:
    def __init__(self, adb_path, adb_port, retry_count):
        self.adb_path = adb_path
        self.adb_port = adb_port
        self.retry_count = retry_count

    def run(self):
        return adb().connectDevice(
            adb_path=self.adb_path,
            adb_port=self.adb_port,
            retryCount=self.retry_count
        )
