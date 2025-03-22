from PyQt5.QtWidgets import QGraphicsItem
from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtGui import QPainter, QPen, QRadialGradient, QFont, QColor
import math

class CellUnit(QGraphicsItem):
    """Base class for all cell units in the game"""
    
    def __init__(self, x, y, cell_type, points=10, radius = 30):  # zmieniono "strength" na "points" i ustawiono domyślnie na 10
        super().__init__()
        self.x = x
        self.y = y
        self.radius = radius
        self.cell_type = cell_type  # e.g., "player", "enemy", "neutral"
        self.points = points  # punkty to podstawowa waluta
        self.strength = (self.points // 10) + 1  # strength wynika z punktów
        self.connections = []  # List of connected cells
        self.highlighted = False  # Nowy atrybut określający czy komórka jest podświetlona
        
    def setHighlighted(self, highlighted):
        """Ustawia stan podświetlenia komórki"""
        if self.highlighted != highlighted:
            self.highlighted = highlighted
            self.update()  # Odświeża wygląd komórki
    
    def boundingRect(self):
        """Define the bounding rectangle for the cell"""
        effective_radius = self.radius * (1 + 0.2 * (self.strength - 1))  # łagodniejszy wzrost promienia
        return QRectF(self.x - effective_radius - 10, self.y - effective_radius - 10, 
                      effective_radius * 2 + 20, effective_radius * 2 + 20)
    
    def shape(self):
        # Zwracamy ścieżkę będącą okręgiem o promieniu effective_radius
        from PyQt5.QtGui import QPainterPath
        path = QPainterPath()
        effective_radius = self.radius * (1 + 0.2 * (self.strength - 1))
        path.addEllipse(QPointF(self.x, self.y), effective_radius, effective_radius)
        return path
    
    def paint(self, painter, option, widget):
        """Draw the cell with proper color and effects"""
        effective_radius = self.radius * (1 + 0.2 * (self.strength - 1))  # łagodniejszy wzrost promienia
        # Set color based on cell type
        if self.cell_type == "player":
            base_color = QColor(0, 200, 100)  # Green for player
        elif self.cell_type == "enemy":
            base_color = QColor(200, 50, 50)  # Red for enemy
        elif self.cell_type == "neutral":
            base_color = QColor(200, 150, 0)  # Yellow/orange for neutral
            
        # Create gradient for cell
        gradient = QRadialGradient(self.x, self.y, effective_radius)
        gradient.setColorAt(0, base_color.lighter(150))
        gradient.setColorAt(0.8, base_color)
        gradient.setColorAt(1, base_color.darker(150))
        
        # Draw cell
        if self.highlighted:
            # Jeśli komórka jest podświetlona, rysujemy jasną obwódkę
            painter.setPen(QPen(Qt.yellow, 4))
        else:
            painter.setPen(QPen(Qt.white, 2))
            
        painter.setBrush(gradient)
        painter.drawEllipse(QRectF(self.x - effective_radius, self.y - effective_radius, 
                                   effective_radius * 2, effective_radius * 2))
        
        # Rysowanie dużego, białego napisu z liczbą punktów wyśrodkowanego w całej komórce
        # Oblicz dynamicznie rozmiar czcionki w zależności od liczby cyfr w punktach
        font_size = int(effective_radius / 1.5)
        if len(str(self.points)) > 2:
            font_size = int(effective_radius / 2)
        font = QFont('Arial', font_size)
        painter.setFont(font)
        painter.setPen(Qt.white)
        text_rect = QRectF(self.x - effective_radius, self.y - effective_radius, effective_radius * 2, effective_radius * 2)
        painter.drawText(text_rect, Qt.AlignCenter, str(self.points))
        
        # Rysowanie wskaźników siły (kropki) z uwzględnieniem stanu mostu:
        # Każda kropka reprezentuje jeden poziom siły (maksymalnie 9).
        # Jeśli most został już rozpoczęty, rysujemy obrys zamiast wypełnienia.
        used_dots = sum(1 for conn in self.connections if conn.source_cell is self)
        total_dots = min(self.strength, 9)
        rows = math.ceil(total_dots / 3)
        effective_radius = self.radius * (1 + 0.2 * (self.strength - 1))
        dot_radius = effective_radius / 10
        spacing = effective_radius / 3
        count_dot = 0
        for row in range(rows):
            row_dots = 3 if row < rows - 1 else total_dots - row * 3
            y_dotted = self.y + effective_radius * (0.5 + row * 0.15)
            if y_dotted + dot_radius > self.y + effective_radius:
                y_dotted = self.y + effective_radius - dot_radius
            for col in range(row_dots):
                x_dotted = self.x + (col - (row_dots - 1) / 2) * spacing
                # Jeśli count_dot >= total_dots - used_dots, to rysujemy obrys (most od prawej)
                if count_dot >= total_dots - used_dots:
                    painter.setPen(QPen(Qt.white, 1))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(QRectF(x_dotted - dot_radius, y_dotted - dot_radius,
                                               dot_radius * 2, dot_radius * 2))
                else:
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(Qt.white)
                    painter.drawEllipse(QRectF(x_dotted - dot_radius, y_dotted - dot_radius,
                                               dot_radius * 2, dot_radius * 2))
                count_dot += 1

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
        self.dots = []