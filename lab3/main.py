import sys
from PyQt5.QtWidgets import QApplication, QGraphicsView, QMainWindow
from game_scene import GameScene

class GameWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cell Expansion Wars")
        self.scene = GameScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(self.view.renderHints())
        self.view.setViewportUpdateMode(self.view.FullViewportUpdate)
        self.setCentralWidget(self.view)
        self.resize(850,650)
        self.start_game()
        
    def start_game(self):
        self.scene.initialize_level(1)
        self.scene.timer.start(16)

def main():
    app = QApplication(sys.argv)
    game = GameWindow()
    game.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()