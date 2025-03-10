import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QTextEdit, QPushButton, QMessageBox, QListWidget, QListWidgetItem, QDialog, QDialogButtonBox, QLabel, QScrollArea, QFileDialog, QHBoxLayout, QTabWidget, QCheckBox, QTableWidget, QTableWidgetItem, QSplitter
from main import send_email, fetch_pop3, fetch_imap, get_email_body_pop3, get_email_body_imap
from autoresponder import Autoresponder
from textblob import TextBlob

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mail Client GUI")
        self._init_ui()
        self.current_settings = {}
        self.attachments = []
        self.autoresponder = None

    def _init_ui(self):
        # Podstawowa konfiguracja GUI
        widget = QWidget()
        self.setCentralWidget(widget)
        self.tabs = QTabWidget()
        main_layout = QVBoxLayout()
        widget.setLayout(main_layout)
        main_layout.addWidget(self.tabs)
        mail_tab = QWidget()
        mail_layout = QVBoxLayout()
        mail_tab.setLayout(mail_layout)
        self.tabs.addTab(mail_tab, "Obsługa maili")
        autoresponder_tab = QWidget()
        autoresponder_layout = QVBoxLayout()
        autoresponder_tab.setLayout(autoresponder_layout)
        self.tabs.addTab(autoresponder_tab, "Autoresponder")
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
        self.page_size_cb = QComboBox()
        self.page_size_cb.addItems(["10", "25", "50"])
        form_layout.addRow("Liczba wiadomości:", self.page_size_cb)
        # Konfiguracja pól do wysyłki emaila
        self.send_email_widget = QWidget()
        send_layout = QFormLayout(self.send_email_widget)
        self.recipient_le = QLineEdit()
        send_layout.addRow("Odbiorca:", self.recipient_le)
        self.subject_le = QLineEdit()
        send_layout.addRow("Temat:", self.subject_le)
        self.body_te = QTextEdit()
        send_layout.addRow("Treść:", self.body_te)
        mail_layout.addLayout(form_layout)
        mail_layout.addWidget(self.send_email_widget)
        self.attachments_widget = QWidget()
        attachments_layout = QVBoxLayout()
        self.attachments_widget.setLayout(attachments_layout)
        attachments_label = QLabel("Załączniki:")
        attachments_layout.addWidget(attachments_label)
        attachment_buttons_layout = QHBoxLayout()
        self.add_attachment_btn = QPushButton("Dodaj załącznik")
        self.add_attachment_btn.clicked.connect(self.add_attachment)
        self.remove_attachment_btn = QPushButton("Usuń zaznaczony")
        self.remove_attachment_btn.clicked.connect(self.remove_attachment)
        attachment_buttons_layout.addWidget(self.add_attachment_btn)
        attachment_buttons_layout.addWidget(self.remove_attachment_btn)
        attachments_layout.addLayout(attachment_buttons_layout)
        self.attachments_list = QListWidget()
        attachments_layout.addWidget(self.attachments_list)
        mail_layout.addWidget(self.attachments_widget)
        self.submit_btn = QPushButton("Wykonaj")
        self.submit_btn.clicked.connect(self.process_mail)
        mail_layout.addWidget(self.submit_btn)
        self.mail_list = QTableWidget()
        self.mail_list.setColumnCount(2)
        self.mail_list.setHorizontalHeaderLabels(["Temat", "Sentyment"])
        self.mail_list.cellClicked.connect(self.on_mail_clicked)
        self.output_te = QTextEdit()
        self.output_te.setReadOnly(True)
        splitter = QSplitter()
        splitter.addWidget(self.mail_list)
        splitter.addWidget(self.output_te)
        mail_layout.addWidget(splitter)
        # Ustawienia autorespondera
        self.autoresponder_form = QFormLayout()
        self.autoresponder_enabled_cb = QCheckBox()
        self.autoresponder_enabled_cb.stateChanged.connect(self.on_autoresponder_toggle)
        self.autoresponder_form.addRow("Włącz autoresponder:", self.autoresponder_enabled_cb)
        self.autoresponder_imap_server_le = QLineEdit("imap.gmail.com")
        self.autoresponder_form.addRow("Serwer IMAP:", self.autoresponder_imap_server_le)
        self.autoresponder_imap_port_le = QLineEdit("993")
        self.autoresponder_form.addRow("Port IMAP:", self.autoresponder_imap_port_le)
        self.autoresponder_smtp_server_le = QLineEdit("smtp.gmail.com")
        self.autoresponder_form.addRow("Serwer SMTP:", self.autoresponder_smtp_server_le)
        self.autoresponder_smtp_port_le = QLineEdit("587")
        self.autoresponder_form.addRow("Port SMTP:", self.autoresponder_smtp_port_le)
        self.autoresponder_email_le = QLineEdit()
        self.autoresponder_form.addRow("E-mail:", self.autoresponder_email_le)
        self.autoresponder_password_le = QLineEdit()
        self.autoresponder_password_le.setEchoMode(QLineEdit.Password)
        self.autoresponder_form.addRow("Hasło:", self.autoresponder_password_le)
        self.autoresponder_message_te = QTextEdit()
        self.autoresponder_message_te.setPlaceholderText("Wpisz treść automatycznej odpowiedzi...")
        self.autoresponder_message_te.setText("Dziękuję za Twoją wiadomość!\n\nJestem obecnie niedostępny. Odpowiem najszybciej jak to możliwe.\n\nPozdrawiam,\nAutoresponder")
        self.autoresponder_form.addRow("Treść odpowiedzi:", self.autoresponder_message_te)
        self.autoresponder_interval_le = QLineEdit("60")
        self.autoresponder_form.addRow("Częstotliwość sprawdzania (s):", self.autoresponder_interval_le)
        self.autoresponder_status_label = QLabel("Status: Wyłączony")
        self.autoresponder_form.addRow("Status:", self.autoresponder_status_label)
        self.save_autoresponder_btn = QPushButton("Zapisz ustawienia autorespondera")
        self.save_autoresponder_btn.clicked.connect(self.save_autoresponder_settings)
        autoresponder_layout.addLayout(self.autoresponder_form)
        autoresponder_layout.addWidget(self.save_autoresponder_btn)
        self.on_protocol_changed(self.protocol_cb.currentText())

    def on_protocol_changed(self, protocol):
        if protocol == 'smtp':
            self.server_le.setText("smtp.gmail.com")
            self.port_le.setText("587")
            self.send_email_widget.setVisible(True)
            self.attachments_widget.setVisible(True)
            self.page_size_cb.setEnabled(False)
            self.add_attachment_btn.setEnabled(True)
            self.remove_attachment_btn.setEnabled(True)
            self.attachments_list.setEnabled(True)
        elif protocol in ['pop3', 'imap']:
            default_server = "pop.gmail.com" if protocol == 'pop3' else "imap.gmail.com"
            default_port = "995" if protocol == 'pop3' else "993"
            self.server_le.setText(default_server)
            self.port_le.setText(default_port)
            self.send_email_widget.setVisible(False)
            self.attachments_widget.setVisible(False)
            self.page_size_cb.setEnabled(True)
            self.add_attachment_btn.setEnabled(False)
            self.remove_attachment_btn.setEnabled(False)
            self.attachments_list.setEnabled(False)

    def add_attachment(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Wybierz plik do załączenia")
        if file_path:
            self.attachments.append(file_path)
            self.attachments_list.addItem(os.path.basename(file_path))
            item = self.attachments_list.item(self.attachments_list.count() - 1)
            item.setData(256, file_path)

    def remove_attachment(self):
        selected_items = self.attachments_list.selectedItems()
        if not selected_items:
            return
        selected_item = selected_items[0]
        file_path = selected_item.data(256)
        row = self.attachments_list.row(selected_item)
        self.attachments_list.takeItem(row)
        if file_path in self.attachments:
            self.attachments.remove(file_path)

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
        self.current_settings = {"protocol": protocol, "server": server, "port": port, "username": username, "password": password}
        try:
            if protocol == 'smtp':
                recipient = self.recipient_le.text().strip()
                subject = self.subject_le.text().strip()
                body = self.body_te.toPlainText().strip()
                if not (recipient and subject and body):
                    QMessageBox.warning(self, "Błąd", "Dla SMTP wymagane są odbiorca, temat i treść.")
                    return
                attachments_list = self.attachments if self.attachments else None
                send_email(server, port, username, password, recipient, subject, body, attachments_list)
                self.output_te.append("Email wysłany.")
                if attachments_list:
                    self.output_te.append(f"Wysłano {len(attachments_list)} załączników.")
            elif protocol == 'pop3':
                page_size = int(self.page_size_cb.currentText())
                messages = fetch_pop3(server, port, username, password, page_size)
                self.mail_list.setRowCount(0)
                for msg_id, subject in messages:
                    blob = TextBlob(subject)
                    polarity = blob.sentiment.polarity
                    sentiment = "Pozytywny" if polarity > 0.1 else "Negatywny" if polarity < -0.1 else "Neutralny"
                    row_position = self.mail_list.rowCount()
                    self.mail_list.insertRow(row_position)
                    subject_item = QTableWidgetItem(f"{msg_id}: {subject}")
                    subject_item.setData(256, msg_id)
                    sentiment_item = QTableWidgetItem(sentiment)
                    self.mail_list.setItem(row_position, 0, subject_item)
                    self.mail_list.setItem(row_position, 1, sentiment_item)
                self.output_te.append("Pobrano wiadomości POP3.")
            elif protocol == 'imap':
                page_size = int(self.page_size_cb.currentText())
                messages = fetch_imap(server, port, username, password, page_size)
                self.mail_list.setRowCount(0)
                for msg_id, subject in messages:
                    blob = TextBlob(subject)
                    polarity = blob.sentiment.polarity
                    sentiment = "Pozytywny" if polarity > 0.1 else "Negatywny" if polarity < -0.1 else "Neutralny"
                    row_position = self.mail_list.rowCount()
                    self.mail_list.insertRow(row_position)
                    subject_item = QTableWidgetItem(f"{msg_id}: {subject}")
                    subject_item.setData(256, msg_id)
                    sentiment_item = QTableWidgetItem(sentiment)
                    self.mail_list.setItem(row_position, 0, subject_item)
                    self.mail_list.setItem(row_position, 1, sentiment_item)
                self.output_te.append("Pobrano wiadomości IMAP.")
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd: {e}")

    def on_mail_clicked(self, row, column):
        item = self.mail_list.item(row, 0)
        if not item:
            return
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
            text_edit = QTextEdit()
            text_edit.setPlainText(full_message)
            text_edit.setReadOnly(True)
            dlg_layout.addWidget(text_edit)
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

    def on_autoresponder_toggle(self, state):
        if state:
            if not self.autoresponder:
                self.save_autoresponder_settings()
            if self.autoresponder and self.autoresponder.start():
                self.autoresponder_status_label.setText("Status: Włączony")
                self.output_te.append("Autoresponder został włączony.")
        else:
            if self.autoresponder and self.autoresponder.stop():
                self.autoresponder_status_label.setText("Status: Wyłączony")
                self.output_te.append("Autoresponder został wyłączony.")

    def save_autoresponder_settings(self):
        try:
            imap_server = self.autoresponder_imap_server_le.text()
            imap_port = int(self.autoresponder_imap_port_le.text())
            smtp_server = self.autoresponder_smtp_server_le.text()
            smtp_port = int(self.autoresponder_smtp_port_le.text())
            email = self.autoresponder_email_le.text() or self.username_le.text()
            password = self.autoresponder_password_le.text() or self.password_le.text()
            message = self.autoresponder_message_te.toPlainText()
            try:
                interval = int(self.autoresponder_interval_le.text())
            except ValueError:
                interval = 60
            if not all([imap_server, smtp_server, email, password, message]):
                QMessageBox.warning(self, "Błąd", "Wypełnij wszystkie wymagane pola.")
                return
            if self.autoresponder and self.autoresponder.is_running:
                self.autoresponder.stop()
            self.autoresponder = Autoresponder(
                imap_server=imap_server,
                imap_port=imap_port,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                username=email,
                password=password,
                response_message=message,
                check_interval=interval
            )
            if self.autoresponder_enabled_cb.isChecked():
                self.autoresponder.start()
                self.autoresponder_status_label.setText("Status: Włączony")
                self.output_te.append("Autoresponder został skonfigurowany i włączony.")
            else:
                self.autoresponder_status_label.setText("Status: Wyłączony (skonfigurowany)")
                self.output_te.append("Ustawienia autorespondera zostały zapisane.")
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można zapisać ustawień autorespondera: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
