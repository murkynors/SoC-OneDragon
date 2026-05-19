import easyocr
import cv2
import yaml


class OCRSingleton:
    instance = None

    def __init__(self):
        self._OCR = easyocr.Reader(self._load_languages())

    def _load_languages(self):
        try:
            with open('app_config.yaml', 'r', encoding='utf-8') as config_file:
                config_data = yaml.safe_load(config_file) or []
        except FileNotFoundError:
            return ['ch_sim', 'en']

        for item in config_data:
            if isinstance(item, dict) and 'ocrLanguages' in item:
                languages = item['ocrLanguages']
                if isinstance(languages, list) and languages:
                    return languages
        return ['ch_sim', 'en']

    @staticmethod
    def getInstance():
        if OCRSingleton.instance is None:
            OCRSingleton.instance = OCRSingleton()
        return OCRSingleton.instance

    def findTextPosition(self, img, text, enhanced=False):
        result = self._readtext(img, enhanced=enhanced)
        for line in result:
            if line[2] > 0.3:
                if text in line[1] or self._normalize_text(text) in self._normalize_text(line[1]):
                    positionRect = line[0]
                    center = ((positionRect[0][0] + positionRect[1][0]) / 2,
                              (positionRect[1][1] + positionRect[2][1]) / 2)
                    return (line[1], center)
        return None

    def _normalize_text(self, text):
        mapping = str.maketrans({
            '關': '关',
            '卡': '卡',
            '開': '开',
            '始': '始',
            '獎': '奖',
            '勵': '励',
            '領': '领',
            '獲': '获',
            '穫': '获',
            '選': '选',
            '擇': '择',
            '隊': '队',
            '鍵': '键',
            '贈': '赠',
            '兌': '兑',
            '換': '换',
            '遠': '远',
            '當': '当',
            '發': '发',
            '灣': '湾',
            '紅': '红',
            '曉': '晓',
            '審': '审',
            '蘭': '兰',
            '鎮': '镇',
            '編': '编',
            '來': '来',
            '湧': '涌',
            '騎': '骑',
            '國': '国',
            '幟': '帜',
            '輝': '辉',
            '鈴': '铃',
        })
        return str(text).translate(mapping).replace(" ", "").replace("-", "").replace("－", "")

    def scanText(self, img, enhanced=False):
        result = self._readtext(img, enhanced=enhanced)
        lineList = []
        for line in result:
            if line[2] > 0.3:
                positionRect = line[0]
                center = ((positionRect[0][0] + positionRect[1][0]) / 2,
                          (positionRect[1][1] + positionRect[2][1]) / 2)
                lineList.append((line[1], center))
        return lineList

    def _readtext(self, img, enhanced=False):
        result = self._OCR.readtext(img)
        if not enhanced:
            return result

        try:
            for enhanced_img, scale in self._enhanced_images(img):
                for line in self._OCR.readtext(
                        enhanced_img,
                        contrast_ths=0.05,
                        adjust_contrast=0.7,
                        text_threshold=0.25,
                        low_text=0.2,
                        link_threshold=0.2,
                        mag_ratio=2,
                ):
                    result.append((self._scale_box(line[0], scale), line[1], line[2]))
        except Exception as exc:
            print("enhanced OCR failed:", exc)
        return result

    def _enhanced_images(self, img):
        source = cv2.imread(img) if isinstance(img, str) else img
        if source is None:
            return []
        gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY) if len(source.shape) == 3 else source
        scaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        _, binary = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        adaptive = cv2.adaptiveThreshold(
            scaled,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            5,
        )
        return [(scaled, 2), (binary, 2), (adaptive, 2)]

    def _scale_box(self, box, scale):
        return [[point[0] / scale, point[1] / scale] for point in box]

