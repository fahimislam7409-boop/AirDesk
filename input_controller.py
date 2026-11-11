import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32

# Mouse event constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000

# Keyboard event constants
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

# Structures for SendInput
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", _INPUT),
    ]

INPUT_KEYBOARD = 1

# Virtual Key Mapping
VK_MAP = {
    "enter": 0x0D,
    "return": 0x0D,
    "backspace": 0x08,
    "tab": 0x09,
    "escape": 0x1B,
    "esc": 0x1B,
    "space": 0x20,
    "delete": 0x2E,
    "del": 0x2E,
    "insert": 0x2D,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "arrowup": 0x26,
    "up": 0x26,
    "arrowdown": 0x28,
    "down": 0x28,
    "arrowleft": 0x25,
    "left": 0x25,
    "arrowright": 0x27,
    "right": 0x27,
    "control": 0x11,
    "ctrl": 0x11,
    "alt": 0x12,
    "shift": 0x10,
    "meta": 0x5B,
    "win": 0x5B,
    "windows": 0x5B,
    "capslock": 0x14,
    "volume_up": 0xAF,
    "volume_down": 0xAE,
    "volume_mute": 0xAD,
    "media_play_pause": 0xB3,
    "media_next": 0xB0,
    "media_prev": 0xB1,
}

for i in range(1, 13):
    VK_MAP[f"f{i}"] = 0x6F + i

class InputController:
    def __init__(self):
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)
        self._pressed_keys = set()

    def update_screen_metrics(self):
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)

    # --- Mouse Controls ---

    def move_to(self, x, y):
        """Move cursor directly to absolute coordinates."""
        target_x = max(0, min(self.screen_width - 1, int(x)))
        target_y = max(0, min(self.screen_height - 1, int(y)))
        user32.SetCursorPos(target_x, target_y)

    def move_relative(self, dx, dy, sensitivity=1.0):
        """Move cursor relatively based on delta (for tablet trackpad mode)."""
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        target_x = max(0, min(self.screen_width - 1, int(pt.x + dx * sensitivity)))
        target_y = max(0, min(self.screen_height - 1, int(pt.y + dy * sensitivity)))
        user32.SetCursorPos(target_x, target_y)

    def mouse_down(self, button="left"):
        b = button.lower()
        if b == "left":
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        elif b == "right":
            user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        elif b == "middle":
            user32.mouse_event(MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)

    def mouse_up(self, button="left"):
        b = button.lower()
        if b == "left":
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif b == "right":
            user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        elif b == "middle":
            user32.mouse_event(MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)

    def click(self, button="left"):
        self.mouse_down(button)
        time.sleep(0.01)
        self.mouse_up(button)

    def double_click(self, button="left"):
        self.click(button)
        time.sleep(0.05)
        self.click(button)

    def wheel(self, delta_y=0, delta_x=0):
        if delta_y != 0:
            # Standard mouse wheel click is 120 units
            user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(delta_y), 0)
        if delta_x != 0:
            user32.mouse_event(MOUSEEVENTF_HWHEEL, 0, 0, int(delta_x), 0)

    # --- Keyboard Controls ---

    def type_unicode_char(self, char):
        """Type a single Unicode character using SendInput (supports Bangla, Emoji, English)."""
        code = ord(char)
        # Key down
        inp_down = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0)
        )
        # Key up
        inp_up = INPUT(
            type=INPUT_KEYBOARD,
            ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
        )
        user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
        user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))

    def type_text(self, text):
        """Types full string directly into whatever window is active."""
        for char in text:
            if char == "\n":
                self.press_key("enter")
            elif char == "\t":
                self.press_key("tab")
            else:
                self.type_unicode_char(char)
            time.sleep(0.005)

    def _get_vk(self, key_name):
        k = key_name.lower()
        if k in VK_MAP:
            return VK_MAP[k]
        if len(k) == 1:
            # Single character
            char = k.upper()
            return ord(char)
        return None

    def key_down(self, key_name):
        vk = self._get_vk(key_name)
        if vk:
            flags = 0
            if key_name.lower() in ("arrowup", "arrowdown", "arrowleft", "arrowright", "insert", "delete", "home", "end", "pageup", "pagedown"):
                flags |= KEYEVENTF_EXTENDEDKEY
            user32.keybd_event(vk, 0, flags, 0)
            self._pressed_keys.add(vk)

    def key_up(self, key_name):
        vk = self._get_vk(key_name)
        if vk:
            flags = KEYEVENTF_KEYUP
            if key_name.lower() in ("arrowup", "arrowdown", "arrowleft", "arrowright", "insert", "delete", "home", "end", "pageup", "pagedown"):
                flags |= KEYEVENTF_EXTENDEDKEY
            user32.keybd_event(vk, 0, flags, 0)
            self._pressed_keys.discard(vk)

    def press_key(self, key_name):
        self.key_down(key_name)
        time.sleep(0.02)
        self.key_up(key_name)

    def release_all_keys(self):
        for vk in list(self._pressed_keys):
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        self._pressed_keys.clear()

    # --- System Action Shortcuts ---

    def execute_action(self, action_name):
        act = action_name.lower()
        if act == "win_d":
            self.key_down("win")
            self.press_key("d")
            self.key_up("win")
        elif act == "win_tab":
            self.key_down("win")
            self.press_key("tab")
            self.key_up("win")
        elif act == "alt_tab":
            self.key_down("alt")
            self.press_key("tab")
            self.key_up("alt")
        elif act == "ctrl_c":
            self.key_down("ctrl")
            self.press_key("c")
            self.key_up("ctrl")
        elif act == "ctrl_v":
            self.key_down("ctrl")
            self.press_key("v")
            self.key_up("ctrl")
        elif act == "ctrl_z":
            self.key_down("ctrl")
            self.press_key("z")
            self.key_up("ctrl")
        elif act == "task_mgr":
            self.key_down("ctrl")
            self.key_down("shift")
            self.press_key("esc")
            self.key_up("shift")
            self.key_up("ctrl")
        elif act == "lock":
            user32.LockWorkStation()
        elif act == "vol_up":
            self.press_key("volume_up")
        elif act == "vol_down":
            self.press_key("volume_down")
        elif act == "vol_mute":
            self.press_key("volume_mute")
        elif act == "play_pause":
            self.press_key("media_play_pause")
        elif act == "next_track":
            self.press_key("media_next")
        elif act == "prev_track":
            self.press_key("media_prev")

