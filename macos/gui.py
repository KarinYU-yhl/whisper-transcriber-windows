"""
Whisper Transcriber - macOS build.

macOS version of the cross-platform Whisper GUI. The user-facing behaviour
(file selection, drag & drop, batch processing, model selection, language
selection, Hugging Face cache management, offline local models, progress logs,
timestamped .txt + .srt output) is identical to the Windows build. It uses
faster-whisper (CTranslate2) with the public Systran/faster-whisper-* models,
which avoids the 401 / "Repository Not Found" errors of the old MLX build. On
macOS inference runs on the CPU (int8). Audio decoding uses PyAV (bundled
FFmpeg), so a separate FFmpeg install is not required.
"""
import os

# Must be set before huggingface_hub is imported. The xet download backend can
# fail behind corporate proxies ("Byte range not sequential"); the classic HTTP
# download path is more robust.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import tkinterdnd2
from tkinterdnd2 import DND_FILES
import sys
import logging
import time
import datetime
import threading
import truststore
import webbrowser
import subprocess
import multiprocessing
import queue
import json
from huggingface_hub import try_to_load_from_cache, scan_cache_dir

# Silence the harmless "unauthenticated requests to the HF Hub" warning.
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

# Folder where recorded meetings (and their transcripts) are stored.
MEETINGS_DIR = os.path.join(os.path.expanduser("~"), "WhisperMeetings")

# Inject system trust store for corporate proxies / SSL inspection.
truststore.inject_into_ssl()

# Config lives in the user profile on Windows (%USERPROFILE%\.mlx_whisper_config.json).
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".mlx_whisper_config.json")

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def detect_device():
    """Return (device, compute_type). Prefer CUDA, fall back to CPU int8."""
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def transcription_worker(result_queue, audio_path, model_name, language_code, language_name):
    """
    Worker process for transcription. Runs in a separate process so the
    Stop button can terminate it cleanly.
    """
    import sys
    import time
    import logging

    import truststore

    truststore.inject_into_ssl()
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

    class QueueLogger:
        def __init__(self, q):
            self.queue = q

        def write(self, msg):
            if msg:
                self.queue.put(("log", msg))

        def flush(self):
            pass

    sys.stdout = QueueLogger(result_queue)
    sys.stderr = QueueLogger(result_queue)

    try:
        from faster_whisper import WhisperModel

        device, compute_type = detect_device()
        print(f"Starting transcription for: {audio_path}")
        print(f"Loading model ({model_name}) on {device} [{compute_type}]...")

        model = WhisperModel(model_name, device=device, compute_type=compute_type)

        if language_code:
            print(f"Language set to: {language_name} ({language_code})")
        else:
            print("Language: Auto-detect")

        start_time = time.time()

        segments, info = model.transcribe(
            audio_path,
            language=language_code,  # None -> auto-detect
            beam_size=5,
            vad_filter=True,
            # Stop the model from hallucinating repeated content (e.g. counting
            # "7, 8, 9..." during silence) by not conditioning on prior output.
            condition_on_previous_text=False,
            no_repeat_ngram_size=3,
            no_speech_threshold=0.6,
        )

        if not language_code:
            print(
                f"Detected language: {info.language} "
                f"(probability {info.language_probability:.2f})"
            )

        total = info.duration or 0.0
        segments_data = []
        for segment in segments:
            segments_data.append((float(segment.start), float(segment.end), segment.text))
            # verbose-style progress line
            print(f"[{segment.start:6.1f}s -> {segment.end:6.1f}s] {segment.text.strip()}")
            if total:
                pct = min(100, int(segment.end / total * 100))
                result_queue.put(("progress", pct))

        text = "".join(s[2] for s in segments_data).strip()
        duration = time.time() - start_time

        result_queue.put(("success", (text, duration, segments_data)))

    except Exception as e:
        import traceback

        result_queue.put(("error", f"{e}\n{traceback.format_exc()}"))


