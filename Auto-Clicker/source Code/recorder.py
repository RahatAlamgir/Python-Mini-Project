from pynput import mouse, keyboard as pynput_key
import time


# ---------- STATE ----------
recording = False
recorded_commands = []

last_event_time = 0
is_mouse_dragging = False
last_click_time = 0
drag_start = None

# UI callbacks (set from ui.py)
log = None
insert_to_editor = None
update_status = None
save_script = None

# ------- hotkey --------

pressed_keys = set()

modifier_map = {
    "ctrl_l": "ctrl", 
    "ctrl_r": "ctrl",

    "shift_l": "shift", 
    "shift_r": "shift",

    "alt_l": "alt", 
    "alt_r": "alt",
    "alt_gr": "alt",

    "cmd": "win"
    
}

active_modifiers = set()
recent_hotkey_keys = set()
modifier_pressed_time = {}
modifier_used_in_combo = {}

# ---------- SET UI CALLBACKS ----------

def set_ui_callbacks(log_func, insert_func, status_func, save_func):
    global log, insert_to_editor, update_status, save_script
    log = log_func
    insert_to_editor = insert_func
    update_status = status_func
    save_script = save_func
# ---------- RECORD HELPER ----------
def add_recorded_cmd(cmd):
    global last_event_time, recorded_commands

    now = time.time()

    if last_event_time != 0:
        delay = int((now - last_event_time) * 1000)
        if delay > 20:
            recorded_commands.append(f"wait {delay}")

    # Cleaner spacing
    if cmd.startswith("press"):
        if not recorded_commands or recorded_commands[-1] != "":
            recorded_commands.append("")

    recorded_commands.append(cmd)

    if cmd.startswith("end"):
        if not recorded_commands or recorded_commands[-1] != "":
            recorded_commands.append("")

    last_event_time = now



def normalize_key(k):
    if not k:
        return None

    # Convert control characters (Ctrl+C etc.)
    if len(k) == 1 and ord(k) < 32:
        return chr(ord(k) + 96)

    k = k.lower()

    # Normalize modifiers
    if k in modifier_map:
        return modifier_map[k]

    return k
# ---------- KEYBOARD ----------


def on_rec_press(key):
    global recording, pressed_keys, active_modifiers
    global modifier_pressed_time, modifier_used_in_combo

    if not recording:
        return

    try:
        k = key.char
    except AttributeError:
        k = str(key).replace("Key.", "")

    k = normalize_key(k)

    if not k or k in ['f6', 'f7']:
        return

    # Prevent spam
    if k in pressed_keys:
        return

    pressed_keys.add(k)

    # -------- MODIFIER PRESSED --------
    if k in ["ctrl", "shift", "alt","win"]:
        active_modifiers.add(k)
        modifier_pressed_time[k] = time.time()
        #modifier_used_in_combo[k] = False
        return

    # -------- COMBO DETECT --------
    if active_modifiers:
        mods = list(active_modifiers)
        combo_keys = mods + [k]

        add_recorded_cmd(f"hotkey {' '.join(combo_keys)}")

        # Mark only THESE keys as part of hotkey
        recent_hotkey_keys.update(combo_keys)

        for m in mods:
            modifier_used_in_combo[m] = True

        return

    # -------- NORMAL KEY --------
    add_recorded_cmd(f"press {k}")

def on_rec_release(key):
    global recording, pressed_keys, active_modifiers
    global modifier_pressed_time, modifier_used_in_combo

    if not recording:
        return

    try:
        k = key.char
    except AttributeError:
        k = str(key).replace("Key.", "")

    k = normalize_key(k)

    if not k or k in ['f6', 'f7']:
        return

    if k in pressed_keys:
        pressed_keys.remove(k)

    # -------- MODIFIER RELEASE --------
    if k in ["ctrl", "shift", "alt","win"]:
        if k in active_modifiers:
            active_modifiers.remove(k)

        # If NOT used in combo → treat as real press
        if not modifier_used_in_combo.get(k, False):
            duration = int((time.time() - modifier_pressed_time.get(k, time.time())) * 1000)

            add_recorded_cmd(f"press {k}")
            if duration > 20:
                add_recorded_cmd(f"wait {duration}")
            add_recorded_cmd(f"end {k}")

        return

    # -------- SKIP ONLY HOTKEY KEYS --------
    if k in recent_hotkey_keys:
        recent_hotkey_keys.discard(k)
        return

    add_recorded_cmd(f"end {k}")


drag_start = None

def on_rec_click(x, y, button, pressed):
    global is_mouse_dragging, recording, drag_start,last_click_time

    if not recording:
        return

    btn = str(button).replace("Button.", "")


    if pressed:
        is_mouse_dragging = True   # START DRAG
        now = time.time()

        if now - last_click_time < 0.3:
            add_recorded_cmd(f"move {int(x)} {int(y)}")
            add_recorded_cmd(f"dclick {btn}")
            last_click_time = 0
        else:
            drag_start = (int(x), int(y))
            add_recorded_cmd(f"move {int(x)} {int(y)}")
            add_recorded_cmd(f"press mouse {btn}")
            last_click_time = now

    else:
        is_mouse_dragging = False

        x2, y2 = int(x), int(y)

        if drag_start:
            x1, y1 = drag_start

            # Detect real drag
            if abs(x1 - x2) > 5 or abs(y1 - y2) > 5:
                add_recorded_cmd(f"drag {x1} {y1} {x2} {y2} 0.2")

        if last_click_time != 0:
            add_recorded_cmd(f"end mouse {btn}")
        drag_start = None


def on_rec_scroll(x, y, dx, dy):
    if not recording:
        return

    add_recorded_cmd(f"scroll {int(dy * 120)}")


# ---------- TOGGLE RECORD ----------
def toggle_record():
    global recording, recorded_commands, last_event_time

    if recording:
        # STOP RECORDING
        recording = False
        if update_status:
            update_status()

        if log:
            log("✅ RECORDING FINISHED")

        if insert_to_editor:
            insert_to_editor(
                f"\n// --- Recorded at {time.strftime('%H:%M:%S')} ---\n"
            )
            insert_to_editor("\n".join(recorded_commands) + "\n")

        if save_script:
            save_script()
    else:
        # START RECORDING
        recorded_commands = []
        last_event_time = time.time()
        recording = True

        if update_status:
            update_status()

        if log:
            log("🔴 RECORDING STARTED (F7 to stop)", "warning")


# ---------- START LISTENERS ----------
def start_listeners():
    m_listener = mouse.Listener(
        on_click=on_rec_click,
        # on_move=on_rec_move,
        on_scroll=on_rec_scroll
    )

    k_listener = pynput_key.Listener(
        on_press=on_rec_press,
        on_release=on_rec_release
    )

    m_listener.start()
    k_listener.start()