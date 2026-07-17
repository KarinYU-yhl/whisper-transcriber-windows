import PyInstaller.__main__
import os
import shutil
import customtkinter
import tkinterdnd2
import subprocess
import importlib.util
import plistlib

# Application version
APP_VERSION = "1.0.27"

# Get customtkinter path to include its data files
ctk_path = os.path.dirname(customtkinter.__file__)

# Get tkinterdnd2 path to include its data files
tkdnd_path = os.path.dirname(tkinterdnd2.__file__)

# Get mlx path to include metallib (for macOS 26+)
mlx_spec = importlib.util.find_spec("mlx")
mlx_path = mlx_spec.submodule_search_locations[0]
mlx_metallib = os.path.join(mlx_path, "lib", "mlx.metallib")
mlx_libmlx = os.path.join(mlx_path, "lib", "libmlx.dylib")

# macOS 15 compatible mlx package directory (downloaded from PyPI)
macos15_mlx_src = "macos15_mlx"

# Create a copy named default.metallib for compatibility if needed
default_metallib_path = "default.metallib"
if os.path.exists(mlx_metallib):
    shutil.copy2(mlx_metallib, default_metallib_path)
else:
    print(f"Warning: mlx.metallib not found at {mlx_metallib}")

app_name = "MLXWhisperTranscriber"

print("Building Application Bundle...")
args = [
    'gui.py',
    '--name=MLXWhisperTranscriber',
    '--windowed',  # No terminal window
    '--icon=app_icon.icns', # Application Icon
    '--onedir',    # Create a directory (easier for debugging than --onefile)
    '--clean',
    '--noconfirm',
    '--hidden-import=mlx',
    '--hidden-import=mlx.core',
    '--hidden-import=mlx.nn',
    '--collect-all=mlx',
    '--collect-all=mlx_whisper',
    f'--add-data={ctk_path}:customtkinter',  # Include customtkinter themes/images
    f'--add-data={tkdnd_path}:tkinterdnd2',  # Include tkinterdnd2 binaries
    '--runtime-hook=runtime_hook.py',  # Run before main app to setup mlx libraries
]

if os.path.exists(mlx_metallib):
    # args.append(f'--add-data={mlx_metallib}:.') # Add mlx.metallib to root
    # args.append(f'--add-data={mlx_metallib}:mlx/lib') # Add mlx.metallib to mlx/lib
    pass

if os.path.exists(default_metallib_path):
    # args.append(f'--add-data={default_metallib_path}:.') # Add default.metallib to root
    pass

PyInstaller.__main__.run(args)

# Clean up temp file
if os.path.exists(default_metallib_path):
    os.remove(default_metallib_path)

# Post-processing: Copy metallib files to ensure they are found
dist_dir = "dist"
resources_dir = os.path.join(dist_dir, f"{app_name}.app", "Contents", "Resources")
frameworks_dir = os.path.join(dist_dir, f"{app_name}.app", "Contents", "Frameworks")
# mlx is in Frameworks/mlx/lib
frameworks_mlx_lib_dir = os.path.join(frameworks_dir, "mlx", "lib")
# Try to find mlx.metallib in Frameworks first
source_metallib = os.path.join(frameworks_mlx_lib_dir, "mlx.metallib")

if not os.path.exists(source_metallib):
    # Fallback to Resources if not found in Frameworks (unlikely for onedir)
    print(f"  Warning: mlx.metallib not found in {source_metallib}")
    source_metallib = os.path.join(resources_dir, "mlx", "lib", "mlx.metallib")

print("Setting up dual macOS version support...")

macos15_mlx_src = "macos15_mlx"
macos15_mlx_dest = os.path.join(resources_dir, "macos15_mlx")

if os.path.exists(macos15_mlx_src):
    if os.path.exists(macos15_mlx_dest):
        shutil.rmtree(macos15_mlx_dest)
    shutil.copytree(macos15_mlx_src, macos15_mlx_dest)
    print(f"  Copied macOS 15 mlx package to: {macos15_mlx_dest}")
    
    # Ensure the copied files are writable so they can be signed
    subprocess.run(["chmod", "-R", "u+w", macos15_mlx_dest], check=True)
else:
    print(f"  Warning: macOS 15 mlx source not found: {macos15_mlx_src}")

