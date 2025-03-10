import smtplib
import poplib
import imaplib
import email
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import decode_header
import sys
sys.stdout.reconfigure(encoding='utf-8')

def send_email(smtp_server, smtp_port, username, password, recipient, subject, body, attachments=None, read_receipt=True):
    # Przygotowanie wiadomości email z opcjonalnymi załącznikami
    msg = MIMEMultipart()
    msg['From'] = username
    msg['To'] = recipient
    msg['Subject'] = subject
    # Dodane nagłówki potwierdzenia przeczytania, jeśli zaznaczono
    if read_receipt:
        msg['Disposition-Notification-To'] = username
        msg['Return-Receipt-To'] = username
    msg.attach(MIMEText(body))
    if attachments:
        for attachment_path in attachments:
            if os.path.isfile(attachment_path):
                try:
                    with open(attachment_path, 'rb') as attachment_file:
                        part = MIMEApplication(attachment_file.read(), Name=os.path.basename(attachment_path))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                    msg.attach(part)
                except Exception as e:
                    print(f"Nie udało się dołączyć załącznika {attachment_path}: {e}")
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
    print("Email wysłany.")

def decode_subject(subject):
    if not subject:
        return ""
    dh = decode_header(subject)
    subject_parts = []
    for part, encoding in dh:
        if isinstance(part, bytes):
            try:
                subject_parts.append(part.decode(encoding or "utf-8", errors="replace"))
            except Exception:
                subject_parts.append(part.decode("utf-8", errors="replace"))
        else:
            subject_parts.append(part)
    return "".join(subject_parts)

def fetch_pop3(pop3_server, pop3_port, username, password, page_size=10):
    # Pobranie wiadomości poprzez POP3, iterując od najnowszych
    server = poplib.POP3_SSL(pop3_server, pop3_port)
    try:
        server.user(username)
        server.pass_(password)
        num_messages = len(server.list()[1])
        print("Łączna liczba wiadomości:", num_messages)
        start_index = max(1, num_messages - page_size + 1)
        end_index = num_messages + 1
        page_messages = min(page_size, num_messages)
        print(f"Pobieram {page_messages} najnowszych wiadomości...")
        results = []
        for i in range(end_index - 1, start_index - 1, -1):
            resp, lines, octets = server.retr(i)
            if resp.startswith(b'-ERR'):
                raise Exception("Błąd autoryzacji POP3. Upewnij się, że używasz poprawnych danych logowania (dla Gmaila – hasło aplikacji).")
            msg_content = email.message_from_bytes(b"\n".join(lines))
            raw_subject = msg_content.get("Subject")
            subject = decode_subject(raw_subject)
            print("Wiadomość", i, ":", subject)
            results.append((i, subject))
    finally:
        server.quit()
    return results

def fetch_imap(imap_server, imap_port, username, password, page_size=10):
    # Pobieranie wiadomości przez IMAP (od najnowszych)
    with imaplib.IMAP4_SSL(imap_server, imap_port) as mail:
        mail.login(username, password)
        mail.select('inbox')
        typ, data = mail.search(None, 'ALL')
        ids = data[0].split()
        total = len(ids)
        print("Łączna liczba wiadomości:", total)
        ids = list(reversed(ids))
        page_ids = ids[:page_size]
        print(f"Pobieram {len(page_ids)} najnowszych wiadomości...")
        results = []
        for num in page_ids:
            typ, data = mail.fetch(num, '(BODY[HEADER.FIELDS (SUBJECT)])')
            if data[0]:
                raw_header = data[0][1].decode("utf-8", errors="replace")
                subject = decode_subject(raw_header)
                print("Wiadomość:", subject)
                results.append((num.decode() if isinstance(num, bytes) else num, subject))
        return results

def decode_body(payload):
    for encoding in ["utf-8", "cp1250", "iso-8859-2"]:
        try:
            return payload.decode(encoding, errors="replace")
        except Exception:
            continue
    return payload.decode("utf-8", errors="replace")

def decode_payload(part):
    payload = part.get_payload(decode=True)
    charset = part.get_content_charset()
    if charset:
        try:
            return payload.decode(charset, errors="replace")
        except Exception:
            pass
    for encoding in ["utf-8", "cp1250", "iso-8859-2"]:
        try:
            return payload.decode(encoding, errors="replace")
        except Exception:
            continue
    return payload.decode("utf-8", errors="replace")

def get_email_body_pop3(pop3_server, pop3_port, username, password, msg_index):
    # Pobranie treści wiadomości POP3
    server = poplib.POP3_SSL(pop3_server, pop3_port)
    try:
        server.user(username)
        server.pass_(password)
        resp, lines, octets = server.retr(msg_index)
        msg_content = email.message_from_bytes(b"\n".join(lines))
        body = ""
        if msg_content.is_multipart():
            for part in msg_content.walk():
                if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                    body = decode_payload(part)
                    break
        else:
            body = decode_payload(msg_content)
    finally:
        server.quit()
    return body

def get_email_body_imap(imap_server, imap_port, username, password, msg_id):
    # Pobranie treści wiadomości IMAP
    with imaplib.IMAP4_SSL(imap_server, imap_port) as mail:
        mail.login(username, password)
        mail.select('inbox')
        typ, data = mail.fetch(msg_id, '(RFC822)')
        raw_email = data[0][1]
        msg_content = email.message_from_bytes(raw_email)
        body = ""
        if msg_content.is_multipart():
            for part in msg_content.walk():
                if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                    body = decode_payload(part)
                    break
        else:
            body = decode_payload(msg_content)
    return body

def main():
    # Funkcja główna: wybór protokołu i wykonanie akcji
    protocol = input("Wybierz protokół (smtp, pop3, imap): ").strip().lower()
    username = input("Podaj nazwę użytkownika: ").strip()
    password = input("Podaj hasło: ").strip()
    if protocol == 'smtp':
        default_server, default_port = 'smtp.gmail.com', 587
        recipient = input("Podaj odbiorcę: ").strip()
        subject = input("Podaj temat wiadomości: ").strip()
        body = input("Podaj treść wiadomości: ").strip()
        attachments = []
        while True:
            attachment = input("Podaj ścieżkę do załącznika (lub pozostaw puste, aby zakończyć): ").strip()
            if not attachment:
                break
            if os.path.isfile(attachment):
                attachments.append(attachment)
            else:
                print(f"Plik {attachment} nie istnieje.")
    elif protocol == 'pop3':
        default_server, default_port = 'pop.gmail.com', 995
    elif protocol == 'imap':
        default_server, default_port = 'imap.gmail.com', 993
    else:
        print("Nieznany protokół.")
        return
    server = input(f"Podaj adres serwera (domyślnie: {default_server}): ").strip() or default_server
    port_input = input(f"Podaj port serwera (domyślnie: {default_port}): ").strip()
    port = int(port_input) if port_input else default_port
    if protocol in ['pop3', 'imap']:
        page_size_input = input("Podaj liczbę wiadomości do pobrania (10, 25, 50, domyślnie: 10): ").strip()
        page_size = int(page_size_input) if page_size_input in ['10','25','50'] else 10
    if protocol == 'smtp':
        send_email(server, port, username, password, recipient, subject, body, attachments if attachments else None)
    elif protocol == 'pop3':
        fetch_pop3(server, port, username, password, page_size)
    elif protocol == 'imap':
        fetch_imap(server, port, username, password, page_size)

if __name__ == "__main__":
    main()
