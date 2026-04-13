import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk
import os

class ImageResizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Resizer Pro")
        self.root.geometry("550x620")

        self.image_path = None
        self.folder_path = None
        self.original_width = 0
        self.original_height = 0

        # Buttons
        tk.Button(root, text="Select Image", command=self.select_image).pack(pady=5)
        tk.Button(root, text="Select Folder (Batch)", command=self.select_folder).pack(pady=5)

        # Drag & Drop Area
        self.drop_label = tk.Label(root, text="Drag & Drop Image or Folder Here", bg="lightgray", width=40, height=3)
        self.drop_label.pack(pady=10)

        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind("<<Drop>>", self.handle_drop)

        # Info
        self.info_label = tk.Label(root, text="No selection")
        self.info_label.pack()

        # Preview
        self.preview_label = tk.Label(root)
        self.preview_label.pack(pady=10)

        # Width
        tk.Label(root, text="Width:").pack()
        self.width_entry = tk.Entry(root)
        self.width_entry.pack()

        # Height
        tk.Label(root, text="Height:").pack()
        self.height_entry = tk.Entry(root)
        self.height_entry.pack()

        # Options
        self.keep_ratio = tk.BooleanVar()
        tk.Checkbutton(root, text="Keep Aspect Ratio", variable=self.keep_ratio).pack()

        self.replace_original = tk.BooleanVar()
        tk.Checkbutton(root, text="Replace Original (Single only)", variable=self.replace_original).pack()

        # Quality slider
        tk.Label(root, text="Quality / Compression").pack(pady=5)
        self.quality_slider = tk.Scale(root, from_=10, to=100, orient="horizontal")
        self.quality_slider.set(90)
        self.quality_slider.pack()

        # Resize Button
        tk.Button(root, text="Resize", command=self.process).pack(pady=15)

        # Bind ratio logic
        self.width_entry.bind("<KeyRelease>", self.update_height)
        self.height_entry.bind("<KeyRelease>", self.update_width)

        self.updating = False

    # -------- DRAG & DROP --------
    def handle_drop(self, event):
        path = event.data.strip("{}")  # fix for spaces
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

        self.info_label.config(text=f"Image: {os.path.basename(path)} ({self.original_width}x{self.original_height})")

        self.width_entry.delete(0, tk.END)
        self.width_entry.insert(0, self.original_width)

        self.height_entry.delete(0, tk.END)
        self.height_entry.insert(0, self.original_height)

        self.show_preview(img)

    # -------- SELECT FOLDER --------
    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.load_folder(path)

    def load_folder(self, path):
        self.image_path = None
        self.folder_path = path
        self.info_label.config(text=f"Folder: {path}")
        self.preview_label.config(image="")

    # -------- PREVIEW --------
    def show_preview(self, img):
        preview = img.copy()
        preview.thumbnail((250, 250))
        self.tk_img = ImageTk.PhotoImage(preview)
        self.preview_label.config(image=self.tk_img)

    # -------- ASPECT RATIO --------
    def update_height(self, event):
        if not self.keep_ratio.get() or self.updating:
            return
        try:
            self.updating = True
            w = int(self.width_entry.get())
            ratio = self.original_height / self.original_width
            self.height_entry.delete(0, tk.END)
            self.height_entry.insert(0, int(w * ratio))
        except:
            pass
        self.updating = False

    def update_width(self, event):
        if not self.keep_ratio.get() or self.updating:
            return
        try:
            self.updating = True
            h = int(self.height_entry.get())
            ratio = self.original_width / self.original_height
            self.width_entry.delete(0, tk.END)
            self.width_entry.insert(0, int(h * ratio))
        except:
            pass
        self.updating = False

    # -------- MAIN PROCESS --------
    def process(self):
        try:
            w = int(self.width_entry.get())
            h = int(self.height_entry.get())
        except:
            messagebox.showerror("Error", "Invalid size")
            return

        quality = self.quality_slider.get()

        if self.image_path:
            self.resize_single(w, h, quality)
        elif self.folder_path:
            self.resize_batch(w, h, quality)
        else:
            messagebox.showerror("Error", "Select something first")

    # -------- SAVE WITH QUALITY --------
    def save_image(self, img, path, quality):
        ext = path.lower()

        if ext.endswith(".jpg") or ext.endswith(".jpeg"):
            img.save(path, quality=quality, optimize=True)
        elif ext.endswith(".png"):
            compress = int((100 - quality) / 10)  # 0–9
            img.save(path, compress_level=compress, optimize=True)
        else:
            img.save(path)

    # -------- SINGLE --------
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

            messagebox.showinfo("Success", "Image resized!")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # -------- BATCH --------
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

            messagebox.showinfo("Done", f"{count} images resized!\nSaved in resized_output")

        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = ImageResizerApp(root)
    root.mainloop()