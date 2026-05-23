import os
import time

from device import adb_controller as ADBClass
from utils import image_tools as OctoUtil
from workflows.common import adb, log


class pvpWorkflow:
    DEFAULT_SETTINGS = {
        "difficulty": "normal",
        "battleCount": 1,
    }
    DIFFICULTY_LABELS = {
        "easy": "简单",
        "normal": "普通",
        "hard": "困难",
    }
    DIFFICULTY_INDEX = {
        "easy": 0,
        "normal": 1,
        "hard": 2,
    }

    def __init__(self, adb_path, adb_port, settings=None):
        self.adb_path = adb_path
        self.adb_port = adb_port
        self.settings = self.resolve_settings(settings)

    def resolve_settings(self, settings):
        resolved = dict(self.DEFAULT_SETTINGS)
        if isinstance(settings, dict):
            difficulty = settings.get("difficulty")
            if difficulty in self.DIFFICULTY_INDEX:
                resolved["difficulty"] = difficulty
            try:
                resolved["battleCount"] = max(1, int(settings.get("battleCount", resolved["battleCount"])))
            except (TypeError, ValueError):
                resolved["battleCount"] = self.DEFAULT_SETTINGS["battleCount"]
        return resolved

    def log(self, message):
        log(message)

    def capture(self, path="./img/pvpFlow.png"):
        adb().screen_capture(path)
        return path

    def click_pos(self, pos, sleep_seconds=1):
        adb().tap(pos)
        time.sleep(sleep_seconds)

    def find_template(
            self,
            template_path,
            screenshot_path="./img/pvpFlow.png",
            threshold=0.8,
            is_single=True,
            min_x=None,
            max_x=None,
            min_y=None,
            max_y=None
    ):
        if not os.path.exists(template_path):
            return None
        return OctoUtil.OctoUtil.cv2CheckImgExist(
            template_path,
            screenshot_path,
            isSingle=is_single,
            threshold=threshold,
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y
        )

    def click_template(
            self,
            template_path,
            screenshot_path="./img/pvpFlow.png",
            retries=3,
            sleep_seconds=1,
            threshold=0.8,
            min_x=None,
            max_x=None,
            min_y=None,
            max_y=None
    ):
        for _ in range(retries):
            self.capture(screenshot_path)
            pos = self.find_template(
                template_path,
                screenshot_path,
                threshold=threshold,
                min_x=min_x,
                max_x=max_x,
                min_y=min_y,
                max_y=max_y
            )
            print(f"cv2 result ({template_path}): ", pos)
            if pos is not None:
                self.click_pos(pos, sleep_seconds)
                return True
            if OctoUtil.OctoUtil.handleCommonBlockingScreen(screenshot_path):
                continue
            time.sleep(sleep_seconds)
        return False

    def click_game_back_button(self, screenshot_path="./img/pvpBackCheck.png", retries=1, sleep_seconds=1):
        return self.click_template(
            "./Icons/backButton.png",
            screenshot_path,
            retries=retries,
            sleep_seconds=sleep_seconds,
            threshold=0.72,
            min_x=0,
            max_x=170,
            min_y=0,
            max_y=100
        )

    def is_main_screen(self):
        screenshot_path = self.capture("./img/pvpMainCheck.png")
        for template_path in (
            "./Icons/MainPageCheck.png",
            "./Icons/loggedInCheckImg.png",
            "./Icons/RewardIcon.png",
            "./Icons/friend.png",
            "./Icons/yuanhang.png",
        ):
            pos = self.find_template(template_path, screenshot_path, threshold=0.72)
            if pos is not None:
                return True
        return False

    def back_to_main_screen(self, max_steps=10):
        for _ in range(max_steps):
            if self.is_main_screen():
                return True
            if self.click_game_back_button("./img/pvpBackCheck.png", retries=1, sleep_seconds=1):
                continue
            self.log("未识别到游戏内返回键，停止回主界面兜底")
            break
        if self.is_main_screen():
            return True
        self.log("未能确认已回到主界面")
        return False

    def open_pvp_screen(self):
        if not self.click_template("./Icons/menu.png", "./img/pvpMenuCheck.png", retries=4, sleep_seconds=1):
            self.log("未找到主界面菜单按钮")
            return False
        if not self.click_template("./Icons/pvp.png", "./img/pvpEntryCheck.png", retries=4, sleep_seconds=2):
            self.log("未找到 PVP 入口")
            return False
        return True

    def select_fight_target(self):
        difficulty = self.settings["difficulty"]
        difficulty_label = self.DIFFICULTY_LABELS.get(difficulty, difficulty)
        target_index = self.DIFFICULTY_INDEX.get(difficulty, 1)
        for _ in range(8):
            screenshot_path = self.capture("./img/pvpFightTargetCheck.png")
            positions = self.find_template(
                "./Icons/pvp_fight.png",
                screenshot_path,
                is_single=False,
                threshold=0.72,
                min_y=360
            )
            print("cv2 result (./Icons/pvp_fight.png): ", positions)
            if positions:
                positions = sorted(positions, key=lambda pos: pos[0])
                selected_pos = positions[min(target_index, len(positions) - 1)]
                self.log(f"PVP 选择难度：{difficulty_label}")
                self.click_pos(selected_pos, 3)
                return True
            if OctoUtil.OctoUtil.handleCommonBlockingScreen(screenshot_path):
                continue
            time.sleep(1)
        self.log("未找到 PVP 挑战按钮")
        return False

    def find_battle_start_button(self, screenshot_path):
        return self.find_template("./Icons/battleStart.png", screenshot_path, threshold=0.72)

    def start_battle(self):
        battle_start_pos = None
        for _ in range(15):
            screenshot_path = self.capture("./img/pvpBattleStartCheck.png")
            battle_start_pos = self.find_battle_start_button(screenshot_path)
            print("cv2 result (./Icons/battleStart.png): ", battle_start_pos)
            if battle_start_pos is not None:
                break
            if OctoUtil.OctoUtil.handleCommonBlockingScreen(screenshot_path):
                continue
            time.sleep(1)
        if battle_start_pos is None:
            self.log("未找到 PVP 开始战斗按钮")
            return False

        self.click_pos(battle_start_pos, 10)
        screenshot_path = self.capture("./img/pvpBattleSwitchCheck.png")
        manual_switch_pos = self.find_template("./Icons/manuelBattleSwitch.png", screenshot_path, threshold=0.72)
        print("cv2 result (./Icons/manuelBattleSwitch.png): ", manual_switch_pos)
        if manual_switch_pos is not None:
            self.click_pos(manual_switch_pos, 1)
        return True

    def dismiss_rank_up(self, wait_seconds=5):
        deadline = time.monotonic() + wait_seconds
        dismissed = False
        while time.monotonic() < deadline:
            screenshot_path = self.capture("./img/pvpRankUpCheck.png")
            rank_up_pos = self.find_template("./Icons/pvp_rank_up.png", screenshot_path, threshold=0.72)
            print("cv2 result (./Icons/pvp_rank_up.png): ", rank_up_pos)
            if rank_up_pos is not None:
                self.log("识别到 PVP 段位提升，点击右下角关闭")
                self.click_pos((1218, 660), 1)
                dismissed = True
                continue
            time.sleep(0.5)
        return dismissed

    def wait_battle_finished(self, timeout_seconds=240):
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            screenshot_path = self.capture("./img/pvpFightEndCheck.png")
            end_pos = self.find_template("./Icons/pvp_fight_end.png", screenshot_path, threshold=0.72)
            print("cv2 result (./Icons/pvp_fight_end.png): ", end_pos)
            if end_pos is not None:
                self.log("PVP 战斗胜利")
                self.click_pos(end_pos, 2)
                self.dismiss_rank_up()
                return True
            if OctoUtil.OctoUtil.handleCommonBlockingScreen(screenshot_path):
                continue
            time.sleep(5)
        self.log("等待 PVP 战斗胜利超时")
        return False

    def run_one_battle(self, battle_index):
        self.log(f"开始 PVP 战斗 {battle_index}/{self.settings['battleCount']}")
        if not self.select_fight_target():
            return False
        if not self.start_battle():
            return False
        return self.wait_battle_finished()

    def collect_mission_rewards(self):
        if not self.click_template("./Icons/pvp_mission.png", "./img/pvpMissionEntryCheck.png", retries=4, sleep_seconds=1):
            self.log("未找到 PVP 任务入口")
            return False
        if not self.click_template(
                "./Icons/pvp_receive_all.png",
                "./img/pvpReceiveAllCheck.png",
                retries=4,
                sleep_seconds=1,
                threshold=0.72
        ):
            self.log("未找到 PVP 一键领取按钮")
        self.back_to_main_screen(max_steps=10)
        return True

    def run(self):
        adb_is_connected = adb().connectDevice(
            adb_path=self.adb_path,
            adb_port=self.adb_port,
            retryCount=20
        )
        if not adb_is_connected:
            self.log("连接模拟器失败，停止 PVP")
            return False

        self.log("开始 PVP")
        self.back_to_main_screen()
        try:
            if not self.open_pvp_screen():
                return False

            for battle_index in range(1, self.settings["battleCount"] + 1):
                if not self.run_one_battle(battle_index):
                    return False
                time.sleep(2)

            return self.collect_mission_rewards()
        finally:
            self.back_to_main_screen()
            self.log("结束 PVP")
