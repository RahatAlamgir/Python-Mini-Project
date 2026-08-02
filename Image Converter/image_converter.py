import os
import json
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageOps

# Integrate TkinterDnD with CustomTkinter
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    class CTkDnD(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
except ImportError:
    class CTkDnD(ctk.CTk):
        pass
    DND_FILES = None

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "config.json"

class ModernImageConverter(CTkDnD):
    def __init__(self):
        super().__init__()

        self.title("Modern Image Converter, Resizer & Editor")
        self.geometry("940x880")
        self.resizable(False, False)

        self.files_to_process = []
        self.current_preview_image = None
        self.active_image_dims = (0, 0)  # Stores (width, height)
        self.updating_aspect = False     # Guard flag to prevent calculation loops

        # Rotation state tracking (0, 90, 180, 270)
        self.rotation_angle = 0
        self.flip_h = False
        self.flip_v = False

        # Load config settings
        self.config_data = self.load_config()
        self.last_used_path = self.config_data.get("last_path", os.path.expanduser("~"))
        self.last_used_format = self.config_data.get("last_format", "PNG")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- LEFT PANEL: Image Preview & File Metadata ---
        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")

        self.lbl_preview_title = ctk.CTkLabel(
            self.left_panel, text="Image Preview & Info", font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_preview_title.pack(pady=(15, 5))

        # Preview Drop Zone Box
        self.preview_box = ctk.CTkFrame(self.left_panel, width=380, height=320, fg_color="#1a1a1a")
        self.preview_box.pack(padx=15, pady=5)
        self.preview_box.pack_propagate(False)

        self.lbl_image_display = ctk.CTkLabel(
            self.preview_box, 
            text="Drag & Drop Images Here\n\n— or —\n\nClick 'Select Images' Below", 
            text_color="gray",
            font=ctk.CTkFont(size=14)
        )
        self.lbl_image_display.pack(expand=True)

        # Metadata Info Card
        self.info_frame = ctk.CTkFrame(self.left_panel, fg_color="#242424")
        self.info_frame.pack(padx=15, pady=10, fill="x")

        self.lbl_info_name = ctk.CTkLabel(self.info_frame, text="Name: -", font=ctk.CTkFont(size=12), anchor="w")
        self.lbl_info_name.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_info_res = ctk.CTkLabel(self.info_frame, text="Resolution: -", font=ctk.CTkFont(size=12), anchor="w")
        self.lbl_info_res.pack(fill="x", padx=10, pady=2)

        self.lbl_info_size = ctk.CTkLabel(self.info_frame, text="File Size: -", font=ctk.CTkFont(size=12), anchor="w")
        self.lbl_info_size.pack(fill="x", padx=10, pady=(2, 6))

        self.btn_browse = ctk.CTkButton(
            self.left_panel,
            text="📁 Select Images",
            command=self.browse_files,
            height=38,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.btn_browse.pack(padx=15, pady=5, fill="x")

        self.lbl_file_count = ctk.CTkLabel(self.left_panel, text="0 file(s) loaded", font=ctk.CTkFont(size=12))
        self.lbl_file_count.pack(pady=(0, 10))

        # --- RIGHT PANEL: Controls & Settings ---
        self.right_panel = ctk.CTkFrame(self)
        self.right_panel.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")

        # 1. Custom File Name Output
        self.lbl_filename = ctk.CTkLabel(
            self.right_panel, text="Custom Output Name (Optional)", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_filename.pack(anchor="w", padx=15, pady=(12, 2))

        self.entry_filename = ctk.CTkEntry(
            self.right_panel, placeholder_text="Leave blank to keep original name"
        )
        self.entry_filename.pack(anchor="w", padx=15, pady=(0, 8), fill="x")

        # 2. Save Path Settings
        self.lbl_save_path = ctk.CTkLabel(
            self.right_panel, text="Output Folder Path", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_save_path.pack(anchor="w", padx=15, pady=(4, 2))

        self.path_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.path_frame.pack(fill="x", padx=15, pady=(0, 8))

        self.entry_save_path = ctk.CTkEntry(self.path_frame)
        self.entry_save_path.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_save_path.insert(0, self.last_used_path)

        self.btn_browse_dir = ctk.CTkButton(
            self.path_frame, text="Browse", width=60, command=self.browse_output_dir
        )
        self.btn_browse_dir.pack(side="right")

        # 3. Format Dropdown & Quality Control Slider
        self.format_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.format_frame.pack(fill="x", padx=15, pady=(4, 8))

        self.lbl_format = ctk.CTkLabel(
            self.format_frame, text="Target Format", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_format.pack(anchor="w", pady=(0, 2))

        self.format_var = ctk.StringVar(value=self.last_used_format)
        self.format_menu = ctk.CTkOptionMenu(
            self.format_frame,
            values=["PNG", "JPEG", "WEBP", "ICO", "BMP", "TIFF"],
            variable=self.format_var,
            command=self.on_format_changed
        )
        self.format_menu.pack(anchor="w", fill="x")

        # Quality Slider Container (for JPEG & WEBP)
        self.quality_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.quality_frame.pack(fill="x", padx=15, pady=(0, 8))

        self.lbl_quality = ctk.CTkLabel(
            self.quality_frame, text="Quality / Compression: 85%", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_quality.pack(anchor="w")

        self.quality_slider = ctk.CTkSlider(
            self.quality_frame, from_=1, to=100, number_of_steps=99, command=self.on_quality_change
        )
        self.quality_slider.set(85)
        self.quality_slider.pack(fill="x", pady=(2, 0))

        # 4. Rotation & Flipping Controls
        self.lbl_transform = ctk.CTkLabel(
            self.right_panel, text="Rotation & Flipping", font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_transform.pack(anchor="w", padx=15, pady=(4, 2))

        self.btn_transform_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.btn_transform_frame.pack(fill="x", padx=15, pady=(0, 8))

        self.btn_rot_left = ctk.CTkButton(
            self.btn_transform_frame, text="↺ 90°", width=80, command=lambda: self.apply_rotation(90)
        )
        self.btn_rot_left.pack(side="left", padx=(0, 5))

        self.btn_rot_right = ctk.CTkButton(
            self.btn_transform_frame, text="↻ 90°", width=80, command=lambda: self.apply_rotation(-90)
        )
        self.btn_rot_right.pack(side="left", padx=(0, 5))

        self.btn_flip_h = ctk.CTkButton(
            self.btn_transform_frame, text="⇄ Flip H", width=80, command=self.toggle_flip_h
        )
        self.btn_flip_h.pack(side="left", padx=(0, 5))

        self.btn_flip_v = ctk.CTkButton(
            self.btn_transform_frame, text="⇅ Flip V", width=80, command=self.toggle_flip_v
        )
        self.btn_flip_v.pack(side="left")

        # 5. Resizing Controls with Live Aspect Calculation
        self.resize_switch_var = ctk.BooleanVar(value=False)
        self.resize_switch = ctk.CTkSwitch(
            self.right_panel,
            text="Enable Resizing",
            variable=self.resize_switch_var,
            command=self.toggle_resize_inputs,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.resize_switch.pack(anchor="w", padx=15, pady=(6, 4))

        self.dim_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.dim_frame.pack(fill="x", padx=15, pady=(0, 8))

        self.entry_width = ctk.CTkEntry(self.dim_frame, placeholder_text="Width px", width=90, state="disabled")
        self.entry_width.pack(side="left", padx=(0, 10))
        self.entry_width.bind("<KeyRelease>", self.on_width_changed)

        self.entry_height = ctk.CTkEntry(self.dim_frame, placeholder_text="Height px", width=90, state="disabled")
        self.entry_height.pack(side="left", padx=(0, 10))
        self.entry_height.bind("<KeyRelease>", self.on_height_changed)

        self.aspect_ratio_var = ctk.BooleanVar(value=True)
        self.aspect_check = ctk.CTkCheckBox(
            self.dim_frame, text="Keep Aspect", variable=self.aspect_ratio_var, state="disabled"
        )
        self.aspect_check.pack(side="left")

        # 6. Metadata Strip Toggle & Overwrite Checkbox
        self.strip_metadata_var = ctk.BooleanVar(value=True)
        self.strip_metadata_check = ctk.CTkCheckBox(
            self.right_panel,
            text="Strip Metadata (EXIF / GPS / Camera Info)",
            variable=self.strip_metadata_var,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.strip_metadata_check.pack(anchor="w", padx=15, pady=(6, 4))

        self.replace_var = ctk.BooleanVar(value=False)
        self.replace_check = ctk.CTkCheckBox(
            self.right_panel,
            text="Replace / Overwrite Original Files",
            variable=self.replace_var,
            command=self.toggle_path_state,
            text_color="#FF5555",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.replace_check.pack(anchor="w", padx=15, pady=(4, 12))

        # 7. Progress & Convert Action
        self.progress_bar = ctk.CTkProgressBar(self.right_panel)
        self.progress_bar.pack(fill="x", padx=15, pady=(8, 4))
        self.progress_bar.set(0)

        self.lbl_status = ctk.CTkLabel(self.right_panel, text="Ready", font=ctk.CTkFont(size=12))
        self.lbl_status.pack(pady=(0, 8))

        self.btn_convert = ctk.CTkButton(
            self.right_panel,
            text="Start Conversion",
            command=self.process_images,
            height=45,
            fg_color="#1f538d",
            hover_color="#14375e",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.btn_convert.pack(fill="x", padx=15, pady=(0, 15))

        self.setup_drag_and_drop()
        self.update_quality_slider_state(self.last_used_format)

    # --- Rotation & Flip Controls ---
    def apply_rotation(self, angle_change):
        self.rotation_angle = (self.rotation_angle + angle_change) % 360
        if self.files_to_process:
            self.update_preview(self.files_to_process[0])

    def toggle_flip_h(self):
        self.flip_h = not self.flip_h
        if self.files_to_process:
            self.update_preview(self.files_to_process[0])

    def toggle_flip_v(self):
        self.flip_v = not self.flip_v
        if self.files_to_process:
            self.update_preview(self.files_to_process[0])

    # --- Quality Slider Helpers ---
    def on_quality_change(self, value):
        self.lbl_quality.configure(text=f"Quality / Compression: {int(value)}%")

    def update_quality_slider_state(self, fmt):
        if fmt.upper() in ("JPEG", "WEBP"):
            self.quality_slider.configure(state="normal")
            self.lbl_quality.configure(text_color=("black", "white"))
        else:
            self.quality_slider.configure(state="disabled")
            self.lbl_quality.configure(text_color="gray")

    # --- Live Aspect Ratio Handlers ---
    def on_width_changed(self, event):
        if self.updating_aspect or not self.aspect_ratio_var.get():
            return
        orig_w, orig_h = self.active_image_dims
        if orig_w == 0 or orig_h == 0:
            return

        w_str = self.entry_width.get().strip()
        if w_str.isdigit() and int(w_str) > 0:
            self.updating_aspect = True
            new_w = int(w_str)
            new_h = round(new_w * (orig_h / orig_w))
            self.entry_height.delete(0, "end")
            self.entry_height.insert(0, str(new_h))
            self.updating_aspect = False

    def on_height_changed(self, event):
        if self.updating_aspect or not self.aspect_ratio_var.get():
            return
        orig_w, orig_h = self.active_image_dims
        if orig_w == 0 or orig_h == 0:
            return

        h_str = self.entry_height.get().strip()
        if h_str.isdigit() and int(h_str) > 0:
            self.updating_aspect = True
            new_h = int(h_str)
            new_w = round(new_h * (orig_w / orig_h))
            self.entry_width.delete(0, "end")
            self.entry_width.insert(0, str(new_w))
            self.updating_aspect = False

    # --- Configuration Helpers ---
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_config(self, key, value):
        self.config_data[key] = value
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config_data, f, indent=4)
        except Exception as e:
            print(f"Failed to write config: {e}")

    # --- Drag & Drop Setup ---
    def setup_drag_and_drop(self):
        if DND_FILES is not None:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self.handle_drop)
            self.preview_box.drop_target_register(DND_FILES)
            self.preview_box.dnd_bind("<<Drop>>", self.handle_drop)

    def handle_drop(self, event):
        files = self.tk.splitlist(event.data)
        valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".ico", ".bmp", ".tiff", ".svg", ".avif"}
        
        dropped_valid_files = [f for f in files if Path(f).suffix.lower() in valid_exts]
        if dropped_valid_files:
            self.files_to_process = dropped_valid_files
            self.lbl_file_count.configure(text=f"{len(self.files_to_process)} file(s) loaded")
            self.rotation_angle = 0
            self.flip_h = False
            self.flip_v = False
            self.update_preview(self.files_to_process[0])
        else:
            messagebox.showwarning("Invalid File", "No supported image format found in dropped item(s).")

    def on_format_changed(self, selected_format):
        self.save_config("last_format", selected_format)
        self.update_quality_slider_state(selected_format)

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
            self.rotation_angle = 0
            self.flip_h = False
            self.flip_v = False
            self.update_preview(self.files_to_process[0])

    def update_preview(self, file_path):
        try:
            path_obj = Path(file_path)
            ext = path_obj.suffix.lower()

            if ext == ".svg":
                import cairosvg
                import io
                png_data = cairosvg.svg2png(url=file_path)
                img = Image.open(io.BytesIO(png_data))
            else:
                img = Image.open(file_path)

            # Apply Transformation Previews
            if self.rotation_angle != 0:
                img = img.rotate(self.rotation_angle, expand=True)
            if self.flip_h:
                img = ImageOps.mirror(img)
            if self.flip_v:
                img = ImageOps.flip(img)

            orig_w, orig_h = img.size
            self.active_image_dims = (orig_w, orig_h)

            # Retrieve File Size
            file_bytes = os.path.getsize(file_path)
            size_str = f"{file_bytes / 1024:.2f} KB" if file_bytes < 1024 * 1024 else f"{file_bytes / (1024 * 1024):.2f} MB"

            # Update Metadata Label
            self.lbl_info_name.configure(text=f"Name: {path_obj.name}")
            self.lbl_info_res.configure(text=f"Resolution: {orig_w} × {orig_h} px")
            self.lbl_info_size.configure(text=f"File Size: {size_str}")

            # Update Preview Display Image
            img_copy = img.copy()
            img_copy.thumbnail((360, 300), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img_copy, dark_image=img_copy, size=img_copy.size)

            self.lbl_image_display.configure(image=ctk_img, text="")
            self.current_preview_image = ctk_img

            # Populate width & height inputs if resize is active
            if self.resize_switch_var.get():
                self.entry_width.delete(0, "end")
                self.entry_width.insert(0, str(orig_w))
                self.entry_height.delete(0, "end")
                self.entry_height.insert(0, str(orig_h))

        except Exception as e:
            self.lbl_image_display.configure(image="", text=f"Preview Unavailable\n({e})")

    def browse_output_dir(self):
        directory = filedialog.askdirectory(initialdir=self.entry_save_path.get())
        if directory:
            self.entry_save_path.delete(0, "end")
            self.entry_save_path.insert(0, directory)
            self.save_config("last_path", directory)

    def toggle_resize_inputs(self):
        state = "normal" if self.resize_switch_var.get() else "disabled"
        self.entry_width.configure(state=state)
        self.entry_height.configure(state=state)
        self.aspect_check.configure(state=state)

        if self.resize_switch_var.get() and self.active_image_dims != (0, 0):
            self.entry_width.delete(0, "end")
            self.entry_width.insert(0, str(self.active_image_dims[0]))
            self.entry_height.delete(0, "end")
            self.entry_height.insert(0, str(self.active_image_dims[1]))

    def toggle_path_state(self):
        state = "disabled" if self.replace_var.get() else "normal"
        self.entry_save_path.configure(state=state)
        self.btn_browse_dir.configure(state=state)

    # --- Image Processing Pipeline ---
    def process_images(self):
        if not self.files_to_process:
            messagebox.showwarning("Warning", "Please select or drop at least one image file first.")
            return

        target_format = self.format_var.get().upper()
        replace_orig = self.replace_var.get()
        do_resize = self.resize_switch_var.get()
        strip_meta = self.strip_metadata_var.get()
        quality_val = int(self.quality_slider.get())
        custom_name = self.entry_filename.get().strip()

        req_w, req_h = None, None
        if do_resize:
            w_str = self.entry_width.get().strip()
            h_str = self.entry_height.get().strip()
            try:
                req_w = int(w_str) if w_str else None
                req_h = int(h_str) if h_str else None
            except ValueError:
                messagebox.showerror("Error", "Please enter valid pixel values for dimensions.")
                return

        output_dir = self.entry_save_path.get().strip()
        if not replace_orig:
            if not os.path.exists(output_dir):
                messagebox.showerror("Error", "The specified output directory does not exist.")
                return
            self.save_config("last_path", output_dir)

        total = len(self.files_to_process)
        converted_count = 0

        for idx, file_path in enumerate(self.files_to_process, start=1):
            try:
                ext = Path(file_path).suffix.lower()
                if ext == ".svg":
                    import cairosvg
                    import io
                    png_data = cairosvg.svg2png(url=file_path)
                    img = Image.open(io.BytesIO(png_data))
                else:
                    img = Image.open(file_path)

                # Capture original EXIF data before edits if metadata stripping is DISABLED
                exif_data = None if strip_meta else img.info.get("exif")

                # 1. Apply Transforms (Rotation & Flipping)
                if self.rotation_angle != 0:
                    img = img.rotate(self.rotation_angle, expand=True)
                if self.flip_h:
                    img = ImageOps.mirror(img)
                if self.flip_v:
                    img = ImageOps.flip(img)

                # 2. Resizing Stage
                if do_resize and (req_w and req_h):
                    img = img.resize((max(1, req_w), max(1, req_h)), Image.Resampling.LANCZOS)

                # 3. Handle Color Modes (JPEG white background replacement for alpha channels)
                if target_format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                    img = background

                # 4. Construct Output Path
                p = Path(file_path)
                out_ext = ".jpg" if target_format == "JPEG" else f".{target_format.lower()}"

                if custom_name:
                    filename_stem = f"{custom_name}_{idx}" if total > 1 else custom_name
                else:
                    filename_stem = p.stem

                if replace_orig:
                    save_path = p.with_name(f"{filename_stem}{out_ext}")
                else:
                    save_path = Path(output_dir) / f"{filename_stem}{out_ext}"

                # 5. Build Save Parameters
                save_kwargs = {}
                if target_format in ("JPEG", "WEBP"):
                    save_kwargs["quality"] = quality_val

                if not strip_meta and exif_data:
                    save_kwargs["exif"] = exif_data

                # 6. Save Output Image
                if target_format == "ICO":
                    img.save(save_path, format="ICO", sizes=[(256, 256)])
                else:
                    img.save(save_path, format=target_format, **save_kwargs)

                if replace_orig and save_path != p and p.exists():
                    os.remove(p)

                converted_count += 1
            except Exception as e:
                print(f"Failed to process {file_path}: {e}")

            self.progress_bar.set(idx / total)
            self.lbl_status.configure(text=f"Processing {idx}/{total}...")
            self.update_idletasks()

        self.lbl_status.configure(text="Processing complete!")
        messagebox.showinfo("Success", f"Successfully converted {converted_count} out of {total} images.")

if __name__ == "__main__":
    app = ModernImageConverter()
    app.mainloop()