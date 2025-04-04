import os
import re
import xml.etree.ElementTree as ET

from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import QFont, QPen, QBrush, QColor, QLinearGradient
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsTextItem, QGraphicsProxyWidget, QPushButton, QSlider, QLabel, QMessageBox, QProgressBar

import config
from game_history import load_game_history
from game_objects import CellUnit, CellConnection

# Dodajemy globalną flagę debugowania (domyślnie wyłączoną)
DEBUG_MODE = False

class PlaybackScene(QGraphicsScene):
    def __init__(self, history_file, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        # Załaduj historię z pliku XML
        self.history = load_game_history(history_file)
        self.move_history = self.history.get("moves", [])
        self.current_move_index = 0

        # Obliczamy czas replay (na podstawie timestampów ruchów, jeśli dostępne)
        if self.move_history:
            self.replay_start_time = self.move_history[0].get("timestamp", 0)
            self.replay_end_time = self.move_history[-1].get("timestamp", 0)
            self.replay_duration = self.replay_end_time - self.replay_start_time
        else:
            self.replay_duration = 0

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

        # ZAMIENNIK: Suwak do ustawiania interwału wraz z etykietą prędkości
        # Suwak prędkości - przesunięty do prawego górnego rogu
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(10)
        self.speed_slider.setValue(1)
        self.speed_slider.setFixedWidth(150)
        self.speed_proxy = QGraphicsProxyWidget()
        self.speed_proxy.setWidget(self.speed_slider)
        self.speed_proxy.setPos(config.WINDOW_WIDTH-160, config.WINDOW_HEIGHT-30)  # zmieniona pozycja na prawy górny róg
        self.addItem(self.speed_proxy)
        # Aktualizacja etykiety prędkości - przesunięta poniżej suwaka
        self.speed_label = QGraphicsTextItem("1.0x")
        self.speed_label.setDefaultTextColor(Qt.white)
        self.speed_label.setFont(QFont(config.FONT_FAMILY, 14))
        self.speed_label.setPos(config.WINDOW_WIDTH - 160, config.WINDOW_HEIGHT-60)
        self.addItem(self.speed_label)
        self.speed_slider.valueChanged.connect(lambda val: self.speed_label.setPlainText(f"{val:.1f}x"))

        # Przycisk powrotu do menu - przesunięty do lewego górnego rogu
        back_button = QPushButton("Powrót do menu")
        back_button.setFixedSize(150, 40)
        back_proxy = QGraphicsProxyWidget()
        back_proxy.setWidget(back_button)
        back_proxy.setPos(0, config.WINDOW_HEIGHT-50)  # zmieniona pozycja na lewy górny róg
        self.addItem(back_proxy)
        back_button.clicked.connect(self.return_to_menu)

        # ----------------------- NOWE --------------------------
        # Dodajemy progress bar do odtwarzania powtórki
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(300)
        progress_proxy = QGraphicsProxyWidget()
        progress_proxy.setWidget(self.progress_bar)
        progress_proxy.setPos((config.WINDOW_WIDTH - 300)/2, config.WINDOW_HEIGHT - 50)
        self.addItem(progress_proxy)
        # Dodajemy etykietę pokazującą aktualny czas replay (w formacie mm:ss)
        self.clock_label = QLabel("00:00 / 00:00")
        self.clock_label.setStyleSheet("color: white; background-color: transparent;")
        clock_proxy = QGraphicsProxyWidget()
        clock_proxy.setWidget(self.clock_label)
        clock_proxy.setPos((config.WINDOW_WIDTH - 70)/2, config.WINDOW_HEIGHT - 70)
        self.addItem(clock_proxy)
        # --------------------- KONIEC NOWYCH --------------------

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
            
            # Dodajemy animowane kółka (dots) analogicznie do głównej gry
            if not (hasattr(conn, 'conflict') and conn.conflict):
                if conn.connection_type == "player":
                    dot_color = config.COLOR_DOT_PLAYER
                else:
                    dot_color = config.COLOR_DOT_ENEMY
                for progress in conn.dots:
                    x = conn.source_cell.x + progress * (conn.target_cell.x - conn.source_cell.x)
                    y = conn.source_cell.y + progress * (conn.target_cell.y - conn.source_cell.y)
                    dot_radius = 4
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(dot_color)
                    painter.drawEllipse(QRectF(x - dot_radius, y - dot_radius, dot_radius * 2, dot_radius * 2))

    def animate_dots(self):
        # Zwiększ przyrost animacji zgodnie z ustawioną prędkością replay (speed_slider)
        delta = 0.016 * self.speed_slider.value()
        for conn in self.connections:
            for i in range(len(conn.dots)):
                conn.dots[i] += delta
                if conn.dots[i] >= 1.0:
                    conn.dots[i] = 0.0  # resetujemy, by animacja była ciągła
        self.update()

    def start_playback(self):
        self.current_move_index = 0
        self.playback_timer.start(int(1000 / self.speed_slider.value()))
        self.animation_timer.start(16)

    def apply_move_event(self, move):
        description = move.get("description", "").strip()
        if DEBUG_MODE:
            print("DEBUG: apply_move_event - description:", description)
        if description.startswith("Utworzono most"):
            if DEBUG_MODE:
                print("DEBUG: Próba utworzenia mostu.")
            pattern = r"Utworzono most między \(([\d.]+),\s*([\d.]+)\) a \(([\d.]+),\s*([\d.]+)\) o koszcie (\d+)"
            m = re.search(pattern, description)
            if m and DEBUG_MODE:
                print("DEBUG: Wzorzec dopasowany! Dane mostu:", m.groups())
            elif not m and DEBUG_MODE:
                print("DEBUG: Wzorzec nie został dopasowany.")
            if m:
                x1, y1, x2, y2, cost = list(map(float, m.groups()[:4])) + [int(m.group(5))]
                found = False
                for conn in self.connections:
                    sx, sy = conn.source_cell.x, conn.source_cell.y
                    tx, ty = conn.target_cell.x, conn.target_cell.y
                    if abs(sx - x1) < 10 and abs(sy - y1) < 10 and abs(tx - x2) < 10 and abs(ty - y2) < 10:
                        conn.flash = True  # podświetl istniejący most
                        QTimer.singleShot(500, lambda: setattr(conn, 'flash', False))
                        found = True
                        break
                if not found:
                    if DEBUG_MODE:
                        print("DEBUG: Nie znaleziono istniejącego mostu. Tworzę nowy most.")
                    src = None
                    tgt = None
                    for cell in self.cells:
                        if abs(cell.x - x1) < 10 and abs(cell.y - y1) < 10:
                            src = cell
                        if abs(cell.x - x2) < 10 and abs(cell.y - y2) < 10:
                            tgt = cell
                    if src and tgt:
                        new_conn = CellConnection(src, tgt, src.cell_type)
                        new_conn.cost = cost
                        new_conn.flash = True
                        new_conn.dots.append(0)  # Inicjujemy animowane kółko
                        self.connections.append(new_conn)
            return
        elif description.startswith("Usunięto most"):
            pattern = r"Usunięto most między \(([\d.]+),\s*([\d.]+)\) a \(([\d.]+),\s*([\d.]+)\)"
            m = re.search(pattern, description)
            if m:
                if DEBUG_MODE:
                    print("DEBUG: Most do usunięcia znaleziony:", m.groups())
                x1, y1, x2, y2 = map(float, m.groups())
                for conn in self.connections:
                    sx, sy = conn.source_cell.x, conn.source_cell.y
                    tx, ty = conn.target_cell.x, conn.target_cell.y
                    if abs(sx - x1) < 10 and abs(sy - y1) < 10 and abs(tx - x2) < 10 and abs(ty - y2) < 10:
                        if DEBUG_MODE:
                            print("DEBUG: Usuwam most:", conn)
                        # Usuwamy most tylko z listy połączeń, ponieważ nie jest QGraphicsItem
                        self.connections.remove(conn)
                        break
            else:
                if DEBUG_MODE:
                    print("DEBUG: Wzorzec usunięcia mostu nie dopasowany.")
            return
        elif description.startswith("Status punktowy:"):
            matches = re.findall(r"\((\w+) @ ([\d.]+),([\d.]+): (\d+) pts\)", description)
            if DEBUG_MODE:
                print("DEBUG: Aktualizacja statusu. Znalazłem komórki:", matches)
            for new_type, x, y, pts in matches:
                x, y, pts = float(x), float(y), int(pts)
                for cell in self.cells:
                    if abs(cell.x - x) < 10 and abs(cell.y - y) < 10:
                        cell.cell_type = new_type  # aktualizacja typu zgodnie z opisem
                        cell.points = pts
                        cell.strength = (pts // 10) + 1
                        cell.update()
            return
        elif description.startswith("Status po ogłoszeniu wyniku:"):
            matches = re.findall(r"\((\w+) @ ([\d.]+),([\d.]+): (\d+) pts\)", description)
            if DEBUG_MODE:
                print("DEBUG: Aktualizacja finalnego statusu. Znalazłem komórki:", matches)
            for new_type, x, y, pts in matches:
                x, y, pts = float(x), float(y), int(pts)
                for cell in self.cells:
                    if abs(cell.x - x) < 10 and abs(cell.y - y) < 10:
                        cell.cell_type = new_type
                        cell.points = pts
                        cell.strength = (pts // 10) + 1
                        cell.update()
            return

    def play_next_move(self):
        if self.current_move_index < len(self.move_history):
            move = self.move_history[self.current_move_index]
            self.apply_move_event(move)
            self.current_move_index += 1
            self.playback_timer.start(int(1000 / self.speed_slider.value()))
            # ----------------------- NOWE --------------------------
            progress = int((self.current_move_index / len(self.move_history)) * 100)
            self.progress_bar.setValue(progress)
            if self.replay_duration > 0:
                current_time = self.replay_start_time + (self.current_move_index / len(self.move_history)) * self.replay_duration
                # Formatowanie do mm:ss
                minutes = int((current_time - self.replay_start_time) // 60)
                seconds = int((current_time - self.replay_start_time) % 60)
                total_minutes = int(self.replay_duration // 60)
                total_seconds = int(self.replay_duration % 60)
                self.clock_label.setText(f"{minutes:02d}:{seconds:02d} / {total_minutes:02d}:{total_seconds:02d}")
            else:
                self.clock_label.setText("00:00 / 00:00")
            # --------------------- KONIEC NOWYCH --------------------
        else:
            self.playback_timer.stop()
            self.animation_timer.stop()
            self.show_game_result()

    def show_game_result(self):
        # Szukamy ostatniego ruchu ze statusem punktowym
        final_status = ""
        for move in reversed(self.move_history):
            desc = move.get("description", "")
            if desc.startswith("Status punktowy:") or desc.startswith("Status po ogłoszeniu wyniku:"):
                final_status = desc
                break
        matches = re.findall(r"\((\w+) @ [\d.]+,[\d.]+: \d+ pts\)", final_status)
        player_count = matches.count("player")
        enemy_count = matches.count("enemy")
        if enemy_count == 0 and player_count > 0:
            result = "Gracz wygrał"
        elif player_count == 0 and enemy_count > 0:
            result = "Gracz przegrał."
        else:
            result = "Gra zakończona."
        QMessageBox.information(None, "Koniec replay", result)

    def return_to_menu(self):
        if self.views() and self.views()[0].parent():
            self.views()[0].parent().show_menu()
