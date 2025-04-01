import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QGraphicsView, QMainWindow, QDockWidget, QTextEdit, QMessageBox

from config import WINDOW_WIDTH, WINDOW_HEIGHT, POWERUP_FREEZE, POWERUP_TAKEOVER, POWERUP_ADD_POINTS, POWERUP_NEW_CELL
from game_scene import GameScene
from level_editor_scene import LevelEditorScene
from logger import Logger
from menu_scene import MenuScene

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
        self.log_dock.setFeatures(QDockWidget.DockWidgetClosable |
                                  QDockWidget.DockWidgetMovable |
                                  QDockWidget.DockWidgetFloatable)
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
        freeze_action.triggered.connect(lambda: self.activate_powerup(POWERUP_FREEZE))
        takeover_action.triggered.connect(lambda: self.activate_powerup(POWERUP_TAKEOVER))
        addpoints_action.triggered.connect(lambda: self.activate_powerup(POWERUP_ADD_POINTS))
        newcell_action.triggered.connect(lambda: self.activate_powerup(POWERUP_NEW_CELL))

        self.menu_scene = MenuScene()
        self.menu_scene.logger = self.logger
        self.game_scene = None
        self.editor_scene = None

        self.view = DynamicGraphicsView()
        self.view.setRenderHints(self.view.renderHints())
        self.view.setViewportUpdateMode(self.view.FullViewportUpdate)
        self.setCentralWidget(self.view)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.menu_scene.level_selected = self.start_game
        self.menu_scene.editor_selected = self.start_editor

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
        self.game_scene = GameScene()
        self.game_scene.logger = self.logger
        self.view.setScene(self.game_scene)
        self.game_scene.initialize_level(level_id)
        # Ustawienie trybu single player w zależności od wybranej opcji
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

    def activate_powerup(self, powerup_type):
        if self.game_scene:
            self.game_scene.activate_powerup(powerup_type)
        else:
            QMessageBox.information(self, "Powerup", "Brak aktywnej sceny gry.")

def main():
    app = QApplication(sys.argv)
    game = GameWindow()
    game.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()