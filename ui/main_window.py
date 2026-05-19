import glob
import os
import re

from soc_one_dragon.services.logger import LoggerSingleton
from soc_one_dragon.workflows.receive_reward import receiveReward
from soc_one_dragon.workflows.start_app import runStartApp
from soc_one_dragon.workflows.main_material import mainMaterial

import yaml
from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import Qt, QIcon

from soc_one_dragon.device import adb_controller as ADBClass
from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import QPushButton, QCheckBox, QSizePolicy
from soc_one_dragon.utils import image_tools as OctoUtil
from soc_one_dragon.models.reward_tasks import REWARD_SUBTASK_DEFAULTS, REWARD_SUBTASK_LABELS
from soc_one_dragon.models.scheduled_mission import scheduleMission
from soc_one_dragon.ui.runtime import FlowThread, Monitor
from soc_one_dragon.ui.styles import LIST_BUTTON_STYLE, SELECTED_BUTTON_STYLE


class OctoUI(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("铃兰一条龙")
        self.selectedFiles = []
        self.setMinimumSize(1000, 560)
        self.runProg = True
        self.lastReadPtr = 0
        self.isLoadingMissions = False
        self.editingMission = scheduleMission.UIInit(None)




        self.scheduleMissionList = []
        self.missionNameList = []
        self.missionInfoList = []
        self.characterNameList = []
        # UI 启动时先读取 app_config.yaml，后续下拉框和角色按钮都依赖这份配置。
        if os.path.exists('app_config.yaml'):
            with open('app_config.yaml', 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
                self.missionInfoList = config_data[4]["missionInfo"]
                for mission in config_data[4]["missionInfo"]:
                    self.missionNameList.append(mission['name'])
                self.characterNameList = config_data[3]['characterList']

        self.tabs = QtWidgets.QTabWidget()
        self.tab1 = QtWidgets.QWidget()
        self.tab1Layout = QtWidgets.QHBoxLayout(self.tab1)
        self.tab1Layout.setContentsMargins(16, 16, 16, 16)
        self.tab1Layout.setSpacing(16)
        self.leftPanel = QtWidgets.QVBoxLayout()
        self.leftPanel.setSpacing(12)
        self.mission = []
        self.startAppOptionWidget = QtWidgets.QWidget()
        self.startAppOptionLayout = QtWidgets.QHBoxLayout(self.startAppOptionWidget)
        self.startAppOptionLayout.setAlignment(QtCore.Qt.AlignTop)

        self.startAppCheckbox = QCheckBox('开始唤醒', self)
        self.startAppCheckbox.stateChanged.connect(self.saveTaskSelection)
        self.startAppSetting = QtWidgets.QPushButton("设置")

        self.startAppOptionLayout.addWidget(self.startAppCheckbox)
        self.startAppOptionLayout.addStretch()
        self.startAppOptionLayout.addWidget(self.startAppSetting)


        self.farmResOptionWidget = QtWidgets.QWidget()
        self.farmResOptionLayout = QtWidgets.QHBoxLayout(self.farmResOptionWidget)
        self.farmResOptionLayout.setAlignment(QtCore.Qt.AlignTop)

        self.farmResCheckbox = QCheckBox('自动刷图', self)
        self.farmResCheckbox.stateChanged.connect(self.saveTaskSelection)
        self.farmResSetting = QtWidgets.QPushButton("设置")

        self.farmResOptionLayout.addWidget(self.farmResCheckbox)
        self.farmResOptionLayout.addStretch()
        self.farmResOptionLayout.addWidget(self.farmResSetting)

        self.receiveRewardOptionWidget = QtWidgets.QWidget()
        self.receiveRewardOptionLayout = QtWidgets.QHBoxLayout(self.receiveRewardOptionWidget)
        self.receiveRewardOptionLayout.setAlignment(QtCore.Qt.AlignTop)

        self.receiveRewardCheckbox = QCheckBox('领取奖励', self)
        self.receiveRewardCheckbox.stateChanged.connect(self.saveTaskSelection)
        self.receiveRewardSetting = QtWidgets.QPushButton("设置")
        self.receiveRewardSetting.clicked.connect(self.openReceiveRewardSettings)
        self.receiveRewardSubtasks = self.defaultReceiveRewardSubtasks()

        self.receiveRewardOptionLayout.addWidget(self.receiveRewardCheckbox)
        self.receiveRewardOptionLayout.addStretch()
        self.receiveRewardOptionLayout.addWidget(self.receiveRewardSetting)

        self.taskBox = QtWidgets.QGroupBox("任务队列")

        self.StartBtn = QtWidgets.QPushButton("启动")
        self.StartBtn.setObjectName("primaryButton")
        self.StartBtn.connect(self.StartBtn, QtCore.SIGNAL("clicked()"), lambda: self.startMainFlow([self.startAppCheckbox.isChecked(), self.farmResCheckbox.isChecked(), self.receiveRewardCheckbox.isChecked()]))

        self.StopBtn = QtWidgets.QPushButton("停止")
        self.StopBtn.setObjectName("dangerButton")
        self.StopBtn.connect(self.StopBtn, QtCore.SIGNAL("clicked()"), lambda: self.stopMainFlow())

        self.taskIntroLabel = QtWidgets.QLabel("选择要执行的自动化步骤，日志会在右侧实时刷新。")
        self.taskIntroLabel.setProperty("role", "muted")

        self.taskLabelLayout = QtWidgets.QVBoxLayout(self.taskBox)
        self.taskLabelLayout.setSpacing(10)
        self.taskLabelLayout.addWidget(self.taskIntroLabel)
        self.taskLabelLayout.addWidget(self.startAppOptionWidget)
        self.taskLabelLayout.addWidget(self.farmResOptionWidget)
        self.taskLabelLayout.addWidget(self.receiveRewardOptionWidget)
        self.taskLabelLayout.addSpacing(8)
        self.taskLabelLayout.addWidget(self.StartBtn)
        self.taskLabelLayout.addWidget(self.StopBtn)


        self.leftPanel.addWidget(self.taskBox)

        self.rightPanel = QtWidgets.QVBoxLayout()
        self.rightPanel.setSpacing(10)
        self.logTitle = QtWidgets.QLabel("运行日志")
        self.logTitle.setProperty("role", "title")
        self.logHint = QtWidgets.QLabel("脚本输出、异常和停止请求会显示在这里。")
        self.logHint.setProperty("role", "muted")

        self.streamerDisplayWidget = QtWidgets.QWidget()
        self.streamerDisplayVbox = QtWidgets.QVBoxLayout()
        self.streamerDisplayWidget.setLayout(self.streamerDisplayVbox)
        self.recordingScrollArea = QtWidgets.QScrollArea()
        self.recordingScrollArea.setWidget(self.streamerDisplayWidget)
        self.recordingScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.recordingScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.recordingScrollArea.setWidgetResizable(True)
        self.recordingScrollArea.setObjectName("panel")

        self.logText = QtWidgets.QTextEdit()
        self.logText.setReadOnly(True)
        self.logText.setText("")
        self.streamerDisplayVbox.addWidget(self.logText)
        self.rightPanel.addWidget(self.logTitle)
        self.rightPanel.addWidget(self.logHint)
        self.rightPanel.addWidget(self.recordingScrollArea, 1)

        self.tab1Layout.addLayout(self.leftPanel, 1)
        self.tab1Layout.addLayout(self.rightPanel, 2)

        self.fixVideoTabWidget = QtWidgets.QWidget()
        self.fixVideoTabLayout = QtWidgets.QHBoxLayout()
        self.fixVideoTabLayout.setContentsMargins(16, 16, 16, 16)
        self.fixVideoTabLayout.setSpacing(16)
        self.fixVideoTabWidget.setLayout(self.fixVideoTabLayout)

        self.flineEditsWidget = QtWidgets.QWidget()
        self.flineEditsVbox = QtWidgets.QVBoxLayout()
        self.flineEditsVbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.flineEditsWidget.setLayout(self.flineEditsVbox)
        self.flineEditsScrollArea = QtWidgets.QScrollArea()
        self.flineEditsScrollArea.setWidget(self.flineEditsWidget)
        self.flineEditsScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.flineEditsScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.flineEditsScrollArea.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.flineEditsScrollArea.setWidgetResizable(True)
        self.flineEditsScrollArea.setObjectName("panel")

        self.saveSettingBtn = QtWidgets.QPushButton("保存文件")
        self.saveSettingBtn.clicked.connect(
            lambda: self.save_preset(self.missionPresetDropdown.currentText())
        )

        self.loadSettingBtn = QtWidgets.QPushButton("加载文件")
        self.loadSettingBtn.clicked.connect(
            lambda: self.onLoadMissionPreset(self.missionPresetDropdown.currentText())
        )

        self.fAddButton = QtWidgets.QPushButton("新增任务")
        self.fAddButton.clicked.connect(self.add_empty_mission)

        self.missionRemoveButton = QtWidgets.QPushButton("删除任务")
        self.missionRemoveButton.connect(self.missionRemoveButton, QtCore.SIGNAL("clicked()"), self.remove_missions)
        self.newPresetButton = QtWidgets.QPushButton("另存为")

        self.newPresetTextEdit = QtWidgets.QLineEdit()

        self.newPresetButton.clicked.connect(
            lambda: self.save_as_new_preset(self.newPresetTextEdit.text())
        )
        self.missionPresetDropdownWidget = QtWidgets.QWidget()
        self.missionPresetDropdownLayout = QtWidgets.QHBoxLayout()
        self.missionPresetDropdownWidget.setLayout(self.missionPresetDropdownLayout)

        self.missionPresetDropdownLabel = QtWidgets.QLabel("预设列表")
        self.missionPresetDropdown = QtWidgets.QComboBox()
        self.missionPresetDropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        directory_path = "./configs/*.yaml"
        conf_files = glob.glob(directory_path)

        for file_path in conf_files:
            self.missionPresetDropdown.addItem(file_path)
            self.missionPresetDropdown.setCurrentIndex(0)
        self.missionPresetDropdownLayout.addWidget(self.missionPresetDropdownLabel)
        self.missionPresetDropdownLayout.addStretch()
        self.missionPresetDropdownLayout.addWidget(self.missionPresetDropdown)

        self.missionSettingSLWidget = QtWidgets.QWidget()
        self.missionSettingSLLayout = QtWidgets.QHBoxLayout()
        self.missionSettingSLWidget.setLayout(self.missionSettingSLLayout)
        self.missionSettingSLLayout.addWidget(self.loadSettingBtn)
        self.missionSettingSLLayout.addWidget(self.saveSettingBtn)

        self.missionSettingSaveAsWidget = QtWidgets.QWidget()
        self.missionSettingSaveAsLayout = QtWidgets.QHBoxLayout()
        self.missionSettingSaveAsWidget.setLayout(self.missionSettingSaveAsLayout)
        self.missionSettingSaveAsLayout.addWidget(self.newPresetButton)
        self.missionSettingSaveAsLayout.addWidget(self.newPresetTextEdit)
        self.missionSettingDifficultyWidget = QtWidgets.QWidget()
        self.missionSettingDifficultyLayout = QtWidgets.QHBoxLayout()
        self.missionSettingDifficultyWidget.setLayout(self.missionSettingDifficultyLayout)

        self.missionSettingDifficultyLabel = QtWidgets.QLabel("难度")
        self.missionSettingDifficultyDropdown = QtWidgets.QComboBox()
        self.missionSettingDifficultyDropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for mission in self.missionInfoList:
            if mission["id"] == self.editingMission.missionId:
                for difficulty in mission.difficulty:
                    self.missionSettingDifficultyDropdown.addItem(difficulty)
                self.missionSettingDifficultyDropdown.setCurrentIndex(0)
                break
        self.missionSettingDifficultyDropdown.currentIndexChanged.connect(
            lambda : self.onMissionDifficultyChanged(self.missionSettingDifficultyDropdown.currentText()))
        self.missionSettingDifficultyLayout.addWidget(self.missionSettingDifficultyLabel)
        self.missionSettingDifficultyLayout.addStretch()
        self.missionSettingDifficultyLayout.addWidget(self.missionSettingDifficultyDropdown)
        self.missionSettingButtonWidget = QtWidgets.QWidget()
        self.missionSettingButtonLayout = QtWidgets.QHBoxLayout()
        self.missionSettingButtonWidget.setLayout(self.missionSettingButtonLayout)
        self.missionSettingButtonLayout.addWidget(self.fAddButton)
        self.missionSettingButtonLayout.addWidget(self.missionRemoveButton)
        self.heroListToggleButton = QtWidgets.QPushButton("展开角色列表")
        self.heroListToggleButton.clicked.connect(self.toggleHeroListPanel)
        self.heroListText = QtWidgets.QLabel("角色列表")

        self.PPLeftPanelWidget = QtWidgets.QWidget()
        self.PPLeftPanelLayout = QtWidgets.QVBoxLayout()
        self.PPLeftPanelLayout.setSpacing(10)
        self.PPLeftPanelLayout.addWidget(self.flineEditsScrollArea)
        self.PPLeftPanelLayout.addWidget(self.missionSettingSLWidget)
        self.PPLeftPanelLayout.addWidget(self.missionSettingSaveAsWidget)

        self.PPLeftPanelLayout.addWidget(self.missionPresetDropdownWidget)
        self.PPLeftPanelLayout.addWidget(self.missionSettingButtonWidget)
        self.PPLeftPanelLayout.addWidget(self.heroListToggleButton)
        self.PPLeftPanelWidget.setLayout(self.PPLeftPanelLayout)

        self.heroListWidget = QtWidgets.QWidget()
        self.heroListGrid = QtWidgets.QGridLayout()
        self.heroListGrid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.heroListWidget.setLayout(self.heroListGrid)
        self.heroListScrollArea = QtWidgets.QScrollArea()
        self.heroListScrollArea.setWidget(self.heroListWidget)
        self.heroListScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.heroListScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.heroListScrollArea.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.heroListScrollArea.setWidgetResizable(True)
        self.heroListScrollArea.setObjectName("panel")

        self.charSelectionList = []
        self.selectedCharacterName = None
        self.heroListGridTitle = QtWidgets.QLabel("角色选择: ")
        for characterName in self.characterNameList:
            self.add_character_button(characterName)
        self.updateCharacterGridStatus()
        self.heroSettingAddButton = QtWidgets.QPushButton("新增角色")
        self.heroSettingAddButton.clicked.connect(self.add_empty_character)

        self.heroSettingClearButton = QtWidgets.QPushButton("清除选择")
        self.heroSettingClearButton.clicked.connect(self.clear_current_character_selection)

        self.heroSettingButtonWidget = QtWidgets.QWidget()
        self.heroSettingButtonLayout = QtWidgets.QHBoxLayout()
        self.heroSettingButtonWidget.setLayout(self.heroSettingButtonLayout)
        self.heroSettingButtonLayout.addWidget(self.heroSettingAddButton)
        self.heroSettingButtonLayout.addWidget(self.heroSettingClearButton)

        self.missionSettingLabel = QtWidgets.QLabel("关卡设置")
        self.missionSettingLabel.setProperty("role", "title")

        self.missionSettingWidget = QtWidgets.QWidget()
        self.missionSettingWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.missionSettingWidget.setObjectName("missionSetting")
        self.missionSettingLayout = QtWidgets.QVBoxLayout()
        self.missionSettingWidget.setLayout(self.missionSettingLayout)

        self.missionSettingAutoOrManuelWidget = QtWidgets.QWidget()
        self.missionSettingAutoOrManuelLayout = QtWidgets.QHBoxLayout()
        self.missionSettingAutoOrManuelWidget.setLayout(self.missionSettingAutoOrManuelLayout)

        self.missionSettingAutoOrManuelLabelWidget = QtWidgets.QLabel("代行模式")
        self.missionSettingAutoOrManuelSwitchWidget = QtWidgets.QCheckBox()
        self.missionSettingAutoOrManuelSwitchWidget.clicked.connect(self.updateAutoOrManuelStatus)

        self.missionSettingAutoOrManuelLayout.addWidget(self.missionSettingAutoOrManuelLabelWidget)
        self.missionSettingAutoOrManuelLayout.addStretch()
        self.missionSettingAutoOrManuelLayout.addWidget(self.missionSettingAutoOrManuelSwitchWidget)

        self.missionSettingFreeAutoWidget = QtWidgets.QWidget()
        self.missionSettingFreeAutoLayout = QtWidgets.QHBoxLayout()
        self.missionSettingFreeAutoWidget.setLayout(self.missionSettingFreeAutoLayout)

        self.missionSettingFreeAutoLabelWidget = QtWidgets.QLabel("使用免费代行")
        self.missionSettingFreeAutoSwitchWidget = QtWidgets.QCheckBox()
        self.missionSettingFreeAutoSwitchWidget.clicked.connect(self.updateFreeAutoStatus)

        self.missionSettingFreeAutoLayout.addWidget(self.missionSettingFreeAutoLabelWidget)
        self.missionSettingFreeAutoLayout.addStretch()
        self.missionSettingFreeAutoLayout.addWidget(self.missionSettingFreeAutoSwitchWidget)

        self.missionSettingAutoDeployWidget = QtWidgets.QWidget()
        self.missionSettingAutoDeployLayout = QtWidgets.QHBoxLayout()
        self.missionSettingAutoDeployWidget.setLayout(self.missionSettingAutoDeployLayout)

        self.missionSettingAutoDeployLabelWidget = QtWidgets.QLabel("自动上阵")
        self.missionSettingAutoDeploySwitchWidget = QtWidgets.QCheckBox()
        self.missionSettingAutoDeploySwitchWidget.clicked.connect(self.updateAutoDeployStatus)

        self.missionSettingAutoDeployLayout.addWidget(self.missionSettingAutoDeployLabelWidget)
        self.missionSettingAutoDeployLayout.addStretch()
        self.missionSettingAutoDeployLayout.addWidget(self.missionSettingAutoDeploySwitchWidget)

        self.missionSettingDefaultDifficultyWidget = QtWidgets.QWidget()
        self.missionSettingDefaultDifficultyLayout = QtWidgets.QHBoxLayout()
        self.missionSettingDefaultDifficultyWidget.setLayout(self.missionSettingDefaultDifficultyLayout)

        self.missionSettingDefaultDifficultyLabelWidget = QtWidgets.QLabel("默认难度")
        self.missionSettingDefaultDifficultySwitchWidget = QtWidgets.QCheckBox()
        self.missionSettingDefaultDifficultySwitchWidget.clicked.connect(self.updateDefaultDifficultyStatus)

        self.missionSettingDefaultDifficultyLayout.addWidget(self.missionSettingDefaultDifficultyLabelWidget)
        self.missionSettingDefaultDifficultyLayout.addStretch()
        self.missionSettingDefaultDifficultyLayout.addWidget(self.missionSettingDefaultDifficultySwitchWidget)

        self.missionSettingHighRewardWidget = QtWidgets.QWidget()
        self.missionSettingHighRewardLayout = QtWidgets.QHBoxLayout()
        self.missionSettingHighRewardWidget.setLayout(self.missionSettingHighRewardLayout)

        self.missionSettingHighRewardLabelWidget = QtWidgets.QLabel("高额优先")
        self.missionSettingHighRewardSwitchWidget = QtWidgets.QCheckBox()
        self.missionSettingHighRewardSwitchWidget.clicked.connect(self.updateHighRewardFirstStatus)

        self.missionSettingHighRewardLayout.addWidget(self.missionSettingHighRewardLabelWidget)
        self.missionSettingHighRewardLayout.addStretch()
        self.missionSettingHighRewardLayout.addWidget(self.missionSettingHighRewardSwitchWidget)

        self.missionSettingDifficultyWidget = QtWidgets.QWidget()
        self.missionSettingDifficultyLayout = QtWidgets.QHBoxLayout()
        self.missionSettingDifficultyWidget.setLayout(self.missionSettingDifficultyLayout)

        self.missionSettingDifficultyLabel = QtWidgets.QLabel("难度")
        self.missionSettingDifficultyDropdown = QtWidgets.QComboBox()
        self.missionSettingDifficultyDropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for mission in self.missionInfoList:
            if mission["id"] == self.editingMission.missionId:
                for difficulty in mission.difficulty:
                    self.missionSettingDifficultyDropdown.addItem(difficulty)
                self.missionSettingDifficultyDropdown.setCurrentIndex(0)
                break
        self.missionSettingDifficultyDropdown.currentIndexChanged.connect(
            lambda : self.onMissionDifficultyChanged(self.missionSettingDifficultyDropdown.currentText()))
        self.missionSettingDifficultyLayout.addWidget(self.missionSettingDifficultyLabel)
        self.missionSettingDifficultyLayout.addStretch()
        self.missionSettingDifficultyLayout.addWidget(self.missionSettingDifficultyDropdown)
        self.missionSettingMidMissionWidget = QtWidgets.QWidget()
        self.missionSettingMidMissionLayout = QtWidgets.QHBoxLayout()
        self.missionSettingMidMissionWidget.setLayout(self.missionSettingMidMissionLayout)

        self.missionSettingMidMissionLabel = QtWidgets.QLabel("分页")
        self.missionSettingMidMissionDropdown = QtWidgets.QComboBox()
        self.missionSettingMidMissionDropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for mission in self.missionInfoList:
            if mission["id"] == self.editingMission.missionId:
                for midMission in mission.midMission:
                    self.missionSettingMidMissionDropdown.addItem(midMission)
                self.missionSettingMidMissionDropdown.setCurrentIndex(0)
                break
        self.missionSettingMidMissionDropdown.currentIndexChanged.connect(
            lambda: self.onMissionMidMissionChanged(self.missionSettingMidMissionDropdown.currentText()))
        self.missionSettingMidMissionLayout.addWidget(self.missionSettingMidMissionLabel)
        self.missionSettingMidMissionLayout.addStretch()
        self.missionSettingMidMissionLayout.addWidget(self.missionSettingMidMissionDropdown)
        self.missionSettingFreeAutoSwitchWidget.setEnabled(False)
        self.missionSettingAutoOrManuelSwitchWidget.setEnabled(False)
        self.missionSettingAutoDeploySwitchWidget.setEnabled(False)
        self.missionSettingDefaultDifficultySwitchWidget.setEnabled(False)
        self.missionSettingHighRewardSwitchWidget.setEnabled(False)

        self.missionSettingLayout.addWidget(self.missionSettingAutoOrManuelWidget)
        self.missionSettingLayout.addWidget(self.missionSettingFreeAutoWidget)
        self.missionSettingLayout.addWidget(self.missionSettingAutoDeployWidget)
        self.missionSettingLayout.addWidget(self.missionSettingDefaultDifficultyWidget)
        self.missionSettingLayout.addWidget(self.missionSettingHighRewardWidget)
        self.missionSettingLayout.addWidget(self.missionSettingDifficultyWidget)
        self.missionSettingLayout.addWidget(self.missionSettingMidMissionWidget)
        self.missionSettingLayout.addStretch()

        self.PPMiddlePanelWidget = QtWidgets.QWidget()
        self.PPMiddlePanelLayout = QtWidgets.QVBoxLayout()
        self.PPMiddlePanelLayout.setSpacing(10)
        self.PPMiddlePanelLayout.addWidget(self.heroListText)
        self.PPMiddlePanelLayout.addWidget(self.heroListGridTitle)
        self.PPMiddlePanelLayout.addWidget(self.heroListScrollArea)
        self.PPMiddlePanelLayout.addWidget(self.heroSettingButtonWidget)
        self.PPMiddlePanelWidget.setLayout(self.PPMiddlePanelLayout)
        self.PPMiddlePanelWidget.setVisible(False)

        self.PPRightPanelWidget = QtWidgets.QWidget()
        self.PPRightPanelLayout = QtWidgets.QVBoxLayout()
        self.PPRightPanelLayout.setSpacing(10)
        self.PPRightPanelWidget.setLayout(self.PPRightPanelLayout)
        self.PPRightPanelLayout.addWidget(self.missionSettingLabel)
        self.PPRightPanelLayout.addWidget(self.missionSettingWidget)

        self.fixVideoTabLayout.addWidget(self.PPLeftPanelWidget, 1)
        self.fixVideoTabLayout.addWidget(self.PPMiddlePanelWidget, 1)
        self.fixVideoTabLayout.addWidget(self.PPRightPanelWidget, 1)



        self.tabSetting = QtWidgets.QWidget()
        self.tabSettingLayout = QtWidgets.QVBoxLayout()
        self.tabSettingLayout.setContentsMargins(16, 16, 16, 16)
        self.tabSettingLayout.setSpacing(12)
        self.tabFormLayout = QtWidgets.QFormLayout()
        self.tabSetting.setLayout(self.tabSettingLayout)

        self.adbDirTextEdit = QtWidgets.QLineEdit()
        self.connectionPortTextEdit = QtWidgets.QLineEdit()
        self.controlModeDropdown = QtWidgets.QComboBox()
        self.controlModeDropdown.addItems(["window", "adb"])
        self.windowTitleTextEdit = QtWidgets.QLineEdit()
        self.processNameTextEdit = QtWidgets.QLineEdit()
        self.baseResolutionTextEdit = QtWidgets.QLineEdit()
        self.ocrLanguageDropdown = QtWidgets.QComboBox()
        self.ocrLanguageDropdown.addItems(["ch_sim,en", "ch_tra,en"])

        self.isLoadingRuntimeSettings = True
        try:
            if os.path.exists('app_config.yaml'):
                with open('app_config.yaml', 'r', encoding='utf-8') as file:
                    config_data = yaml.safe_load(file)
                    config_lookup = {}
                    for item in config_data:
                        if isinstance(item, dict):
                            config_lookup.update(item)
                    self.adbDirTextEdit.setText(config_lookup.get('adbDir', ''))
                    self.connectionPortTextEdit.setText(config_lookup.get('connectionPort', ''))
                    self.controlModeDropdown.setCurrentText(
                        ADBClass.AdbSingleton.normalize_control_mode(config_lookup.get('controlMode', 'window'), 'window')
                    )
                    self.windowTitleTextEdit.setText(config_lookup.get('windowTitle', '铃兰'))
                    self.processNameTextEdit.setText(config_lookup.get('processName', 'SoC.exe'))
                    base_resolution = config_lookup.get('baseResolution', [1280, 720])
                    self.baseResolutionTextEdit.setText(f"{base_resolution[0]}x{base_resolution[1]}")
                    ocr_languages = config_lookup.get('ocrLanguages', ['ch_sim', 'en'])
                    self.ocrLanguageDropdown.setCurrentText(",".join(ocr_languages))
                    task_selection = config_lookup.get('taskSelection', {})
                    self.receiveRewardSubtasks = self.resolveReceiveRewardSubtasks(task_selection)
                    self.startAppCheckbox.setChecked(task_selection.get('startApp', False))
                    self.farmResCheckbox.setChecked(task_selection.get('farmResources', False))
                    self.receiveRewardCheckbox.setChecked(task_selection.get('receiveReward', False))
        finally:
            self.isLoadingRuntimeSettings = False


        self.tabFormLayout.addRow("控制模式", self.controlModeDropdown)
        self.tabFormLayout.addRow("窗口标题", self.windowTitleTextEdit)
        self.tabFormLayout.addRow("进程名", self.processNameTextEdit)
        self.tabFormLayout.addRow("基准分辨率", self.baseResolutionTextEdit)
        self.tabFormLayout.addRow("OCR语言", self.ocrLanguageDropdown)
        self.tabFormLayout.addRow("ADB路径", self.adbDirTextEdit)
        self.tabFormLayout.addRow("连接地址", self.connectionPortTextEdit)

        self.applySetting = QtWidgets.QPushButton("保存设置")
        self.applySetting.setObjectName("primaryButton")
        self.applySetting.clicked.connect(self.applySettingAction)
        self.settingActionRow = QtWidgets.QHBoxLayout();
        self.settingActionRow.addWidget(self.applySetting)
        self.tabSettingLayout.addLayout(self.tabFormLayout)
        self.tabSettingLayout.addLayout(self.settingActionRow)
        self.tabs.addTab(self.tab1, "一键刷资源")
        self.tabs.addTab(self.fixVideoTabWidget, "刷图流程")
        self.tabs.addTab(self.tabSetting, "设置")
        self.tabs.currentChanged.connect(self.onTabChanged)

        self.setCentralWidget(self.tabs)

        self.setWindowTitle("铃兰一条龙")
        self.resize(1100, 640)

        self.initMissions()
        self.timer = QtCore.QTimer()
        self.timer.start(1000)

        # 日志文件由流程线程写入，UI 定时增量读取，避免后台任务直接操作界面控件。
        self.timer_log = QTimer()
        self.timer_log.timeout.connect(self.monitor_log)
        self.timer_log.start(1000)

    def monitor_log(self):
        file_path = 'logs\\log_test.txt'
        monitor = Monitor(file_path, self.lastReadPtr)
        newText = monitor.check()
        self.lastReadPtr = newText[1]
        if len(newText[0]) > 0:
            self.logText.append(newText[0])

    def toggleHeroListPanel(self):
        is_visible = self.PPMiddlePanelWidget.isVisible()
        self.PPMiddlePanelWidget.setVisible(not is_visible)
        self.heroListToggleButton.setText("收起角色列表" if not is_visible else "展开角色列表")

    def autoSaveMissions(self):
        if getattr(self, "isLoadingMissions", False):
            return
        if not hasattr(self, "scheduleMissionList"):
            return
        # 任务编辑控件是即时保存模式，避免用户切页或直接启动时丢失当前配置。
        OctoUtil.OctoUtil.parse_mission_to_preset_yaml(self.scheduleMissionList, '.\\active_config.yaml')

    def onTabChanged(self, index):
        if getattr(self, "isLoadingRuntimeSettings", False):
            return
        self.saveRuntimeSettings()

    def initMissionCheckRepeated(self, config_data, missionId, past_mission):
        for mission in list(config_data[0]['LevelAutomation'].keys()):
            if (missionId in mission) and (mission not in past_mission):
                missionId = mission
                break
            if mission == list(config_data[0]['LevelAutomation'].keys())[-1]:
                return (False, missionId)
        return (True, missionId)
    def initMissions(self):
        self.loadMissionsPreset('.\\active_config.yaml')
        self.updateCharacterGridStatus()

    def loadMissionsPreset(self, presetFileName):
        self.isLoadingMissions = True
        try:
            with open(presetFileName, 'r', encoding='utf-8') as configfile:
                config_data = yaml.safe_load(configfile)
            self.scheduleMissionList.clear()
            self.mission.clear()
            while self.flineEditsVbox.count():
                child = self.flineEditsVbox.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            for shortFormMissionId, missionId, missionConfig in self.resolvePresetMissionEntries(config_data):
                characters = missionConfig.get("characters", "")
                isAuto = missionConfig.get("isAuto", True)
                isFreeAuto = missionConfig.get("isFreeAuto", False)
                autoDeploy = missionConfig.get("autoDeploy", False)
                defaultDifficulty = missionConfig.get("defaultDifficulty", False)
                highRewardFirst = missionConfig.get("highRewardFirst", False)
                mission = scheduleMission.ConfigInit(shortFormMissionId, isAuto, isFreeAuto, characters.split(','), autoDeploy, defaultDifficulty, highRewardFirst)
                newMissionRowWidget = QtWidgets.QWidget()
                newMissionRowLayout = QtWidgets.QHBoxLayout()
                newMissionRowWidget.setLayout(newMissionRowLayout)

                dropdown = QtWidgets.QComboBox()
                dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

                for missionName in self.missionNameList:
                    dropdown.addItem(missionName)
                dropdown.setCurrentIndex(mission.missionArrIndex)

                setting_button = QPushButton()
                setting_button.setProperty("list-button", True)
                setting_button.setIcon(QIcon("setting_icon.png"))
                setting_button.setStyleSheet(LIST_BUTTON_STYLE)
                mission.missionBtn = setting_button
                mission.missionRow = newMissionRowWidget

                self.scheduleMissionList.append(mission)
                dropdown.currentIndexChanged.connect(
                    lambda _targetMissionId=dropdown.currentText(), _mission=mission: self.onMissionIdChanged(
                        _targetMissionId, _mission))
                setting_button.connect(setting_button, QtCore.SIGNAL("clicked()"),
                                       lambda _missionId=mission.id: self.selectMissionEdit(_missionId))

                newMissionRowLayout.addWidget(dropdown)
                newMissionRowLayout.addWidget(setting_button)
                self.mission.append(newMissionRowWidget)
                self.flineEditsVbox.addWidget(newMissionRowWidget)
                self.updateCharacterGridStatus()

            if self.scheduleMissionList:
                self.selectMissionEdit(self.scheduleMissionList[0].id)
            else:
                self.editingMission = scheduleMission.UIInit(None)
                self.updateCharacterGridStatus()
        finally:
            self.isLoadingMissions = False

    def stripDuplicateMissionSuffix(self, missionId):
        match = re.match(r'^(.*_\d{2})_\d+$', missionId)
        if match:
            return match.group(1)
        return missionId

    def resolvePresetMissionEntries(self, config_data):
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
                # 同一关卡可以在预设里重复出现，保存时会追加 _1/_2；这里按顺序还原。
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

    def onFlowFinished(self):
        self.thread_pool = []
    def startMainFlow(self, taskCheckBoxArray):
        self.saveRuntimeSettings()
        for thread in getattr(self, "thread_pool", []):
            if thread.isRunning():
                LoggerSingleton.getInstance().info('./logs/log_test.txt', "已有流程正在运行，请先停止或等待结束")
                return

        file_path = 'logs\\log_test.txt'

        with open(file_path, 'w') as file:
            file.truncate(0)
        self.lastReadPtr = 0
        ADBClass.AdbSingleton.getInstance().resetStop()
        LoggerSingleton.getInstance().info('./logs/log_test.txt', "开始执行流程")

        # 自动化流程放进独立 QThread，主线程只负责 Qt 界面响应。
        thread_pool = QThreadPool.globalInstance()
        thread_pool.setMaxThreadCount(1)
        self.thread_pool = []
        self.MainFlow = self.constructFlow(taskCheckBoxArray)
        flowThread = FlowThread(self.MainFlow)
        flowThread.finished.connect(self.onFlowFinished)
        flowThread.start()
        self.thread_pool.append(flowThread)

    def stopMainFlow(self):
        if not getattr(self, "thread_pool", None):
            LoggerSingleton.getInstance().info('./logs/log_test.txt', "停止：当前没有运行中的流程")
            return
        LoggerSingleton.getInstance().info('./logs/log_test.txt', "停止：已请求停止流程")
        ADBClass.AdbSingleton.getInstance().requestStop()
        for thread in self.thread_pool:
            if thread.isRunning():
                thread.requestInterruption()
                if not thread.wait(1000):
                    LoggerSingleton.getInstance().info('./logs/log_test.txt', "正在停止流程，请稍候")
                    return
        self.thread_pool = []
        LoggerSingleton.getInstance().info('./logs/log_test.txt', "停止：流程已结束")

    def defaultReceiveRewardSubtasks(self):
        return dict(REWARD_SUBTASK_DEFAULTS)

    def resolveReceiveRewardSubtasks(self, task_selection):
        reward_subtasks = self.defaultReceiveRewardSubtasks()
        if not isinstance(task_selection, dict):
            return reward_subtasks

        configured_subtasks = task_selection.get('receiveRewardSubtasks', {})
        if isinstance(configured_subtasks, dict):
            for key in REWARD_SUBTASK_DEFAULTS:
                if key in configured_subtasks:
                    reward_subtasks[key] = bool(configured_subtasks[key])

        flat_key_map = {
            'rewardDaily': 'daily',
            'rewardExploration': 'exploration',
            'rewardFriend': 'friend',
            'rewardVoyage': 'voyage',
        }
        for flat_key, subtask_key in flat_key_map.items():
            if flat_key in task_selection:
                reward_subtasks[subtask_key] = bool(task_selection[flat_key])

        return reward_subtasks

    def getReceiveRewardSubtasks(self):
        if not hasattr(self, "receiveRewardSubtasks"):
            self.receiveRewardSubtasks = self.defaultReceiveRewardSubtasks()
        return self.resolveReceiveRewardSubtasks({
            'receiveRewardSubtasks': self.receiveRewardSubtasks
        })

    def buildTaskSelection(self):
        return {
            'startApp': self.startAppCheckbox.isChecked(),
            'farmResources': self.farmResCheckbox.isChecked(),
            'receiveReward': self.receiveRewardCheckbox.isChecked(),
            'receiveRewardSubtasks': self.getReceiveRewardSubtasks(),
        }

    def openReceiveRewardSettings(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("领取奖励设置")
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(QtWidgets.QLabel("选择脚本需要领取的奖励："))

        current_subtasks = self.getReceiveRewardSubtasks()
        checkbox_map = {}
        for key, label in REWARD_SUBTASK_LABELS.items():
            checkbox = QCheckBox(label, dialog)
            checkbox.setChecked(current_subtasks.get(key, REWARD_SUBTASK_DEFAULTS[key]))
            checkbox_map[key] = checkbox
            layout.addWidget(checkbox)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            dialog
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self.receiveRewardSubtasks = {
                key: checkbox.isChecked()
                for key, checkbox in checkbox_map.items()
            }
            self.saveTaskSelection()

    def saveTaskSelection(self):
        if not hasattr(self, "startAppCheckbox"):
            return
        if getattr(self, "isLoadingRuntimeSettings", False):
            return
        if os.path.exists('app_config.yaml'):
            with open('app_config.yaml', 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file) or []
        else:
            data = []

        runtime_config = None
        for item in data:
            if isinstance(item, dict) and 'controlMode' in item:
                runtime_config = item
                break
        if runtime_config is None:
            runtime_config = {}
            data.append(runtime_config)

        runtime_config['taskSelection'] = self.buildTaskSelection()

        with open('app_config.yaml', 'w', encoding='utf-8') as file:
            yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)

    def saveRuntimeSettings(self):
        if os.path.exists('app_config.yaml'):
            with open('app_config.yaml', 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file) or []
        else:
            data = []

        if len(data) < 1 or not isinstance(data[0], dict):
            data.insert(0, {})
        if len(data) < 2 or not isinstance(data[1], dict):
            data.insert(1, {})

        data[0]['adbDir'] = self.adbDirTextEdit.text()
        data[1]['connectionPort'] = self.connectionPortTextEdit.text()

        runtime_config = None
        for item in data:
            if isinstance(item, dict) and 'controlMode' in item:
                runtime_config = item
                break
        if runtime_config is None:
            runtime_config = {}
            data.append(runtime_config)

        base_resolution_text = self.baseResolutionTextEdit.text().lower().replace(" ", "")
        try:
            base_width, base_height = [int(value) for value in base_resolution_text.split("x", 1)]
        except ValueError:
            base_width, base_height = 1280, 720
            self.baseResolutionTextEdit.setText("1280x720")

        runtime_config['controlMode'] = ADBClass.AdbSingleton.normalize_control_mode(
            self.controlModeDropdown.currentText(), 'window'
        )
        runtime_config['windowTitle'] = self.windowTitleTextEdit.text()
        runtime_config['processName'] = self.processNameTextEdit.text()
        runtime_config['baseResolution'] = [base_width, base_height]
        runtime_config['ocrLanguages'] = self.ocrLanguageDropdown.currentText().split(',')
        runtime_config['taskSelection'] = self.buildTaskSelection()

        with open('app_config.yaml', 'w', encoding='utf-8') as file:
            yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)

    def updateFreeAutoStatus(self):
        self.editingMission.freeAuto = self.missionSettingFreeAutoSwitchWidget.isChecked()
        self.autoSaveMissions()
    def updateAutoOrManuelStatus(self):
        self.editingMission.auto = self.missionSettingAutoOrManuelSwitchWidget.isChecked()
        self.autoSaveMissions()
    def updateAutoDeployStatus(self):
        self.editingMission.autoDeploy = self.missionSettingAutoDeploySwitchWidget.isChecked()
        self.autoSaveMissions()
    def updateDefaultDifficultyStatus(self):
        self.editingMission.defaultDifficulty = self.missionSettingDefaultDifficultySwitchWidget.isChecked()
        self.missionSettingDifficultyDropdown.setEnabled(not self.editingMission.defaultDifficulty)
        self.missionSettingMidMissionDropdown.setEnabled(True)
        self.autoSaveMissions()
    def updateHighRewardFirstStatus(self):
        self.editingMission.highRewardFirst = self.missionSettingHighRewardSwitchWidget.isChecked()
        self.autoSaveMissions()
    def constructFlow(self, taskCheckBoxArray):
        self.MainFlow = []
        if taskCheckBoxArray[0]:
            StartAppWf = runStartApp(self.adbDirTextEdit.text(),self.connectionPortTextEdit.text())
            self.MainFlow.append(StartAppWf)
        if taskCheckBoxArray[1]:
            mainMaterialWf = mainMaterial(self.adbDirTextEdit.text(),self.connectionPortTextEdit.text())
            self.MainFlow.append(mainMaterialWf)
        if taskCheckBoxArray[2]:
            receiveRewardWf = receiveReward(
                self.adbDirTextEdit.text(),
                self.connectionPortTextEdit.text(),
                self.getReceiveRewardSubtasks()
            )
            self.MainFlow.append(receiveRewardWf)
        return self.MainFlow

    def applySettingAction(self):
        self.saveRuntimeSettings()

    def add_empty_mission(self):
        newMissionRowWidget = QtWidgets.QWidget()
        newMissionRowLayout = QtWidgets.QHBoxLayout()
        newMissionRowWidget.setLayout(newMissionRowLayout)

        dropdown = QtWidgets.QComboBox()
        dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for missionName in self.missionNameList:
            dropdown.addItem(missionName)
        dropdown.setCurrentIndex(0)

        setting_button = QPushButton()
        setting_button.setProperty("list-button", True)
        setting_button.setIcon(QIcon("setting_icon.png"))
        setting_button.setStyleSheet(LIST_BUTTON_STYLE)
        newMission = scheduleMission.UIInit(dropdown.currentText(), setting_button, newMissionRowWidget)
        self.scheduleMissionList.append(newMission)
        dropdown.currentIndexChanged.connect(lambda _targetMissionId=dropdown.currentText(), _mission=newMission: self.onMissionIdChanged(
                             _targetMissionId, _mission))
        setting_button.connect(setting_button, QtCore.SIGNAL("clicked()"), lambda _missionId=newMission.id: self.selectMissionEdit(_missionId))

        newMissionRowLayout.addWidget(dropdown)
        newMissionRowLayout.addWidget(setting_button)
        self.mission.append(newMissionRowWidget)
        self.flineEditsVbox.addWidget(newMissionRowWidget)
        self.updateCharacterGridStatus()
        self.autoSaveMissions()

    def onMissionIdChanged(self, _missionId, _mission):
        _mission.setMission(_missionId)
        self.selectMissionEdit(_mission.id)
        self.updateCharacterGridStatus()
        self.autoSaveMissions()

    def onMissionDifficultyChanged(self, _targetDifficulty):
        self.editingMission.setDifficulty(_targetDifficulty)
        for mission in self.scheduleMissionList:
            if mission.id == self.editingMission.id:
                mission.setDifficulty(int(_targetDifficulty))

        self.updateCharacterGridStatus()
        self.autoSaveMissions()
    def onLoadMissionPreset(self, _targetPreset):
        self.loadMissionsPreset(_targetPreset)

        self.updateCharacterGridStatus()
        self.autoSaveMissions()

    def onMissionMidMissionChanged(self, _targetMidMission):
        self.editingMission.setMidMission(_targetMidMission)
        for mission in self.scheduleMissionList:
            if mission.id == self.editingMission.id:
                mission.setMidMission(_targetMidMission)

        self.updateCharacterGridStatus()

    def add_character_button(self, character):
        row = int(len(self.charSelectionList) / 3)
        col = len(self.charSelectionList) % 3
        charBtn = QtWidgets.QPushButton(character)
        self.heroListGrid.addWidget(charBtn, row, col)
        self.charSelectionList.append(charBtn)
        charBtn.clicked.connect(lambda checked=False, _character=character, _btn=charBtn: self.selectCharacter(_character, _btn))
        charBtn.setStyleSheet(LIST_BUTTON_STYLE)
        return charBtn

    def save_character_list(self):
        if not os.path.exists('app_config.yaml'):
            return
        with open('app_config.yaml', 'r', encoding='utf-8') as file:
            config_data = yaml.safe_load(file) or []
        for item in config_data:
            if isinstance(item, dict) and "characterList" in item:
                item["characterList"] = self.characterNameList
                break
        with open('app_config.yaml', 'w', encoding='utf-8') as file:
            yaml.safe_dump(config_data, file, allow_unicode=True, sort_keys=False)

    def add_empty_character(self):
        character, ok = QtWidgets.QInputDialog.getText(self, "新增角色", "角色名称")
        character = character.strip()
        if not ok or character == "":
            return
        if character in self.characterNameList:
            return
        self.characterNameList.append(character)
        self.add_character_button(character)
        self.save_character_list()
        self.updateCharacterGridStatus()

    def clear_current_character_selection(self):
        if self.editingMission.missionName == "None":
            return
        self.editingMission.characterList.clear()
        self.selectedCharacterName = None
        self.updateCharacterGridStatus()
        self.autoSaveMissions()

    def selectMissionEdit(self, missionId):
        for mission in self.scheduleMissionList:

            if mission.id == missionId:
                self.editingMission = mission
                self.updateCharacterGridStatus()

                for missionInfo in self.missionInfoList:
                    if missionInfo['id'] == self.editingMission.missionId:
                        self.missionSettingDifficultyDropdown.blockSignals(True)
                        self.missionSettingDifficultyDropdown.clear()

                        for difficulty in missionInfo["difficultyCount"]:
                            self.missionSettingDifficultyDropdown.addItem(str(difficulty))
                        self.missionSettingDifficultyDropdown.setCurrentIndex(mission.allDifficulty.index(mission.difficulty))
                        self.missionSettingDifficultyDropdown.blockSignals(False)

                        # 切换当前任务时同步刷新分页和难度下拉框，避免编辑状态指向旧任务。
                        self.missionSettingMidMissionDropdown.blockSignals(True)
                        self.missionSettingMidMissionDropdown.clear()

                        for middleLevel in missionInfo["middleLevel"]:
                            self.missionSettingMidMissionDropdown.addItem(str(middleLevel))
                        if len(mission.allMidMission) > 0:
                            self.missionSettingMidMissionDropdown.setCurrentIndex(
                                mission.allMidMission.index(mission.midMission)
                            )
                        self.missionSettingMidMissionDropdown.blockSignals(False)
                        break

                break

    def selectCharacter(self, character, btn: QPushButton):
        self.selectedCharacterName = character
        if character not in self.editingMission.characterList:
            self.editingMission.characterList.append(character)
            btn.setStyleSheet(SELECTED_BUTTON_STYLE)
        else:
            self.editingMission.characterList.remove(character)
            btn.setStyleSheet(LIST_BUTTON_STYLE)
        self.updateCharacterGridStatus()
        self.autoSaveMissions()
    def updateCharacterGridStatus(self):
        if self.editingMission.missionName == "None":
            for btn in self.charSelectionList:
                btn.setEnabled(False)
            self.missionRemoveButton.setEnabled(False)
            if hasattr(self, "heroSettingClearButton"):
                self.heroSettingClearButton.setEnabled(False)
            if hasattr(self, "missionSettingAutoDeploySwitchWidget"):
                self.missionSettingAutoDeploySwitchWidget.setEnabled(False)
            if hasattr(self, "missionSettingDefaultDifficultySwitchWidget"):
                self.missionSettingDefaultDifficultySwitchWidget.setEnabled(False)
            if hasattr(self, "missionSettingHighRewardSwitchWidget"):
                self.missionSettingHighRewardSwitchWidget.setEnabled(False)
            if hasattr(self, "missionSettingDifficultyDropdown"):
                self.missionSettingDifficultyDropdown.setEnabled(False)
            if hasattr(self, "missionSettingMidMissionDropdown"):
                self.missionSettingMidMissionDropdown.setEnabled(False)
        else:
            isFull = self.editingMission.maxCharCount >= 0 and len(self.editingMission.characterList) >= self.editingMission.maxCharCount
            maxCharCountText = str(self.editingMission.maxCharCount) if self.editingMission.maxCharCount >= 0 else "不限"
            self.heroListGridTitle.setText("角色选择: " + str(len(self.editingMission.characterList)) + "/"+ maxCharCountText)
            self.missionRemoveButton.setEnabled(True)
            for btn in self.charSelectionList:
                btn.setEnabled(True)
                if btn.text() in self.editingMission.characterList:
                    btn.setStyleSheet(SELECTED_BUTTON_STYLE)
                else:
                    btn.setStyleSheet(LIST_BUTTON_STYLE)
                    if isFull:
                        btn.setEnabled(False)
                for mission in self.scheduleMissionList:
                    if mission.id != self.editingMission.id:
                        if btn.text() in mission.characterList:
                            btn.setEnabled(False)
            for mission in self.scheduleMissionList:
                if mission.id == self.editingMission.id:
                    mission.missionBtn.setStyleSheet(SELECTED_BUTTON_STYLE)
                else:
                    mission.missionBtn.setStyleSheet(LIST_BUTTON_STYLE)
            self.missionSettingFreeAutoSwitchWidget.setEnabled(True)
            self.missionSettingAutoOrManuelSwitchWidget.setEnabled(True)
            if hasattr(self, "missionSettingAutoDeploySwitchWidget"):
                self.missionSettingAutoDeploySwitchWidget.setEnabled(True)
            if hasattr(self, "missionSettingDefaultDifficultySwitchWidget"):
                self.missionSettingDefaultDifficultySwitchWidget.setEnabled(True)
            if hasattr(self, "missionSettingHighRewardSwitchWidget"):
                self.missionSettingHighRewardSwitchWidget.setEnabled(True)
            if hasattr(self, "heroSettingClearButton"):
                self.heroSettingClearButton.setEnabled(True)
            self.missionSettingFreeAutoSwitchWidget.setChecked(self.editingMission.freeAuto)
            self.missionSettingAutoOrManuelSwitchWidget.setChecked(self.editingMission.auto)
            if hasattr(self, "missionSettingAutoDeploySwitchWidget"):
                self.missionSettingAutoDeploySwitchWidget.setChecked(self.editingMission.autoDeploy)
            if hasattr(self, "missionSettingDefaultDifficultySwitchWidget"):
                self.missionSettingDefaultDifficultySwitchWidget.setChecked(self.editingMission.defaultDifficulty)
            if hasattr(self, "missionSettingHighRewardSwitchWidget"):
                self.missionSettingHighRewardSwitchWidget.setChecked(self.editingMission.highRewardFirst)
            if hasattr(self, "missionSettingDifficultyDropdown"):
                self.missionSettingDifficultyDropdown.setEnabled(not self.editingMission.defaultDifficulty)
            if hasattr(self, "missionSettingMidMissionDropdown"):
                self.missionSettingMidMissionDropdown.setEnabled(True)
    def remove_missions(self):
        for mission in self.scheduleMissionList:
            if mission.id == self.editingMission.id:
                self.editingMission.missionRow.deleteLater()
                self.scheduleMissionList.remove(mission)
                if len(self.scheduleMissionList) > 0:
                    self.editingMission = self.scheduleMissionList[0]
                else:
                    self.editingMission = scheduleMission.UIInit(None)
                self.updateCharacterGridStatus()
                self.autoSaveMissions()
                break
    def save_missions(self):
        filename = f'.\\active_config.yaml'
        OctoUtil.OctoUtil.parse_mission_to_preset_yaml(self.scheduleMissionList, filename)
    def save_preset(self, fileName):
        OctoUtil.OctoUtil.parse_mission_to_preset_yaml(self.scheduleMissionList, fileName)

    def save_as_new_preset(self, filename):
        filename = f'.\\configs\\{filename}.yaml'
        OctoUtil.OctoUtil.parse_mission_to_preset_yaml(self.scheduleMissionList, filename)


