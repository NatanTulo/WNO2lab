import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QGraphicsView, QMainWindow, QDockWidget, QTextEdit, QMessageBox

from config import WINDOW_WIDTH, WINDOW_HEIGHT, POWERUP_FREEZE, POWERUP_TAKEOVER, POWERUP_ADD_POINTS
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
        
        # Utworzenie loggera
        self.logger = Logger(max_lines=100)
        
        # Utworzenie widoku loggera w docku
        self.log_dock = QDockWidget("Log", self)
        # Umożliwiamy zamykanie, poruszanie i oddokowywanie
        self.log_dock.setFeatures(QDockWidget.DockWidgetClosable | 
                                  QDockWidget.DockWidgetMovable | 
                                  QDockWidget.DockWidgetFloatable)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_dock.setWidget(self.log_view)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        # Ustawienie początkowej wysokości loggera na 100 pikseli (dock automatycznie się rozmiaruje później)
        self.resizeDocks([self.log_dock], [100], Qt.Vertical)
        self.logger.set_text_edit(self.log_view)
        
        # Dodaj pasek menu z akcją przełączania widoku logów
        menu_bar = self.menuBar()
        view_menu = menu_bar.addMenu("Widok")
        self.toggle_log_action = view_menu.addAction("Pokaż/Ukryj Logi")
        self.toggle_log_action.setCheckable(True)
        self.toggle_log_action.setChecked(True)
        self.toggle_log_action.triggered.connect(self.toggle_log_dock)
        
        # Nowe menu Powerupy
        powerup_menu = menu_bar.addMenu("Powerupy")
        freeze_action = powerup_menu.addAction("Zamrożenie komórki")
        takeover_action = powerup_menu.addAction("Przejęcie komórki")
        addpoints_action = powerup_menu.addAction("Dodaj 10 punktów")
        freeze_action.triggered.connect(lambda: self.activate_powerup(POWERUP_FREEZE))
        takeover_action.triggered.connect(lambda: self.activate_powerup(POWERUP_TAKEOVER))
        addpoints_action.triggered.connect(lambda: self.activate_powerup(POWERUP_ADD_POINTS))
        
        # Tworzenie scen
        self.menu_scene = MenuScene()
        self.menu_scene.logger = self.logger  # przekazanie loggera do menu
        self.game_scene = None
        self.editor_scene = None  # Nowy atrybut dla sceny edytora
        
        # Konfiguracja widoku z dynamicznym skalowaniem
        self.view = DynamicGraphicsView()
        self.view.setRenderHints(self.view.renderHints())
        self.view.setViewportUpdateMode(self.view.FullViewportUpdate)
        self.setCentralWidget(self.view)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        
        # Połączenie sygnałów z menu
        self.menu_scene.level_selected = self.start_game
        self.menu_scene.editor_selected = self.start_editor  # Nowe połączenie dla edytora
        
        # Rozpoczęcie od menu
        self.show_menu()
        
        # Przykładowe logowanie
        self.logger.log("Aplikacja uruchomiona.")
        
    def toggle_log_dock(self, visible):
        if visible:
            self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
            self.log_dock.show()
        else:
            self.log_dock.hide()
        
    def show_menu(self):
        # Zatrzymaj timery gry, jeśli istnieją
        if self.game_scene:
            self.game_scene.timer.stop()
            self.game_scene.points_timer.stop()
            
        # Przełącz widok na scenę menu
        self.view.setScene(self.menu_scene)
        
    def start_game(self, level_id):
        self.game_scene = GameScene()
        self.game_scene.logger = self.logger  # ustawienie loggera dla gry
        self.view.setScene(self.game_scene)
        self.game_scene.initialize_level(level_id)
        # Ustawienie trybu turowego pobrane z menu
        if self.menu_scene.turn_based:
            self.game_scene.turn_based_mode = True
            self.game_scene.start_turn_timer()
        self.game_scene.timer.start(16)
        self.game_scene.points_timer.start(2000)
        
    def start_editor(self, level_id):
        # Tworzenie i wyświetlanie edytora poziomów
        self.editor_scene = LevelEditorScene(level_id)
        self.editor_scene.logger = self.logger  # ustawienie loggera dla edytora
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