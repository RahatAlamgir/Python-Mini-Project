import sys
import os
import json
import pyperclip
from PIL import ImageGrab

from PyQt6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor, QCursor, QGuiApplication, QPixmap, QPainter, 
    QImage, QIcon, QPen, QRegion, QLinearGradient, QBrush
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QComboBox, QSlider, QLabel, QLineEdit, QSpinBox
)

SETTINGS_FILE = "settings.json"

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def parse_hex_color(hex_str):
    """Safely parses 6-digit or 8-digit Hex/ARGB strings into QColor."""
    if not hex_str:
        return QColor()
    hex_str = str(hex_str).strip().lstrip("#").replace("0x", "")
    
    if len(hex_str) == 8:
        a = int(hex_str[0:2], 16)
        r = int(hex_str[2:4], 16)
        g = int(hex_str[4:6], 16)
        b = int(hex_str[6:8], 16)
        return QColor(r, g, b, a)
    elif len(hex_str) == 6:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return QColor(r, g, b, 255)
    return QColor()


class SplitSwatchFrame(QFrame):
    """Custom Frame that renders a split 'New' (Left) vs 'Current' (Right) color preview."""
    def __init__(self, click_callback, parent=None):
        super().__init__(parent)
        self.click_callback = click_callback
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.new_color = QColor("#3B82F6")
        self.current_color = QColor("#3B82F6")
        self.is_split = False

    def set_colors(self, new_col, current_col, is_split=False):
        self.new_color = new_col
        self.current_color = current_col
        self.is_split = is_split
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.click_callback()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        
        if self.is_split:
            left_rect = QRectF(rect.x(), rect.y(), rect.width() / 2.0, rect.height())
            painter.fillRect(left_rect, self.new_color)

            right_rect = QRectF(rect.x() + rect.width() / 2.0, rect.y(), rect.width() / 2.0, rect.height())
            painter.fillRect(right_rect, self.current_color)
        else:
            painter.fillRect(rect, self.new_color)

        painter.setPen(QPen(QColor("#3C3C3C"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(rect.x(), rect.y(), rect.width() - 1, rect.height() - 1))


class SaturationValueSquare(QWidget):
    """2D Box for Saturation (X) and Value (Y) + Vertical Hue Bar."""
    colorChanged = pyqtSignal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(264, 150)
        
        self.hue = 0.0
        self.sat = 0.0
        self.val = 1.0
        self.alpha = 1.0
        
        self.dragging_box = False
        self.dragging_hue = False

    def set_color(self, qcolor):
        h, s, v, a = qcolor.getHsvF()
        if h >= 0:
            self.hue = h
        self.sat = s
        self.val = v if v >= 0 else 1.0
        self.alpha = a if a >= 0 else 1.0
        self.update()

    def get_color(self):
        col = QColor.fromHsvF(self.hue, self.sat, self.val)
        col.setAlphaF(self.alpha)
        return col

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        box_x, box_y = 0.0, 5.0
        box_w, box_h = 224.0, 140.0
        box_rect = QRectF(box_x, box_y, box_w, box_h)

        pure_hue = QColor.fromHsvF(self.hue, 1.0, 1.0)
        painter.fillRect(box_rect, pure_hue)

        sat_grad = QLinearGradient(box_x, box_y, box_x + box_w, box_y)
        sat_grad.setColorAt(0.0, QColor(255, 255, 255, 255))
        sat_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillRect(box_rect, QBrush(sat_grad))

        val_grad = QLinearGradient(box_x, box_y, box_x, box_y + box_h)
        val_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        val_grad.setColorAt(1.0, QColor(0, 0, 0, 255))
        painter.fillRect(box_rect, QBrush(val_grad))

        painter.setPen(QPen(QColor("#3C3C3C"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(box_rect)

        knob_x = box_x + self.sat * box_w
        knob_y = box_y + (1.0 - self.val) * box_h
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawEllipse(QPointF(knob_x, knob_y), 4, 4)

        hue_x, hue_y = 240.0, 5.0
        hue_w, hue_h = 24.0, 140.0
        hue_rect = QRectF(hue_x, hue_y, hue_w, hue_h)

        hue_grad = QLinearGradient(hue_x, hue_y, hue_x, hue_y + hue_h)
        colors = [
            (0.00, QColor(255, 0, 0)),
            (0.17, QColor(255, 255, 0)),
            (0.33, QColor(0, 255, 0)),
            (0.50, QColor(0, 255, 255)),
            (0.67, QColor(0, 0, 255)),
            (0.83, QColor(255, 0, 255)),
            (1.00, QColor(255, 0, 0))
        ]
        for pos, col in colors:
            hue_grad.setColorAt(pos, col)

        painter.setBrush(QBrush(hue_grad))
        painter.setPen(QPen(QColor("#3C3C3C"), 1))
        painter.drawRect(hue_rect)

        handle_y = hue_y + self.hue * hue_h
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FFFFFF"))

        arrow_left = [
            QPointF(hue_x - 1, handle_y),
            QPointF(hue_x - 5, handle_y - 4),
            QPointF(hue_x - 5, handle_y + 4)
        ]
        arrow_right = [
            QPointF(hue_x + hue_w + 1, handle_y),
            QPointF(hue_x + hue_w + 5, handle_y - 4),
            QPointF(hue_x + hue_w + 5, handle_y + 4)
        ]
        painter.drawPolygon(arrow_left)
        painter.drawPolygon(arrow_right)

    def mousePressEvent(self, event):
        pos = event.pos()
        if self._is_in_box(pos):
            self.dragging_box = True
            self._update_box_from_pos(pos)
        elif self._is_in_hue(pos):
            self.dragging_hue = True
            self._update_hue_from_pos(pos)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        if self.dragging_box:
            self._update_box_from_pos(pos)
        elif self.dragging_hue:
            self._update_hue_from_pos(pos)

    def mouseReleaseEvent(self, event):
        self.dragging_box = False
        self.dragging_hue = False

    def _is_in_box(self, pos):
        return 0 <= pos.x() <= 224 and 5 <= pos.y() <= 145

    def _is_in_hue(self, pos):
        return 235 <= pos.x() <= 264 and 5 <= pos.y() <= 145

    def _update_box_from_pos(self, pos):
        x = max(0.0, min(224.0, float(pos.x())))
        y = max(5.0, min(145.0, float(pos.y())))
        
        self.sat = x / 224.0
        self.val = 1.0 - ((y - 5.0) / 140.0)

        self.update()
        self.colorChanged.emit(self.get_color())

    def _update_hue_from_pos(self, pos):
        y = max(5.0, min(145.0, float(pos.y())))
        self.hue = (y - 5.0) / 140.0

        self.update()
        self.colorChanged.emit(self.get_color())


class FullscreenOverlay(QWidget):
    """Snapshot screen with fixed step loupe zoom (4x, 8x, 16x)."""
    def __init__(self, main_picker):
        super().__init__()
        self.main_picker = main_picker
        self.mouse_pos = QPoint(-1000, -1000)

        self.zoom_levels = [4, 8, 16]
        self.zoom_index = 1
        self.loupe_radius = 60
        
        screen_img = ImageGrab.grab(all_screens=True)
        img_data = screen_img.tobytes("raw", "RGB")
        self.qimage = QImage(
            img_data, 
            screen_img.width, 
            screen_img.height, 
            screen_img.width * 3, 
            QImage.Format.Format_RGB888
        )
        self.pixmap = QPixmap.fromImage(self.qimage)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        geo = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(geo)

        self.setMouseTracking(True)
        QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))

    @property
    def zoom_factor(self):
        return self.zoom_levels[self.zoom_index]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.drawPixmap(0, 0, self.pixmap)

        x, y = self.mouse_pos.x(), self.mouse_pos.y()
        if 0 <= x < self.qimage.width() and 0 <= y < self.qimage.height():
            src_w = int((self.loupe_radius * 2) / self.zoom_factor)
            src_h = int((self.loupe_radius * 2) / self.zoom_factor)
            src_x = x - src_w // 2
            src_y = y - src_h // 2

            cropped_pixmap = self.pixmap.copy(src_x, src_y, src_w, src_h)
            zoomed_pixmap = cropped_pixmap.scaled(
                self.loupe_radius * 2, 
                self.loupe_radius * 2, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.FastTransformation
            )

            loupe_rect = QRect(x - self.loupe_radius, y - self.loupe_radius, self.loupe_radius * 2, self.loupe_radius * 2)
            loupe_region = QRegion(loupe_rect, QRegion.RegionType.Ellipse)
            
            painter.save()
            painter.setClipRegion(loupe_region)
            painter.drawPixmap(loupe_rect.topLeft(), zoomed_pixmap)

            px_size = self.zoom_factor
            center_x = x - (px_size // 2)
            center_y = y - (px_size // 2)
            painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(center_x, center_y, px_size, px_size)

            painter.restore()

            painter.setPen(QPen(QColor("#007ACC"), 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(loupe_rect)

            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(x - 12, y - self.loupe_radius - 8, f"{self.zoom_factor}x")

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_index = min(len(self.zoom_levels) - 1, self.zoom_index + 1)
        else:
            self.zoom_index = max(0, self.zoom_index - 1)
        self.update()

    def mouseMoveEvent(self, event):
        self.mouse_pos = event.pos()
        x, y = self.mouse_pos.x(), self.mouse_pos.y()

        if 0 <= x < self.qimage.width() and 0 <= y < self.qimage.height():
            qcolor = self.qimage.pixelColor(x, y)
            self.main_picker.update_color_from_picker(qcolor)

        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.cleanup_and_close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cleanup_and_close()

    def cleanup_and_close(self):
        QGuiApplication.restoreOverrideCursor()
        self.close()


class FlutterColorPicker(QWidget):
    def __init__(self, icon):
        super().__init__()
        self.app_icon = icon
        self.current_color = QColor("#3B82F6")
        self.saved_color = QColor("#3B82F6")
        self.history = []
        
        self.init_ui()
        self.load_settings()
        self.position_bottom_left()

    def position_bottom_left(self):
        screen = QApplication.primaryScreen().geometry()
        margin = 15
        x = margin
        y = screen.height() - self.height() - margin - 40
        self.move(x, y)

    def init_ui(self):
        self.setWindowTitle("Flutter Color Picker")
        self.setWindowIcon(self.app_icon)

        self.setFixedSize(280, 115)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #CCCCCC;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QPushButton.format-btn {
                background-color: #252526;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
                border-radius: 2px;
                text-align: center;
                font-family: 'Consolas', 'Cascadia Code', monospace;
                font-size: 11px;
            }
            QPushButton.format-btn:hover {
                background-color: #2A2D2E;
                border-color: #007ACC;
                color: #FFFFFF;
            }
            QPushButton.action-btn {
                background-color: #252526;
                color: #888888;
                border: 1px solid #3C3C3C;
                border-radius: 2px;
                font-size: 10px;
            }
            QPushButton.action-btn:hover {
                color: #FFFFFF;
                border-color: #007ACC;
            }
            QComboBox {
                background-color: #252526;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
                border-radius: 2px;
                padding: 2px 5px;
                font-size: 11px;
                font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background-color: #252526;
                color: #D4D4D4;
                selection-background-color: #094771;
                border: 1px solid #3C3C3C;
            }
            QLineEdit {
                background-color: #252526;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
                border-radius: 2px;
                padding: 2px 4px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #007ACC;
            }
            QSpinBox {
                background-color: #252526;
                color: #D4D4D4;
                border: 1px solid #3C3C3C;
                border-radius: 2px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                padding: 1px;
            }
            QSpinBox:focus {
                border-color: #007ACC;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #3C3C3C;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #007ACC;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QLabel {
                font-size: 10px;
                color: #888888;
            }
        """)

        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(6)
        self.main_layout.setContentsMargins(8, 8, 8, 8)

        # 1. Tweak Container
        self.tweak_container = QWidget()
        tweak_layout = QVBoxLayout(self.tweak_container)
        tweak_layout.setContentsMargins(0, 2, 0, 10)
        tweak_layout.setSpacing(10)

        # Direct Text Input
        self.txt_input = QLineEdit()
        self.txt_input.setFixedHeight(24)
        self.txt_input.setPlaceholderText("Paste/Type color (#HEX or 0xARGB)...")
        self.txt_input.returnPressed.connect(self.on_text_entered)
        tweak_layout.addWidget(self.txt_input)

        # 2D Saturation / Value Canvas
        self.sat_val_widget = SaturationValueSquare()
        self.sat_val_widget.colorChanged.connect(self.on_box_color_changed)
        tweak_layout.addWidget(self.sat_val_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # RGBA Sliders + Spinboxes
        rgba_layout = QVBoxLayout()
        rgba_layout.setSpacing(4)

        self.sliders = {}
        self.spinboxes = {}
        for channel in ['R', 'G', 'B', 'A']:
            h_layout = QHBoxLayout()
            h_layout.setSpacing(6)
            
            lbl = QLabel(channel)
            lbl.setFixedWidth(12)
            
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 255)
            slider.valueChanged.connect(self.on_slider_changed)
            
            spinbox = QSpinBox()
            spinbox.setRange(0, 255)
            spinbox.setFixedWidth(38)
            spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spinbox.valueChanged.connect(self.on_spinbox_changed)
            
            h_layout.addWidget(lbl)
            h_layout.addWidget(slider)
            h_layout.addWidget(spinbox)
            rgba_layout.addLayout(h_layout)

            self.sliders[channel] = slider
            self.spinboxes[channel] = spinbox

        tweak_layout.addLayout(rgba_layout)
        self.tweak_container.hide()
        self.main_layout.addWidget(self.tweak_container)

        # 2. Top Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)

        self.swatch = SplitSwatchFrame(self.start_eyedropper)
        self.swatch.setFixedHeight(28)
        self.swatch.setToolTip("Click to pick color")
        top_bar.addWidget(self.swatch, stretch=1)

        self.btn_save = QPushButton("💾 Save")
        self.btn_save.setFixedSize(55, 28)
        self.btn_save.setProperty("class", "action-btn")
        self.btn_save.setToolTip("Save current color to history")
        self.btn_save.clicked.connect(self.on_save_clicked)
        top_bar.addWidget(self.btn_save)

        self.btn_tweak_toggle = QPushButton("⚙️ Tweak")
        self.btn_tweak_toggle.setFixedSize(65, 28)
        self.btn_tweak_toggle.setProperty("class", "action-btn")
        self.btn_tweak_toggle.setCheckable(True)
        self.btn_tweak_toggle.toggled.connect(self.toggle_tweaker)
        top_bar.addWidget(self.btn_tweak_toggle)

        self.main_layout.addLayout(top_bar)

        # 3. Format Dropdown + Copy Output
        format_bar = QHBoxLayout()
        format_bar.setSpacing(6)

        self.combo_format = QComboBox()
        self.combo_format.setFixedHeight(26)
        self.combo_format.addItems(["HEX", "ARGB Hex", "fromARGB", "fromRGBO", "HSL"])
        self.combo_format.currentIndexChanged.connect(self.on_format_changed)
        format_bar.addWidget(self.combo_format)

        self.btn_copy = QPushButton()
        self.btn_copy.setProperty("class", "format-btn")
        self.btn_copy.setFixedHeight(26)
        self.btn_copy.clicked.connect(self.copy_current_code)
        format_bar.addWidget(self.btn_copy, stretch=1)

        self.main_layout.addLayout(format_bar)

        # 4. History Strip
        self.history_layout = QHBoxLayout()
        self.history_layout.setSpacing(4)
        self.main_layout.addLayout(self.history_layout)

        self.setLayout(self.main_layout)
        self.update_color_display()

    def start_eyedropper(self):
        self.overlay = FullscreenOverlay(self)
        self.overlay.show()

    def update_color_from_picker(self, color):
        self.current_color = color
        self.sat_val_widget.set_color(color)
        self.update_color_display()

    def on_box_color_changed(self, color):
        self.current_color = color
        self.update_color_display()

    def on_slider_changed(self):
        r = self.sliders['R'].value()
        g = self.sliders['G'].value()
        b = self.sliders['B'].value()
        a = self.sliders['A'].value()
        
        self.current_color = QColor(r, g, b, a)
        
        self.sat_val_widget.blockSignals(True)
        self.sat_val_widget.set_color(self.current_color)
        self.sat_val_widget.blockSignals(False)
        
        self.update_color_display(sync_controls=False)
        for ch, val in zip(['R', 'G', 'B', 'A'], [r, g, b, a]):
            self.spinboxes[ch].blockSignals(True)
            self.spinboxes[ch].setValue(val)
            self.spinboxes[ch].blockSignals(False)

    def on_spinbox_changed(self):
        r = self.spinboxes['R'].value()
        g = self.spinboxes['G'].value()
        b = self.spinboxes['B'].value()
        a = self.spinboxes['A'].value()

        self.current_color = QColor(r, g, b, a)

        self.sat_val_widget.blockSignals(True)
        self.sat_val_widget.set_color(self.current_color)
        self.sat_val_widget.blockSignals(False)

        self.update_color_display(sync_controls=False)
        for ch, val in zip(['R', 'G', 'B', 'A'], [r, g, b, a]):
            self.sliders[ch].blockSignals(True)
            self.sliders[ch].setValue(val)
            self.sliders[ch].blockSignals(False)

    def on_text_entered(self):
        raw_text = self.txt_input.text().strip()
        parsed_color = parse_hex_color(raw_text)

        if parsed_color.isValid():
            self.update_color_from_picker(parsed_color)

    def on_save_clicked(self):
        self.saved_color = QColor(self.current_color)
        self.add_to_history(self.current_color)
        
        orig_text = self.btn_save.text()
        self.btn_save.setText("✓ Saved")
        QTimer.singleShot(800, lambda: self.btn_save.setText(orig_text))

    def toggle_tweaker(self, checked):
        curr_geom = self.geometry()
        height_diff = 290 if checked else -290

        if checked:
            self.tweak_container.show()
        else:
            self.tweak_container.hide()

        new_y = curr_geom.y() - height_diff
        new_h = curr_geom.height() + height_diff

        self.setGeometry(curr_geom.x(), new_y, 280, new_h)
        self.setFixedSize(280, new_h)
        
        self.update_color_display()

    def add_to_history(self, color):
        r, g, b, a = color.getRgb()
        hex_key = f"#{a:02X}{r:02X}{g:02X}{b:02X}"
        
        # Deduplicate history list
        self.history = [
            c for c in self.history 
            if f"#{c.alpha():02X}{c.red():02X}{c.green():02X}{c.blue():02X}" != hex_key
        ]
        self.history.insert(0, QColor(color))
        self.history = self.history[:8]
        
        self.render_history()
        self.save_settings()

    def render_history(self):
        while self.history_layout.count():
            child = self.history_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for col in self.history:
            frame = SplitSwatchFrame(lambda c=col: self.load_from_history(c))
            frame.setFixedHeight(18)
            frame.set_colors(col, col, False)
            frame.setToolTip(f"#{col.alpha():02X}{col.red():02X}{col.green():02X}{col.blue():02X}")
            self.history_layout.addWidget(frame)

    def load_from_history(self, color):
        self.saved_color = QColor(color)
        self.update_color_from_picker(color)
        self.copy_current_code()

    def update_color_display(self, sync_controls=True):
        r, g, b, a = self.current_color.getRgb()

        if sync_controls:
            for channel, val in zip(['R', 'G', 'B', 'A'], [r, g, b, a]):
                self.sliders[channel].blockSignals(True)
                self.sliders[channel].setValue(val)
                self.sliders[channel].blockSignals(False)

                self.spinboxes[channel].blockSignals(True)
                self.spinboxes[channel].setValue(val)
                self.spinboxes[channel].blockSignals(False)

        is_tweaking = self.btn_tweak_toggle.isChecked()
        self.swatch.set_colors(self.current_color, self.saved_color, is_split=is_tweaking)

        idx = self.combo_format.currentIndex()
        text_val = ""

        if idx == 0:
            text_val = f"#{r:02X}{g:02X}{b:02X}"
        elif idx == 1:
            text_val = f"Color(0x{a:02X}{r:02X}{g:02X}{b:02X})"
        elif idx == 2:
            text_val = f"Color.fromARGB({a}, {r}, {g}, {b})"
        elif idx == 3:
            text_val = f"Color.fromRGBO({r}, {g}, {b}, {a/255:.2f})"
        elif idx == 4:
            h, s, v, _ = self.current_color.getHsvF()
            text_val = f"HSLColor.fromAHSL({a/255:.2f}, {h*360:.0f}, {s:.2f}, {v:.2f})"

        self.btn_copy.setText(text_val)

    def copy_current_code(self):
        text = self.btn_copy.text()
        pyperclip.copy(text)

        self.btn_copy.setText("✓ Copied!")
        QTimer.singleShot(800, self.update_color_display)

    def on_format_changed(self, index):
        self.update_color_display()
        self.save_settings()

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    
                    hex_list = data.get("history", [])
                    self.history = []
                    for h_str in hex_list[:8]:
                        col = parse_hex_color(h_str)
                        if col.isValid():
                            self.history.append(col)
                    
                    if self.history:
                        self.current_color = QColor(self.history[0])
                        self.saved_color = QColor(self.history[0])
                        self.sat_val_widget.set_color(self.current_color)

                    self.combo_format.blockSignals(True)
                    idx = data.get("selected_format_index", 0)
                    if 0 <= idx < self.combo_format.count():
                        self.combo_format.setCurrentIndex(idx)
                    self.combo_format.blockSignals(False)
                    
                    self.render_history()
                    self.update_color_display()
            except Exception:
                pass

    def save_settings(self):
        try:
            formatted_history = []
            for c in self.history[:8]:
                r, g, b, a = c.getRgb()
                formatted_history.append(f"#{a:02X}{r:02X}{g:02X}{b:02X}")

            data = {
                "selected_format_index": self.combo_format.currentIndex(),
                "history": formatted_history
            }
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    icon_path = resource_path("picker.ico")
    icon = QIcon(icon_path)
    app.setWindowIcon(icon)

    picker = FlutterColorPicker(icon)
    picker.show()
    sys.exit(app.exec())