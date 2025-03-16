import sys
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsItem, QMainWindow
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QRadialGradient, QFont, QTransform  # dodany import
import math  # dodany import

class CellUnit(QGraphicsItem):
    """Base class for all cell units in the game"""
    
    def __init__(self, x, y, radius, cell_type, points=10):  # zmieniono "strength" na "points" i ustawiono domyślnie na 10
        super().__init__()
        self.x = x
        self.y = y
        self.radius = radius
        self.cell_type = cell_type  # e.g., "player", "enemy", "neutral"
        self.points = points  # punkty to podstawowa waluta
        self.strength = (self.points // 10) + 1  # strength wynika z punktów
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
        
        # Rysowanie dużego, białego napisu z liczbą punktów wyśrodkowanego w całej komórce
        # Oblicz dynamicznie rozmiar czcionki w zależności od liczby cyfr w punktach
        font_size = int(self.radius / 1.5)
        if len(str(self.points)) > 2:
            font_size = int(self.radius / 2)
        font = QFont('Arial', font_size)
        painter.setFont(font)
        painter.setPen(Qt.white)
        text_rect = QRectF(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)
        painter.drawText(text_rect, Qt.AlignCenter, str(self.points))
        
        # Nowe rysowanie wskaźników siły (kropki) umieszczonych niżej, nie wychodzących poza obrys komórki
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.white)
        n_dots = min(self.strength, 9)
        rows = math.ceil(n_dots / 3)
        dot_radius = self.radius / 10
        spacing = self.radius / 3
        for row in range(rows):
            row_dots = 3 if row < rows - 1 else n_dots - row * 3
            y_dotted = self.y + self.radius * (0.5 + row * 0.15)  # pozycja w pionie przesunięta w dół
            # Upewnij się, że kropki nie wyjdą poza dolny obrys
            if y_dotted + dot_radius > self.y + self.radius:
                y_dotted = self.y + self.radius - dot_radius
            for col in range(row_dots):
                x_dotted = self.x + (col - (row_dots - 1) / 2) * spacing
                painter.drawEllipse(QRectF(x_dotted - dot_radius, y_dotted - dot_radius,
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
        
    def add_point(self):
        """Dodaje punkt do komórki oraz aktualizuje siłę"""
        self.points += 1
        self.strength = (self.points // 10) + 1
        self.update()


class CellConnection:
    """Class to represent connections between cells"""
    
    def __init__(self, source_cell, target_cell, connection_type="neutral"):
        self.source_cell = source_cell
        self.target_cell = target_cell
        self.connection_type = connection_type  # "player", "enemy", "neutral"
        self.flow_animation = 0
        self.active = False
        # Dodano listę dla animowanych kropek w mostach
        self.dots = []
        
    def update_animation(self):
        """Update flow animation state"""
        if self.active:
            self.flow_animation = (self.flow_animation + 1) % 60


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
        self.drag_start_cell = None  
        self.drag_current_pos = None  # Nowa zmienna do śledzenia pozycji kursora podczas przeciągania
        
        # Nowy timer do dodawania punktów co 1000 ms
        self.points_timer = QTimer()
        self.points_timer.timeout.connect(self.add_points)
        self.points_timer.start(1000)
        
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
            if conn.connection_type == "player":
                # Aktualizacja postępu każdej kropki
                finished = []
                for i in range(len(conn.dots)):
                    conn.dots[i] += 0.016  # przybliżony przyrost dla 60 FPS
                    if conn.dots[i] >= 1.0:
                        # Po dotarciu kropki do celu dodajemy 1 punkt do komórki docelowej
                        conn.target_cell.points += 1
                        conn.target_cell.update()
                        finished.append(i)
                # Usuwanie kropek, które zakończyły podróż
                for index in sorted(finished, reverse=True):
                    del conn.dots[index]
                
        # Check win/lose conditions
        self.check_game_state()
                
    def mousePressEvent(self, event):
        clicked_item = self.itemAt(event.scenePos(), QTransform())
        if isinstance(clicked_item, CellUnit) and clicked_item.cell_type == "player":
            self.drag_start_cell = clicked_item
        else:
            # Naciśnięcie lpm poza komórką – próba przecięcia mostu
            P = event.scenePos()
            for conn in self.connections:
                if conn.connection_type == "player":
                    A = QPointF(conn.source_cell.x, conn.source_cell.y)
                    B = QPointF(conn.target_cell.x, conn.target_cell.y)
                    AB = QPointF(B.x() - A.x(), B.y() - A.y())
                    AP = QPointF(P.x() - A.x(), P.y() - A.y())
                    ab2 = AB.x() ** 2 + AB.y() ** 2
                    if ab2 == 0:
                        continue
                    t = (AP.x() * AB.x() + AP.y() * AB.y()) / ab2
                    if t < 0 or t > 1:
                        continue
                    Qx = A.x() + t * AB.x()
                    Qy = A.y() + t * AB.y()
                    dist = math.hypot(P.x() - Qx, P.y() - Qy)
                    if dist < 5:  # próg wykrywania przecięcia
                        if conn in self.connections:
                            self.connections.remove(conn)
                        if conn in conn.source_cell.connections:
                            conn.source_cell.connections.remove(conn)
                        if conn in conn.target_cell.connections:
                            conn.target_cell.connections.remove(conn)
                        cost = getattr(conn, "cost", 0)
                        source_points = round(t * cost)
                        target_points = cost - source_points
                        conn.source_cell.points += source_points
                        conn.target_cell.points += target_points
                        conn.source_cell.strength = (conn.source_cell.points // 10) + 1
                        conn.target_cell.strength = (conn.target_cell.points // 10) + 1
                        conn.source_cell.update()
                        conn.target_cell.update()
                        break
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if self.drag_start_cell:
            self.drag_current_pos = event.scenePos()
            # Sprawdzenie przecięcia kursorem dowolnego mostu gracza
            for conn in self.connections:
                if conn.connection_type == "player":
                    A = QPointF(conn.source_cell.x, conn.source_cell.y)
                    B = QPointF(conn.target_cell.x, conn.target_cell.y)
                    P = self.drag_current_pos
                    AB = QPointF(B.x() - A.x(), B.y() - A.y())
                    AP = QPointF(P.x() - A.x(), P.y() - A.y())
                    ab2 = AB.x() ** 2 + AB.y() ** 2
                    if ab2 == 0:
                        continue
                    t = (AP.x() * AB.x() + AP.y() * AB.y()) / ab2
                    if t < 0 or t > 1:
                        continue
                    Qx = A.x() + t * AB.x()
                    Qy = A.y() + t * AB.y()
                    dist = math.hypot(P.x() - Qx, P.y() - Qy)
                    if dist < 5:  # próg wykrywania przecięcia
                        # Usunięcie mostu
                        if conn in self.connections:
                            self.connections.remove(conn)
                        if conn in conn.source_cell.connections:
                            conn.source_cell.connections.remove(conn)
                        if conn in conn.target_cell.connections:
                            conn.target_cell.connections.remove(conn)
                        cost = getattr(conn, "cost", 0)
                        # Rozdzielenie punktów proporcjonalnie do pozycji przecięcia
                        source_points = round(t * cost)
                        target_points = cost - source_points
                        conn.source_cell.points += source_points
                        conn.target_cell.points += target_points
                        conn.source_cell.strength = (conn.source_cell.points // 10) + 1
                        conn.target_cell.strength = (conn.target_cell.points // 10) + 1
                        conn.source_cell.update()
                        conn.target_cell.update()
                        self.drag_start_cell = None
                        self.drag_current_pos = None
                        break
            self.update()
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Na zakończenie przeciągania sprawdza, czy zwolniono LPM nad inną własną komórką.
           Koszt budowy mostu jest zależny od odległości między komórkami."""
        if self.drag_start_cell is None:
            return
        release_item = self.itemAt(event.scenePos(), QTransform())
        if (isinstance(release_item, CellUnit) and
            release_item.cell_type == "player" and
            release_item != self.drag_start_cell):
            # Oblicz dystans między komórkami
            dx = release_item.x - self.drag_start_cell.x
            dy = release_item.y - self.drag_start_cell.y
            distance = math.hypot(dx, dy)
            cost = int(distance / 20)  # zmieniono obliczanie kosztu - usunięto minimalną wartość
            if self.drag_start_cell.points >= cost:
                # Odejmij punkty i zaktualizuj siłę
                self.drag_start_cell.points -= cost
                self.drag_start_cell.strength = (self.drag_start_cell.points // 10) + 1
                self.drag_start_cell.update()
                # Jeśli połączenie już istnieje, nie tworzymy nowego
                exists = any(((conn.source_cell == self.drag_start_cell and conn.target_cell == release_item) or
                              (conn.source_cell == release_item and conn.target_cell == self.drag_start_cell))
                              for conn in self.connections)
                if not exists:
                    new_conn = self.create_connection(self.drag_start_cell, release_item, "player")
                    new_conn.cost = cost  # zapis kosztu budowy mostu
        self.drag_start_cell = None
        self.drag_current_pos = None  # Reset pozycji kursora
        
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
        
    def add_points(self):
        """Dodaje 1 punkt do każdej komórki (oprócz neutralnych) co sekundę oraz przesyła kropki przez mosty gracza"""
        for cell in self.cells:
            if cell.cell_type != "neutral":
                cell.add_point()
        # Dla każdego mostu gracza przesyłamy kropkę, jeśli komórka źródłowa ma wystarczająco punktów
        for conn in self.connections:
            if conn.connection_type == "player":
                if conn.source_cell.points >= 1:
                    conn.source_cell.points -= 1
                    conn.source_cell.strength = (conn.source_cell.points // 10) + 1
                    conn.source_cell.update()
                    conn.dots.append(0)  # nowa kropka z postępem 0

    def drawForeground(self, painter, rect):
        if self.drag_start_cell and self.drag_current_pos:
            dx = self.drag_current_pos.x() - self.drag_start_cell.x
            dy = self.drag_current_pos.y() - self.drag_start_cell.y
            distance = math.hypot(dx, dy)
            cost = int(distance / 20)
            color = QColor(0, 255, 0) if self.drag_start_cell.points >= cost else QColor(255, 0, 0)
            painter.setPen(QPen(color, 2))
            painter.drawLine(QPointF(self.drag_start_cell.x, self.drag_start_cell.y), self.drag_current_pos)
        # Rysowanie wszystkich mostów jako ciemnozielone linie
        for conn in self.connections:
            source = QPointF(conn.source_cell.x, conn.source_cell.y)
            target = QPointF(conn.target_cell.x, conn.target_cell.y)
            painter.setPen(QPen(QColor(0,100,0), 3))
            painter.drawLine(source, target)
            # Rysujemy animowane, jaśniejsze zielone kropki tylko dla mostów budowanych przez gracza
            if conn.connection_type == "player":
                for progress in conn.dots:
                    x = conn.source_cell.x + progress * (conn.target_cell.x - conn.source_cell.x)
                    y = conn.source_cell.y + progress * (conn.target_cell.y - conn.source_cell.y)
                    dot_radius = 4  # promień kropki
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(144,238,144))
                    painter.drawEllipse(QRectF(x - dot_radius, y - dot_radius, dot_radius * 2, dot_radius * 2))


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