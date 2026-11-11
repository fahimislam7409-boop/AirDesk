import os
import sys
import json
import time
import socket
import asyncio
import fractions
import secrets
import io
import base64
from pathlib import Path
from contextlib import asynccontextmanager

import psutil
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import VideoFrame
import numpy as np
import qrcode

from streamer import ScreenStreamer, attach_thread_to_desktop
from input_controller import InputController

# Directory paths (supports standalone PyInstaller EXE bundle)
if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent
    APP_DIR = BUNDLE_DIR

BASE_DIR = APP_DIR
STATIC_DIR = BUNDLE_DIR / "static"
CONFIG_FILE = APP_DIR / "config.json"
PID_FILE = APP_DIR / "airdesk.pid"
LOG_FILE = APP_DIR / "airdesk.log"

def free_port(port: int):
    """Ensure port is available by terminating stale instances."""
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.pid == current_pid:
                continue
            for conn in proc.net_connections(kind='inet'):
                if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    print(f"[PortManager] Port {port} occupied by PID {proc.pid} ({proc.name()}). Terminating old instance...")
                    proc.kill()
                    proc.wait(timeout=1.5)
                    time.sleep(0.3)
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired, Exception):
            pass

def generate_qr_base64(url: str) -> str:
    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return ""

# Save PID for clean stopping
try:
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
except Exception:
    pass

# Load configuration
def load_config():
    default_config = {
        "host": "0.0.0.0",
        "port": 8000,
        "pin": "123456",
        "auth_required": True,
        "fps": 30,
        "quality": 75,
        "scale": 1.0,
        "default_mode": "touchpad"
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                user_conf = json.load(f)
                default_config.update(user_conf)
        except Exception as e:
            print(f"[Server] Failed to read config.json: {e}")
    return default_config

config = load_config()

# App instances
streamer = ScreenStreamer(
    target_fps=config["fps"],
    default_quality=config["quality"],
    default_scale=config["scale"]
)
input_ctrl = InputController()

# Active WebRTC peer connections
pcs = set()

# Session tokens for authentication
valid_tokens = set()

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

# Discovery Protocol for Zero-Config LAN Detection
class DiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, http_port):
        self.http_port = http_port
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        try:
            msg = data.decode("utf-8", errors="ignore").strip()
            if "AIRDESK_DISCOVER" in msg or "AETHERDESK_DISCOVER" in msg:
                my_ip = get_local_ip()
                payload = json.dumps({
                    "magic": "AIRDESK_BEACON",
                    "hostname": socket.gethostname(),
                    "ip": my_ip,
                    "port": self.http_port,
                    "version": "2.2.0"
                }).encode("utf-8")
                self.transport.sendto(payload, addr)
                print(f"[Discovery] Answered discovery ping from {addr[0]}:{addr[1]}")
        except Exception:
            pass

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    attach_thread_to_desktop()

    # Start LAN UDP auto-discovery beacon on UDP port 8001
    loop = asyncio.get_running_loop()
    port = int(config.get("port", 8000))
    discovery_transport = None
    try:
        discovery_transport, _ = await loop.create_datagram_endpoint(
            lambda: DiscoveryProtocol(port),
            local_addr=("0.0.0.0", 8001),
            allow_broadcast=True
        )
        print("[Discovery] LAN UDP auto-discovery beacon active on UDP:8001")
    except Exception as e:
        print(f"[Discovery] Note: UDP 8001 beacon not bound ({e})")

    yield

    # Shutdown
    if discovery_transport:
        discovery_transport.close()
    coros = [pc.close() for pc in list(pcs)]
    if coros:
        await asyncio.gather(*coros, return_exceptions=True)
    pcs.clear()
    if PID_FILE.exists():
        try:
            PID_FILE.unlink()
        except Exception:
            pass

app = FastAPI(title="AirDesk Remote Server", lifespan=lifespan)

# Static files mount with no-cache headers
@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# WebRTC Video Track
class DesktopVideoTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, streamer, fps=30):
        super().__init__()
        self.streamer = streamer
        self.fps = fps
        self._timestamp = 0
        self.time_base = fractions.Fraction(1, 90000)

    async def recv(self):
        pts = self._timestamp
        self._timestamp += int(90000 / self.fps)
        
        delay = 1.0 / self.fps
        await asyncio.sleep(delay)
        
        loop = asyncio.get_running_loop()
        frame_bgr = await loop.run_in_executor(None, self.streamer.get_frame_raw, True)
        
        if frame_bgr is None:
            sw, sh = self.streamer.get_screen_size()
            frame_bgr = np.zeros((sh, sw, 3), dtype=np.uint8)
            
        frame = VideoFrame.from_ndarray(frame_bgr, format="bgr24")
        frame.pts = pts
        frame.time_base = self.time_base
        return frame

