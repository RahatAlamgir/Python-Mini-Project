import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from config import BASE_DIR
from main_window import OverlayImageViewer

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