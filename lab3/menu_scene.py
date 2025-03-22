from PyQt5.QtWidgets import QGraphicsScene, QGraphicsTextItem, QGraphicsRectItem, QGraphicsItemGroup, QGraphicsPixmapItem
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QBrush, QPen, QFont, QLinearGradient, QPixmap
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
        self.editor_selected = None  # Nowy sygnał dla edytora
        
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
            button.left_rect.level_id = i + 1  # przypisujemy identyfikator poziomu tylko do lewego obszaru
            button.right_rect.level_id = i + 1  # przypisujemy również do prawego obszaru
            button.right_rect.is_edit_button = True  # oznaczamy jako przycisk edycji
            self.level_buttons.append(button)
            y_pos += 60
    
    def create_button(self, text, x, y, width=200):
        # Podział przycisku na lewą część z tekstem i prawą z ikoną
        class Button(QGraphicsItemGroup):
            def __init__(self, text, x, y, width, parent=None):
                super().__init__(parent)
                self.setFiltersChildEvents(False)  # zmienione z setHandlesChildEvents(False)
                height = 50
                right_width = height  # prawa część jako kwadrat
                left_width = width - right_width  # lewa część rozszerzona

                # Lewa część z tekstem
                self.left_rect = QGraphicsRectItem(x, y, left_width, height)
                self.left_rect.setBrush(QBrush(QColor(50, 50, 150)))
                self.left_rect.setPen(QPen(Qt.white, 2))
                self.left_rect.level_id = 0  # zostanie ustawione na konkretny poziom
                self.addToGroup(self.left_rect)

                self.text_item = QGraphicsTextItem(text, self.left_rect)
                self.text_item.setDefaultTextColor(Qt.white)
                self.text_item.setFont(QFont("Arial", 14))
                self.update_text_position(x, y, left_width, height)

                # Dodajemy utworzenie prawego prostokąta z ikoną
                self.right_rect = QGraphicsRectItem(x + left_width, y, right_width, height)
                self.right_rect.setBrush(QBrush(QColor(80, 80, 180)))
                self.right_rect.setPen(QPen(Qt.white, 2))
                self.right_rect.level_id = 0  # zostanie ustawione na konkretny poziom
                self.right_rect.is_edit_button = False  # domyślnie nie jest przyciskiem edycji
                self.addToGroup(self.right_rect)

                # Prawa część z ikoną (placeholder)
                pixmap_path = os.path.join(os.path.dirname(__file__), 'olowek.png')
                self.icon_item = QGraphicsPixmapItem(QPixmap(pixmap_path), self.right_rect)
                self.update_icon_position(x + left_width, y, right_width, height)

                for item in [self.left_rect, self.right_rect]:
                    item.setCursor(Qt.PointingHandCursor)

            def update_text_position(self, x, y, width, height):
                text_rect = self.text_item.boundingRect()
                text_x = (width - text_rect.width()) / 2
                text_y = (height - text_rect.height()) / 2
                self.text_item.setPos(x + text_x, y + text_y)

            def update_icon_position(self, x, y, width, height):
                icon_rect = self.icon_item.boundingRect()
                icon_x = (width - icon_rect.width()) / 2
                icon_y = (height - icon_rect.height()) / 2
                self.icon_item.setPos(x + icon_x, y + icon_y)

        button = Button(text, x, y, width)
        self.addItem(button)
        return button
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.scenePos()
            clicked_items = self.items(pos)
            
            for item in clicked_items:
                if isinstance(item, QGraphicsRectItem) and hasattr(item, 'level_id') and item.level_id > 0:
                    # Sprawdzenie czy kliknięcie jest na części lewej (graj) czy prawej (edytuj)
                    if hasattr(item, 'is_edit_button') and item.is_edit_button:
                        if self.editor_selected:
                            self.editor_selected(item.level_id)
                    else:
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
