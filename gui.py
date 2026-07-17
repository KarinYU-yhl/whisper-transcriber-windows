import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import tkinterdnd2
from tkinterdnd2 import DND_FILES
import threading
import os
import sys

# Note: mlx library setup is handled by runtime_hook.py (PyInstaller runtime hook)
# which runs before any imports and replaces libraries based on macOS version

import mlx_whisper
import shutil
import truststore
import webbrowser
import subprocess
import multiprocessing
import queue
import json
from huggingface_hub import try_to_load_from_cache, scan_cache_dir

# Inject system trust store for corporate proxies/SSL inspection
truststore.inject_into_ssl()

# Add Homebrew paths to PATH for macOS app bundles (GUI apps don't inherit shell PATH)
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin" + os.pathsep + "/usr/local/bin"

CONFIG_FILE = os.path.expanduser("~/.mlx_whisper_config.json")

# Configuration
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

def transcription_worker(result_queue, audio_path, model_name, language_code, language_name):
    """
    Worker process for transcription.
    Runs in a separate process to allow termination (Stop button).
    """
    import sys
    import os
    import time
    
    # Set up MLX metallib path BEFORE importing mlx_whisper in subprocess
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            # Onefile mode
            bundle_dir = sys._MEIPASS
        else:
            # Onedir mode: sys.executable is in Contents/MacOS/MLXWhisperTranscriber
            # Resources are in Contents/Resources
            # Frameworks are in Contents/Frameworks
            app_dir = os.path.dirname(sys.executable)
            # Go up to Contents
            contents_dir = os.path.dirname(app_dir)
            bundle_dir = os.path.join(contents_dir, "Resources")
            
        # Check Resources/mlx/lib/mlx.metallib first
        metallib_path = os.path.join(bundle_dir, "mlx", "lib", "mlx.metallib")
        if not os.path.exists(metallib_path):
             # Fallback to Resources/default.metallib
             metallib_path = os.path.join(bundle_dir, "default.metallib")
             
        if os.path.exists(metallib_path):
            os.environ["MLX_METALLIB_PATH"] = metallib_path
            # Also set DYLD_LIBRARY_PATH to ensure linked libraries are found if needed
            # os.environ["DYLD_LIBRARY_PATH"] = os.path.join(contents_dir, "Frameworks")
    
    # Re-import necessary modules in the new process
    import mlx_whisper
    import truststore
    
    # Re-inject truststore and path
    truststore.inject_into_ssl()
    # Ensure PATH is correct in the subprocess
    if "/opt/homebrew/bin" not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin" + os.pathsep + "/usr/local/bin"

    class QueueLogger:
        def __init__(self, queue):
            self.queue = queue
        def write(self, msg):
            # Filter out empty newlines to reduce queue traffic
            if msg:
                self.queue.put(("log", msg))
        def flush(self):
            pass

    # Redirect stdout/stderr to the queue
    sys.stdout = QueueLogger(result_queue)
    sys.stderr = QueueLogger(result_queue)

    try:
        print(f"Starting transcription for: {audio_path}")
        print(f"Loading model ({model_name})...")

        transcribe_args = {
            "audio": audio_path,
            "path_or_hf_repo": model_name,
            "verbose": True
        }
        
        if language_code:
            transcribe_args["language"] = language_code
            print(f"Language set to: {language_name} ({language_code})")
        else:
            print("Language: Auto-detect")

        # Run transcription
        start_time = time.time()
        result = mlx_whisper.transcribe(**transcribe_args)
        end_time = time.time()
        duration = end_time - start_time
        
        # Send result back
        result_queue.put(("success", (result["text"], duration)))
        
    except Exception as e:
        result_queue.put(("error", str(e)))


