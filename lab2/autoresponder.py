import imaplib
import email
import time
import threading
import logging
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='autoresponder.log',
                    filemode='a')
logger = logging.getLogger('autoresponder')

# Dodanie logowania do konsoli
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class Autoresponder:
    def __init__(self, imap_server, imap_port, smtp_server, smtp_port, 
                 username, password, response_message, check_interval=60):
        """
        Inicjalizacja autorespondera
        
        Args:
            imap_server (str): Adres serwera IMAP
            imap_port (int): Port serwera IMAP
            smtp_server (str): Adres serwera SMTP
            smtp_port (int): Port serwera SMTP
            username (str): Adres email użytkownika
            password (str): Hasło
            response_message (str): Treść automatycznej odpowiedzi
            check_interval (int): Częstotliwość sprawdzania nowych maili (w sekundach)
        """
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.response_message = response_message
        self.check_interval = check_interval
        self.is_running = False
        self.processed_ids = set()  # Zbiór ID przetworzonych wiadomości
        self.thread = None
        # Czas uruchomienia - będziemy reagować tylko na wiadomości wysłane po tym czasie
        self.start_time = None
        logger.info(f"Autoresponder zainicjalizowany dla adresu {username}, serwer IMAP: {imap_server}:{imap_port}, serwer SMTP: {smtp_server}:{smtp_port}")
    
    def start(self):
        """Uruchamia autoresponder w osobnym wątku"""
        if not self.is_running:
            logger.info("Próba uruchomienia autorespondera...")
            self.is_running = True
            # Zapisz czas uruchomienia
            self.start_time = datetime.now()
            logger.info(f"Autoresponder będzie reagował na wiadomości wysłane po: {self.start_time}")
            print(f"[Autoresponder] Uruchomiono {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} - będę reagować tylko na nowe wiadomości")
            
            self.thread = threading.Thread(target=self._run)
            self.thread.daemon = True
            self.thread.start()
            logger.info(f"Autoresponder uruchomiony w wątku {self.thread.name}")
            print(f"Autoresponder uruchomiony! Sprawdzanie poczty co {self.check_interval} sekund.")
            return True
        logger.warning("Próba uruchomienia już działającego autorespondera")
        return False
    
    def stop(self):
        """Zatrzymuje autoresponder"""
        if self.is_running:
            logger.info("Zatrzymywanie autorespondera...")
            self.is_running = False
            if self.thread:
                logger.info(f"Oczekiwanie na zakończenie wątku {self.thread.name}")
                # Uwaga: nie możemy dołączyć wątku w GUI, tylko sygnalizujemy mu zakończenie
            logger.info("Autoresponder zatrzymany")
            print("Autoresponder zatrzymany.")
            return True
        logger.warning("Próba zatrzymania już zatrzymanego autorespondera")
        return False
    
    def _run(self):
        """Główna pętla autorespondera"""
        logger.info("Rozpoczęcie głównej pętli autorespondera")
        print(f"[Autoresponder] Rozpoczęcie sprawdzania nowych wiadomości co {self.check_interval} sekund")
        
        while self.is_running:
            try:
                logger.info("Sprawdzanie nowych wiadomości...")
                print(f"[Autoresponder] Sprawdzanie nowych wiadomości... ({datetime.now().strftime('%H:%M:%S')})")
                
                # Pobieranie nowych wiadomości
                new_messages = self._fetch_new_messages()
                
                if new_messages:
                    logger.info(f"Znaleziono {len(new_messages)} nowych wiadomości")
                    print(f"[Autoresponder] Znaleziono {len(new_messages)} nowych wiadomości")
                    
                    # Odpowiadanie na nowe wiadomości
                    for msg_id, msg_data in new_messages:
                        if msg_id not in self.processed_ids:
                            logger.info(f"Przetwarzanie wiadomości o ID: {msg_id}")
                            print(f"[Autoresponder] Przetwarzanie wiadomości o ID: {msg_id}")
                            self._process_message(msg_id, msg_data)
                            self.processed_ids.add(msg_id)
                            logger.info(f"Wiadomość {msg_id} przetworzona i dodana do przetworzonych")
                        else:
                            logger.info(f"Wiadomość {msg_id} już była przetworzona, pomijanie")
                else:
                    logger.info("Brak nowych wiadomości")
                    print("[Autoresponder] Brak nowych wiadomości")
                    
            except Exception as e:
                error_msg = f"Błąd w pętli autorespondera: {e}"
                logger.error(error_msg)
                print(f"[Autoresponder] BŁĄD: {error_msg}")
                import traceback
                logger.error(traceback.format_exc())
                print("[Autoresponder] Szczegółowy komunikat błędu zapisany do logu")
            
            # Czekanie na kolejne sprawdzenie
            logger.debug(f"Oczekiwanie {self.check_interval} sekund przed następnym sprawdzeniem")
            print(f"[Autoresponder] Oczekiwanie {self.check_interval} sekund przed następnym sprawdzeniem")
            time.sleep(self.check_interval)
    
    def _fetch_new_messages(self):
        """
        Pobiera nowe wiadomości z serwera IMAP
        
        Returns:
            list: Lista krotek (message_id, message_data)
        """
        try:
            logger.info(f"Łączenie z serwerem IMAP {self.imap_server}:{self.imap_port}")
            print(f"[Autoresponder] Łączenie z serwerem IMAP {self.imap_server}:{self.imap_port}")
            
            # Łączenie z serwerem IMAP
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            try:
                logger.info("Łączenie udane, próba logowania")
                mail.login(self.username, self.password)
                logger.info("Logowanie udane, wybór skrzynki odbiorczej")
                mail.select('inbox', readonly=True)  # Używamy readonly=True, aby zapobiec oznaczaniu jako przeczytane
                
                # Ustal kryterium wyszukiwania, uwzględniając datę uruchomienia
                if self.start_time:
                    search_criteria = f'(UNSEEN SINCE "{self.start_time.strftime("%d-%b-%Y")}")'
                else:
                    search_criteria = 'UNSEEN'
                logger.info(f"Wyszukiwanie nieprzeczytanych wiadomości z kryterium: {search_criteria}")
                typ, data = mail.search(None, search_criteria)
                if typ != 'OK':
                    logger.warning(f"Nie można wyszukać nowych wiadomości: typ={typ}")
                    print(f"[Autoresponder] Ostrzeżenie: Nie można wyszukać nowych wiadomości: typ={typ}")
                    return []
                
                msg_ids = data[0].split()
                # Ograniczenie do 10 ostatnich wiadomości (najświeższych)
                msg_ids = msg_ids[-10:]
                logger.info(f"Znaleziono {len(msg_ids)} nieprzeczytanych wiadomości (ograniczenie do 10 ostatnich)")
                print(f"[Autoresponder] Znaleziono {len(msg_ids)} nieprzeczytanych wiadomości (10 ostatnich)")
                messages = []
                for msg_id in msg_ids:
                    try:
                        uid = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                        # Próba pobrania nagłówka Date – UID
                        try:
                            typ, header_data = mail.uid('fetch', uid, '(BODY[HEADER.FIELDS (Date)])')
                        except Exception as e_uid:
                            logger.warning(f"UID fetch nie powiodło się dla {uid}: {e_uid}. Próbuję fetch zamiast UID.")
                            typ, header_data = mail.fetch(uid, '(BODY[HEADER.FIELDS (Date)])')
                        date_header = ""
                        if typ == 'OK' and header_data and header_data[0]:
                            date_header_bytes = header_data[0][1]
                            date_header = date_header_bytes.decode(errors="replace").replace("Date:", "").strip() if date_header_bytes else ""
                        # Jeśli nie udało się pobrać nagłówka, pobierz pełną wiadomość (również z fallback)
                        if not date_header:
                            logger.warning(f"Nie udało się pobrać nagłówka daty dla wiadomości {uid}, pobieram pełną treść")
                            try:
                                typ_full, full_msg_data = mail.uid('fetch', uid, '(RFC822.PEEK)')
                            except Exception as e_uid_full:
                                logger.warning(f"UID fetch pełnej wiadomości nie powiodło się dla {uid}: {e_uid_full}. Próbuję fetch zamiast UID.")
                                typ_full, full_msg_data = mail.fetch(uid, '(RFC822.PEEK)')
                            if typ_full == 'OK' and full_msg_data and full_msg_data[0]:
                                full_msg = email.message_from_bytes(full_msg_data[0][1])
                                date_header = full_msg.get("Date", "").strip()
                            else:
                                logger.warning(f"Nie udało się pobrać pełnej wiadomości {uid}")
                                continue
                        message_date = None
                        if date_header:
                            try:
                                message_date = email.utils.parsedate_to_datetime(date_header)
                            except Exception as dt_err:
                                logger.warning(f"Nie udało się sparsować daty dla wiadomości {uid}: {dt_err}")
                                continue
                        logger.info(f"Pobieranie wiadomości o UID: {uid}")
                        try:
                            typ, msg_data = mail.uid('fetch', uid, '(RFC822.PEEK)')
                        except Exception as e_fetch:
                            logger.warning(f"UID fetch wiadomości nie powiodło się dla {uid}: {e_fetch}. Próbuję fetch zamiast UID.")
                            typ, msg_data = mail.fetch(uid, '(RFC822.PEEK)')
                        if typ == 'OK':
                            messages.append((uid, msg_data[0][1]))
                            logger.info(f"Wiadomość {uid} pobrana pomyślnie")
                        else:
                            logger.warning(f"Nie udało się pobrać wiadomości {uid}: typ={typ}")
                    except Exception as e:
                        logger.error(f"Błąd podczas pobierania wiadomości {msg_id}: {e}")
                        print(f"[Autoresponder] Błąd podczas pobierania wiadomości {msg_id}: {e}")
                
                logger.info(f"Pobrano {len(messages)} wiadomości")
                return messages
            finally:
                # Upewnij się, że zawsze zamykamy połączenie
                try:
                    mail.close()
                except:
                    pass
                try:
                    mail.logout()
                except:
                    pass
        except Exception as e:
            logger.error(f"Błąd podczas łączenia z serwerem IMAP: {e}")
            print(f"[Autoresponder] BŁĄD podczas łączenia z serwerem IMAP: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _process_message(self, msg_id, msg_data):
        """
        Przetwarza pojedynczą wiadomość i wysyła odpowiedź
        
        Args:
            msg_id (str): ID wiadomości
            msg_data (bytes): Treść wiadomości w formacie RFC822
        """
        try:
            # Parsowanie wiadomości
            logger.info(f"Parsowanie wiadomości o ID {msg_id}")
            msg = email.message_from_bytes(msg_data)
            
            # Pobieranie adresu nadawcy i daty wiadomości
            from_header = msg['From']
            date_header = msg['Date']
            logger.info(f"Nagłówek From: {from_header}, Date: {date_header}")
            
            # Sprawdź czy wiadomość jest nowsza niż czas uruchomienia autorespondera
            message_date = None
            if date_header:
                try:
                    message_date = parsedate_to_datetime(date_header)
                    logger.info(f"Data wiadomości: {message_date}, data uruchomienia: {self.start_time}")
                    print(f"[Autoresponder] Data wiadomości: {message_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Jeśli wiadomość jest starsza niż czas uruchomienia autorespondera, pomiń ją
                    if message_date < self.start_time:
                        logger.info(f"Pomijanie wiadomości z powodu daty: {message_date} < {self.start_time}")
                        print(f"[Autoresponder] Pomijanie starej wiadomości wysłanej przed uruchomieniem")
                        return
                except Exception as e:
                    # W przypadku błędu parsowania daty, kontynuuj przetwarzanie
                    logger.warning(f"Nie można określić czasu wiadomości: {e}, kontynuuję przetwarzanie")
            
            from_addr = email.utils.parseaddr(from_header)[1]
            subject = msg['Subject'] or "(Brak tematu)"
            
            logger.info(f"Adres nadawcy: {from_addr}, Temat: {subject}")
            print(f"[Autoresponder] Znaleziono wiadomość od: {from_addr}, Temat: {subject}")
            
            # Sprawdzenie czy to nie jest nasz własny email (unikanie pętli)
            if from_addr.lower() == self.username.lower():
                logger.info(f"Pomijanie własnego maila: {subject}")
                print(f"[Autoresponder] Pomijanie wiadomości od samego siebie: {subject}")
                return
            
            # Sprawdzenie czy to nie jest automatyczna odpowiedź
            auto_submitted = msg.get('Auto-Submitted', 'no').lower()
            logger.info(f"Nagłówek Auto-Submitted: {auto_submitted}")
            
            if auto_submitted and auto_submitted != 'no':
                logger.info(f"Pomijanie automatycznej odpowiedzi: {subject}, Auto-Submitted={auto_submitted}")
                print(f"[Autoresponder] Pomijanie automatycznej odpowiedzi: {subject}, Auto-Submitted={auto_submitted}")
                return
            
            # Sprawdzenie nagłówków wskazujących na automatyczną wiadomość
            for header in ['X-Autoreply', 'X-Autorespond', 'Precedence', 'X-Precedence']:
                value = msg.get(header)
                if value:
                    logger.info(f"Znaleziono nagłówek automatycznej odpowiedzi: {header}={value}")
                    print(f"[Autoresponder] Pomijanie automatycznej wiadomości z nagłówkiem {header}={value}")
                    return
            
            # Sprawdzenie czy w temacie nie ma "Re:" lub "Fwd:"
            if subject.lower().startswith('re:') or subject.lower().startswith('fwd:'):
                logger.info(f"Pomijanie wiadomości z Re:/Fwd: w temacie: {subject}")
                print(f"[Autoresponder] Pomijanie wiadomości z Re:/Fwd: w temacie: {subject}")
                return
                
            # Wysyłanie odpowiedzi
            logger.info(f"Wysyłanie odpowiedzi do: {from_addr}, temat: {subject}")
            print(f"[Autoresponder] Wysyłanie odpowiedzi do: {from_addr}, temat: Re: {subject}")
            self._send_response(from_addr, subject, msg.get('Message-ID', ''))
            logger.info(f"Wysłano odpowiedź do: {from_addr}, temat: {subject}")
            
            # Zapamiętaj ID wiadomości, aby nie odpowiadać na nią ponownie
            self.processed_ids.add(msg_id)
            
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania wiadomości {msg_id}: {e}")
            print(f"[Autoresponder] BŁĄD podczas przetwarzania wiadomości {msg_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _send_response(self, recipient, original_subject, message_id):
        """
        Wysyła automatyczną odpowiedź
        
        Args:
            recipient (str): Adres odbiorcy
            original_subject (str): Temat oryginalnej wiadomości
            message_id (str): ID oryginalnej wiadomości
        """
        try:
            logger.info(f"Przygotowywanie odpowiedzi do {recipient}")
            from main import send_email
            
            # Tworzenie tematu odpowiedzi
            subject = "Re: " + original_subject if original_subject else "Automatyczna odpowiedź"
            logger.info(f"Temat odpowiedzi: {subject}")
            
            # Dodanie znacznika czasu do treści wiadomości, by ułatwić debugowanie
            response_text = (
                f"{self.response_message}\n\n"
                f"---\n"
                f"Automatyczna odpowiedź wysłana: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            logger.info(f"Wysyłanie odpowiedzi przez SMTP: {self.smtp_server}:{self.smtp_port}")
            print(f"[Autoresponder] Wysyłanie odpowiedzi przez SMTP: {self.smtp_server}:{self.smtp_port}")
            
            # Wysłanie wiadomości
            send_email(self.smtp_server, self.smtp_port, self.username, self.password, 
                      recipient, subject, response_text)
            
            logger.info(f"Odpowiedź wysłana pomyślnie do {recipient}")
            print(f"[Autoresponder] Odpowiedź wysłana pomyślnie do {recipient}")
            
        except Exception as e:
            logger.error(f"Błąd podczas wysyłania odpowiedzi do {recipient}: {e}")
            print(f"[Autoresponder] BŁĄD podczas wysyłania odpowiedzi do {recipient}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def set_response_message(self, message):
        """Aktualizuje treść automatycznej odpowiedzi"""
        self.response_message = message
        logger.info("Zaktualizowano treść automatycznej odpowiedzi")
        print(f"[Autoresponder] Zaktualizowano treść automatycznej odpowiedzi")
