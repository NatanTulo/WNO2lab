import sys
from PyQt5.QtWidgets import QApplication, QGraphicsView, QMainWindow
from PyQt5.QtCore import Qt
from game_scene import GameScene
from menu_scene import MenuScene

class GameWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cell Expansion Wars")
        
        # Tworzenie scen
        self.menu_scene = MenuScene()
        self.game_scene = None
        
        # Konfiguracja widoku
        self.view = QGraphicsView()
        self.view.setRenderHints(self.view.renderHints())
        self.view.setViewportUpdateMode(self.view.FullViewportUpdate)
        self.setCentralWidget(self.view)
        self.resize(850, 650)
        
        # Połączenie sygnałów z menu
        self.menu_scene.level_selected = self.start_game
        
        # Rozpoczęcie od menu
        self.show_menu()
        
    def show_menu(self):
        # Zatrzymaj timery gry, jeśli istnieją
        if self.game_scene:
            self.game_scene.timer.stop()
            self.game_scene.points_timer.stop()
            
        # Przełącz widok na scenę menu
        self.view.setScene(self.menu_scene)
        
    def start_game(self, level_id):
        self.game_scene = GameScene()
        self.view.setScene(self.game_scene)
        self.game_scene.initialize_level(level_id)
        self.game_scene.timer.start(16)
        self.game_scene.points_timer.start(2000)

def main():
    app = QApplication(sys.argv)
    game = GameWindow()
    game.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()