if os.path.exists(source_metallib):
    print(f"Ensuring metallib files are in place (source: {source_metallib})...")
    # Copy to root as default.metallib (required by mlx)
    target_default = os.path.join(resources_dir, "default.metallib")
    if os.path.exists(target_default) or os.path.islink(target_default):
        os.remove(target_default)
    shutil.copy2(source_metallib, target_default)
    print(f"  Copied: {target_default}")
    
    # Copy to root as mlx.metallib (just in case)
    target_mlx = os.path.join(resources_dir, "mlx.metallib")
    if os.path.exists(target_mlx) or os.path.islink(target_mlx):
        os.remove(target_mlx)
    shutil.copy2(source_metallib, target_mlx)
    print(f"  Copied: {target_mlx}")
else:
    print(f"  Error: Source metallib not found at {source_metallib}")
    print(f"  Contents of frameworks/mlx/lib: {os.listdir(frameworks_mlx_lib_dir) if os.path.exists(frameworks_mlx_lib_dir) else 'Not found'}")

# Update Info.plist with version information
print("Updating Info.plist with version information...")
info_plist_path = os.path.join(dist_dir, f"{app_name}.app", "Contents", "Info.plist")
if os.path.exists(info_plist_path):
    with open(info_plist_path, 'rb') as f:
        plist = plistlib.load(f)
    
    plist['CFBundleShortVersionString'] = APP_VERSION
    plist['CFBundleVersion'] = APP_VERSION
    plist['CFBundleIdentifier'] = 'com.necoha.mlxwhispertranscriber'
    plist['NSHumanReadableCopyright'] = f'Copyright © 2025 necoha. All rights reserved.'
    
    with open(info_plist_path, 'wb') as f:
        plistlib.dump(plist, f)
    print(f"  Set version to: {APP_VERSION}")

# Remove .dist-info directories to avoid signing errors
print("Removing .dist-info directories...")
contents_dir = os.path.join(dist_dir, f"{app_name}.app", "Contents")
for root, dirs, files in os.walk(contents_dir, topdown=True):
    # Remove files and broken symlinks
    for f in files:
        if f.endswith(".dist-info"):
            dist_info_path = os.path.join(root, f)
            print(f"  Removing file/link: {dist_info_path}")
            os.remove(dist_info_path)
            
    # Remove directories
    for d in list(dirs):
        if d.endswith(".dist-info"):
            dist_info_path = os.path.join(root, d)
            print(f"  Removing dir: {dist_info_path}")
            if os.path.islink(dist_info_path):
                os.unlink(dist_info_path)
            else:
                shutil.rmtree(dist_info_path)
            dirs.remove(d) # Prevent recursion

# Code signing
SIGNING_IDENTITY = "Developer ID Application: Kazuki Tsutsumi (PJ6C64J6UP)"
NOTARY_PROFILE = "MLXWhisperNotaryProfile"
print(f"Signing application with identity: {SIGNING_IDENTITY}...")
app_path_for_signing = os.path.join(dist_dir, f"{app_name}.app")
entitlements_path = "entitlements.plist"

