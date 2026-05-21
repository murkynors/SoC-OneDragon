import os
import time

from soc_one_dragon.utils import image_tools as OctoUtil
from soc_one_dragon.workflows.common import adb, log, run_manual_battle_flow


class weeklyTower:
    # 1280x720 固定点位，对应截图里的 9-1 到 9-5 节点中心。
    TOWER_NODE_POSITIONS = [
        ("9-1", (696, 543)),
        ("9-2", (555, 445)),
        ("9-3", (696, 347)),
        ("9-4", (555, 249)),
        ("9-5", (696, 151)),
    ]
    RIGHT_BOTTOM_CONFIRM_POS = (1218, 660)

    def __init__(self, adb_path, adb_port):
        self.adb_path = adb_path
        self.adb_port = adb_port

    def log(self, message):
        log(message)

    def capture(self, path="./img/weeklyTower.png"):
        adb().screen_capture(path)
        return path

    def find_template(
            self,
            template_path,
            screenshot_path="./img/weeklyTower.png",
            threshold=0.8,
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
            threshold=threshold,
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y
        )

    def click_template(
            self,
            template_paths,
            screenshot_path="./img/weeklyTower.png",
            retries=3,
            sleep_seconds=1,
            threshold=0.8,
            min_x=None,
            max_x=None,
            min_y=None,
            max_y=None
    ):
        if isinstance(template_paths, str):
            template_paths = [template_paths]
        template_paths = [path for path in template_paths if os.path.exists(path)]
        if not template_paths:
            return False

        for _ in range(retries):
            self.capture(screenshot_path)
            for template_path in template_paths:
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
                    adb().tap(pos)
                    time.sleep(sleep_seconds)
                    return True
            if OctoUtil.OctoUtil.handleCommonBlockingScreen(screenshot_path):
                continue
            time.sleep(sleep_seconds)
        return False

    def click_game_back_button(self, screenshot_path="./img/weeklyTowerBackCheck.png", retries=1, sleep_seconds=1):
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
        screenshot_path = self.capture("./img/weeklyTowerMainCheck.png")
        for template_path in ("./Icons/MainPageCheck.png", "./Icons/loggedInCheckImg.png"):
            if self.find_template(template_path, screenshot_path, threshold=0.72) is not None:
                return True
        return False

    def is_material_screen(self):
        screenshot_path = self.capture("./img/weeklyTowerMaterialCheck.png")
        return self.find_template("./Icons/materialMissionCheck.png", screenshot_path, threshold=0.72) is not None

    def back_to_main_screen(self, max_steps=10):
        for _ in range(max_steps):
            if self.is_main_screen():
                return True
            if self.click_game_back_button(retries=1, sleep_seconds=1):
                continue
            self.log("未识别到游戏内返回键，停止回主界面兜底")
            break
        if self.is_main_screen():
            return True
        self.log("未能确认已回到主界面")
        return False

    def open_material_screen(self):
        for _ in range(12):
            if self.is_material_screen():
                return True

            screenshot_path = self.capture("./img/weeklyTowerOpenMaterialCheck.png")
            material_pos = self.find_template("./Icons/materialMissionCheck.png", screenshot_path, threshold=0.72)
            if material_pos is not None:
                return True

            one_in_three_pos = self.find_template("./Icons/1in3menu.png", screenshot_path, threshold=0.72)
            print("cv2 result (./Icons/1in3menu.png): ", one_in_three_pos)
            if one_in_three_pos is not None:
                adb().tap((290, 330))
                time.sleep(2)
                continue

            main_pos = self.find_template("./Icons/loggedInCheckImg.png", screenshot_path, threshold=0.72)
            print("cv2 result (./Icons/loggedInCheckImg.png): ", main_pos)
            if main_pos is not None:
                adb().tap(main_pos)
                time.sleep(2)
                continue

            fallback_main_pos = self.find_template("./Icons/MainPageCheck.png", screenshot_path, threshold=0.72)
            print("cv2 result (./Icons/MainPageCheck.png): ", fallback_main_pos)
            if fallback_main_pos is not None:
                adb().tap(fallback_main_pos)
                time.sleep(2)
                continue

            if OctoUtil.OctoUtil.handleCommonBlockingScreen(screenshot_path):
                continue
            time.sleep(1)

        self.log("进入刷图界面超时，停止每周爬塔")
        return False

    def navigate_to_tower(self):
        if not self.open_material_screen():
            return False

        # 刷图界面底部入口横排，从右往左滑出每周爬塔入口。
        adb().swipe((1176, 377), (101, 377), 1000)
        time.sleep(1.5)
        if not self.click_template("./Icons/tower.png", "./img/weeklyTowerEntryCheck.png", retries=4, sleep_seconds=2, threshold=0.72):
            self.log("未找到每周爬塔入口")
            return False

        # 进入塔后右侧中部可能有弹窗/提示，先点一下跳过。
        adb().tap((1060, 360))
        time.sleep(3)
        return True

    def find_tower_start_button(self):
        screenshot_path = self.capture("./img/weeklyTowerStartFightCheck.png")
        return self.find_template("./Icons/TowerStartFight.png", screenshot_path, threshold=0.72)

    def try_start_node_fight(self, node_name, node_pos):
        for attempt in range(1, 3):
            self.log(f"每周爬塔选择 {node_name}，尝试 {attempt}/2")
            adb().tap(node_pos)
            time.sleep(1)
            start_pos = self.find_tower_start_button()
            print("cv2 result (./Icons/TowerStartFight.png): ", start_pos)
            if start_pos is not None:
                adb().tap(start_pos)
                time.sleep(10)
                return True
            time.sleep(1)
        self.log(f"{node_name} 未找到开始战斗按钮，换下一个位置")
        return False

    def run_node(self, node_name, node_pos):
        if not self.try_start_node_fight(node_name, node_pos):
            return False
        if run_manual_battle_flow("weeklyTower"):
            self.log(f"{node_name} 战斗胜利")
            return True
        self.log(f"{node_name} 普通战斗流程失败")
        return False

    def dismiss_harvest_summary(self):
        time.sleep(3)
        screenshot_path = self.capture("./img/weeklyTowerHarvestCheck.png")
        harvest_pos = self.find_template(
            "./Icons/harvest_overview.png",
            screenshot_path,
            threshold=0.56,
            min_x=250,
            max_x=1050,
            min_y=20,
            max_y=190
        )
        print("cv2 result (./Icons/harvest_overview.png): ", harvest_pos)
        if harvest_pos is not None:
            self.log("识别到收获一览，点击右下角关闭")
            adb().tap(self.RIGHT_BOTTOM_CONFIRM_POS)
            time.sleep(1)
            return True
        self.log("未识别到收获一览，跳过关闭")
        return False

    def collect_rewards(self):
        reward_icons = ("./Icons/tower_reward.png", "./Icons/TowerReward.png")
        if self.click_template(reward_icons, "./img/weeklyTowerRewardCheck.png", retries=4, sleep_seconds=1, threshold=0.72):
            self.dismiss_harvest_summary()
            return True
        self.log("未找到每周爬塔领奖按钮")
        return False

    def run(self):
        adb_is_connected = adb().connectDevice(
            adb_path=self.adb_path,
            adb_port=self.adb_port,
            retryCount=20
        )
        if not adb_is_connected:
            self.log("连接模拟器失败，停止爬塔")
            return False

        self.log("开始每周爬塔")
        self.back_to_main_screen()
        if not self.navigate_to_tower():
            return False

        for node_name, node_pos in self.TOWER_NODE_POSITIONS:
            self.run_node(node_name, node_pos)
            time.sleep(2)

        self.collect_rewards()
        self.back_to_main_screen()
        self.log("结束每周爬塔")
        return True


startFight = weeklyTower
getCurrentProgress = weeklyTower
