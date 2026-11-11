import ctypes
from ctypes import wintypes
import time
import cv2
import numpy as np

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HANDLE),
        ("ptScreenPos", wintypes.POINT),
    ]

def attach_thread_to_desktop():
    """Attach current thread to the active user input desktop."""
    try:
        hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
            user32.CloseDesktop(hdesk)
            return True
    except Exception:
        pass
    return False

class ScreenStreamer:
    def __init__(self, target_fps=30, default_quality=75, default_scale=1.0):
        self.target_fps = target_fps
        self.quality = default_quality
        self.scale = default_scale
        self.screen_width = max(800, user32.GetSystemMetrics(0))
        self.screen_height = max(600, user32.GetSystemMetrics(1))
        
        self.dx_camera = None
        self.mss_instance = None
        self._last_frame = None
        self._init_capture_engine()

    def _init_capture_engine(self):
        attach_thread_to_desktop()
        # 1. Try DXCAM hardware capture (NVIDIA RTX 5060)
        try:
            import dxcam
            self.dx_camera = dxcam.create(output_color="BGR")
            print("[Streamer] DXCAM GPU capture initialized.")
        except Exception as e:
            print(f"[Streamer] DXCAM init failed ({e}), using MSS backup.")
            self.dx_camera = None

        # 2. MSS backup
        try:
            import mss
            self.mss_instance = mss.MSS()
            print("[Streamer] MSS capture initialized.")
        except Exception as e:
            print(f"[Streamer] MSS init error: {e}")

    def get_screen_size(self):
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        if w > 0 and h > 0:
            self.screen_width, self.screen_height = w, h
        return self.screen_width, self.screen_height

    def _draw_cursor(self, img):
        """Draw mouse cursor directly on captured frame."""
        try:
            ci = CURSORINFO()
            ci.cbSize = ctypes.sizeof(CURSORINFO)
            if user32.GetCursorInfo(ctypes.byref(ci)):
                if ci.flags & 1:  # CURSOR_SHOWING
                    cx = ci.ptScreenPos.x
                    cy = ci.ptScreenPos.y
                    h, w = img.shape[:2]
                    if 0 <= cx < w and 0 <= cy < h:
                        pts = np.array([
                            [cx, cy],
                            [cx, cy + 18],
                            [cx + 5, cy + 14],
                            [cx + 9, cy + 22],
                            [cx + 12, cy + 20],
                            [cx + 8, cy + 13],
                            [cx + 14, cy + 13]
                        ], dtype=np.int32)
                        cv2.polylines(img, [pts], True, (0, 0, 0), 2, cv2.LINE_AA)
                        cv2.fillPoly(img, [pts], (255, 255, 255), cv2.LINE_AA)
        except Exception:
            pass

    def get_frame_raw(self, draw_cursor=True):
        """Returns BGR numpy array of current screen."""
        attach_thread_to_desktop()
        frame = None

        # 1. Try DXCAM
        if self.dx_camera:
            try:
                frame = self.dx_camera.grab()
            except Exception:
                try:
                    self._init_capture_engine()
                    if self.dx_camera:
                        frame = self.dx_camera.grab()
                except Exception:
                    frame = None

        # 2. Fallback to MSS if DXCAM gave None
        if frame is None and self.mss_instance:
            try:
                mon = self.mss_instance.monitors[1]
                sct_img = self.mss_instance.grab(mon)
                frame = np.array(sct_img)[:, :, :3]
            except Exception:
                try:
                    import mss
                    self.mss_instance = mss.MSS()
                    mon = self.mss_instance.monitors[1]
                    sct_img = self.mss_instance.grab(mon)
                    frame = np.array(sct_img)[:, :, :3]
                except Exception:
                    frame = None

        # 3. If capture succeeded, cache it
        if frame is not None:
            self._last_frame = frame.copy()
        elif self._last_frame is not None:
            # Desktop was static or momentary glitch, use cached frame
            frame = self._last_frame.copy()

        # 4. If still None (first frame glitch), generate placeholder desktop
        if frame is None:
            sw, sh = self.get_screen_size()
            frame = np.zeros((sh, sw, 3), dtype=np.uint8)
            cv2.putText(frame, "AetherDesk: Initializing Desktop...", (50, sh // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 200), 2)

        if draw_cursor:
            self._draw_cursor(frame)

        return frame

    def get_frame_jpeg(self, quality=None, scale=None):
        """Returns compressed JPEG bytes for streaming."""
        frame = self.get_frame_raw(draw_cursor=True)
        if frame is None:
            return None

        q = int(quality if quality is not None else self.quality)
        s = float(scale if scale is not None else self.scale)

        if s < 0.99:
            h, w = frame.shape[:2]
            nw, nh = max(320, int(w * s)), max(240, int(h * s))
            frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)

        ret, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, q])
        if ret:
            return jpeg.tobytes()
        return None
