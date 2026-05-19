import os
import re
import time
from difflib import SequenceMatcher

from PIL import Image, ImageStat

from soc_one_dragon.services import ocr_service as OCRClass
from soc_one_dragon.utils import image_tools as OctoUtil
from soc_one_dragon.workflows.common import SetupAdb, adb, log


class receiveReward:
    DEFAULT_REWARD_OPTIONS = {
        'daily': True,
        'exploration': False,
        'friend': False,
        'voyage': False,
    }

    VOYAGE_REGIONS = [
        ("浪涌城-骑士之歌", ['./Icons/voyage_region_surge_knight.png'], (168, 286), (40, 220, 330, 380), 0.58),
        ("浪涌城-绯红之夜", ['./Icons/voyage_region_surge_crimson.png'], (635, 335), (450, 240, 780, 430), 0.42),
        ("晨曦堡-王国之帜", ['./Icons/voyage_region_dawn_flag.png', './Icons/voyage_region_dawn_flag_alt.png'], (220, 525), (50, 420, 380, 640), 0.32),
        ("暮光城-光辉审判", ['./Icons/voyage_region_twilight_judgement.png'], (495, 610), (250, 430, 650, 700), 0.45),
        ("铃兰小镇-天平之上", ['./Icons/voyage_region_bell_balance.png'], (675, 465), (450, 300, 780, 560), 0.65),
    ]
    VOYAGE_DISPATCHES_PER_REGION = 2

    def __init__(self, adb_path, adb_port, reward_options=None):
        self.adb_path = adb_path
        self.adb_port = adb_port
        self.reward_options = self.resolve_reward_options(reward_options)
        self.voyage_remaining_dispatches = None

    def run(self):
        adb_is_connected = adb().connectDevice(
            adb_path=self.adb_path,
            adb_port=self.adb_port,
            retryCount=20
        )
        if not adb_is_connected:
            log("连接模拟器失败，停止收奖励")
            return False
        SetupAdb(self.adb_path, self.adb_port, retry_count=5).run()
        log("开始收奖励")

        reward_steps = [
            ('daily', '每日奖励', self.collect_daily_reward),
            ('exploration', '探索奖励', self.collect_exploration_reward),
            ('friend', '好友奖励', self.collect_friend_reward),
            ('voyage', '远航奖励', self.collect_voyage_reward),
        ]
        if not any(self.reward_options.values()):
            self.log("未选择任何奖励子项，跳过收奖励")
            return True

        for option_key, reward_name, reward_func in reward_steps:
            if not self.reward_options.get(option_key, False):
                continue
            self.log(f"开始领取{reward_name}")
            try:
                self.back_to_main_screen()
                reward_func()
                self.back_to_main_screen()
                self.log(f"结束领取{reward_name}")
            except RuntimeError as exc:
                if str(exc) == "流程已停止":
                    raise
                self.log(f"{reward_name}流程异常：{exc}")
            except Exception as exc:
                self.log(f"{reward_name}流程异常：{exc}")

        log("结束收奖励")
        return True

    def resolve_reward_options(self, reward_options):
        resolved_options = dict(self.DEFAULT_REWARD_OPTIONS)
        if isinstance(reward_options, dict):
            for key in self.DEFAULT_REWARD_OPTIONS:
                if key in reward_options:
                    resolved_options[key] = bool(reward_options[key])
        return resolved_options

    def log(self, message):
        log(message)

    def capture(self, path='./img/rewardFlow.png', handle_blocking_screens=False):
        adb().screen_capture(path)
        if handle_blocking_screens and self.handle_blocking_screens(path):
            adb().screen_capture(path)
        return path

    def click_pos(self, pos, sleep_seconds=1):
        adb().tap(pos)
        time.sleep(sleep_seconds)

    def swipe_pos(self, pos_start, pos_end, duration=800, sleep_seconds=1):
        adb().swipe(pos_start, pos_end, duration)
        time.sleep(sleep_seconds)

    def handle_blocking_screens(self, screenshot_path):
        return OctoUtil.OctoUtil.handleCommonBlockingScreen(screenshot_path)

    def click_template(
            self,
            template_paths,
            screenshot_path='./img/rewardFlow.png',
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
                pos = OctoUtil.OctoUtil.cv2CheckImgExist(
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
            if self.handle_blocking_screens(screenshot_path):
                continue
            time.sleep(sleep_seconds)
        return False

    def normalized_text(self, text):
        return OCRClass.OCRSingleton.getInstance()._normalize_text(str(text))

    def text_matches(self, detected_text, target_text):
        normalized_detected = self.normalized_text(detected_text)
        normalized_target = self.normalized_text(target_text)
        if not normalized_detected or not normalized_target:
            return False
        if normalized_target in normalized_detected:
            return True
        if len(normalized_detected) >= 3 and normalized_detected in normalized_target:
            return True
        similarity_threshold = 0.82 if len(normalized_target) >= 4 else 0.85
        return SequenceMatcher(None, normalized_detected, normalized_target).ratio() >= similarity_threshold

    def crop_ocr_region(self, screenshot_path, min_x=None, max_x=None, min_y=None, max_y=None, padding=8):
        if not any(value is not None for value in (min_x, max_x, min_y, max_y)):
            return screenshot_path, (0, 0)

        try:
            image = Image.open(screenshot_path)
        except Exception as exc:
            print("ocr crop failed:", exc)
            return screenshot_path, (0, 0)

        width, height = image.size
        left = int(min_x) if min_x is not None else 0
        right = int(max_x) if max_x is not None else width
        top = int(min_y) if min_y is not None else 0
        bottom = int(max_y) if max_y is not None else height
        left = max(0, left - padding)
        top = max(0, top - padding)
        right = min(width, right + padding)
        bottom = min(height, bottom + padding)
        if right <= left or bottom <= top:
            return screenshot_path, (0, 0)

        base, ext = os.path.splitext(screenshot_path)
        cropped_path = f"{base}OcrCrop{ext or '.png'}"
        os.makedirs(os.path.dirname(cropped_path) or ".", exist_ok=True)
        image.crop((left, top, right, bottom)).save(cropped_path)
        return cropped_path, (left, top)

    def scan_text_positions(self, target_texts, screenshot_path='./img/rewardFlow.png', min_x=None, max_x=None, min_y=None, max_y=None):
        if isinstance(target_texts, str):
            target_texts = [target_texts]
        self.capture(screenshot_path)
        scan_path, offset = self.crop_ocr_region(screenshot_path, min_x, max_x, min_y, max_y)
        scan_res = OCRClass.OCRSingleton.getInstance().scanText(scan_path, enhanced=scan_path != screenshot_path)
        matched_positions = []
        for detected_text, center in scan_res:
            center = (center[0] + offset[0], center[1] + offset[1])
            if min_x is not None and center[0] < min_x:
                continue
            if max_x is not None and center[0] > max_x:
                continue
            if min_y is not None and center[1] < min_y:
                continue
            if max_y is not None and center[1] > max_y:
                continue
            if any(self.text_matches(detected_text, target_text) for target_text in target_texts):
                matched_positions.append((detected_text, center))
        print("ocr matches: ", target_texts, matched_positions)
        return matched_positions

    def click_text(self, target_texts, screenshot_path='./img/rewardFlow.png', retries=3, sleep_seconds=1, min_x=None, max_x=None, min_y=None, max_y=None):
        for _ in range(retries):
            positions = self.scan_text_positions(target_texts, screenshot_path, min_x, max_x, min_y, max_y)
            if positions:
                self.click_pos(positions[0][1], sleep_seconds)
                return True
            time.sleep(sleep_seconds)
        return False

    def click_game_back_button(self, screenshot_path='./img/rewardBackCheck.png', retries=1, sleep_seconds=1):
        return self.click_template(
            './Icons/backButton.png',
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
        screenshot_path = self.capture('./img/rewardMainCheck.png')
        for template_path in (
            './Icons/MainPageCheck.png',
            './Icons/loggedInCheckImg.png',
            './Icons/RewardIcon.png',
            './Icons/friend.png',
            './Icons/yuanhang.png',
        ):
            if not os.path.exists(template_path):
                continue
            if OctoUtil.OctoUtil.cv2CheckImgExist(template_path, screenshot_path) is not None:
                return True
        try:
            scan_res = OCRClass.OCRSingleton.getInstance().scanText(screenshot_path)
        except Exception as exc:
            print("main screen OCR failed:", exc)
            scan_res = []
        detected_texts = [detected_text for detected_text, _ in scan_res]
        has_voyage = any(
            self.text_matches(text, "远航") or self.text_matches(text, "遠航") or self.text_matches(text, "出航")
            for text in detected_texts
        )
        bottom_menu_matches = sum(
            1 for target_text in ("角色", "仓库", "邂逅", "商店", "心之羁绊", "天赋")
            if any(self.text_matches(text, target_text) for text in detected_texts)
        )
        if has_voyage and bottom_menu_matches >= 2:
            return True
        return False

    def back_to_main_screen(self, max_steps=10):
        for _ in range(max_steps):
            if self.is_main_screen():
                return True
            if self.click_game_back_button('./img/rewardBackCheck.png', retries=1, sleep_seconds=1):
                continue
            self.log("未识别到游戏内返回键，停止回主界面兜底，避免误点左上角头像")
            break
        if self.is_main_screen():
            return True
        self.log("未能确认已回到主界面")
        return False

    def collect_daily_reward(self):
        if not self.click_template('./Icons/RewardIcon.png', './img/rewardIconCheck.png', retries=3, sleep_seconds=2):
            self.log("未找到每日奖励入口")
            return False
        if not self.click_template('./Icons/RewardTake.png', './img/rewardTakeCheck.png', retries=4, sleep_seconds=2):
            if not self.click_text(("领取", "領取"), './img/rewardTakeCheck.png', retries=3, sleep_seconds=2):
                self.log("未找到每日奖励领取按钮")
                return False
        self.click_pos((645, 555), 1)
        self.click_game_back_button('./img/rewardIconCheck.png', retries=2, sleep_seconds=1)
        return True

    def click_exploration_entry(self, max_seconds=10):
        deadline = time.monotonic() + max_seconds
        template_paths = [
            path for path in ('./Icons/explorationReward.png', './Icons/explorationReward2.png')
            if os.path.exists(path)
        ]
        while time.monotonic() < deadline:
            screenshot_path = self.capture('./img/explorationRewardCheck.png')
            for template_path in template_paths:
                pos = OctoUtil.OctoUtil.cv2CheckImgExist(template_path, screenshot_path)
                print(f"cv2 result ({template_path}): ", pos)
                if pos is not None:
                    self.click_pos(pos, 2)
                    return True

            positions = self.scan_text_positions(("探索奖励", "探索獎勵"), './img/explorationRewardCheck.png')
            if positions:
                self.click_pos(positions[0][1], 2)
                return True
            time.sleep(0.5)
        return False

    def collect_exploration_reward(self):
        if not self.click_exploration_entry(max_seconds=10):
            self.log("10秒内未找到探索奖励入口，跳过探索奖励")
            return False

        self.click_pos((190, 475), 2)
        if not self.click_text(("领取", "領取"), './img/explorationTakeCheck.png', retries=4, sleep_seconds=1):
            self.log("未找到探索奖励领取按钮，继续尝试返回")

        self.click_game_back_button('./img/explorationBackCheck.png', retries=1, sleep_seconds=1)
        self.click_game_back_button('./img/explorationBackCheck.png', retries=1, sleep_seconds=1)
        for _ in range(6):
            if self.is_main_screen():
                return True
            if not self.click_game_back_button('./img/explorationBackCheck.png', retries=1, sleep_seconds=1):
                break
        return self.is_main_screen()

    def collect_friend_reward(self):
        if not self.click_template('./Icons/friend.png', './img/friendRewardCheck.png', retries=3, sleep_seconds=2):
            self.log("未找到好友入口")
            return False
        self.click_text(("全部领取", "全部領取"), './img/friendTakeCheck.png', retries=4, sleep_seconds=1)
        gift_button_bounds = {
            "min_x": 900,
            "max_x": 1230,
            "min_y": 25,
            "max_y": 95,
        }
        if not self.click_template(
            './Icons/friendGiftSend.png',
            './img/friendGiftCheck.png',
            retries=2,
            sleep_seconds=1,
            threshold=0.72,
            **gift_button_bounds
        ) and not self.click_text(
            ("一键赠送", "一鍵贈送"),
            './img/friendGiftCheck.png',
            retries=2,
            sleep_seconds=1,
            **gift_button_bounds
        ):
            self.log("未识别到好友一键赠送按钮，使用预设坐标")
            self.click_pos((1073, 60), 1)
        self.click_game_back_button('./img/friendBackCheck.png', retries=3, sleep_seconds=1)
        return True

    def collect_voyage_reward(self):
        if not self.click_template('./Icons/yuanhang.png', './img/voyageEntryCheck.png', retries=3, sleep_seconds=2):
            if not self.click_text(("远航", "遠航"), './img/voyageEntryCheck.png', retries=3, sleep_seconds=2):
                self.log("未找到远航入口")
                return False

        if not self.click_template(
            './Icons/voyage_harvest_all.png',
            './img/voyageHarvestCheck.png',
            retries=2,
            sleep_seconds=1,
            threshold=0.72,
            min_x=760,
            max_x=1040,
            min_y=610,
            max_y=700
        ) and not self.click_text(
            ("全部收获", "全部收穫", "全部收货"),
            './img/voyageHarvestCheck.png',
            retries=2,
            sleep_seconds=1,
            min_x=760,
            max_x=1040,
            min_y=610,
            max_y=700
        ):
            self.log("未识别到右下角全部收获按钮，使用预设坐标")
            self.click_pos((910, 665), 1)
        self.dismiss_harvest_summary()

        voyage_exhausted = False
        self.voyage_remaining_dispatches = None
        for region_name, template_paths, fallback_pos, search_bounds, threshold in self.VOYAGE_REGIONS:
            if self.dispatch_voyage_region(region_name, template_paths, fallback_pos, search_bounds, threshold) == "exhausted":
                voyage_exhausted = True
                break
        if voyage_exhausted:
            self.log("远航今日剩余次数已用尽，进入兑换")

        if self.open_voyage_exchange():
            self.exchange_bottom_items()
        else:
            self.log("未能进入远航兑换界面，跳过兑换")
        self.click_game_back_button('./img/voyageExchangeBackCheck.png', retries=1, sleep_seconds=1)
        self.click_game_back_button('./img/voyageBackCheck.png', retries=2, sleep_seconds=1)
        return True

    def voyage_region_ocr_target(self, region_name):
        if "-" in region_name:
            return region_name.split("-", 1)[1]
        if "－" in region_name:
            return region_name.split("－", 1)[1]
        return region_name[-4:]

    def dismiss_harvest_summary(self, initial_sleep=1.5, wait_seconds=4):
        # 收获一览是可选弹窗，只在确实识别到时才关闭。
        time.sleep(initial_sleep)
        deadline = time.monotonic() + wait_seconds
        while True:
            screenshot_path = self.capture('./img/voyageHarvestSummaryCheck.png')
            if self.is_voyage_harvest_summary_screen(screenshot_path):
                self.log("识别到远航收获一览，点击右下角关闭")
                for _ in range(3):
                    self.click_pos((1218, 660), 1)
                    screenshot_path = self.capture('./img/voyageHarvestSummaryCheck.png')
                    if not self.is_voyage_harvest_summary_screen(screenshot_path):
                        return True
                    self.log("远航收获一览仍未关闭，再次点击右下角关闭")
                return False

            if time.monotonic() >= deadline:
                return False
            time.sleep(0.5)

    def is_voyage_harvest_summary_screen(self, screenshot_path):
        if OctoUtil.OctoUtil.cv2CheckImgExist(
            './Icons/harvest_overview.png',
            screenshot_path,
            threshold=0.56,
            min_x=250,
            max_x=1050,
            min_y=20,
            max_y=190
        ) is not None:
            return True
        if OctoUtil.OctoUtil.screenshot_has_text(
            screenshot_path,
            ("收获一览", "收穫一覽", "收货一览", "投影", "星星的指引", "荣耀之力", "远志之力")
        ):
            return True
        return self.has_voyage_harvest_summary_panel(screenshot_path)

    def has_voyage_harvest_summary_panel(self, screenshot_path):
        try:
            image = Image.open(screenshot_path).convert("RGB")
            panel = image.crop((0, 160, 1280, 560))
            pixels = list(panel.getdata())
            if not pixels:
                return False
            blue_panel_ratio = sum(
                1 for red, green, blue in pixels
                if 45 <= red <= 115 and 65 <= green <= 135 and 90 <= blue <= 175
            ) / len(pixels)
            print("voyage harvest summary panel ratio:", blue_panel_ratio)
            return blue_panel_ratio > 0.45
        except Exception as exc:
            print("voyage harvest summary panel check failed:", exc)
            return False

    def is_voyage_region_detail_screen(self, screenshot_path):
        try:
            image = Image.open(screenshot_path).convert("L")
            # 右侧地区详情面板比地图亮，用亮度快速判断是否已进详情页。
            brightness = ImageStat.Stat(image.crop((650, 120, 1070, 610))).mean[0]
            print("voyage detail brightness:", brightness)
            return brightness > 75
        except Exception as exc:
            print("voyage detail screen check failed:", exc)
            return False

    def is_voyage_main_screen(self, screenshot_path):
        if OctoUtil.OctoUtil.cv2CheckImgExist(
            './Icons/yuanhang_exchange.png',
            screenshot_path,
            threshold=0.65,
            min_x=120,
            max_x=260,
            min_y=590,
            max_y=710
        ) is not None:
            return True
        if OctoUtil.OctoUtil.cv2CheckImgExist(
            './Icons/voyage_harvest_all.png',
            screenshot_path,
            threshold=0.72,
            min_x=760,
            max_x=1040,
            min_y=610,
            max_y=700
        ) is not None:
            return True
        try:
            scan_res = OCRClass.OCRSingleton.getInstance().scanText(screenshot_path)
        except Exception as exc:
            print("voyage main screen OCR failed:", exc)
            scan_res = []
        detected_texts = [detected_text for detected_text, _ in scan_res]
        has_exchange = any(self.text_matches(text, "兑换") or self.text_matches(text, "兌換") for text in detected_texts)
        has_dispatch = any(self.text_matches(text, "派遣") for text in detected_texts)
        has_harvest = any(self.text_matches(text, "全部收获") or self.text_matches(text, "全部收穫") for text in detected_texts)
        return has_exchange and (has_dispatch or has_harvest)

    def ensure_voyage_main_screen_for_exchange(self):
        screenshot_path = self.capture('./img/voyageMainReturnCheck.png')
        if self.is_voyage_main_screen(screenshot_path):
            return True
        if self.is_main_screen():
            self.log("当前已回到游戏主界面，重新进入远航")
            return self.click_template('./Icons/yuanhang.png', './img/voyageEntryCheck.png', retries=3, sleep_seconds=2) or self.click_text(
                ("远航", "遠航"),
                './img/voyageEntryCheck.png',
                retries=3,
                sleep_seconds=2
            )
        if self.is_voyage_region_detail_screen(screenshot_path):
            self.log("当前仍在远航详情页，点击右下角关闭后进入兑换")
            self.click_pos((1188, 665), 1)
        else:
            self.log("当前不在远航主界面，尝试点击游戏内返回键")
            self.click_game_back_button('./img/voyageMainReturnBackCheck.png', retries=1, sleep_seconds=1)
        screenshot_path = self.capture('./img/voyageMainReturnCheck.png')
        return self.is_voyage_main_screen(screenshot_path)

    def open_voyage_exchange(self):
        if not self.ensure_voyage_main_screen_for_exchange():
            self.log("未能确认远航主界面，跳过远航兑换")
            return False

        if self.click_template(
            './Icons/yuanhang_exchange.png',
            './img/voyageExchangeEntryCheck.png',
            retries=2,
            sleep_seconds=1,
            min_x=120,
            max_x=260,
            min_y=600,
            max_y=710
        ):
            return True
        if self.click_text(("兑换", "兌換"), './img/voyageExchangeEntryCheck.png', retries=2, sleep_seconds=1, min_x=100, max_x=280, min_y=590):
            return True
        if self.confirm_voyage_exchange_screen('./img/voyageExchangeEntryCheck.png', log_failure=False):
            return True
        self.log("未找到远航兑换入口，尝试预设坐标")
        self.click_pos((185, 665), 1)
        return self.confirm_voyage_exchange_screen('./img/voyageExchangeEntryCheck.png')

    def confirm_voyage_exchange_screen(self, screenshot_path='./img/voyageExchangeConfirmCheck.png', retries=3, sleep_seconds=0.5, log_failure=True):
        for _ in range(retries):
            screenshot_path = self.capture(screenshot_path)
            if self.is_voyage_exchange_screen(screenshot_path):
                return True
            if self.handle_blocking_screens(screenshot_path):
                time.sleep(sleep_seconds)
                continue
            time.sleep(sleep_seconds)
        if log_failure:
            self.log("多次确认后仍不在远航兑换界面")
        return False

    def is_voyage_exchange_screen(self, screenshot_path):
        try:
            scan_res = OCRClass.OCRSingleton.getInstance().scanText(screenshot_path)
        except Exception as exc:
            print("voyage exchange screen OCR failed:", exc)
            return False
        detected_texts = [detected_text for detected_text, _ in scan_res]
        has_exchange_title = any(self.text_matches(text, "兑换") or self.text_matches(text, "兌換") for text in detected_texts)
        has_shop_tab = any(self.text_matches(text, "商店") or self.text_matches(text, "交易行") for text in detected_texts)
        return has_exchange_title and has_shop_tab

    def open_voyage_region_detail(self, region_name, template_paths, fallback_pos, search_bounds, threshold, retries=2):
        for _ in range(retries):
            self.dismiss_harvest_summary(initial_sleep=0, wait_seconds=0)
            min_x, min_y, max_x, max_y = search_bounds
            clicked = self.click_template(
                template_paths,
                './img/voyageRegionTemplateCheck.png',
                retries=1,
                sleep_seconds=1,
                threshold=threshold,
                min_x=min_x,
                max_x=max_x,
                min_y=min_y,
                max_y=max_y
            )
            if not clicked:
                self.log(f"远航地区 {region_name} 未匹配到地区模板，使用预设坐标")
                self.click_pos(fallback_pos, 1)
            screenshot_path = self.capture('./img/voyageRegionDetailCheck.png')
            if self.is_voyage_region_detail_screen(screenshot_path):
                return True
            self.log(f"远航地区 {region_name} 未进入详情页，重试选择地区")
        return False

    def click_voyage_local_dispatch(self, screenshot_path='./img/voyageDispatchLocalCheck.png'):
        if self.click_template(
            './Icons/voyage_dispatch_local.png',
            screenshot_path,
            retries=2,
            sleep_seconds=1,
            threshold=0.72,
            min_x=580,
            max_x=1100,
            min_y=480,
            max_y=620
        ):
            return True
        self.capture(screenshot_path)
        if self.is_voyage_region_detail_screen(screenshot_path):
            self.log("已进入远航地区详情页但未匹配到派遣到本地模板，使用预设坐标")
            self.click_pos((835, 552), 1)
            return True
        if self.click_text(("派遣到本地", "派遣至本地"), screenshot_path, retries=1, sleep_seconds=1):
            return True
        return False

    def parse_voyage_remaining_count(self, detected_texts):
        for detected_text in detected_texts:
            normalized = self.normalized_text(detected_text)
            normalized = normalized.replace("O", "0").replace("o", "0").replace("／", "/")
            match = re.search(r"(\d+)\s*/\s*(\d+)", normalized)
            if match:
                return int(match.group(1))
            match = re.search(r"剩余次数(\d+)", normalized)
            if match:
                return int(match.group(1))
        return None

    def get_voyage_remaining_count(self, screenshot_path):
        scan_path, _ = self.crop_ocr_region(
            screenshot_path,
            min_x=850,
            max_x=1065,
            min_y=520,
            max_y=575,
            padding=4
        )
        scan_res = OCRClass.OCRSingleton.getInstance().scanText(scan_path)
        detected_texts = [detected_text for detected_text, _ in scan_res]
        remaining_count = self.parse_voyage_remaining_count(detected_texts)
        if remaining_count is None:
            scan_res = OCRClass.OCRSingleton.getInstance().scanText(scan_path, enhanced=True)
            detected_texts = [detected_text for detected_text, _ in scan_res]
            remaining_count = self.parse_voyage_remaining_count(detected_texts)
        print("voyage remaining OCR: ", detected_texts, remaining_count)
        return remaining_count

    def ensure_voyage_remaining_dispatches(self, screenshot_path='./img/voyageRemainingCheck.png'):
        if self.voyage_remaining_dispatches is not None:
            return self.voyage_remaining_dispatches
        self.capture(screenshot_path)
        remaining_count = self.get_voyage_remaining_count(screenshot_path)
        if remaining_count is None:
            remaining_count = len(self.VOYAGE_REGIONS) * self.VOYAGE_DISPATCHES_PER_REGION
            self.log(f"未能读取远航今日剩余次数，本次按最多 {remaining_count} 次尝试派遣")
        else:
            self.log(f"远航今日剩余次数：{remaining_count}")
        self.voyage_remaining_dispatches = remaining_count
        return self.voyage_remaining_dispatches

    def finish_voyage_dispatch_phase(self):
        screenshot_path = self.capture('./img/voyageFinishDispatchCheck.png')
        if self.is_voyage_main_screen(screenshot_path):
            return True
        if self.is_voyage_region_detail_screen(screenshot_path):
            self.click_pos((1188, 665), 1)
            return True
        return False

    def dispatch_voyage_once(self, region_name):
        if not self.click_template(
            './Icons/voyage_select_team.png',
            './img/voyageSelectTeamCheck.png',
            retries=3,
            sleep_seconds=1,
            threshold=0.72,
            min_x=850,
            max_x=1160,
            min_y=240,
            max_y=340
        ) and not self.click_text(("选择编队", "選擇編隊"), './img/voyageSelectTeamCheck.png', retries=2, sleep_seconds=1):
            self.log(f"远航地区 {region_name} 未找到按钮：选择编队，使用预设坐标")
            self.click_pos((1010, 290), 1)
        if not self.click_template(
            './Icons/voyage_use_team.png',
            './img/voyageUseTeamCheck.png',
            retries=3,
            sleep_seconds=1,
            threshold=0.72,
            min_x=900,
            max_x=1160,
            min_y=250,
            max_y=650
        ) and not self.click_text(("使用",), './img/voyageUseTeamCheck.png', retries=2, sleep_seconds=1, min_x=900, max_x=1160):
            self.log(f"远航地区 {region_name} 未找到按钮：使用，使用预设坐标")
            self.click_pos((1035, 355), 1)
        if not self.click_template(
            './Icons/voyage_dispatch.png',
            './img/voyageDispatchCheck.png',
            retries=3,
            sleep_seconds=1,
            threshold=0.68,
            min_x=760,
            max_x=1120,
            min_y=540,
            max_y=650
        ) and not self.click_text(("派遣",), './img/voyageDispatchCheck.png', retries=2, sleep_seconds=1, min_x=760, min_y=560):
            self.log(f"远航地区 {region_name} 未找到按钮：派遣，先尝试右下角预设位置")
            self.click_pos((995, 660), 1)
            if not self.click_template(
                './Icons/voyage_dispatch.png',
                './img/voyageDispatchCheck.png',
                retries=2,
                sleep_seconds=1,
                threshold=0.68,
                min_x=760,
                max_x=1120,
                min_y=540,
                max_y=650
            ) and not self.click_text(("派遣",), './img/voyageDispatchCheck.png', retries=1, sleep_seconds=1, min_x=760, min_y=560):
                self.log(f"远航地区 {region_name} 仍未识别到派遣按钮，使用预设坐标")
                self.click_pos((945, 590), 1)
        return True

    def dispatch_voyage_region(self, region_name, template_paths, fallback_pos, search_bounds, threshold):
        ready_for_dispatch = False
        if self.voyage_remaining_dispatches is None:
            if not self.open_voyage_region_detail(region_name, template_paths, fallback_pos, search_bounds, threshold):
                self.log(f"远航地区 {region_name} 未进入地区详情，跳过该地区")
                return False
            if not self.click_voyage_local_dispatch():
                self.log(f"远航地区 {region_name} 未找到派遣到本地，跳过该地区")
                return False
            ready_for_dispatch = True

        remaining_count = self.ensure_voyage_remaining_dispatches()
        if remaining_count <= 0:
            self.log(f"远航地区 {region_name} 今日剩余次数已用尽，结束派遣")
            self.finish_voyage_dispatch_phase()
            return "exhausted"

        dispatch_count = min(self.VOYAGE_DISPATCHES_PER_REGION, remaining_count)
        for _ in range(dispatch_count):
            if not ready_for_dispatch:
                if not self.open_voyage_region_detail(region_name, template_paths, fallback_pos, search_bounds, threshold):
                    self.log(f"远航地区 {region_name} 未进入地区详情，跳过剩余派遣")
                    return False
                if not self.click_voyage_local_dispatch():
                    self.log(f"远航地区 {region_name} 未找到派遣到本地，跳过剩余派遣")
                    return False
                ready_for_dispatch = True

            result = self.dispatch_voyage_once(region_name)
            if result == "exhausted":
                return result
            self.voyage_remaining_dispatches -= 1
            ready_for_dispatch = False
            if self.voyage_remaining_dispatches <= 0:
                self.log(f"远航地区 {region_name} 今日剩余次数已用尽，结束派遣")
                self.finish_voyage_dispatch_phase()
                return "exhausted"
        return True

    def scroll_voyage_exchange_to_bottom(self):
        for _ in range(3):
            self.swipe_pos((1125, 650), (1125, 145), duration=900, sleep_seconds=0.8)

    def exchange_bottom_items(self):
        self.scroll_voyage_exchange_to_bottom()
        screenshot_path = self.capture('./img/voyageExchangeBottomCheck.png')
        exchange_positions = OctoUtil.OctoUtil.cv2CheckImgExist(
            './Icons/voyage_exchange_bottom.png',
            screenshot_path,
            isSingle=False,
            threshold=0.72,
            min_x=500,
            max_x=1210,
            min_y=80,
            max_y=690
        )
        print("cv2 result (./Icons/voyage_exchange_bottom.png): ", exchange_positions)
        if not exchange_positions:
            if not self.confirm_voyage_exchange_screen('./img/voyageExchangeBottomMissingCheck.png'):
                self.log("当前不在远航兑换界面，跳过底部兑换")
                return False
            self.log("未找到远航底部兑换按钮")
            return False
        exchange_positions = sorted(exchange_positions, key=lambda pos: (pos[1], pos[0]))
        for pos in exchange_positions:
            self.click_pos(pos, 0.8)
            self.dismiss_harvest_summary(initial_sleep=0.8)
        return True
