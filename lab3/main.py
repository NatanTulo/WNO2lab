import sys
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsItem, QMainWindow
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QRadialGradient


class CellUnit(QGraphicsItem):
    """Base class for all cell units in the game"""
    
    def __init__(self, x, y, radius, cell_type, strength=1):
        super().__init__()
        self.x = x
        self.y = y
        self.radius = radius
        self.cell_type = cell_type  # e.g., "player", "enemy", "neutral"
        self.strength = strength  # Number of dots inside
        self.connections = []  # List of connected cells
        self.pulse_animation = 0  # For pulsing effect
        
    def boundingRect(self):
        """Define the bounding rectangle for the cell"""
        return QRectF(self.x - self.radius - 10, self.y - self.radius - 10, 
                     self.radius * 2 + 20, self.radius * 2 + 20)
    
    def paint(self, painter, option, widget):
        """Draw the cell with proper color and effects"""
        # Set color based on cell type
        if self.cell_type == "player":
            base_color = QColor(0, 200, 100)  # Green for player
        elif self.cell_type == "enemy":
            base_color = QColor(200, 50, 50)  # Red for enemy
        elif self.cell_type == "neutral":
            base_color = QColor(200, 150, 0)  # Yellow/orange for neutral
            
        # Create gradient for cell
        gradient = QRadialGradient(self.x, self.y, self.radius)
        gradient.setColorAt(0, base_color.lighter(150))
        gradient.setColorAt(0.8, base_color)
        gradient.setColorAt(1, base_color.darker(150))
        
        # Draw cell
        painter.setPen(QPen(Qt.white, 2))
        painter.setBrush(gradient)
        painter.drawEllipse(self.x - self.radius, self.y - self.radius, 
                           self.radius * 2, self.radius * 2)
        
        # Draw strength indicators (dots)
        dot_radius = self.radius / 10
        spacing = self.radius / 4
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.white)
        
        for i in range(min(self.strength, 9)):  # Max 9 dots
            if i < 3:  # First row
                dot_x = self.x + (i - 1) * spacing
                dot_y = self.y + self.radius / 3
            elif i < 6:  # Second row
                dot_x = self.x + (i - 4) * spacing
                dot_y = self.y
            else:  # Third row
                dot_x = self.x + (i - 7) * spacing
                dot_y = self.y - self.radius / 3
                
            painter.drawEllipse(QRectF(dot_x - dot_radius, dot_y - dot_radius, 
                                       dot_radius * 2, dot_radius * 2))
    
    def update_animation(self):
        """Update pulse animation state"""
        self.pulse_animation = (self.pulse_animation + 1) % 60
        self.update()
        
    def increase_strength(self):
        """Increase cell's strength"""
        self.strength += 1
        
    def decrease_strength(self):
        """Decrease cell's strength"""
        self.strength = max(0, self.strength - 1)


class CellConnection:
    """Class to represent connections between cells"""
    
    def __init__(self, source_cell, target_cell, connection_type="neutral"):
        self.source_cell = source_cell
        self.target_cell = target_cell
        self.connection_type = connection_type  # "player", "enemy", "neutral"
        self.flow_animation = 0
        self.active = False
        
    def update_animation(self):
        """Update flow animation state"""
        if self.active:
            self.flow_animation = (self.flow_animation + 1) % 60
        
    def set_type(self, new_type):
        """Change the connection type"""
        self.connection_type = new_type
        
    def toggle_active(self):
        """Toggle whether connection is actively transferring units"""
        self.active = not self.active


