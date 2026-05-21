import subprocess
import time
from pathlib import Path

import yaml

from soc_one_dragon.services.logger import LoggerSingleton


def _set_process_dpi_awareness():
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception as exc:
        print("set dpi awareness failed:", exc)


_set_process_dpi_awareness()


class NativeWindow:
    def __init__(self, hwnd):
        self.hwnd = hwnd

    @property
    def title(self):
        import win32gui

        return win32gui.GetWindowText(self.hwnd)

    @property
    def left(self):
        return self._rect()[0]

    @property
    def top(self):
        return self._rect()[1]

    @property
    def width(self):
        left, top, right, bottom = self._rect()
        return right - left

    @property
    def height(self):
        left, top, right, bottom = self._rect()
        return bottom - top

    @property
    def isMinimized(self):
        import win32gui

        return bool(win32gui.IsIconic(self.hwnd))

    @property
    def isVisible(self):
        import win32gui

        return bool(win32gui.IsWindowVisible(self.hwnd))

    def restore(self):
        import win32con
        import win32gui

        win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNORMAL)

    def activate(self):
        import win32con
        import win32gui

        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(self.hwnd)

    def _rect(self):
        import win32gui

        return win32gui.GetWindowRect(self.hwnd)


class AdbSingleton:
    instance = None
    APP_ACTIVITY = ""
    APP_PACKAGE = "com.xd.ssrpg"
    APP_PACKAGE_CANDIDATES = ["com.xd.ssrpg", "com.xd.ssrpgtw"]

    def __init__(self, adb_path='', adb_port='', retryCount=5):
        self.deviceConnected = False
        self.adb_path = adb_path
        self.adb_port = adb_port
        self.retry_count = retryCount
        self.control_mode = "adb"
        self.window_title = ""
        self.process_name = "SoC.exe"
        self.base_resolution = (1280, 720)
        self.window_click_backend = "pyautogui"
        self._window = None
        self._last_window_match_summary = ""
        self.stop_requested = False

    @staticmethod
    def getInstance():
        if AdbSingleton.instance is None:
            AdbSingleton.instance = AdbSingleton()
        return AdbSingleton.instance

    @staticmethod
    def normalize_control_mode(control_mode, default="adb"):
        mode = str(control_mode or default).strip().lower()
        mode = {
            "windows": "window",
            "win": "window",
        }.get(mode, mode)
        if mode in ("window", "adb"):
            return mode
        return default

    @staticmethod
    def normalize_window_click_backend(click_backend, default="pyautogui"):
        backend = str(click_backend or default).strip().lower().replace("-", "_")
        backend = {
            "py_auto_gui": "pyautogui",
            "mouseevent": "mouse_event",
            "mouse": "mouse_event",
            "sendinput": "send_input",
            "send": "send_input",
            "post": "post_message",
            "postmessage": "post_message",
        }.get(backend, backend)
        if backend in ("pyautogui", "mouse_event", "send_input", "post_message"):
            return backend
        return default

    def connectDevice(self, adb_path='', adb_port='', retryCount=5):
        self._load_runtime_config()
        if self.control_mode == "window":
            print("connectWindow", self.window_title, self.process_name, self.base_resolution, retryCount)
        else:
            print("connectDevice", adb_path, adb_port, retryCount)
        LoggerSingleton.getInstance().info('./logs/log_test.txt', "正在连接模拟器")
        if adb_path and adb_path != self.adb_path:
            self.adb_path = adb_path
        if adb_port and adb_port != self.adb_port:
            self.adb_port = adb_port
        if retryCount != self.retry_count:
            self.retry_count = retryCount

        if self.control_mode == "window":
            return self._connect_window()

        for i in range(self.retry_count):
            if not self.deviceConnected:
                res = self.adb_connect()
                print("runCmd adb_connect:", res[0])
                if b'connected to' in res[0] or b'already connected' in res[0]:
                    self.setDeviceConnected(True)
                    print("Device Connected")
                    break
                else:
                    self.setDeviceConnected(False)
        return self.deviceConnected

    def _load_runtime_config(self):
        config_path = Path("app_config.yaml")
        if not config_path.exists():
            return

        with config_path.open("r", encoding="utf-8") as config_file:
            config_data = yaml.safe_load(config_file) or []

        for item in config_data:
            if not isinstance(item, dict):
                continue
            adb_dir = item.get("adbDir")
            if adb_dir:
                self.adb_path = str(adb_dir)
            connection_port = item.get("connectionPort")
            if connection_port:
                self.adb_port = str(connection_port)
            self.control_mode = self.normalize_control_mode(item.get("controlMode", self.control_mode), self.control_mode)
            self.window_title = str(item.get("windowTitle", self.window_title))
            self.process_name = str(item.get("processName", self.process_name))
            app_package = item.get("appPackage")
            if app_package:
                AdbSingleton.APP_PACKAGE = str(app_package)
            app_activity = item.get("appActivity")
            if app_activity:
                AdbSingleton.APP_ACTIVITY = str(app_activity)
            package_candidates = item.get("appPackageCandidates")
            if isinstance(package_candidates, list) and package_candidates:
                AdbSingleton.APP_PACKAGE_CANDIDATES = [str(package) for package in package_candidates]
            base_resolution = item.get("baseResolution")
            if isinstance(base_resolution, list) and len(base_resolution) == 2:
                self.base_resolution = (int(base_resolution[0]), int(base_resolution[1]))
            self.window_click_backend = self.normalize_window_click_backend(
                item.get("windowClickBackend", self.window_click_backend),
                self.window_click_backend,
            )

    def _connect_window(self):
        window = self._find_window()
        if window is None:
            self.setDeviceConnected(False)
            LoggerSingleton.getInstance().info(
                './logs/log_test.txt',
                f"未找到可用的官方模拟器窗口：标题={self.window_title or '未设置'}，"
                f"进程={self.process_name or '未设置'}"
            )
            if self._last_window_match_summary:
                LoggerSingleton.getInstance().info('./logs/log_test.txt', self._last_window_match_summary)
            return False

        self._window = window
        self._activate_window()
        self._ensure_window_client_on_screen()
        bounds = self._window_bounds()
        base_width, base_height = self.base_resolution
        if bounds["width"] < base_width * 0.5 or bounds["height"] < base_height * 0.5:
            self.setDeviceConnected(False)
            LoggerSingleton.getInstance().info(
                './logs/log_test.txt',
                f"官方模拟器窗口尺寸过小：{bounds['width']}x{bounds['height']}，"
                "请确认窗口未最小化且游戏画面已打开"
            )
            return False
        if (bounds["width"], bounds["height"]) != self.base_resolution:
            LoggerSingleton.getInstance().info(
                './logs/log_test.txt',
                f"窗口分辨率 {bounds['width']}x{bounds['height']} 与基准 "
                f"{self.base_resolution[0]}x{self.base_resolution[1]} 不一致，请确认模拟器画面设置"
            )
        self.setDeviceConnected(True)
        return True

    def _find_window(self):
        try:
            import pygetwindow as gw
        except ImportError as exc:
            raise RuntimeError("缺少 pygetwindow，请先运行 uv sync") from exc

        title = self.window_title.strip()
        windows = gw.getAllWindows()
        if title:
            title_matches = [window for window in windows if title.lower() in window.title.lower()]
        else:
            title_matches = [window for window in windows if window.title]

        summary_parts = []
        self._restore_candidate_windows(title_matches)
        title_match = self._select_usable_window(title_matches)
        if title_match is not None:
            return title_match
        title_summary = self._format_window_match_summary("标题", title_matches)
        if title_summary:
            summary_parts.append(title_summary)

        process_matches = self._find_windows_by_process_name()
        self._restore_candidate_windows(process_matches)
        process_match = self._select_usable_window(process_matches)
        if process_match is not None:
            return process_match
        process_summary = self._format_window_match_summary("进程", process_matches)
        if process_summary:
            summary_parts.append(process_summary)

        self._last_window_match_summary = "；".join(summary_parts)
        return None

    def _select_usable_window(self, windows):
        base_width, base_height = self.base_resolution
        min_width = base_width * 0.5
        min_height = base_height * 0.5
        visible_matches = [
            window for window in windows
            if getattr(window, "width", 0) > 0
            and getattr(window, "height", 0) > 0
            and getattr(window, "isVisible", True)
            and not getattr(window, "isMinimized", False)
            and getattr(window, "width", 0) >= min_width
            and getattr(window, "height", 0) >= min_height
        ]
        if visible_matches:
            return max(visible_matches, key=lambda window: window.width * window.height)
        return None

    def _restore_candidate_windows(self, windows):
        for window in windows:
            if not getattr(window, "isMinimized", False):
                continue
            try:
                window.restore()
                time.sleep(0.2)
            except Exception as exc:
                print("restore candidate window failed:", exc)

    def _find_windows_by_process_name(self):
        process_name = self.process_name.strip().lower()
        if not process_name:
            return []

        try:
            import win32api
            import win32con
            import win32gui
            import win32process
        except ImportError as exc:
            raise RuntimeError("缺少 pywin32，请先运行 uv sync") from exc

        matched_windows = []

        def get_process_name(pid):
            try:
                process = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                try:
                    return Path(win32process.GetModuleFileNameEx(process, 0)).name.lower()
                finally:
                    win32api.CloseHandle(process)
            except Exception:
                return ""

        def collect_window(hwnd, _):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if get_process_name(pid) == process_name:
                matched_windows.append(NativeWindow(hwnd))

        win32gui.EnumWindows(collect_window, None)
        return matched_windows

    def _format_window_match_summary(self, match_type, windows):
        if not windows:
            return ""
        summaries = []
        for window in windows[:5]:
            summaries.append(
                f"'{window.title}' {window.width}x{window.height} "
                f"minimized={getattr(window, 'isMinimized', False)}"
            )
        return f"{match_type}匹配到窗口但没有可用游戏画面：" + "，".join(summaries)

    def _activate_window(self):
        if self._window is None:
            return
        hwnd = self._window_hwnd()

        def try_step(name, func):
            try:
                func()
                return True
            except Exception as exc:
                print(f"activate window {name} failed:", exc)
                return False

        if hwnd is not None:
            try:
                import win32api
                import win32con
                import win32gui
                import win32process
            except ImportError as exc:
                raise RuntimeError("缺少 pywin32，请先运行 uv sync") from exc

            if try_step("is iconic", lambda: win32gui.IsIconic(hwnd)) and win32gui.IsIconic(hwnd):
                try_step("restore", lambda: win32gui.ShowWindow(hwnd, win32con.SW_RESTORE))
                time.sleep(0.5)

            try_step("show", lambda: win32gui.ShowWindow(hwnd, win32con.SW_SHOW))
            try_step("set window top", lambda: win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOP,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
            ))
            try_step("bring top", lambda: win32gui.BringWindowToTop(hwnd))
            try_step("set foreground", lambda: win32gui.SetForegroundWindow(hwnd))
            try_step("set active", lambda: win32gui.SetActiveWindow(hwnd))
            try_step("set focus", lambda: win32gui.SetFocus(hwnd))

            try:
                foreground_hwnd = win32gui.GetForegroundWindow()
                foreground_thread, _ = win32process.GetWindowThreadProcessId(foreground_hwnd)
                target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
                current_thread = win32api.GetCurrentThreadId()
                attached = []
                for thread_id in {foreground_thread, target_thread}:
                    if thread_id and thread_id != current_thread:
                        if try_step("attach thread input", lambda tid=thread_id: win32process.AttachThreadInput(current_thread, tid, True)):
                            attached.append(thread_id)
                try_step("attached set foreground", lambda: win32gui.SetForegroundWindow(hwnd))
                try_step("attached bring top", lambda: win32gui.BringWindowToTop(hwnd))
                for thread_id in attached:
                    try_step("detach thread input", lambda tid=thread_id: win32process.AttachThreadInput(current_thread, tid, False))
            except Exception as exc:
                print("activate window attached foreground failed:", exc)

        if getattr(self._window, "isMinimized", False):
            try_step("pygetwindow restore", lambda: self._window.restore())
            time.sleep(0.5)
            self._window = self._find_window()
            if self._window is None:
                return
        try_step("pygetwindow activate", lambda: self._window.activate())
        time.sleep(0.2)

    def _window_bounds(self):
        if self._window is None:
            self._window = self._find_window()
        if self._window is None:
            raise RuntimeError("未找到官方模拟器窗口，请检查 app_config.yaml 的 windowTitle")
        hwnd = self._window_hwnd()
        if hwnd is not None:
            try:
                import win32gui

                left, top = win32gui.ClientToScreen(hwnd, (0, 0))
                client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
                return {
                    "left": int(left),
                    "top": int(top),
                    "width": int(client_right - client_left),
                    "height": int(client_bottom - client_top),
                }
            except Exception as exc:
                print("get client bounds failed:", exc)
        return {
            "left": int(self._window.left),
            "top": int(self._window.top),
            "width": int(self._window.width),
            "height": int(self._window.height),
        }

    def _window_hwnd(self):
        return getattr(self._window, "hwnd", None) or getattr(self._window, "_hWnd", None)

    def _virtual_screen_bounds(self):
        try:
            import ctypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            left = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
            top = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
            width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
            height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
            return {"left": int(left), "top": int(top), "width": int(width), "height": int(height)}
        except Exception as exc:
            print("get virtual screen bounds failed:", exc)
            return {"left": 0, "top": 0, "width": 0, "height": 0}

    def _ensure_window_client_on_screen(self):
        hwnd = self._window_hwnd()
        if hwnd is None:
            return
        try:
            import win32con
            import win32gui

            bounds = self._window_bounds()
            desktop = self._virtual_screen_bounds()
            if desktop["width"] <= 0 or desktop["height"] <= 0:
                return

            desktop_right = desktop["left"] + desktop["width"]
            desktop_bottom = desktop["top"] + desktop["height"]
            bounds_right = bounds["left"] + bounds["width"]
            bounds_bottom = bounds["top"] + bounds["height"]
            if (
                bounds["left"] >= desktop["left"]
                and bounds["top"] >= desktop["top"]
                and bounds_right <= desktop_right
                and bounds_bottom <= desktop_bottom
            ):
                return

            window_left, window_top, window_right, window_bottom = win32gui.GetWindowRect(hwnd)
            client_left, client_top = win32gui.ClientToScreen(hwnd, (0, 0))
            offset_x = client_left - window_left
            offset_y = client_top - window_top

            if bounds["width"] <= desktop["width"]:
                desired_client_left = min(max(bounds["left"], desktop["left"]), desktop_right - bounds["width"])
            else:
                desired_client_left = desktop["left"]

            if bounds["height"] <= desktop["height"]:
                desired_client_top = min(max(bounds["top"], desktop["top"]), desktop_bottom - bounds["height"])
            else:
                desired_client_top = desktop["top"]

            win32gui.SetWindowPos(
                hwnd,
                None,
                int(desired_client_left - offset_x),
                int(desired_client_top - offset_y),
                int(window_right - window_left),
                int(window_bottom - window_top),
                win32con.SWP_NOZORDER | win32con.SWP_NOSIZE,
            )
            time.sleep(0.2)
            new_bounds = self._window_bounds()
            LoggerSingleton.getInstance().info(
                './logs/log_test.txt',
                "已调整窗口位置："
                f"客户端={new_bounds['left']},{new_bounds['top']} "
                f"{new_bounds['width']}x{new_bounds['height']}；"
                f"桌面={desktop['left']},{desktop['top']} {desktop['width']}x{desktop['height']}"
            )
        except Exception as exc:
            print("ensure window on screen failed:", exc)

    def _to_screen_pos(self, pos):
        bounds = self._window_bounds()
        base_width, base_height = self.base_resolution
        scale_x = bounds["width"] / base_width
        scale_y = bounds["height"] / base_height
        return (
            bounds["left"] + int(float(pos[0]) * scale_x),
            bounds["top"] + int(float(pos[1]) * scale_y),
        )

    def _move_mouse(self, screen_pos):
        x, y = int(screen_pos[0]), int(screen_pos[1])
        try:
            import ctypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            if user32.SetCursorPos(x, y):
                return True
            print("ctypes SetCursorPos failed:", ctypes.get_last_error(), (x, y), self._virtual_screen_bounds())
        except Exception as exc:
            print("ctypes move failed:", exc)

        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError("缺少 pyautogui，请先运行 uv sync") from exc
        pyautogui.moveTo(x, y, duration=0.05)
        return True

    def _send_input_mouse(self, screen_pos, button_flags=0):
        try:
            import ctypes

            desktop = self._virtual_screen_bounds()
            if desktop["width"] <= 1 or desktop["height"] <= 1:
                return False

            x, y = int(screen_pos[0]), int(screen_pos[1])
            if not (
                desktop["left"] <= x < desktop["left"] + desktop["width"]
                and desktop["top"] <= y < desktop["top"] + desktop["height"]
            ):
                LoggerSingleton.getInstance().info(
                    './logs/log_test.txt',
                    f"点击坐标超出桌面范围：{(x, y)}；桌面={desktop}"
                )
                return False

            class MouseInput(ctypes.Structure):
                _fields_ = [
                    ("dx", ctypes.c_long),
                    ("dy", ctypes.c_long),
                    ("mouseData", ctypes.c_ulong),
                    ("dwFlags", ctypes.c_ulong),
                    ("time", ctypes.c_ulong),
                    ("dwExtraInfo", ctypes.c_size_t),
                ]

            class InputUnion(ctypes.Union):
                _fields_ = [("mi", MouseInput)]

            class Input(ctypes.Structure):
                _fields_ = [
                    ("type", ctypes.c_ulong),
                    ("union", InputUnion),
                ]

            absolute_x = int((x - desktop["left"]) * 65535 / (desktop["width"] - 1))
            absolute_y = int((y - desktop["top"]) * 65535 / (desktop["height"] - 1))
            mouse_flags = 0x0001 | 0x8000 | 0x4000 | button_flags
            input_event = Input(
                type=0,
                union=InputUnion(mi=MouseInput(absolute_x, absolute_y, 0, mouse_flags, 0, 0)),
            )
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            sent = user32.SendInput(1, ctypes.byref(input_event), ctypes.sizeof(input_event))
            if sent == 1:
                return True
            print("SendInput failed:", ctypes.get_last_error(), (x, y), desktop)
        except Exception as exc:
            print("send input failed:", exc)
        return False

    def _target_window_at_pos(self, screen_pos):
        try:
            import win32gui

            x, y = int(screen_pos[0]), int(screen_pos[1])
            hwnd = win32gui.WindowFromPoint((x, y))
            if hwnd:
                return hwnd
        except Exception as exc:
            print("window from point failed:", exc)
        return self._window_hwnd()

    def _window_info(self, hwnd):
        if hwnd is None:
            return "hwnd=None"
        try:
            import win32gui

            return (
                f"hwnd={hwnd} title='{win32gui.GetWindowText(hwnd)}' "
                f"class='{win32gui.GetClassName(hwnd)}'"
            )
        except Exception as exc:
            return f"hwnd={hwnd} info_error={exc}"

    def _post_window_click(self, screen_pos):
        hwnd = self._target_window_at_pos(screen_pos)
        if hwnd is None:
            return False
        try:
            import win32api
            import win32con
            import win32gui

            x, y = int(screen_pos[0]), int(screen_pos[1])
            client_x, client_y = win32gui.ScreenToClient(hwnd, (x, y))
            l_param = win32api.MAKELONG(client_x, client_y)
            win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, l_param)
            win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, l_param)
            time.sleep(0.08)
            win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, l_param)
            print("post window click", self._window_info(hwnd), (client_x, client_y))
            return True
        except Exception as exc:
            print("post window click failed:", exc, self._window_info(hwnd))
        return False

    def _window_mouse_down(self, screen_pos):
        if self.window_click_backend == "send_input" and self._send_input_mouse(screen_pos, 0x0002):
            return
        self._move_mouse(screen_pos)
        time.sleep(0.03)
        if self.window_click_backend == "pyautogui":
            try:
                import pyautogui

                pyautogui.mouseDown()
                return
            except ImportError as exc:
                raise RuntimeError("缺少 pyautogui，请先运行 uv sync") from exc
            except Exception as exc:
                print("pyautogui mouse down failed:", exc)

        try:
            import win32api
            import win32con

            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            return
        except Exception as exc:
            print("win32 mouse down failed:", exc)

        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError("缺少 pyautogui，请先运行 uv sync") from exc
        pyautogui.mouseDown()

    def _window_mouse_up(self, screen_pos):
        if self.window_click_backend == "send_input" and self._send_input_mouse(screen_pos, 0x0004):
            return
        self._move_mouse(screen_pos)
        time.sleep(0.03)
        if self.window_click_backend == "pyautogui":
            try:
                import pyautogui

                pyautogui.mouseUp()
                return
            except ImportError as exc:
                raise RuntimeError("缺少 pyautogui，请先运行 uv sync") from exc
            except Exception as exc:
                print("pyautogui mouse up failed:", exc)

        try:
            import win32api
            import win32con

            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            return
        except Exception as exc:
            print("win32 mouse up failed:", exc)

        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError("缺少 pyautogui，请先运行 uv sync") from exc
        pyautogui.mouseUp()

    def _window_click(self, screen_pos):
        self._activate_window()
        self._move_mouse(screen_pos)
        time.sleep(0.08)
        if self.window_click_backend == "post_message":
            self._post_window_click(screen_pos)
            return
        self._window_mouse_down(screen_pos)
        time.sleep(0.12)
        self._window_mouse_up(screen_pos)

    def adb_connect(self):
        command = [self.adb_path, "connect", self.adb_port]
        print(" ".join(command))
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        return [output, error]

    def adb_device(self):
        command = [self.adb_path, "devices"]
        print(" ".join(command))
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        return [output, error]

    def adb_shell(self, command):
        full_command = [self.adb_path, "-s", self.adb_port, "shell", command]
        print(" ".join(full_command))
        p = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        return [output, error]

    def resolve_app_package(self, installed_packages):
        candidates = []
        for package in [AdbSingleton.APP_PACKAGE, *AdbSingleton.APP_PACKAGE_CANDIDATES]:
            if package and package not in candidates:
                candidates.append(package)
        installed_set = set(installed_packages)
        for package in candidates:
            if package in installed_set:
                AdbSingleton.APP_PACKAGE = package
                return package
        return None

    def trigger_key_event(self, key):
        self._raise_if_stop_requested()
        if self.control_mode == "window":
            try:
                import pyautogui
            except ImportError as exc:
                raise RuntimeError("缺少 pyautogui，请先运行 uv sync") from exc
            self._activate_window()
            pyautogui.press(str(key))
            return
        command = ["input", "keyevent", str(key)]
        self.adb_shell(" ".join(command))

    def screen_capture(self, path):
        self._raise_if_stop_requested()
        if self.control_mode == "window":
            return self._window_screen_capture(path)

        full_command = [self.adb_path, "-s", self.adb_port, "exec-out", "screencap", "/sdcard/cache.png"]
        print(" ".join(full_command))
        p = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        full_command = [self.adb_path, "-s", self.adb_port, "pull", "/sdcard/cache.png", path]
        print(" ".join(full_command))
        p = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.communicate()
        full_command = [self.adb_path, "-s", self.adb_port, "shell", "rm", "/sdcard/cache.png"]
        print(" ".join(full_command))
        p = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return path

    def _window_screen_capture(self, path):
        try:
            import mss
            import mss.tools
        except ImportError as exc:
            raise RuntimeError("缺少 mss，请先运行 uv sync") from exc

        self._activate_window()
        bounds = self._window_bounds()
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with mss.mss() as sct:
            sct_img = sct.grab(bounds)
            base_width, base_height = self.base_resolution
            if sct_img.size != self.base_resolution:
                from PIL import Image

                image = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
                image = image.resize((base_width, base_height), Image.Resampling.LANCZOS)
                image.save(output_path)
            else:
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(output_path))
        return str(output_path)

    def swipe(self, posStart, posEnd, duration=None):
        self._raise_if_stop_requested()
        if self.control_mode == "window":
            self._activate_window()
            start_x, start_y = self._to_screen_pos(posStart)
            end_x, end_y = self._to_screen_pos(posEnd)
            self._window_mouse_down((start_x, start_y))
            time.sleep((duration or 300) / 1000)
            self._window_mouse_up((end_x, end_y))
            return

        command = ["input", "swipe", str(posStart[0]), str(posStart[1]), str(posEnd[0]), str(posEnd[1])]
        if duration:
            command.append(str(duration))
        self.adb_shell(" ".join(command))

    def tap(self, pos):
        self._raise_if_stop_requested()
        if pos is None:
            return
        if self.control_mode == "window":
            screen_pos = self._to_screen_pos(pos)
            bounds = self._window_bounds()
            desktop = self._virtual_screen_bounds()
            target_hwnd = self._target_window_at_pos(screen_pos)
            print("window tap", pos, "->", screen_pos)
            LoggerSingleton.getInstance().info(
                './logs/log_test.txt',
                f"点击窗口坐标 {pos} -> 屏幕坐标 {screen_pos}"
            )
            LoggerSingleton.getInstance().info(
                './logs/log_test.txt',
                "窗口点击调试："
                f"backend={self.window_click_backend}；"
                f"client={bounds['left']},{bounds['top']} {bounds['width']}x{bounds['height']}；"
                f"desktop={desktop['left']},{desktop['top']} {desktop['width']}x{desktop['height']}；"
                f"target={self._window_info(target_hwnd)}"
            )
            self._window_click(screen_pos)
            return

        command = ["input", "tap", str(pos[0]), str(pos[1])]
        self.adb_shell(" ".join(command))

    def tap_down(self, pos):
        self._raise_if_stop_requested()
        if self.control_mode == "window":
            self._activate_window()
            self._window_mouse_down(self._to_screen_pos(pos))
            return
        command = ["input", "touchscreen", "touch", str(pos[0]), str(pos[1])]
        self.adb_shell(" ".join(command))

    def tap_up(self, pos):
        self._raise_if_stop_requested()
        if self.control_mode == "window":
            self._activate_window()
            self._window_mouse_up(self._to_screen_pos(pos))
            return
        command = ["input", "touchscreen", "release", str(pos[0]), str(pos[1])]
        self.adb_shell(" ".join(command))

    def get_screen_resolution(self):
        if self.control_mode == "window":
            bounds = self._window_bounds()
            return (bounds["width"], bounds["height"])
        output, error = self.adb_shell("wm size")
        print(output)
        resolution_str = output.decode("utf-8").strip().split(" ")[2]
        width, height = map(int, resolution_str.split("x"))
        return (width, height)

    def capture_screen(self, filename):
        filepath = Path(__file__).parent / "img" / filename
        self.screen_capture(str(filepath))
        return filepath

    def getAllPackages(self):
        if self.control_mode == "window":
            return [AdbSingleton.APP_PACKAGE]
        output, error = self.adb_shell("pm list packages")
        output_array = [
            item.replace("package:", "", 1)
            for item in output.decode(errors="ignore").splitlines()
            if item.startswith("package:")
        ]
        print("res: ", output_array)
        resolved_package = self.resolve_app_package(output_array)
        if resolved_package:
            print("Resolved app package:", resolved_package)
        else:
            LoggerSingleton.getInstance().info(
                './logs/log_test.txt',
                f"未找到游戏包，已安装包中没有：{', '.join(AdbSingleton.APP_PACKAGE_CANDIDATES)}"
            )
        return output_array

    def startApp(self):
        if self.control_mode == "window":
            self._activate_window()
            return b"window activated"
        if AdbSingleton.APP_ACTIVITY:
            output, error = self.adb_shell("am start -n " + AdbSingleton.APP_ACTIVITY)
        else:
            output, error = self.adb_shell(
                f"monkey -p {AdbSingleton.APP_PACKAGE} -c android.intent.category.LAUNCHER 1"
            )
        print(output)
        return output
    def setDeviceConnected(self, connected):
        self.deviceConnected = connected

    def isDeviceConnected(self):
        return self.deviceConnected

    def requestStop(self):
        self.stop_requested = True

    def resetStop(self):
        self.stop_requested = False

    def _raise_if_stop_requested(self):
        if self.stop_requested:
            raise RuntimeError("流程已停止")
