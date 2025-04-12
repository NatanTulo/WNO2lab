import sys
import os
import json
import tempfile
import datetime
import socket
import threading

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QGraphicsView, QMainWindow, QDockWidget, 
    QTextEdit, QMessageBox, QDialog, QVBoxLayout, QListWidget, 
    QPushButton, QHBoxLayout, QLabel, QComboBox, QListWidgetItem
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
        self.network_listener_started = False  # nowa flaga dla TCP/IP
        self.previous_turn_based_state = None  # zapamiętuje pierwotny stan trybu turowego

    def toggle_log_dock(self, visible):
        if visible:
            self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
            self.log_dock.show()
        else:
            self.log_dock.hide()

    def show_menu(self):
        if self.game_scene:
            # Zatrzymanie wszystkich timerów gry
            self.game_scene.timer.stop()
            self.game_scene.points_timer.stop()
            
            # Zatrzymanie timera tur
            if hasattr(self.game_scene, 'turn_timer') and self.game_scene.turn_timer:
                self.game_scene.turn_timer.stop()
                try:
                    self.game_scene.turn_timer.timeout.disconnect()
                except (TypeError, RuntimeError):
                    pass  # Ignoruj błąd jeśli nie ma podłączonych sygnałów
            
            # Zatrzymanie timera przeciwnika
            if hasattr(self.game_scene, 'enemy_timer') and self.game_scene.enemy_timer:
                self.game_scene.enemy_timer.stop()
                try:
                    self.game_scene.enemy_timer.timeout.disconnect()
                except (TypeError, RuntimeError):
                    pass
            
            # Zatrzymanie timera podpowiedzi
            if hasattr(self.game_scene, 'hint_timer') and self.game_scene.hint_timer:
                self.game_scene.hint_timer.stop()
                try:
                    self.game_scene.hint_timer.timeout.disconnect()
                except (TypeError, RuntimeError):
                    pass
            
            if self.logger:
                self.logger.log("GameWindow: Wszystkie timery zatrzymane, przejście do menu.")

        self.view.setScene(self.menu_scene)

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
            # Przy innych trybach przywracamy stan z przełącznika
            if self.previous_turn_based_state is not None:
                self.game_scene.turn_based_mode = self.previous_turn_based_state
                self.previous_turn_based_state = None
            else:
                self.game_scene.turn_based_mode = self.menu_scene.turn_based
        elif self.menu_scene.game_mode == "gra sieciowa":
            try:
                remote_ip = self.menu_scene.ip_lineedit.text().strip()
                port_text = self.menu_scene.port_lineedit.text().strip()
                if not remote_ip or not port_text:
                    raise ValueError("Pola IP lub Port są puste.")
                remote_port = int(port_text)
                self.start_network_listener(remote_port)
                local_ip = get_local_ip()
                message = f"Połączono gracza z adresu {local_ip}"
                self.send_network_message(remote_ip, remote_port, message)
            except Exception as e:
                if self.logger:
                    self.logger.log(f"Błąd konfiguracji sieciowej: {e}")
                self.show_menu()
                return
            # Ustawiamy lokalnie rolę gracza na "player" i informujemy przeciwnika
            self.game_scene.is_multiplayer = True
            self.game_scene.multiplayer_role = "player"
            self.send_network_message(remote_ip, remote_port, "set_role;enemy")
            # Zapamiętujemy stan trybu turowego wybrany przez użytkownika
            if self.previous_turn_based_state is None:
                self.previous_turn_based_state = self.menu_scene.turn_based
            self.game_scene.turn_based_mode = True
            self.game_scene.single_player = False
            import random
            if self.logger:
                self.logger.log(f"Multiplayer role assigned: {self.game_scene.multiplayer_role}")
            # Ustaw callback wysyłający aktualizacje stanu gry
            self.game_scene.network_send_callback = lambda msg: self.send_network_message(remote_ip, remote_port, msg)
        else:
            # Przypadek dla trybu 2 graczy lokalnie
            if self.previous_turn_based_state is not None:
                self.game_scene.turn_based_mode = self.previous_turn_based_state
                self.previous_turn_based_state = None
            else:
                self.game_scene.turn_based_mode = self.menu_scene.turn_based
            self.game_scene.single_player = False
        self.game_scene.timer.start(16)
        self.game_scene.points_timer.start(2000)

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
        if replay_source == "NoSQL":
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
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Zmiana: nasłuchuj na wszystkich interfejsach, ustawiając adres "0.0.0.0"
            server_sock.bind(("0.0.0.0", port))
            server_sock.listen(5)
            while True:
                conn, addr = server_sock.accept()
                data = conn.recv(1024).decode("utf-8")
                if data:
                    if self.logger:
                        self.logger.log(f"Odebrano wiadomość z {addr}: {data}")
                    # Przekazujemy odebraną wiadomość do sceny gry
                    if self.game_scene:
                        self.game_scene.process_network_message(data)
                conn.close()
        except Exception as e:
            if self.logger:
                self.logger.log(f"Błąd nasłuchiwania TCP/IP: {e}")
        finally:
            server_sock.close()

    def send_network_message(self, ip, port, message):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((ip, port))
            sock.sendall(message.encode("utf-8"))
            sock.close()
            if self.logger:
                self.logger.log(f"Wysłano wiadomość do {ip}:{port}: {message}")
        except Exception as e:
            if self.logger:
                self.logger.log(f"Błąd wysyłania wiadomości do {ip}:{port}: {e}")

def get_local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # adres nie musi być osiągalny
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