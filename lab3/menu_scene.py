from PyQt5.QtWidgets import QGraphicsScene, QGraphicsTextItem, QGraphicsRectItem
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QBrush, QPen, QFont, QLinearGradient
import json
import os

class MenuScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 800, 600)
        self.level_buttons = []
        self.levels_data = []
        self.load_levels()
        self.setup_menu()
        
    def load_levels(self):
        try:
            levels_path = os.path.join(os.path.dirname(__file__), 'levels.json')
            with open(levels_path, 'r') as f:
                self.levels_data = json.load(f)
        except Exception as e:
            print(f"Błąd wczytywania poziomów: {e}")
            # Domyślne poziomy w przypadku błędu wczytywania pliku
            self.levels_data = [{"name": "Poziom 1"}]
            
    def setup_menu(self):
        # Tytuł
        title = QGraphicsTextItem("Cell Expansion Wars")
        title.setFont(QFont("Arial", 36, QFont.Bold))
        title.setDefaultTextColor(Qt.white)
        
        # Wyśrodkowanie tytułu
        title_width = title.boundingRect().width()
        title.setPos((self.width() - title_width) / 2, 100)
        self.addItem(title)
        
        # Wybór poziomu
        level_title = QGraphicsTextItem("Wybierz poziom:")
        level_title.setFont(QFont("Arial", 24))
        level_title.setDefaultTextColor(Qt.white)
        
        # Wyśrodkowanie tekstu "Wybierz poziom"
        level_title_width = level_title.boundingRect().width()
        level_title.setPos((self.width() - level_title_width) / 2, 200)
        self.addItem(level_title)
        
        # Tworzenie przycisków poziomów
        y_pos = 250
        button_width = 300  # Szerszy przycisk dla tekstu
        
        for i, level in enumerate(self.levels_data):
            button_x = (self.width() - button_width) / 2  # Wyśrodkowanie przycisku
            level_name = level.get('name', f'Poziom {i+1}')
            button_text = f"Poziom {i+1}: {level_name}"
            
            button = self.create_button(button_text, button_x, y_pos, button_width)
            button.level_id = i + 1
            self.level_buttons.append(button)
            y_pos += 60
    
    def create_button(self, text, x, y, width=200):
        class Button(QGraphicsRectItem):
            def __init__(self, text, x, y, width, parent=None):
                super().__init__(x, y, width, 50, parent)
                self.setBrush(QBrush(QColor(50, 50, 150)))
                self.setPen(QPen(Qt.white, 2))

                # Dodanie tekstu
                self.text_item = QGraphicsTextItem(text, self)
                self.text_item.setDefaultTextColor(Qt.white)
                self.text_item.setFont(QFont("Arial", 14))

                # **Poprawione centrowanie tekstu**
                self.update_text_position()

                # Ustawienie kursora
                self.setCursor(Qt.PointingHandCursor)

            def update_text_position(self):
                """Poprawne centrowanie tekstu po dodaniu do przycisku"""
                text_rect = self.text_item.boundingRect()
                button_rect = self.rect()

                text_x = (button_rect.width() - text_rect.width()) / 2
                text_y = (button_rect.height() - text_rect.height()) / 2

                self.text_item.setPos(self.rect().x() + text_x, self.rect().y() + text_y)

        
        button = Button(text, x, y, width)
        self.addItem(button)
        return button
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.scenePos()
            clicked_items = self.items(pos)
            
            for item in clicked_items:
                if isinstance(item, QGraphicsRectItem) and hasattr(item, 'level_id') and item.level_id > 0:
                    self.level_selected(item.level_id)
                    return
        
        super().mousePressEvent(event)
    
    def level_selected(self, level_id):
        # Ta metoda będzie połączona z głównym oknem aby rozpocząć grę
        pass
        
    def drawBackground(self, painter, rect):
        # Rysowanie gradientowego tła podobnego do tła w GameScene
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(230, 190, 255))  # Jasny fiolet
        gradient.setColorAt(1, QColor(100, 0, 150))    # Ciemny fiolet
        painter.fillRect(rect, gradient)
