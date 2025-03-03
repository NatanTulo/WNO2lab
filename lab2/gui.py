import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QTextEdit, QPushButton, QMessageBox,
    QListWidget, QListWidgetItem, QDialog, QDialogButtonBox, QLabel, 
    QScrollArea, QFileDialog, QHBoxLayout, QTabWidget, QCheckBox
)
# Import funkcji z main.py
from main import send_email, fetch_pop3, fetch_imap, get_email_body_pop3, get_email_body_imap
# Import autorespondera
from autoresponder import Autoresponder

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mail Client GUI")
        self._init_ui()
        # Przechowujemy szczegóły sesji mailowej dla późniejszego pobierania wiadomości
        self.current_settings = {}
        # Lista załączników
        self.attachments = []
        # Autoresponder
        self.autoresponder = None

    def _init_ui(self):
        widget = QWidget()
        self.setCentralWidget(widget)
        
        # Zakładki główne
        self.tabs = QTabWidget()
        main_layout = QVBoxLayout()
        widget.setLayout(main_layout)
        main_layout.addWidget(self.tabs)
        
        # Zakładka podstawowa do obsługi maili
        mail_tab = QWidget()
        mail_layout = QVBoxLayout()
        mail_tab.setLayout(mail_layout)
        self.tabs.addTab(mail_tab, "Obsługa maili")
        
        # Zakładka autorespondera
        autoresponder_tab = QWidget()
        autoresponder_layout = QVBoxLayout()
        autoresponder_tab.setLayout(autoresponder_layout)
        self.tabs.addTab(autoresponder_tab, "Autoresponder")
        
        # Układamy kontrolki na zakładce mail_tab
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
        
        self.body_te = QTextEdit()  # Zmiana z QLineEdit na QTextEdit dla dłuższych wiadomości
        form_layout.addRow("Treść:", self.body_te)
        
        mail_layout.addLayout(form_layout)
        
        # Sekcja załączników
        attachments_layout = QVBoxLayout()
        attachments_label = QLabel("Załączniki:")
        attachments_layout.addWidget(attachments_label)
        
        # Przyciski do obsługi załączników
        attachment_buttons_layout = QHBoxLayout()
        self.add_attachment_btn = QPushButton("Dodaj załącznik")
        self.add_attachment_btn.clicked.connect(self.add_attachment)
        self.remove_attachment_btn = QPushButton("Usuń zaznaczony")
        self.remove_attachment_btn.clicked.connect(self.remove_attachment)
        attachment_buttons_layout.addWidget(self.add_attachment_btn)
        attachment_buttons_layout.addWidget(self.remove_attachment_btn)
        attachments_layout.addLayout(attachment_buttons_layout)
        
        # Lista załączników
        self.attachments_list = QListWidget()
        attachments_layout.addWidget(self.attachments_list)
        mail_layout.addLayout(attachments_layout)
        
        self.submit_btn = QPushButton("Wykonaj")
        self.submit_btn.clicked.connect(self.process_mail)
        mail_layout.addWidget(self.submit_btn)
        
        # Dodajemy listę maili
        self.mail_list = QListWidget()
        self.mail_list.itemClicked.connect(self.on_mail_clicked)
        mail_layout.addWidget(self.mail_list)
        
        self.output_te = QTextEdit()
        self.output_te.setReadOnly(True)
        mail_layout.addWidget(self.output_te)
        
        # Układamy kontrolki na zakładce autoresponder_tab
        self.autoresponder_form = QFormLayout()
        
        # CheckBox do włączania/wyłączania autorespondera
        self.autoresponder_enabled_cb = QCheckBox()
        self.autoresponder_enabled_cb.stateChanged.connect(self.on_autoresponder_toggle)
        self.autoresponder_form.addRow("Włącz autoresponder:", self.autoresponder_enabled_cb)
        
        # Ustawienia IMAP dla autorespondera (może być inne niż główne)
        self.autoresponder_imap_server_le = QLineEdit("imap.gmail.com")
        self.autoresponder_form.addRow("Serwer IMAP:", self.autoresponder_imap_server_le)
        
        self.autoresponder_imap_port_le = QLineEdit("993")
        self.autoresponder_form.addRow("Port IMAP:", self.autoresponder_imap_port_le)
        
        # Ustawienia SMTP dla autorespondera
        self.autoresponder_smtp_server_le = QLineEdit("smtp.gmail.com")
        self.autoresponder_form.addRow("Serwer SMTP:", self.autoresponder_smtp_server_le)
        
        self.autoresponder_smtp_port_le = QLineEdit("587")
        self.autoresponder_form.addRow("Port SMTP:", self.autoresponder_smtp_port_le)
        
        # Pole na email i hasło (mogą być te same co w głównej zakładce)
        self.autoresponder_email_le = QLineEdit()
        self.autoresponder_form.addRow("E-mail:", self.autoresponder_email_le)
        
        self.autoresponder_password_le = QLineEdit()
        self.autoresponder_password_le.setEchoMode(QLineEdit.Password)
        self.autoresponder_form.addRow("Hasło:", self.autoresponder_password_le)
        
        # Treść automatycznej odpowiedzi
        self.autoresponder_message_te = QTextEdit()
        self.autoresponder_message_te.setPlaceholderText("Wpisz treść automatycznej odpowiedzi...")
        self.autoresponder_message_te.setText("Dziękuję za Twoją wiadomość!\n\nJestem obecnie niedostępny. Odpowiem najszybciej jak to możliwe.\n\nPozdrawiam,\nAutoresponder")
        self.autoresponder_form.addRow("Treść odpowiedzi:", self.autoresponder_message_te)
        
        # Częstotliwość sprawdzania nowych wiadomości (w sekundach)
        self.autoresponder_interval_le = QLineEdit("60")
        self.autoresponder_form.addRow("Częstotliwość sprawdzania (s):", self.autoresponder_interval_le)
        
        # Status autorespondera
        self.autoresponder_status_label = QLabel("Status: Wyłączony")
        self.autoresponder_form.addRow("Status:", self.autoresponder_status_label)
        
        # Przycisk do zapisywania ustawień autorespondera
        self.save_autoresponder_btn = QPushButton("Zapisz ustawienia autorespondera")
        self.save_autoresponder_btn.clicked.connect(self.save_autoresponder_settings)
        
        autoresponder_layout.addLayout(self.autoresponder_form)
        autoresponder_layout.addWidget(self.save_autoresponder_btn)
        
        # Domyślne ustawienia
        self.on_protocol_changed(self.protocol_cb.currentText())

    def on_protocol_changed(self, protocol):
        # Ustawienia domyślne dla Gmail oraz aktywacja pól
        if protocol == 'smtp':
            self.server_le.setText("smtp.gmail.com")
            self.port_le.setText("587")
            self.recipient_le.setEnabled(True)
            self.subject_le.setEnabled(True)
            self.body_te.setEnabled(True)
            self.page_size_cb.setEnabled(False)
            self.add_attachment_btn.setEnabled(True)
            self.remove_attachment_btn.setEnabled(True)
            self.attachments_list.setEnabled(True)
        elif protocol == 'pop3':
            self.server_le.setText("pop.gmail.com")
            self.port_le.setText("995")
            self.recipient_le.setEnabled(False)
            self.subject_le.setEnabled(False)
            self.body_te.setEnabled(False)
            self.page_size_cb.setEnabled(True)
            self.add_attachment_btn.setEnabled(False)
            self.remove_attachment_btn.setEnabled(False)
            self.attachments_list.setEnabled(False)
        elif protocol == 'imap':
            self.server_le.setText("imap.gmail.com")
            self.port_le.setText("993")
            self.recipient_le.setEnabled(False)
            self.subject_le.setEnabled(False)
            self.body_te.setEnabled(False)
            self.page_size_cb.setEnabled(True)
            self.add_attachment_btn.setEnabled(False)
            self.remove_attachment_btn.setEnabled(False)
            self.attachments_list.setEnabled(False)

    def add_attachment(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Wybierz plik do załączenia")
        if file_path:
            # Dodaj ścieżkę do listy załączników
            self.attachments.append(file_path)
            # Dodaj nazwę pliku do listy w GUI
            self.attachments_list.addItem(os.path.basename(file_path))
            # Przechowaj pełną ścieżkę w danych elementu
            item = self.attachments_list.item(self.attachments_list.count() - 1)
            item.setData(256, file_path)

    def remove_attachment(self):
        selected_items = self.attachments_list.selectedItems()
        if not selected_items:
            return
            
        selected_item = selected_items[0]
        file_path = selected_item.data(256)
        row = self.attachments_list.row(selected_item)
        
        # Usuń z listy GUI
        self.attachments_list.takeItem(row)
        
        # Usuń z listy załączników
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
                body = self.body_te.toPlainText().strip()  # Używamy toPlainText dla QTextEdit
                if not (recipient and subject and body):
                    QMessageBox.warning(self, "Błąd", "Dla SMTP wymagane są odbiorca, temat i treść.")
                    return
                
                # Pobieramy listę załączników
                attachments_list = self.attachments if self.attachments else None
                
                send_email(server, port, username, password, recipient, subject, body, attachments_list)
                self.output_te.append("Email wysłany.")
                if attachments_list:
                    self.output_te.append(f"Wysłano {len(attachments_list)} załączników.")
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
        
    def on_autoresponder_toggle(self, state):
        """Obsługuje włączanie/wyłączanie autorespondera"""
        if state:
            # Jeśli autoresponder nie istnieje, utwórz go
            if not self.autoresponder:
                self.save_autoresponder_settings()
            
            # Włącz autoresponder
            if self.autoresponder and self.autoresponder.start():
                self.autoresponder_status_label.setText("Status: Włączony")
                self.output_te.append("Autoresponder został włączony.")
                
        else:
            # Wyłącz autoresponder
            if self.autoresponder and self.autoresponder.stop():
                self.autoresponder_status_label.setText("Status: Wyłączony")
                self.output_te.append("Autoresponder został wyłączony.")
    
    def save_autoresponder_settings(self):
        """Zapisuje ustawienia autorespondera"""
        try:
            # Pobieranie ustawień z formularza
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
                interval = 60  # Domyślnie 60 sekund
            
            # Walidacja danych
            if not all([imap_server, smtp_server, email, password, message]):
                QMessageBox.warning(self, "Błąd", "Wypełnij wszystkie wymagane pola.")
                return
            
            # Jeśli autoresponder już działa, zatrzymaj go
            if self.autoresponder and self.autoresponder.is_running:
                self.autoresponder.stop()
            
            # Tworzenie nowego autorespondera
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
            
            # Jeśli checkbox jest zaznaczony, uruchom autoresponder
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
