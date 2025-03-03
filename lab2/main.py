import argparse
import smtplib
import poplib
import imaplib
import email
from email.mime.text import MIMEText
from email.header import decode_header

def send_email(smtp_server, smtp_port, username, password, recipient, subject, body):
    msg = MIMEText(body)
    msg['From'] = username
    msg['To'] = recipient
    msg['Subject'] = subject
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
    server = poplib.POP3_SSL(pop3_server, pop3_port)
    try:
        server.user(username)
        server.pass_(password)
        num_messages = len(server.list()[1])
        print("Łączna liczba wiadomości:", num_messages)
        page_messages = min(page_size, num_messages)
        print(f"Pobieram {page_messages} wiadomości...")
        results = []
        for i in range(1, page_messages + 1):
            resp, lines, octets = server.retr(i)
            msg_content = email.message_from_bytes(b"\n".join(lines))
            raw_subject = msg_content.get("Subject")
            subject = decode_subject(raw_subject)
            print("Wiadomość", i, ":", subject)
            results.append(f"Wiadomość {i}: {subject}")
    finally:
        server.quit()
    return results

def fetch_imap(imap_server, imap_port, username, password, page_size=10):
    with imaplib.IMAP4_SSL(imap_server, imap_port) as mail:
        mail.login(username, password)
        mail.select('inbox')
        typ, data = mail.search(None, 'ALL')
        ids = data[0].split()
        total = len(ids)
        print("Łączna liczba wiadomości:", total)
        page_ids = ids[:page_size]
        print(f"Pobieram {len(page_ids)} wiadomości...")
        results = []
        for num in page_ids:
            typ, data = mail.fetch(num, '(BODY[HEADER.FIELDS (SUBJECT)])')
            if data[0]:
                raw_header = data[0][1].decode()
                subject = decode_subject(raw_header)
                print("Wiadomość:", subject)
                results.append(subject)
        return results

def main():
    # Pobranie interaktywnych danych od użytkownika
    protocol = input("Wybierz protokół (smtp, pop3, imap): ").strip().lower()
    username = input("Podaj nazwę użytkownika: ").strip()
    password = input("Podaj hasło: ").strip()

    # Ustawienia domyślne dla Gmail w zależności od protokołu
    if protocol == 'smtp':
        default_server, default_port = 'smtp.gmail.com', 587
        recipient = input("Podaj odbiorcę: ").strip()
        subject = input("Podaj temat wiadomości: ").strip()
        body = input("Podaj treść wiadomości: ").strip()
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
        send_email(server, port, username, password, recipient, subject, body)
    elif protocol == 'pop3':
        fetch_pop3(server, port, username, password, page_size)
    elif protocol == 'imap':
        fetch_imap(server, port, username, password, page_size)

if __name__ == "__main__":
    main()
