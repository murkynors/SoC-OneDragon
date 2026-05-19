import os
import random

import yaml

from soc_one_dragon.utils import image_tools as OctoUtil


class scheduleMission:
    @classmethod
    def ConfigInit(cls, fullId, auto, freeAuto, characterList, autoDeploy=False, defaultDifficulty=False, highRewardFirst=False):
        allMissionList = []
        missionId = None
        difficulty = None
        midMission = None
        if characterList == ['']:
            characterList = []
        with open('app_config.yaml', 'r', encoding='utf-8') as keyconfigfile:
            keyconfig_data = yaml.safe_load(keyconfigfile)
            allMissionList = keyconfig_data[4]["missionInfo"]
        for mission in allMissionList:
             if mission["id"] in fullId:
                missionId = mission["id"]
                missionName = mission["name"]
                allMiddleMission = mission["middleLevel"]
                allDifficulty = mission["difficultyCount"]
                missionArrIndex = allMissionList.index(mission)

                difficulty = fullId.replace(mission["id"], "")
                if OctoUtil.OctoUtil.check_string(difficulty) is True:
                    full_suffix = difficulty.split("_")
                    midMission = full_suffix[0]
                    difficulty = int(full_suffix[1])
                else:
                    difficulty = int(difficulty.lstrip("_"))
                    midMission = None

                if difficulty not in allDifficulty:
                    difficulty = allDifficulty[-1]
                difficultyInfoArrIndex = allDifficulty.index(difficulty)
                allDifficultyCharCount = mission["difficultyAutoCharCount"]
                if len(allDifficultyCharCount) == 1:
                    maxCharCount = allDifficultyCharCount[0]
                else:
                    maxCharCount = allDifficultyCharCount[difficultyInfoArrIndex]
                _id = random.randint(0, 100000)

        return cls(missionId, missionName, midMission, difficulty, auto, freeAuto, autoDeploy, defaultDifficulty, highRewardFirst, _id, characterList, maxCharCount, allMissionList, allDifficultyCharCount, allDifficulty, allMiddleMission, missionArrIndex)

    @classmethod
    def UIInit(cls, missionParam, missionBtn=None, missionRow=None):
        allMissionList = []
        allDifficultyCharCount = []
        allDifficulty = []
        allMidMission = []
        missionArrIndex = None
        if os.path.exists('app_config.yaml'):
            with open('app_config.yaml', 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
                allMissionList = config_data[4]["missionInfo"]
        if missionParam is not None:
            if isinstance(missionParam, str):
                missionName = missionParam
                for mission in allMissionList:
                    if mission["name"] == missionParam:
                        missionId = mission["id"]
                        missionArrIndex = allMissionList.index(mission)
                        allDifficultyCharCount = mission["difficultyAutoCharCount"]
                        allDifficulty = mission["difficultyCount"]
                        allMidMission = mission["middleLevel"]
            elif isinstance(missionParam, int):
                missionId = allMissionList[missionParam]['id']
                missionArrIndex = missionParam
                missionName = allMissionList[missionParam]['name']
                allDifficultyCharCount = allMissionList[missionParam]["difficultyAutoCharCount"]
                allDifficulty = allMissionList[missionParam]["difficultyCount"]
                allMidMission = allMissionList[missionParam]["middleLevel"]
            else:
                raise TypeError("missionParam must be mission name or mission index")
        else:
            missionName = "None"
            missionId = -1
        missionBtn = missionBtn
        missionRow = missionRow
        difficulty = 1
        midMission = ""
        maxCharCount = 1
        if missionName != "None":
            maxCharCount = allDifficultyCharCount[allDifficulty.index(difficulty)]
        characterList = []
        auto = True
        freeAuto = False
        autoDeploy = False
        defaultDifficulty = False
        highRewardFirst = False
        _id = random.randint(0, 100000)
        return cls(missionId, missionName, midMission, difficulty, auto, freeAuto, autoDeploy, defaultDifficulty, highRewardFirst, _id, characterList, maxCharCount, allMissionList, allDifficultyCharCount, allDifficulty, allMidMission, missionArrIndex, missionBtn, missionRow)

    def __init__(self, missionId, missionName, midMission, difficulty, auto, freeAuto, autoDeploy, defaultDifficulty, highRewardFirst, _id, characterList, maxCharCount, allMissionList, allDifficultyCharCount, allDifficulty, allMidMission, missionArrIndex, missionBtn=None, missionRow=None):
        self.missionId = missionId
        self.missionName = missionName
        self.midMission = midMission
        self.difficulty = int(difficulty)
        self.auto = auto
        self.freeAuto = freeAuto
        self.autoDeploy = autoDeploy
        self.defaultDifficulty = defaultDifficulty
        self.highRewardFirst = highRewardFirst
        self.id = _id
        self.characterList = characterList
        self.maxCharCount = maxCharCount
        self.missionArrIndex = missionArrIndex
        self.missionBtn = missionBtn
        self.missionRow = missionRow
        self.allMissionList = allMissionList
        self.allDifficultyCharCount = allDifficultyCharCount
        self.allDifficulty = allDifficulty
        self.allMidMission = allMidMission

    def setDifficulty(self, difficulty):
        self.difficulty = int(difficulty)
        difficultyIndex = self.allDifficulty.index(self.difficulty)
        if len(self.allDifficultyCharCount) == 1:
            self.maxCharCount = self.allDifficultyCharCount[0]
        else:
            self.maxCharCount = self.allDifficultyCharCount[difficultyIndex]
        if self.maxCharCount >= 0 and len(self.characterList) > self.maxCharCount:
            self.characterList = self.characterList[:self.maxCharCount]

    def setMidMission(self, midMission):
        self.midMission = midMission

    def setMission(self, missionParam):
        if missionParam is not None:
            if isinstance(missionParam, str):
                self.missionName = missionParam
                for mission in self.allMissionList:
                    if mission["name"] == missionParam:
                        self.missionId = mission["id"]
                        self.missionArrIndex = self.allMissionList.index(mission)
                        self.allDifficultyCharCount = mission["difficultyAutoCharCount"]
                        self.allDifficulty = mission["difficultyCount"]
                        self.allMidMission = mission["middleLevel"]
            elif isinstance(missionParam, int):
                self.missionId = self.allMissionList[missionParam]['id']
                self.missionArrIndex = missionParam
                self.missionName = self.allMissionList[missionParam]['name']
                self.allDifficultyCharCount = self.allMissionList[missionParam]["difficultyAutoCharCount"]
                self.allDifficulty = self.allMissionList[missionParam]["difficultyCount"]
                self.allMidMission = self.allMissionList[missionParam]["middleLevel"]

            else:
                raise TypeError("missionParam must be mission name or mission index")
            if self.difficulty in self.allDifficulty:
                difficultyIndex = self.allDifficulty.index(self.difficulty)
                self.difficulty = self.allDifficulty[difficultyIndex]
                if len(self.allDifficultyCharCount) == 1:
                    self.maxCharCount = self.allDifficultyCharCount[0]
                else:
                    self.maxCharCount = self.allDifficultyCharCount[difficultyIndex]
            else:
                self.difficulty = self.allDifficulty[0]
                if len(self.allDifficultyCharCount) == 1:
                    self.maxCharCount = self.allDifficultyCharCount[0]
                else:
                    self.maxCharCount = self.allDifficultyCharCount[self.allDifficulty.index(self.difficulty)]

            if self.midMission in self.allMidMission:
                midMissionIndex = self.allMidMission.index(self.midMission)
                self.midMission = self.allMidMission[midMissionIndex]
            else:
                if len(self.allMidMission) > 0:
                    self.midMission = self.allMidMission[0]
                else:
                    self.midMission = ""
