import os
import sys
import subprocess
import zipfile
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_TOOLS = os.path.join(BASE_DIR, "build_tools")
APP_DIR = os.path.join(BASE_DIR, "android_app")
RES_DIR = os.path.join(APP_DIR, "res")
SRC_DIR = os.path.join(APP_DIR, "src")
BIN_DIR = os.path.join(APP_DIR, "bin")
MANIFEST = os.path.join(APP_DIR, "AndroidManifest.xml")

AAPT2 = os.path.join(BUILD_TOOLS, "aapt2.exe")
ANDROID_JAR = os.path.join(BUILD_TOOLS, "android.jar")
R8_JAR = os.path.join(BUILD_TOOLS, "r8.jar")
SIGNER_JAR = os.path.join(BUILD_TOOLS, "uber-apk-signer.jar")

COMPILED_RES = os.path.join(APP_DIR, "compiled_res.zip")
UNALIGNED_APK = os.path.join(APP_DIR, "unaligned.apk")
FINAL_APK = os.path.join(BASE_DIR, "AirDesk.apk")
TABLET_APK = os.path.join(BASE_DIR, "AirDesk_RedmiPadPro.apk")

def run_cmd(cmd, desc):
    print(f"--> {desc}...")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"ERROR: {desc} failed!")
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
        sys.exit(1)
    return res.stdout

def main():
    print("=" * 60)
    print("  Building AirDesk APK (Universal & Redmi Pad Pro)...")
    print("=" * 60)

    # Clean old bin and intermediate files
    if os.path.exists(BIN_DIR):
        shutil.rmtree(BIN_DIR, ignore_errors=True)
    os.makedirs(BIN_DIR, exist_ok=True)

    for temp_f in [COMPILED_RES, UNALIGNED_APK, os.path.join(APP_DIR, "unaligned-aligned-debugSigned.apk"), os.path.join(APP_DIR, "unaligned-aligned-debugSigned.apk.idsig")]:
        if os.path.exists(temp_f):
            try:
                os.remove(temp_f)
            except Exception:
                pass

    # 1. Compile Resources with aapt2
    run_cmd(f'"{AAPT2}" compile --dir "{RES_DIR}" -o "{COMPILED_RES}"', "Compiling Android resources")

    # 2. Link with aapt2 (generates R.java and initial APK structure)
    run_cmd(f'"{AAPT2}" link -I "{ANDROID_JAR}" --manifest "{MANIFEST}" -o "{UNALIGNED_APK}" "{COMPILED_RES}" --java "{SRC_DIR}" --auto-add-overlay', "Linking APK and generating R.java")

    # 3. Find all java files
    java_files = []
    for root, dirs, files in os.walk(SRC_DIR):
        for f in files:
            if f.endswith(".java"):
                java_files.append(f'"{os.path.join(root, f)}"')

    java_files_str = " ".join(java_files)

    # 4. Compile Java with javac
    run_cmd(f'javac -cp "{ANDROID_JAR}" -d "{BIN_DIR}" {java_files_str}', "Compiling Java source code")

    # 5. Find all compiled class files
    class_files = []
    for root, dirs, files in os.walk(BIN_DIR):
        for f in files:
            if f.endswith(".class"):
                class_files.append(f'"{os.path.join(root, f)}"')

    class_files_str = " ".join(class_files)

    # 6. Convert .class to classes.dex with D8
    run_cmd(f'java -cp "{R8_JAR}" com.android.tools.r8.D8 --lib "{ANDROID_JAR}" --output "{BIN_DIR}" {class_files_str}', "Dexing with D8")

    # 7. Add classes.dex into unaligned.apk
    dex_path = os.path.join(BIN_DIR, "classes.dex")
    if not os.path.exists(dex_path):
        print("ERROR: classes.dex not found!")
        sys.exit(1)

    print("--> Packaging classes.dex into APK...")
    with zipfile.ZipFile(UNALIGNED_APK, "a") as z:
        z.write(dex_path, "classes.dex")

    # 8. Sign and zipalign with uber-apk-signer (v1, v2, v3, v4 signatures)
    print("--> Signing & zipaligning APK...")
    run_cmd(f'java -jar "{SIGNER_JAR}" --apks "{UNALIGNED_APK}" -o "{APP_DIR}"', "Signing APK")

    # Find signed apk output
    signed_apk = os.path.join(APP_DIR, "unaligned-aligned-debugSigned.apk")
    if not os.path.exists(signed_apk):
        for f in os.listdir(APP_DIR):
            if f.endswith("-aligned-debugSigned.apk"):
                signed_apk = os.path.join(APP_DIR, f)
                break

    if signed_apk and os.path.exists(signed_apk):
        shutil.copy2(signed_apk, FINAL_APK)
        shutil.copy2(signed_apk, TABLET_APK)
        
        releases_dir = os.path.join(BASE_DIR, "releases")
        os.makedirs(releases_dir, exist_ok=True)
        shutil.copy2(signed_apk, os.path.join(releases_dir, "AirDesk.apk"))
        shutil.copy2(signed_apk, os.path.join(releases_dir, "AirDesk_RedmiPadPro.apk"))

        print("\n" + "=" * 60)
        print(f"  🎉 SUCCESS! AirDesk APK Built Successfully!")
        print(f"  📦 Universal APK   : {FINAL_APK}")
        print(f"  📦 Tablet APK File : {TABLET_APK}")
        print(f"  📊 Size: {os.path.getsize(FINAL_APK) / 1024:.1f} KB")
        print("=" * 60)
    else:
        print("ERROR: Signed APK not found!")
        sys.exit(1)

if __name__ == "__main__":
    main()
