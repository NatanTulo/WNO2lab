import sys
import os
import json
import tempfile
import datetime
import socket
import threading
import time

from PyQt5.QtCore import Qt, QTimer, QEventLoop, pyqtSlot, QObject
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QGraphicsView, QMainWindow, QDockWidget,
    QTextEdit, QMessageBox, QDialog, QVBoxLayout, QListWidget,
    QPushButton, QHBoxLayout, QLabel, QComboBox, QListWidgetItem,
    QProgressDialog, QGraphicsTextItem
)

import config
from game_scene import GameScene
from level_editor_scene import LevelEditorScene
from logger import Logger
from menu_scene import MenuScene
from playback_scene import PlaybackScene
import game_history

class DynamicGraphicsView(QGraphicsView):
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.scene():
            self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)

class ConnectionHandler(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    @pyqtSlot()
    def request_finish_connection(self):
        self.parent.finish_connection_setup()

    @pyqtSlot(str)
    def request_process_message(self, data):
        self.parent.process_game_message(data)

class GameWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cell Expansion Wars")

        self.logger = Logger(max_lines=100)

        self.log_dock = QDockWidget("Log", self)
        self.log_dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_dock.setWidget(self.log_view)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        self.resizeDocks([self.log_dock], [100], Qt.Vertical)
        self.logger.set_text_edit(self.log_view)

        menu_bar = self.menuBar()
        view_menu = menu_bar.addMenu("Widok")
        self.toggle_log_action = view_menu.addAction("Pokaż/Ukryj Logi")
        self.toggle_log_action.setCheckable(True)
        self.toggle_log_action.setChecked(True)
        self.toggle_log_action.triggered.connect(self.toggle_log_dock)

        powerup_menu = menu_bar.addMenu("Powerupy")
        freeze_action = powerup_menu.addAction("Zamrożenie komórki")
        takeover_action = powerup_menu.addAction("Przejęcie komórki")
        addpoints_action = powerup_menu.addAction("Dodaj 10 punktów")
        newcell_action = powerup_menu.addAction("Dodaj nową komórkę")
        freeze_action.triggered.connect(lambda: self.activate_powerup(config.POWERUP_FREEZE))
        takeover_action.triggered.connect(lambda: self.activate_powerup(config.POWERUP_TAKEOVER))
        addpoints_action.triggered.connect(lambda: self.activate_powerup(config.POWERUP_ADD_POINTS))
        newcell_action.triggered.connect(lambda: self.activate_powerup(config.POWERUP_NEW_CELL))

        self.menu_scene = MenuScene()
        self.menu_scene.logger = self.logger
        self.game_scene = None
        self.editor_scene = None

        self.view = DynamicGraphicsView()
        self.view.setRenderHints(self.view.renderHints())
        self.view.setViewportUpdateMode(self.view.FullViewportUpdate)
        self.setCentralWidget(self.view)
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

        self.menu_scene.level_selected = self.start_game
        self.menu_scene.editor_selected = self.start_editor
        self.menu_scene.replay_selected = self.start_replay

        self.show_menu()

        self.logger.log("Aplikacja uruchomiona.")
        self.network_listener_started = False                         
        self.previous_turn_based_state = None                                             
        self.connection_established = False
        self.connection_timeout = 10000                                       

        self.handler = ConnectionHandler(self)

    def toggle_log_dock(self, visible):
        if visible:
            self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
            self.log_dock.show()
        else:
            self.log_dock.hide()

    def show_menu(self):
        saved_role = None
        if self.game_scene and hasattr(self.game_scene, 'multiplayer_role'):
            saved_role = self.game_scene.multiplayer_role

        if hasattr(self, 'role_check_timer') and self.role_check_timer:
            self.role_check_timer.stop()

        if self.game_scene:
            self.game_scene.timer.stop()
            self.game_scene.points_timer.stop()

            if hasattr(self.game_scene, 'turn_timer') and self.game_scene.turn_timer:
                self.game_scene.turn_timer.stop()
                try:
                    self.game_scene.turn_timer.timeout.disconnect()
                except (TypeError, RuntimeError):
                    pass                                                   

            if hasattr(self.game_scene, 'enemy_timer') and self.game_scene.enemy_timer:
                self.game_scene.enemy_timer.stop()
                try:
                    self.game_scene.enemy_timer.timeout.disconnect()
                except (TypeError, RuntimeError):
                    pass

            if hasattr(self.game_scene, 'hint_timer') and self.game_scene.hint_timer:
                self.game_scene.hint_timer.stop()
                try:
                    self.game_scene.hint_timer.timeout.disconnect()
                except (TypeError, RuntimeError):
                    pass

            if self.logger:
                self.logger.log("GameWindow: Wszystkie timery zatrzymane, przejście do menu.")

        self.view.setScene(self.menu_scene)

        if saved_role and hasattr(self, 'menu_scene'):
            self.menu_scene.last_used_role = saved_role

    def start_game(self, level_id):
        self.game_scene = GameScene()
        self.game_scene.logger = self.logger
        self.game_scene.current_level = level_id
        quicksave_xml = os.path.join("saves", f"quicksave_level{level_id}.xml")
        quicksave_json = os.path.join("saves", f"quicksave_level{level_id}.json")
        if os.path.exists(quicksave_xml) or os.path.exists(quicksave_json):
            result = QMessageBox.question(None, "Wczytaj quicksave?",
                f"Znaleziono quicksave dla poziomu {level_id}. Czy chcesz z niego skorzystać?",
                QMessageBox.Yes | QMessageBox.No)
            if result == QMessageBox.Yes:
                if not self.game_scene.quickload():
                    self.show_menu()
                    return
            else:
                self.game_scene.initialize_level(level_id)
        else:
            self.game_scene.initialize_level(level_id)
        self.view.setScene(self.game_scene)

        if self.menu_scene.game_mode == "1 gracz":
            self.game_scene.single_player = True
            self.game_scene.start_enemy_timer()
            if self.previous_turn_based_state is not None:
                self.game_scene.turn_based_mode = self.previous_turn_based_state
                self.previous_turn_based_state = None
            else:
                self.game_scene.turn_based_mode = self.menu_scene.turn_based
            self.game_scene.timer.start(16)
            self.game_scene.points_timer.start(2000)

        elif self.menu_scene.game_mode == "gra sieciowa":
            remote_ip = self.menu_scene.ip_lineedit.text().strip()
            port_text = self.menu_scene.port_lineedit.text().strip()

            self.use_ipv6 = ":" in remote_ip and not remote_ip.startswith("127.")

            if not remote_ip or not port_text:
                QMessageBox.critical(self, "Błąd połączenia",
                                    "Pola IP lub Port są puste.")
                self.show_menu()
                return

            try:
                remote_port = int(port_text)

                self.connection_established = False
                if hasattr(self, 'connection_setup_completed'):
                    delattr(self, 'connection_setup_completed')                                     

                self.start_network_listener(remote_port)
                local_ip = get_local_ip(self.use_ipv6)

                self.game_scene.is_multiplayer = True

                self.game_scene.is_connection_initiator = True
                self.game_scene.multiplayer_role = "player"

                if self.previous_turn_based_state is None:
                    self.previous_turn_based_state = self.menu_scene.turn_based

                self.game_scene.turn_based_mode = True
                self.game_scene.single_player = False

                self.game_scene.network_send_callback = lambda msg: self.send_network_message(remote_ip, remote_port, msg)

                self.game_scene.on_disconnect = lambda: self.handle_client_disconnect()

                self.connection_active = True
                self.connection_setup_completed = False                                                      

                self.game_scene.connecting_text = QGraphicsTextItem("Łączenie z drugim graczem...")
                self.game_scene.connecting_text.setDefaultTextColor(Qt.white)
                self.game_scene.connecting_text.setFont(QFont("Arial", 24))
                connecting_rect = self.game_scene.connecting_text.boundingRect()
                self.game_scene.connecting_text.setPos(
                    (self.game_scene.width() - connecting_rect.width()) / 2,
                    (self.game_scene.height() - connecting_rect.height()) / 2
                )
                self.game_scene.addItem(self.game_scene.connecting_text)

                connection_message = f"connection_request;player"
                if self.logger:
                    self.logger.log(f"Próba połączenia z {remote_ip}:{remote_port}")

                self.send_network_message(remote_ip, remote_port, connection_message)

                self.send_network_message(remote_ip, remote_port, f"set_role;enemy")

                self.connection_check_timer = QTimer()
                self.connection_check_timer.setSingleShot(True)
                self.connection_check_timer.timeout.connect(self.finish_connection_setup)
                self.connection_check_timer.start(500)                                   

                self.heartbeat_timer = QTimer()
                self.heartbeat_timer.timeout.connect(lambda: self.send_heartbeat_with_sync(remote_ip, remote_port))
                self.last_heartbeat_received = time.time()
                self.heartbeat_timer.start(2000)                            

                self.connection_safety_timer = QTimer()
                self.connection_safety_timer.setSingleShot(True)
                self.connection_safety_timer.timeout.connect(self.handle_connection_timeout)
                self.connection_safety_timer.start(8000)                                     

            except Exception as e:
                if self.logger:
                    self.logger.log(f"Błąd konfiguracji sieciowej: {e}")
                QMessageBox.critical(self, "Błąd połączenia",
                                   f"Nie udało się nawiązać połączenia")
                self.show_menu()
                return

        else:
            if self.previous_turn_based_state is not None:
                self.game_scene.turn_based_mode = self.previous_turn_based_state
                self.previous_turn_based_state = None
            else:
                self.game_scene.turn_based_mode = self.menu_scene.turn_based
            self.game_scene.single_player = False

            self.game_scene.timer.start(16)
            self.game_scene.points_timer.start(2000)

    def finish_connection_setup(self):
        """Kończy konfigurację połączenia i rozpoczyna grę"""
        if hasattr(self, 'connection_safety_timer') and self.connection_safety_timer.isActive():
            self.connection_safety_timer.stop()

        if hasattr(self, 'game_scene') and self.game_scene:
            if hasattr(self.game_scene, 'connecting_text') and self.game_scene.connecting_text:
                try:
                    self.game_scene.removeItem(self.game_scene.connecting_text)
                    self.game_scene.connecting_text = None
                    if self.logger:
                        self.logger.log("Usunięto komunikat o łączeniu")
                except Exception as e:
                    if self.logger:
                        self.logger.log(f"Błąd podczas usuwania tekstu łączenia: {e}")

            if not hasattr(self, 'connection_setup_completed') or not self.connection_setup_completed:
                self.connection_setup_completed = True

                if not hasattr(self.game_scene, 'multiplayer_role'):
                    self.game_scene.multiplayer_role = "player" if getattr(self.game_scene, 'is_connection_initiator', True) else "enemy"

                role_text = "ZIELONY" if self.game_scene.multiplayer_role == "player" else "CZERWONY"
                if hasattr(self.game_scene, 'role_info') and self.game_scene.role_info:
                    self.game_scene.removeItem(self.game_scene.role_info)
                    self.game_scene.role_info = None

                role_info = QGraphicsTextItem(f"Twój kolor: {role_text}")
                role_info.setDefaultTextColor(Qt.white)
                role_info.setFont(QFont("Arial", 16))
                role_rect = role_info.boundingRect()
                role_info.setPos((self.game_scene.width() - role_rect.width()) / 2, self.game_scene.height()-40.0)
                self.game_scene.addItem(role_info)
                self.game_scene.role_info = role_info

                if self.logger:
                    self.logger.log(f"Przypisana rola: {role_text}, Inicjator: {getattr(self.game_scene, 'is_connection_initiator', False)}")

                try:
                    self.game_scene.start_turn_timer()
                    if self.logger:
                        self.logger.log("Timer tury został uruchomiony")
                except Exception as e:
                    if self.logger:
                        self.logger.log(f"Błąd podczas uruchamiania timera tury: {e}")

                try:
                    self.game_scene.timer.start(16)
                    self.game_scene.points_timer.start(2000)
                    if self.logger:
                        self.logger.log("Timery gry zostały uruchomione")
                except Exception as e:
                    if self.logger:
                        self.logger.log(f"Błąd podczas uruchamiania timerów gry: {e}")

                if hasattr(self.game_scene, "network_send_callback") and self.game_scene.network_send_callback:
                    self.game_scene.send_game_state_snapshot()
                    if self.logger:
                        self.logger.log("Wysłano pełną synchronizację stanu gry")

                if self.logger:
                    self.logger.log("Połączenie skonfigurowane, gra rozpoczęta.")

                self.role_check_timer = QTimer()
                self.role_check_timer.timeout.connect(self.ensure_role_display)
                self.role_check_timer.start(500)                        

    def remove_role_info(self):
        """Usuwa informację o roli po kilku sekundach"""
        if hasattr(self, 'game_scene') and self.game_scene and hasattr(self.game_scene, 'role_info') and self.game_scene.role_info:
            self.game_scene.removeItem(self.game_scene.role_info)
            self.game_scene.role_info = None

    def handle_client_disconnect(self):
        """Obsługuje rozłączenie klienta w trybie multiplayer"""
        if hasattr(self, 'game_scene') and self.game_scene:
            if self.logger:
                self.logger.log("Wykryto rozłączenie z drugim graczem. Gra zostanie zakończona.")

            if hasattr(self, 'heartbeat_timer') and self.heartbeat_timer:
                self.heartbeat_timer.stop()

            disconnect_text = QGraphicsTextItem("Utracono połączenie z drugim graczem")
            disconnect_text.setDefaultTextColor(Qt.red)
            disconnect_text.setFont(QFont("Arial", 24))
            disconnect_rect = disconnect_text.boundingRect()
            disconnect_text.setPos((self.game_scene.width() - disconnect_rect.width()) / 2,
                                 (self.game_scene.height() - disconnect_rect.height()) / 2)
            self.game_scene.addItem(disconnect_text)

            self.game_scene.stop_all_timers()
            QTimer.singleShot(3000, lambda: self.show_menu())

    def check_connection_status(self):
        """Sprawdza czy połączenie jest nadal aktywne"""
        now = time.time()
        if now - self.last_heartbeat_received > 6.0:
            if self.logger:
                self.logger.log(f"Brak odpowiedzi przez ponad 6 sekund. Ostatni heartbeat: {self.last_heartbeat_received}")
            self.handle_client_disconnect()
            return False
        return True

    def start_editor(self, level_id):
        self.editor_scene = LevelEditorScene(level_id)
        self.editor_scene.logger = self.logger
        self.view.setScene(self.editor_scene)

    def select_replay_file(self, replay_source):
        dialog = QDialog(self)
        dialog.setWindowTitle("Wybór replay")
        layout = QVBoxLayout(dialog)
        label = QLabel("Wybierz plik replay:")
        layout.addWidget(label)
        level_combo = QComboBox()
        level_combo.addItems(["Poziom 1", "Poziom 2", "Poziom 3"])
        layout.addWidget(level_combo)
        list_widget = QListWidget()
        layout.addWidget(list_widget)
        ext = ".xml" if replay_source == "XML" else ".json" if replay_source == "JSON" else ""
        replays_dir = "replays"
        if not os.path.exists(replays_dir):
            os.makedirs(replays_dir)

        def update_list():
            list_widget.clear()
            selected_level = int(level_combo.currentText().split()[1])
            level_prefix = f"replay_level{selected_level}_"
            files = [f for f in os.listdir(replays_dir) if f.startswith(level_prefix) and f.endswith(ext)]
            sorted_files = sorted(files, key=lambda f: os.path.getmtime(os.path.join(replays_dir, f)), reverse=True)
            for f in sorted_files:
                list_widget.addItem(f)
        update_list()
        level_combo.currentIndexChanged.connect(update_list)

        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Anuluj")
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        selected_file = [None]

        def on_ok():
            item = list_widget.currentItem()
            if item:
                selected_file[0] = os.path.join(replays_dir, item.text())
                dialog.accept()
        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(dialog.reject)
        if dialog.exec_() == QDialog.Accepted:
            return selected_file[0]
        return None

    def select_replay_document(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Wybór replay z MongoDB")
        layout = QVBoxLayout(dialog)
        lbl = QLabel("Wybierz replay z bazy MongoDB:")
        layout.addWidget(lbl)
        level_combo = QComboBox()
        level_combo.addItems(["Poziom 1", "Poziom 2", "Poziom 3"])
        layout.addWidget(level_combo)
        list_widget = QListWidget()
        layout.addWidget(list_widget)
        doc_mapping = {}
        def update_list():
            list_widget.clear()
            doc_mapping.clear()
            row = 0
            selected_level = int(level_combo.currentText().split()[1])
            documents = list(game_history.replays_collection.find({"level": selected_level}))
            quicksaves = sorted([doc for doc in documents if doc.get("is_quicksave")],
                                key=lambda doc: doc.get("moves", [{}])[0].get("timestamp", 0), reverse=True)
            regular = sorted([doc for doc in documents if not doc.get("is_quicksave")],
                             key=lambda doc: doc.get("moves", [{}])[0].get("timestamp", 0), reverse=True)
            if quicksaves:
                header = QListWidgetItem("=== Quick Saves ===")
                header.setFlags(header.flags() & ~Qt.ItemIsSelectable)
                list_widget.addItem(header)
                row += 1
                for doc in quicksaves:
                    ts = doc.get("moves", [{}])[0].get("timestamp", 0)
                    try:
                        time_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        time_str = "Brak daty"
                    id_short = str(doc["_id"])[:8]
                    display_text = f"[Quick] {time_str} - {id_short}"
                    list_item = QListWidgetItem(display_text)
                    list_widget.addItem(list_item)
                    doc_mapping[row] = doc
                    row += 1
            if regular:
                header = QListWidgetItem("=== Regular Replays ===")
                header.setFlags(header.flags() & ~Qt.ItemIsSelectable)
                list_widget.addItem(header)
                row += 1
                for doc in regular:
                    ts = doc.get("moves", [{}])[0].get("timestamp", 0)
                    try:
                        time_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        time_str = "Brak daty"
                    id_short = str(doc["_id"])[:8]
                    display_text = f"[Replay] {time_str} - {id_short}"
                    list_item = QListWidgetItem(display_text)
                    list_widget.addItem(list_item)
                    doc_mapping[row] = doc
                    row += 1
        update_list()
        level_combo.currentIndexChanged.connect(update_list)
        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Anuluj")
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
        selected_doc = [None]
        def on_ok():
            idx = list_widget.currentRow()
            if idx in doc_mapping:
                selected_doc[0] = doc_mapping[idx]
                dialog.accept()
        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(dialog.reject)
        if dialog.exec_() == QDialog.Accepted:
            return selected_doc[0]
        return None

    def start_replay(self):
        replay_source = getattr(self.menu_scene, "replay_source", "XML")
        if (replay_source == "NoSQL"):
            selected_doc = self.select_replay_document()
            if not selected_doc:
                return
            if "_id" in selected_doc:
                selected_doc["_id"] = str(selected_doc["_id"])
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
            json.dump(selected_doc, temp_file, indent=4, ensure_ascii=False)
            temp_file.close()
            filename = temp_file.name
        else:
            selected = self.select_replay_file(replay_source)
            if not selected:
                return
            filename = selected
        self.playback_scene = PlaybackScene(filename)
        self.playback_scene.logger = self.logger
        self.view.setScene(self.playback_scene)
        self.playback_scene.start_playback()

    def start_network_listener(self, port):
        if not self.network_listener_started:
            thread = threading.Thread(target=self.network_listener, args=(port,), daemon=True)
            thread.start()
            self.network_listener_started = True
            if self.logger:
                self.logger.log(f"Uruchomiono nasłuchiwanie TCP/IP na porcie {port}.")

    def network_listener(self, port):
        if hasattr(self, 'use_ipv6') and self.use_ipv6:
            server_sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            try:
                server_sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            except Exception as e:
                if self.logger:
                    self.logger.log(f"Ostrzeżenie: Nie można skonfigurować socketu do obsługi dual-stack: {e}")
            bind_address = ("::", port)
        else:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            bind_address = ("0.0.0.0", port)

        try:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(bind_address)
            server_sock.settimeout(0.5)                                        
            server_sock.listen(5)

            if self.logger:
                ip_version = "IPv6" if hasattr(self, 'use_ipv6') and self.use_ipv6 else "IPv4"
                self.logger.log(f"Nasłuchiwanie {ip_version} uruchomione na porcie {port}")

            buffer_size = 4096                                              

            while True:
                try:
                    conn, addr = server_sock.accept()
                    try:
                        data = b""
                        while True:
                            chunk = conn.recv(buffer_size)
                            if not chunk:
                                break
                            data += chunk
                            if len(chunk) < buffer_size:
                                break

                        if data:
                            decoded_data = data.decode("utf-8")

                            if "heartbeat" in decoded_data:
                                self.last_heartbeat_received = time.time()

                                if ";time:" in decoded_data:
                                    try:
                                        time_part = decoded_data.split(";time:")[1].split(";")[0]
                                        time_value = int(time_part)

                                        if hasattr(self, 'game_scene') and self.game_scene:
                                            if hasattr(self.game_scene, 'current_turn') and hasattr(self.game_scene, 'multiplayer_role'):
                                                if self.game_scene.current_turn != self.game_scene.multiplayer_role:
                                                    self.game_scene.round_time_remaining = time_value
                                                    if self.logger:
                                                        self.logger.log(f"Synchronizacja czasu: {time_value}s pozostało")
                                    except Exception as e:
                                        if self.logger:
                                            self.logger.log(f"Błąd parsowania czasu z heartbeat: {e}")

                                try:
                                    conn.sendall("heartbeat_ack".encode("utf-8"))
                                except:
                                    pass

                            if "connection_request" in decoded_data:
                                if self.logger:
                                    self.logger.log(f"Otrzymano żądanie połączenia z {addr}")
                                try:
                                    conn.sendall("connection_confirm;ok".encode("utf-8"))

                                    if hasattr(self, 'game_scene') and self.game_scene:
                                        self.game_scene.is_connection_initiator = False
                                        self.game_scene.multiplayer_role = "enemy"
                                        if self.logger:
                                            self.logger.log("Ustawiono rolę odbiorcy jako ENEMY")

                                    if hasattr(self, 'connection_check_timer') and self.connection_check_timer.isActive():
                                        self.connection_check_timer.stop()

                                    self.handler.request_finish_connection()

                                except Exception as e:
                                    if self.logger:
                                        self.logger.log(f"Błąd wysyłania potwierdzenia połączenia: {e}")

                            if "request_full_sync" in decoded_data:
                                if self.logger:
                                    self.logger.log(f"Otrzymano żądanie pełnej synchronizacji od {addr}")

                                if hasattr(self, 'game_scene') and self.game_scene and hasattr(self.game_scene, 'network_send_callback'):
                                    if hasattr(self.game_scene, 'round_time_remaining'):
                                        self.game_scene.network_send_callback(f"sync_time;{self.game_scene.round_time_remaining}")

                                    if hasattr(self.game_scene, 'cells') and self.game_scene.cells:
                                        for i, cell in enumerate(self.game_scene.cells):
                                            self.game_scene.network_send_callback(f"sync_cell;{i};{cell.cell_type};{cell.points}")

                                    self.game_scene.network_send_callback("sync_complete")

                                    if self.logger:
                                        self.logger.log("Wysłano pełny stan gry do partnera")

                            if decoded_data.startswith("sync_time") and ";" in decoded_data:
                                try:
                                    time_value = int(decoded_data.split(";")[1])
                                    if hasattr(self, 'game_scene') and self.game_scene:
                                        self.game_scene.round_time_remaining = time_value
                                        if self.logger:
                                            self.logger.log(f"Zsynchronizowano czas: {time_value}s")
                                except Exception as e:
                                    if self.logger:
                                        self.logger.log(f"Błąd synchronizacji czasu: {e}")

                            if decoded_data.startswith("sync_cell") and len(decoded_data.split(";")) >= 4:
                                try:
                                    parts = decoded_data.split(";")
                                    cell_index = int(parts[1])
                                    cell_type = parts[2]
                                    cell_points = int(parts[3])

                                    if hasattr(self, 'game_scene') and self.game_scene and hasattr(self.game_scene, 'cells'):
                                        if 0 <= cell_index < len(self.game_scene.cells):
                                            cell = self.game_scene.cells[cell_index]
                                            cell.cell_type = cell_type
                                            cell.points = cell_points
                                            cell.strength = (cell.points // config.POINTS_PER_STRENGTH) + 1
                                            cell.update()
                                            if self.logger:
                                                self.logger.log(f"Zsynchronizowano komórkę {cell_index}: {cell_type}, {cell_points} punktów")
                                except Exception as e:
                                    if self.logger:
                                        self.logger.log(f"Błąd synchronizacji komórki: {e}")

                            priority_msg = False
                            if "switch_turn" in decoded_data:
                                priority_msg = True
                                try:
                                    conn.sendall("received".encode("utf-8"))
                                except:
                                    pass

                            if self.logger and not decoded_data.startswith("update_turn_time") and not decoded_data.startswith("heartbeat") and not decoded_data.startswith("snapshot_"):
                                if len(decoded_data) > 100:
                                    self.logger.log(f"Odebrano wiadomość z {addr}: {decoded_data[:100]}...")
                                else:
                                    self.logger.log(f"Odebrano wiadomość z {addr}: {decoded_data}")

                            if self.game_scene:
                                self.handler.request_process_message(decoded_data)
                    except Exception as e:
                        if self.logger:
                            self.logger.log(f"Błąd podczas przetwarzania otrzymanej wiadomości: {e}")
                    finally:
                        conn.close()
                except socket.timeout:
                    pass
                except Exception as e:
                    if self.logger:
                        self.logger.log(f"Wyjątek w pętli nasłuchiwania: {e}")
                    if hasattr(self, 'game_scene') and self.game_scene and hasattr(self.game_scene, 'is_multiplayer'):
                        if self.game_scene.is_multiplayer:
                            self.check_connection_status()
        except Exception as e:
            if self.logger:
                self.logger.log(f"Błąd nasłuchiwania TCP/IP: {e}")
        finally:
            server_sock.close()
            if self.logger:
                self.logger.log("Serwer nasłuchujący zamknięty")

    def send_network_message(self, ip, port, message):
        try:
            use_ipv6 = ":" in ip and not ip.startswith("127.")

            if use_ipv6:
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            if "set_role" in message and hasattr(self, 'game_scene') and self.game_scene:
                if getattr(self.game_scene, 'is_connection_initiator', False):
                    if "enemy" not in message:
                        message = "set_role;enemy"
                        if self.logger:
                            self.logger.log("Poprawiono wysyłaną rolę na: enemy")
                else:
                    if "player" not in message:
                        message = "set_role;player"
                        if self.logger:
                            self.logger.log("Poprawiono wysyłaną rolę na: player")

            priority_msg = False
            if "switch_turn" in message or "heartbeat" in message:
                priority_msg = True

            is_snapshot = message.startswith("snapshot_")
            timeout_value = 5 if is_snapshot else (2 if priority_msg else 3)

            sock.settimeout(timeout_value)                                  

            retries = 3 if is_snapshot else (2 if priority_msg else 1)
            retry_count = 0

            if use_ipv6 and "%" in ip:
                ip_parts = ip.split("%")
                ip = ip_parts[0]

            success = False
            while retry_count <= retries and not success:
                try:
                    if use_ipv6:
                        sock.connect((ip, port))
                    else:
                        sock.connect((ip, port))

                    sock.sendall(message.encode("utf-8"))

                    if "heartbeat" in message:
                        sock.settimeout(1.0)
                        try:
                            response = sock.recv(1024).decode("utf-8")
                            if "heartbeat_ack" in response:
                                self.last_heartbeat_received = time.time()
                        except socket.timeout:
                            if retry_count == retries:
                                if hasattr(self, 'game_scene') and self.game_scene and hasattr(self.game_scene, 'is_multiplayer'):
                                    if self.game_scene.is_multiplayer:
                                        self.check_connection_status()

                    elif priority_msg:
                        sock.settimeout(1.0)
                        try:
                            response = sock.recv(1024).decode("utf-8")
                            if response == "received":
                                if self.logger and not message.startswith("heartbeat"):
                                    self.logger.log(f"Otrzymano potwierdzenie odebrania {message}")
                        except socket.timeout:
                            pass

                    if self.logger and not message.startswith("update_turn_time") and not message.startswith("heartbeat") and not message.startswith("snapshot_"):
                        self.logger.log(f"Wysłano wiadomość do {ip}:{port}: {message[:50]}..." if len(message) > 50 else f"Wysłano wiadomość do {ip}:{port}: {message}")
                    success = True
                except Exception as e:
                    retry_count += 1
                    if retry_count <= retries:
                        if self.logger and not message.startswith("heartbeat") and not message.startswith("snapshot_"):
                            self.logger.log(f"Ponawiam wysłanie wiadomości ({retry_count}/{retries+1})")
                        time.sleep(0.2 * retry_count)                                    
                    else:
                        if self.logger and not message.startswith("heartbeat") and not message.startswith("snapshot_"):
                            self.logger.log(f"Nie udało się wysłać wiadomości po {retries+1} próbach: {e}")
                        if hasattr(self, 'game_scene') and self.game_scene and hasattr(self.game_scene, 'is_multiplayer'):
                            if self.game_scene.is_multiplayer:
                                self.check_connection_status()
        except Exception as e:
            if self.logger and not message.startswith("heartbeat"):
                self.logger.log(f"Błąd wysyłania wiadomości do {ip}:{port}: {e}")
            if hasattr(self, 'game_scene') and self.game_scene and hasattr(self.game_scene, 'is_multiplayer'):
                if self.game_scene.is_multiplayer:
                    self.check_connection_status()
        finally:
            if 'sock' in locals():
                sock.close()

    def send_network_message_with_confirmation(self, ip, port, message, max_retries=3):
        use_ipv6 = ":" in ip and not ip.startswith("127.")

        """Wysyła wiadomość sieciową i czeka na potwierdzenie lub zakończenie prób"""
        for retry in range(max_retries):
            try:
                if use_ipv6:
                    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                else:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                sock.settimeout(2.0)                                       

                if use_ipv6 and "%" in ip:
                    connect_ip = ip.split("%")[0]
                else:
                    connect_ip = ip

                sock.connect((connect_ip, port))
                sock.sendall(message.encode("utf-8"))

                try:
                    response = sock.recv(1024).decode("utf-8")
                    if response and "connection_confirm" in response:
                        if self.logger:
                            self.logger.log(f"Otrzymano potwierdzenie połączenia: {response}")
                        return True
                except socket.timeout:
                    pass

                if self.logger:
                    self.logger.log(f"Próba {retry+1}/{max_retries} - brak potwierdzenia")

                time.sleep(0.5)
            except Exception as e:
                if self.logger:
                    self.logger.log(f"Błąd podczas próby połączenia ({retry+1}/{max_retries}): {e}")
                time.sleep(0.5)
            finally:
                sock.close()

        return False

    def process_game_message(self, data):
        if self.game_scene:
            if data.startswith("set_role;") and ";" in data:
                parts = data.strip().split(";")
                if len(parts) >= 2:
                    role = parts[1].strip()
                    if role in ["player", "enemy"]:
                        QTimer.singleShot(100, lambda: self.ensure_role_display(role))

            self.game_scene.process_network_message(data)
        else:
            if self.logger:
                self.logger.log("Otrzymano wiadomość sieciową, ale brak aktywnej sceny gry")

    def ensure_role_display(self, role=None):
        """Upewnia się, że rola gracza jest wyświetlana"""
        if hasattr(self, 'game_scene') and self.game_scene:
            if role:
                self.game_scene.multiplayer_role = role

            if not hasattr(self.game_scene, 'role_info') or not self.game_scene.role_info or not self.game_scene.role_info.scene():
                if not hasattr(self.game_scene, 'multiplayer_role'):
                    self.game_scene.multiplayer_role = "player" if getattr(self.game_scene, 'is_connection_initiator', True) else "enemy"

                role_text = "ZIELONY" if self.game_scene.multiplayer_role == "player" else "CZERWONY"
                role_info = QGraphicsTextItem(f"Twój kolor: {role_text}")
                role_info.setDefaultTextColor(Qt.white)
                role_info.setFont(QFont("Arial", 16))
                role_rect = role_info.boundingRect()
                role_info.setPos((self.game_scene.width() - role_rect.width()) / 2, self.game_scene.height()-40.0)
                self.game_scene.addItem(role_info)
                self.game_scene.role_info = role_info

                if self.logger:
                    self.logger.log(f"Dodano brakujący wskaźnik roli: {role_text}")

    def handle_connection_established(self):
        """Metoda wywoływana w wątku głównym po nawiązaniu połączenia"""
        if hasattr(self, 'connection_callback') and callable(self.connection_callback):
            callback = self.connection_callback
            self.connection_callback = None                                   
            callback()                       

    def handle_connection_timeout(self):
        """Obsługuje timeout połączenia"""
        if hasattr(self, 'game_scene') and self.game_scene:
            if not hasattr(self, 'connection_setup_completed') or not self.connection_setup_completed:
                if self.logger:
                    self.logger.log("Timeout połączenia - brak odpowiedzi od drugiego gracza")

                if hasattr(self.game_scene, 'connecting_text') and self.game_scene.connecting_text:
                    self.game_scene.removeItem(self.game_scene.connecting_text)
                    self.game_scene.connecting_text = None

                QMessageBox.critical(self, "Problem z połączeniem",
                                  "Nie udało się nawiązać połączenia z drugim graczem. Upewnij się, że podane IP i port są prawidłowe.")
                self.show_menu()

    def send_heartbeat_with_sync(self, ip, port):
        """Wysyła heartbeat wraz z aktualnym stanem gry dla lepszej synchronizacji"""
        use_ipv6 = ":" in ip and not ip.startswith("127.")

        if hasattr(self, 'game_scene') and self.game_scene:
            try:
                if not hasattr(self, '_last_full_sync_time'):
                    self._last_full_sync_time = 0

                current_time = time.time()
                if current_time - self._last_full_sync_time > 5:                                
                    self._last_full_sync_time = current_time
                    self.game_scene.send_game_state_snapshot()
                else:
                    time_remaining = self.game_scene.round_time_remaining if hasattr(self.game_scene, 'round_time_remaining') else 0

                    if hasattr(self.game_scene, 'current_turn') and hasattr(self.game_scene, 'multiplayer_role'):
                        if self.game_scene.current_turn == self.game_scene.multiplayer_role:
                            self.send_network_message(ip, port, f"heartbeat;time:{time_remaining}")
                        else:
                            self.send_network_message(ip, port, "heartbeat")
            except Exception as e:
                if self.logger:
                    self.logger.log(f"Błąd podczas wysyłania heartbeat z synchronizacją: {e}")
        else:
            self.send_network_message(ip, port, "heartbeat")

def get_local_ip(use_ipv6=False):
    if use_ipv6:
        try:
            s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            s.connect(("2001:4860:4860::8888", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            pass

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def main():
    app = QApplication(sys.argv)
    game = GameWindow()
    game.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()