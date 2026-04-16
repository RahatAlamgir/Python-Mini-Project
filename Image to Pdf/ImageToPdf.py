import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os

selected_images = []
thumbnails = []
thumb_labels = []
drag_index = None


THUMB_SIZE = 120
COLUMNS = 5

drag_data = {
    "index": None,
    "ghost": None
}


hover_index = None

# Page sizes (72 DPI approx)
PAGE_SIZES = {
    "None": None,
    "A5": (420, 595),
    "A4": (595, 842),
    "A3": (842, 1191),
    "Letter": (612, 792),
    "Legal": (612, 1008),
    "Square": (800, 800)
}

# ---------------- SELECT ----------------
def select_images():
    files = filedialog.askopenfilenames(
        filetypes=[("Images", "*.png *.jpg *.jpeg")]
    )
    if files:
        selected_images.extend(files)
        refresh_thumbnails()

# ---------------- THUMBNAILS ----------------
def bind_drag(widget, index):
    widget.bind("<Button-1>", lambda e: start_drag(e, index))
    widget.bind("<B1-Motion>", on_drag)
    widget.bind("<ButtonRelease-1>", on_drop)

def refresh_thumbnails():
    for widget in canvas_frame.winfo_children():
        widget.destroy()

    for i, path in enumerate(selected_images):
        frame = tk.Frame(canvas_frame, bd=2, relief="ridge")
        frame.grid(row=i//COLUMNS, column=i % COLUMNS, padx=8, pady=8)

        img = Image.open(path)
        img.thumbnail((THUMB_SIZE, THUMB_SIZE))
        tk_img = ImageTk.PhotoImage(img)

        lbl = tk.Label(frame, image=tk_img)
        lbl.image = tk_img
        lbl.pack()

        name = tk.Label(frame, text=os.path.basename(path), wraplength=100)
        name.pack()

        # bind to frame
        bind_drag(frame, i)

        # bind to image label
        bind_drag(lbl, i)

        # bind to text label
        bind_drag(name, i)

# ---------------- DRAG START ----------------
def start_drag(event, index):
    drag_data["index"] = index

    # create ghost window
    ghost = tk.Toplevel(root)
    ghost.overrideredirect(True)
    ghost.attributes("-alpha", 0.7)
    ghost.attributes("-topmost", True)

    img = Image.open(selected_images[index])
    img.thumbnail((120, 120))
    tk_img = ImageTk.PhotoImage(img)

    label = tk.Label(ghost, image=tk_img, bd=2, relief="solid")
    label.image = tk_img
    label.pack()

    drag_data["ghost"] = ghost

# ---------------- DRAG MOVE ----------------
def on_drag(event):
    ghost = drag_data["ghost"]
    if not ghost:
        return

    # move ghost with cursor
    x = root.winfo_pointerx()
    y = root.winfo_pointery()
    ghost.geometry(f"+{x+10}+{y+10}")

    # detect widget under mouse
    widget = root.winfo_containing(x, y)

    for i, frame in enumerate(canvas_frame.winfo_children()):
        if frame == widget or frame == widget.master:
            highlight_target(i)
            drag_data["target"] = i
            break

# ---------------- HIGHLIGHT ----------------
def highlight_target(target_index):
    for i, frame in enumerate(canvas_frame.winfo_children()):
        if i == target_index:
            frame.config(bg="lightgreen")
        else:
            frame.config(bg="SystemButtonFace")

# ---------------- DROP ----------------
def on_drop(event):
    ghost = drag_data["ghost"]
    if ghost:
        ghost.destroy()

    src = drag_data.get("index")
    dst = drag_data.get("target")

    if src is not None and dst is not None and src != dst:
        item = selected_images.pop(src)
        selected_images.insert(dst, item)

    drag_data["index"] = None
    drag_data["ghost"] = None
    drag_data["target"] = None

    animate_reorder()

# ---------------- SMOOTH ANIMATION ----------------
def animate_reorder():
    # simple fake animation (refresh delay)
    for frame in canvas_frame.winfo_children():
        frame.grid_configure(padx=20, pady=20)

    root.after(80, lambda: refresh_thumbnails())

# ---------------- PREVIEW ----------------
def show_preview(index):
    img = Image.open(selected_images[index])
    img.thumbnail((300, 300))
    tk_img = ImageTk.PhotoImage(img)
    preview_label.image = tk_img
    preview_label.config(image=tk_img)

# ---------------- RESIZE ----------------
def resize_to_page(img, size):
    if size is None:
        return img

    page_w, page_h = size
    img_ratio = img.width / img.height
    page_ratio = page_w / page_h

    if img_ratio > page_ratio:
        new_w = page_w
        new_h = int(page_w / img_ratio)
    else:
        new_h = page_h
        new_w = int(page_h * img_ratio)

    img = img.resize((new_w, new_h))
    bg = Image.new("RGB", (page_w, page_h), "white")

    bg.paste(img, ((page_w-new_w)//2, (page_h-new_h)//2))
    return bg

# ---------------- CONVERT ----------------
def convert_to_pdf():
    if not selected_images:
        messagebox.showerror("Error", "No images selected!")
        return

    save_path = filedialog.asksaveasfilename(defaultextension=".pdf")
    if not save_path:
        return

    size = PAGE_SIZES[page_size.get()]
    imgs = []

    for p in selected_images:
        img = Image.open(p)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img = resize_to_page(img, size)
        imgs.append(img)

    imgs[0].save(save_path, save_all=True, append_images=imgs[1:])
    messagebox.showinfo("Done", "PDF Created!")

# ---------------- UI ----------------
root = tk.Tk()
root.title("Image → PDF Pro Tool")
root.geometry("900x500")

# LEFT SCROLL AREA
canvas = tk.Canvas(root)
scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
canvas_frame = tk.Frame(canvas)

canvas_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas.create_window((0, 0), window=canvas_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="left", fill="y")

# RIGHT PANEL
right = tk.Frame(root)
right.pack(side="right", padx=10)

preview_label = tk.Label(right)
preview_label.pack(pady=10)

tk.Button(right, text="Select Images", command=select_images).pack(pady=5)

tk.Label(right, text="Page Size").pack()
page_size = tk.StringVar(value="None")
ttk.Combobox(right, textvariable=page_size,
             values=list(PAGE_SIZES.keys()),
             state="readonly").pack()

tk.Button(right, text="Convert", bg="green", fg="white",
          command=convert_to_pdf).pack(pady=20)

root.mainloop()