class CacheManagerDialog(ctk.CTkToplevel):
    """Dialog for managing Hugging Face model cache."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        self.title("Model Cache Manager")
        self.geometry("700x450")
        self.resizable(True, True)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Downloaded Models (Hugging Face Cache)",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.title_label.pack(side="left")
        
        self.refresh_button = ctk.CTkButton(
            self.header_frame,
            text="Refresh",
            command=self.refresh_cache_list,
            width=80
        )
        self.refresh_button.pack(side="right")
        
        # Cache location info
        self.cache_path_label = ctk.CTkLabel(
            self,
            text=f"Cache Location: ~/.cache/huggingface/hub",
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        self.cache_path_label.pack(fill="x", padx=20, pady=(0, 10))
        
        # Scrollable frame for model list
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=650, height=280)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Total size label
        self.total_size_label = ctk.CTkLabel(
            self,
            text="Total: Calculating...",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.total_size_label.pack(pady=(5, 10))
        
        # Close button
        self.close_button = ctk.CTkButton(
            self,
            text="Close",
            command=self.destroy,
            width=100
        )
        self.close_button.pack(pady=(0, 20))
        
        # Load cache info
        self.model_checkboxes = {}
        self.refresh_cache_list()
        
        # Center window
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def format_size(self, size_bytes):
        """Format size in bytes to human readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def refresh_cache_list(self):
        """Refresh the list of cached models."""
        # Clear existing widgets
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.model_checkboxes.clear()
        
        try:
            cache_info = scan_cache_dir()
            
            # Filter for whisper models (mlx-community)
            whisper_repos = [repo for repo in cache_info.repos 
                           if 'whisper' in repo.repo_id.lower() or 'mlx-community' in repo.repo_id.lower()]
            
            if not whisper_repos:
                no_model_label = ctk.CTkLabel(
                    self.scroll_frame,
                    text="No Whisper models found in cache.\n\nModels will appear here after downloading.",
                    text_color="gray"
                )
                no_model_label.pack(pady=50)
                self.total_size_label.configure(text="Total: 0 MB")
                return
            
            total_size = 0
            
            for repo in sorted(whisper_repos, key=lambda r: r.size_on_disk, reverse=True):
                total_size += repo.size_on_disk
                
                # Create frame for each model
                model_frame = ctk.CTkFrame(self.scroll_frame)
                model_frame.pack(fill="x", padx=5, pady=5)
                model_frame.grid_columnconfigure(1, weight=1)
                
                # Checkbox for selection
                var = ctk.BooleanVar(value=False)
                checkbox = ctk.CTkCheckBox(
                    model_frame,
                    text="",
                    variable=var,
                    width=20
                )
                checkbox.grid(row=0, column=0, padx=(10, 5), pady=10)
                
                # Store reference for deletion
                self.model_checkboxes[repo.repo_id] = {
                    'var': var,
                    'repo': repo
                }
                
                # Model name and size
                info_frame = ctk.CTkFrame(model_frame, fg_color="transparent")
                info_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
                
                name_label = ctk.CTkLabel(
                    info_frame,
                    text=repo.repo_id,
                    font=ctk.CTkFont(size=13, weight="bold"),
                    anchor="w"
                )
                name_label.pack(fill="x", anchor="w")
                
                size_label = ctk.CTkLabel(
                    info_frame,
                    text=f"Size: {self.format_size(repo.size_on_disk)}",
                    text_color="gray",
                    font=ctk.CTkFont(size=12),
                    anchor="w"
                )
                size_label.pack(fill="x", anchor="w")
                
                # Delete button for individual model
                delete_btn = ctk.CTkButton(
                    model_frame,
                    text="Delete",
                    command=lambda r=repo: self.delete_single_model(r),
                    width=70,
                    height=28,
                    fg_color="#DC2626",
                    hover_color="#B91C1C"
                )
                delete_btn.grid(row=0, column=2, padx=10, pady=10)
            
            # Update total size
            self.total_size_label.configure(text=f"Total: {self.format_size(total_size)}")
            
            # Add delete selected button if there are models
            if whisper_repos:
                delete_selected_btn = ctk.CTkButton(
                    self.scroll_frame,
                    text="Delete Selected",
                    command=self.delete_selected_models,
                    fg_color="#DC2626",
                    hover_color="#B91C1C"
                )
                delete_selected_btn.pack(pady=15)
                
        except Exception as e:
            error_label = ctk.CTkLabel(
                self.scroll_frame,
                text=f"Error loading cache: {e}",
                text_color="red"
            )
            error_label.pack(pady=50)
    
    def delete_single_model(self, repo):
        """Delete a single model from cache."""
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete:\n\n{repo.repo_id}\n\nSize: {self.format_size(repo.size_on_disk)}\n\nThis action cannot be undone.",
            parent=self
        )
        
        if confirm:
            try:
                # Get all revision commit hashes for this repo
                revision_hashes = [rev.commit_hash for rev in repo.revisions]
                
                # Delete using the cache API
                cache_info = scan_cache_dir()
                delete_strategy = cache_info.delete_revisions(*revision_hashes)
                
                # Show what will be freed
                freed_size = delete_strategy.expected_freed_size
                
                # Execute deletion
                delete_strategy.execute()
                
                messagebox.showinfo(
                    "Deleted",
                    f"Successfully deleted {repo.repo_id}\n\nFreed: {self.format_size(freed_size)}",
                    parent=self
                )
                
                # Refresh the list
                self.refresh_cache_list()
                
                # Update cache status in main window
                self.parent.on_model_change(self.parent.model_var.get())
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete model:\n{e}", parent=self)
    
    def delete_selected_models(self):
        """Delete all selected models."""
        selected = [(repo_id, data) for repo_id, data in self.model_checkboxes.items() 
                    if data['var'].get()]
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select models to delete.", parent=self)
            return
        
        # Calculate total size
        total_size = sum(data['repo'].size_on_disk for _, data in selected)
        model_names = "\n".join([repo_id for repo_id, _ in selected])
        
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete {len(selected)} model(s)?\n\n{model_names}\n\nTotal size: {self.format_size(total_size)}\n\nThis action cannot be undone.",
            parent=self
        )
        
        if confirm:
            try:
                # Collect all revision hashes
                all_hashes = []
                for _, data in selected:
                    for rev in data['repo'].revisions:
                        all_hashes.append(rev.commit_hash)
                
                # Delete using the cache API
                cache_info = scan_cache_dir()
                delete_strategy = cache_info.delete_revisions(*all_hashes)
                freed_size = delete_strategy.expected_freed_size
                delete_strategy.execute()
                
                messagebox.showinfo(
                    "Deleted",
                    f"Successfully deleted {len(selected)} model(s)\n\nFreed: {self.format_size(freed_size)}",
                    parent=self
                )
                
                # Refresh the list
                self.refresh_cache_list()
                
                # Update cache status in main window
                self.parent.on_model_change(self.parent.model_var.get())
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete models:\n{e}", parent=self)


