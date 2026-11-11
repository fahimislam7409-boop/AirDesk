import os
import sys
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICO_PATH = os.path.join(BASE_DIR, "airdesk.ico")
STATIC_PATH = os.path.join(BASE_DIR, "static")
SERVER_PY = os.path.join(BASE_DIR, "server.py")
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")

print("=" * 60)
print("  🚀 Building Standalone AirDesk.exe with PyInstaller...")
print("=" * 60)

# Build command
cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--windowed",  # Opens directly as a professional Desktop GUI Application (No CMD window!)
    "--name", "AirDesk",
    "--icon", ICO_PATH,
    "--add-data", f"{STATIC_PATH};static",
    "--exclude-module", "cv2",
    "--exclude-module", "playwright",
    "--exclude-module", "scipy",
    "--exclude-module", "matplotlib",
    "--exclude-module", "tkinter",
    "--exclude-module", "yt_dlp",
    "--hidden-import", "webview",
    "--hidden-import", "webview.platforms.winforms",
    "--hidden-import", "clr",
    "--hidden-import", "pythonnet",
    "--hidden-import", "psutil",
    "--hidden-import", "uvicorn.logging",
    "--hidden-import", "uvicorn.loops",
    "--hidden-import", "uvicorn.loops.auto",
    "--hidden-import", "uvicorn.protocols",
    "--hidden-import", "uvicorn.protocols.http",
    "--hidden-import", "uvicorn.protocols.http.auto",
    "--hidden-import", "uvicorn.protocols.websockets",
    "--hidden-import", "uvicorn.protocols.websockets.auto",
    "--hidden-import", "uvicorn.lifespan",
    "--hidden-import", "uvicorn.lifespan.on",
    "--hidden-import", "dxcam",
    "--hidden-import", "mss",
    "--hidden-import", "aiortc",
    "--hidden-import", "av",
    "--hidden-import", "qrcode",
    "--hidden-import", "PIL",
    "--hidden-import", "PIL.Image",
    "--hidden-import", "PIL.ImageDraw",
    SERVER_PY
]

print(f"Running command: {' '.join(cmd)}")
res = subprocess.run(cmd, cwd=BASE_DIR)

if res.returncode != 0:
    print("\n❌ PyInstaller build failed!")
    sys.exit(1)

built_exe = os.path.join(DIST_DIR, "AirDesk.exe")
if os.path.exists(built_exe):
    # Copy to root and releases/
    root_exe = os.path.join(BASE_DIR, "AirDesk.exe")
    releases_dir = os.path.join(BASE_DIR, "releases")
    os.makedirs(releases_dir, exist_ok=True)
    release_exe = os.path.join(releases_dir, "AirDesk.exe")

    shutil.copy2(built_exe, root_exe)
    shutil.copy2(built_exe, release_exe)

    size_mb = os.path.getsize(root_exe) / (1024 * 1024)
    print("\n" + "=" * 60)
    print("  🎉 SUCCESS! Standalone AirDesk.exe Built Successfully!")
    print(f"  📦 Output Root     : {root_exe}")
    print(f"  📦 Output Releases : {release_exe}")
    print(f"  📊 Size            : {size_mb:.2f} MB")
    print("=" * 60)
else:
    print("\n❌ Built AirDesk.exe not found in dist folder!")
    sys.exit(1)
