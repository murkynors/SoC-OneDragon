import time

from PIL import Image

from services import ocr_service as OCRClass
from utils.image_tools import OctoUtil
from workflows.common import SetupAdb, adb, log

LOGIN_SCREENSHOT = "./img/loginCapture.png"
LOGIN_BULLETIN_CLOSE_ICON = "./Icons/loginBulletinClose.png"
LOGIN_START_GAME_ICON = "./Icons/loginStartGame.png"
LOGGED_IN_CHECK_ICON = "./Icons/loggedInCheckImg.png"


def _text_exists_in_screenshot(screenshot_path, target_texts):
    if isinstance(target_texts, str):
        target_texts = [target_texts]
    try:
        scan_res = OCRClass.OCRSingleton.getInstance().scanText(screenshot_path)
    except Exception as exc:
        print("start app blocking OCR failed:", exc)
        return False
    for detected_text, _ in scan_res:
        normalized_detected = OCRClass.OCRSingleton.getInstance()._normalize_text(detected_text)
        for target_text in target_texts:
            normalized_target = OCRClass.OCRSingleton.getInstance()._normalize_text(target_text)
            if normalized_target in normalized_detected:
                return True
    return False


def _to_int_pos(pos):
    return (int(pos[0]), int(pos[1]))


def _is_expected_login_bulletin_close(match_result, screenshot_path, min_score=0.35):
    if match_result is None or match_result["max_score"] < min_score:
        return False

    try:
        with Image.open(screenshot_path) as image:
            width, height = image.size
    except Exception as exc:
        print("read screenshot size failed:", exc)
        width, height = 1280, 720

    x, y = match_result["max_location"]
    return (
        width * 0.25 <= x <= width * 0.85
        and height * 0.08 <= y <= height * 0.70
    )


def dismiss_login_bulletin(screenshot_path):
    match_result = OctoUtil.cv2_match_template_details(
        LOGIN_BULLETIN_CLOSE_ICON,
        screenshot_path,
        threshold=0.75
    )
    if match_result is None:
        return False

    if match_result["matched"]:
        log("识别到登录公告关闭按钮，点击关闭")
        adb().tap(_to_int_pos(match_result["tap_pos"]))
        time.sleep(1)
        return True

    # 登录公告关闭按钮可能随版本轻微变化；仅在弹窗区域且 OCR 确认是公告时使用低分候选。
    if not _is_expected_login_bulletin_close(match_result, screenshot_path):
        return False
    bulletin_texts = (
        "公告", "更新", "通知", "维护",
        "版本", "活动", "亲爱的", "玩家",
        "內容", "内容", "修复", "補償", "补偿",
    )
    if not _text_exists_in_screenshot(screenshot_path, bulletin_texts):
        return False

    log("识别到登录公告界面，点击候选关闭按钮")
    adb().tap(_to_int_pos(match_result["max_tap_pos"]))
    time.sleep(1)
    return True


def find_login_template(icon_path, screenshot_path, threshold=0.75):
    match_result = OctoUtil.cv2_match_template_details(icon_path, screenshot_path, threshold=threshold)
    if match_result is None or not match_result["matched"]:
        return None
    return _to_int_pos(match_result["tap_pos"])


def handle_start_app_blocking_screen(screenshot_path):
    if OctoUtil.handleCommonBlockingScreen(screenshot_path):
        return True

    if _text_exists_in_screenshot(screenshot_path, ("签到", "本日签到", "累计签到", "簽到")):
        log("识别到签到界面，使用预设坐标关闭")
        adb().tap((1180, 50))
        time.sleep(1)
        return True

    return False


class StartApp:
    def __init__(self, adb_path, adb_port):
        self.adb_path = adb_path
        self.adb_port = adb_port

    def run(self):
        res = adb().getAllPackages()
        print("available package", res)

        app_package = adb().resolve_app_package(res)
        if app_package:
            adb().startApp()
            return True

        print("App not found")
        log("未找到游戏应用，停止唤醒")
        return False


class ScreenshotTemplateLogin:
    def __init__(self, screenshot, icon, retry_count, subpattern, current_stage):
        self.screenshot = screenshot
        self.icon = icon
        self.retry_count = retry_count
        self.subpattern = subpattern
        self.current_stage = current_stage

    def run(self):
        isValid = False
        tap_pos = (0, 0)
        cv2_img_screenshot_rect = (0, 0, 0, 0)
        cv2_img_screenshot_result = (0, 0, 0, 0)
        for _ in range(self.retry_count):
            adb().screen_capture(self.screenshot)
            match_result = OctoUtil.cv2_match_template_details(self.icon, self.screenshot, threshold=0.75)
            if match_result is None:
                time.sleep(1)
                continue

            cv2_img_screenshot_result = match_result["locations"]
            if match_result["matched"]:
                isValid = True
                print("There is a result.")
                cv2_img_screenshot_rect = match_result["rect"]
                tap_pos = match_result["tap_pos"]
            else:
                print("There is no result.")
                # 主模板没出现时，用子模板判断当前是否已经跳到了后续登录阶段。
                subPattern = self.subpattern
                if subPattern is not None:
                    for subPattern in subPattern:
                        print("subPattern: ", subPattern)
                        sub_match = OctoUtil.cv2_match_template_details(
                            subPattern["subPattern"],
                            self.screenshot,
                            threshold=0.75
                        )
                        if sub_match is None:
                            continue
                        if sub_match["matched"]:
                            isValid = True
                            print("There is a sub pattern result.")
                            self.current_stage = subPattern["targetStage"]
                            break
                        print("There is no sub pattern.")
                if not isValid and handle_start_app_blocking_screen(self.screenshot):
                    time.sleep(1)
                    continue
            if isValid:
                break
            time.sleep(1)
        if isValid is False:
            log("登录界面识别超时，停止唤醒")
            return None
        return (tap_pos, cv2_img_screenshot_rect, cv2_img_screenshot_result)


