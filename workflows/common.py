import os
import time

from device import adb_controller as ADBClass
from services.logger import LoggerSingleton
from utils import image_tools as OctoUtil


LOG_PATH = './logs/log_test.txt'


def adb():
    return ADBClass.AdbSingleton.getInstance()


def log(message):
    LoggerSingleton.getInstance().info(LOG_PATH, message)


def find_template(template_path, screenshot_path, threshold=0.72):
    if not os.path.exists(template_path):
        return None
    return OctoUtil.OctoUtil.cv2CheckImgExist(template_path, screenshot_path, threshold=threshold)


def wait_and_click_template(
        template_path,
        screenshot_path,
        step_name,
        timeout_seconds=30,
        interval_seconds=1,
        threshold=0.72,
        sleep_after_click=1
):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        adb().screen_capture(screenshot_path)
        pos = find_template(template_path, screenshot_path, threshold=threshold)
        print(f"cv2 result ({template_path}): ", pos)
        if pos is not None:
            adb().tap(pos)
            time.sleep(sleep_after_click)
            return True
        if OctoUtil.OctoUtil.handleCommonBlockingScreen(screenshot_path):
            continue
        time.sleep(interval_seconds)
    log(f"普通战斗流程超时：未找到{step_name}")
    return False


def run_manual_battle_flow(
        screenshot_prefix,
        battle_start_timeout=30,
        auto_switch_timeout=20,
        win_timeout=240
):
    if not wait_and_click_template(
            './Icons/battleStart.png',
            f'./img/{screenshot_prefix}BattleStart.png',
            '开始战斗按钮',
            timeout_seconds=battle_start_timeout,
            sleep_after_click=8
    ):
        return False

    wait_and_click_template(
        './Icons/manuelBattleSwitch.png',
        f'./img/{screenshot_prefix}ManualSwitch.png',
        '自动战斗按钮',
        timeout_seconds=auto_switch_timeout,
        sleep_after_click=1
    )

    return wait_and_click_template(
        './Icons/winBattleText.png',
        f'./img/{screenshot_prefix}WinBattle.png',
        '战斗胜利',
        timeout_seconds=win_timeout,
        interval_seconds=5,
        sleep_after_click=3
    )


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
