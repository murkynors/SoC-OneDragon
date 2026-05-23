import ast
import traceback

from PySide6 import QtCore
from PySide6.QtCore import QRunnable, QThread

from device import adb_controller as ADBClass
from services.logger import LoggerSingleton


class Signals(QtCore.QObject):
    finished = QtCore.Signal()


class FlowRunnable(QRunnable):
    def __init__(self, flow):
        super().__init__(self)
        self.signal = Signals()
        self.flow = flow

    def run(self):
        self.flow.run()
        self.signal.finished.emit()


class FlowThread(QThread):
    finished = Signals()

    def __init__(self, flow):
        super().__init__()
        self.flow = flow

    def run(self):
        try:
            for fw in self.flow:
                # 每个流程步骤之间检查停止标记，避免用户点“停止”后还继续跑完整队列。
                if self.isInterruptionRequested() or ADBClass.AdbSingleton.getInstance().stop_requested:
                    LoggerSingleton.getInstance().info('./logs/log_test.txt', "流程已停止")
                    break
                result = fw.run()
                if result is False:
                    LoggerSingleton.getInstance().info('./logs/log_test.txt', "流程因前置步骤失败已停止")
                    break
        except RuntimeError as exc:
            if str(exc) == "流程已停止":
                LoggerSingleton.getInstance().info('./logs/log_test.txt', "流程已停止")
            else:
                traceback.print_exc()
                LoggerSingleton.getInstance().info('./logs/log_test.txt', f"流程异常停止：{exc}")
        except Exception as exc:
            traceback.print_exc()
            LoggerSingleton.getInstance().info('./logs/log_test.txt', f"流程异常停止：{exc}")
        self.finished.emit()


class Monitor:
    def __init__(self, filename, last_read_ptr=0):
        self.filename = filename
        self.last_read_ptr = last_read_ptr

    def check(self):
        with open(self.filename) as file:
            file.seek(0, 2)
            file.seek(max(self.last_read_ptr, 0), 0)

            # 日志写入器会把 bytes repr 写成单行，这里只读取上次位置之后的新增内容。
            content_lines = file.read().split("\n")
            new_content = ""
            for line in content_lines:
                if line != "":
                    new_content += ast.literal_eval(line).decode()
                    if line != content_lines[-2]:
                        new_content += '\n'

            self.last_read_ptr = file.tell()
            return (new_content, self.last_read_ptr)
