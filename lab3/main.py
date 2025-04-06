import sys
import os
import json
import tempfile
import datetime
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QGraphicsView, QMainWindow, QDockWidget, QTextEdit, QMessageBox, QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel, QComboBox
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

    def toggle_log_dock(self, visible):
        if visible:
            self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
            self.log_dock.show()
        else:
            self.log_dock.hide()

    def show_menu(self):
        if self.game_scene:
            self.game_scene.timer.stop()
            self.game_scene.points_timer.stop()

        self.view.setScene(self.menu_scene)

    def start_game(self, level_id):
        import os
        self.game_scene = GameScene()
        self.game_scene.logger = self.logger
        self.game_scene.current_level = level_id
        # Aktualizacja ścieżek do folderu saves
        quicksave_xml = os.path.join("saves", f"quicksave_level{level_id}.xml")
        quicksave_json = os.path.join("saves", f"quicksave_level{level_id}.json")
        if os.path.exists(quicksave_xml) or os.path.exists(quicksave_json):
            result = QMessageBox.question(None, "Wczytaj quicksave?",
                f"Znaleziono quicksave dla poziomu {level_id}. Czy chcesz z niego skorzystać?",
                QMessageBox.Yes | QMessageBox.No)
            if result == QMessageBox.Yes:
                if not self.game_scene.quickload():
                    # Jeśli wczytanie quicksave'a nie powiodło się, pokazujemy menu zamiast ładować świeży poziom
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
        else:
            self.game_scene.single_player = False
        if self.menu_scene.turn_based:
            self.game_scene.turn_based_mode = True
            self.game_scene.start_turn_timer()
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
        # Dodanie rozwijanej listy do wyboru poziomu
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
        # Dodajemy rozwijaną listę do wyboru poziomu
        level_combo = QComboBox()
        level_combo.addItems(["Poziom 1", "Poziom 2", "Poziom 3"])
        layout.addWidget(level_combo)
        list_widget = QListWidget()
        layout.addWidget(list_widget)
        items = []
        def update_list():
            list_widget.clear()
            items.clear()
            selected_level = int(level_combo.currentText().split()[1])
            documents = list(game_history.replays_collection.find({"level": selected_level}))
            # Sortuj dokumenty według znacznika czasu (najpierw najnowsze)
            documents = sorted(documents, key=lambda doc: doc.get("moves", [{}])[0].get("timestamp", 0), reverse=True)
            for doc in documents:
                ts = doc.get("moves", [{}])[0].get("timestamp", 0)
                try:
                    time_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    time_str = "Brak daty"
                id_short = str(doc["_id"])[:8]
                display_text = f"{time_str} - {id_short}"
                list_widget.addItem(display_text)
                items.append(doc)
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
            if idx >= 0:
                selected_doc[0] = items[idx]
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

def main():
    app = QApplication(sys.argv)
    game = GameWindow()
    game.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()