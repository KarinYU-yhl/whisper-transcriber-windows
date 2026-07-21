"""
Build a standalone macOS application (.app) and a one-click installer (.dmg)
with PyInstaller.

Run this ON A MAC (PyInstaller cannot cross-compile from Windows/Linux):

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python build.py

Produces:
    dist/WhisperTranscriber.app                    (the application bundle)
    dist/WhisperTranscriber-<version>.dmg          (drag-to-Applications installer)
"""
import os
import shutil
import subprocess
import sys

import PyInstaller.__main__
import customtkinter
import tkinterdnd2

APP_VERSION = "1.0.27"
APP_NAME = "WhisperTranscriber"
BUNDLE_ID = "com.whisper.transcriber"

if sys.platform != "darwin":
    print("WARNING: This build script must run on macOS to produce a .app/.dmg.")

ctk_path = os.path.dirname(customtkinter.__file__)
tkdnd_path = os.path.dirname(tkinterdnd2.__file__)

# On macOS/Linux the add-data separator is ':' (it is ';' on Windows).
SEP = ":"

icon_arg = []
if os.path.exists("app_icon.icns"):
    icon_arg = ["--icon=app_icon.icns"]

print("Building macOS application...")

args = [
    "gui.py",
    f"--name={APP_NAME}",
    "--windowed",          # build a .app bundle (no terminal window)
    "--onedir",
    "--clean",
    "--noconfirm",
    f"--osx-bundle-identifier={BUNDLE_ID}",
    "--collect-all=faster_whisper",
    "--collect-all=ctranslate2",
    "--collect-all=av",            # PyAV bundles the FFmpeg libraries
    "--collect-all=tokenizers",
    "--collect-all=soundcard",     # microphone capture (bundles cffi)
    "--collect-data=customtkinter",
    f"--add-data={ctk_path}{SEP}customtkinter",
    f"--add-data={tkdnd_path}{SEP}tkinterdnd2",
    "--hidden-import=huggingface_hub",
    "--hidden-import=truststore",
    *icon_arg,
]

PyInstaller.__main__.run(args)

app_path = os.path.join("dist", f"{APP_NAME}.app")
print(f"\nBuild complete: {app_path}")
print(f"Version: {APP_VERSION}")

if not os.path.isdir(app_path):
    print("ERROR: .app bundle was not produced; skipping DMG creation.")
    sys.exit(1)


def build_dmg():
    """Package the .app into a drag-to-Applications .dmg installer."""
    dmg_name = f"{APP_NAME}-{APP_VERSION}.dmg"
    dmg_path = os.path.join("dist", dmg_name)
    staging = os.path.join("dist", "dmg_root")

    if os.path.exists(dmg_path):
        os.remove(dmg_path)
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)

    # Copy the app and add an /Applications symlink so users can drag-to-install.
    shutil.copytree(app_path, os.path.join(staging, f"{APP_NAME}.app"), symlinks=True)
    os.symlink("/Applications", os.path.join(staging, "Applications"))

    subprocess.run(
        [
            "hdiutil", "create",
            "-volname", APP_NAME,
            "-srcfolder", staging,
            "-ov",
            "-format", "UDZO",
            dmg_path,
        ],
        check=True,
    )
    shutil.rmtree(staging)
    print(f"\nInstaller created: {dmg_path}")


if sys.platform == "darwin":
    build_dmg()
else:
    print("Skipping DMG creation (not running on macOS).")
