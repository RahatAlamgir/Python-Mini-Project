import os
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image

# Initialize UI Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ModernImageConverter(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Modern Image Converter & Resizer")
        self.geometry("680x720")
        self.resizable(False, False)

        self.files_to_process = []

        # Header Title
        self.header_label = ctk.CTkLabel(
            self, 
            text="Image Converter & Resizer", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.header_label.pack(pady=(20, 10))

        # --- File Selection Frame ---
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.pack(fill="x", padx=25, pady=10)

        self.btn_browse = ctk.CTkButton(
            self.file_frame, 
            text="Select Files or Drag Folders", 
            command=self.browse_files,
            height=38,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.btn_browse.pack(side="left", padx=15, pady=15, expand=True, fill="x")

        self.lbl_file_count = ctk.CTkLabel(
            self.file_frame, 
            text="No files selected", 
            font=ctk.CTkFont(size=13)
        )
        self.lbl_file_count.pack(side="right", padx=15, pady=15)

        # --- Settings Container ---
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.pack(fill="x", padx=25, pady=10)

        # Conversion Format Section
        self.lbl_format = ctk.CTkLabel(
            self.settings_frame, 
            text="Output Format", 
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.lbl_format.pack(anchor="w", padx=20, pady=(15, 5))

        self.format_var = ctk.StringVar(value="PNG")
        self.format_menu = ctk.CTkOptionMenu(
            self.settings_frame, 
            values=["PNG", "JPEG", "WEBP", "ICO", "BMP", "TIFF"],
            variable=self.format_var,
            width=180,
            height=32
        )
        self.format_menu.pack(anchor="w", padx=20, pady=(0, 15))

        # Divider
        ctk.CTkFrame(self.settings_frame, height=2, fg_color="gray30").pack(fill="x", padx=20, pady=5)

        # Resizing Options
        self.resize_switch_var = ctk.BooleanVar(value=False)
        self.resize_switch = ctk.CTkSwitch(
            self.settings_frame, 
            text="Enable Resizing", 
            variable=self.resize_switch_var,
            command=self.toggle_resize_inputs,
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.resize_switch.pack(anchor="w", padx=20, pady=(15, 10))

        self.dim_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.dim_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.lbl_width = ctk.CTkLabel(self.dim_frame, text="Width (px):")
        self.lbl_width.pack(side="left", padx=(0, 5))
        
        self.entry_width = ctk.CTkEntry(self.dim_frame, width=90, state="disabled")
        self.entry_width.pack(side="left", padx=(0, 20))

        self.lbl_height = ctk.CTkLabel(self.dim_frame, text="Height (px):")
        self.lbl_height.pack(side="left", padx=(0, 5))

        self.entry_height = ctk.CTkEntry(self.dim_frame, width=90, state="disabled")
        self.entry_height.pack(side="left", padx=(0, 20))

        self.aspect_ratio_var = ctk.BooleanVar(value=True)
        self.aspect_check = ctk.CTkCheckBox(
            self.dim_frame, 
            text="Maintain Aspect Ratio", 
            variable=self.aspect_ratio_var,
            state="disabled"
        )
        self.aspect_check.pack(side="left")

        # Divider
        ctk.CTkFrame(self.settings_frame, height=2, fg_color="gray30").pack(fill="x", padx=20, pady=5)

        # File Handling Section
        self.replace_var = ctk.BooleanVar(value=False)
        self.replace_check = ctk.CTkCheckBox(
            self.settings_frame, 
            text="Replace Original Image (Overwrites file if format matches)", 
            variable=self.replace_var,
            text_color="#FF5555",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.replace_check.pack(anchor="w", padx=20, pady=15)

        # --- Action Button & Progress Bar ---
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.pack(fill="x", padx=25, pady=(15, 5))
        self.progress_bar.set(0)

        self.lbl_status = ctk.CTkLabel(self, text="Ready", font=ctk.CTkFont(size=12))
        self.lbl_status.pack(pady=(0, 10))

        self.btn_convert = ctk.CTkButton(
            self, 
            text="Start Conversion", 
            command=self.process_images,
            height=45,
            fg_color="#1f538d",
            hover_color="#14375e",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.btn_convert.pack(fill="x", padx=25, pady=(0, 20))

    def browse_files(self):
        files = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[
                ("Image Files", "*.png *.jpg *.jpeg *.webp *.ico *.bmp *.tiff *.svg *.avif"),
                ("All Files", "*.*")
            ]
        )
        if files:
            self.files_to_process = list(files)
            self.lbl_file_count.configure(text=f"{len(self.files_to_process)} file(s) selected")

    def toggle_resize_inputs(self):
        state = "normal" if self.resize_switch_var.get() else "disabled"
        self.entry_width.configure(state=state)
        self.entry_height.configure(state=state)
        self.aspect_check.configure(state=state)

    def process_images(self):
        if not self.files_to_process:
            messagebox.showwarning("Warning", "Please select at least one image file first.")
            return

        target_format = self.format_var.get().upper()
        replace_orig = self.replace_var.get()
        do_resize = self.resize_switch_var.get()

        target_w, target_h = None, None
        if do_resize:
            try:
                target_w = int(self.entry_width.get()) if self.entry_width.get() else None
                target_h = int(self.entry_height.get()) if self.entry_height.get() else None
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numerical values for dimensions.")
                return

        output_dir = None
        if not replace_orig:
            output_dir = filedialog.askdirectory(title="Select Output Folder")
            if not output_dir:
                return

        total = len(self.files_to_process)
        converted_count = 0

        for idx, file_path in enumerate(self.files_to_process, start=1):
            try:
                # Handle SVG input conversion
                ext = Path(file_path).suffix.lower()
                if ext == ".svg":
                    import cairosvg
                    import io
                    png_data = cairosvg.svg2png(url=file_path)
                    img = Image.open(io.BytesIO(png_data))
                else:
                    img = Image.open(file_path)

                # Convert color mode for JPEG / target compatibility
                if target_format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                    img = background

                # Handle Resizing
                if do_resize and (target_w or target_h):
                    orig_w, orig_h = img.size
                    if self.aspect_ratio_var.get():
                        if target_w and not target_h:
                            target_h = int(orig_h * (target_w / orig_w))
                        elif target_h and not target_w:
                            target_w = int(orig_w * (target_h / orig_h))
                        elif target_w and target_h:
                            img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
                            target_w, target_h = img.size

                    if not self.aspect_ratio_var.get():
                        img = img.resize((target_w or orig_w, target_h or orig_h), Image.Resampling.LANCZOS)

                # Determine Save Path
                p = Path(file_path)
                out_ext = f".{target_format.lower()}"
                if target_format == "JPEG":
                    out_ext = ".jpg"

                if replace_orig:
                    save_path = p.with_suffix(out_ext)
                else:
                    save_path = Path(output_dir) / f"{p.stem}{out_ext}"

                # Save Image
                if target_format == "ICO":
                    img.save(save_path, format="ICO", sizes=[(256, 256)])
                else:
                    img.save(save_path, format=target_format)

                # If replace original was selected and file format changed, remove old original file
                if replace_orig and save_path != p and p.exists():
                    os.remove(p)

                converted_count += 1
            except Exception as e:
                print(f"Failed to process {file_path}: {e}")

            # Update progress UI
            self.progress_bar.set(idx / total)
            self.lbl_status.configure(text=f"Processing {idx}/{total}...")
            self.update_idletasks()

        self.lbl_status.configure(text="Processing complete!")
        messagebox.showinfo("Success", f"Successfully processed {converted_count} out of {total} images.")

if __name__ == "__main__":
    app = ModernImageConverter()
    app.mainloop()