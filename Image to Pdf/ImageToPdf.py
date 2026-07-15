import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

# ---------------- THEME & CONSTANTS ----------------
BG_MAIN = "#F8F9FA"       # Light gray background
BG_SIDEBAR = "#FFFFFF"    # White panel background
ACCENT_COLOR = "#4A90E2"  # Modern blue
SUCCESS_COLOR = "#2ECC71" # Modern green
TEXT_COLOR = "#2C3E50"    # Dark slate text
HIGHLIGHT_COLOR = "#D1E8FF"# Drop target highlight

THUMB_SIZE = 120
COLUMNS = 4

selected_images = []
drag_data = {
    "index": None,
    "ghost": None,
    "target": None
}

PAGE_SIZES = {
    "Original Size": None,
    "A5": (420, 595),
    "A4": (595, 842),
    "A3": (842, 1191),
    "Letter": (612, 792),
    "Legal": (612, 1008),
    "Square (800x800)": (800, 800)
}

# ---------------- LOGIC & EVENTS ----------------
def select_images():
    files = filedialog.askopenfilenames(
        filetypes=[("Images", "*.png *.jpg *.jpeg")]
    )
    if files:
        selected_images.extend(files)
        refresh_thumbnails()

def bind_drag(widget, index):
    widget.bind("<Button-1>", lambda e: start_drag(e, index))
    widget.bind("<B1-Motion>", on_drag)
    widget.bind("<ButtonRelease-1>", on_drop)

def refresh_thumbnails():
    for widget in canvas_frame.winfo_children():
        widget.destroy()

    for i, path in enumerate(selected_images):
        # Modern Card Design
        frame = tk.Frame(canvas_frame, bg="white", bd=0, highlightthickness=1, highlightbackground="#E0E0E0")
        frame.grid(row=i//COLUMNS, column=i % COLUMNS, padx=12, pady=12, sticky="nsew")

        try:
            img = Image.open(path)
            img.thumbnail((THUMB_SIZE, THUMB_SIZE))
            tk_img = ImageTk.PhotoImage(img)

            lbl = tk.Label(frame, image=tk_img, bg="white")
            lbl.image = tk_img
            lbl.pack(padx=5, pady=5)
        except Exception:
            lbl = tk.Label(frame, text="Error loading image", bg="white", fg="red")
            lbl.pack(padx=5, pady=5)

        # Truncate long names elegantly
        base_name = os.path.basename(path)
        display_name = base_name if len(base_name) <= 15 else base_name[:12] + "..."
        
        name = tk.Label(frame, text=display_name, bg="white", fg=TEXT_COLOR, font=("Segoe UI", 9))
        name.pack(padx=5, pady=(0, 5))

        # Re-bind elements for dragging
        bind_drag(frame, i)
        bind_drag(lbl, i)
        bind_drag(name, i)

def start_drag(event, index):
    drag_data["index"] = index

    # Modern translucent ghost window
    ghost = tk.Toplevel(root)
    ghost.overrideredirect(True)
    ghost.attributes("-alpha", 0.7)
    ghost.attributes("-topmost", True)

    try:
        img = Image.open(selected_images[index])
        img.thumbnail((100, 100))
        tk_img = ImageTk.PhotoImage(img)
        label = tk.Label(ghost, image=tk_img, bd=1, relief="solid", bg="white")
        label.image = tk_img
        label.pack()
    except Exception:
        pass

    drag_data["ghost"] = ghost

def on_drag(event):
    ghost = drag_data["ghost"]
    if not ghost:
        return

    x = root.winfo_pointerx()
    y = root.winfo_pointery()
    ghost.geometry(f"+{x+12}+{y+12}")

    widget = root.winfo_containing(x, y)
    
    drag_data["target"] = None
    for i, frame in enumerate(canvas_frame.winfo_children()):
        if frame == widget or frame == widget.master:
            highlight_target(i)
            drag_data["target"] = i
            break
    else:
        # Reset highlights if we aren't hovering over any card
        highlight_target(None)

def highlight_target(target_index):
    for i, frame in enumerate(canvas_frame.winfo_children()):
        if i == target_index:
            frame.config(bg=HIGHLIGHT_COLOR, highlightbackground=ACCENT_COLOR)
            for child in frame.winfo_children():
                child.config(bg=HIGHLIGHT_COLOR)
        else:
            frame.config(bg="white", highlightbackground="#E0E0E0")
            for child in frame.winfo_children():
                child.config(bg="white")

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

    refresh_thumbnails()

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

    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    bg = Image.new("RGB", (page_w, page_h), "white")
    bg.paste(img, ((page_w-new_w)//2, (page_h-new_h)//2))
    return bg

def convert_to_pdf():
    if not selected_images:
        messagebox.showerror("Error", "No images selected!")
        return

    save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
    if not save_path:
        return

    size = PAGE_SIZES[page_size.get()]
    imgs = []

    for p in selected_images:
        try:
            img = Image.open(p)
            if img.mode != "RGB":
                img = img.convert("RGB")
            img = resize_to_page(img, size)
            imgs.append(img)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process {os.path.basename(p)}:\n{e}")
            return

    if imgs:
        imgs[0].save(save_path, save_all=True, append_images=imgs[1:])
        messagebox.showinfo("Success", "PDF created successfully!")

# ---------------- UI LAYOUT ----------------
root = tk.Tk()
root.title("Image → PDF Converter")
root.geometry("950x600")
root.configure(bg=BG_MAIN)

# Ttk Styles Setup
style = ttk.Style()
style.theme_use("clam")
style.configure("TCombobox", fieldbackground="white", background="#E0E0E0")
style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), foreground="white", background=ACCENT_COLOR)
style.map("Action.TButton", background=[("active", "#357ABD")])
style.configure("Convert.TButton", font=("Segoe UI", 11, "bold"), foreground="white", background=SUCCESS_COLOR)
style.map("Convert.TButton", background=[("active", "#27AE60")])

# Main Window Split
left_panel = tk.Frame(root, bg=BG_MAIN)
left_panel.pack(side="left", fill="both", expand=True, padx=20, pady=20)

right_panel = tk.Frame(root, bg=BG_SIDEBAR, width=280, bd=0, highlightthickness=1, highlightbackground="#E0E0E0")
right_panel.pack(side="right", fill="y", padx=(0, 20), pady=20)
right_panel.pack_propagate(False)

# Custom Clean Canvas & Scrollbar Layout
canvas = tk.Canvas(left_panel, bg=BG_MAIN, bd=0, highlightthickness=0)
scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=canvas.yview)
canvas_frame = tk.Frame(canvas, bg=BG_MAIN)