class CacheManagerDialog(ctk.CTkToplevel):
    """Dialog for managing the Hugging Face model cache."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title("Model Cache Manager")
        self.geometry("700x450")
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="Downloaded Models (Hugging Face Cache)",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.title_label.pack(side="left")

        self.refresh_button = ctk.CTkButton(
            self.header_frame, text="Refresh", command=self.refresh_cache_list, width=80
        )
        self.refresh_button.pack(side="right")

        hub_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
        self.cache_path_label = ctk.CTkLabel(
            self,
            text=f"Cache Location: {hub_dir}",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        )
        self.cache_path_label.pack(fill="x", padx=20, pady=(0, 10))

        self.scroll_frame = ctk.CTkScrollableFrame(self, width=650, height=280)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.total_size_label = ctk.CTkLabel(
            self, text="Total: Calculating...", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.total_size_label.pack(pady=(5, 10))

        self.close_button = ctk.CTkButton(self, text="Close", command=self.destroy, width=100)
        self.close_button.pack(pady=(0, 20))

        self.model_checkboxes = {}
        self.refresh_cache_list()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def refresh_cache_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.model_checkboxes.clear()

        try:
            cache_info = scan_cache_dir()

            whisper_repos = [
                repo
                for repo in cache_info.repos
                if "whisper" in repo.repo_id.lower()
            ]

            if not whisper_repos:
                no_model_label = ctk.CTkLabel(
                    self.scroll_frame,
                    text="No Whisper models found in cache.\n\n"
                    "Models will appear here after downloading.",
                    text_color="gray",
                )
                no_model_label.pack(pady=50)
                self.total_size_label.configure(text="Total: 0 MB")
                return

            total_size = 0

            for repo in sorted(whisper_repos, key=lambda r: r.size_on_disk, reverse=True):
                total_size += repo.size_on_disk

                model_frame = ctk.CTkFrame(self.scroll_frame)
                model_frame.pack(fill="x", padx=5, pady=5)
                model_frame.grid_columnconfigure(1, weight=1)

                var = ctk.BooleanVar(value=False)
                checkbox = ctk.CTkCheckBox(model_frame, text="", variable=var, width=20)
                checkbox.grid(row=0, column=0, padx=(10, 5), pady=10)

                self.model_checkboxes[repo.repo_id] = {"var": var, "repo": repo}

                info_frame = ctk.CTkFrame(model_frame, fg_color="transparent")
                info_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

                name_label = ctk.CTkLabel(
                    info_frame,
                    text=repo.repo_id,
                    font=ctk.CTkFont(size=13, weight="bold"),
                    anchor="w",
                )
                name_label.pack(fill="x", anchor="w")

                size_label = ctk.CTkLabel(
                    info_frame,
                    text=f"Size: {self.format_size(repo.size_on_disk)}",
                    text_color="gray",
                    font=ctk.CTkFont(size=12),
                    anchor="w",
                )
                size_label.pack(fill="x", anchor="w")

                delete_btn = ctk.CTkButton(
                    model_frame,
                    text="Delete",
                    command=lambda r=repo: self.delete_single_model(r),
                    width=70,
                    height=28,
                    fg_color="#DC2626",
                    hover_color="#B91C1C",
                )
                delete_btn.grid(row=0, column=2, padx=10, pady=10)

            self.total_size_label.configure(text=f"Total: {self.format_size(total_size)}")

            if whisper_repos:
                delete_selected_btn = ctk.CTkButton(
                    self.scroll_frame,
                    text="Delete Selected",
                    command=self.delete_selected_models,
                    fg_color="#DC2626",
                    hover_color="#B91C1C",
                )
                delete_selected_btn.pack(pady=15)

        except Exception as e:
            error_label = ctk.CTkLabel(
                self.scroll_frame, text=f"Error loading cache: {e}", text_color="red"
            )
            error_label.pack(pady=50)

    def delete_single_model(self, repo):
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete:\n\n{repo.repo_id}\n\n"
            f"Size: {self.format_size(repo.size_on_disk)}\n\nThis action cannot be undone.",
            parent=self,
        )

        if confirm:
            try:
                revision_hashes = [rev.commit_hash for rev in repo.revisions]
                cache_info = scan_cache_dir()
                delete_strategy = cache_info.delete_revisions(*revision_hashes)
                freed_size = delete_strategy.expected_freed_size
                delete_strategy.execute()

                messagebox.showinfo(
                    "Deleted",
                    f"Successfully deleted {repo.repo_id}\n\n"
                    f"Freed: {self.format_size(freed_size)}",
                    parent=self,
                )
                self.refresh_cache_list()
                self.parent.on_model_change(self.parent.model_var.get())
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete model:\n{e}", parent=self)

    def delete_selected_models(self):
        selected = [
            (repo_id, data)
            for repo_id, data in self.model_checkboxes.items()
            if data["var"].get()
        ]

        if not selected:
            messagebox.showwarning("No Selection", "Please select models to delete.", parent=self)
            return

        total_size = sum(data["repo"].size_on_disk for _, data in selected)
        model_names = "\n".join([repo_id for repo_id, _ in selected])

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete {len(selected)} model(s)?\n\n{model_names}\n\n"
            f"Total size: {self.format_size(total_size)}\n\nThis action cannot be undone.",
            parent=self,
        )

        if confirm:
            try:
                all_hashes = []
                for _, data in selected:
                    for rev in data["repo"].revisions:
                        all_hashes.append(rev.commit_hash)

                cache_info = scan_cache_dir()
                delete_strategy = cache_info.delete_revisions(*all_hashes)
                freed_size = delete_strategy.expected_freed_size
                delete_strategy.execute()

                messagebox.showinfo(
                    "Deleted",
                    f"Successfully deleted {len(selected)} model(s)\n\n"
                    f"Freed: {self.format_size(freed_size)}",
                    parent=self,
                )
                self.refresh_cache_list()
                self.parent.on_model_change(self.parent.model_var.get())
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete models:\n{e}", parent=self)


class App(ctk.CTk, tkinterdnd2.TkinterDnD.DnDWrapper):
    # faster-whisper accepts short size names and downloads the matching
    # Systran/faster-whisper-* repo from Hugging Face automatically.
    MODEL_INFO = {
        "tiny": "Speed: ★★★★★ | Accuracy: ★☆☆☆☆ (Fastest)",
        "base": "Speed: ★★★★☆ | Accuracy: ★★☆☆☆ (Fast)",
        "small": "Speed: ★★★☆☆ | Accuracy: ★★★☆☆ (Balanced)",
        "medium": "Speed: ★★☆☆☆ | Accuracy: ★★★★☆ (High Accuracy)",
        "large-v3": "Speed: ★☆☆☆☆ | Accuracy: ★★★★★ (Best Accuracy)",
        "large-v3-turbo": "Speed: ★★★☆☆ | Accuracy: ★★★★★ (Fast, High Accuracy, Recommended)",
    }

    # Short size name -> Hugging Face repo id (used for cache status / source link).
    MODEL_REPOS = {
        "tiny": "Systran/faster-whisper-tiny",
        "base": "Systran/faster-whisper-base",
        "small": "Systran/faster-whisper-small",
        "medium": "Systran/faster-whisper-medium",
        "large-v3": "Systran/faster-whisper-large-v3",
        "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
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

        self.title("Whisper Transcriber (macOS)")
        self.geometry("850x560")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Report the active compute device instead of demanding FFmpeg
        # (faster-whisper bundles audio decoding through PyAV).
        device, compute_type = detect_device()
        self.device_desc = f"{device.upper()} ({compute_type})"

        self.title_label = ctk.CTkLabel(
            self, text="Whisper Transcriber", font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.file_frame.grid_columnconfigure(0, weight=1)

        self.file_path_entry = ctk.CTkEntry(self.file_frame, placeholder_text="Select an audio file...")
        self.file_path_entry.grid(row=0, column=0, padx=(10, 10), pady=10, sticky="ew")

        self.browse_button = ctk.CTkButton(self.file_frame, text="Browse", command=self.browse_file, width=100)
        self.browse_button.grid(row=0, column=1, padx=(0, 10), pady=10)

        # Meeting recording controls (row 1 of the file frame).
        self.record_button = ctk.CTkButton(
            self.file_frame,
            text="● Record Meeting",
            command=self.toggle_recording,
            width=150,
            fg_color="#059669",
            hover_color="#047857",
        )
        self.record_button.grid(row=1, column=0, padx=(10, 10), pady=(0, 10), sticky="w")

        self.record_status_label = ctk.CTkLabel(
            self.file_frame,
            text="Record your mic (+ system audio if BlackHole is installed), then auto-transcribe.",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        )
        self.record_status_label.grid(row=1, column=1, padx=(0, 10), pady=(0, 10), sticky="w")

        self.model_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.model_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.model_frame.grid_columnconfigure(1, weight=1)

        self.model_label = ctk.CTkLabel(self.model_frame, text="Model:", font=ctk.CTkFont(weight="bold"))
        self.model_label.grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.model_var = ctk.StringVar(value="large-v3")
        self.model_select_menu = ctk.CTkOptionMenu(
            self.model_frame,
            values=[
                "large-v3",
                "large-v3-turbo",
                "tiny",
                "base",
                "small",
                "medium",
            ],
            variable=self.model_var,
            command=self.on_model_change,
        )
        self.model_select_menu.grid(row=0, column=1, padx=(0, 10), sticky="ew")

        self.local_model_button = ctk.CTkButton(
            self.model_frame, text="Load Local...", command=self.select_local_model, width=100, fg_color="green"
        )
        self.local_model_button.grid(row=0, column=2, padx=(0, 10), sticky="w")

        self.help_button = ctk.CTkButton(
            self.model_frame, text="?", command=self.show_help, width=30, fg_color="gray"
        )
        self.help_button.grid(row=0, column=3, padx=(0, 5), sticky="w")

        self.cache_manage_button = ctk.CTkButton(
            self.model_frame, text="Manage Cache", command=self.show_cache_manager, width=100, fg_color="#6B7280"
        )
        self.cache_manage_button.grid(row=0, column=4, padx=(0, 10), sticky="w")

        self.cache_status_label = ctk.CTkLabel(self.model_frame, text="Checking...", text_color="gray")
        self.cache_status_label.grid(row=0, column=5, padx=(0, 0), sticky="w")

        self.path_label = ctk.CTkLabel(self.model_frame, text="Source:", font=ctk.CTkFont(size=12))
        self.path_label.grid(row=1, column=0, padx=(0, 10), pady=(5, 0), sticky="w")

        self.model_source_link = ctk.CTkButton(
            self.model_frame,
            text="large-v3",
            fg_color="transparent",
            text_color=("blue", "#4DA6FF"),
            anchor="w",
            font=ctk.CTkFont(size=12, underline=True),
            hover_color=("gray85", "gray25"),
            command=self.open_source,
        )
        self.model_source_link.grid(row=1, column=1, columnspan=5, padx=(0, 0), pady=(5, 0), sticky="ew")

        self.model_info_label = ctk.CTkLabel(
            self.model_frame, text="", text_color="gray", font=ctk.CTkFont(size=12)
        )
        self.model_info_label.grid(row=2, column=0, columnspan=6, padx=(0, 10), pady=(5, 0), sticky="w")

        # State
        self.selected_file = None
        self.file_queue = []
        self.batch_total_files = 0
        self.batch_total_duration = 0.0
        self.is_transcribing = False
        self.process = None
        self.result_queue = None
        # Meeting recording state
        self.recorder = None
        self.is_recording = False
        self.last_model_dir = (
            os.path.join(os.getcwd(), "models")
            if os.path.exists(os.path.join(os.getcwd(), "models"))
            else os.getcwd()
        )

        self.load_config()
        self.on_model_change(self.model_var.get())

        self.options_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.options_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.language_label = ctk.CTkLabel(self.options_frame, text="Language:", font=ctk.CTkFont(weight="bold"))
        self.language_label.grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.language_var = ctk.StringVar(value="Auto")
        self.language_menu = ctk.CTkOptionMenu(
            self.options_frame,
            values=["Auto"] + list(self.LANGUAGE_CODES.keys()),
            variable=self.language_var,
        )
        self.language_menu.grid(row=0, column=1, padx=(0, 10), sticky="w")

        self.device_label = ctk.CTkLabel(
            self.options_frame,
            text=f"Compute: {self.device_desc}",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        )
        self.device_label.grid(row=0, column=2, padx=(20, 0), sticky="w")

        self.tabview = ctk.CTkTabview(self, width=500, height=200)
        self.tabview.grid(row=4, column=0, padx=20, pady=10, sticky="nsew")
        self.grid_rowconfigure(4, weight=1)

        self.tab_logs = self.tabview.add("Logs")
        self.tab_result = self.tabview.add("Result")

        self.tabview.set("Logs")
        self.log_textbox = ctk.CTkTextbox(self.tab_logs, width=500, height=150)
        self.log_textbox.pack(expand=True, fill="both")
        self.log_textbox.insert("0.0", f"Ready to transcribe. Compute device: {self.device_desc}\n")
        self.log_textbox.configure(state="disabled")

        self.result_textbox = ctk.CTkTextbox(self.tab_result, width=500, height=150)
        self.result_textbox.pack(expand=True, fill="both")

        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=5, column=0, padx=20, pady=20)

        self.transcribe_button = ctk.CTkButton(
            self.button_frame,
            text="Start Transcription",
            command=self.start_transcription_thread,
            font=ctk.CTkFont(size=15, weight="bold"),
            height=40,
            width=200,
        )
        self.transcribe_button.pack()

        self.progress_bar = ctk.CTkProgressBar(self.button_frame, width=400)
        self.progress_bar.set(0)

        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self.drop_file)

    def drop_file(self, event):
        try:
            files = self.tk.splitlist(event.data)
        except Exception:
            files = [event.data]

        if not files:
            return

        self.file_queue = list(files)
        self.batch_total_files = len(files)
        self.batch_total_duration = 0.0

        self.file_path_entry.delete(0, "end")
        if len(files) == 1:
            self.selected_file = files[0]
            self.file_path_entry.insert(0, files[0])
            self.log_message(f"Selected file: {os.path.basename(files[0])}")
        else:
            self.selected_file = files[0]
            self.file_path_entry.insert(0, f"{len(files)} files selected for batch processing")
            self.log_message(f"Selected {len(files)} files for batch processing:")
            for f in files:
                self.log_message(f" - {os.path.basename(f)}")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)

                if "last_model_dir" in config and os.path.isdir(config["last_model_dir"]):
                    self.last_model_dir = config["last_model_dir"]

                if "last_model" in config:
                    last_model = config["last_model"]
                    if os.path.isdir(last_model):
                        if last_model not in self.model_select_menu._values:
                            current_values = self.model_select_menu._values
                            self.model_select_menu.configure(values=[last_model] + current_values)
                        self.model_var.set(last_model)
                        self.on_model_change(last_model)
                    elif last_model in self.model_select_menu._values:
                        self.model_var.set(last_model)
                        self.on_model_change(last_model)
            except Exception as e:
                print(f"Failed to load config: {e}")

    def save_config(self):
        config = {"last_model_dir": self.last_model_dir, "last_model": self.model_var.get()}
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def select_local_model(self):
        folder_path = filedialog.askdirectory(title="Select Model Folder", initialdir=self.last_model_dir)
        if not folder_path:
            return

        self.last_model_dir = os.path.dirname(folder_path)
        self.save_config()

        # faster-whisper (CTranslate2) folders contain a model.bin + config.json.
        found_paths = []
        if os.path.exists(os.path.join(folder_path, "config.json")):
            found_paths.append(folder_path)
        else:
            self.log_message("Searching for models in subdirectories...")
            for root, dirs, files in os.walk(folder_path):
                if "config.json" in files:
                    found_paths.append(root)
                    dirs[:] = []

        if not found_paths:
            messagebox.showwarning(
                "Invalid Model Folder",
                "Could not find 'config.json' in the selected folder or its subdirectories.\n"
                "Please select a valid faster-whisper (CTranslate2) model folder.",
            )
            return

        found_paths.sort()

        current_values = self.model_select_menu._values
        new_values = found_paths + [v for v in current_values if v not in found_paths]
        self.model_select_menu.configure(values=new_values)

        target_path = found_paths[0]
        self.model_var.set(target_path)
        self.on_model_change(target_path)

        self.log_message(f"Selected local model path: {target_path}")
        if len(found_paths) > 1:
            self.log_message(
                f"Found {len(found_paths)} models in the folder. You can switch between them in the dropdown."
            )
        elif target_path != folder_path:
            self.log_message("(Auto-detected model inside subfolder)")

    def show_cache_manager(self):
        CacheManagerDialog(self)

    def show_help(self):
        help_text = (
            "How to use Local Models (Offline Mode):\n\n"
            "1. Go to Hugging Face (e.g. https://huggingface.co/Systran/faster-whisper-large-v3/tree/main).\n"
            "2. Download all files (or clone the repo) into a folder.\n"
            "   Required files: config.json, model.bin, tokenizer.json, vocabulary.txt.\n"
            "3. Click 'Load Local...' and select that folder.\n\n"
            "This lets you run the app even when a corporate firewall blocks automatic downloads.\n\n"
            "NOTE: This build uses faster-whisper (CTranslate2) models, NOT the old MLX models. "
            "Use the Systran/faster-whisper-* repositories (public, no login required)."
        )
        messagebox.showinfo("Help: Manual Download", help_text)

    def _repo_for(self, model_name):
        """Return the HF repo id for a short size name, else the name itself."""
        return self.MODEL_REPOS.get(model_name, model_name)

    def on_model_change(self, model_name):
        self.save_config()

        if os.path.isdir(model_name):
            self.current_source = model_name
            self.model_source_link.configure(text=model_name)
            self.cache_status_label.configure(text="Local Folder", text_color="blue")
            self.model_info_label.configure(text="Local Model (Details unknown)")
        else:
            repo_id = self._repo_for(model_name)
            url = f"https://huggingface.co/{repo_id}"
            self.current_source = url
            self.model_source_link.configure(text=url)

            info_text = self.MODEL_INFO.get(model_name, "No information available")
            self.model_info_label.configure(text=info_text)

            cached_path = try_to_load_from_cache(repo_id=repo_id, filename="config.json")
            if cached_path:
                self.cache_status_label.configure(text="✓ Cached", text_color="green")
            else:
                self.cache_status_label.configure(text="⚠ Not Cached", text_color="orange")

    def open_source(self):
        if hasattr(self, "current_source") and self.current_source:
            if os.path.isdir(self.current_source):
                subprocess.run(["open", self.current_source])  # macOS: reveal in Finder
            else:
                webbrowser.open(self.current_source)

    def browse_file(self):
        file_paths = filedialog.askopenfilenames(
            filetypes=[
                ("Audio/Video Files", "*.mp3 *.wav *.m4a *.mp4 *.flac *.mov *.ogg *.wma *.aac *.mkv"),
                ("All Files", "*.*"),
            ]
        )
        if file_paths:
            self.file_queue = list(file_paths)
            self.batch_total_files = len(file_paths)
            self.batch_total_duration = 0.0

            self.file_path_entry.delete(0, "end")
            if len(file_paths) == 1:
                self.selected_file = file_paths[0]
                self.file_path_entry.insert(0, file_paths[0])
                self.log_message(f"Selected file: {os.path.basename(file_paths[0])}")
            else:
                self.selected_file = file_paths[0]
                self.file_path_entry.insert(0, f"{len(file_paths)} files selected for batch processing")
                self.log_message(f"Selected {len(file_paths)} files for batch processing:")
                for f in file_paths:
                    self.log_message(f" - {os.path.basename(f)}")

    def log_message(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def log_message_no_newline(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.is_transcribing:
            messagebox.showwarning("Busy", "Please wait for the current transcription to finish.")
            return

        try:
            from meeting_recorder import MeetingRecorder
        except Exception as e:
            messagebox.showerror(
                "Missing Dependency",
                f"Audio capture library not available:\n{e}\n\nInstall it with:\npip install soundcard",
            )
            return

        try:
            self.recorder = MeetingRecorder(include_mic=True)
            self.recorder.start()
        except Exception as e:
            messagebox.showerror("Recording Error", f"Could not start recording:\n{e}")
            self.recorder = None
            return

        self.is_recording = True
        self.record_button.configure(
            text="■ Stop & Transcribe", fg_color="red", hover_color="darkred"
        )
        self.browse_button.configure(state="disabled")
        self.transcribe_button.configure(state="disabled")
        self.log_message("\n[Recording] Meeting recording started. Speak / start your Teams call.")
        self.log_message("Tip: keep this app running in the background during the meeting.")
        self._update_record_timer()

    def _update_record_timer(self):
        if not self.is_recording or not self.recorder:
            return
        elapsed = int(self.recorder.elapsed)
        mm, ss = divmod(elapsed, 60)
        hh, mm = divmod(mm, 60)
        bars = int(self.recorder.level * 20)
        meter = "█" * bars + "·" * (20 - bars)
        self.record_status_label.configure(
            text=f"Recording  {hh:02d}:{mm:02d}:{ss:02d}   [{meter}]",
            text_color="red",
        )
        self.after(200, self._update_record_timer)

    def stop_recording(self):
        if not self.recorder:
            return

        self.record_button.configure(state="disabled", text="Processing...")
        self.record_status_label.configure(text="Finalizing recording...", text_color="gray")
        self.log_message("\n[Recording] Stopping and saving audio...")

        # Mixing/saving can take a moment for long meetings; do it off the UI thread.
        threading.Thread(target=self._finalize_recording, daemon=True).start()

    def _finalize_recording(self):
        try:
            from meeting_recorder import save_wav

            audio = self.recorder.stop()
            errors = self.recorder.errors()

            if audio.size == 0:
                self.after(0, lambda: self._recording_failed(errors or ["No audio was captured."]))
                return

            os.makedirs(MEETINGS_DIR, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            wav_path = os.path.join(MEETINGS_DIR, f"meeting_{stamp}.wav")
            save_wav(audio, wav_path)

            duration = audio.size / 16000.0
            self.after(0, lambda: self._recording_done(wav_path, duration, errors))
        except Exception as e:
            self.after(0, lambda: self._recording_failed([str(e)]))

    def _recording_done(self, wav_path, duration, errors):
        self.recorder = None
        self.is_recording = False
        self.record_button.configure(
            state="normal", text="● Record Meeting", fg_color="#059669", hover_color="#047857"
        )
        self.record_status_label.configure(
            text=f"Saved recording ({duration/60:.1f} min). Transcribing...", text_color="gray"
        )
        self.browse_button.configure(state="normal")
        self.transcribe_button.configure(state="normal")

        mm, ss = divmod(int(duration), 60)
        self.log_message(f"[Recording] Saved {mm}m {ss}s to:\n{wav_path}")
        for err in errors:
            self.log_message(f"[Recording] Note: {err}")

        # Queue the recording and reuse the normal transcription pipeline.
        self.file_queue = [wav_path]
        self.selected_file = wav_path
        self.batch_total_files = 1
        self.batch_total_duration = 0.0
        self.file_path_entry.delete(0, "end")
        self.file_path_entry.insert(0, wav_path)
        self.start_transcription_thread()

    def _recording_failed(self, errors):
        self.recorder = None
        self.is_recording = False
        self.record_button.configure(
            state="normal", text="● Record Meeting", fg_color="#059669", hover_color="#047857"
        )
        self.record_status_label.configure(
            text="Record your mic (+ system audio if BlackHole is installed), then auto-transcribe.",
            text_color="gray",
        )
        self.browse_button.configure(state="normal")
        self.transcribe_button.configure(state="normal")
        msg = "\n".join(errors)
        self.log_message(f"[Recording] Failed: {msg}")
        messagebox.showerror("Recording Failed", msg)

    def start_transcription_thread(self):
        if not self.file_queue and not self.selected_file:
            messagebox.showwarning("No File", "Please select an audio file first.")
            return

        if not self.file_queue and self.selected_file:
            self.file_queue = [self.selected_file]
            self.batch_total_files = 1
            self.batch_total_duration = 0.0

        if self.is_transcribing:
            return

        self.is_transcribing = True
        self.transcribe_button.configure(
            text="Stop Transcription", fg_color="red", hover_color="darkred", command=self.stop_transcription
        )
        self.browse_button.configure(state="disabled")
        self.record_button.configure(state="disabled")

        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        self.process_next_in_queue()

    def process_next_in_queue(self):
        if not self.file_queue:
            self.log_message("Batch processing complete.")
            self.reset_ui()
            return

        current_file = self.file_queue[0]
        self.log_message(f"\n--- Starting: {os.path.basename(current_file)} ---")

        audio_path = current_file
        model_name = self.model_var.get()
        language_selection = self.language_var.get()
        language_code = None
        if language_selection != "Auto":
            language_code = self.LANGUAGE_CODES.get(language_selection)

        self.result_queue = multiprocessing.Queue()

        self.process = multiprocessing.Process(
            target=transcription_worker,
            args=(self.result_queue, audio_path, model_name, language_code, language_selection),
        )
        self.process.start()

        self.progress_bar.set(0)
        self.after(100, self.check_queue)

    def stop_transcription(self):
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=0.5)
            if self.process.is_alive():
                self.process.kill()

            self.log_message("\n[Stopped] Transcription stopped by user.")
            self.reset_ui()

    def check_queue(self):
        try:
            while True:
                msg_type, content = self.result_queue.get_nowait()

                if msg_type == "log":
                    self.log_message_no_newline(content)
                elif msg_type == "progress":
                    self.progress_bar.set(content / 100.0)
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
            if self.is_transcribing:
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

                self.log_message("\n[Error] Transcription process terminated unexpectedly.")
                messagebox.showerror("Error", "Transcription process crashed or was terminated.")
                self.reset_ui()

    def handle_success(self, content):
        text, duration, segments = content
        self.batch_total_duration += duration
        self.progress_bar.set(1.0)

        minutes, seconds = divmod(duration, 60)
        if minutes > 0:
            time_str = f"{int(minutes)}m {int(seconds)}s"
        else:
            time_str = f"{duration:.1f}s"

        current_file = self.file_queue[0] if self.file_queue else self.selected_file
        base_name = os.path.splitext(current_file)[0]

        try:
            from output_formats import write_outputs, timestamped_text

            txt_path, srt_path = write_outputs(base_name, segments)
            self.log_message(f"SUCCESS: Transcription saved to:\n{txt_path}\n{srt_path}")
            self.log_message(f"Time taken: {time_str}")
            # Show the timestamped version so the user can see the times inline.
            self.show_transcription_result(timestamped_text(segments) or text)

            if len(self.file_queue) <= 1:
                total_minutes, total_seconds = divmod(self.batch_total_duration, 60)
                if total_minutes > 0:
                    total_time_str = f"{int(total_minutes)}m {int(total_seconds)}s"
                else:
                    total_time_str = f"{self.batch_total_duration:.1f}s"

                msg = (
                    f"Transcription completed successfully!\n\n"
                    f"Processed: {self.batch_total_files} files\nTotal Time: {total_time_str}"
                )
                messagebox.showinfo("Batch Complete", msg)
        except Exception as e:
            self.log_message(f"Error saving file: {e}")
            messagebox.showerror("Error", f"Could not save file: {e}")

        if self.file_queue:
            self.file_queue.pop(0)

        self.process_next_in_queue()

    def handle_error(self, error_msg):
        if "Expecting value" in error_msg or "JSONDecodeError" in error_msg:
            model_url = f"https://huggingface.co/{self._repo_for(self.model_var.get())}"
            error_msg += (
                f"\n\nPossible Cause: A corporate firewall/proxy is blocking Hugging Face.\n\n"
                f"SOLUTION:\n1. Open this URL in your browser:\n{model_url}\n"
                f"2. Click 'Continue' on any warning page.\n3. Try again."
            )

        self.log_message(f"ERROR: {error_msg}")

        if len(self.file_queue) > 1:
            if not messagebox.askyesno("Error", f"An error occurred:\n{error_msg}\n\nContinue with next file?"):
                self.reset_ui()
                return
        else:
            messagebox.showerror("Error", f"An error occurred:\n{error_msg}")

        if self.file_queue:
            self.file_queue.pop(0)

        self.process_next_in_queue()

    def show_transcription_result(self, text):
        self.result_textbox.delete("0.0", "end")
        self.result_textbox.insert("0.0", text)
        self.tabview.set("Result")

    def reset_ui(self):
        self.is_transcribing = False
        self.transcribe_button.configure(
            text="Start Transcription",
            fg_color=["#3B8ED0", "#1F6AA5"],
            hover_color=["#36719F", "#144870"],
            command=self.start_transcription_thread,
        )
        self.browse_button.configure(state="normal")
        self.record_button.configure(state="normal")
        self.progress_bar.pack_forget()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = App()
    app.mainloop()