# Schemas
class LoginRequest(BaseModel):
    pin: str

class OfferRequest(BaseModel):
    sdp: str
    type: str

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return "<h1>AirDesk: static/index.html not found.</h1>"

@app.get("/manifest.json")
async def get_manifest():
    manifest_path = STATIC_DIR / "manifest.json"
    if manifest_path.exists():
        return FileResponse(manifest_path, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="manifest.json not found")

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    dashboard_path = STATIC_DIR / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return "<h1>AirDesk: static/dashboard.html not found.</h1>"

@app.get("/api/dashboard_info")
async def get_dashboard_info():
    ip = get_local_ip()
    port = int(config.get("port", 8000))
    url = f"http://{ip}:{port}"
    qr_b64 = generate_qr_base64(url)
    return {
        "url": url,
        "qr_base64": qr_b64,
        "pin": config.get("pin", "123456"),
        "hostname": socket.gethostname(),
        "gpu": "NVIDIA GeForce RTX 5060 (DXCam GPU Duplication)",
        "port": port
    }

@app.api_route("/apk", methods=["GET", "HEAD"])
@app.api_route("/download", methods=["GET", "HEAD"])
async def download_apk():
    search_dirs = [APP_DIR, BUNDLE_DIR, APP_DIR / "releases", BUNDLE_DIR / "releases"]
    for d in search_dirs:
        for name in ["AirDesk.apk", "AirDesk_RedmiPadPro.apk"]:
            apk_path = d / name
            if apk_path.exists():
                return FileResponse(
                    path=str(apk_path),
                    filename="AirDesk.apk",
                    media_type="application/vnd.android.package-archive"
                )
    raise HTTPException(status_code=404, detail="APK file not found")

@app.post("/api/login")
async def login(req: LoginRequest):
    if not config["auth_required"] or req.pin.strip() == str(config["pin"]).strip():
        token = secrets.token_hex(16)
        valid_tokens.add(token)
        return {"success": True, "token": token}
    return JSONResponse(status_code=401, content={"success": False, "message": "Incorrect PIN"})

@app.get("/api/info")
async def get_info(token: str = None):
    if config["auth_required"] and token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Unauthorized")
    sw, sh = streamer.get_screen_size()
    return {
        "hostname": socket.gethostname(),
        "local_ip": get_local_ip(),
        "screen_width": sw,
        "screen_height": sh,
        "fps": streamer.target_fps,
        "quality": streamer.quality,
        "scale": streamer.scale,
        "auth_required": config["auth_required"]
    }

async def wait_for_ice(pc, timeout=2.0):
    if pc.iceGatheringState == "complete":
        return
    fut = asyncio.get_running_loop().create_future()
    @pc.on("icegatheringstatechange")
    def on_change():
        if pc.iceGatheringState == "complete" and not fut.done():
            fut.set_result(True)
    try:
        await asyncio.wait_for(fut, timeout=timeout)
    except asyncio.TimeoutError:
        pass

@app.post("/api/offer")
async def webrtc_offer(params: OfferRequest, token: str = None):
    if config["auth_required"] and token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Unauthorized")

    offer = RTCSessionDescription(sdp=params.sdp, type=params.type)
    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("iceconnectionstatechange")
    async def on_ice_state_change():
        if pc.iceConnectionState in ("failed", "closed"):
            await pc.close()
            pcs.discard(pc)

    track = DesktopVideoTrack(streamer, fps=streamer.target_fps)
    pc.addTrack(track)

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # Wait for ICE candidates so SDP includes them
    await wait_for_ice(pc, timeout=2.0)

    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if config["auth_required"] and token not in valid_tokens:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    sw, sh = streamer.get_screen_size()
    await websocket.send_json({
        "type": "init",
        "width": sw,
        "height": sh,
        "default_mode": config.get("default_mode", "touchpad")
    })

    # High-speed WebSocket Turbo Stream (active by default!)
    ws_stream_active = True

    async def ws_stream_worker():
        nonlocal ws_stream_active
        loop = asyncio.get_running_loop()
        while ws_stream_active:
            t0 = time.time()
            jpeg_bytes = await loop.run_in_executor(None, streamer.get_frame_jpeg)
            if jpeg_bytes:
                try:
                    await websocket.send_bytes(jpeg_bytes)
                except Exception:
                    break
            elapsed = time.time() - t0
            sleep_time = max(0.002, (1.0 / streamer.target_fps) - elapsed)
            await asyncio.sleep(sleep_time)

    # Launch streaming immediately upon connection
    ws_stream_task = asyncio.create_task(ws_stream_worker())

    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            mtype = data.get("type")

            if mtype == "ping":
                await websocket.send_json({"type": "pong", "t": data.get("t")})

            elif mtype == "move":
                input_ctrl.move_to(data.get("x", 0), data.get("y", 0))

            elif mtype == "delta":
                sens = float(data.get("sens", 1.0))
                input_ctrl.move_relative(data.get("dx", 0), data.get("dy", 0), sens)

            elif mtype == "mousedown":
                input_ctrl.mouse_down(data.get("button", "left"))

            elif mtype == "mouseup":
                input_ctrl.mouse_up(data.get("button", "left"))

            elif mtype == "click":
                input_ctrl.click(data.get("button", "left"))

            elif mtype == "double_click":
                input_ctrl.double_click(data.get("button", "left"))

            elif mtype == "wheel":
                input_ctrl.wheel(delta_y=data.get("dy", 0), delta_x=data.get("dx", 0))

            elif mtype == "keydown":
                input_ctrl.key_down(data.get("key"))

            elif mtype == "keyup":
                input_ctrl.key_up(data.get("key"))

            elif mtype == "press":
                input_ctrl.press_key(data.get("key"))

            elif mtype == "type":
                input_ctrl.type_text(data.get("text", ""))

            elif mtype == "action":
                input_ctrl.execute_action(data.get("action", ""))

            elif mtype == "start_stream":
                if not ws_stream_active:
                    ws_stream_active = True
                    ws_stream_task = asyncio.create_task(ws_stream_worker())

            elif mtype == "stop_stream":
                ws_stream_active = False
                if ws_stream_task:
                    ws_stream_task.cancel()

            elif mtype == "settings":
                if "fps" in data:
                    streamer.target_fps = int(data["fps"])
                if "quality" in data:
                    streamer.quality = int(data["quality"])
                if "scale" in data:
                    streamer.scale = float(data["scale"])

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[Server] WebSocket error: {e}")
    finally:
        ws_stream_active = False
        if ws_stream_task:
            ws_stream_task.cancel()
        input_ctrl.release_all_keys()

