import datetime
from PyQt5.QtWidgets import QTextEdit

class Logger:
    def __init__(self, max_lines=100):
        self.max_lines = max_lines
        self.lines = []
        self.text_edit = None

    def set_text_edit(self, text_edit: QTextEdit):
        self.text_edit = text_edit
        self._update_text_edit()

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        self.lines.append(log_message)
        if len(self.lines) > self.max_lines:
            self.lines = self.lines[-self.max_lines:]
        self._update_text_edit()

    def _update_text_edit(self):
        if self.text_edit:
            self.text_edit.setPlainText("\n".join(self.lines))