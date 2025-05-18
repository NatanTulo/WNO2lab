import socket
import threading

HOST = '127.0.0.1'
PORT = 12345
SHIFT = 1 
client_counter = 1 

clients = []
client_nicknames = {}
clients_lock = threading.Lock()

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
    global client_counter
    with clients_lock:
        client_nicknames[conn] = str(client_counter)
        default_nick = client_nicknames[conn]
        client_counter += 1
        clients.append(conn)
    print(f"Połączono z ({addr[0]}, {default_nick})") 
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
            decrypted = caesar_decrypt(data.decode())
            
            if decrypted.startswith("NICK|"):
                newnick = decrypted.split("|", 1)[1].strip()
                with clients_lock:
                    client_nicknames[conn] = newnick
                print(f"Zaktualizowano nazwę klienta na {newnick}")
                continue

            if decrypted.startswith("PRIVATE|"):
                parts = decrypted.split("|", 2)
                if len(parts) < 3:
                    continue
                target_nick = parts[1].strip()
                msg_content = parts[2].strip()
                sent = False
                with clients_lock:
                    for client in clients:
                        if client != conn and client_nicknames.get(client, "") == target_nick:
                            private_msg = f"Prywatna wiadomość od {client_nicknames[conn]}: {msg_content}"
                            encrypted_private = caesar_encrypt(private_msg)
                            try:
                                client.sendall(encrypted_private.encode())
                            except:
                                pass
                            sent = True
                    if not sent:
                        print(f"Nie znaleziono klienta o nazwie {target_nick}")
                continue

            print(f"Otrzymano wiadomość od Klient {client_nicknames[conn]}:")
            print(f"  Zaszyfrowana: {data.decode()}")
            if decrypted.startswith("Klient"):
                parts = decrypted.split(":", 1)
                content = parts[1].strip() if len(parts) > 1 else ""
            else:
                content = decrypted
            print(f"  Odszyfrowana: {content}")
            message = f"Klient {client_nicknames[conn]}: {decrypted}"
            encrypted_message = caesar_encrypt(message)
            broadcast(encrypted_message.encode(), conn)
    except:
        pass
    finally:
        with clients_lock:
            if conn in clients:
                clients.remove(conn)
                client_nicknames.pop(conn, None)
        conn.close()
        print("Rozłączono", addr)

def handle_server_send():
    while True:
        try:
            msg = input()
        except (KeyboardInterrupt, EOFError):
            break
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
    
    threading.Thread(target=handle_server_send).start()
    
    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()
    except KeyboardInterrupt:
        print("\nPrzerywanie działania serwera...")
    finally:
        s.close()

if __name__ == '__main__':
    main()
