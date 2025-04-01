import math
import time

from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtGui import QPainterPath, QPen, QRadialGradient, QFont, QColor
from PyQt5.QtWidgets import QGraphicsItem

from config import DEFAULT_CELL_RADIUS, POINTS_PER_STRENGTH, COLOR_PLAYER, COLOR_ENEMY, COLOR_NEUTRAL, FONT_FAMILY, COLOR_FROZEN_OUTLINE

class CellUnit(QGraphicsItem):
    """Base class for all cell units in the game"""

    def __init__(self, x, y, cell_type, points=10, radius=DEFAULT_CELL_RADIUS):
        super().__init__()
        self.x = x
        self.y = y
        self.radius = radius
        self.cell_type = cell_type
        self.points = points
        self.strength = (self.points // POINTS_PER_STRENGTH) + 1
        self.connections = []
        self.highlighted = False
        self.frozen = False
        self.freeze_end_time = 0

    def setHighlighted(self, highlighted):
        """Ustawia stan podświetlenia komórki"""
        if self.highlighted != highlighted:
            self.highlighted = highlighted
            self.update()

    def boundingRect(self):
        """Define the bounding rectangle for the cell"""
        effective_radius = self.radius * (1 + 0.2 * (self.strength - 1))
        return QRectF(self.x - effective_radius - 10, self.y - effective_radius - 10,
                      effective_radius * 2 + 20, effective_radius * 2 + 20)

    def shape(self):
        path = QPainterPath()
        effective_radius = self.radius * (1 + 0.2 * (self.strength - 1))
        path.addEllipse(QPointF(self.x, self.y), effective_radius, effective_radius)
        return path

    def paint(self, painter, option, widget):
        """Draw the cell with proper color and effects"""
        effective_radius = self.radius * (1 + 0.2 * (self.strength - 1))
        if self.cell_type == "player":
            base_color = COLOR_PLAYER
        elif self.cell_type == "enemy":
            base_color = COLOR_ENEMY
        elif self.cell_type == "neutral":
            base_color = COLOR_NEUTRAL

        gradient = QRadialGradient(self.x, self.y, effective_radius)
        gradient.setColorAt(0, base_color.lighter(150))
        gradient.setColorAt(0.8, base_color)
        gradient.setColorAt(1, base_color.darker(150))

        if self.highlighted:
            painter.setPen(QPen(Qt.yellow, 4))
        else:
            painter.setPen(QPen(Qt.white, 2))

        painter.setBrush(gradient)
        painter.drawEllipse(QRectF(self.x - effective_radius, self.y - effective_radius,
                                   effective_radius * 2, effective_radius * 2))

        font_size = int(effective_radius / 1.5)
        if len(str(self.points)) > 2:
            font_size = int(effective_radius / 2)
        font = QFont(FONT_FAMILY, font_size)
        painter.setFont(font)
        painter.setPen(Qt.white)
        text_rect = QRectF(self.x - effective_radius, self.y - effective_radius, effective_radius * 2, effective_radius * 2)
        painter.drawText(text_rect, Qt.AlignCenter, str(self.points))

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

        if self.frozen:
            current_time = time.time()
            if current_time < self.freeze_end_time:
                painter.setPen(QPen(COLOR_FROZEN_OUTLINE, 4))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QRectF(self.x - effective_radius, self.y - effective_radius,
                                           effective_radius * 2, effective_radius * 2))
                remaining = max(0, int(self.freeze_end_time - current_time))
                counter_text = str(remaining)
                font = QFont(FONT_FAMILY, int(effective_radius / 2))
                painter.setFont(font)
                painter.setPen(QPen(QColor(0, 150, 255), 2))
                text_rect = QRectF(self.x + effective_radius - 20, self.y + effective_radius - 20, 40, 40)
                painter.drawText(text_rect, Qt.AlignCenter, counter_text)
            else:
                self.frozen = False
                self.freeze_end_time = 0
                self.update()

    def add_point(self):
        """Dodaje punkt do komórki oraz aktualizuje siłę"""
        if self.frozen:
            return
        self.points += 1
        self.strength = (self.points // POINTS_PER_STRENGTH) + 1
        self.update()
        
    def get_outgoing_connections_count(self):
        """Zwraca liczbę połączeń wychodzących z komórki"""
        return sum(1 for conn in self.connections if conn.source_cell is self)
        
    def can_create_new_connection(self):
        """Sprawdza czy komórka może utworzyć nowe połączenie"""
        return self.get_outgoing_connections_count() < self.strength

class CellConnection:
    """Class to represent connections between cells"""

    def __init__(self, source_cell, target_cell, connection_type="neutral"):
        self.source_cell = source_cell
        self.target_cell = target_cell
        self.connection_type = connection_type
        self.dots = []