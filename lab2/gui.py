import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QTextEdit, QPushButton, QMessageBox
)
# Import funkcji z main.py
from main import send_email, fetch_pop3, fetch_imap

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mail Client GUI")
        self._init_ui()

    def _init_ui(self):
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        form_layout = QFormLayout()
        self.protocol_cb = QComboBox()
        self.protocol_cb.addItems(["smtp", "pop3", "imap"])
        self.protocol_cb.currentTextChanged.connect(self.on_protocol_changed)
        form_layout.addRow("Protokół:", self.protocol_cb)
        
        self.username_le = QLineEdit()
        form_layout.addRow("E-mail:", self.username_le)
        
        self.password_le = QLineEdit()
        self.password_le.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Hasło:", self.password_le)
        
        self.server_le = QLineEdit()
        form_layout.addRow("Serwer:", self.server_le)
        
        self.port_le = QLineEdit()
        form_layout.addRow("Port:", self.port_le)
        
        # Dodaj nowe pole wyboru liczby wiadomości
        self.page_size_cb = QComboBox()
        self.page_size_cb.addItems(["10", "25", "50"])
        form_layout.addRow("Liczba wiadomości:", self.page_size_cb)
        
        self.recipient_le = QLineEdit()
        form_layout.addRow("Odbiorca:", self.recipient_le)
        
        self.subject_le = QLineEdit()
        form_layout.addRow("Temat:", self.subject_le)
        
        self.body_le = QLineEdit()
        form_layout.addRow("Treść:", self.body_le)
        
        layout.addLayout(form_layout)
        
        self.submit_btn = QPushButton("Wykonaj")
        self.submit_btn.clicked.connect(self.process_mail)
        layout.addWidget(self.submit_btn)
        
        self.output_te = QTextEdit()
        self.output_te.setReadOnly(True)
        layout.addWidget(self.output_te)
        
        self.on_protocol_changed(self.protocol_cb.currentText())

    def on_protocol_changed(self, protocol):
        # Ustawienia domyślne dla Gmail i włączanie/wyłączanie pól dla SMTP
        if protocol == 'smtp':
            self.server_le.setText("smtp.gmail.com")
            self.port_le.setText("587")
            self.recipient_le.setEnabled(True)
            self.subject_le.setEnabled(True)
            self.body_le.setEnabled(True)
            self.page_size_cb.setEnabled(False)
        elif protocol == 'pop3':
            self.server_le.setText("pop.gmail.com")
            self.port_le.setText("995")
            self.recipient_le.setEnabled(False)
            self.subject_le.setEnabled(False)
            self.body_le.setEnabled(False)
            self.page_size_cb.setEnabled(True)
        elif protocol == 'imap':
            self.server_le.setText("imap.gmail.com")
            self.port_le.setText("993")
            self.recipient_le.setEnabled(False)
            self.subject_le.setEnabled(False)
            self.body_le.setEnabled(False)
            self.page_size_cb.setEnabled(True)

    def process_mail(self):
        protocol = self.protocol_cb.currentText()
        username = self.username_le.text().strip()
        password = self.password_le.text().strip()
        server = self.server_le.text().strip()
        try:
            port = int(self.port_le.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Błąd", "Port musi być liczbą.")
            return
        
        try:
            if protocol == 'smtp':
                recipient = self.recipient_le.text().strip()
                subject = self.subject_le.text().strip()
                body = self.body_le.text().strip()
                if not (recipient and subject and body):
                    QMessageBox.warning(self, "Błąd", "Dla SMTP wymagane są odbiorca, temat i treść.")
                    return
                send_email(server, port, username, password, recipient, subject, body)
                self.output_te.append("Email wysłany.")
            elif protocol == 'pop3':
                page_size = int(self.page_size_cb.currentText())
                messages = fetch_pop3(server, port, username, password, page_size)
                self.output_te.append("Pobrano wiadomości POP3:")
                for msg in messages:
                    self.output_te.append(msg)
            elif protocol == 'imap':
                page_size = int(self.page_size_cb.currentText())
                messages = fetch_imap(server, port, username, password, page_size)
                self.output_te.append("Pobrano wiadomości IMAP:")
                for msg in messages:
                    self.output_te.append(msg)
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
