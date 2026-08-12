import io
import json
import os
import re
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image
import urllib.request
import yt_dlp

CONFIG_FILE = "app_config.json"
HISTORY_FILE = "download_history.json"
MAX_HISTORY_LIMIT = 500

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent
        self.title("Download History")
        self.geometry("700x600")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 10))

        title = ctk.CTkLabel(header, text="Download History", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(side="left")

        clear_btn = ctk.CTkButton(
            header,
            text="Clear History",
            fg_color="#D03B29",
            hover_color="#A82B1E",
            width=100,
            height=28,
            command=self.clear_history
        )
        clear_btn.pack(side="right")

        self.scroll_frame = ctk.CTkScrollableFrame(self, width=650, height=500)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.load_history_list()

    def load_history_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        history = self.parent.load_history()

        if not history:
            no_history_label = ctk.CTkLabel(
                self.scroll_frame, text="No download history found.", text_color="gray"
            )
            no_history_label.pack(pady=50)
            return

        for item in reversed(history):
            card = ctk.CTkFrame(self.scroll_frame, corner_radius=8)
            card.pack(fill="x", pady=4, padx=5)

            details_frame = ctk.CTkFrame(card, fg_color="transparent")
            details_frame.pack(side="left", fill="both", expand=True, padx=10, pady=8)

            raw_title = item.get("title", "Unknown Title")
            title_lbl = ctk.CTkLabel(
                details_frame,
                text=raw_title,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w"
            )
            title_lbl.pack(fill="x")

            meta_text = f"Format: {item.get('format', 'mp4')} | Quality: {item.get('quality', '1080p')} | Date: {item.get('date', 'N/A')}"
            meta_lbl = ctk.CTkLabel(details_frame, text=meta_text, font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
            meta_lbl.pack(fill="x")

            actions_frame = ctk.CTkFrame(card, fg_color="transparent")
            actions_frame.pack(side="right", padx=10, pady=10)

            copy_btn = ctk.CTkButton(
                actions_frame,
                text="📋",
                width=36,
                height=32,
                font=ctk.CTkFont(size=14),
                fg_color="#2B2B2B",
                hover_color="#3B3B3B",
                command=lambda url=item.get("url", ""): self.copy_url(url)
            )
            copy_btn.pack(side="left", padx=3)

            delete_btn = ctk.CTkButton(
                actions_frame,
                text="🗑️",
                width=36,
                height=32,
                font=ctk.CTkFont(size=14),
                fg_color="#D03B29",
                hover_color="#A82B1E",
                command=lambda url=item.get("url", ""): self.delete_item(url)
            )
            delete_btn.pack(side="left", padx=3)

    def copy_url(self, url):
        if url:
            self.clipboard_clear()
            self.clipboard_append(url)
            messagebox.showinfo("Copied", "URL copied to clipboard!")

    def delete_item(self, url):
        history = self.parent.load_history()
        updated_history = [item for item in history if item.get("url") != url]
        self.parent.save_history(updated_history)
        self.load_history_list()

    def clear_history(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear your download history?"):
            self.parent.save_history([])
            self.load_history_list()


class VideoDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Video Downloader")
        self.geometry("640x640")
        self.resizable(False, False)

        try:
            self.iconbitmap("icon.ico")
        except Exception:
            pass

        self.config = self.load_config()
        self.download_path = self.config.get("download_path", os.path.expanduser("~/Downloads"))
        self.last_quality = self.config.get("quality", "1080p")
        self.last_download_type = self.config.get("download_type", "Video")
        self.last_video_format = self.config.get("video_format", "mp4")
        self.last_subtitle = self.config.get("subtitle", "None")
        self.last_browser = self.config.get("browser", "Chrome")

        self.original_video_title = ""

        self._build_ui()

    def apply_cookie_option(self, ydl_opts):
        selected_browser = self.browser_var.get()

        if selected_browser == "None":
            return

        # Handle custom cookies.txt file option
        if selected_browser == "cookies.txt file":
            cookie_file = os.path.join(os.getcwd(), "cookies.txt")
            if os.path.exists(cookie_file):
                ydl_opts["cookiefile"] = cookie_file
            return

        browser_map = {
            "Chrome": ["chrome"],
            "Edge": ["edge"],
            "Firefox": ["firefox"],
            "Brave": ["brave"],
            "Opera": ["opera"],
            "Chromium": ["chromium"],
            "Vivaldi": ["vivaldi"],
            "Safari": ["safari"],
            "Auto (Detect All)": ["chrome", "edge", "firefox", "brave", "opera", "chromium", "vivaldi", "safari"]
        }

        candidates = browser_map.get(selected_browser, ["chrome"])

        for b in candidates:
            # Try setting browser directly
            ydl_opts["cookiesfrombrowser"] = (b,)
            return

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_config(self):
        data = {
            "download_path": self.download_path,
            "quality": self.quality_var.get(),
            "download_type": self.type_var.get(),
            "video_format": self.format_var.get(),
            "subtitle": self.subtitle_var.get(),
            "browser": self.browser_var.get()
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_history(self, history):
        trimmed_history = history[-MAX_HISTORY_LIMIT:]
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(trimmed_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save history: {e}")

    def record_download(self, url, title, mode, fmt, quality):
        from datetime import datetime
        history = self.load_history()

        history = [item for item in history if item.get("url") != url]

        entry = {
            "title": title if title else "Video",
            "url": url,
            "mode": mode,
            "format": fmt,
            "quality": quality,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        history.append(entry)
        self.save_history(history)

    def open_history_window(self):
        HistoryWindow(self)

    def _build_ui(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=30, pady=(15, 5))

        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Video Downloader", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.title_label.pack(side="left", anchor="w")

        self.top_actions_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.top_actions_frame.pack(side="right", anchor="e")

        self.browser_var = ctk.StringVar(value=self.last_browser)
        self.browser_dropdown = ctk.CTkOptionMenu(
            self.top_actions_frame,
            values=[
                "Chrome", "Edge", "Firefox", "Brave", 
                "Opera", "Chromium", "Vivaldi", "Safari", 
                "Auto (Detect All)", "cookies.txt file", "None"
            ],
            variable=self.browser_var,
            width=130,
            height=30,
            command=lambda _: self.save_config()
        )
        self.browser_dropdown.pack(side="left", padx=(0, 8))

        self.history_btn = ctk.CTkButton(
            self.top_actions_frame,
            text="📜 History",
            width=90,
            height=30,
            command=self.open_history_window
        )
        self.history_btn.pack(side="left")

        self.url_frame = ctk.CTkFrame(self, corner_radius=10)
        self.url_frame.pack(fill="x", padx=30, pady=5)

        self.url_label = ctk.CTkLabel(self.url_frame, text="Video Link", font=ctk.CTkFont(size=12, weight="bold"))
        self.url_label.pack(anchor="w", padx=15, pady=(8, 2))

        self.url_entry = ctk.CTkEntry(
            self.url_frame, placeholder_text="Paste video URL from YouTube, Instagram, TikTok, Facebook...", height=35
        )
        self.url_entry.pack(fill="x", padx=15, pady=(0, 10))
        self.url_entry.bind("<KeyRelease>", self.on_url_change)

        self.preview_frame = ctk.CTkFrame(self, height=180, corner_radius=10)
        self.preview_frame.pack(fill="x", padx=30, pady=5)
        self.preview_frame.pack_propagate(False)

        self.thumbnail_label = ctk.CTkLabel(
            self.preview_frame, text="Paste a valid video URL to preview", text_color="gray"
        )
        self.thumbnail_label.pack(expand=True, fill="both")
        self.thumbnail_label.bind("<Button-1>", self.on_preview_click)

        self.options_frame = ctk.CTkFrame(self, corner_radius=10)
        self.options_frame.pack(fill="x", padx=30, pady=5)

        self.rename_label = ctk.CTkLabel(self.options_frame, text="Name:", font=ctk.CTkFont(size=12))
        self.rename_label.grid(row=0, column=0, padx=(15, 5), pady=(10, 4), sticky="w")

        self.rename_entry = ctk.CTkEntry(
            self.options_frame, placeholder_text="Video name will autofill here...", height=32
        )
        self.rename_entry.grid(row=0, column=1, columnspan=3, padx=(5, 15), pady=(10, 4), sticky="ew")

        self.type_label = ctk.CTkLabel(self.options_frame, text="Mode:", font=ctk.CTkFont(size=12))
        self.type_label.grid(row=1, column=0, padx=(15, 5), pady=4, sticky="w")

        self.type_var = ctk.StringVar(value=self.last_download_type)
        self.type_dropdown = ctk.CTkOptionMenu(
            self.options_frame,
            values=["Video", "Audio Only", "Convert Local Video"],
            variable=self.type_var,
            height=32,
            command=self.on_type_change
        )
        self.type_dropdown.grid(row=1, column=1, padx=5, pady=4, sticky="ew")

        self.quality_label = ctk.CTkLabel(self.options_frame, text="Quality:", font=ctk.CTkFont(size=12))
        self.quality_label.grid(row=1, column=2, padx=(15, 5), pady=4, sticky="w")

        self.quality_var = ctk.StringVar(value=self.last_quality)
        self.quality_dropdown = ctk.CTkOptionMenu(
            self.options_frame,
            values=[
                "Best Available",
                "2160p (4K)",
                "1440p (2K)",
                "1080p",
                "720p",
                "480p",
                "360p",
                "240p",
                "144p"
            ],
            variable=self.quality_var,
            height=32,
            command=lambda _: self.save_config()
        )
        self.quality_dropdown.grid(row=1, column=3, padx=(5, 15), pady=4, sticky="ew")

        self.format_label = ctk.CTkLabel(self.options_frame, text="Format:", font=ctk.CTkFont(size=12))
        self.format_label.grid(row=2, column=0, padx=(15, 5), pady=4, sticky="w")

        self.format_var = ctk.StringVar(value=self.last_video_format)
        self.format_dropdown = ctk.CTkOptionMenu(
            self.options_frame,
            values=["mp4", "mkv", "webm"],
            variable=self.format_var,
            height=32,
            command=lambda _: self.save_config()
        )
        self.format_dropdown.grid(row=2, column=1, padx=5, pady=4, sticky="ew")

        self.subtitle_label = ctk.CTkLabel(self.options_frame, text="Subtitles:", font=ctk.CTkFont(size=12))
        self.subtitle_label.grid(row=2, column=2, padx=(15, 5), pady=4, sticky="w")

        self.subtitle_var = ctk.StringVar(value=self.last_subtitle)
        self.subtitle_dropdown = ctk.CTkOptionMenu(
            self.options_frame,
            values=["None", "Embed English", "Embed Auto-Subs"],
            variable=self.subtitle_var,
            height=32,
            command=lambda _: self.save_config()
        )
        self.subtitle_dropdown.grid(row=2, column=3, padx=(5, 15), pady=4, sticky="ew")

        self.path_button = ctk.CTkButton(
            self.options_frame,
            text="Choose Folder",
            fg_color="transparent",
            border_width=1,
            height=32,
            command=self.browse_folder,
        )
        self.path_button.grid(row=3, column=0, columnspan=2, padx=(15, 5), pady=(6, 10), sticky="ew")

        self.path_label = ctk.CTkLabel(
            self.options_frame, text=self.download_path, text_color="gray", anchor="w"
        )
        self.path_label.grid(row=3, column=2, columnspan=2, padx=(5, 15), pady=(6, 10), sticky="ew")

        self.options_frame.grid_columnconfigure(0, weight=0)
        self.options_frame.grid_columnconfigure(1, weight=1)
        self.options_frame.grid_columnconfigure(2, weight=0)
        self.options_frame.grid_columnconfigure(3, weight=1)

        self.download_btn = ctk.CTkButton(
            self,
            text="Download",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=42,
            corner_radius=8,
            command=self.start_download_thread,
        )
        self.download_btn.pack(fill="x", padx=30, pady=(10, 5))

        self.progress_bar = ctk.CTkProgressBar(self, width=580, height=10)
        self.progress_bar.pack(padx=30, pady=(4, 2))
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.pack(pady=(0, 10))

        self.on_type_change(self.type_var.get())

    def on_preview_click(self, event=None):
        if self.type_var.get() == "Convert Local Video":
            self.browse_local_file()

    def browse_local_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.webm *.flv *.m4v")]
        )
        if file_path:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, file_path)
            self.rename_entry.delete(0, tk.END)
            self.rename_entry.insert(0, os.path.splitext(os.path.basename(file_path))[0])
            self.thumbnail_label.configure(
                image="", text=f"Selected Local File:\n{os.path.basename(file_path)}", text_color="white"
            )

    def on_type_change(self, choice):
        if choice == "Convert Local Video":
            self.url_label.configure(text="Video File Path")
            self.url_entry.delete(0, tk.END)
            self.url_entry.configure(placeholder_text="Click here or Browse preview box to select a video file...")
            self.thumbnail_label.configure(
                text="📁 Click here to select a local video file", text_color="#3B82F6"
            )
            self.quality_label.configure(text="Res:")
            self.quality_dropdown.configure(
                state="normal", 
                values=["Keep Original", "1080p", "720p", "480p", "360p"]
            )
            self.quality_var.set("Keep Original")

            self.format_dropdown.configure(values=["mp4", "mkv", "webm", "avi", "mov"])
            if self.format_var.get() not in ["mp4", "mkv", "webm", "avi", "mov"]:
                self.format_var.set("mp4")

            self.subtitle_label.configure(text="Compress:")
            self.subtitle_dropdown.configure(values=["None", "Balanced", "High Compress"])
            self.subtitle_var.set("Balanced")

            self.browser_dropdown.configure(state="disabled")

            self.download_btn.configure(text="Convert & Compress Video")

        elif choice == "Audio Only":
            self.url_label.configure(text="Video Link")
            self.quality_label.configure(text="Quality:")
            self.quality_dropdown.configure(state="disabled")

            self.format_dropdown.configure(values=["mp3", "m4a", "wav"])
            if self.format_var.get() not in ["mp3", "m4a", "wav"]:
                self.format_var.set("mp3")

            self.subtitle_label.configure(text="Subtitles:")
            self.subtitle_dropdown.configure(values=["None", "Embed English", "Embed Auto-Subs"])
            self.subtitle_var.set("None")

            self.browser_dropdown.configure(state="normal")

            self.download_btn.configure(text="Download Audio")
            self.thumbnail_label.configure(text="Paste a valid video URL to preview", text_color="gray")

        else:
            self.url_label.configure(text="Video Link")
            self.quality_label.configure(text="Quality:")

            video_qualities = [
                "Best Available", "2160p (4K)", "1440p (2K)", "1080p", 
                "720p", "480p", "360p", "240p", "144p"
            ]
            self.quality_dropdown.configure(state="normal", values=video_qualities)
            if self.quality_var.get() not in video_qualities:
                self.quality_var.set("1080p")

            self.format_dropdown.configure(values=["mp4", "mkv", "webm"])
            if self.format_var.get() not in ["mp4", "mkv", "webm"]:
                self.format_var.set("mp4")

            self.subtitle_label.configure(text="Subtitles:")
            self.subtitle_dropdown.configure(values=["None", "Embed English", "Embed Auto-Subs"])
            if self.subtitle_var.get() not in ["None", "Embed English", "Embed Auto-Subs"]:
                self.subtitle_var.set("None")

            self.browser_dropdown.configure(state="normal")

            self.download_btn.configure(text="Download Video")
            self.thumbnail_label.configure(text="Paste a valid video URL to preview", text_color="gray")

        self.save_config()

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_path)
        if folder:
            self.download_path = folder
            self.path_label.configure(text=folder)
            self.save_config()

    def on_url_change(self, event=None):
        if self.type_var.get() == "Convert Local Video":
            return

        url = self.url_entry.get().strip()
        if re.match(r"^https?://[^\s]+$", url):
            self.thumbnail_label.configure(text="Loading video preview...", image="")
            threading.Thread(target=self.fetch_preview, args=(url,), daemon=True).start()

    def fetch_preview(self, url):
        try:
            ydl_opts = {
                'quiet': True, 
                'skip_download': True,
            }
            self.apply_cookie_option(ydl_opts)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                thumb_url = info.get('thumbnail')
                self.original_video_title = info.get('title', '')

            ctk_img = None
            if thumb_url:
                req = urllib.request.Request(thumb_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    image_data = response.read()

                pil_img = Image.open(io.BytesIO(image_data))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(260, 160))

            self.after(0, self.update_preview_ui, ctk_img, self.original_video_title)
        except Exception:
            self.after(0, self.update_preview_ui, None, "")

    def update_preview_ui(self, ctk_img, title):
        if ctk_img:
            self.thumbnail_label.configure(image=ctk_img, text="")
        else:
            self.thumbnail_label.configure(image="", text="Could not load video preview", text_color="gray")

        self.rename_entry.delete(0, tk.END)
        if title:
            self.rename_entry.insert(0, title)

    def start_download_thread(self):
        input_val = self.url_entry.get().strip()
        if not input_val:
            messagebox.showwarning("Warning", "Please enter a valid video URL or file path.")
            return

        self.download_btn.configure(state="disabled")
        self.progress_bar.set(0)

        if self.type_var.get() == "Convert Local Video":
            self.status_label.configure(text="Processing local video...", text_color="white")
            threading.Thread(target=self.process_local_video, args=(input_val,), daemon=True).start()
        else:
            self.status_label.configure(text="Starting download...", text_color="white")
            threading.Thread(target=self.download_video, args=(input_val,), daemon=True).start()

    def get_file_duration(self, file_path):
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", file_path
        ]
        try:
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace"
            )
            return float(result.stdout.strip())
        except Exception:
            return None

    def process_local_video(self, file_path):
        if not os.path.exists(file_path):
            self.after(0, self.on_download_error, "File path does not exist.")
            return

        custom_name = self.rename_entry.get().strip()
        target_format = self.format_var.get()
        resolution = self.quality_var.get()
        compression = self.subtitle_var.get()

        base_title = re.sub(r'[\\/*?:"<>|]', "", custom_name).strip() if custom_name else "converted_video"
        output_file = os.path.join(self.download_path, f"{base_title}_converted.{target_format}")

        total_duration = self.get_file_duration(file_path)
        cmd = ["ffmpeg", "-y", "-i", file_path]

        scale_map = {
            "1080p": "scale=1920:-2",
            "720p": "scale=1280:-2",
            "480p": "scale=854:-2",
            "360p": "scale=640:-2"
        }
        if resolution in scale_map:
            cmd.extend(["-vf", scale_map[resolution]])

        crf_map = {"None": "18", "Balanced": "23", "High Compress": "28"}
        if compression in crf_map:
            cmd.extend(["-c:v", "libx264", "-crf", crf_map[compression], "-preset", "medium", "-c:a", "aac"])

        cmd.append(output_file)

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                universal_newlines=True
            )

            time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

            for line in process.stdout:
                match = time_pattern.search(line)
                if match and total_duration:
                    hours, minutes, seconds = map(float, match.groups())
                    elapsed_time = hours * 3600 + minutes * 60 + seconds
                    progress = min(elapsed_time / total_duration, 1.0)
                    percentage = int(progress * 100)
                    self.after(0, self.update_progress_ui, progress, f"Processing Video: {percentage}%")

            process.wait()

            if process.returncode == 0:
                self.record_download(file_path, base_title, "Convert Local Video", target_format, resolution)
                self.after(0, self.on_download_success)
            else:
                self.after(0, self.on_download_error, "FFmpeg failed to convert the file.")
        except Exception as e:
            self.after(0, self.on_download_error, str(e))

    def _format_size(self, bytes_val):
        if not bytes_val or bytes_val <= 0:
            return "N/A"
        if bytes_val >= 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"
        return f"{bytes_val / (1024 * 1024):.2f} MB"

    def progress_hook(self, d):
        if d["status"] == "downloading":
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded_bytes = d.get("downloaded_bytes", 0)

            if total_bytes > 0:
                progress = downloaded_bytes / total_bytes
                percentage = int(progress * 100)
                size_str = f"{self._format_size(downloaded_bytes)} / {self._format_size(total_bytes)}"
            else:
                progress = 0
                percentage = 0
                size_str = f"{self._format_size(downloaded_bytes)}"

            raw_speed = d.get("speed")
            if raw_speed:
                speed_mb = raw_speed / (1024 * 1024)
                speed_str = f"{speed_mb:05.2f} MB/s"
            else:
                speed_str = "00.00 MB/s"

            status_text = f"Downloading {percentage}% | speed {speed_str} | {size_str}"
            self.after(0, self.update_progress_ui, progress, status_text)

        elif d["status"] == "finished":
            self.after(0, self.update_progress_ui, 1.0, "Processing & converting file...")

    def update_progress_ui(self, progress_val, status_text):
        self.progress_bar.set(progress_val)
        self.status_label.configure(text=status_text)

    def download_video(self, url):
        mode = self.type_var.get()
        quality = self.quality_var.get()
        selected_format = self.format_var.get()
        subtitle_option = self.subtitle_var.get()
        custom_name = self.rename_entry.get().strip()

        raw_name = custom_name if custom_name else self.original_video_title
        sanitized_name = re.sub(r'[\\/*?:"<>|]', "", raw_name).strip() if raw_name else ""
        base_title = sanitized_name if sanitized_name else "invalidName"

        ydl_opts = {
            "progress_hooks": [self.progress_hook],
            "quiet": True,
            "no_warnings": True,
            "nocolor": True,
        }
        self.apply_cookie_option(ydl_opts)

        if subtitle_option == "Embed English":
            ydl_opts.update({
                "writesubtitles": True,
                "subtitleslangs": ["en.*", "en"],
                "embedsubtitles": True,
            })
        elif subtitle_option == "Embed Auto-Subs":
            ydl_opts.update({
                "writeautomaticsub": True,
                "subtitleslangs": ["en.*", "en"],
                "embedsubtitles": True,
            })

        actual_quality_tag = ""
        try:
            info_opts = {'quiet': True, 'skip_download': True}
            self.apply_cookie_option(info_opts)
            with yt_dlp.YoutubeDL(info_opts) as ydl_info:
                info = ydl_info.extract_info(url, download=False)
                if mode == "Audio Only":
                    actual_quality_tag = f"{int(info.get('abr', 320))}kbps" if info.get('abr') else "audio"
                else:
                    height = info.get('height')
                    if height:
                        actual_quality_tag = f"{height}p"
        except Exception:
            pass

        if "Best" in quality:
            quality_tag = actual_quality_tag if actual_quality_tag else "1080p"
            format_str = "bestvideo+bestaudio/best"
        else:
            match = re.search(r"\d+p?", quality)
            quality_tag = match.group() if match else quality
            height = re.search(r"\d+", quality).group() if re.search(r"\d+", quality) else "1080"
            format_str = (
                f"bestvideo[height<={height}]+bestaudio/"
                f"best[height<={height}]/best"
            )

        output_file_pattern = f"{base_title}-{quality_tag}.%(ext)s"
        output_template = os.path.join(self.download_path, output_file_pattern)

        if mode == "Audio Only":
            ydl_opts.update({
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": selected_format,
                    "preferredquality": "320",
                }],
            })
        else:
            ydl_opts.update({
                "format": format_str,
                "outtmpl": output_template,
                "merge_output_format": selected_format,
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.record_download(url, base_title, mode, selected_format, quality)
            self.after(0, self.on_download_success)

        except Exception as e:
            self.after(0, self.on_download_error, str(e))

    def on_download_success(self):
        self.progress_bar.set(1.0)
        self.status_label.configure(text="Operation Complete! 🎉", text_color="#2FA572")
        self.download_btn.configure(state="normal")
        messagebox.showinfo("Success", f"File saved to:\n{self.download_path}")

    def on_download_error(self, error_message):
        self.progress_bar.set(0)
        self.status_label.configure(text="Operation Failed", text_color="#D03B29")
        self.download_btn.configure(state="normal")
        messagebox.showerror("Error", f"An error occurred:\n{error_message}")


if __name__ == "__main__":
    app = VideoDownloaderApp()
    app.mainloop()