import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QTextEdit, QPushButton, QMessageBox,
    QListWidget, QListWidgetItem, QDialog, QDialogButtonBox, QLabel, QScrollArea
)
# Import funkcji z main.py
from main import send_email, fetch_pop3, fetch_imap, get_email_body_pop3, get_email_body_imap

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mail Client GUI")
        self._init_ui()
        # Przechowujemy szczegóły sesji mailowej dla późniejszego pobierania wiadomości
        self.current_settings = {}

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
        
        # Pole wyboru liczby wiadomości
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
        
        # Dodajemy listę maili
        self.mail_list = QListWidget()
        self.mail_list.itemClicked.connect(self.on_mail_clicked)
        layout.addWidget(self.mail_list)
        
        self.output_te = QTextEdit()
        self.output_te.setReadOnly(True)
        layout.addWidget(self.output_te)
        
        self.on_protocol_changed(self.protocol_cb.currentText())

    def on_protocol_changed(self, protocol):
        # Ustawienia domyślne dla Gmail oraz aktywacja pól
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
        
        # Zapisujemy ustawienia dla późniejszego pobierania pełnej treści
        self.current_settings = {
            "protocol": protocol,
            "server": server,
            "port": port,
            "username": username,
            "password": password
        }
        
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
                self.mail_list.clear()
                for msg_id, subject in messages:
                    item = QListWidgetItem(f"{msg_id}: {subject}")
                    # Przechowujemy id w danych elementu
                    item.setData(256, msg_id)
                    self.mail_list.addItem(item)
                self.output_te.append("Pobrano wiadomości POP3.")
            elif protocol == 'imap':
                page_size = int(self.page_size_cb.currentText())
                messages = fetch_imap(server, port, username, password, page_size)
                self.mail_list.clear()
                for msg_id, subject in messages:
                    item = QListWidgetItem(f"{msg_id}: {subject}")
                    item.setData(256, msg_id)
                    self.mail_list.addItem(item)
                self.output_te.append("Pobrano wiadomości IMAP.")
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd: {e}")

    def on_mail_clicked(self, item):
        msg_id = item.data(256)
        protocol = self.current_settings.get("protocol")
        server = self.current_settings.get("server")
        port = self.current_settings.get("port")
        username = self.current_settings.get("username")
        password = self.current_settings.get("password")
        try:
            if protocol == "pop3":
                full_message = get_email_body_pop3(server, port, username, password, int(msg_id))
            elif protocol == "imap":
                full_message = get_email_body_imap(server, port, username, password, msg_id)
            else:
                return
            dlg = QDialog(self)
            dlg.setWindowTitle("Treść wiadomości")
            dlg_layout = QVBoxLayout(dlg)
            # Używamy QTextEdit, aby umożliwić kopiowanie
            text_edit = QTextEdit()
            text_edit.setPlainText(full_message)
            text_edit.setReadOnly(True)
            dlg_layout.addWidget(text_edit)
            # Dodajemy przycisk kopiowania
            copy_btn = QPushButton("Kopiuj treść")
            copy_btn.clicked.connect(lambda: self.copy_to_clipboard(full_message))
            dlg_layout.addWidget(copy_btn)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok)
            buttons.accepted.connect(dlg.accept)
            dlg_layout.addWidget(buttons)
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można pobrać treści: {e}")

    def copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
