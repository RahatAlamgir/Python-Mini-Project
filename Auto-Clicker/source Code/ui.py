import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import time
import re
import ctypes

import keyboard
import pyautogui

import guide
import aboutDev
import engine
import recorder
from pynput import mouse

import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# ---------- TASKBAR ----------
def set_app_id():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            'rahat.autoclicker.pro.v3'
        )
    except:
        pass


def change_taskbar_icon(icon_name):
    try:
        if os.path.exists(icon_name):
            root.iconbitmap(icon_name)
    except:
        pass


# ---------- GLOBAL ----------
root = None
editor = None
log_box = None
status_label = None
config_var = None
config_dropdown = None
delete_btn = None
line_numbers = None



# ---------- LOG ----------
def log(msg, tag="info"):
    timestamp = time.strftime("[%H:%M:%S]")
    log_box.insert(tk.END, f"{timestamp} {msg}\n", tag)
    log_box.see(tk.END)


def safe_log(msg, tag="info"):
    root.after(0, lambda: log(msg, tag))



def update_ui_status():
    if recorder.recording:
        status_label.config(text="● RECORDING", fg="#f39c12")
        
        change_taskbar_icon(resource_path("ico/rec.ico"))
        toggle_overlay(True) 
    elif engine.running:
        status_label.config(text="● RUNNING", fg="#00ff88")
        
        change_taskbar_icon(resource_path("ico/busy.ico"))
        toggle_overlay(True)  
    else:
        status_label.config(text="○ STOPPED", fg="#ff5555")
        
        change_taskbar_icon(resource_path("ico/idle.ico"))
        toggle_overlay(False) # Hide overlay when stopped

# -------------- overlay -----------------------

overlay_window = None
animation_running = False
alpha_value = 0.7
alpha_direction = 1 # 1 for fading in, -1 for fading out

def animate_pulse():
    global alpha_value, alpha_direction, animation_running
    if not animation_running or not overlay_window:
        return

    # Adjust alpha
    alpha_value += (0.02 * alpha_direction)
    
    if alpha_value >= 0.9:
        alpha_value = 0.9
        alpha_direction = -1
    elif alpha_value <= 0.4:
        alpha_value = 0.4
        alpha_direction = 1

    try:
        overlay_window.attributes("-alpha", alpha_value)
        # Repeat every 50ms for smooth 20fps animation
        root.after(50, animate_pulse)
    except:
        animation_running = False

def toggle_overlay(show):
    global overlay_window, animation_running
    if show and overlay_var.get():
        if not overlay_window:
            overlay_window = tk.Toplevel(root)
            overlay_window.overrideredirect(True)
            overlay_window.attributes("-topmost", True)
            overlay_window.attributes("-alpha", 0.7) # Initial transparency
            overlay_window.configure(bg="#00ff88")
            
            # Position
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            overlay_window.geometry(f"120x30+{sw-140}+{sh-70}")
            if engine.running:
                tk.Label(
                    overlay_window, text="Running", 
                    fg="black", bg="#00ff88", 
                    font=("Segoe UI", 9, "bold")
                ).pack(expand=True, fill="both")
            elif recorder.recording:
                tk.Label(
                    overlay_window, text="Recording", 
                    fg="black", bg="#f39c12", 
                    font=("Segoe UI", 9, "bold")
                ).pack(expand=True, fill="both")
            
            # Start animation
            animation_running = True
            animate_pulse()
    else:
        animation_running = False
        if overlay_window:
            overlay_window.destroy()
            overlay_window = None

# --------- picker ---------------

def create_picker_overlay():
    overlay = tk.Toplevel()
    overlay.attributes("-fullscreen", True)
    overlay.attributes("-topmost", True)
    overlay.attributes("-alpha", 0.01)  # almost invisible
    overlay.config(cursor="crosshair")  # 👈 cursor change

    # Block all interactions
    overlay.bind("<Button-1>", lambda e: None)

    return overlay

def pick_color(log):
    def worker():
        # 1. Hide the main UI
        root.after(0, root.withdraw)
        
        # 2. Create overlay on the main thread and store reference
        overlay_ref = []
            
        root.after(0, overlay_ref.append(create_picker_overlay()))
        time.sleep(0.5)

        def on_click(x, y, button, pressed):
            if pressed:
                try:
                    r, g, b = pyautogui.pixel(x, y)
                    hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)
                    
                    # Insert result safely
                    editor.after(0, lambda: insert_picker(hex_color + " "))

                    if log:
                        log(f"Picked color at ({x},{y}) {hex_color}", "info")

                except Exception as e:
                    if log:
                        log(f"Color pick error: {e}", "error")

                # 3. Restore UI safely
                def restore():
                    if overlay_ref:
                        overlay_ref[0].destroy()
                    root.deiconify()
                    root.focus_force()

                root.after(0, restore)
                return False # Stop the listener

        with mouse.Listener(on_click=on_click) as listener:
            listener.join()

    threading.Thread(target=worker, daemon=True).start()

