import json
import os

from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QColor, QPen, QFont, QLinearGradient, QCursor
from PyQt5.QtWidgets import (
    QGraphicsScene, QGraphicsTextItem, QInputDialog, 
    QMessageBox, QMenu, QGraphicsView, QPushButton, QGraphicsProxyWidget
)

from config import WINDOW_WIDTH, WINDOW_HEIGHT, FONT_FAMILY, EDITOR_TITLE_FONT_SIZE, EDITOR_SUBTITLE_FONT_SIZE, EDITOR_INSTRUCTION_FONT_SIZE
from game_objects import CellUnit

class LevelEditorScene(QGraphicsScene):
    def __init__(self, level_id=1, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.level_id = level_id
        self.cells = []
        self.dragging_cell = None
        self.drag_offset = QPointF(0, 0)
        self.logger = None  # dodany atrybut logger
        
        # Ładowanie wybranego poziomu lub utworzenie nowego
        self.load_level()
        self.setup_ui()
    
    def setup_ui(self):
        # Tytuł
        title = QGraphicsTextItem("Edytor poziomów")
        title.setFont(QFont(FONT_FAMILY, EDITOR_TITLE_FONT_SIZE, QFont.Bold))
        title.setDefaultTextColor(Qt.white)
        title_width = title.boundingRect().width()
        title.setPos((self.width() - title_width) / 2, 20)
        self.addItem(title)
        
        # Informacje o poziomie
        level_text = QGraphicsTextItem(f"Edycja poziomu {self.level_id}: {self.level_name}")
        level_text.setFont(QFont(FONT_FAMILY, EDITOR_SUBTITLE_FONT_SIZE))
        level_text.setDefaultTextColor(Qt.white)
        level_text_width = level_text.boundingRect().width()
        level_text.setPos((self.width() - level_text_width) / 2, 60)
        self.addItem(level_text)
        
        # Instrukcje
        instructions = [
            "Prawy przycisk myszy: Dodaj nową komórkę",
            "Lewy przycisk + przeciągnięcie: Przesuń komórkę",
            "Podwójne kliknięcie: Edytuj właściwości komórki",
            "Delete: Usuń wybraną komórkę",
            "S: Zapisz poziom",
            "Esc: Powrót do menu"
        ]
        
        y_pos = 100
        for instruction in instructions:
            text = QGraphicsTextItem(instruction)
            text.setFont(QFont(FONT_FAMILY, EDITOR_INSTRUCTION_FONT_SIZE))
            text.setDefaultTextColor(Qt.white)
            text.setPos(20, y_pos)
            self.addItem(text)
            y_pos += 25
        
        # Przycisk zapisu
        save_button = QPushButton("Zapisz poziom")
        save_button.setFixedSize(150, 40)
        save_proxy = QGraphicsProxyWidget()
        save_proxy.setWidget(save_button)
        save_proxy.setPos(self.width() - 170, 20)
        self.addItem(save_proxy)
        save_button.clicked.connect(self.save_level)
        
        # Przycisk powrotu
        back_button = QPushButton("Powrót do menu")
        back_button.setFixedSize(150, 40)
        back_proxy = QGraphicsProxyWidget()
        back_proxy.setWidget(back_button)
        back_proxy.setPos(20, 20)
        self.addItem(back_proxy)
        back_button.clicked.connect(self.return_to_menu)
    
    def load_level(self):
        try:
            levels_path = os.path.join(os.path.dirname(__file__), 'levels.json')
            with open(levels_path, 'r') as f:
                levels = json.load(f)
                
            if 1 <= self.level_id <= len(levels):
                level_data = levels[self.level_id - 1]
                
                # Ładowanie nazwy poziomu
                self.level_name = level_data.get("name", f"Poziom {self.level_id}")
                
                # Tworzenie komórek na podstawie danych
                for cell_data in level_data.get("cells", []):
                    cell = CellUnit(
                        cell_data.get("x", 0),
                        cell_data.get("y", 0),
                        cell_data.get("type", "neutral"),
                        cell_data.get("points", 2)
                    )
                    self.cells.append(cell)
                    self.addItem(cell)
            else:
                # Tworzenie nowego poziomu jeśli nie istnieje
                self.level_name = f"Nowy poziom {self.level_id}"
                # Dodanie domyślnych komórek gracza i przeciwnika
                player_cell = CellUnit(200, 300, "player", 20)
                enemy_cell = CellUnit(600, 300, "enemy", 20)
                self.cells.extend([player_cell, enemy_cell])
                for cell in self.cells:
                    self.addItem(cell)
        except Exception as e:
            print(f"Błąd ładowania poziomu: {e}")
            # Tworzenie nowego poziomu
            self.level_name = f"Nowy poziom {self.level_id}"
            # Dodanie domyślnych komórek
            player_cell = CellUnit(200, 300, "player", 20)
            enemy_cell = CellUnit(600, 300, "enemy", 20)
            self.cells.extend([player_cell, enemy_cell])
            for cell in self.cells:
                self.addItem(cell)
    
    def save_level(self):
        try:
            # Najpierw pytamy o nazwę poziomu
            name, ok = QInputDialog.getText(None, "Nazwa poziomu", 
                                          "Wprowadź nazwę poziomu:", 
                                          text=self.level_name)
            if not ok:
                return False
                
            self.level_name = name
            
            # Tworzenie danych poziomu
            level_data = {
                "name": self.level_name,
                "cells": [
                    {
                        "x": cell.x,
                        "y": cell.y,
                        "type": cell.cell_type,
                        "points": cell.points
                    } for cell in self.cells
                ],
                "connections": []  # Nie edytujemy połączeń w edytorze
            }
            
            # Ładowanie wszystkich poziomów
            levels_path = os.path.join(os.path.dirname(__file__), 'levels.json')
            try:
                with open(levels_path, 'r') as f:
                    levels = json.load(f)
            except:
                levels = []
            
            # Aktualizacja lub dodanie poziomu
            if 1 <= self.level_id <= len(levels):
                levels[self.level_id - 1] = level_data
            else:
                # Dodanie nowego poziomu
                while len(levels) < self.level_id - 1:
                    # Wypełnienie luk placeholderem
                    levels.append({"name": f"Pusty poziom {len(levels) + 1}", "cells": [], "connections": []})
                levels.append(level_data)
            
            # Zapisanie do pliku
            with open(levels_path, 'w', encoding='utf-8') as f:
                json.dump(levels, f, indent=2, ensure_ascii=False)
                
            QMessageBox.information(None, "Sukces", f"Poziom {self.level_id} zapisany pomyślnie!")
            if self.logger:
                self.logger.log(f"LevelEditorScene: Poziom {self.level_id} zapisany.")
            return True
        except Exception as e:
            QMessageBox.critical(None, "Błąd", f"Nie udało się zapisać poziomu: {e}")
            if self.logger:
                self.logger.log(f"LevelEditorScene: Błąd przy zapisie poziomu {self.level_id}: {e}")
            return False
    
    def return_to_menu(self):
        if self.views() and self.views()[0].parent():
            self.views()[0].parent().show_menu()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Próba wybrania komórki
            item = self.itemAt(event.scenePos(), QGraphicsView.transform(self.views()[0]))
            if isinstance(item, CellUnit):
                self.dragging_cell = item
                self.drag_offset = event.scenePos() - QPointF(item.x, item.y)
                return
        
        elif event.button() == Qt.RightButton:
            # Tworzenie nowej komórki w miejscu kliknięcia
            menu = QMenu()
            player_action = menu.addAction("Dodaj komórkę gracza")
            enemy_action = menu.addAction("Dodaj komórkę przeciwnika")
            neutral_action = menu.addAction("Dodaj neutralną komórkę")
            
            action = menu.exec_(QCursor.pos())
            
            if action == player_action:
                cell_type = "player"
            elif action == enemy_action:
                cell_type = "enemy"
            elif action == neutral_action:
                cell_type = "neutral"
            else:
                return
            
            # Pytanie o początkowe punkty
            points, ok = QInputDialog.getInt(None, "Początkowe punkty", 
                                           "Wprowadź początkowe punkty dla komórki:", 
                                           10, 1, 1000, 1)
            if ok:
                new_cell = CellUnit(event.scenePos().x(), event.scenePos().y(), cell_type, points)
                self.cells.append(new_cell)
                self.addItem(new_cell)
                if self.logger:
                    self.logger.log(f"LevelEditorScene: Dodano komórkę typu '{cell_type}' na pozycji ({event.scenePos().x():.0f}, {event.scenePos().y():.0f}).")
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.dragging_cell:
            # Przesunięcie komórki
            new_pos = event.scenePos() - self.drag_offset
            self.dragging_cell.x = new_pos.x()
            self.dragging_cell.y = new_pos.y()
            self.dragging_cell.update()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self.dragging_cell = None
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.scenePos(), QGraphicsView.transform(self.views()[0]))
        if isinstance(item, CellUnit):
            # Edycja właściwości komórki
            menu = QMenu()
            # Edycja punktów
            edit_points_action = menu.addAction("Edytuj punkty")
            # Zmiana typu komórki
            cell_type_menu = menu.addMenu("Zmień typ komórki")
            player_action = cell_type_menu.addAction("Gracz")
            enemy_action = cell_type_menu.addAction("Przeciwnik")
            neutral_action = cell_type_menu.addAction("Neutralna")
            
            action = menu.exec_(QCursor.pos())
            
            if action == edit_points_action:
                points, ok = QInputDialog.getInt(None, "Edytuj punkty", 
                                               "Wprowadź punkty dla komórki:", 
                                               item.points, 1, 1000, 1)
                if ok:
                    item.points = points
                    item.strength = (item.points // 10) + 1
                    item.update()
            elif action == player_action:
                item.cell_type = "player"
                item.update()
            elif action == enemy_action:
                item.cell_type = "enemy"
                item.update()
            elif action == neutral_action:
                item.cell_type = "neutral"
                item.update()
        
        super().mouseDoubleClickEvent(event)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            # Usuwanie wybranych elementów
            selected_items = self.selectedItems()
            if not selected_items:
                # Jeśli nic nie wybrano, sprawdź pod kursorem
                if self.views():
                    view = self.views()[0]
                    scene_pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))
                    item = self.itemAt(scene_pos, QGraphicsView.transform(view))
                    if isinstance(item, CellUnit):
                        self.cells.remove(item)
                        self.removeItem(item)
            else:
                for item in selected_items:
                    if isinstance(item, CellUnit):
                        self.cells.remove(item)
                        self.removeItem(item)
        elif event.key() == Qt.Key_S:
            # Zapisz poziom (S)
            self.save_level()
        elif event.key() == Qt.Key_Escape:
            # Powrót do menu
            self.return_to_menu()
        
        super().keyPressEvent(event)
    
    def drawBackground(self, painter, rect):
        # Rysowanie gradientowego tła
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(230, 190, 255))  # Jasny fiolet
        gradient.setColorAt(1, QColor(100, 0, 150))    # Ciemny fiolet
        painter.fillRect(rect, gradient)
        
        # Rysowanie siatki pomocniczej
        painter.setPen(QPen(QColor(255, 255, 255, 50), 1))
        
        grid_size = 50
        
        # Linie pionowe
        for x in range(0, int(self.width()), grid_size):
            painter.drawLine(x, 0, x, int(self.height()))
        
        # Linie poziome
        for y in range(0, int(self.height()), grid_size):
            painter.drawLine(0, y, int(self.width()), y)