class LoginReward:
    def run(self):
        isLoading = True
        while isLoading is True:
            adb().screen_capture('./img/loginReward.png')
            if handle_start_app_blocking_screen('./img/loginReward.png'):
                adb().screen_capture('./img/loginReward.png')
            isSpeedAnimation = OctoUtil.check_pixel_color('./img/loginReward.png', 751, 35,
                                                                   (45, 49, 60, 255))
            if isSpeedAnimation is False:
                isLoading = False
            time.sleep(2)
        time.sleep(10)

        adb().screen_capture('./img/loginRewardDailyCheck.png')
        if handle_start_app_blocking_screen('./img/loginRewardDailyCheck.png'):
            adb().screen_capture('./img/loginRewardDailyCheck.png')
        res = self.cv2CheckImgExist('./Icons/RewardPopUp.png', './img/loginRewardDailyCheck.png')
        print("cv2 result (MATERIAL_MENU): ", res)
        if res:
            adb().tap((640, 630))
            time.sleep(1)
            adb().screen_capture('./img/loginRewardDailyCheck.png')
            res = self.cv2CheckImgExist('./Icons/dailyBulletinClose.png', './img/loginRewardDailyCheck.png')
            if res:
                adb().tap(res)
                time.sleep(1)
        return True

    def cv2CheckImgExist(self, patternPath, screenshotPath):
        pos = OctoUtil.cv2CheckImgExist(patternPath, screenshotPath)
        if pos is None and OctoUtil.handleCommonBlockingScreen(screenshotPath):
            adb().screen_capture(screenshotPath)
            pos = OctoUtil.cv2CheckImgExist(patternPath, screenshotPath)
        return pos


class RunStartApp:
    def __init__(self, adb_path, adb_port):
        self.adb_path = adb_path
        self.adb_port = adb_port
        self.currentStage = 0

    def wait_until_logged_in(self, timeout_seconds=90, interval_seconds=1):
        deadline = time.monotonic() + timeout_seconds
        clicked_start = False

        while time.monotonic() < deadline:
            adb().screen_capture(LOGIN_SCREENSHOT)

            logged_in_pos = find_login_template(LOGGED_IN_CHECK_ICON, LOGIN_SCREENSHOT, threshold=0.75)
            print(f"cv2 result ({LOGGED_IN_CHECK_ICON}): ", logged_in_pos)
            if logged_in_pos is not None:
                self.currentStage = 2
                return True

            if dismiss_login_bulletin(LOGIN_SCREENSHOT):
                continue

            if handle_start_app_blocking_screen(LOGIN_SCREENSHOT):
                continue

            start_pos = find_login_template(LOGIN_START_GAME_ICON, LOGIN_SCREENSHOT, threshold=0.75)
            print(f"cv2 result ({LOGIN_START_GAME_ICON}): ", start_pos)
            if start_pos is not None:
                log("识别到进入游戏按钮，点击进入")
                adb().tap(start_pos)
                clicked_start = True
                self.currentStage = 1
                time.sleep(3)
                return True

            time.sleep(interval_seconds)

        if clicked_start:
            log("进入游戏后等待主页超时，停止唤醒")
        else:
            log("登录界面识别超时，停止唤醒")
        return False

    def run(self):
        log("开始唤醒")

        adb_is_connected = adb().connectDevice(
            adb_path=self.adb_path,
            adb_port=self.adb_port,
            retryCount=20
        )
        if not adb_is_connected:
            return False
        SetupAdb(self.adb_path, self.adb_port, retry_count=5).run()
        StartAppFlow = StartApp(adb_path=self.adb_path, adb_port=self.adb_port)
        if not StartAppFlow.run():
            return False

        time.sleep(5)
        if not self.wait_until_logged_in():
            return False

        if self.currentStage < 2:
            time.sleep(10)
            loginRewardFlow = LoginReward()
            loginRewardFlow.run()
        log("唤醒完毕")
        return True


screenshot_cv2_match_template_login = ScreenshotTemplateLogin
loginReward = LoginReward
runStartApp = RunStartApp
