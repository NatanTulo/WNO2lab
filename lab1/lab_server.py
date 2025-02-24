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
            try:
                header_candidate = data.decode(errors="ignore")
            except:
                header_candidate = ""
            if header_candidate.startswith("AUDIO|"):
                # Wysyłamy nagłówek do pozostałych klientów
                broadcast(data, conn)
                parts = header_candidate.split("|")
                if len(parts) >= 3:
                    try:
                        filesize = int(parts[2].strip())
                    except:
                        filesize = 0
                else:
                    filesize = 0
                remaining = filesize
                while remaining > 0:
                    chunk = conn.recv(min(1024, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    broadcast(chunk, conn)
                continue
            print(f"Odebrano od {addr}:")
            print(f"  Zaszyfrowana: {data.decode()}")
            decrypted = caesar_decrypt(data.decode())
            if decrypted.startswith("Klient"):
                parts = decrypted.split(":", 1)
                content = parts[1].strip() if len(parts) > 1 else ""
            else:
                content = decrypted
            print(f"  Odszyfrowana: {content}")
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