class App(ctk.CTk, tkinterdnd2.TkinterDnD.DnDWrapper):
    MODEL_INFO = {
        "mlx-community/whisper-tiny": "Speed: ★★★★★ | Accuracy: ★☆☆☆☆ (Fastest, MLX Optimized)",
        "mlx-community/whisper-base": "Speed: ★★★★☆ | Accuracy: ★★☆☆☆ (Fast, MLX Optimized)",
        "mlx-community/whisper-small": "Speed: ★★★☆☆ | Accuracy: ★★★☆☆ (Balanced, MLX Optimized)",
        "mlx-community/whisper-medium": "Speed: ★★☆☆☆ | Accuracy: ★★★★☆ (High Accuracy, MLX Optimized)",
        "mlx-community/whisper-large-v3": "Speed: ★☆☆☆☆ | Accuracy: ★★★★★ (Best Accuracy, MLX Optimized)",
        "mlx-community/whisper-large-v3-mlx": "Speed: ★☆☆☆☆ | Accuracy: ★★★★★ (Best Accuracy, MLX Optimized)",
        "mlx-community/whisper-large-v3-turbo": "Speed: ★★★☆☆ | Accuracy: ★★★★★ (Fast, High Accuracy, Recommended, MLX Optimized)",
    }

    LANGUAGE_CODES = {
        "English": "en",
        "Chinese": "zh",
        "German": "de",
        "Spanish": "es",
        "Russian": "ru",
        "French": "fr",
        "Portuguese": "pt",
        "Japanese": "ja",
        "Korean": "ko",
        "Italian": "it",
        "Dutch": "nl",
        "Polish": "pl",
        "Turkish": "tr",
        "Vietnamese": "vi",
        "Indonesian": "id",
        "Thai": "th",
        "Arabic": "ar",
        "Hindi": "hi",
        "Swedish": "sv",
        "Czech": "cs",
    }

    def __init__(self):
        super().__init__()
        self.TkdndVersion = tkinterdnd2.TkinterDnD._require(self)

        # Window setup
        self.title("MLX Whisper Transcriber")
        self.geometry("850x550")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Check for FFmpeg
        if not shutil.which("ffmpeg"):
            messagebox.showwarning("Missing Dependency", "FFmpeg not found.\nPlease install it via 'brew install ffmpeg' to ensure audio processing works.")

        # Title Label
        self.title_label = ctk.CTkLabel(self, text="MLX Whisper Transcriber", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # File Selection Frame
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.file_frame.grid_columnconfigure(0, weight=1)

        self.file_path_entry = ctk.CTkEntry(self.file_frame, placeholder_text="Select an audio file...")
        self.file_path_entry.grid(row=0, column=0, padx=(10, 10), pady=10, sticky="ew")

        self.browse_button = ctk.CTkButton(self.file_frame, text="Browse", command=self.browse_file, width=100)
        self.browse_button.grid(row=0, column=1, padx=(0, 10), pady=10)

        # Model Selection
        self.model_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.model_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.model_frame.grid_columnconfigure(1, weight=1)

        # Row 0: Controls
        self.model_label = ctk.CTkLabel(self.model_frame, text="Model:", font=ctk.CTkFont(weight="bold"))
        self.model_label.grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.model_var = ctk.StringVar(value="mlx-community/whisper-large-v3")
        self.model_select_menu = ctk.CTkOptionMenu(
            self.model_frame,
            values=[
                "mlx-community/whisper-large-v3",
                "mlx-community/whisper-large-v3-mlx",
                "mlx-community/whisper-large-v3-turbo",
                "mlx-community/whisper-tiny",
                "mlx-community/whisper-base",
                "mlx-community/whisper-small",
                "mlx-community/whisper-medium"
            ],
            variable=self.model_var,
            command=self.on_model_change
        )
        self.model_select_menu.grid(row=0, column=1, padx=(0, 10), sticky="ew")

        self.local_model_button = ctk.CTkButton(self.model_frame, text="Load Local...", command=self.select_local_model, width=100, fg_color="green")
        self.local_model_button.grid(row=0, column=2, padx=(0, 10), sticky="w")

        self.help_button = ctk.CTkButton(self.model_frame, text="?", command=self.show_help, width=30, fg_color="gray")
        self.help_button.grid(row=0, column=3, padx=(0, 5), sticky="w")

        self.cache_manage_button = ctk.CTkButton(self.model_frame, text="Manage Cache", command=self.show_cache_manager, width=100, fg_color="#6B7280")
        self.cache_manage_button.grid(row=0, column=4, padx=(0, 10), sticky="w")

        self.cache_status_label = ctk.CTkLabel(self.model_frame, text="Checking...", text_color="gray")
        self.cache_status_label.grid(row=0, column=5, padx=(0, 0), sticky="w")

        # Row 1: Path/URL Display
        self.path_label = ctk.CTkLabel(self.model_frame, text="Source:", font=ctk.CTkFont(size=12))
        self.path_label.grid(row=1, column=0, padx=(0, 10), pady=(5, 0), sticky="w")

        self.model_source_link = ctk.CTkButton(
            self.model_frame,
            text="mlx-community/whisper-large-v3",
            fg_color="transparent",
            text_color=("blue", "#4DA6FF"),
            anchor="w",
            font=ctk.CTkFont(size=12, underline=True),
            hover_color=("gray85", "gray25"),
            command=self.open_source
        )
        self.model_source_link.grid(row=1, column=1, columnspan=5, padx=(0, 0), pady=(5, 0), sticky="ew")

        # Row 2: Model Info
        self.model_info_label = ctk.CTkLabel(self.model_frame, text="", text_color="gray", font=ctk.CTkFont(size=12))
        self.model_info_label.grid(row=2, column=0, columnspan=6, padx=(0, 10), pady=(5, 0), sticky="w")

        # Variables
        self.selected_file = None
        self.file_queue = []  # Queue for batch processing
        self.batch_total_files = 0
        self.batch_total_duration = 0.0
        self.is_transcribing = False
        self.process = None
        self.result_queue = None
        # Remember last visited directory for models
        self.last_model_dir = os.path.join(os.getcwd(), "models") if os.path.exists(os.path.join(os.getcwd(), "models")) else os.getcwd()

        # Load saved configuration (before initial on_model_change to avoid overwriting)
        self.load_config()

        # Initial check (if load_config didn't trigger it, or to ensure UI update)
        # If load_config set a model, on_model_change was already called.
        # If not, we call it with the default.
        # To be safe, we can just call it. It's idempotent-ish (updates UI).
        self.on_model_change(self.model_var.get())

        # Options Frame (Language)
        self.options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.options_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.language_label = ctk.CTkLabel(self.options_frame, text="Language:", font=ctk.CTkFont(weight="bold"))
        self.language_label.grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.language_var = ctk.StringVar(value="Auto")
        self.language_menu = ctk.CTkOptionMenu(
            self.options_frame,
            values=["Auto"] + list(self.LANGUAGE_CODES.keys()),
            variable=self.language_var
        )
        self.language_menu.grid(row=0, column=1, padx=(0, 10), sticky="w")

        # Status / Result Area (Tabs)
        self.tabview = ctk.CTkTabview(self, width=500, height=200)
        self.tabview.grid(row=4, column=0, padx=20, pady=10, sticky="nsew")
        self.grid_rowconfigure(4, weight=1) # Make the text area expandable
        
        self.tab_logs = self.tabview.add("Logs")
        self.tab_result = self.tabview.add("Result")
        
        # Log Textbox
        self.tabview.set("Logs")
        self.log_textbox = ctk.CTkTextbox(self.tab_logs, width=500, height=150)
        self.log_textbox.pack(expand=True, fill="both")
        self.log_textbox.insert("0.0", "Ready to transcribe.\n")
        self.log_textbox.configure(state="disabled")

        # Result Textbox
        self.result_textbox = ctk.CTkTextbox(self.tab_result, width=500, height=150)
        self.result_textbox.pack(expand=True, fill="both")

        # Action Buttons
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=5, column=0, padx=20, pady=20)

        self.transcribe_button = ctk.CTkButton(self.button_frame, text="Start Transcription", command=self.start_transcription_thread, font=ctk.CTkFont(size=15, weight="bold"), height=40, width=200)
        self.transcribe_button.pack()

        # Progress Bar (Indeterminate)
        self.progress_bar = ctk.CTkProgressBar(self.button_frame, width=400, mode="indeterminate")
        # self.progress_bar.pack(pady=10) # Packed only when running

        # Enable Drag & Drop
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.drop_file)

    def drop_file(self, event):
        # Parse dropped files (handles spaces and multiple files)
        try:
            files = self.tk.splitlist(event.data)
        except Exception:
            # Fallback for simple string
            files = [event.data]

        if not files:
            return

        self.file_queue = list(files)
        self.batch_total_files = len(files)
        self.batch_total_duration = 0.0
        
        # Update UI
        self.file_path_entry.delete(0, "end")
        if len(files) == 1:
            self.selected_file = files[0]
            self.file_path_entry.insert(0, files[0])
            self.log_message(f"Selected file: {os.path.basename(files[0])}")
        else:
            self.selected_file = files[0] # Set first file as primary for now
            self.file_path_entry.insert(0, f"{len(files)} files selected for batch processing")
            self.log_message(f"Selected {len(files)} files for batch processing:")
            for f in files:
                self.log_message(f" - {os.path.basename(f)}")

    def load_config(self):
        """Load configuration from JSON file."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    
                # Restore last model directory
                if "last_model_dir" in config and os.path.isdir(config["last_model_dir"]):
                    self.last_model_dir = config["last_model_dir"]
                
                # Restore last selected model
                if "last_model" in config:
                    last_model = config["last_model"]
                    # If it's a local path, ensure it exists and add to dropdown
                    if os.path.isdir(last_model):
                        if last_model not in self.model_select_menu._values:
                            current_values = self.model_select_menu._values
                            self.model_select_menu.configure(values=[last_model] + current_values)
                        self.model_var.set(last_model)
                        self.on_model_change(last_model)
                    # If it's a HF repo, just set it
                    elif last_model in self.model_select_menu._values:
                        self.model_var.set(last_model)
                        self.on_model_change(last_model)
                        
            except Exception as e:
                print(f"Failed to load config: {e}")

    def save_config(self):
        """Save configuration to JSON file."""
        config = {
            "last_model_dir": self.last_model_dir,
            "last_model": self.model_var.get()
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def select_local_model(self):
        folder_path = filedialog.askdirectory(title="Select Model Folder", initialdir=self.last_model_dir)
        if not folder_path:
            return
        
        # Update last visited directory (parent of the selected folder)
        self.last_model_dir = os.path.dirname(folder_path)
        self.save_config()

        # Check if config.json exists, if not search subdirectories
        found_paths = []
        
        # Check root first
        if os.path.exists(os.path.join(folder_path, "config.json")):
            found_paths.append(folder_path)
        else:
            self.log_message("Searching for models in subdirectories...")
            for root, dirs, files in os.walk(folder_path):
                if "config.json" in files:
                    found_paths.append(root)
                    # Don't traverse inside a model folder (optimization)
                    dirs[:] = []
        
        if not found_paths:
            messagebox.showwarning("Invalid Model Folder", "Could not find 'config.json' in the selected folder or its subdirectories.\nPlease select a valid Hugging Face model folder.")
            return

        # Sort paths to ensure consistent order
        found_paths.sort()

        # Update dropdown with found local models
        current_values = self.model_select_menu._values
        # Add new paths to the top, removing duplicates
        new_values = found_paths + [v for v in current_values if v not in found_paths]
        self.model_select_menu.configure(values=new_values)

        # Select the first found model (or the one that matches current selection if possible?)
        # For now, just select the first one found, but let user switch.
        target_path = found_paths[0]
        self.model_var.set(target_path)
        self.on_model_change(target_path)
        
        self.log_message(f"Selected local model path: {target_path}")
        if len(found_paths) > 1:
            self.log_message(f"Found {len(found_paths)} models in the folder. You can switch between them in the dropdown.")
        elif target_path != folder_path:
            self.log_message(f"(Auto-detected model inside subfolder)")

    def show_cache_manager(self):
        """Show cache management dialog."""
        CacheManagerDialog(self)

    def show_help(self):
        help_text = (
            "How to use Local Models (Offline Mode):\n\n"
            "1. Go to Hugging Face (e.g., https://huggingface.co/mlx-community/whisper-large-v3/tree/main).\n"
            "2. Download all files (or clone the repo) into a folder.\n"
            "   Required files: config.json, model.safetensors (or weights.npz), tokenizer.json, etc.\n"
            "3. Click 'Load Local...' and select that folder.\n\n"
            "This allows you to use the app even if the corporate firewall blocks automatic downloads."
        )
        messagebox.showinfo("Help: Manual Download", help_text)

    def on_model_change(self, model_name):
        # Save the new selection
        self.save_config()

        # Update URL/Path display
        if os.path.isdir(model_name):
            self.current_source = model_name
            self.model_source_link.configure(text=model_name)
            self.cache_status_label.configure(text="Local Folder", text_color="blue")
            self.model_info_label.configure(text="Local Model (Details unknown)")
        else:
            url = f"https://huggingface.co/{model_name}"
            self.current_source = url
            self.model_source_link.configure(text=url)
            
            # Update Info
            info_text = self.MODEL_INFO.get(model_name, "No information available")
            self.model_info_label.configure(text=info_text)
            
            # Check cache status
            cached_path = try_to_load_from_cache(repo_id=model_name, filename="config.json")
            if cached_path:
                self.cache_status_label.configure(text="✓ Cached", text_color="green")
            else:
                self.cache_status_label.configure(text="⚠ Not Cached", text_color="orange")

    def open_source(self):
        if hasattr(self, 'current_source') and self.current_source:
            if os.path.isdir(self.current_source):
                subprocess.run(["open", self.current_source])
            else:
                webbrowser.open(self.current_source)

    def browse_file(self):
        file_paths = filedialog.askopenfilenames(
            filetypes=[("Audio/Video Files", "*.mp3 *.wav *.m4a *.mp4 *.flac *.mov"), ("All Files", "*.*")]
        )
        if file_paths:
            self.file_queue = list(file_paths)
            self.batch_total_files = len(file_paths)
            self.batch_total_duration = 0.0
            
            # Update UI
            self.file_path_entry.delete(0, "end")
            if len(file_paths) == 1:
                self.selected_file = file_paths[0]
                self.file_path_entry.insert(0, file_paths[0])
                self.log_message(f"Selected file: {os.path.basename(file_paths[0])}")
            else:
                self.selected_file = file_paths[0] # Set first file as primary for now
                self.file_path_entry.insert(0, f"{len(file_paths)} files selected for batch processing")
                self.log_message(f"Selected {len(file_paths)} files for batch processing:")
                for f in file_paths:
                    self.log_message(f" - {os.path.basename(f)}")

    def log_message(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def start_transcription_thread(self):
        if not self.file_queue and not self.selected_file:
            messagebox.showwarning("No File", "Please select an audio file first.")
            return
        
        # If queue is empty but selected_file is set (legacy/manual browse), add it
        if not self.file_queue and self.selected_file:
            self.file_queue = [self.selected_file]
            self.batch_total_files = 1
            self.batch_total_duration = 0.0

        if self.is_transcribing:
            return

        self.is_transcribing = True
        self.transcribe_button.configure(text="Stop Transcription", fg_color="red", hover_color="darkred", command=self.stop_transcription)
        self.browse_button.configure(state="disabled")
        
        # Show and start progress bar
        self.progress_bar.pack(pady=10)
        self.progress_bar.start()

        self.process_next_in_queue()

    def process_next_in_queue(self):
        if not self.file_queue:
            self.log_message("Batch processing complete.")
            self.reset_ui()
            return

        current_file = self.file_queue[0] # Peek, remove on success/error
        self.log_message(f"\n--- Starting: {os.path.basename(current_file)} ---")
        
        # Prepare arguments
        audio_path = current_file
        model_name = self.model_var.get()
        language_selection = self.language_var.get()
        language_code = None
        if language_selection != "Auto":
            language_code = self.LANGUAGE_CODES.get(language_selection)

        # Create Queue
        self.result_queue = multiprocessing.Queue()

        # Start Process
        self.process = multiprocessing.Process(
            target=transcription_worker,
            args=(self.result_queue, audio_path, model_name, language_code, language_selection)
        )
        self.process.start()

        # Start polling the queue
        self.after(100, self.check_queue)
        self.after(100, self.check_queue)

    def stop_transcription(self):
        if self.process and self.process.is_alive():
            # Try terminate first (SIGTERM)
            self.process.terminate()
            # Give it a moment to die
            self.process.join(timeout=0.5)
            if self.process.is_alive():
                # Force kill if still alive (SIGKILL)
                self.process.kill()
            
            self.log_message("\n[Stopped] Transcription stopped by user.")
            self.reset_ui()

    def check_queue(self):
        try:
            while True:
                # Get all available messages
                msg_type, content = self.result_queue.get_nowait()
                
                if msg_type == "log":
                    self.log_message_no_newline(content)
                elif msg_type == "success":
                    self.handle_success(content)
                    return
                elif msg_type == "error":
                    self.handle_error(content)
                    return
        except queue.Empty:
            pass
        
        if self.process and self.process.is_alive():
            self.after(100, self.check_queue)
        else:
            # Process died unexpectedly or finished without sending success/error
            if self.is_transcribing:
                # Check if we have any pending messages one last time
                try:
                    msg_type, content = self.result_queue.get_nowait()
                    if msg_type == "success":
                        self.handle_success(content)
                        return
                    elif msg_type == "error":
                        self.handle_error(content)
                        return
                except queue.Empty:
                    pass
                    
                # If still no result, it crashed silently
                self.log_message("\n[Error] Transcription process terminated unexpectedly.")
                messagebox.showerror("Error", "Transcription process crashed or was terminated.")
                self.reset_ui()

    def handle_success(self, content):
        text, duration = content
        self.batch_total_duration += duration
        
        # Format duration
        minutes, seconds = divmod(duration, 60)
        if minutes > 0:
            time_str = f"{int(minutes)}m {int(seconds)}s"
        else:
            time_str = f"{duration:.1f}s"

        # Save to file
        current_file = self.file_queue[0] if self.file_queue else self.selected_file
        base_name = os.path.splitext(current_file)[0]
        output_path = f"{base_name}.txt"
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            self.log_message(f"SUCCESS: Transcription saved to:\n{output_path}")
            self.log_message(f"Time taken: {time_str}")
            self.show_transcription_result(text)
            
            # Only show popup if it's the last file
            if len(self.file_queue) <= 1:
                # Format total duration
                total_minutes, total_seconds = divmod(self.batch_total_duration, 60)
                if total_minutes > 0:
                    total_time_str = f"{int(total_minutes)}m {int(total_seconds)}s"
                else:
                    total_time_str = f"{self.batch_total_duration:.1f}s"
                
                msg = f"Transcription completed successfully!\n\nProcessed: {self.batch_total_files} files\nTotal Time: {total_time_str}"
                messagebox.showinfo("Batch Complete", msg)
        except Exception as e:
            self.log_message(f"Error saving file: {e}")
            messagebox.showerror("Error", f"Could not save file: {e}")
        
        # Remove processed file from queue
        if self.file_queue:
            self.file_queue.pop(0)
            
        # Process next
        self.process_next_in_queue()

    def handle_error(self, error_msg):
        if "Expecting value" in error_msg or "JSONDecodeError" in error_msg:
            model_url = f"https://huggingface.co/{self.model_var.get()}"
            error_msg += f"\n\nPossible Cause: Corporate Firewall (Cisco Umbrella) is blocking Hugging Face.\n\nSOLUTION:\n1. Open this URL in your browser:\n{model_url}\n2. Click 'Continue' on the warning page.\n3. Try again."
        
        self.log_message(f"ERROR: {error_msg}")
        
        # If batch processing, ask to continue
        if len(self.file_queue) > 1:
            if not messagebox.askyesno("Error", f"An error occurred:\n{error_msg}\n\nContinue with next file?"):
                self.reset_ui()
                return
        else:
            messagebox.showerror("Error", f"An error occurred:\n{error_msg}")
            
        # Remove failed file from queue
        if self.file_queue:
            self.file_queue.pop(0)
            
        # Process next
        self.process_next_in_queue()

    def log_message_no_newline(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def run_transcription(self):
        # Deprecated, replaced by transcription_worker
        pass

    def show_transcription_result(self, text):
        self.result_textbox.delete("0.0", "end")
        self.result_textbox.insert("0.0", text)
        self.tabview.set("Result")

    def reset_ui(self):
        self.is_transcribing = False
        self.transcribe_button.configure(text="Start Transcription", fg_color=["#3B8ED0", "#1F6AA5"], hover_color=["#36719F", "#144870"], command=self.start_transcription_thread)
        self.browse_button.configure(state="normal")
        self.progress_bar.stop()
        self.progress_bar.pack_forget()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = App()
    app.mainloop()