canvas_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas.create_window((0, 0), window=canvas_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Right Control Panel Configuration
title_lbl = tk.Label(right_panel, text="Options", bg=BG_SIDEBAR, fg=TEXT_COLOR, font=("Segoe UI", 14, "bold"))
title_lbl.pack(pady=(20, 15), padx=20, anchor="w")

btn_select = ttk.Button(right_panel, text="➕ Add Images", style="Action.TButton", command=select_images)
btn_select.pack(fill="x", padx=20, pady=10)

separator = ttk.Separator(right_panel, orient="horizontal")
separator.pack(fill="x", padx=20, pady=15)

lbl_size = tk.Label(right_panel, text="Output Page Size", bg=BG_SIDEBAR, fg=TEXT_COLOR, font=("Segoe UI", 10))
lbl_size.pack(padx=20, anchor="w", pady=(0, 5))

page_size = tk.StringVar(value="Original Size")
combo_size = ttk.Combobox(right_panel, textvariable=page_size, values=list(PAGE_SIZES.keys()), state="readonly")
combo_size.pack(fill="x", padx=20, pady=(0, 20))

# Flexible spacer to push the convert button to the bottom
spacer = tk.Frame(right_panel, bg=BG_SIDEBAR)
spacer.pack(fill="both", expand=True)

btn_convert = ttk.Button(right_panel, text="Export to PDF", style="Convert.TButton", command=convert_to_pdf)
btn_convert.pack(fill="x", padx=20, pady=20)

root.mainloop()