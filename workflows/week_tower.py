import re
import time

from PIL import Image

from soc_one_dragon.services import ocr_service as OCRClass
from soc_one_dragon.utils import image_tools as OctoUtil
from soc_one_dragon.workflows.common import SetupAdb, adb, log


class NavigateToTower:
    def run(self):
        adb().screen_capture('./img/weeklyTower.png')
        res = OctoUtil.OctoUtil.cv2CheckImgExist('./Icons/loggedInCheckImg.png', './img/weeklyTower.png')
        if res:
            adb().tap(res)
            time.sleep(1)

        adb().tap((280, 311))
        time.sleep(3)
        adb().swipe((1176, 377), (101, 377), 1000)
        time.sleep(1)
        adb().tap((640, 334))
        time.sleep(1)


class StartFight:
    def run(self):
        adb().tap((500, 440))
        time.sleep(1)
        adb().screen_capture('./img/weeklyTower.png')
        res = OctoUtil.OctoUtil.cv2CheckImgExist('./Icons/TowerStartFight.png', './img/weeklyTower.png')
        if res is None:
            adb().tap((738, 440))
            time.sleep(1)
            res = OctoUtil.OctoUtil.cv2CheckImgExist('./Icons/TowerStartFight.png', './img/weeklyTower.png')
            if res is not None:
                adb().tap(res)
                time.sleep(1)
        else:
            adb().tap(res)
            time.sleep(1)


class GetCurrentProgress:
    def run(self):
        adb().screen_capture('./img/weeklyTower.png')
        res = OctoUtil.OctoUtil.cv2CheckImgExist('./Icons/TowerReward.png', './img/weeklyTower.png')
        if res:
            adb().tap(res)
            time.sleep(1)

        # 进度文本形如 1/10，只裁剪数字区域避免周围 UI 干扰 OCR。
        adb().screen_capture('./img/weeklyTower.png')
        im = Image.open('./img/weeklyTower.png')
        im = im.crop((741, 552, 866, 592))
        im.save('./img/weeklyTower.png')
        im.close()

        res = OCRClass.OCRSingleton.getInstance().scanText('./img/weeklyTower.png')
        print(res)
        res = re.findall(r'\d+', res[0][0])
        res = int(res[0])
        print(res)
        back_pos = OctoUtil.OctoUtil.cv2CheckImgExist('./Icons/backButton.png', './img/weeklyTower.png', needScreenShot=True)
        if back_pos is not None:
            adb().tap(back_pos)
        time.sleep(1)
        return res



class weeklyTower:
    def __init__(self, adb_path, adb_port):
        self.adb_path = adb_path
        self.adb_port = adb_port

    def run(self):
        adb_is_connected = adb().connectDevice(
            adb_path=self.adb_path,
            adb_port=self.adb_port,
            retryCount=20
        )
        if not adb_is_connected:
            log("连接模拟器失败，停止爬塔")
            return False
        SetupAdb(self.adb_path, self.adb_port, retry_count=5).run()

        OctoUtil.OctoUtil.backToMainScreen()

        NavigateToTower().run()
        time.sleep(3)
        GetCurrentProgress().run()


startFight = StartFight
getCurrentProgress = GetCurrentProgress
