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

# Uproszczona konfiguracja logowania
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='autoresponder.log', filemode='a')
logger = logging.getLogger('autoresponder')
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class Autoresponder:
	"""Obsługuje automatyczne odpowiadanie na nowe wiadomości."""
	def __init__(self, imap_server, imap_port, smtp_server, smtp_port, username, password, response_message, check_interval=60):
		# Inicjalizacja podstawowych parametrów
		self.imap_server = imap_server
		self.imap_port = imap_port
		self.smtp_server = smtp_server
		self.smtp_port = smtp_port
		self.username = username
		self.password = password
		self.response_message = response_message
		self.check_interval = check_interval
		self.is_running = False
		self.processed_ids = set()
		self.thread = None
		self.start_time = None
		logger.info(f"Autoresponder zainicjalizowany dla {username}")

	def start(self):
		if not self.is_running:
			logger.info("Uruchamianie autorespondera")
			self.is_running = True
			self.start_time = datetime.now()
			logger.info(f"Start time: {self.start_time}")
			print(f"[Autoresponder] Uruchomiono {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
			self.thread = threading.Thread(target=self._run)
			self.thread.daemon = True
			self.thread.start()
			logger.info(f"Wątek autorespondera: {self.thread.name}")
			print(f"Autoresponder uruchomiony! Sprawdzanie co {self.check_interval} sekund.")
			return True
		logger.warning("Autoresponder już działa")
		return False

	def stop(self):
		if self.is_running:
			logger.info("Zatrzymywanie autorespondera")
			self.is_running = False
			if self.thread:
				logger.info(f"Oczekiwanie na zakończenie wątku {self.thread.name}")
			logger.info("Autoresponder zatrzymany")
			print("Autoresponder zatrzymany.")
			return True
		logger.warning("Autoresponder już zatrzymany")
		return False

	def _run(self):
		# Główna pętla sprawdzania nowych wiadomości
		logger.info("Główna pętla autorespondera")
		print(f"[Autoresponder] Sprawdzanie co {self.check_interval} sekund")
		while self.is_running:
			try:
				logger.info("Sprawdzanie wiadomości")
				print(f"[Autoresponder] Sprawdzanie wiadomości... {datetime.now().strftime('%H:%M:%S')}")
				new_messages = self._fetch_new_messages()
				if new_messages:
					logger.info(f"{len(new_messages)} nowych wiadomości")
					print(f"[Autoresponder] {len(new_messages)} nowych wiadomości")
					for msg_id, msg_data in new_messages:
						if msg_id not in self.processed_ids:
							logger.info(f"Przetwarzanie {msg_id}")
							print(f"[Autoresponder] Przetwarzanie {msg_id}")
							self._process_message(msg_id, msg_data)
							self.processed_ids.add(msg_id)
							logger.info(f"{msg_id} przetworzona")
						else:
							logger.info(f"{msg_id} już przetworzona")
				else:
					logger.info("Brak nowych wiadomości")
					print("[Autoresponder] Brak nowych wiadomości")
			except Exception as e:
				logger.error(f"Błąd: {e}")
				print(f"[Autoresponder] BŁĄD: {e}")
				import traceback
				logger.error(traceback.format_exc())
				print("[Autoresponder] Szczegóły błędu w logu")
			logger.debug(f"Oczekiwanie {self.check_interval} sekund")
			print(f"[Autoresponder] Oczekiwanie {self.check_interval} sekund")
			time.sleep(self.check_interval)

	def _fetch_new_messages(self):
		# Logika pobierania wiadomości: obsługa UID/fetch z fallbackem
		try:
			logger.info(f"Łączenie z {self.imap_server}:{self.imap_port}")
			print(f"[Autoresponder] Łączenie z {self.imap_server}:{self.imap_port}")
			mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
			try:
				logger.info("Logowanie IMAP")
				mail.login(self.username, self.password)
				logger.info("Wybór skrzynki odbiorczej")
				mail.select('inbox', readonly=True)
				search_criteria = f'(UNSEEN SINCE "{self.start_time.strftime("%d-%b-%Y")}")' if self.start_time else 'UNSEEN'
				logger.info(f"Wyszukiwanie: {search_criteria}")
				typ, data = mail.search(None, search_criteria)
				if typ != 'OK':
					logger.warning(f"Błąd wyszukiwania: {typ}")
					print(f"[Autoresponder] Błąd wyszukiwania: {typ}")
					return []
				msg_ids = data[0].split()[-10:]
				logger.info(f"{len(msg_ids)} wiadomości (limit 10)")
				print(f"[Autoresponder] {len(msg_ids)} wiadomości (10 ostatnich)")
				messages = []
				for msg_id in msg_ids:
					try:
						uid = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
						try:
							typ, header_data = mail.uid('fetch', uid, '(BODY[HEADER.FIELDS (Date)])')
						except Exception as e_uid:
							logger.warning(f"UID fetch nieudany dla {uid}, próba fetch")
							typ, header_data = mail.fetch(uid, '(BODY[HEADER.FIELDS (Date)])')
						date_header = ""
						if typ == 'OK' and header_data and header_data[0]:
							date_header_bytes = header_data[0][1]
							date_header = date_header_bytes.decode(errors="replace").replace("Date:", "").strip() if date_header_bytes else ""
						if not date_header:
							logger.warning(f"Brak nagłówka daty dla {uid}, pobieranie pełnej wiadomości")
							try:
								typ_full, full_msg_data = mail.uid('fetch', uid, '(RFC822.PEEK)')
							except Exception as e_uid_full:
								logger.warning(f"UID fetch pełnej wiadomości nieudany dla {uid}, próba fetch")
								typ_full, full_msg_data = mail.fetch(uid, '(RFC822.PEEK)')
							if typ_full == 'OK' and full_msg_data and full_msg_data[0]:
								full_msg = email.message_from_bytes(full_msg_data[0][1])
								date_header = full_msg.get("Date", "").strip()
							else:
								logger.warning(f"Nie pobrano pełnej wiadomości {uid}")
								continue
						message_date = None
						if date_header:
							try:
								message_date = email.utils.parsedate_to_datetime(date_header)
							except Exception as dt_err:
								logger.warning(f"Parsowanie daty nieudane dla {uid}: {dt_err}")
								continue
						logger.info(f"Pobieranie wiadomości {uid}")
						try:
							typ, msg_data = mail.uid('fetch', uid, '(RFC822.PEEK)')
						except Exception as e_fetch:
							logger.warning(f"UID fetch wiadomości nieudany dla {uid}, próba fetch")
							typ, msg_data = mail.fetch(uid, '(RFC822.PEEK)')
						if typ == 'OK':
							messages.append((uid, msg_data[0][1]))
							logger.info(f"{uid} pobrana")
						else:
							logger.warning(f"Błąd pobierania {uid}: {typ}")
					except Exception as e:
						logger.error(f"Błąd pobierania wiadomości {msg_id}: {e}")
						print(f"[Autoresponder] Błąd pobierania {msg_id}: {e}")
				logger.info(f"Pobrano {len(messages)} wiadomości")
				return messages
			finally:
				try: 
					mail.close() 
				except: 
					pass
				try: 
					mail.logout() 
				except: 
					pass
		except Exception as e:
			logger.error(f"Błąd połączenia IMAP: {e}")
			print(f"[Autoresponder] BŁĄD połączenia: {e}")
			import traceback
			logger.error(traceback.format_exc())
			return []

	def _process_message(self, msg_id, msg_data):
		# Przetwarzanie wiadomości: parsowanie, weryfikacja kryteriów i wysyłka odpowiedzi
		try:
			logger.info(f"Parsowanie {msg_id}")
			msg = email.message_from_bytes(msg_data)
			from_header = msg['From']
			date_header = msg['Date']
			logger.info(f"From: {from_header}, Date: {date_header}")
			message_date = None
			if date_header:
				try:
					message_date = parsedate_to_datetime(date_header)
					logger.info(f"Data: {message_date} vs start: {self.start_time}")
					print(f"[Autoresponder] Data: {message_date.strftime('%Y-%m-%d %H:%M:%S')}")
					if message_date < self.start_time:
						logger.info(f"Pominięto {msg_id} (stara wiadomość)")
						print("[Autoresponder] Pominięto starą wiadomość")
						return
				except Exception as e:
					logger.warning(f"Nieudane parsowanie daty: {e}")
			from_addr = email.utils.parseaddr(from_header)[1]
			subject = msg['Subject'] or "(Brak tematu)"
			logger.info(f"{from_addr}, Temat: {subject}")
			print(f"[Autoresponder] Od: {from_addr}, Temat: {subject}")
			if from_addr.lower() == self.username.lower():
				logger.info("Pominięto własną wiadomość")
				print("[Autoresponder] Pominięto własną wiadomość")
				return
			auto_submitted = msg.get('Auto-Submitted', 'no').lower()
			logger.info(f"Auto-Submitted: {auto_submitted}")
			if auto_submitted and auto_submitted != 'no':
				logger.info("Pominięto automatyczną odpowiedź")
				print("[Autoresponder] Pominięto automatyczną odpowiedź")
				return
			for header in ['X-Autoreply', 'X-Autorespond', 'Precedence', 'X-Precedence']:
				value = msg.get(header)
				if value:
					logger.info(f"Pominięto wiadomość z nagłówkiem {header}")
					print(f"[Autoresponder] Pominięto {header}")
					return
			if subject.lower().startswith('re:') or subject.lower().startswith('fwd:'):
				logger.info("Pominięto wiadomość z Re:/Fwd:")
				print("[Autoresponder] Pominięto wiadomość z Re:/Fwd:")
				return
			logger.info(f"Wysyłanie odpowiedzi: Re: {subject}")
			print(f"[Autoresponder] Wysyłanie odpowiedzi: Re: {subject}")
			self._send_response(from_addr, subject, msg.get('Message-ID', ''))
			logger.info("Odpowiedź wysłana")
			self.processed_ids.add(msg_id)
		except Exception as e:
			logger.error(f"Błąd przetwarzania {msg_id}: {e}")
			print(f"[Autoresponder] BŁĄD przetwarzania {msg_id}: {e}")
			import traceback
			logger.error(traceback.format_exc())

	def _send_response(self, recipient, original_subject, message_id):
		# Wysyłka odpowiedzi przez SMTP
		try:
			logger.info(f"Przygotowywanie odpowiedzi do {recipient}")
			from main import send_email
			subject = "Re: " + original_subject if original_subject else "Automatyczna odpowiedź"
			logger.info(f"Temat odpowiedzi: {subject}")
			response_text = f"{self.response_message}\n\n---\nAutomatyczna odpowiedź: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
			logger.info(f"Łączenie SMTP {self.smtp_server}:{self.smtp_port}")
			print(f"[Autoresponder] SMTP: {self.smtp_server}:{self.smtp_port}")
			send_email(self.smtp_server, self.smtp_port, self.username, self.password, recipient, subject, response_text)
			logger.info(f"Odpowiedź do {recipient} wysłana")
			print(f"[Autoresponder] Odpowiedź do {recipient} wysłana")
		except Exception as e:
			logger.error(f"Błąd wysyłania do {recipient}: {e}")
			print(f"[Autoresponder] BŁĄD wysyłania do {recipient}: {e}")
			import traceback
			logger.error(traceback.format_exc())

	def set_response_message(self, message):
		self.response_message = message
		logger.info("Treść odpowiedzi zaktualizowana")
		print("[Autoresponder] Treść odpowiedzi zaktualizowana")
