from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QKeySequenceEdit, QDialogButtonBox


class HotkeyConfigDialog(QDialog):
    def __init__(self, current_sequence, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Hotkey")
        self.resize(300, 150)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Press shortcut keys to register:", self))

        self.key_edit = QKeySequenceEdit(QKeySequence(current_sequence), self)
        layout.addWidget(self.key_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

    def get_sequence_str(self):
        return self.key_edit.keySequence().toString()