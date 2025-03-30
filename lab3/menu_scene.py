from PyQt5.QtWidgets import QGraphicsScene, QGraphicsTextItem, QGraphicsRectItem, QGraphicsItemGroup, QGraphicsPixmapItem, QGraphicsItem
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QPen, QFont, QLinearGradient, QPixmap
import resources_rc #pyrcc5 resources.rc -o resources_rc.py
import json
import os

class SwitchButton(QGraphicsItem):
    def __init__(self, width=60, height=30, parent=None):
        super().__init__(parent)
        self._state = False  # OFF
        self.width = width
        self.height = height
        self.callback = None  # Funkcja wywoływana przy zmianie stanu
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton)

    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)
        
    def shape(self):
        from PyQt5.QtGui import QPainterPath
        path = QPainterPath()
        # Zwracamy cały obszar przycisku (zaokrąglony prostokąt)
        path.addRoundedRect(self.boundingRect(), self.height/2, self.height/2)
        return path

    def paint(self, painter, option, widget):
        # Rysujemy tło (zaokrąglone prostokąty)
        radius = self.height / 2
        bg_color = QColor(200, 200, 200) if not self._state else QColor(0, 150, 136)
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(self.boundingRect(), radius, radius)
        # Rysujemy przesuwany okrąg
        circle_diameter = self.height - 4
        circle_rect = QRectF(2, 2, circle_diameter, circle_diameter)
        if self._state:
            circle_rect.moveLeft(self.width - circle_diameter - 2)
        painter.setBrush(Qt.white)
        painter.drawEllipse(circle_rect)

    def mousePressEvent(self, event):
        self._state = not self._state
        self.update()
        if self.callback:
            self.callback(self._state)
        event.accept()

class MenuScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, 800, 600)
        self.level_buttons = []
        self.levels_data = []
        self.turn_based = False  # Tryb turowy domyślnie wyłączony
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

        # Dodaj etykietę opisującą przełącznik trybu turowego
        switch_label = QGraphicsTextItem("Tryb turowy")
        switch_label.setFont(QFont("Arial", 16))
        switch_label.setDefaultTextColor(Qt.white)
        switch_label_width = switch_label.boundingRect().width()
        switch_label.setPos((self.width() - switch_label_width) / 2, 460)
        self.addItem(switch_label)

        # Usuwamy poprzedni tekstowy przełącznik i tworzymy SwitchButton
        self.switch = SwitchButton(60, 30)
        # Ustawiamy pozycję poniżej etykiety
        self.switch.setPos((self.width() - self.switch.width) / 2, 490)
        # Callback zmienia atrybut trybu turowego
        self.switch.callback = lambda state: setattr(self, 'turn_based', state)
        self.addItem(self.switch)
    
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
                self.icon_item = QGraphicsPixmapItem(QPixmap(":/olowek.png"), self.right_rect)
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
        
        # Pozwól, aby zdarzenie trafiło do SwitchButton i innych elementów
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
