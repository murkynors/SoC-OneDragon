import os
import re
import time

import yaml
from PIL import Image

from device import adb_controller as ADBClass
from services import ocr_service as OCRClass
from utils import image_tools as OctoUtil
import numpy as np
from PIL import ImageChops

from workflows.common import adb, log


class mainMaterial:
    AUTO_RUN_COMPLETED_CONFIRM_POS = (1218, 660)

    def __init__(self, adb_path, adb_port):
        self.adb_path = adb_path
        self.adb_port = adb_port
        self.currentStage = 0

    def load_active_config(self):
        with open('active_config.yaml', 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)

    def get_active_mission_config(self, mission_code):
        return self.load_active_config()[0]['LevelAutomation'][mission_code]

    def log(self, message):
        log(message)

    def format_mission_log(self, mission_name, mission_config):
        parts = [f"刷图: {mission_name}"]
        if mission_config.get('isAuto', True):
            parts.append("(自动)")
            if mission_config.get('autoDeploy', False):
                parts.append("(自动上阵)")
            else:
                parts.append("| " + mission_config.get('characters', ''))
            if mission_config.get('isFreeAuto', False):
                parts.append("(章鱼罐头)")
        else:
            parts.append("(手动)")
        return " ".join(parts)

    def clickAutoCharacter(self, mission_status, mission_code):
        level_character_list = self.get_active_mission_config(mission_code)['characters']
        level_character = level_character_list.split(',')

        resArr = []
        for char in level_character:
            print(char)
            matches = re.findall(r'"([^"]*)"', char)

            if len(matches) > 0:
                char = matches[0]
                print("Text inside quotation marks:", char)
            ADBClass.AdbSingleton.getInstance().screen_capture('./img/autoRunScreenshot.png')
            res = OCRClass.OCRSingleton.getInstance().findTextPosition('./img/autoRunScreenshot.png', char)
            notRunOunOutOfCharacter = True
            while notRunOunOutOfCharacter:
                if res is not None:
                    left = 970
                    top = 554
                    right = 985
                    bottom = 585
                    inputImgPath = './img/checkSelectedCharNum.png'
                    ADBClass.AdbSingleton.getInstance().screen_capture(inputImgPath)
                    screenshot = Image.open(inputImgPath)
                    cropped_image = screenshot.crop((left, top, right, bottom))
                    cropped_image.save('./img/checkSelectedCharNumBefore.png')

                    OctoUtil.OctoUtil.checkSelectedCharNum(top, left, bottom, right)
                    ADBClass.AdbSingleton.getInstance().tap(res[1])
                    time.sleep(1)
                    inputImgPath = './img/checkSelectedCharNum.png'
                    ADBClass.AdbSingleton.getInstance().screen_capture(inputImgPath)
                    screenshot = Image.open(inputImgPath)
                    cropped_image = screenshot.crop((left, top, right, bottom))
                    cropped_image.save('./img/checkSelectedCharNumAfter.png')

                    image_one = Image.open("./img/checkSelectedCharNumBefore.png").convert('RGB')
                    image_two = Image.open("./img/checkSelectedCharNumAfter.png").convert('RGB')

                    diff = ImageChops.difference(image_one, image_two)
                    if diff.getbbox() is not None:
                        time.sleep(1)
                        ADBClass.AdbSingleton.getInstance().swipe((400, 325), (400, 10000), 1000)
                        time.sleep(3)
                        break
                    else:
                        return (f"Character Cannot Be Selected: {char}", res)
                else:
                    left = 139
                    top = 312
                    right = 607
                    bottom = 428

                    ADBClass.AdbSingleton.getInstance().screen_capture('./img/ScrollCharacterBefore.png')
                    screenshot = Image.open('./img/ScrollCharacterBefore.png')
                    cropped_image = screenshot.crop((left, top, right, bottom))
                    cropped_image.save("./img/ScrollCharacterBeforeCroppedScreenshot.png")

                    ADBClass.AdbSingleton.getInstance().swipe((400, 600), (400, 225), 1000)
                    time.sleep(4)

                    ADBClass.AdbSingleton.getInstance().screen_capture('./img/ScrollCharacterAfter.png')
                    screenshot = Image.open('./img/ScrollCharacterAfter.png')
                    cropped_image = screenshot.crop((left, top, right, bottom))
                    cropped_image.save("./img/ScrollCharacterAfterCroppedScreenshot.png")

                    image_one = Image.open("./img/ScrollCharacterBeforeCroppedScreenshot.png").convert('RGB')
                    image_two = Image.open("./img/ScrollCharacterAfterCroppedScreenshot.png").convert('RGB')

                    diff = ImageChops.difference(image_one, image_two)

                    if diff.getbbox() is not None:
                        print("The images are different.")
                        ADBClass.AdbSingleton.getInstance().screen_capture('./img/autoRunScreenshot.png')
                        time.sleep(2)
                        res = OCRClass.OCRSingleton.getInstance().findTextPosition('./img/autoRunScreenshot.png', char)
                        time.sleep(2)

                    else:
                        print("The images are the same.")
                        return ("error", "No character found")

            resArr.append(res)
        if len(resArr) != len(level_character):
            return ("error", "No character found")
        else:
            return ("success", "Character found")

    def confirmAutoDeployCharacters(self):
        screenshot_path = './img/autoDeployConfirm.png'
        for _ in range(4):
            time.sleep(1)
            ADBClass.AdbSingleton.getInstance().screen_capture(screenshot_path)

            for icon_path in ('./Icons/ConfirmButton.png', './Icons/DisabledConfirmButton.png'):
                if not os.path.exists(icon_path):
                    continue
                cvres = self.cv2CheckImgExist(icon_path, screenshot_path)
                if cvres is not None:
                    ADBClass.AdbSingleton.getInstance().tap(cvres)
                    time.sleep(1)
                    return ("success", "auto deploy")

            start_auto_pos = self.cv2CheckImgExist('./Icons/StartAutoBattle.png', screenshot_path)
            if start_auto_pos is not None:
                return ("success", "auto deploy already confirmed")

            continue_auto_pos = self.findContinueAutoRunButton(screenshot_path)
            if continue_auto_pos is not None:
                ADBClass.AdbSingleton.getInstance().tap(continue_auto_pos)
                continue

            auto_run_pos = self.findAutoRunMissionButton(screenshot_path)
            if auto_run_pos is not None:
                self.log("自动上阵确认未打开，仍在关卡详情页，重新点击代行")
                ADBClass.AdbSingleton.getInstance().tap(auto_run_pos)
                continue

        self.log("未找到自动上阵确认按钮")
        return ("error", "auto deploy confirm button not found")

    def clickGameBackButton(self, screenshot_path='./img/levelCapture.png'):
        ADBClass.AdbSingleton.getInstance().screen_capture(screenshot_path)
        back_pos = self.cv2CheckImgExist('./Icons/backButton.png', screenshot_path)
        if back_pos is None:
            self.log("未识别到游戏内返回键，取消返回操作")
            return False
        ADBClass.AdbSingleton.getInstance().tap(back_pos)
        return True

    def isMainScreen(self, screenshot_path='./img/mainMaterialMainCheck.png'):
        ADBClass.AdbSingleton.getInstance().screen_capture(screenshot_path)
        for template_path in (
            './Icons/MainPageCheck.png',
            './Icons/loggedInCheckImg.png',
            './Icons/RewardIcon.png',
            './Icons/friend.png',
            './Icons/yuanhang.png',
        ):
            if not os.path.exists(template_path):
                continue
            if self.cv2CheckImgExist(template_path, screenshot_path) is not None:
                return True
        return False

    def backToMainScreen(self, max_steps=10):
        for _ in range(max_steps):
            if self.isMainScreen():
                return True
            if self.clickGameBackButton('./img/mainMaterialBackCheck.png'):
                time.sleep(1)
                continue
            self.log("未识别到游戏内返回键，停止回主界面兜底")
            break
        if self.isMainScreen():
            return True
        self.log("未能确认已回到主界面")
        return False

    def skipCurrentMission(self, mission_name, start_mission_result):
        reason = start_mission_result[1] if start_mission_result and len(start_mission_result) > 1 else "unknown"
        self.log(f"{mission_name} 可能已刷过，跳过当前任务：{reason}")
        if self.clickGameBackButton():
            time.sleep(2)

    def checkCurrentPageStatus(self, destinationPage):
        if "DailyMaterial" in destinationPage[0]:
            ADBClass.AdbSingleton.getInstance().screen_capture('./img/levelCapture.png')
            res = self.cv2CheckImgExist('./Icons/materialMissionCheck.png', './img/levelCapture.png')
            print("cv2 result (MATERIAL_MENU): ", res)
            if res:
                return ("MATERIAL_MENU", res)
            res = self.cv2CheckImgExist('./Icons/loginStartGame.png', './img/levelCapture.png')
            print("cv2 result (LOGIN_START): ", res)
            if res:
                return ("LOGIN_START", res)
            if os.path.exists('./Icons/MainPageCheck.png'):
                res = self.cv2CheckImgExist('./Icons/MainPageCheck.png', './img/levelCapture.png')
                print("cv2 result (MAIN_PAGE): ", res)
                if res:
                    return ("MAIN_PAGE", res)
            res = self.cv2CheckImgExist('./Icons/loggedInCheckImg.png', './img/levelCapture.png')
            print("cv2 result (MAIN_PAGE_FALLBACK): ", res)
            if res:
                return ("MAIN_PAGE_FALLBACK", res)
            res = self.cv2CheckImgExist('./Icons/1in3menu.png', './img/levelCapture.png')
            print("cv2 result (ONE_IN_THREE): ", res)
            if res:
                return ("ONE_IN_THREE", res)
            res = self.cv2CheckImgExist('./Icons/backButton.png', './img/levelCapture.png')
            print("cv2 result (OTHER_WITH_BACK_BTN): ", res)
            if res:
                return ("OTHER_WITH_BACK_BTN", res)
            if OctoUtil.OctoUtil.handleCommonBlockingScreen('./img/levelCapture.png'):
                return ("OTHER", None)
            return ("OTHER", None)

    def cv2CheckImgExist(self, patternPath, screenshotPath, isSingle=True):
        return OctoUtil.OctoUtil.cv2CheckImgExist(patternPath, screenshotPath, isSingle=isSingle)

    def GotoDailyMaterialStep(self, currentStatus, destinationPage):
        currentPage = currentStatus[0]
        print("GotoDailyMaterialStep ||| currentPage: ", currentPage, " | destinationPage: ", destinationPage)
        match currentPage:
            case "ONE_IN_THREE":
                ADBClass.AdbSingleton.getInstance().tap((290, 330))
                return "ONGOING"
            case "LOGIN_START":
                ADBClass.AdbSingleton.getInstance().tap(currentStatus[1])
                self.log("已点击进入游戏，等待加载")
                time.sleep(5)
                return "ONGOING"
            case "MAIN_PAGE":
                logged_in_pos = self.cv2CheckImgExist('./Icons/loggedInCheckImg.png', './img/levelCapture.png')
                print("cv2 result (MAIN_PAGE_CLICK): ", logged_in_pos)
                ADBClass.AdbSingleton.getInstance().tap(logged_in_pos or currentStatus[1])
                return "ONGOING"
            case "MAIN_PAGE_FALLBACK":
                ADBClass.AdbSingleton.getInstance().tap(currentStatus[1])
                return "ONGOING"
            case "OTHER_WITH_BACK_BTN":
                ADBClass.AdbSingleton.getInstance().tap(currentStatus[1])
                return "ONGOING"
            case "OTHER":
                self.log("当前界面暂未识别，等待加载")
                return "WAITING"
            case "MATERIAL_MENU":
                if destinationPage[1] is not None:
                    match destinationPage[1]:
                        case "EXP":
                            ADBClass.AdbSingleton.getInstance().tap((645, 470))
                            return "ARRIVED"
                        case "SRD":
                            ADBClass.AdbSingleton.getInstance().tap((410, 366))
                            return "ARRIVED"
                        case "WUP":
                            ADBClass.AdbSingleton.getInstance().tap((1252, 384))
                            return "ARRIVED"
                        case "WEA":
                            ADBClass.AdbSingleton.getInstance().tap((202, 443))
                            return "ARRIVED"
                        case "TRT":
                            ADBClass.AdbSingleton.getInstance().tap((40, 430))
                            return "ARRIVED"
                        case "STAR":
                            ADBClass.AdbSingleton.getInstance().tap((1078, 430))
                            return "ARRIVED"
                        case "ENC":
                            ADBClass.AdbSingleton.getInstance().tap((875, 430))
                            return "ARRIVED"

    def GotoMiddleStep(self, destinationPage, highRewardFirst=False):
        print("GotoDifficultyStep ||| destinationPage: ", destinationPage)
        if destinationPage[3] == "multi":
            middleNo = destinationPage[4]
            left = 45
            top = 453
            right = 1235
            bottom = 582

            def refresh_middle_selection_screenshot():
                ADBClass.AdbSingleton.getInstance().screen_capture('./img/GotoMiddleStepScreenshot.png')
                screenshot = Image.open('./img/GotoMiddleStepScreenshot.png')
                cropped_image = screenshot.crop((left, top, right, bottom))
                cropped_image.save("./img/GotoMiddleStepScreenshotCroppedScreenshot.png")
                return screenshot

            screenshot = refresh_middle_selection_screenshot()

            if highRewardFirst and os.path.exists('./Icons/highReward.png'):
                highRewardLeft = 45
                highRewardTop = 80
                highRewardRight = 1235
                highRewardBottom = 453
                highRewardCrop = screenshot.crop((highRewardLeft, highRewardTop, highRewardRight, highRewardBottom))
                highRewardCrop.save("./img/GotoMiddleStepHighRewardScreenshot.png")
                highRewardRes = self.cv2CheckImgExist(
                    './Icons/highReward.png',
                    './img/GotoMiddleStepHighRewardScreenshot.png',
                    False
                )
                print("cv2 result (HIGH_REWARD): ", highRewardRes)
                if highRewardRes:
                    highRewardRes = sorted(highRewardRes, key=lambda pos: (pos[1], pos[0]))
                    tapPos = (highRewardRes[0][0] + highRewardLeft, highRewardRes[0][1] + highRewardTop)
                    self.log("高额优先：选择高额分页")
                    ADBClass.AdbSingleton.getInstance().tap(tapPos)
                    time.sleep(1.5)
                    refresh_middle_selection_screenshot()
                    if self.hasMissionActionButton('./img/GotoMiddleStepScreenshot.png'):
                        self.log("已打开关卡详情，直接进入启动流程")
                        return True

            if destinationPage[1] == "WEA":
                weaponTrialPos = self.findAvailableWeaponTrial(screenshot)
                if weaponTrialPos is not None:
                    self.log("武器试炼：选择当前可用分页")
                    ADBClass.AdbSingleton.getInstance().tap(weaponTrialPos)
                    time.sleep(1.5)
                    refresh_middle_selection_screenshot()
                    if self.hasMissionActionButton('./img/GotoMiddleStepScreenshot.png'):
                        self.log("已打开关卡详情，直接进入启动流程")
                        return True

            if self.hasMissionActionButton('./img/GotoMiddleStepScreenshot.png'):
                self.log("已打开关卡详情，直接进入启动流程")
                return True

            res = OCRClass.OCRSingleton.getInstance().findTextPosition(
                './img/GotoMiddleStepScreenshotCroppedScreenshot.png', str(middleNo))
            print("res: ", res)
            if res is not None:
                ADBClass.AdbSingleton.getInstance().tap((res[1][0] + left, res[1][1] + top))
                return True
            else:
                cvres = self.cv2CheckImgExist('./Icons/MiddleLevelENCIdentifier.png',
                                              './img/GotoMiddleStepScreenshotCroppedScreenshot.png', False)
                if cvres is None or len(cvres) < middleNo:
                    self.log(f"未找到第 {middleNo} 个中间关卡入口，停止刷图")
                    return False
                tapPos = (cvres[middleNo - 1][0] + left, cvres[middleNo - 1][1] + top)
                ADBClass.AdbSingleton.getInstance().tap(tapPos)
        return True

    def findAvailableWeaponTrial(self, screenshot):
        width, height = screenshot.size
        weaponTrialCards = [
            {'tap': (0.264, 0.760), 'crop': (0.171, 0.165, 0.356, 0.885)},
            {'tap': (0.500, 0.760), 'crop': (0.407, 0.165, 0.593, 0.885)},
            {'tap': (0.735, 0.760), 'crop': (0.643, 0.165, 0.828, 0.885)},
        ]
        grayscale = screenshot.convert('L')
        candidates = []
        for card in weaponTrialCards:
            crop = (
                int(card['crop'][0] * width),
                int(card['crop'][1] * height),
                int(card['crop'][2] * width),
                int(card['crop'][3] * height),
            )
            tap = (int(card['tap'][0] * width), int(card['tap'][1] * height))
            card_image = grayscale.crop(crop)
            mean_brightness = float(np.array(card_image).mean())
            print("weapon trial card brightness: ", tap, mean_brightness)
            candidates.append((mean_brightness, tap))

        if not candidates:
            return None

        candidates.sort(reverse=True)
        if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < 10:
            return None
        return candidates[0][1]

    def GotoDifficultyStep(self, destinationPage):
        print("GotoDifficultyStep ||| destinationPage: ", destinationPage)
        time.sleep(2)
        ADBClass.AdbSingleton.getInstance().screen_capture('./img/gotoDifficultyStepCapture.png')
        screenshot = Image.open("./img/gotoDifficultyStepCapture.png")

        # 难度页右上角会显示“关X”，只裁剪这块区域做 OCR，减少误识别。
        left = 830
        top = 80
        right = 904
        bottom = 110

        cropped_image = screenshot.crop((left, top, right, bottom))
        cropped_image.save("./img/gotoDifficultyStepCroppedScreenshot.png")
        scanRes = OCRClass.OCRSingleton.getInstance().scanText('./img/gotoDifficultyStepCroppedScreenshot.png')
        print("scanRes: ", scanRes)

        for item in scanRes:
            text = item[0]
            match = re.search(r'卡(\d+)', text)
            if match:
                number = int(match.group(1))
                print(f"Found number: {number}", "||| DestinationPage(2): ", destinationPage[2],
                      "||| Destination Diff: ",
                      number - destinationPage[2])
                destDiff = number - destinationPage[2]
                if destDiff == 0:
                    print("Found number: ", number)
                    return "ARRIVED"
                else:
                    if destDiff > 0:
                        for i in range(destDiff * 2):
                            ADBClass.AdbSingleton.getInstance().tap((400, 390))
                            time.sleep(1)
                    else:
                        return ("error", "difficulty locked")
                    ADBClass.AdbSingleton.getInstance().screen_capture('./img/gotoDifficultyStepCapture.png')
                    screenshot = Image.open("./img/gotoDifficultyStepCapture.png")

                    # 点击难度后再次裁剪右上角关卡号，确认已经进入目标难度。
                    left = 830
                    top = 80
                    right = 904
                    bottom = 110

                    cropped_image = screenshot.crop((left, top, right, bottom))
                    cropped_image.save("./img/gotoDifficultyStepCroppedScreenshot.png")
                    scanRes = OCRClass.OCRSingleton.getInstance().scanText(
                        './img/gotoDifficultyStepCroppedScreenshot.png')
                    print("scanRes: ", scanRes)

                    for item in scanRes:
                        text = item[0]
                        match = re.search(r'卡(\d+)', text)
                        if match:
                            return "ARRIVED"
            else:
                print("No number found.")

    def stripDuplicateMissionSuffix(self, missionId):
        match = re.match(r'^(.*_\d{2})_\d+$', missionId)
        if match:
            return match.group(1)
        return missionId

    def resolveMissionConfigEntries(self, config_data):
        levelAutomation = config_data[0].get('LevelAutomation', {})
        missionText = config_data[1].get('Material_Mission', {}).get('mission', '')
        missionOrder = [mission for mission in missionText.split(',') if mission]
        usedMissionIds = set()
        resolvedEntries = []

        for shortFormMissionId in missionOrder:
            missionId = None
            if shortFormMissionId in levelAutomation and shortFormMissionId not in usedMissionIds:
                missionId = shortFormMissionId
            else:
                duplicatePrefix = shortFormMissionId + "_"
                for candidateMissionId in levelAutomation.keys():
                    if candidateMissionId in usedMissionIds:
                        continue
                    if candidateMissionId.startswith(duplicatePrefix):
                        duplicateSuffix = candidateMissionId[len(duplicatePrefix):]
                        if duplicateSuffix.isdigit():
                            missionId = candidateMissionId
                            break

            if missionId is None:
                continue

            usedMissionIds.add(missionId)
            resolvedEntries.append((shortFormMissionId, missionId, levelAutomation[missionId]))

        for missionId, missionConfig in levelAutomation.items():
            if missionId in usedMissionIds:
                continue
            resolvedEntries.append((self.stripDuplicateMissionSuffix(missionId), missionId, missionConfig))

        return resolvedEntries

    def getMissionConfigEntriesFromConfig(self):
        return self.resolveMissionConfigEntries(self.load_active_config())

    def getMissionListFromConfig(self):
        return [mission for mission, _, _ in self.getMissionConfigEntriesFromConfig()]

    def findAutoRunMissionButton(self, screenshot_path):
        if os.path.exists('./Icons/autoRunMissionBtn.png'):
            cvres = self.cv2CheckImgExist('./Icons/autoRunMissionBtn.png', screenshot_path)
            print("cv2 result (autoRunMissionBtn): ", cvres)
            if cvres is not None:
                return cvres

        ocr_res = OCRClass.OCRSingleton.getInstance().findTextPosition(screenshot_path, "代行")
        print("ocr result (autoRunMissionBtn): ", ocr_res)
        if ocr_res:
            return ocr_res[1]
        return None

    def hasMissionActionButton(self, screenshot_path):
        if os.path.exists('./Icons/autoRunMissionBtn.png'):
            cvres = self.cv2CheckImgExist('./Icons/autoRunMissionBtn.png', screenshot_path)
            print("cv2 result (autoRunMissionBtn visible): ", cvres)
            if cvres is not None:
                return True
        if os.path.exists('./Icons/battleStart.png'):
            cvres = self.cv2CheckImgExist('./Icons/battleStart.png', screenshot_path)
            print("cv2 result (battleStart visible): ", cvres)
            if cvres is not None:
                return True

        for text in OCRClass.OCRSingleton.localized_texts(("代行", "代行"), ("出击", "出擊")):
            ocr_res = OCRClass.OCRSingleton.getInstance().findTextPosition(screenshot_path, text)
            print(f"ocr result ({text} visible): ", ocr_res)
            if ocr_res:
                return True
        return False

    def findContinueAutoRunButton(self, screenshot_path):
        if os.path.exists('./Icons/IgnoreInstantAuto.png'):
            cvres = self.cv2CheckImgExist('./Icons/IgnoreInstantAuto.png', screenshot_path)
            print("cv2 result (IgnoreInstantAuto): ", cvres)
            if cvres is not None:
                return cvres

        for text in OCRClass.OCRSingleton.localized_texts(("继续代行", "繼續代行"), ("继续", "繼續")):
            ocr_res = OCRClass.OCRSingleton.getInstance().findTextPosition(screenshot_path, text)
            print(f"ocr result ({text}): ", ocr_res)
            if ocr_res:
                return ocr_res[1]
        return None

    def findAutoRunCompletedButton(self, screenshot_path):
        if os.path.exists('./Icons/autoRunMissionCompleted.png'):
            cvres = self.cv2CheckImgExist('./Icons/autoRunMissionCompleted.png', screenshot_path)
            print("cv2 result (autoRunMissionCompleted): ", cvres)
            if cvres is not None:
                return cvres

        for text in OCRClass.OCRSingleton.localized_texts(("继续代行", "繼續代行"), ("代行奖励", "代行獎勵")):
            ocr_res = OCRClass.OCRSingleton.getInstance().findTextPosition(screenshot_path, text)
            print(f"ocr result ({text}): ", ocr_res)
            if ocr_res:
                return (640, 615)
        return None

    def dismissAutoRunCompleted(self, retries=8):
        for _ in range(retries):
            ADBClass.AdbSingleton.getInstance().screen_capture('./img/startMission.png')
            completed_pos = self.findAutoRunCompletedButton('./img/startMission.png')
            if completed_pos is not None:
                ADBClass.AdbSingleton.getInstance().tap(self.AUTO_RUN_COMPLETED_CONFIRM_POS)
                time.sleep(2)
                return True
            time.sleep(1)
        return False

    def findBattleStartButton(self, screenshot_path):
        if os.path.exists('./Icons/battleStart.png'):
            cvres = self.cv2CheckImgExist('./Icons/battleStart.png', screenshot_path)
            print("cv2 result (battleStart): ", cvres)
            if cvres is not None:
                return cvres

        for text in OCRClass.OCRSingleton.localized_texts(("开始", "開始")):
            ocr_res = OCRClass.OCRSingleton.getInstance().findTextPosition(screenshot_path, text)
            print(f"ocr result ({text}): ", ocr_res)
            if ocr_res:
                return ocr_res[1]
        return None

    def startMissionAuto(self, mission_status, mission_code):
        res = None
        for _ in range(5):
            ADBClass.AdbSingleton.getInstance().screen_capture('./img/startMission.png')
            res = self.findAutoRunMissionButton('./img/startMission.png')
            if res is not None:
                break
            time.sleep(1)
        if res is None:
            self.log("未找到代行按钮，跳过当前任务")
            return ("skip", "auto run button not found")

        ADBClass.AdbSingleton.getInstance().tap(res)
        time.sleep(1)
        cvres = None
        for _ in range(5):
            ADBClass.AdbSingleton.getInstance().screen_capture('./img/startMission.png')
            cvres = self.findContinueAutoRunButton('./img/startMission.png')
            if cvres is not None:
                break
            time.sleep(1)
        if cvres is not None:
            if self.get_active_mission_config(mission_code)['isFreeAuto']:
                ADBClass.AdbSingleton.getInstance().tap((770, 366))
                time.sleep(1)
                ADBClass.AdbSingleton.getInstance().tap((640, 590))
                return ("success", "free auto")
            ADBClass.AdbSingleton.getInstance().tap(cvres)
            print("cv2 result (startMissionBtn): ", cvres)
            time.sleep(1)
        else:
            res = self.cv2CheckImgExist('./Icons/autoRunMissionBtn.png', './img/startMission.png')
            if res:
                return ("error", "level not available for autorun yet")
        if self.get_active_mission_config(mission_code).get('autoDeploy', False):
            res = self.confirmAutoDeployCharacters()
        else:
            res = self.clickAutoCharacter(mission_status, mission_code)
        print(res)
        if not res or res[0] != "success":
            return res
        if res[0] == "success":
            ADBClass.AdbSingleton.getInstance().screen_capture('./img/startMission.png')
            cvres = self.cv2CheckImgExist('./Icons/StartAutoBattle.png', './img/startMission.png')
            if cvres is None:
                if self.dismissAutoRunCompleted(retries=2):
                    return ("success", "auto run completed")
                self.log("未找到开始代行按钮，跳过当前任务")
                return ("skip", "auto battle start button not found")
            ADBClass.AdbSingleton.getInstance().tap(cvres)
            print("cv2 result (startMissionBtn): ", cvres)
            time.sleep(1)
            if not self.dismissAutoRunCompleted():
                ADBClass.AdbSingleton.getInstance().screen_capture('./img/startMission.png')
                cvres = self.cv2CheckImgExist('./Icons/StartAutoBattle.png', './img/startMission.png')
                if cvres is None:
                    return ("success", "auto run started")
                return ("error", "Some Character Is not available")
        return ("success", res)

    def startMissionFight(self):
        ADBClass.AdbSingleton.getInstance().tap((1050, 630))
        time.sleep(5)
        battleStartPos = None
        for i in range(10):
            ADBClass.AdbSingleton.getInstance().screen_capture('./img/startMission.png')
            battleStartPos = self.findBattleStartButton('./img/startMission.png')
            if battleStartPos is not None:
                break
            time.sleep(1)
        if battleStartPos is None:
            self.log("未找到开始战斗按钮，跳过当前任务")
            return ("skip", "battle start button not found")

        ADBClass.AdbSingleton.getInstance().tap(battleStartPos)

        time.sleep(10)

        ADBClass.AdbSingleton.getInstance().screen_capture('./img/startMission.png')
        res = self.cv2CheckImgExist('./Icons/manuelBattleSwitch.png', './img/startMission.png')
        print("cv2 result (startMission): ", res)
        if res:
            ADBClass.AdbSingleton.getInstance().tap(res)

        res = self.cv2CheckImgExist('./Icons/NormalSpeedBattleSwitch.png', './img/startMission.png')
        print("cv2 result (startMission): ", res)
        if res:
            ADBClass.AdbSingleton.getInstance().tap(res)
        time.sleep(2)
        ADBClass.AdbSingleton.getInstance().screen_capture('./img/startMission.png')
        # 战斗内加速按钮开启时该像素为绿色，未开启则补点一次。
        isSpeedAnimation = OctoUtil.OctoUtil.check_pixel_color('./img/startMission.png', 751, 35, (132, 202, 124, 255))
        if isSpeedAnimation is False:
            ADBClass.AdbSingleton.getInstance().tap((752, 35))
        print("isSpeedAnimation: ", isSpeedAnimation)

        fightFinish = False
        while fightFinish is False:
            ADBClass.AdbSingleton.getInstance().screen_capture('./img/inFight.png')
            res = self.cv2CheckImgExist('./Icons/inFightIcon.png', './img/inFight.png')
            print("cv2 result (startMission): ", res)
            if res is None:
                fightFinish = True
                break
            time.sleep(5)
        time.sleep(5)
        ADBClass.AdbSingleton.getInstance().screen_capture('./img/levelUpCheck.png')
        res = self.cv2CheckImgExist('./Icons/levelUpCheck.png', './img/levelUpCheck.png')
        if res:
            ADBClass.AdbSingleton.getInstance().tap((625, 625))
        time.sleep(2)
        ADBClass.AdbSingleton.getInstance().screen_capture('./img/winBattleText.png')
        res = self.cv2CheckImgExist('./Icons/winBattleText.png', './img/winBattleText.png')
        if res:
            ADBClass.AdbSingleton.getInstance().tap(res)
        time.sleep(2)
        ADBClass.AdbSingleton.getInstance().screen_capture('./img/winFightMaterialScreen.png')
        res = self.cv2CheckImgExist('./Icons/winFightMaterialScreen.png', './img/winFightMaterialScreen.png')
        if res:
            ADBClass.AdbSingleton.getInstance().tap(res)
        time.sleep(2)
        return ("success", "manual battle")

    def mapMissionToStatus(self, mission_config, input):
        auto_dictionary = ["EXP", "WUP", "ENC", "STAR", "WEA", "SRD", "TRT"]
        single_level_dictionary = ["EXP", "WUP", "SRD"]
        multi_level_dictionary = ["STAR", "ENC", "WEA", "TRT"]
        for key in auto_dictionary:
            if key in input:
                prefix = key
                suffix = input.replace(key, "")
                if OctoUtil.OctoUtil.check_string(suffix) is True:
                    full_suffix = suffix.split("_")
                    levelNo = full_suffix[0]
                    levelNo = OctoUtil.OctoUtil.map_char_num(levelNo)
                    suffix = int(full_suffix[1])
                else:
                    suffix = int(suffix.lstrip("_"))
                    levelNo = None
                if mission_config.get('isAuto', True) is True:
                    category = "DailyMaterialAuto"
                else:
                    category = "DailyMaterialFight"

        for key in single_level_dictionary:
            if key in input:
                levelType = "single"

        for key in multi_level_dictionary:
            if key in input:
                levelType = "multi"

        return category, prefix, suffix, levelType, levelNo
    def run(self):
        adb_is_connected = adb().connectDevice(
            adb_path=self.adb_path,
            adb_port=self.adb_port,
            retryCount=20
        )
        if not adb_is_connected:
            self.log("连接模拟器失败，停止刷图")
            return False
        self.log("开始刷图")
        try:
            missionConfigEntries = self.getMissionConfigEntriesFromConfig()
            for index, (mission, missionActiveName, missionConfig) in enumerate(missionConfigEntries):
                self.log(self.format_mission_log(missionActiveName, missionConfig))
                defaultDifficulty = missionConfig.get('defaultDifficulty', False)
                highRewardFirst = missionConfig.get('highRewardFirst', False)
                missionStatus = self.mapMissionToStatus(missionConfig, mission)
                print("mission status: ", missionStatus)
                det_res = self.checkCurrentPageStatus(missionStatus)
                navigation_attempts = 0
                while det_res[0] != "ARRIVED" and navigation_attempts < 20:
                    navigation_attempts += 1
                    det_res = self.checkCurrentPageStatus(missionStatus)
                    print("det_res", det_res)
                    GotoStepRes = self.GotoDailyMaterialStep(det_res, missionStatus)
                    print("GotoStepRes", GotoStepRes)
                    if GotoStepRes == "ARRIVED":
                        time.sleep(2)
                        break
                    if GotoStepRes == "WAITING":
                        time.sleep(3)
                        continue
                    time.sleep(2)
                if navigation_attempts >= 20:
                    self.log("跳转资源菜单超时，停止刷图")
                    return False
                GotoMiddleRes = self.GotoMiddleStep(missionStatus, highRewardFirst)
                if GotoMiddleRes is False:
                    return False
                if defaultDifficulty:
                    self.log("使用默认难度，跳过难度选择")
                    GotoDifficultyRes = "ARRIVED"
                else:
                    GotoDifficultyRes = self.GotoDifficultyStep(missionStatus)
                if GotoDifficultyRes == "ARRIVED":
                    print("GotoDifficultyRes ARRIVED")
                    time.sleep(2)
                    if missionStatus[0] == "DailyMaterialAuto":
                        startMissionRes = self.startMissionAuto(missionStatus, missionActiveName)
                        if startMissionRes and startMissionRes[0] == "skip":
                            self.skipCurrentMission(missionActiveName, startMissionRes)
                            continue
                        if not startMissionRes or startMissionRes[0] != "success":
                            self.log(f"代行启动失败：{startMissionRes}")
                            return False
                    elif missionStatus[0] == "DailyMaterialFight":
                        startMissionRes = self.startMissionFight()
                        if startMissionRes and startMissionRes[0] == "skip":
                            self.skipCurrentMission(missionActiveName, startMissionRes)
                            continue
                        if not startMissionRes or startMissionRes[0] != "success":
                            self.log(f"手动战斗启动失败：{startMissionRes}")
                            return False
                        self.log(f"结束刷图: {missionActiveName} (手动) | 已开始行动{index}次")
            return True
        finally:
            self.backToMainScreen()
