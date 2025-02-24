import socket
import threading
import os  # nowy import dla obsługi plików

HOST = '127.0.0.1'
PORT = 12345
SHIFT = 1  # zmienna klucz szyfru (przesunięcie)

def caesar_encrypt(text):
    result = ""
    for ch in text:
        if 'a' <= ch <= 'z':
            result += chr((ord(ch) - ord('a') + SHIFT) % 26 + ord('a'))
        elif 'A' <= ch <= 'Z':
            result += chr((ord(ch) - ord('A') + SHIFT) % 26 + ord('A'))
        else:
            result += ch
    return result

def caesar_decrypt(text):
    result = ""
    for ch in text:
        if 'a' <= ch <= 'z':
            result += chr((ord(ch) - ord('a') - SHIFT) % 26 + ord('a'))
        elif 'A' <= ch <= 'Z':
            result += chr((ord(ch) - ord('A') - SHIFT) % 26 + ord('A'))
        else:
            result += ch
    return result

def send_audio(s, filepath):
    try:
        with open(filepath, 'rb') as f:
            file_data = f.read()
        filename = os.path.basename(filepath)
        filesize = len(file_data)
        header = f"AUDIO|{filename}|{filesize}\n"
        s.sendall(header.encode())  # wysyłamy nagłówek (plain text)
        s.sendall(file_data)          # wysyłamy dane audio
        print(f"Wysłano plik audio: {filename}")
    except Exception as e:
        print("Błąd wysyłania pliku audio:", e)

def receive_audio(s, header):
    # header: "AUDIO|<filename>|<filesize>"
    parts = header.split("|")
    if len(parts) != 3:
        return
    filename = parts[1]
    try:
        filesize = int(parts[2].strip())
    except:
        return
    received = b""
    while len(received) < filesize:
        chunk = s.recv(1024)
        if not chunk:
            break
        received += chunk
    outname = "received_" + filename
    with open(outname, "wb") as f:
        f.write(received)
    print(f"Otrzymano plik audio: {filename} (zapisano jako {outname})")

def handle_recv(s):
    while True:
        try:
            data = s.recv(1024)
            if not data:
                break
            try:
                header_check = data.decode(errors="ignore")
            except:
                header_check = ""
            if header_check.startswith("AUDIO|"):
                receive_audio(s, header_check)
                continue
            encrypted = data.decode()
            plaintext = caesar_decrypt(encrypted)
            if plaintext.startswith("Klient"):
                parts = plaintext.split(":", 1)
                sender = parts[0].strip()
                content = parts[1].strip() if len(parts) > 1 else ""
            else:
                sender = "Serwer"
                content = plaintext
            print(f"Otrzymano wiadomość od {sender}:")
            print(f"  Zaszyfrowana: {encrypted}")
            print(f"  Odszyfrowana: {content}")
        except:
            break

def handle_send(s):
    while True:
        try:
            msg = input()
        except (KeyboardInterrupt, EOFError):
            break
        # Jeśli wiadomość zaczyna się od "sendaudio " – wysyłamy plik
        if msg.startswith("sendaudio "):
            filepath = msg.split(" ", 1)[1].strip()
            send_audio(s, filepath)
        else:
            try:
                encrypted_msg = caesar_encrypt(msg)
                s.sendall(encrypted_msg.encode())
            except:
                break

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    print("Połączono z serwerem")
    
    threading.Thread(target=handle_recv, args=(s,), daemon=True).start()
    threading.Thread(target=handle_send, args=(s,), daemon=True).start()
    
    while True:
        pass

if __name__ == '__main__':
    main()
