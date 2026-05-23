import math
import os
import re
import time

import cv2
import numpy as np
import yaml
from PIL import Image

from device import adb_controller as ADBClass
from services import ocr_service as OCRClass


class OctoUtil:
    @staticmethod
    def detectImgOCR(m_ocr, img_path):
        result = m_ocr.ocr(img_path, cls=True)
        print("res: ", result[0])
        return result

    @staticmethod
    def check_hv_certain_word(m_ocr, target,profile):
        profile.screen_capture("./img/screenshot.png")
        resultArr = OctoUtil.detectImgOCR(m_ocr, "./img/screenshot.png")
        passedData = []
        for line in resultArr[0]:
            if (OctoUtil.check_percent(line[1][0], target, 0.7)[0] is True):
                passedData.append((line[1][0], (OctoUtil.check_percent(line[1][0], target, 0.7)[1]), line[0]))
                print("text: ", line[1][0], " confidence: ", line[1][1], " rect: ", line[0], "checkRes: ",
                    OctoUtil.check_percent(line[1][0], target, 0.7))
        if len(passedData) > 0:
            max_item = max(passedData, key=lambda x: x[1])
            print("MaxItem: ", max_item, np.mean(np.array(max_item[2]), axis=0))
            return [len(passedData) > 0, np.mean(np.array(max_item[2]), axis=0)]
        else:
            return [len(passedData) > 0, ()]

    @staticmethod
    def print_param(params):
        print(params)

    @staticmethod
    def check_percent(main_text, verification_text, percent_overlap_text_appearance_in_verification_text):
        words_main_text = OctoUtil.split_str(main_text)
        words_verification_text = OctoUtil.split_str(verification_text)
        count = 0
        for word in words_main_text:
            if word in words_verification_text:
                count += 1
        overlap_text_appearance_in_verification_text = count / len(words_verification_text) * 100
        verification_text_perc_in_main_text = len(words_verification_text) / len(words_main_text) * 100
        return overlap_text_appearance_in_verification_text >= percent_overlap_text_appearance_in_verification_text, verification_text_perc_in_main_text

    @staticmethod
    def check_pixel_color(image_path, coordinate_x, coordinate_y, color):
        image = Image.open(image_path)
        pixel_color = image.getpixel((coordinate_x, coordinate_y))
        print("Color(RGB): ", pixel_color)
        return pixel_color == color

    @staticmethod
    def pad_number_with_zeros(string, number):
        return f"{string}_{int(number):02d}"

    @staticmethod
    def split_str(text):
        chars = []
        for c in text:
            chars.append(c)
        return chars

    @staticmethod
    def normalized_text_contains(main_text, target_text):
        ocr_instance = OCRClass.OCRSingleton.getInstance()
        return ocr_instance._normalize_text(target_text) in ocr_instance._normalize_text(main_text)

    @staticmethod
    def screenshot_has_text(screenshot_path, target_texts):
        if isinstance(target_texts, str):
            target_texts = [target_texts]
        try:
            scan_res = OCRClass.OCRSingleton.getInstance().scanText(screenshot_path)
        except Exception as exc:
            print("blocking screen OCR failed:", exc)
            return False
        for detected_text, _ in scan_res:
            if any(OctoUtil.normalized_text_contains(detected_text, target_text) for target_text in target_texts):
                return True
        return False

    @staticmethod
    def cv2CheckImgOnScreenshot(pattern_path, screenshot_path, threshold=0.75):
        if not os.path.exists(pattern_path):
            return None
        screenshot = cv2.imread(screenshot_path, 0)
        pattern = cv2.imread(pattern_path, 0)
        if screenshot is None or pattern is None:
            return None
        result = cv2.matchTemplate(screenshot, pattern, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        if len(locations[0]) == 0:
            return None
        x, y = locations[::-1]
        w, h = pattern.shape[::-1]
        return (x[0] + w / 2, y[0] + h / 2)

    @staticmethod
    def cv2_match_template_details(pattern_path, screenshot_path, threshold=0.75):
        screenshot = cv2.imread(screenshot_path, 0)
        pattern = cv2.imread(pattern_path, 0)
        if screenshot is None or pattern is None:
            return None

        result = cv2.matchTemplate(screenshot, pattern, cv2.TM_CCOEFF_NORMED)
        _, max_score, _, max_location = cv2.minMaxLoc(result)
        print("template max score: ", max_score, "location: ", max_location, "icon: ", pattern_path)

        locations = np.where(result >= threshold)
        if len(locations[0]) == 0:
            return {
                "matched": False,
                "locations": locations,
                "rect": (0, 0, 0, 0),
                "tap_pos": (0, 0),
            }

        x, y = locations[::-1]
        w, h = pattern.shape[::-1]
        return {
            "matched": True,
            "locations": locations,
            "rect": (x[0], y[0], w, h),
            "tap_pos": (x[0] + w / 2, y[0] + h / 2),
        }

    @staticmethod
    def log_blocking_screen(message):
        print(message)
        try:
            from services.logger import LoggerSingleton
            LoggerSingleton.getInstance().info('./logs/log_test.txt', message)
        except Exception as exc:
            print("blocking screen log failed:", exc)

    @staticmethod
    def handleCommonBlockingScreen(screenshot_path):
        daily_close_pos = OctoUtil.cv2CheckImgOnScreenshot('./Icons/dailyBulletinClose.png', screenshot_path)
        if daily_close_pos is not None:
            OctoUtil.log_blocking_screen("识别到通用关闭按钮，点击关闭")
            ADBClass.AdbSingleton.getInstance().tap(daily_close_pos)
            time.sleep(1)
            return True

        if OctoUtil.screenshot_has_text(screenshot_path, ("收获一览", "收穫一覽", "收货一览")):
            OctoUtil.log_blocking_screen("识别到收获一览，点击右下角关闭")
            ADBClass.AdbSingleton.getInstance().tap((1218, 660))
            time.sleep(1)
            return True
        return False

    @staticmethod
    def crop_image(screenshot_path, lrtb, cropped_path):
        screenshot = Image.open(screenshot_path)
        cropped_image = screenshot.crop(lrtb)

        cropped_image.save(cropped_path)
        scanRes = OCRClass.OCRSingleton.getInstance().scanText(cropped_path)
        return scanRes

    @staticmethod
    def check_string(string):
        pattern = re.compile(r'[A-Za-z]')
        match = pattern.search(string)
        return bool(match)

    @staticmethod
    def map_char_num(letter):
        return ord(letter) - ord('A') + 1

    @staticmethod
    def eliminate_close_values(array, threshold):
        result = []
        for value in array:
            if all(abs(value - other) > threshold for other in result):
                result.append(value)
        return result

    @staticmethod
    def parse_mission_to_yaml(mission):
        data, missionListStr = OctoUtil._build_mission_yaml_data(mission)
        if missionListStr:
            data[1]['Material_Mission']['mission'] += missionListStr
        with open('active_config.yaml', 'w', encoding='utf-8') as file:
            yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)

    @staticmethod
    def checkSelectedCharNum(top, left, bottom, right, inputImgPath = None):
        ADBClass.AdbSingleton().getInstance().connectDevice("D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe",
                                              "127.0.0.1:7555")
        if inputImgPath is None:
            inputImgPath = './img/checkSelectedCharNum.png'
            ADBClass.AdbSingleton.getInstance().screen_capture(inputImgPath)
        screenshot = Image.open(inputImgPath)
        cropped_image = screenshot.crop((left, top, right, bottom))

        dir_name = os.path.dirname(inputImgPath)
        file_name, extension = os.path.splitext(os.path.basename(inputImgPath))

        new_file_name = file_name + 'CroppedScreenshot' + extension
        croppedInputImgPath = os.path.join(dir_name, new_file_name)

        cropped_image.save(croppedInputImgPath)
        res = OCRClass.OCRSingleton.getInstance().scanText(croppedInputImgPath)
        print(res)
        return res

    @staticmethod
    def parse_mission_to_preset_yaml(mission, fileName):
        data, missionListStr = OctoUtil._build_mission_yaml_data(mission, allow_duplicate_keys=True)
        if missionListStr:
            data[1]['Material_Mission']['mission'] += missionListStr
        with open(fileName, 'w', encoding='utf-8') as file:
            yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)

    @staticmethod
    def _build_mission_yaml_data(mission, allow_duplicate_keys=False):
        data = [
            {'LevelAutomation': {}},
            {'Material_Mission': {'mission': ""}}
        ]
        mission_keys = []

        for level in mission:
            mission_key = OctoUtil.pad_number_with_zeros(
                level.missionId + (level.midMission or ""),
                level.difficulty
            )
            mission_keys.append(mission_key)
            yaml_key = mission_key
            if allow_duplicate_keys:
                duplicate_index = 1
                while yaml_key in data[0]['LevelAutomation']:
                    yaml_key = f"{mission_key}_{duplicate_index}"
                    duplicate_index += 1

            data[0]['LevelAutomation'][yaml_key] = {
                'characters': ",".join(level.characterList),
                'isAuto': level.auto,
                'isFreeAuto': level.freeAuto,
                'autoDeploy': getattr(level, 'autoDeploy', False),
                'defaultDifficulty': getattr(level, 'defaultDifficulty', False),
                'highRewardFirst': getattr(level, 'highRewardFirst', False)
            }

        return data, ",".join(mission_keys)

    @staticmethod
    def cv2CheckImgExist(
            patternPath,
            screenshotPath,
            isSingle=True,
            needScreenShot=False,
            threshold=0.8,
            min_x=None,
            max_x=None,
            min_y=None,
            max_y=None
    ):
        if needScreenShot:
            ADBClass.AdbSingleton.getInstance().screen_capture(screenshotPath)

        def match_current_screenshot():
            screenshot = cv2.imread(screenshotPath, 0)
            pattern = cv2.imread(patternPath, 0)
            if screenshot is None:
                print(f"Screenshot not found or unreadable: {screenshotPath}")
                return None, None, None, (0, 0)
            if pattern is None:
                print(f"Template asset not found or unreadable: {patternPath}")
                return None, None, None, (0, 0)

            offset_x = int(min_x) if min_x is not None else 0
            offset_y = int(min_y) if min_y is not None else 0
            right = int(max_x) if max_x is not None else screenshot.shape[1]
            bottom = int(max_y) if max_y is not None else screenshot.shape[0]
            offset_x = max(0, min(offset_x, screenshot.shape[1]))
            offset_y = max(0, min(offset_y, screenshot.shape[0]))
            right = max(offset_x, min(right, screenshot.shape[1]))
            bottom = max(offset_y, min(bottom, screenshot.shape[0]))
            if any(value is not None for value in (min_x, max_x, min_y, max_y)):
                screenshot = screenshot[offset_y:bottom, offset_x:right]

            if screenshot.size == 0 or pattern.shape[0] > screenshot.shape[0] or pattern.shape[1] > screenshot.shape[1]:
                return None, pattern, screenshot, (offset_x, offset_y)

            result = cv2.matchTemplate(screenshot, pattern, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold)
            return locations, pattern, screenshot, (offset_x, offset_y)

        locations, pattern, screenshot, offset = match_current_screenshot()
        if locations is None:
            return None

        if isSingle:
            if len(locations[0]) > 0:
                _, max_val, _, max_loc = cv2.minMaxLoc(cv2.matchTemplate(screenshot, pattern, cv2.TM_CCOEFF_NORMED))
                if max_val < threshold:
                    return None
                w, h = pattern.shape[::-1]
                return (offset[0] + max_loc[0] + w / 2, offset[1] + max_loc[1] + h / 2)
            else:
                return None
        else:
            if len(locations[0]) > 0:
                x, y = locations[::-1]
                w, h = pattern.shape[::-1]
                resArr = []
                for i in range(len(locations[0])):
                    currCoord = (offset[0] + x[i] + w / 2, offset[1] + y[i] + h / 2)
                    isTooClose = False
                    for coord in resArr:
                        dist = math.dist(coord, currCoord)
                        if dist < 50:
                            isTooClose = True
                            break
                    if not isTooClose:
                        resArr.append(currCoord)
                return resArr
            else:
                return None

    @staticmethod
    def backToMainScreen():
        while OctoUtil.cv2CheckImgExist('./Icons/loggedInCheckImg.png', './img/levelCapture.png', needScreenShot=True) is None:
            res = OctoUtil.cv2CheckImgExist('./Icons/backButton.png', './img/levelCapture.png')
            if res is not None:
                ADBClass.AdbSingleton.getInstance().tap(res)
                time.sleep(1)
            elif OctoUtil.handleCommonBlockingScreen('./img/levelCapture.png'):
                time.sleep(1)