def print_banner(ip, port):
    url = f"http://{ip}:{port}"
    print("\n" + "=" * 60)
    print("  🚀 AirDesk Remote Desktop Server is LIVE!")
    print("=" * 60)
    print(f"  👉 Tablet / Phone URL : {url}")
    print(f"  👉 Local PC URL       : http://localhost:{port}")
    print(f"  📥 Download APK (App) : {url}/apk")
    if config["auth_required"]:
        print(f"  🔑 Security PIN Code  : {config['pin']}")
    else:
        print("  🔓 Security PIN       : None (Disabled)")
    print("-" * 60)
    print("  👨‍💻 Developer         : Fahim Islam")
    print("  🌐 Facebook          : https://www.facebook.com/fahim.islam.7409/")
    print("  📺 YouTube Channel   : https://www.youtube.com/@FreelancerFahimIslam")
    print("  💬 WhatsApp          : @CoderFahim")
    print("  🐙 GitHub            : https://github.com/fahimislam7409-boop/AirDesk")
    print("=" * 60)
    print("  📱 Scan with your Tablet or Phone Camera to Connect:")
    print("-" * 60)
    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.print_ascii(invert=True)
    except Exception:
        pass
    print("=" * 60)
    print("  (Press Ctrl+C to stop the server)\n")

class DesktopBridge:
    def open_browser(self, url):
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception:
            pass

if __name__ == "__main__":
    ip = get_local_ip()
    port = int(config.get("port", 8000))
    is_silent = "--silent" in sys.argv
    is_cli = "--cli" in sys.argv or "--headless" in sys.argv or is_silent

    # 1. Clean port 8000 if occupied by old instance to prevent WinError 10048
    free_port(port)

    attach_thread_to_desktop()

    if is_cli:
        if not is_silent:
            print_banner(ip, port)
        uvicorn.run(
            app,
            host=config.get("host", "0.0.0.0"),
            port=port,
            log_level="warning" if is_silent else "info",
            access_log=False if is_silent else True
        )
    else:
        # Modern Desktop GUI Dashboard Mode
        try:
            import webview
            import threading
            has_gui = True
        except ImportError:
            has_gui = False

        if has_gui:
            server_config = uvicorn.Config(
                app,
                host=config.get("host", "0.0.0.0"),
                port=port,
                log_level="warning",
                access_log=False
            )
            server = uvicorn.Server(server_config)
            server_thread = threading.Thread(target=server.run, daemon=True)
            server_thread.start()

            # Wait briefly for server to bind
            time.sleep(0.6)

            bridge = DesktopBridge()
            dashboard_url = f"http://127.0.0.1:{port}/dashboard"

            window = webview.create_window(
                title="AirDesk - Personal Remote Desktop",
                url=dashboard_url,
                js_api=bridge,
                width=960,
                height=680,
                min_size=(800, 560),
                background_color="#090d16"
            )
            webview.start()
            server.should_exit = True
        else:
            print_banner(ip, port)
            uvicorn.run(app, host=config.get("host", "0.0.0.0"), port=port)
