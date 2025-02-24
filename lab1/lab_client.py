import socket
import threading

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

def handle_recv(s):
    while True:
        try:
            data = s.recv(1024)
            if not data:
                break
            encrypted = data.decode()
            plaintext = caesar_decrypt(encrypted)
            # Ustalamy nadawcę oraz treść wiadomości
            if plaintext.startswith("Klient"):
                parts = plaintext.split(":", 1)
                sender = parts[0].strip()
                content = parts[1].strip() if len(parts) > 1 else ""
                pos = encrypted.find(":")
                if pos != -1:
                    encrypted_content = encrypted[pos+1:].strip()
                else:
                    encrypted_content = encrypted
            else:
                sender = "Serwer"
                content = plaintext
                encrypted_content = encrypted
            # Drukujemy nagłówek oraz szczegóły wiadomości
            print(f"Otrzymano wiadomość od {sender}:")
            print(f"  Zaszyfrowana: {encrypted_content}")
            print(f"  Odszyfrowana: {content}")
        except:
            break

def handle_send(s):
    while True:
        try:
            msg = input()
        except (KeyboardInterrupt, EOFError):
            break
        try:
            # Szyfrujemy wiadomość przed wysłaniem
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
