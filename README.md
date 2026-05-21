# SoC One Dragon

铃兰之剑自动化辅助

铃兰之剑收菜很痛苦，找找git有带佬写过辅助，拿来自己改改AI改改适配了简中新版，因为我是老咸鱼，所以只适合给老咸鱼收菜，嗷儿

目前支持日常刷图，日常奖励，荣耀之战，每周爬塔

## 使用说明

分辨率限定1280x720。

默认使用adb连接模拟器进行后台操作。

window模式(连接官方windows客户端前台操作)仍在完善中，需要使用管理员启动辅助，游戏窗口不能最小化，不能放在边界外。

## 运行

进入本目录后：

```bash
uv sync
uv run python run.py
```

## 目录说明

```text
soc_one_dragon/
├── run.py                    # 独立启动入口
├── app.py                    # Qt 初始化、工作目录切换
├── app_config.yaml           # 全局配置
├── active_config.yaml        # 当前刷图任务配置
├── Icons/                    # OpenCV 模板素材
├── configs/                  # 任务预设
├── img/                      # 运行截图输出
├── logs/                     # 日志输出
├── res/ / ocr/               # OCR 模型与字典资源
├── ui/                       # 主窗口、样式、后台线程和日志监视
├── models/                   # 任务数据模型
├── workflows/                # 唤醒、刷图、领奖等流程
├── device/                   # ADB/window 控制
├── services/                 # OCR、日志服务
├── utils/                    # 图像匹配和配置写入工具
└── flow/                     # 流程节点框架
```

## 维护入口

- 改界面：优先看 `ui/main_window.py` 和 `ui/styles.py`。
- 改任务数据结构：优先看 `models/scheduled_mission.py`。
- 改执行流程：优先看 `workflows/`。
- 改截图、模板匹配、配置写入：优先看 `utils/image_tools.py`。
- 改设备控制：优先看 `device/adb_controller.py`。

## 注意

`Icons/` 下的文件名仍被流程代码直接引用，替换素材时尽量保持文件名不变。运行产生的 `img/` 和 `logs/` 可以清理，不影响程序下次启动。


## 声明

本项目基于[EzyAssistanceSS](https://github.com/KiraEzy/EzyAssistanceSS)开发，感谢开源



