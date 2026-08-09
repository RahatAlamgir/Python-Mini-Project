# 🖱️ Auto Clicker Pro

A powerful and flexible desktop automation tool built with Python.
Record, edit, and replay mouse & keyboard actions with precision.

---

## 🚀 Features

* 🎥 **Live Recording**

  * Capture mouse clicks, movements, scrolling, and keyboard input
* 🧠 **Smart Playback Engine**

  * Accurate timing with `wait` and `random_wait`
* 🖱️ **Advanced Mouse Support**

  * Click, double-click, drag, scroll, move
* ⌨️ **Keyboard Automation**

  * Press, hold, release, and tap keys
* 🔁 **Loop Execution**

  * Run scripts once, multiple times, or infinitely
* 📁 **Script Management**

  * Create, save, load, and delete scripts easily
* 🛡️ **Safety System**

  * Prevents stuck keys or mouse buttons
* 🎯 **Hotkey Control**

  * `F6` → Start/Stop Script
  * `F7` → Start/Stop Recording
* 🧾 **Built-in Script Editor**
* 🎨 **Dynamic Taskbar Icons** (Idle / Running / Recording)

---

## 📦 Installation


### 1. Install dependencies

```bash
pip install pyautogui keyboard pynput
```

### 2. Run the app

```bash
python main.py
```

---

## 🎮 Usage

### ▶️ Running a Script

1. Select a script from dropdown
2. Press **F6** or click run
3. Press **F6 again** to stop

---

### 🔴 Recording a Script

1. Press **F7** to start recording
2. Perform actions (mouse + keyboard)
3. Press **F7** again to stop
4. Script will appear in the editor

---

## 📜 Script Commands

### 🔁 Flow Control

```
loop [n]            # Repeat n times (-1 = infinite)
wait [ms]           # Delay in milliseconds
random_wait [a] [b] # Random delay between a and b ms
```

---

### ⌨️ Keyboard

```
tap [key]     # Press and release
press [key]   # Hold key down
end [key]     # Release key
```

---

### 🖱️ Mouse

```
click [left/right/middle]        # Single click
dclick [left/right/middle]       # Double click
move [x] [y]                     # Move cursor
scroll [amount]                  # Scroll wheel

press mouse [button]             # Hold mouse button
end mouse [button]               # Release mouse button
```

---

## 🧪 Example Script

```
loop 5
move 500 300
click left
wait 200
dclick left
wait 1000
```

---

## 📁 Project Structure

```
auto-clicker-pro/
│
├── main.py
├── configs/          # Saved scripts
├── ico/              # App icons (idle, busy, rec)
└── README.md
```

---

## ⚠️ Notes

* Works best on **Windows**
* Do not run scripts that interfere with system-critical tasks
* Recording and playback timing may vary slightly depending on system performance

---

## 👨‍💻 Author

**Md Rahat Alamgir**

🔗 GitHub: https://github.com/RahatAlamgir

🔗 Linkdin: https://www.linkedin.com/in/rahat-alamgir

---

## ⭐ Support

If you like this project:

* ⭐ Star the repo
* 🐛 Report bugs
* 💡 Suggest features

---

## 🛠️ Future Improvements

* GUI-based script builder
* Image recognition automation
* Macro sharing system
* Better timing optimization

---

## 📜 License

This project is open-source.

