import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image
import customtkinter as ctk

# Set the modern design theme out of the box
ctk.set_appearance_mode("Dark") 
ctk.set_default_color_theme("blue") 

class ModernImageResizer(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.title("Image Resizer Pro")
        self.geometry("540x720")
        self.minsize(500, 650)

        # State Variables
        self.image_path = None
        self.folder_path = None
        self.original_width = 0
        self.original_height = 0
        self.updating = False

        # --- UI LAYOUT ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # 1. Header Title
        self.title_label = ctk.CTkLabel(self, text="IMAGE RESIZER PRO", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # 2. File Selection Row
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.select_img_btn = ctk.CTkButton(self.btn_frame, text="Select Image", font=ctk.CTkFont(family="Segoe UI", weight="bold"), command=self.select_image)
        self.select_img_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.select_dir_btn = ctk.CTkButton(self.btn_frame, text="Select Folder (Batch)", font=ctk.CTkFont(family="Segoe UI", weight="bold"), command=self.select_folder)
        self.select_dir_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # 3. Modern Drag & Drop Zone
        self.drop_label = tk.Label(
            self,
            text="⬇\nDrag & Drop Image or Folder Here",
            font=("Segoe UI", 11),
            bg="#2b2b2b",
            fg="#a6adc8",
            bd=1,
            relief="solid",
            height=3
        )
        self.drop_label.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind("<<Drop>>", self.handle_drop)

        # 4. Interactive Preview Card
        self.preview_frame = ctk.CTkFrame(self, fg_color="#212121", corner_radius=12)
        self.preview_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(0, weight=1)

        # Fixed here: changed italic=True to slant="italic"
        self.preview_label = ctk.CTkLabel(self.preview_frame, text="No Image Loaded", font=ctk.CTkFont(family="Segoe UI", slant="italic"), text_color="#7f7f7f")
        self.preview_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Info Status Banner
        self.info_label = ctk.CTkLabel(self, text="Ready", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#a6adc8")
        self.info_label.grid(row=4, column=0, padx=20, pady=5, sticky="w")

        # 5. Dimensions Settings Card
        self.settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.settings_frame.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        self.settings_frame.grid_columnconfigure((0, 1), weight=1)

        # Width Input
        self.w_div = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.w_div.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        ctk.CTkLabel(self.w_div, text="Width (px)", font=ctk.CTkFont(family="Segoe UI", size=12)).pack(anchor="w")
        self.width_entry = ctk.CTkEntry(self.w_div, placeholder_text="Width")
        self.width_entry.pack(fill="x", pady=(2, 0))

        # Height Input
        self.h_div = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.h_div.grid(row=0, column=1, padx=(10, 0), sticky="ew")
        ctk.CTkLabel(self.h_div, text="Height (px)", font=ctk.CTkFont(family="Segoe UI", size=12)).pack(anchor="w")
        self.height_entry = ctk.CTkEntry(self.h_div, placeholder_text="Height")
        self.height_entry.pack(fill="x", pady=(2, 0))

        # 6. Checkboxes Controls
        self.opt_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.opt_frame.grid(row=6, column=0, padx=20, pady=5, sticky="ew")
        
        self.keep_ratio = ctk.BooleanVar(value=True)
        self.ratio_check = ctk.CTkCheckBox(self.opt_frame, text="Keep Aspect Ratio", variable=self.keep_ratio, font=ctk.CTkFont(family="Segoe UI", size=13))
        self.ratio_check.pack(side="left", expand=True, anchor="w")

        self.replace_original = ctk.BooleanVar()
        self.replace_check = ctk.CTkCheckBox(self.opt_frame, text="Replace Original", variable=self.replace_original, font=ctk.CTkFont(family="Segoe UI", size=13))
        self.replace_check.pack(side="right", expand=True, anchor="e")

        # 7. Modern Compression Slider
        self.slider_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.slider_frame.grid(row=7, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.slider_frame, text="Quality / Compression Ratio", font=ctk.CTkFont(family="Segoe UI", size=12)).pack(anchor="w")
        self.quality_slider = ctk.CTkSlider(self.slider_frame, from_=10, to=100, number_of_steps=90)
        self.quality_slider.set(90)
        self.quality_slider.pack(fill="x", pady=(4, 0))

        # 8. Primary Dynamic Action Button
        self.process_btn = ctk.CTkButton(
            self, 
            text="RESIZE TARGET", 
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            height=45,
            command=self.process
        )
        self.process_btn.grid(row=8, column=0, padx=20, pady=(15, 25), sticky="ew")

        # Dynamic Aspect Ratio Bindings
        self.width_entry.bind("<KeyRelease>", self.update_height)
        self.height_entry.bind("<KeyRelease>", self.update_width)

    # -------- DRAG & DROP --------
    def handle_drop(self, event):
        path = event.data.strip("{}")
        if os.path.isfile(path):
            self.load_image(path)
        elif os.path.isdir(path):
            self.load_folder(path)

    # -------- SELECT IMAGE --------
    def select_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if path:
            self.load_image(path)

    def load_image(self, path):
        self.folder_path = None
        self.image_path = path

        img = Image.open(path)
        self.original_width, self.original_height = img.size

        self.info_label.configure(text=f"Loaded: {os.path.basename(path)} ({self.original_width}x{self.original_height})")

        self.width_entry.delete(0, tk.END)
        self.width_entry.insert(0, str(self.original_width))

        self.height_entry.delete(0, tk.END)
        self.height_entry.insert(0, str(self.original_height))

        self.show_preview(img)

    # -------- SELECT FOLDER --------
    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.load_folder(path)

    def load_folder(self, path):
        self.image_path = None
        self.folder_path = path
        self.info_label.configure(text=f"Batch Directory Target: {path}")
        self.preview_label.configure(image=None, text="Batch Directory Selected")

    # -------- PREVIEW --------
    def show_preview(self, img):
        preview = img.copy()
        preview.thumbnail((260, 220))
        self.ctk_img = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
        self.preview_label.configure(image=self.ctk_img, text="")

    # -------- ASPECT RATIO LOGIC --------
    def update_height(self, event):
        if not self.keep_ratio.get() or self.updating or not self.original_width:
            return
        try:
            self.updating = True
            val = self.width_entry.get()
            if val:
                w = int(val)
                ratio = self.original_height / self.original_width
                self.height_entry.delete(0, tk.END)
                self.height_entry.insert(0, str(int(w * ratio)))
        except ValueError:
            pass
        self.updating = False

    def update_width(self, event):
        if not self.keep_ratio.get() or self.updating or not self.original_height:
            return
        try:
            self.updating = True
            val = self.height_entry.get()
            if val:
                h = int(val)
                ratio = self.original_width / self.original_height
                self.width_entry.delete(0, tk.END)
                self.width_entry.insert(0, str(int(h * ratio)))
        except ValueError:
            pass
        self.updating = False

    # -------- MAIN PROCESS --------
    def process(self):
        try:
            w = int(self.width_entry.get())
            h = int(self.height_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid dimensions specified.")
            return

        quality = int(self.quality_slider.get())

        if self.image_path:
            self.resize_single(w, h, quality)
        elif self.folder_path:
            self.resize_batch(w, h, quality)
        else:
            messagebox.showerror("Error", "Select an image or folder first.")

    def save_image(self, img, path, quality):
        ext = path.lower()
        if ext.endswith((".jpg", ".jpeg")):
            img.save(path, quality=quality, optimize=True)
        elif ext.endswith(".png"):
            compress = int((100 - quality) / 10)
            img.save(path, compress_level=compress, optimize=True)
        else:
            img.save(path)

    def resize_single(self, w, h, quality):
        try:
            img = Image.open(self.image_path)
            if self.keep_ratio.get():
                img.thumbnail((w, h))
                resized = img
            else:
                resized = img.resize((w, h), Image.LANCZOS)

            if self.replace_original.get():
                save_path = self.image_path
            else:
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".jpg",
                    filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")]
                )
                if not save_path:
                    return

            self.save_image(resized, save_path, quality)
            self.show_preview(resized)
            messagebox.showinfo("Success", "Image successfully resized!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def resize_batch(self, w, h, quality):
        try:
            output_folder = os.path.join(self.folder_path, "resized_output")
            os.makedirs(output_folder, exist_ok=True)

            count = 0
            for file in os.listdir(self.folder_path):
                if file.lower().endswith((".png", ".jpg", ".jpeg")):
                    path = os.path.join(self.folder_path, file)
                    img = Image.open(path)

                    if self.keep_ratio.get():
                        img.thumbnail((w, h))
                        resized = img
                    else:
                        resized = img.resize((w, h), Image.LANCZOS)

                    save_path = os.path.join(output_folder, file)
                    self.save_image(resized, save_path, quality)
                    count += 1

            messagebox.showinfo("Done", f"{count} images resized!\nSaved in: resized_output")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = ModernImageResizer()
    app.mainloop()