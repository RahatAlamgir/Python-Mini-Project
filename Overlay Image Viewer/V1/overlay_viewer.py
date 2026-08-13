import sys
import os
import json
import shutil
import requests
import ctypes
from ctypes import wintypes

from PySide6.QtCore import Qt, QPoint, QRect, QByteArray, QEvent, QTimer
from PySide6.QtGui import (
    QPixmap, QImage, QDragEnterEvent, QDropEvent, QAction, QColor, 
    QGuiApplication, QKeySequence, QShortcut, QPainter, QPen, QActionGroup, QIcon
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QMenu, QFileDialog, QSizeGrip,
    QListWidget, QListWidgetItem, QDialog, QMessageBox, QSplitter, 
    QWidgetAction, QInputDialog, QKeySequenceEdit
)

# --- Windows API Constants & Functions for Click Pass-Through & Global Hotkeys ---
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    user32 = ctypes.windll.user32

    # 32-bit / 64-bit compatibility for Window Long calls
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        GetWindowLong = user32.GetWindowLongPtrW
        SetWindowLong = user32.SetWindowLongPtrW
    else:
        GetWindowLong = user32.GetWindowLongW
        SetWindowLong = user32.SetWindowLongW

    GWL_EXSTYLE = -20
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_LAYERED = 0x00080000
    WM_HOTKEY = 0x0312

    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008
    HOTKEY_ID = 9001

# Base application directory
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "overlay_viewer_config.json")
TEMP_IMG_DIR = os.path.join(BASE_DIR, "temp_images")


