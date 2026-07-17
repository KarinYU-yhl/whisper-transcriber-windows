"""
Runtime hook for PyInstaller.
This runs BEFORE the main application and any imports.
Detects macOS version and modifies sys.path to load the correct mlx package.
"""
import os
import sys
import platform

def log(msg):
    """Write to stderr for debugging."""
    try:
        if sys.stderr:
            sys.stderr.write(f"[runtime_hook] {msg}\n")
            sys.stderr.flush()
    except Exception:
        pass

def get_macos_version():
    """Get macOS major version number."""
    try:
        version = platform.mac_ver()[0]  # e.g., "15.7.2" or "26.1"
        if not version:
            return 15 # Fallback
        major = int(version.split('.')[0])
        return major
    except:
        return 15  # Default to macOS 15 if detection fails

def setup_mlx_path():
    """Prepend compatible mlx package path to sys.path."""
    if not getattr(sys, 'frozen', False):
        log("Not frozen, skipping")
        return
    
    macos_version = get_macos_version()
    log(f"macOS version: {macos_version}")
    
    # Only needed for macOS < 26 (assuming 26 is the cutoff for the new mlx)
    # Adjust this logic based on which version needs the "old" mlx
    if macos_version >= 26:
        log("macOS 26+, using default bundled libraries")
        return
    
    log("macOS < 26, switching to macos15_mlx package")
    log(f"sys.executable: {sys.executable}")
    log(f"sys.frozen: {getattr(sys, 'frozen', 'Not Set')}")
    log(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'Not Set')}")
    
    # Potential paths to search for macos15_mlx
    candidate_paths = []
    
    # 1. Check relative to executable (Onedir standard)
    # sys.executable -> Contents/MacOS/MLXWhisperTranscriber
    app_dir = os.path.dirname(sys.executable)
    contents_dir = os.path.dirname(app_dir)
    resources_dir = os.path.join(contents_dir, "Resources")
    candidate_paths.append(os.path.join(resources_dir, "macos15_mlx"))
    
    # 2. Check inside _MEIPASS (Onefile or specific temp dirs)
    if hasattr(sys, '_MEIPASS'):
        candidate_paths.append(os.path.join(sys._MEIPASS, "macos15_mlx"))
        
    # 3. Check Frameworks just in case
    frameworks_dir = os.path.join(contents_dir, "Frameworks")
    candidate_paths.append(os.path.join(frameworks_dir, "macos15_mlx"))

    found_path = None
    for path in candidate_paths:
        log(f"Checking path: {path}")
        if os.path.exists(path):
            found_path = path
            break
            
    if found_path:
        log(f"Found macos15_mlx at: {found_path}")
        # Prepend to sys.path so it takes precedence over standard library
        sys.path.insert(0, found_path)
        log("Added to sys.path[0]")
        
        # Verify
        try:
            import importlib.util
            spec = importlib.util.find_spec("mlx")
            if spec:
                log(f"mlx resolves to: {spec.origin}")
        except Exception as e:
            log(f"Could not verify mlx import: {e}")
    else:
        log("ERROR: macos15_mlx not found in any candidate path!")
        log(f"Contents of Resources: {os.listdir(resources_dir) if os.path.exists(resources_dir) else 'Not found'}")

# Execute on import
setup_mlx_path()
