import os
import xml.etree.ElementTree as ET
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QFont, QPen, QBrush, QColor, QLinearGradient
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsTextItem, QGraphicsProxyWidget, QPushButton, QLineEdit

import config
from game_history import load_game_history
from game_objects import CellUnit, CellConnection

class PlaybackScene(QGraphicsScene):
    def __init__(self, history_file, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        # Załaduj historię z pliku XML
        self.history = load_game_history(history_file)
        self.move_history = self.history.get("moves", [])
        self.current_move_index = 0

        # Odtwórz stan początkowy
        cells_data = self.history.get("initial_state", {}).get("cells", [])
        self.cells = []
        for cell_data in cells_data:
            # Zmiana: używamy get() aby właściwy typ został przypisany (domyślnie "neutral")
            cell = CellUnit(cell_data["x"], cell_data["y"],
                            cell_data.get("type", "neutral"), cell_data["points"])
            self.cells.append(cell)
            self.addItem(cell)
        # Odtwórz połączenia – zakładamy, że indeksy odpowiadają liście cells
        conns_data = self.history.get("initial_state", {}).get("connections", [])
        self.connections = []
        for conn in conns_data:
            src = self.cells[conn["source_index"]] if 0 <= conn["source_index"] < len(self.cells) else None
            tgt = self.cells[conn["target_index"]] if 0 <= conn["target_index"] < len(self.cells) else None
            if src and tgt:
                connection = CellConnection(src, tgt, conn["type"])
                connection.cost = conn["cost"]
                self.connections.append(connection)
        # Element wyświetlający aktualny ruch
        self.move_display = QGraphicsTextItem("")
        self.move_display.setDefaultTextColor(Qt.white)
        self.move_display.setFont(QFont(config.FONT_FAMILY, 20))
        self.move_display.setPos(20, config.WINDOW_HEIGHT - 60)
        self.addItem(self.move_display)

        # Kontrola szybkości – QLineEdit do wprowadzenia interwału (ms)
        self.speed_lineedit = QLineEdit()
        self.speed_lineedit.setPlaceholderText("Interwał (ms)")
        self.speed_lineedit.setText("1000")
        self.speed_lineedit.setFixedWidth(150)
        speed_proxy = QGraphicsProxyWidget()
        speed_proxy.setWidget(self.speed_lineedit)
        speed_proxy.setPos(config.WINDOW_WIDTH - 170, config.WINDOW_HEIGHT - 60)
        self.addItem(speed_proxy)

        # Przycisk powrotu do menu
        back_button = QPushButton("Powrót do menu")
        back_button.setFixedSize(150, 40)
        back_proxy = QGraphicsProxyWidget()
        back_proxy.setWidget(back_button)
        back_proxy.setPos(20, 20)
        self.addItem(back_proxy)
        back_button.clicked.connect(self.return_to_menu)

        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.play_next_move)
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_dots)

    def drawBackground(self, painter, rect):
        # Używamy niebieskiego gradientu dla replay
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(180, 220, 250))  # jasnoniebieski
        gradient.setColorAt(1, QColor(0, 100, 200))    # ciemnoniebieski
        painter.fillRect(rect, gradient)

    def drawForeground(self, painter, rect):
        for conn in self.connections:
            source = QPointF(conn.source_cell.x, conn.source_cell.y)
            target = QPointF(conn.target_cell.x, conn.target_cell.y)
            if conn.connection_type == "player":
                pen_color = config.COLOR_CONN_PLAYER
            else:
                pen_color = config.COLOR_CONN_ENEMY
            if hasattr(conn, "flash") and conn.flash:
                pen = QPen(pen_color.lighter(), 5)
            else:
                pen = QPen(pen_color, 3)
            painter.setPen(pen)
            painter.drawLine(source, target)

    def animate_dots(self):
        for conn in self.connections:
            for i in range(len(conn.dots)):
                conn.dots[i] += 0.016
                if conn.dots[i] >= 1.0:
                    conn.dots[i] = 0.0  # resetujemy, by animacja była ciągła
        self.update()

    def start_playback(self):
        self.current_move_index = 0
        self.playback_timer.start(int(self.speed_lineedit.text()))
        self.animation_timer.start(16)

    def apply_move_event(self, move):
        description = move.get("description", "")
        # Obsługa tworzenia mostu
        if description.startswith("Utworzono most"):
            import re
            pattern = r"Utworzono most między \((\d+), (\d+)\) a \((\d+), (\d+)\) o koszcie (\d+)"
            m = re.search(pattern, description)
            if m:
                x1, y1, x2, y2, cost = map(int, m.groups())
                found = False
                for conn in self.connections:
                    sx, sy = int(conn.source_cell.x), int(conn.source_cell.y)
                    tx, ty = int(conn.target_cell.x), int(conn.target_cell.y)
                    if abs(sx - x1) < 10 and abs(sy - y1) < 10 and abs(tx - x2) < 10 and abs(ty - y2) < 10:
                        conn.flash = True  # podświetl istniejący most
                        QTimer.singleShot(500, lambda: setattr(conn, 'flash', False))
                        found = True
                        break
                if not found:
                    # Utwórz nowy most, jeśli nie został znaleziony
                    src = None
                    tgt = None
                    for cell in self.cells:
                        if abs(cell.x - x1) < 10 and abs(cell.y - y1) < 10:
                            src = cell
                        if abs(cell.x - x2) < 10 and abs(cell.y - y2) < 10:
                            tgt = cell
                    if src and tgt:
                        from game_objects import CellConnection
                        new_conn = CellConnection(src, tgt, src.cell_type)
                        new_conn.cost = cost
                        new_conn.flash = True
                        self.connections.append(new_conn)
            return
        # Obsługa usunięcia mostu
        elif description.startswith("Usunięto most"):
            import re
            pattern = r"Usunięto most między \((\d+), (\d+)\) a \((\d+), (\d+)\)"
            m = re.search(pattern, description)
            if m:
                x1, y1, x2, y2 = map(int, m.groups())
                for conn in self.connections:
                    sx, sy = int(conn.source_cell.x), int(conn.source_cell.y)
                    tx, ty = int(conn.target_cell.x), int(conn.target_cell.y)
                    if abs(sx - x1) < 10 and abs(sy - y1) < 10 and abs(tx - x2) < 10 and abs(ty - y2) < 10:
                        self.removeItem(conn)
                        self.connections.remove(conn)
                        break
            return
        # Obsługa statusu punktowego – zawsze aktualizujemy typ i punkty komórki na podstawie opisu ruchu
        elif description.startswith("Status punktowy:"):
            import re
            matches = re.findall(r"\((\w+) @ (\d+),(\d+): (\d+) pts\)", description)
            for new_type, x, y, pts in matches:
                x, y, pts = int(x), int(y), int(pts)
                for cell in self.cells:
                    if abs(cell.x - x) < 10 and abs(cell.y - y) < 10:
                        cell.cell_type = new_type  # aktualizacja typu zgodnie z opisem
                        cell.points = pts
                        cell.strength = (pts // 10) + 1
                        cell.update()
            return

    def play_next_move(self):
        if self.current_move_index < len(self.move_history):
            move = self.move_history[self.current_move_index]
            self.apply_move_event(move)
            self.current_move_index += 1
            self.playback_timer.start(int(self.speed_lineedit.text()))
        else:
            self.playback_timer.stop()
            self.animation_timer.stop()
            self.show_game_result()

    def show_game_result(self):
        import re
        # Szukamy ostatniego ruchu ze statusem punktowym
        final_status = ""
        for move in reversed(self.move_history):
            if move.get("description", "").startswith("Status punktowy:"):
                final_status = move["description"]
                break
        matches = re.findall(r"\((\w+) @ [\d,]+: \d+ pts\)", final_status)
        player_count = matches.count("player")
        enemy_count = matches.count("enemy")
        if enemy_count == 0 and player_count > 0:
            result = "Wygrana!"
        elif player_count == 0 and enemy_count > 0:
            result = "Przegrana!"
        else:
            result = "Gra zakończona."
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(None, "Koniec replay", result)

    def return_to_menu(self):
        if self.views() and self.views()[0].parent():
            self.views()[0].parent().show_menu()
