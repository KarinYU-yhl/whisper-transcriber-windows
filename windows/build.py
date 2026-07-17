"""
Build a standalone Windows executable with PyInstaller.

Produces dist/WhisperTranscriber/WhisperTranscriber.exe (onedir).
Unlike the macOS build there is no code signing / notarization / DMG step.
"""
import os
import shutil

import PyInstaller.__main__
import customtkinter
import tkinterdnd2

APP_VERSION = "1.0.27"
APP_NAME = "WhisperTranscriber"

ctk_path = os.path.dirname(customtkinter.__file__)
tkdnd_path = os.path.dirname(tkinterdnd2.__file__)

# On Windows the add-data separator is ';' (it is ':' on macOS/Linux).
SEP = ";"

icon_arg = []
if os.path.exists("app_icon.ico"):
    icon_arg = ["--icon=app_icon.ico"]

print("Building Windows application...")

args = [
    "gui.py",
    f"--name={APP_NAME}",
    "--windowed",          # no console window
    "--onedir",            # a folder is easier to debug than --onefile
    "--clean",
    "--noconfirm",
    "--collect-all=faster_whisper",
    "--collect-all=ctranslate2",
    "--collect-all=av",            # PyAV bundles the FFmpeg libraries
    "--collect-all=tokenizers",
    "--collect-all=soundcard",     # WASAPI loopback + mic capture (bundles cffi)
    "--collect-data=customtkinter",
    f"--add-data={ctk_path}{SEP}customtkinter",
    f"--add-data={tkdnd_path}{SEP}tkinterdnd2",
    "--hidden-import=huggingface_hub",
    "--hidden-import=truststore",
    *icon_arg,
]

PyInstaller.__main__.run(args)

print(f"\nBuild complete: {os.path.join('dist', APP_NAME, APP_NAME + '.exe')}")
print(f"Version: {APP_VERSION}")

# Optional convenience: leave a version marker next to the exe.
dist_app_dir = os.path.join("dist", APP_NAME)
if os.path.isdir(dist_app_dir):
    with open(os.path.join(dist_app_dir, "VERSION.txt"), "w", encoding="utf-8") as f:
        f.write(APP_VERSION + "\n")
