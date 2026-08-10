import io
import json
import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image
import urllib.request
import yt_dlp

CONFIG_FILE = "app_config.json"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class VideoDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Video Downloader")
        self.geometry("640x640")
        self.resizable(False, False)

        try:
            self.iconbitmap("icon.ico")
        except Exception:
            pass  # Fallback if icon file is missing

        # Load saved settings or use defaults
        self.config = self.load_config()
        self.download_path = self.config.get("download_path", os.path.expanduser("~/Downloads"))
        self.last_quality = self.config.get("quality", "1080p")
        self.last_download_type = self.config.get("download_type", "Video")
        self.last_video_format = self.config.get("video_format", "mp4")
        self.last_subtitle = self.config.get("subtitle", "None")

        self.original_video_title = ""

        self._build_ui()

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
            "subtitle": self.subtitle_var.get()
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def _build_ui(self):
        # Header Section
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=30, pady=(15, 5))

        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Video Downloader", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.title_label.pack(anchor="w")

        # URL Input Section
        self.url_frame = ctk.CTkFrame(self, corner_radius=10)
        self.url_frame.pack(fill="x", padx=30, pady=5)

        self.url_label = ctk.CTkLabel(self.url_frame, text="Video Link", font=ctk.CTkFont(size=12, weight="bold"))
        self.url_label.pack(anchor="w", padx=15, pady=(8, 2))

        self.url_entry = ctk.CTkEntry(
            self.url_frame, placeholder_text="Paste video URL from YouTube, Instagram, TikTok, Facebook...", height=35
        )
        self.url_entry.pack(fill="x", padx=15, pady=(0, 10))
        self.url_entry.bind("<KeyRelease>", self.on_url_change)

        # Thumbnail Preview Frame
        self.preview_frame = ctk.CTkFrame(self, height=180, corner_radius=10)
        self.preview_frame.pack(fill="x", padx=30, pady=5)
        self.preview_frame.pack_propagate(False)

        self.thumbnail_label = ctk.CTkLabel(
            self.preview_frame, text="Paste a valid video URL to preview", text_color="gray"
        )
        self.thumbnail_label.pack(expand=True, fill="both")

        # Options Section
        self.options_frame = ctk.CTkFrame(self, corner_radius=10)
        self.options_frame.pack(fill="x", padx=30, pady=5)

        # Name Field (Spans columns 1 to 3, fully aligned to right edge)
        self.rename_label = ctk.CTkLabel(self.options_frame, text="Name:", font=ctk.CTkFont(size=12))
        self.rename_label.grid(row=0, column=0, padx=(15, 5), pady=(10, 4), sticky="w")

        self.rename_entry = ctk.CTkEntry(
            self.options_frame, placeholder_text="Video name will autofill here...", height=32
        )
        self.rename_entry.grid(row=0, column=1, columnspan=3, padx=(5, 15), pady=(10, 4), sticky="ew")

        # Type (Video / Audio Only)
        self.type_label = ctk.CTkLabel(self.options_frame, text="Mode:", font=ctk.CTkFont(size=12))
        self.type_label.grid(row=1, column=0, padx=(15, 5), pady=4, sticky="w")

        self.type_var = ctk.StringVar(value=self.last_download_type)
        self.type_dropdown = ctk.CTkOptionMenu(
            self.options_frame,
            values=["Video", "Audio Only"],
            variable=self.type_var,
            height=32,
            command=self.on_type_change
        )
        self.type_dropdown.grid(row=1, column=1, padx=5, pady=4, sticky="ew")

        # Quality Dropdown (Aligned right edge with Name entry)
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

        # Format Selection
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

        # Subtitle Selection (Aligned right edge with Name entry)
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

        # Save Location
        self.path_button = ctk.CTkButton(
            self.options_frame,
            text="Choose Folder",
            fg_color="transparent",
            border_width=1,
            height=32,
            command=self.browse_folder,
        )
        self.path_button.grid(row=3, column=0, columnspan=2, padx=(15, 5), pady=(4, 10), sticky="w")

        self.path_label = ctk.CTkLabel(
            self.options_frame, text=self.download_path, text_color="gray", anchor="w"
        )
        self.path_label.grid(row=3, column=2, columnspan=2, padx=(5, 15), pady=(4, 10), sticky="ew")

        # Grid column configuration for balanced alignment
        self.options_frame.grid_columnconfigure(0, weight=0)
        self.options_frame.grid_columnconfigure(1, weight=1)
        self.options_frame.grid_columnconfigure(2, weight=0)
        self.options_frame.grid_columnconfigure(3, weight=1)

        # Download Button
        self.download_btn = ctk.CTkButton(
            self,
            text="Download",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=42,
            corner_radius=8,
            command=self.start_download_thread,
        )
        self.download_btn.pack(fill="x", padx=30, pady=(10, 5))

        # Progress Section
        self.progress_bar = ctk.CTkProgressBar(self, width=580, height=10)
        self.progress_bar.pack(padx=30, pady=(4, 2))
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.pack(pady=(0, 10))

        # Trigger initial state UI
        self.on_type_change(self.type_var.get())

    def on_type_change(self, choice):
        if choice == "Audio Only":
            self.quality_dropdown.configure(state="disabled")
            self.format_dropdown.configure(values=["mp3", "m4a", "wav"])
            if self.format_var.get() not in ["mp3", "m4a", "wav"]:
                self.format_var.set("mp3")
            self.download_btn.configure(text="Download Audio")
        else:
            self.quality_dropdown.configure(state="normal")
            self.format_dropdown.configure(values=["mp4", "mkv", "webm"])
            if self.format_var.get() not in ["mp4", "mkv", "webm"]:
                self.format_var.set("mp4")
            self.download_btn.configure(text="Download Video")
        self.save_config()

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_path)
        if folder:
            self.download_path = folder
            self.path_label.configure(text=folder)
            self.save_config()

    def on_url_change(self, event=None):
        url = self.url_entry.get().strip()
        if re.match(r"^https?://[^\s]+$", url):
            self.thumbnail_label.configure(text="Loading video preview...", image="")
            threading.Thread(target=self.fetch_preview, args=(url,), daemon=True).start()

    def fetch_preview(self, url):
        try:
            ydl_opts = {'quiet': True, 'skip_download': True}
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

        # Autofill the Name field with the extracted video title
        self.rename_entry.delete(0, tk.END)
        if title:
            self.rename_entry.insert(0, title)

    def start_download_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a valid video URL.")
            return

        self.download_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text="Starting download...", text_color="white")

        threading.Thread(target=self.download_video, args=(url,), daemon=True).start()

    def progress_hook(self, d):
        if d["status"] == "downloading":
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded_bytes = d.get("downloaded_bytes", 0)

            if total_bytes:
                progress = downloaded_bytes / total_bytes
                percentage = int(progress * 100)
                speed = d.get("_speed_str", "N/A").strip()
                eta = d.get("_eta_str", "N/A").strip()
                self.after(0, self.update_progress_ui, progress, f"Downloading: {percentage}% | Speed: {speed} | ETA: {eta}")

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

        # Sanitize name
        raw_name = custom_name if custom_name else self.original_video_title
        sanitized_name = re.sub(r'[\\/*?:"<>|]', "", raw_name).strip() if raw_name else ""
        base_title = sanitized_name if sanitized_name else "invalidName"

        ydl_opts = {
            "progress_hooks": [self.progress_hook],
            "quiet": True,
            "no_warnings": True,
        }

        # Subtitle handling
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

        # Fetch video information to resolve actual quality if "Best Available" is selected
        actual_quality_tag = ""
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl_info:
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

            self.after(0, self.on_download_success)

        except Exception as e:
            self.after(0, self.on_download_error, str(e))

    def on_download_success(self):
        self.progress_bar.set(1.0)
        self.status_label.configure(text="Download Complete! 🎉", text_color="#2FA572")
        self.download_btn.configure(state="normal")
        messagebox.showinfo("Success", f"File saved to:\n{self.download_path}")

    def on_download_error(self, error_message):
        self.progress_bar.set(0)
        self.status_label.configure(text="Download Failed", text_color="#D03B29")
        self.download_btn.configure(state="normal")
        messagebox.showerror("Error", f"An error occurred:\n{error_message}")


if __name__ == "__main__":
    app = VideoDownloaderApp()
    app.mainloop()