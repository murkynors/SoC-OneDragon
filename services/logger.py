import logging
from pathlib import Path


class LoggerSingleton:
    instance = None

    def __init__(self):
        self._logger = logging.getLogger(__name__)

    @staticmethod
    def getInstance():
        if LoggerSingleton.instance is None:
            LoggerSingleton.instance = LoggerSingleton()
        return LoggerSingleton.instance

    def info(self, filename, msg):
        logger = self.getInstance()._logger
        logger.setLevel(logging.INFO)

        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        if len(logger.handlers) == 0:
            file_handler = logging.FileHandler(filename)
            logger.addHandler(file_handler)

        # UI 端按 bytes repr 解析日志，暂时保留这个写入格式以兼容现有读取逻辑。
        logger.info(msg.encode("utf-8"))