def pick_position(log):
    def worker():

        root.after(0, root.withdraw)

        overlay_container = []

        root.after(0, overlay_container.append(create_picker_overlay()))

        time.sleep(0.5)

        def on_click(x, y, button, pressed):
            if pressed:
                try:
                    cmd = f"{x} {y} "
                    editor.after(0, lambda: insert_picker(cmd))

                    if log:
                        log(f"Picked position ({x},{y})", "info")

                except Exception as e:
                    if log:
                        log(f"Position pick error: {e}", "error")

                def restore():
                    if overlay_container:
                        overlay_container[0].destroy()
                    root.deiconify()
                    root.focus_force() 

                root.after(0, restore)
                return False  

        with mouse.Listener(on_click=on_click) as listener:
            listener.join()

    threading.Thread(target=worker, daemon=True).start()


# ---------- RUN ----------
def stop_ui_state():
    engine.running = False
    update_ui_status()
    engine.release_all_safe(safe_log)
    log("Session Finished.")


def toggle_run():
    if recorder.recording:
        log("Error: Can't run while recording !", "error")
        return

    if not engine.running:
        name = config_var.get()
        
        # Ensure we append the extension so os.path.exists works
        filename = f"{name}.acp" if not name.endswith(".acp") else name
        path = os.path.join("configs", filename)

        if not name or not os.path.exists(path):
            log(f"Error: Script '{name}' not found on disk!", "error")
            return

        engine.running = True
        update_ui_status() # This will now trigger animated overlay

        threading.Thread(target=worker, args=(path,), daemon=True).start()
    else:
        engine.running = False
        update_ui_status() 


def worker(path):
    with open(path) as f:
        cmds = [
            l.strip()
            for l in f
            if l.strip() and not l.strip().startswith("#")
        ]

    safe_log(f"Started: {os.path.basename(path)}")

    engine.run_script(
        cmds,
        safe_log,
        lambda: root.after(0, stop_ui_state)
    )


# ---------- FILE ----------
def load_configs():
    if not os.path.exists("configs"):
        os.makedirs("configs")
    
    return [f[:-4] for f in os.listdir("configs") if f.endswith(".acp")]


def save_config():
    name = config_var.get().strip()
    if not name:
        log("Error: Name cannot be empty!", "error")
        return

    filename = name if name.endswith(".acp") else f"{name}.acp"
    path = os.path.join("configs", filename)

    with open(path, "w") as f:
        f.write(editor.get("1.0", tk.END).strip())

    log(f"Saved: {filename}")
    
    config_dropdown['values'] = load_configs()


def create_new():

    base_name = "Untitled"
    extension = ".acp"
    counter = 0
    
    suggestion = base_name
    while os.path.exists(os.path.join("configs", f"{suggestion}{extension}")):
        counter += 1
        suggestion = f"{base_name}{counter}"

    # 3. Update UI
    editor.delete("1.0", tk.END)
    config_var.set(suggestion) 
    
    update_line_numbers()
    highlight_current_line()
    
    delete_btn.pack_forget()
    
    editor.focus_set()
    log(f"Ready: {suggestion}")


def delete_config():
    name = config_var.get()
    
    path = os.path.join("configs", f"{name}.acp")

    if os.path.exists(path):
        if messagebox.askyesno("Delete", f"Delete {name}?"):
            os.remove(path)
            editor.delete("1.0", tk.END)
            config_var.set("")
            log(f"Deleted {name}", "error")
            config_dropdown['values'] = load_configs()



def load_selected():
    name = config_var.get()
    if not name:
        return

    path = os.path.join("configs", f"{name}.acp")

    if os.path.exists(path):
        with open(path, "r") as f:
            editor.delete("1.0", tk.END)
            editor.insert(tk.END, f.read())

        highlight_syntax()
        update_line_numbers()
        log(f"Loaded {name}", "warning")


def on_dropdown_change(*args):
    name = config_var.get()

    if name in load_configs():
        delete_btn.pack(fill="x", padx=20, pady=5, after=save_btn)

        load_selected()

    else:
        delete_btn.pack_forget()


# ---------- SYNTAX ----------
KEYWORDS = [
    "wait", "random", "loop", "jump","print" , "stop",
    "tap", "press", "end",
    "click", "dclick", "move", "scroll",
    "mouse", "text", "drag" ,"hotkey" ,
    "color" ,"center" , "find" , "tolerance" , "area"
]