class GameScene(QGraphicsScene):
    """Main game scene class"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 800, 600)
        self.cells = []
        self.connections = []
        self.current_level = 1
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.selected_cell = None
        
    def drawBackground(self, painter, rect):
        # Ustawienie radialnego gradientu: środek jasny fiolent, krawędzie ciemny fiolent
        center = self.sceneRect().center()
        radius = max(self.sceneRect().width(), self.sceneRect().height())
        gradient = QRadialGradient(center, radius)
        gradient.setColorAt(0, QColor(230, 190, 255))  # Jasny fiolent
        gradient.setColorAt(1, QColor(100, 0, 150))      # Ciemny fiolent
        painter.fillRect(rect, gradient)
    
    def initialize_level(self, level_number):
        """Set up cells and connections for a specific level"""
        # Clear existing items
        self.clear()
        self.cells = []
        self.connections = []
        
        # Example level setup - you would load actual level data from a file
        if level_number == 1:
            # Create player cells
            player_cell1 = CellUnit(200, 300, 40, "player", 3)
            player_cell2 = CellUnit(150, 450, 30, "player", 2)
            
            # Create enemy cells
            enemy_cell1 = CellUnit(600, 250, 40, "enemy", 3)
            enemy_cell2 = CellUnit(500, 400, 30, "enemy", 2)
            
            # Create neutral cells
            neutral_cell = CellUnit(350, 350, 35, "neutral", 2)
            
            # Add cells to scene
            for cell in [player_cell1, player_cell2, enemy_cell1, enemy_cell2, neutral_cell]:
                self.cells.append(cell)
                self.addItem(cell)
                
            # Create connections
            self.create_connection(player_cell1, player_cell2, "player")
            self.create_connection(player_cell1, neutral_cell, "neutral")
            self.create_connection(neutral_cell, enemy_cell1, "neutral")
            self.create_connection(enemy_cell1, enemy_cell2, "enemy")
            self.create_connection(neutral_cell, enemy_cell2, "neutral")
            
    def create_connection(self, source, target, conn_type):
        """Create a connection between two cells"""
        connection = CellConnection(source, target, conn_type)
        source.connections.append(connection)
        target.connections.append(connection)
        self.connections.append(connection)
        return connection
        
    def update_game(self):
        """Main game update loop"""
        # Update cell animations
        for cell in self.cells:
            cell.update_animation()
            
        # Update connection animations and handle unit transfers
        for conn in self.connections:
            conn.update_animation()
            if conn.active:
                # Transfer units logic would go here
                pass
                
        # Check win/lose conditions
        self.check_game_state()
                
    def mousePressEvent(self, event):
        """Handle mouse press events for cell selection"""
        clicked_item = self.itemAt(event.scenePos(), QTransform())
        
        if isinstance(clicked_item, CellUnit):
            if clicked_item.cell_type == "player":
                if self.selected_cell is None:
                    # Select this cell
                    self.selected_cell = clicked_item
                else:
                    # Already had a cell selected, try to create connection
                    self.try_create_player_connection(self.selected_cell, clicked_item)
                    self.selected_cell = None
        
    def try_create_player_connection(self, cell1, cell2):
        """Try to create or activate a connection between player cells"""
        # Check if connection already exists
        for conn in self.connections:
            if ((conn.source_cell == cell1 and conn.target_cell == cell2) or
                (conn.source_cell == cell2 and conn.target_cell == cell1)):
                # Connection exists, toggle it
                conn.toggle_active()
                return
                
        # No existing connection, create if cells are close enough
        # This would need proximity calculation logic
        
    def check_game_state(self):
        """Check if player has won or lost the level"""
        player_cells = sum(1 for cell in self.cells if cell.cell_type == "player")
        enemy_cells = sum(1 for cell in self.cells if cell.cell_type == "enemy")
        
        if player_cells == 0:
            # Game over - player lost
            self.game_over(False)
        elif enemy_cells == 0:
            # Game over - player won
            self.game_over(True)
    
    def game_over(self, victory):
        """Handle end of game"""
        self.timer.stop()
        # Display victory/defeat message and options to retry or go to next level


class GameWindow(QMainWindow):
    """Main game window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cell Expansion Wars")
        
        # Create the view and scene
        self.scene = GameScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        self.setCentralWidget(self.view)
        self.resize(850, 650)
        
        # Start a new game
        self.start_game()
        
    def start_game(self):
        """Initialize and start a new game"""
        self.scene.initialize_level(1)
        self.scene.timer.start(16)  # ~60 FPS


def main():
    app = QApplication(sys.argv)
    game = GameWindow()
    game.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()