try:
    # For notarization, we need to sign all Mach-O binaries and metallib files properly
    
    print("  Finding and signing all Mach-O binaries...")
    
    # Use find and file commands to get all Mach-O binaries
    find_result = subprocess.run(
        f'find "{app_path_for_signing}" -type f -exec file {{}} \\; | grep -E "Mach-O|bundle" | cut -d: -f1',
        shell=True, capture_output=True, text=True
    )
    
    mach_o_files = [f.strip() for f in find_result.stdout.strip().split('\n') if f.strip()]
    
    # Also find .metallib files - they need to be signed too
    metallib_result = subprocess.run(
        f'find "{app_path_for_signing}" -name "*.metallib" -type f',
        shell=True, capture_output=True, text=True
    )
    metallib_files = [f.strip() for f in metallib_result.stdout.strip().split('\n') if f.strip()]
    
    # Combine all files that need signing
    all_files_to_sign = mach_o_files + metallib_files
    
    # Sign each file individually (from deepest to shallowest)
    all_files_to_sign.sort(key=lambda x: x.count('/'), reverse=True)
    
    for filepath in all_files_to_sign:
        if os.path.islink(filepath):
            continue
        try:
            subprocess.run([
                "codesign", "--force", "--options", "runtime", "--timestamp",
                "--entitlements", entitlements_path,
                "--sign", SIGNING_IDENTITY,
                filepath
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            # Log failed files but continue
            print(f"    Warning: Could not sign {os.path.basename(filepath)}")
    
    print("  Signing app bundle...")
    # Finally sign the app bundle itself
    subprocess.run([
        "codesign", "--force", "--options", "runtime", "--timestamp",
        "--entitlements", entitlements_path,
        "--sign", SIGNING_IDENTITY,
        app_path_for_signing
    ], check=True)
    
    # Verify the signature
    print("  Verifying signature...")
    verify_result = subprocess.run([
        "codesign", "--verify", "--deep", "--strict", app_path_for_signing
    ], capture_output=True, text=True)
    
    if verify_result.returncode != 0:
        print(f"    Warning: Verification issues: {verify_result.stderr}")
    else:
        print("  App signing completed successfully")
        
except subprocess.CalledProcessError as e:
    print(f"  Warning: App signing failed: {e}")

print("Creating DMG Installer...")

dist_dir = "dist"
app_path = os.path.join(dist_dir, f"{app_name}.app")
dmg_path = os.path.join(dist_dir, f"{app_name}.dmg")
tmp_dmg_dir = os.path.join(dist_dir, "dmg_temp")

# Clean up previous DMG and temp dir
if os.path.exists(dmg_path):
    os.remove(dmg_path)
if os.path.exists(tmp_dmg_dir):
    shutil.rmtree(tmp_dmg_dir)

# Create temp dir for DMG content
os.makedirs(tmp_dmg_dir)

# Copy App to temp dir using ditto to preserve code signatures and extended attributes
print(f"Copying {app_name}.app to temporary DMG folder...")
subprocess.run([
    "ditto", app_path, os.path.join(tmp_dmg_dir, f"{app_name}.app")
], check=True)

# Create symlink to /Applications
print("Creating /Applications link...")
os.symlink("/Applications", os.path.join(tmp_dmg_dir, "Applications"))

# Create DMG
print(f"Generating {app_name}.dmg...")
subprocess.run([
    "hdiutil", "create",
    "-volname", app_name,
    "-srcfolder", tmp_dmg_dir,
    "-ov",
    "-format", "UDZO",
    dmg_path
], check=True)

# Sign DMG
print("Signing DMG...")
try:
    subprocess.run([
        "codesign", "--sign", SIGNING_IDENTITY, "--timestamp",
        dmg_path
    ], check=True)
    print("  DMG signing completed successfully")
except subprocess.CalledProcessError as e:
    print(f"  Warning: DMG signing failed: {e}")

# Notarize DMG
print(f"Notarizing DMG using keychain profile '{NOTARY_PROFILE}'...")
try:
    result = subprocess.run([
        "xcrun", "notarytool", "submit", dmg_path,
        "--keychain-profile", NOTARY_PROFILE,
        "--wait"
    ], check=True, capture_output=True, text=True)
    print(result.stdout)
    
    # Check if notarization was successful by looking for "status: Accepted"
    if "Invalid" in result.stdout or "Rejected" in result.stdout:
        print("  Warning: Notarization was not accepted. Skipping stapling.")
    else:
        print("  Notarization completed. Stapling ticket to DMG...")
        try:
            subprocess.run([
                "xcrun", "stapler", "staple", dmg_path
            ], check=True)
            print("  Stapling completed successfully.")
        except subprocess.CalledProcessError as e2:
            print(f"  Warning: Stapling failed: {e2}")

except subprocess.CalledProcessError as e:
    print(f"  Warning: Notarization failed: {e}")
    print(f"  Please ensure you have created the keychain profile '{NOTARY_PROFILE}' using:")
    print(f"  xcrun notarytool store-credentials \"{NOTARY_PROFILE}\" --apple-id <YOUR_APPLE_ID> --team-id <YOUR_TEAM_ID> --password <APP_SPECIFIC_PASSWORD>")

# Cleanup
shutil.rmtree(tmp_dmg_dir)

print(f"Build Complete! DMG is available at: {dmg_path}")