MODIFIERS = ["ctrl", "shift", "alt", "win"]

def highlight_syntax(event=None):
    editor.after(1, _highlight)


def _highlight():
    content = editor.get("1.0", tk.END)

    for tag in ["keyword", "number", "comment", "modifier"]:
        editor.tag_remove(tag, "1.0", tk.END)

    # ---------- COMMENTS ----------
    for match in re.finditer(r"//.*?//", content):
        start = f"1.0 + {match.start()} chars"
        end = f"1.0 + {match.end()} chars"
        editor.tag_add("comment", start, end)

    # ---------- NUMBERS ----------
    for match in re.finditer(r"\b\d+(\.\d+)?(ms|s|m)?\b", content.lower()):
        start = f"1.0 + {match.start()} chars"
        end = f"1.0 + {match.end()} chars"
        editor.tag_add("number", start, end)

    # ---------- KEYWORDS ----------
    for kw in KEYWORDS:
        for match in re.finditer(rf"\b{kw}\b", content.lower()):
            start_index = f"1.0 + {match.start()} chars"
            if "comment" in editor.tag_names(start_index):
                continue
            end_index = f"1.0 + {match.end()} chars"
            editor.tag_add("keyword", start_index, end_index)

    # ---------- MODIFIERS (NEW) ----------
    for mod in MODIFIERS:
        for match in re.finditer(rf"\b{mod}\b", content.lower()):
            start_index = f"1.0 + {match.start()} chars"

            # skip if inside comment
            if "comment" in editor.tag_names(start_index):
                continue

            end_index = f"1.0 + {match.end()} chars"
            editor.tag_add("modifier", start_index, end_index)

# ---------- LINE NUMBERS ----------
def update_line_numbers(event=None):
    line_numbers.config(state="normal")
    line_numbers.delete("1.0", tk.END)

    i = editor.index("@0,0")
    while True:
        dline = editor.dlineinfo(i)
        if dline is None:
            break
        linenum = str(i).split(".")[0]
        line_numbers.insert(tk.END, linenum + "\n")
        i = editor.index(f"{i}+1line")

    line_numbers.config(state="disabled")


def on_scroll(*args):
    editor.yview(*args)
    line_numbers.yview_moveto(editor.yview()[0])


def on_editor_change(event=None):
        highlight_syntax()
        update_line_numbers()

def combined_key_release(event):
    highlight_syntax()
    update_line_numbers()
    highlight_current_line()

def highlight_current_line(event=None):
    editor.tag_remove("current_line", "1.0", "end")
    editor.tag_add("current_line", "insert linestart", "insert lineend+1c")

def rec_insert_and_refresh(text):
    editor.insert(tk.END, text)
    highlight_syntax()
    update_line_numbers()
    highlight_current_line()

def insert_picker(text):
    editor.insert(tk.INSERT, text)
    update_line_numbers()
    highlight_syntax()
    highlight_current_line()