class ScreenSnipper(QWidget):
    """Overlay window for dragging and capturing a high-resolution rectangular screen area."""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_selecting = False

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)

        primary_screen = QGuiApplication.primaryScreen()
        self.dpr = primary_screen.devicePixelRatio() if primary_screen else 1.0

        screen_rect = QRect()
        for screen in QGuiApplication.screens():
            screen_rect = screen_rect.united(screen.geometry())
        self.setGeometry(screen_rect)

        self.full_screen_pixmap = primary_screen.grabWindow(0, screen_rect.x(), screen_rect.y(), screen_rect.width(), screen_rect.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            rect = QRect(self.start_point, self.end_point).normalized()
            self.hide()

            if rect.width() > 10 and rect.height() > 10:
                scaled_rect = QRect(
                    int(rect.x() * self.dpr),
                    int(rect.y() * self.dpr),
                    int(rect.width() * self.dpr),
                    int(rect.height() * self.dpr)
                )
                cropped = self.full_screen_pixmap.copy(scaled_rect)
                self.callback(cropped)
            else:
                self.callback(None)
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
            self.callback(None)
            self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.is_selecting:
            rect = QRect(self.start_point, self.end_point).normalized()
            scaled_rect = QRect(
                int(rect.x() * self.dpr),
                int(rect.y() * self.dpr),
                int(rect.width() * self.dpr),
                int(rect.height() * self.dpr)
            )
            painter.drawPixmap(rect, self.full_screen_pixmap, scaled_rect)
            
            pen = QPen(QColor(59, 130, 246), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(rect)


class ImageDisplayWidget(QLabel):
    """Custom label that draws crosshair mark and configurable grid overlays."""
    GRID_COLORS = {
        "white": QColor(255, 255, 255, 180),
        "black": QColor(0, 0, 0, 180),
        "red": QColor(239, 68, 68, 200),
        "blue": QColor(59, 130, 246, 200),
        "yellow": QColor(234, 179, 8, 200),
        "cyan": QColor(6, 182, 212, 200)
    }

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.show_mark = True
        self.mark_color = QColor(239, 68, 68)

        # Grid settings
        self.show_grid = False
        self.grid_cols = 3
        self.grid_rows = 3
        self.grid_color_key = "white"

        self.apply_empty_style(True)

    def apply_empty_style(self, is_empty):
        if is_empty:
            self.setStyleSheet("""
                QLabel {
                    background-color: #121214;
                    border: 2px dashed #3F3F46;
                    border-radius: 8px;
                    color: #A1A1AA;
                    font-size: 13px;
                    font-weight: 500;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                }
            """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Draw Grid Overlay
        if self.show_grid and self.grid_cols > 0 and self.grid_rows > 0:
            color = self.GRID_COLORS.get(self.grid_color_key, self.GRID_COLORS["white"])
            grid_pen = QPen(color, 1, Qt.DashLine)
            painter.setPen(grid_pen)

            col_step = w / self.grid_cols
            for col in range(1, self.grid_cols):
                x = int(col * col_step)
                painter.drawLine(x, 0, x, h)

            row_step = h / self.grid_rows
            for row in range(1, self.grid_rows):
                y = int(row * row_step)
                painter.drawLine(0, y, w, y)

        # Draw Center Crosshair Mark
        if self.show_mark:
            center = self.rect().center()
            size = 12
            
            pen_outer = QPen(QColor(0, 0, 0, 200), 3.5)
            painter.setPen(pen_outer)
            painter.drawLine(center.x() - size, center.y(), center.x() + size, center.y())
            painter.drawLine(center.x(), center.y() - size, center.x(), center.y() + size)
            
            pen_inner = QPen(self.mark_color, 2)
            painter.setPen(pen_inner)
            painter.drawLine(center.x() - size, center.y(), center.x() + size, center.y())
            painter.drawLine(center.x(), center.y() - size, center.x(), center.y() + size)


class ImageManagerDialog(QDialog):
    """Popup window to manage, preview, delete, and clean cached recent images."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_viewer = parent
        self.setWindowTitle("Image Manager & Temp Cleanup")
        self.setMinimumSize(620, 420)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #121214;
                color: #E4E4E7;
            }
            QLabel {
                color: #E4E4E7;
                font-family: 'Segoe UI', sans-serif;
            }
            QListWidget {
                background-color: #18181B;
                border: 1px solid #27272A;
                border-radius: 8px;
                color: #E4E4E7;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #2563EB;
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #27272A;
                color: #E4E4E7;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3F3F46;
            }
        """)

        self.init_ui()
        self.populate_list()

    def init_ui(self):
        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal, self)

        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        list_label = QLabel("Recent Cached Images:", self)
        list_label.setStyleSheet("font-weight: bold;")
        self.image_list = QListWidget(self)
        self.image_list.itemSelectionChanged.connect(self.on_item_selected)

        left_layout.addWidget(list_label)
        left_layout.addWidget(self.image_list)

        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_label_heading = QLabel("Live Preview:", self)
        preview_label_heading.setStyleSheet("font-weight: bold;")

        self.preview_label = QLabel("Select an image to preview", self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #000000; border: 1px solid #27272A; border-radius: 8px; color: #71717A;")

        self.info_label = QLabel("", self)
        self.info_label.setStyleSheet("font-size: 11px; color: #A1A1AA;")
        self.info_label.setWordWrap(True)

        right_layout.addWidget(preview_label_heading)
        right_layout.addWidget(self.preview_label, stretch=1)
        right_layout.addWidget(self.info_label)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([220, 380])
        layout.addWidget(splitter, stretch=1)

        btn_layout = QHBoxLayout()

        self.load_selected_btn = QPushButton("📂 Display in Overlay", self)
        self.load_selected_btn.clicked.connect(self.load_selected_to_main)

        self.delete_btn = QPushButton("🗑 Delete Selected", self)
        self.delete_btn.setStyleSheet("background-color: #7F1D1D; color: white; border-color: #991B1B;")
        self.delete_btn.clicked.connect(self.delete_selected_image)

        self.clean_all_btn = QPushButton("🧹 Clear All Temp", self)
        self.clean_all_btn.setStyleSheet("background-color: #991B1B; color: white; font-weight: bold; border-color: #B91C1C;")
        self.clean_all_btn.clicked.connect(self.clean_all_temp)

        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.load_selected_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.clean_all_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def populate_list(self):
        self.image_list.clear()
        for idx, cached_path in enumerate(self.parent_viewer.recent_images):
            filename = os.path.basename(cached_path)
            list_item = QListWidgetItem(f"{idx + 1}. {filename}")
            list_item.setData(Qt.UserRole, cached_path)
            self.image_list.addItem(list_item)

        if self.image_list.count() > 0:
            self.image_list.setCurrentRow(0)

    def on_item_selected(self):
        selected_items = self.image_list.selectedItems()
        if not selected_items:
            self.preview_label.setText("No selection")
            self.info_label.setText("")
            return

        cached_path = selected_items[0].data(Qt.UserRole)

        if os.path.exists(cached_path):
            pixmap = QPixmap(cached_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled)

                file_size_kb = os.path.getsize(cached_path) / 1024.0
                self.info_label.setText(
                    f"Dimensions: {pixmap.width()}x{pixmap.height()} px\n"
                    f"Size: {file_size_kb:.1f} KB\n"
                    f"Cached Path: {cached_path}"
                )
            else:
                self.preview_label.setText("Failed to render image")
        else:
            self.preview_label.setText("File not found")
            self.info_label.setText(f"Missing cached file:\n{cached_path}")

    def load_selected_to_main(self):
        selected_items = self.image_list.selectedItems()
        if selected_items:
            cached_path = selected_items[0].data(Qt.UserRole)
            if os.path.exists(cached_path):
                self.parent_viewer.load_image_from_path(cached_path)

    def delete_selected_image(self):
        selected_items = self.image_list.selectedItems()
        if not selected_items:
            return

        cached_path = selected_items[0].data(Qt.UserRole)

        if os.path.exists(cached_path):
            try:
                os.remove(cached_path)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not delete file:\n{e}")

        self.parent_viewer.recent_images = [
            p for p in self.parent_viewer.recent_images if p != cached_path
        ]
        if self.parent_viewer.current_image_path == cached_path:
            self.parent_viewer.clear_image()

        self.parent_viewer.rebuild_unified_menu()
        self.populate_list()

    def clean_all_temp(self):
        reply = QMessageBox.question(
            self,
            "Confirm Clean All",
            "Are you sure you want to delete ALL images from temp_images?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if os.path.exists(TEMP_IMG_DIR):
                for filename in os.listdir(TEMP_IMG_DIR):
                    file_path = os.path.join(TEMP_IMG_DIR, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        print(f"Failed to delete {file_path}: {e}")

            self.parent_viewer.recent_images.clear()
            self.parent_viewer.clear_image()
            self.parent_viewer.rebuild_unified_menu()

            self.populate_list()
            self.preview_label.clear()
            self.preview_label.setText("Temp folder cleaned!")
            self.info_label.setText("")


class HotkeyConfigDialog(QDialog):
    """Dialog allowing the user to configure a custom hotkey sequence."""
    def __init__(self, current_key, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Lock Hotkey")
        self.setFixedSize(320, 140)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QDialog { background-color: #121214; color: #E4E4E7; }
            QLabel { color: #E4E4E7; font-size: 12px; }
            QKeySequenceEdit { background-color: #18181B; color: #3B82F6; border: 1px solid #3F3F46; padding: 6px; border-radius: 4px; font-weight: bold; }
            QPushButton { background-color: #27272A; color: #E4E4E7; border: 1px solid #3F3F46; border-radius: 4px; padding: 6px 12px; }
            QPushButton:hover { background-color: #3F3F46; }
        """)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Press shortcut key combination:", self))
        
        self.key_editor = QKeySequenceEdit(QKeySequence(current_key), self)
        layout.addWidget(self.key_editor)

        btn_box = QHBoxLayout()
        save_btn = QPushButton("Save Hotkey", self)
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.clicked.connect(self.reject)

        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        layout.addLayout(btn_box)

    def get_sequence_str(self):
        return self.key_editor.keySequence().toString()


class OverlayImageViewer(QWidget):
    def __init__(self):
        super().__init__()
        
        os.makedirs(TEMP_IMG_DIR, exist_ok=True)

        self.recent_images = []
        self.always_on_top = True
        self.transparency_enabled = False
        self.max_quality_mode = True
        self.snap_enabled = True
        self.max_height_preset = 0.0

        self.drag_position = QPoint()
        self.current_image_path = None
        self.current_pixmap = None
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
        self.shortcut_paste.activated.connect(self.paste_image_from_clipboard)

        self.apply_container_style()
        
        QApplication.instance().installEventFilter(self)
        self.setMouseTracking(True)
        self.show_controls_temporarily()

    # --- Windows Native Global Hotkey Registration ---
    def setup_hotkey(self):
        if IS_WINDOWS and self.winId():
            hwnd = int(self.winId())
            user32.UnregisterHotKey(hwnd, HOTKEY_ID)

            # Parse string like "Ctrl+Shift+H" into Win32 Modifiers and Key Code
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
            vk_code = ord(key_str[0]) if len(key_str) == 1 and key_str.isalnum() else 0x48 # Default H

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
            # 1. Save Current Settings
            self.saved_always_on_top = self.always_on_top
            self.saved_auto_hide_enabled = self.auto_hide_enabled

            # 2. Enable Native Click-Through & Disable standard navigation keys
            self.set_win32_click_through(True)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.shortcut_left.setEnabled(False)
            self.shortcut_right.setEnabled(False)
            self.shortcut_paste.setEnabled(False)

            # 3. Pin Top Mode
            self.setWindowFlag(Qt.WindowStaysOnTopHint, True)

            # 4. Hide UI Completely
            self.auto_hide_enabled = False
            self.hide_timer.stop()
            self.controls_visible = False
            self.control_bar_container.hide()
            self.bottom_bar_container.hide()
            self.apply_container_style()
            self.show()
        else:
            # Revert back to interactive mode
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
            bg_hex = "#000000" if self.current_pixmap else "#121214"
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
            filename = f"snip_{len(self.recent_images) + 1}.png"
            cached_path = os.path.join(TEMP_IMG_DIR, filename)
            pixmap.save(cached_path, "PNG", 100)
            self.load_image_from_path(cached_path)

    # --- Clipboard Paste ---
    def paste_image_from_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                filename = f"pasted_{len(self.recent_images) + 1}.png"
                cached_path = os.path.join(TEMP_IMG_DIR, filename)
                image.save(cached_path, "PNG", 100)
                self.load_image_from_path(cached_path)
        elif mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path and self.is_valid_image(file_path):
                    self.import_and_cache_file(file_path)
        else:
            QMessageBox.information(self, "Clipboard Empty", "No valid image found on clipboard.")

    # --- File Handling ---
    def dragEnterEvent(self, event: QDragEnterEvent):
        if not self.hotkey_active and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if not self.hotkey_active:
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path and self.is_valid_image(file_path):
                    self.import_and_cache_file(file_path)

    def is_valid_image(self, file_path):
        valid_exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tiff"}
        return os.path.splitext(file_path)[1].lower() in valid_exts

    def import_and_cache_file(self, source_path):
        try:
            filename = os.path.basename(source_path)
            cached_path = os.path.join(TEMP_IMG_DIR, filename)
            
            if os.path.abspath(source_path) != os.path.abspath(cached_path):
                shutil.copy2(source_path, cached_path)

            self.load_image_from_path(cached_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import image:\n{e}")

    def load_image_from_path(self, cached_path):
        if not os.path.exists(cached_path):
            return

        pixmap = QPixmap(cached_path)
        if not pixmap.isNull():
            self.current_image_path = cached_path
            self.current_pixmap = pixmap
            self.image_label.apply_empty_style(False)
            self.fit_to_image_ratio()
            self.update_image_display()
            self.add_to_recents(cached_path)
            self.title_label.setText(os.path.basename(cached_path))
            self.apply_container_style()

    def clear_image(self):
        self.current_image_path = None
        self.current_pixmap = None
        self.image_label.clear()
        self.image_label.setText("Drag & Drop Image Here\nor double-click to fit ratio")
        self.image_label.apply_empty_style(True)
        self.title_label.setText("Overlay Viewer")
        self.apply_container_style()

    def update_image_display(self):
        if self.current_pixmap and not self.current_pixmap.isNull():
            target_size = self.image_label.size()
            if target_size.width() <= 0 or target_size.height() <= 0:
                return

            if self.max_quality_mode:
                screen = QGuiApplication.screenAt(self.pos()) or QGuiApplication.primaryScreen()
                dpr = screen.devicePixelRatio() if screen else 1.0
                scaled_size = target_size * dpr
                
                scaled = self.current_pixmap.scaled(
                    scaled_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                scaled.setDevicePixelRatio(dpr)
                self.image_label.setPixmap(scaled)
            else:
                scaled = self.current_pixmap.scaled(
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
        if not self.recent_images:
            return
        if self.current_image_path in self.recent_images:
            current_idx = self.recent_images.index(self.current_image_path)
            next_idx = (current_idx - 1) % len(self.recent_images)
        else:
            next_idx = 0
        self.load_image_from_path(self.recent_images[next_idx])

    def next_image(self):
        if not self.recent_images:
            return
        if self.current_image_path in self.recent_images:
            current_idx = self.recent_images.index(self.current_image_path)
            next_idx = (current_idx + 1) % len(self.recent_images)
        else:
            next_idx = 0
        self.load_image_from_path(self.recent_images[next_idx])

    def fit_to_image_ratio(self):
        if not self.current_pixmap or self.current_pixmap.isNull():
            return

        img_width = self.current_pixmap.width()
        img_height = self.current_pixmap.height()
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
            self.import_and_cache_file(file_path)

    def open_url_dialog(self):
        url, ok = QInputDialog.getText(self, "Load Image from URL", "Enter Direct Image URL:")
        if ok and url.strip():
            try:
                response = requests.get(url.strip(), timeout=5)
                response.raise_for_status()
                image = QImage()
                if image.loadFromData(QByteArray(response.content)):
                    filename = f"url_image_{len(self.recent_images) + 1}.png"
                    cached_path = os.path.join(TEMP_IMG_DIR, filename)
                    image.save(cached_path, "PNG", 100)
                    self.load_image_from_path(cached_path)
                else:
                    QMessageBox.warning(self, "Error", "Failed to parse image from URL.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to download image:\n{str(e)}")

    def open_image_manager(self):
        dialog = ImageManagerDialog(self)
        dialog.exec()

    # --- Unified Options Menu ---
    def add_to_recents(self, cached_path):
        if cached_path in self.recent_images:
            self.recent_images.remove(cached_path)
        self.recent_images.insert(0, cached_path)
        self.recent_images = self.recent_images[:20]
        self.rebuild_unified_menu()

    def rebuild_unified_menu(self):
        self.unified_menu.clear()

        # Capture & Paste
        snip_action = QAction("✂ Screen Snipper", self)
        snip_action.triggered.connect(self.start_snipping)
        self.unified_menu.addAction(snip_action)

        paste_action = QAction("📋 Paste from Clipboard (Ctrl+V)", self)
        paste_action.triggered.connect(self.paste_image_from_clipboard)
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

        self.unified_menu.addSeparator()

        # Recents
        recents_header = QAction("Recent Images:", self)
        recents_header.setEnabled(False)
        self.unified_menu.addAction(recents_header)

        if not self.recent_images:
            no_recents = QAction("  (No recent images)", self)
            no_recents.setEnabled(False)
            self.unified_menu.addAction(no_recents)
            return

        for p in self.recent_images:
            if os.path.exists(p):
                filename = os.path.basename(p)
                prefix = "✓ " if p == self.current_image_path else "   "
                action = QAction(f"{prefix}{filename}", self)
                action.triggered.connect(lambda checked=False, path=p: self.load_image_from_path(path))
                self.unified_menu.addAction(action)

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
            "recent_images": self.recent_images[:20],
            "last_image": self.current_image_path,
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

            raw_recents = config.get("recent_images", [])
            self.recent_images = []
            for item in raw_recents:
                path = item if isinstance(item, str) else item.get("cached", "")
                if path and os.path.exists(path):
                    self.recent_images.append(path)
            self.recent_images = self.recent_images[:20]

            self.rebuild_unified_menu()

            last_image = config.get("last_image")
            if last_image and os.path.exists(last_image):
                self.load_image_from_path(last_image)
            else:
                self.clear_image()

        except Exception as e:
            print(f"Failed to load config: {e}")

    def closeEvent(self, event):
        if IS_WINDOWS and self.winId():
            user32.UnregisterHotKey(int(self.winId()), HOTKEY_ID)
        self.save_config()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    icon_path = os.path.join(BASE_DIR, "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    viewer = OverlayImageViewer()
    viewer.show()

    # Re-register hotkey after window handle initialization
    viewer.setup_hotkey()

    sys.exit(app.exec())