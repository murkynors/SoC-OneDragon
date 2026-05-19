import os
import subprocess


class Adb_profile:
    def __init__(self, file_path, device_ip):
        self.adb_path = file_path
        self.device_ip = device_ip

    def adb_connect(self):
        command = [self.adb_path, "connect", self.device_ip]
        print(" ".join(command))
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        return [output, error]

    def adb_device(self):
        command = [self.adb_path, "devices"]
        print(" ".join(command))
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        return [output, error]

    def adb_shell(self, command):
        full_command = [self.adb_path, "-s", self.device_ip, "shell", command]
        print(" ".join(full_command))
        process = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        return [output, error]

    def screen_capture(self, path):
        full_command = [self.adb_path, "-s", self.device_ip, "exec-out", "screencap", "/sdcard/cache.png"]
        print(" ".join(full_command))
        process = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.communicate()

        full_command = [self.adb_path, "-s", self.device_ip, "pull", "/sdcard/cache.png", path]
        print(" ".join(full_command))
        process = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.communicate()

        full_command = [self.adb_path, "-s", self.device_ip, "shell", "rm", "/sdcard/cache.png"]
        print(" ".join(full_command))
        subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return path

    def swipe(self, posStart, posEnd, duration=None):
        command = ["input", "swipe", str(posStart[0]), str(posStart[1]), str(posEnd[0]), str(posEnd[1])]
        if duration:
            command.append(str(duration))
        self.adb_shell(" ".join(command))

    def tap(self, pos):
        command = ["input", "tap", str(pos[0]), str(pos[1])]
        self.adb_shell(" ".join(command))

    def tap_down(self, pos):
        command = ["input", "touchscreen", "touch", str(pos[0]), str(pos[1])]
        self.adb_shell(" ".join(command))

    def tap_up(self, pos):
        command = ["input", "touchscreen", "release", str(pos[0]), str(pos[1])]
        self.adb_shell(" ".join(command))

    def get_screen_resolution(self):
        output, _ = self.adb_shell("wm size")
        print(output)
        resolution_str = output.decode("utf-8").strip().split(" ")[2]
        width, height = map(int, resolution_str.split("x"))
        return (width, height)

    def capture_screen(self, filename):
        cmd = f"{self.adb_path} -s {self.device_ip} shell screencap -p"
        output = os.popen(cmd).read()
        filepath = os.path.join(os.path.dirname(__file__), "img", filename)
        with open(filepath, "wb") as file:
            file.write(output)
        return filepath
