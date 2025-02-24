import socket
import threading

HOST = '127.0.0.1'
PORT = 12345
SHIFT = 1  # zmienna klucz szyfru (przesunięcie)

# Dodajemy listę klientów oraz blokadę do synchronizacji
clients = []
clients_lock = threading.Lock()

# Nowe funkcje szyfrujące (Caesar +1)
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

def broadcast(msg, sender_conn):
    with clients_lock:
        for client in clients:
            if client is not sender_conn:
                try:
                    client.sendall(msg)
                except:
                    pass

def handle_client(conn, addr):
    print("Połączono z", addr)
    with clients_lock:
        clients.append(conn)
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            encrypted_received = data.decode()
            print(f"Odebrano od {addr}:")
            print(f"  Zaszyfrowana: {encrypted_received}")
            decrypted = caesar_decrypt(encrypted_received)
            # Jeśli odszyfrowana wiadomość zaczyna się od "Klient", usuwamy nagłówek
            if decrypted.startswith("Klient"):
                parts = decrypted.split(":", 1)
                content = parts[1].strip() if len(parts) > 1 else ""
            else:
                content = decrypted
            print(f"  Odszyfrowana: {content}")
            # Przygotowujemy pełną wiadomość z nagłówkiem dla broadcastu
            message = f"Klient {addr}: " + decrypted
            encrypted_message = caesar_encrypt(message)
            broadcast(encrypted_message.encode(), conn)
    except:
        pass
    finally:
        with clients_lock:
            if conn in clients:
                clients.remove(conn)
        conn.close()
        print("Rozłączono", addr)

def handle_server_send():
    while True:
        try:
            msg = input()
        except (KeyboardInterrupt, EOFError):  # obsługa wyjątków, aby uniknąć błędów przy ctrl+c
            break
        # Szyfrujemy wiadomość serwera przed wysłaniem
        encrypted_msg = caesar_encrypt(msg)
        with clients_lock:
            for client in clients:
                try:
                    client.sendall(encrypted_msg.encode())
                except:
                    pass

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    print("Serwer nasłuchuje...")
    
    # Uruchamiamy wątek do wysyłania danych od serwera
    threading.Thread(target=handle_server_send).start()
    
    try:
        # Przyjmujemy wiele połączeń w pętli
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()
    except KeyboardInterrupt:
        print("\nPrzerywanie działania serwera...")
    finally:
        s.close()

if __name__ == '__main__':
    main()
