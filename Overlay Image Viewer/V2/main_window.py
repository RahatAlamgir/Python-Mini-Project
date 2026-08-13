import os
import json
from ctypes import wintypes

from PySide6.QtCore import Qt, QPoint, QEvent, QTimer
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QAction,
    QGuiApplication, QKeySequence, QShortcut, QActionGroup
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QMenu, QFileDialog, QSizeGrip,
    QDialog, QMessageBox, QWidgetAction, QInputDialog
)

from config import CONFIG_FILE
from win_api import (
    IS_WINDOWS, user32, HOTKEY_ID, GWL_EXSTYLE, WS_EX_TRANSPARENT,
    WS_EX_LAYERED, WM_HOTKEY, MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN,
    GetWindowLong, SetWindowLong
)
from widgets import ImageDisplayWidget, ScreenSnipper
from dialogs import HotkeyConfigDialog
from image_manager import ImageManager, ImageManagerDialog
from image_manager import ImageManager


class OverlayImageViewer(QWidget):
    def __init__(self):
        super().__init__()

        self.image_manager = ImageManager(self)
        self.image_manager.image_changed.connect(self.on_image_changed)

        self.always_on_top = True
        self.transparency_enabled = False
        self.max_quality_mode = True
        self.snap_enabled = True
        self.max_height_preset = 0.0

        self.drag_position = QPoint()
        self.snap_margin = 25
        self.snipper = None

        # Hotkey and Ghost Mode
        self.hotkey_sequence = "Ctrl+Shift+H"
        self.hotkey_shortcut = None
        self.hotkey_active = False

        # Preserved State Storage
        self.saved_always_on_top = True
        self.saved_auto_hide_enabled = True

        # Auto-hide toggles
        self.auto_hide_enabled = True
        self.controls_visible = True

        # Auto-hide timer
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_controls)

        self.init_ui()
        self.load_config()
        self.setup_hotkey()
        self.setAcceptDrops(True)

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(180, 120)
        self.resize(500, 400)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QWidget(self)
        self.container.setObjectName("Container")

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(4, 4, 4, 4)
        container_layout.setSpacing(2)

        # Top Control Bar
        self.control_bar_container = QWidget(self.container)
        self.control_bar = QHBoxLayout(self.control_bar_container)
        self.control_bar.setContentsMargins(2, 0, 2, 0)

        self.title_label = QLabel("Overlay Viewer", self)
        self.unified_menu = QMenu(self)

        self.close_btn = QPushButton("✕", self)
        self.close_btn.setFixedHeight(20)
        self.close_btn.clicked.connect(self.close)

        self.control_bar.addWidget(self.title_label)
        self.control_bar.addStretch()
        self.control_bar.addWidget(self.close_btn)

        container_layout.addWidget(self.control_bar_container)

        # Image Display Label
        self.image_label = ImageDisplayWidget("Drag & Drop Image Here\nor double-click to fit ratio", self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.image_label.customContextMenuRequested.connect(self.show_context_menu)

        container_layout.addWidget(self.image_label, stretch=1)

        # Bottom Bar Wrapper
        self.bottom_bar_container = QWidget(self.container)
        bottom_bar = QHBoxLayout(self.bottom_bar_container)
        bottom_bar.setContentsMargins(0, 0, 0, 0)
        bottom_bar.addStretch()

        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(12, 12)
        bottom_bar.addWidget(self.size_grip)

        container_layout.addWidget(self.bottom_bar_container)
        self.main_layout.addWidget(self.container)

        # Opacity Slider
        self.opacity_slider = QSlider(Qt.Vertical)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setValue(90)
        self.opacity_slider.setFixedHeight(110)
        self.opacity_slider.valueChanged.connect(self.update_opacity)

        # Navigation Shortcuts
        self.shortcut_left = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.shortcut_left.activated.connect(self.prev_image)

        self.shortcut_right = QShortcut(QKeySequence(Qt.Key_Right), self)
        self.shortcut_right.activated.connect(self.next_image)

        self.shortcut_paste = QShortcut(QKeySequence.Paste, self)
        self.shortcut_paste.activated.connect(lambda: self.image_manager.paste_from_clipboard(self))

        self.apply_container_style()

        QApplication.instance().installEventFilter(self)
        self.setMouseTracking(True)
        self.show_controls_temporarily()

    # --- Windows Native Global Hotkey Registration ---
    def setup_hotkey(self):
        if IS_WINDOWS and self.winId():
            hwnd = int(self.winId())
            user32.UnregisterHotKey(hwnd, HOTKEY_ID)

            modifiers = 0
            seq_str = self.hotkey_sequence.upper()

            if "CTRL" in seq_str:
                modifiers |= MOD_CONTROL
            if "SHIFT" in seq_str:
                modifiers |= MOD_SHIFT
            if "ALT" in seq_str:
                modifiers |= MOD_ALT
            if "META" in seq_str or "WIN" in seq_str:
                modifiers |= MOD_WIN

            key_str = seq_str.split("+")[-1].strip()
            vk_code = ord(key_str[0]) if len(key_str) == 1 and key_str.isalnum() else 0x48

            user32.RegisterHotKey(hwnd, HOTKEY_ID, modifiers, vk_code)
        else:
            if self.hotkey_shortcut:
                self.hotkey_shortcut.setEnabled(False)
                self.hotkey_shortcut.deleteLater()
            self.hotkey_shortcut = QShortcut(QKeySequence(self.hotkey_sequence), self)
            self.hotkey_shortcut.setContext(Qt.ApplicationShortcut)
            self.hotkey_shortcut.activated.connect(self.toggle_hotkey_active_mode)

    def nativeEvent(self, eventType, message):
        if IS_WINDOWS and eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                self.toggle_hotkey_active_mode()
                return True, 0
        return super().nativeEvent(eventType, message)

    def set_win32_click_through(self, transparent: bool):
        """Applies/removes OS-level click-through extended window style."""
        if IS_WINDOWS and self.winId():
            hwnd = int(self.winId())
            current_style = GetWindowLong(hwnd, GWL_EXSTYLE)
            if transparent:
                new_style = current_style | WS_EX_TRANSPARENT | WS_EX_LAYERED
            else:
                new_style = current_style & ~WS_EX_TRANSPARENT
            SetWindowLong(hwnd, GWL_EXSTYLE, new_style)

    def prompt_change_hotkey(self):
        dialog = HotkeyConfigDialog(self.hotkey_sequence, self)
        if dialog.exec() == QDialog.Accepted:
            new_seq = dialog.get_sequence_str()
            if new_seq:
                self.hotkey_sequence = new_seq
                self.setup_hotkey()
                self.rebuild_unified_menu()

    def toggle_hotkey_active_mode(self):
        self.hotkey_active = not self.hotkey_active

        if self.hotkey_active:
            self.saved_always_on_top = self.always_on_top
            self.saved_auto_hide_enabled = self.auto_hide_enabled

            self.set_win32_click_through(True)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.shortcut_left.setEnabled(False)
            self.shortcut_right.setEnabled(False)
            self.shortcut_paste.setEnabled(False)

            self.setWindowFlag(Qt.WindowStaysOnTopHint, True)

            self.auto_hide_enabled = False
            self.hide_timer.stop()
            self.controls_visible = False
            self.control_bar_container.hide()
            self.bottom_bar_container.hide()
            self.apply_container_style()
            self.show()
        else:
            self.set_win32_click_through(False)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.shortcut_left.setEnabled(True)
            self.shortcut_right.setEnabled(True)
            self.shortcut_paste.setEnabled(True)

            self.toggle_always_on_top(self.saved_always_on_top)
            self.toggle_auto_hide_mode(self.saved_auto_hide_enabled)
            self.show_controls_temporarily()
            self.show()

    # --- Mouse & UI Handling ---
    def eventFilter(self, source, event):
        if self.hotkey_active:
            return super().eventFilter(source, event)

        if self.auto_hide_enabled:
            if event.type() in (QEvent.MouseMove, QEvent.HoverMove, QEvent.MouseButtonPress, QEvent.Enter):
                if self.underMouse() or self.rect().contains(self.mapFromGlobal(QGuiApplication.overrideCursor() or self.cursor().pos())):
                    self.show_controls_temporarily()

        if source == self.image_label and event.type() == QEvent.MouseButtonDblClick:
            if event.button() == Qt.LeftButton:
                self.fit_to_image_ratio()
                return True

        return super().eventFilter(source, event)

    def show_controls_temporarily(self):
        if self.hotkey_active:
            return

        if not self.controls_visible:
            self.controls_visible = True
            self.control_bar_container.show()
            self.bottom_bar_container.show()
            self.apply_container_style()

        if self.auto_hide_enabled:
            self.hide_timer.start(3000)

    def hide_controls(self):
        if not self.auto_hide_enabled and not self.hotkey_active:
            return

        self.controls_visible = False
        self.control_bar_container.hide()
        self.bottom_bar_container.hide()
        self.apply_container_style()

    def toggle_auto_hide_mode(self, checked=None):
        if checked is not None:
            self.auto_hide_enabled = checked
        else:
            self.auto_hide_enabled = not self.auto_hide_enabled

        if self.auto_hide_enabled:
            self.show_controls_temporarily()
        else:
            self.hide_timer.stop()
            self.controls_visible = True
            self.control_bar_container.show()
            self.bottom_bar_container.show()
            self.apply_container_style()

        self.rebuild_unified_menu()

    def show_context_menu(self, pos):
        if not self.hotkey_active:
            self.unified_menu.exec(self.image_label.mapToGlobal(pos))

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_transparency_state()

    def apply_container_style(self):
        text_color = "#FFFFFF"
        subtext_color = "#A1A1AA"
        btn_bg = "rgba(255, 255, 255, 0.12)"
        btn_hover = "rgba(255, 255, 255, 0.22)"

        if self.controls_visible:
            bg_hex = "#000000" if self.image_manager.current_pixmap else "#121214"
            border_style = "1px solid rgba(255, 255, 255, 0.25)"
        else:
            bg_hex = "transparent"
            border_style = "none"

        self.container.setStyleSheet(f"""
            QWidget#Container {{
                background-color: {bg_hex};
                border-radius: 8px;
                border: {border_style};
            }}
            QLabel {{
                color: {text_color};
                font-family: 'Segoe UI', sans-serif;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {text_color};
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
            QSlider::groove:vertical {{
                width: 4px;
                background: {btn_bg};
                border-radius: 2px;
            }}
            QSlider::handle:vertical {{
                background: #3B82F6;
                height: 12px;
                margin: 0 -4px;
                border-radius: 6px;
            }}
            QMenu {{
                background-color: #18181B;
                color: #FFFFFF;
                border: 1px solid #27272A;
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: #2563EB;
            }}
        """)

        self.title_label.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {subtext_color};")
        self.close_btn.setStyleSheet(f"""
            QPushButton {{ 
                font-weight: bold; 
                background-color: {btn_bg}; 
                color: {text_color}; 
            }} 
            QPushButton:hover {{ 
                background-color: #EF4444; 
                color: white; 
            }}
        """)

    # --- Mouse Drag & Magnet Snapping ---
    def mousePressEvent(self, event):
        if not self.hotkey_active and event.button() == Qt.LeftButton:
            self.show_controls_temporarily()
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if not self.hotkey_active:
            self.show_controls_temporarily()
            if event.buttons() == Qt.LeftButton and not self.drag_position.isNull():
                target_pos = event.globalPosition().toPoint() - self.drag_position
                if self.snap_enabled:
                    target_pos = self.calculate_snapped_position(target_pos)
                self.move(target_pos)
                event.accept()

    def calculate_snapped_position(self, target_pos):
        screen = QGuiApplication.screenAt(target_pos) or QGuiApplication.primaryScreen()
        if not screen:
            return target_pos

        work_area = screen.availableGeometry()
        x, y = target_pos.x(), target_pos.y()
        w, h = self.width(), self.height()

        if abs(x - work_area.left()) < self.snap_margin:
            x = work_area.left()
        elif abs((x + w) - work_area.right()) < self.snap_margin:
            x = work_area.right() - w

        if abs(y - work_area.top()) < self.snap_margin:
            y = work_area.top()
        elif abs((y + h) - work_area.bottom()) < self.snap_margin:
            y = work_area.bottom() - h

        return QPoint(x, y)

    def toggle_snap(self, checked):
        self.snap_enabled = checked

    def set_max_height_preset(self, ratio):
        self.max_height_preset = ratio
        self.fit_to_image_ratio()
        self.rebuild_unified_menu()

    # --- Grid Controls ---
    def toggle_grid(self, checked):
        self.image_label.show_grid = checked
        self.image_label.update()

    def set_grid_preset(self, cols, rows):
        self.image_label.grid_cols = cols
        self.image_label.grid_rows = rows
        self.image_label.show_grid = True
        self.image_label.update()
        self.rebuild_unified_menu()

    def set_grid_color(self, color_key):
        self.image_label.grid_color_key = color_key
        self.image_label.update()
        self.rebuild_unified_menu()

    def prompt_custom_grid(self):
        text, ok = QInputDialog.getText(
            self, "Custom Grid Dimensions", 
            "Enter grid as Cols x Rows (e.g. 5x5, 6x4, 8x8):",
            text=f"{self.image_label.grid_cols}x{self.image_label.grid_rows}"
        )
        if ok and text.strip():
            parts = text.lower().replace(" ", "").split("x")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                c, r = int(parts[0]), int(parts[1])
                if c > 0 and r > 0:
                    self.set_grid_preset(c, r)
                    return
            QMessageBox.warning(self, "Invalid Input", "Please enter valid dimensions like '5x5' or '4x6'.")

    # --- Screen Snipping ---
    def start_snipping(self):
        self.hide()
        QApplication.processEvents()
        self.snipper = ScreenSnipper(self.on_snip_completed)
        self.snipper.show()

    def on_snip_completed(self, pixmap):
        self.show()
        if pixmap and not pixmap.isNull():
            self.image_manager.save_pixmap_as_snip(pixmap)

    # --- File & Drag-Drop Handling ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if not self.hotkey_active and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if not self.hotkey_active:
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path and self.image_manager.is_valid_image(file_path):
                    self.image_manager.import_and_cache_file(file_path, self)

    def on_image_changed(self, cached_path, pixmap):
        self.image_label.apply_empty_style(False)
        self.fit_to_image_ratio()
        self.update_image_display()
        self.title_label.setText(os.path.basename(cached_path))
        self.apply_container_style()

    def clear_image(self):
        self.image_manager.clear()
        self.image_label.clear()
        self.image_label.setText("Drag & Drop Image Here\nor double-click to fit ratio")
        self.image_label.apply_empty_style(True)
        self.title_label.setText("Overlay Viewer")
        self.apply_container_style()

    def update_image_display(self):
        pixmap = self.image_manager.current_pixmap
        if pixmap and not pixmap.isNull():
            target_size = self.image_label.size()
            if target_size.width() <= 0 or target_size.height() <= 0:
                return

            if self.max_quality_mode:
                screen = QGuiApplication.screenAt(self.pos()) or QGuiApplication.primaryScreen()
                dpr = screen.devicePixelRatio() if screen else 1.0
                scaled_size = target_size * dpr

                scaled = pixmap.scaled(
                    scaled_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                scaled.setDevicePixelRatio(dpr)
                self.image_label.setPixmap(scaled)
            else:
                scaled = pixmap.scaled(
                    target_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled)
        self.image_label.update()

    def toggle_max_quality_mode(self, checked):
        self.max_quality_mode = checked
        self.update_image_display()

    def toggle_center_mark(self, checked):
        self.image_label.show_mark = checked
        self.image_label.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_image_display()

    # --- Navigation ---
    def prev_image(self):
        recents = self.image_manager.managed_images
        current = self.image_manager.current_image_path
        if not recents:
            return
        if current in recents:
            current_idx = recents.index(current)
            next_idx = (current_idx - 1) % len(recents)
        else:
            next_idx = 0
        self.image_manager.load_image_from_path(recents[next_idx])

    def next_image(self):
        recents = self.image_manager.managed_images
        current = self.image_manager.current_image_path
        if not recents:
            return
        if current in recents:
            current_idx = recents.index(current)
            next_idx = (current_idx + 1) % len(recents)
        else:
            next_idx = 0
        self.image_manager.load_image_from_path(recents[next_idx])

    def fit_to_image_ratio(self):
        pixmap = self.image_manager.current_pixmap
        if not pixmap or pixmap.isNull():
            return

        img_width = pixmap.width()
        img_height = pixmap.height()
        if img_height == 0:
            return

        aspect_ratio = img_width / img_height
        chrome_h = 40
        chrome_w = 12

        screen = QGuiApplication.screenAt(self.pos()) or QGuiApplication.primaryScreen()
        work_area = screen.availableGeometry()

        if self.max_height_preset > 0.0:
            target_h = int(work_area.height() * self.max_height_preset)
            content_h = target_h - chrome_h
            content_w = int(content_h * aspect_ratio)
            final_w = max(150, content_w + chrome_w)

            new_y = work_area.top() if self.max_height_preset == 1.0 else self.y()
            self.setGeometry(self.x(), new_y, final_w, target_h)
            return

        max_w = int(work_area.width() * 0.8)
        max_h = int(work_area.height() * 0.8)

        target_content_w = min(img_width, max_w - chrome_w)
        target_content_h = int(target_content_w / aspect_ratio)

        if target_content_h > (max_h - chrome_h):
            target_content_h = max_h - chrome_h
            target_content_w = int(target_content_h * aspect_ratio)

        final_w = max(150, target_content_w + chrome_w)
        final_h = max(100, target_content_h + chrome_h)

        self.resize(final_w, final_h)

    # --- Actions / Dialogs ---
    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif)"
        )
        if file_path:
            self.image_manager.import_and_cache_file(file_path, self)

    def open_url_dialog(self):
        url, ok = QInputDialog.getText(self, "Load Image from URL", "Enter Direct Image URL:")
        if ok and url.strip():
            self.image_manager.load_from_url(url, self)

    def open_image_manager(self):
        self.image_manager.open_manager_dialog(self)

    # --- Unified Options Menu ---
    def rebuild_unified_menu(self):
        self.unified_menu.clear()

        # Capture & Paste
        snip_action = QAction("✂ Screen Snipper", self)
        snip_action.triggered.connect(self.start_snipping)
        self.unified_menu.addAction(snip_action)

        paste_action = QAction("📋 Paste from Clipboard (Ctrl+V)", self)
        paste_action.triggered.connect(lambda: self.image_manager.paste_from_clipboard(self))
        self.unified_menu.addAction(paste_action)

        self.unified_menu.addSeparator()

        # File Actions
        open_action = QAction("📂 Open Image File...", self)
        open_action.triggered.connect(self.open_file_dialog)
        self.unified_menu.addAction(open_action)

        url_action = QAction("🌐 Load from URL...", self)
        url_action.triggered.connect(self.open_url_dialog)
        self.unified_menu.addAction(url_action)

        manager_action = QAction("🖼 Open Image Manager...", self)
        manager_action.triggered.connect(self.open_image_manager)
        self.unified_menu.addAction(manager_action)

        self.unified_menu.addSeparator()

        # Hotkey Configuration Action
        hotkey_action = QAction(f"⚙ Change Hotkey Lock ({self.hotkey_sequence})...", self)
        hotkey_action.triggered.connect(self.prompt_change_hotkey)
        self.unified_menu.addAction(hotkey_action)

        # Auto-Hide Toggle Option
        auto_hide_action = QAction("👁 Toggle Auto-Hide UI", self)
        auto_hide_action.setCheckable(True)
        auto_hide_action.setChecked(self.auto_hide_enabled)
        auto_hide_action.triggered.connect(self.toggle_auto_hide_mode)
        self.unified_menu.addAction(auto_hide_action)

        self.unified_menu.addSeparator()

        # Height Presets
        max_height_menu = QMenu("↕ Max Window Height Preset", self)
        mh_group = QActionGroup(self)
        mh_group.setExclusive(True)

        mh_options = [
            ("Disabled (Auto Fit)", 0.0),
            ("10% Screen Height", 0.10),
            ("20% Screen Height", 0.20),
            ("30% Screen Height", 0.30),
            ("40% Screen Height", 0.40),
            ("50% Screen Height", 0.50),
            ("60% Screen Height", 0.60),
            ("70% Screen Height", 0.70),
            ("80% Screen Height", 0.80),
            ("90% Screen Height", 0.90),
            ("100% Full Screen Height", 1.00)
        ]

        for label, ratio in mh_options:
            action = QAction(label, self)
            action.setCheckable(True)
            if self.max_height_preset == ratio:
                action.setChecked(True)
            action.triggered.connect(lambda checked=False, r=ratio: self.set_max_height_preset(r))
            mh_group.addAction(action)
            max_height_menu.addAction(action)

        self.unified_menu.addMenu(max_height_menu)

        # Grid Submenu
        grid_menu = QMenu("📐 Grid Overlay", self)

        toggle_grid_action = QAction("Show Grid Overlay", self)
        toggle_grid_action.setCheckable(True)
        toggle_grid_action.setChecked(self.image_label.show_grid)
        toggle_grid_action.triggered.connect(self.toggle_grid)
        grid_menu.addAction(toggle_grid_action)

        grid_menu.addSeparator()

        # Grid Presets
        grid_group = QActionGroup(self)
        grid_group.setExclusive(True)

        presets = [
            ("3x3 (Rule of Thirds)", 3, 3),
            ("3x4 Aspect Grid", 3, 4),
            ("4x5 Social Grid", 4, 5),
            ("2x2 Simple Quad", 2, 2),
            ("4x4 Grid", 4, 4)
        ]

        for label, cols, rows in presets:
            action = QAction(label, self)
            action.setCheckable(True)
            if self.image_label.grid_cols == cols and self.image_label.grid_rows == rows:
                action.setChecked(True)
            action.triggered.connect(lambda checked=False, c=cols, r=rows: self.set_grid_preset(c, r))
            grid_group.addAction(action)
            grid_menu.addAction(action)

        grid_menu.addSeparator()
        custom_grid_action = QAction("Custom Dimensions...", self)
        custom_grid_action.triggered.connect(self.prompt_custom_grid)
        grid_menu.addAction(custom_grid_action)

        grid_menu.addSeparator()

        # Grid Color Submenu
        grid_color_menu = QMenu("🎨 Grid Line Color", self)
        color_group = QActionGroup(self)
        color_group.setExclusive(True)

        grid_colors = ["white", "black", "red", "blue", "yellow", "cyan"]
        for c_key in grid_colors:
            action = QAction(c_key.capitalize(), self)
            action.setCheckable(True)
            if self.image_label.grid_color_key == c_key:
                action.setChecked(True)
            action.triggered.connect(lambda checked=False, k=c_key: self.set_grid_color(k))
            color_group.addAction(action)
            grid_color_menu.addAction(action)

        grid_menu.addMenu(grid_color_menu)
        self.unified_menu.addMenu(grid_menu)

        # Center Target Mark Toggle
        mark_action = QAction("🎯 Show Center Crosshair Mark", self)
        mark_action.setCheckable(True)
        mark_action.setChecked(self.image_label.show_mark)
        mark_action.triggered.connect(self.toggle_center_mark)
        self.unified_menu.addAction(mark_action)

        # Quality Toggle
        max_q_action = QAction("⚡ Max Quality Display (1:1 Pixels)", self)
        max_q_action.setCheckable(True)
        max_q_action.setChecked(self.max_quality_mode)
        max_q_action.triggered.connect(self.toggle_max_quality_mode)
        self.unified_menu.addAction(max_q_action)

        # Transparency Submenu
        transparency_submenu = QMenu("👁 Transparency Settings", self)

        enable_trans_action = QAction("Enable Transparency", self)
        enable_trans_action.setCheckable(True)
        enable_trans_action.setChecked(self.transparency_enabled)
        enable_trans_action.triggered.connect(self.toggle_transparency_mode)
        transparency_submenu.addAction(enable_trans_action)

        transparency_submenu.addSeparator()

        slider_widget = QWidget(self)
        slider_layout = QVBoxLayout(slider_widget)
        slider_layout.setContentsMargins(8, 8, 8, 8)
        self.slider_label = QLabel(f"Opacity: {self.opacity_slider.value()}%", slider_widget)
        self.slider_label.setAlignment(Qt.AlignCenter)
        self.slider_label.setStyleSheet("font-size: 11px; color: #AAA;")

        slider_layout.addWidget(self.slider_label)
        slider_layout.addWidget(self.opacity_slider, alignment=Qt.AlignCenter)

        action_slider = QWidgetAction(transparency_submenu)
        action_slider.setDefaultWidget(slider_widget)
        transparency_submenu.addAction(action_slider)

        self.unified_menu.addMenu(transparency_submenu)

        # Always on Top Toggle
        pin_action = QAction("📌 Always on Top (Pin)", self)
        pin_action.setCheckable(True)
        pin_action.setChecked(self.always_on_top)
        pin_action.triggered.connect(self.toggle_always_on_top)
        self.unified_menu.addAction(pin_action)

        # Magnet Snap Toggle
        snap_action = QAction("🧲 Magnet Snap to Edges", self)
        snap_action.setCheckable(True)
        snap_action.setChecked(self.snap_enabled)
        snap_action.triggered.connect(self.toggle_snap)
        self.unified_menu.addAction(snap_action)

    # --- Transparency & Pin Handlers ---
    def toggle_transparency_mode(self, checked):
        self.transparency_enabled = checked
        self.apply_transparency_state()

    def apply_transparency_state(self):
        val = self.opacity_slider.value()
        if hasattr(self, 'slider_label'):
            self.slider_label.setText(f"Opacity: {val}%")

        if self.transparency_enabled:
            self.setWindowOpacity(val / 100.0)
        else:
            self.setWindowOpacity(1.0)

        self.apply_container_style()

    def update_opacity(self, value):
        if hasattr(self, 'slider_label'):
            self.slider_label.setText(f"Opacity: {value}%")
        if self.transparency_enabled:
            self.setWindowOpacity(value / 100.0)

    def toggle_always_on_top(self, checked):
        self.always_on_top = checked
        self.setWindowFlag(Qt.WindowStaysOnTopHint, checked)
        self.show()

    # --- Persistence ---
    def save_config(self):
        config = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "opacity": self.opacity_slider.value(),
            "transparency_enabled": self.transparency_enabled,
            "max_quality_mode": self.max_quality_mode,
            "show_mark": self.image_label.show_mark,
            "show_grid": self.image_label.show_grid,
            "grid_cols": self.image_label.grid_cols,
            "grid_rows": self.image_label.grid_rows,
            "grid_color_key": self.image_label.grid_color_key,
            "always_on_top": self.always_on_top,
            "snap_enabled": self.snap_enabled,
            "max_height_preset": self.max_height_preset,
            "auto_hide_enabled": self.auto_hide_enabled,
            # "recent_images": self.image_manager.recent_images,
            "managed_images": self.image_manager.get_managed_data(),
            "last_image": self.image_manager.current_image_path,
            "hotkey_sequence": self.hotkey_sequence
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self.toggle_always_on_top(True)
            self.rebuild_unified_menu()
            return

        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)

            x = config.get("x", self.x())
            y = config.get("y", self.y())
            w = config.get("width", self.width())
            h = config.get("height", self.height())
            self.setGeometry(x, y, w, h)

            opacity = config.get("opacity", 90)
            self.opacity_slider.setValue(opacity)

            self.transparency_enabled = config.get("transparency_enabled", False)
            self.max_quality_mode = config.get("max_quality_mode", True)
            self.image_label.show_mark = config.get("show_mark", True)
            self.image_label.show_grid = config.get("show_grid", False)
            self.image_label.grid_cols = config.get("grid_cols", 3)
            self.image_label.grid_rows = config.get("grid_rows", 3)
            self.image_label.grid_color_key = config.get("grid_color_key", "white")
            self.max_height_preset = config.get("max_height_preset", 0.0)

            always_top = config.get("always_on_top", True)
            self.toggle_always_on_top(always_top)

            self.snap_enabled = config.get("snap_enabled", True)

            auto_hide = config.get("auto_hide_enabled", True)
            self.toggle_auto_hide_mode(auto_hide)

            self.hotkey_sequence = config.get("hotkey_sequence", "Ctrl+Shift+H")

            self.image_manager.set_managed_images(config.get("managed_images", config.get("recent_images", [])))

            self.rebuild_unified_menu()

            last_image = config.get("last_image")
            if last_image and os.path.exists(last_image):
                self.image_manager.load_image_from_path(last_image)
            else:
                self.clear_image()

        except Exception as e:
            print(f"Failed to load config: {e}")

    def closeEvent(self, event):
        if IS_WINDOWS and self.winId():
            user32.UnregisterHotKey(int(self.winId()), HOTKEY_ID)
        self.save_config()
        event.accept()