# ---------- START APP ----------
def start_app():
    global root, editor, log_box, status_label
    global config_var, config_dropdown, delete_btn, save_btn, line_numbers
    global overlay_var, overlay_window


    set_app_id()
    pyautogui.FAILSAFE = True

    root = tk.Tk()
    root.title("Auto Clicker Pro")
    root.geometry("1000x650")
    root.configure(bg="#0f0f0f")

    change_taskbar_icon("ico/idle.ico")

    overlay_var = tk.BooleanVar(value=True)

    # Sidebar
    sidebar = tk.Frame(root, bg="#1a1a1a", width=250)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    status_label = tk.Label(sidebar, text="○ STOPPED", fg="#ff5555", bg="#1a1a1a", font=("Segoe UI", 18, "bold"))
    status_label.pack(pady=30)

    config_var = tk.StringVar()
    config_var.trace_add("write", on_dropdown_change)

    config_dropdown = ttk.Combobox(sidebar, textvariable=config_var,values=load_configs())
    config_dropdown.pack(pady=5, padx=20, fill="x")

    btn_style = {"relief": "flat", "font": ("Segoe UI", 9, "bold"), "cursor": "hand2"}


    tk.Button(sidebar, text="➕ New Script", bg="#3498db", fg="white", command=create_new, **btn_style).pack(fill="x", padx=20, pady=2)
    save_btn = tk.Button(sidebar, text="💾 Save / Update", bg="#2ecc71", fg="black", command=save_config, **btn_style)
    save_btn.pack(fill="x", padx=20, pady=2)
    delete_btn = tk.Button(sidebar, text="🗑️ Delete Script", bg="#e74c3c", fg="white", command=delete_config, **btn_style)
    
    #  ---------------- picker -----------------------
    tk.Frame(sidebar,bg="#1a1a1a", pady=15).pack(fill="x", padx=0, pady=30)
    tk.Button(sidebar, text="🎯 Pick Color",  bg="#D6CB30", fg="black",command=lambda: pick_color( log), **btn_style).pack(fill="x", padx=20, pady=2)
    tk.Button(sidebar,text="📍 Pick Position",bg="#6EC1E4", fg="black",command=lambda: pick_position(log), **btn_style).pack(fill="x", padx=20, pady=2)

    tk.Checkbutton(sidebar, text="Show Overlay", variable=overlay_var, bg="#1a1a1a", fg="white", selectcolor="#1a1a1a", activebackground="#1a1a1a", font=("Segoe UI", 9)).pack(pady=5)
    
    user_info = tk.Frame(sidebar, bg="#1a1a1a", pady=15); user_info.pack(side="bottom", fill="x", padx=0, pady=15)

    tk.Button(user_info, text="❓ How to Script", bg="#D6CB30", fg="black", command=lambda: guide.show_guide(root), **btn_style).pack(fill="x", padx=20, pady=(20, 2))
    tk.Button(user_info, text="👤 About Developer", bg="#9b59b6", fg="white", command=lambda: aboutDev.show_about(root), **btn_style).pack(fill="x", padx=20, pady=2)
    
    info_box = tk.Frame(sidebar, bg="#111", pady=15); info_box.pack(side="bottom", fill="x", padx=15, pady=20)

    tk.Label(info_box, text="F6: RUN / STOP", fg="#00ff88", bg="#111", font=("Segoe UI", 10, "bold")).pack()
    tk.Label(info_box, text="F7: REC / STOP", fg="#f39c12", bg="#111", font=("Segoe UI", 10, "bold")).pack()

    # Main
    main = tk.Frame(root, bg="#0f0f0f")
    main.pack(side="right", fill="both", expand=True, padx=20, pady=20)

    editor_frame = tk.Frame(main, bg="#0f0f0f")
    editor_frame.pack(fill="both", expand=True)

    scrollbar = tk.Scrollbar(editor_frame)
    scrollbar.pack(side="right", fill="y")

    line_numbers = tk.Text( editor_frame, width=4,bg="#111", fg="#888", font=("Consolas", 12),relief="flat", state="disabled",padx=5, pady=15)
    line_numbers.pack(side="left", fill="y")

    def on_editor_scroll(*args):
        scrollbar.set(*args)
        line_numbers.yview_moveto(args[0])

    editor = tk.Text(editor_frame, bg="#1e1e1e", fg="#d4d4d4", insertbackground="white", font=("Consolas", 12), relief="flat", padx=15, pady=15,yscrollcommand=on_editor_scroll)
    editor.pack(side="left", fill="both", expand=True)

    scrollbar.config(command=on_scroll)

    # Log box
    log_box = tk.Text( main, height=8,bg="#000", fg="white", font=("Consolas", 10), relief="flat", padx=15, pady=15)
    log_box.pack(fill="x", pady=(20, 0))

    log_box.tag_configure("info", foreground="#00ff88")
    log_box.tag_configure("error", foreground="#ff5555")
    log_box.tag_configure("warning", foreground="#f39c12")
    log_box.tag_configure("neutral", foreground="#cccccc")

    # Syntax colors
    editor.tag_configure("keyword", foreground="#4FC3F7")
    editor.tag_configure("number", foreground="#FFD54F")
    editor.tag_configure("comment", foreground="#6A9955")
    editor.tag_configure("modifier", foreground="#FF8A8A")

    editor.tag_configure("current_line", background="#2a2a2a")

    # Bindings
    editor.bind("<KeyRelease>", combined_key_release)
    editor.bind("<MouseWheel>", lambda e: root.after(1, update_line_numbers))
    
    
    editor.bind("<<Paste>>", on_editor_change)
    editor.bind("<Configure>", update_line_numbers)
    editor.bind("<Button-1>", lambda e: editor.after(1, highlight_current_line))

    keyboard.add_hotkey('f6', toggle_run)
    keyboard.add_hotkey('f7', recorder.toggle_record)

    recorder.set_ui_callbacks(safe_log, rec_insert_and_refresh, update_ui_status ,save_config)
    recorder.start_listeners()

    update_line_numbers()
    highlight_syntax()
    highlight_current_line()

    log("Auto Clicker Pro Ready.")
    root.mainloop()