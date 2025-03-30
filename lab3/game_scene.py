from PyQt5.QtWidgets import QGraphicsScene, QMenu, QMessageBox
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QRadialGradient, QFont, QTransform, QCursor
import math
import json
import os
from game_objects import CellUnit, CellConnection
from game_ai import GameAI  # Nowy import

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
        self.drag_current_pos = None
        self.reachable_cells = []  # Nowy atrybut do przechowywania komórek, do których możemy stworzyć most
        
        # Nowy timer do dodawania punktów co 2000 ms
        self.points_timer = QTimer()
        self.points_timer.timeout.connect(self.add_points)
        self.points_timer.start(2000)
        self.game_over_text = None  # Dodano atrybut na komunikat końca gry
        
        # Nowy kod: Inicjalizacja AI i atrybutów do podpowiedzi
        self.game_ai = GameAI(self)
        self.hint_active = False
        self.hint_source = None
        self.hint_target = None
        self.hint_cost = 0
        self.hint_timer = QTimer()
        self.hint_timer.timeout.connect(self.update_hint_animation)
        self.hint_timer.start(500)  # Miganie co 500ms
        self.hint_visible = False
        self.hint_blink_count = 0  # Licznik mrugnięć

        # Nowe atrybuty dla trybu turowego
        self.turn_based_mode = False
        self.current_turn = None  # "player" lub "enemy"
        self.turn_duration = 10  # czas trwania tury w sekundach
        self.round_time_remaining = self.turn_duration
        self.turn_timer = QTimer()

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
        self.current_level = level_number
        
        # Load level data from file
        level_data = self.load_level_data(level_number)
        
        if level_data:
            # Create cells based on level data
            for cell_data in level_data.get("cells", []):
                cell = CellUnit(
                    cell_data.get("x", 0),
                    cell_data.get("y", 0),
                    cell_data.get("type", "neutral"),
                    cell_data.get("points", 2)
                )
                self.cells.append(cell)
                self.addItem(cell)
            
            # Create connections based on level data
            for conn_data in level_data.get("connections", []):
                source_idx = conn_data.get("source", 0)
                target_idx = conn_data.get("target", 0)
                conn_type = conn_data.get("type", "neutral")
                
                if 0 <= source_idx < len(self.cells) and 0 <= target_idx < len(self.cells):
                    source = self.cells[source_idx]
                    target = self.cells[target_idx]
                    connection = self.create_connection(source, target, conn_type)
                    connection.cost = conn_data.get("cost", 0)
        else:
            # Fallback to hardcoded level if loading fails
            self._initialize_default_level(level_number)

    def load_level_data(self, level_number):
        """Load level data from file"""
        try:
            levels_path = os.path.join(os.path.dirname(__file__), 'levels.json')
            with open(levels_path, 'r') as f:
                levels = json.load(f)
                
            if 1 <= level_number <= len(levels):
                return levels[level_number - 1]
            return None
        except Exception as e:
            print(f"Błąd wczytywania poziomu {level_number}: {e}")
            return None

    def _initialize_default_level(self, level_number):
        """Fallback method with hardcoded level data"""
        if level_number == 1:
            # Create player cells
            player_cell1 = CellUnit(200, 300, "player", 30)
            player_cell2 = CellUnit(150, 450, "player", 2)
            
            # Create enemy cells
            enemy_cell1 = CellUnit(600, 250, "enemy", 30)
            enemy_cell2 = CellUnit(500, 400, "enemy", 2)
            
            # Create neutral cells
            neutral_cell = CellUnit(350, 350, "neutral", 2)
            
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
            cell.update()
            
        # Update connection animations and handle unit transfers
        for conn in self.connections:
            if conn.connection_type in ["player", "enemy"]:
                # Aktualizacja postępu każdej kropki
                finished = []
                for i in range(len(conn.dots)):
                    conn.dots[i] += 0.016  # przybliżony przyrost dla 60 FPS
                    if conn.dots[i] >= 1.0:
                        # Jeśli typ mostu jest zgodny z typem docelowej komórki - dodaj punkt,
                        # w przeciwnym wypadku odejmij punkt.
                        if conn.connection_type == conn.target_cell.cell_type:
                            conn.target_cell.points += 1
                        else:
                            conn.target_cell.points -= 1
                            if conn.target_cell.points <= 0:
                                conn.target_cell.cell_type = conn.connection_type
                                conn.target_cell.points = 1
                        conn.target_cell.strength = (conn.target_cell.points // 10) + 1
                        conn.target_cell.update()
                        finished.append(i)
                # Usuwanie kropek, które zakończyły podróż
                for index in sorted(finished, reverse=True):
                    del conn.dots[index]
                
        # Check win/lose conditions
        self.check_game_state()
                
    def calculate_reachable_cells(self):
        """Oblicza i oznacza komórki, do których można stworzyć most"""
        if not self.drag_start_cell:
            return
            
        # Jeśli tryb turowy włączony i komórka źródłowa nie należy do aktywnej strony,
        # nie obliczamy ani nie podświetlamy dostępnych komórek
        if self.turn_based_mode and self.drag_start_cell.cell_type != self.current_turn:
            return
            
        self.reachable_cells = []
        available_points = self.drag_start_cell.points
        
        for cell in self.cells:
            if cell == self.drag_start_cell:
                continue  # Pomijamy komórkę źródłową
                
            # Sprawdzamy czy już istnieje połączenie między tymi komórkami
            exists = any(((conn.source_cell == self.drag_start_cell and conn.target_cell == cell) or
                         (conn.source_cell == cell and conn.target_cell == self.drag_start_cell))
                         for conn in self.connections)
            if exists:
                continue  # Pomijamy jeśli połączenie już istnieje
                
            # Obliczamy koszt połączenia
            dx = cell.x - self.drag_start_cell.x
            dy = cell.y - self.drag_start_cell.y
            distance = math.hypot(dx, dy)
            cost = int(distance / 20)
            
            # Jeśli mamy wystarczająco punktów, dodajemy do listy dostępnych
            if cost <= available_points:
                self.reachable_cells.append(cell)
                cell.setHighlighted(True)  # Oznaczamy komórkę jako możliwą do połączenia
            
        self.update()  # Odświeżamy scenę, aby pokazać zmiany

    def mousePressEvent(self, event):
        clicked_item = self.itemAt(event.scenePos(), QTransform())
        
        # Najpierw resetujemy poprzednie podświetlenia
        for cell in self.reachable_cells:
            cell.setHighlighted(False)
        self.reachable_cells = []
        
        if event.button() == Qt.LeftButton:
            if isinstance(clicked_item, CellUnit) and clicked_item.cell_type == "player":
                self.drag_start_cell = clicked_item
                self.calculate_reachable_cells()  # Obliczamy możliwe komórki docelowe
            else:
                self.drag_start_cell = None
        elif event.button() == Qt.RightButton:
            if isinstance(clicked_item, CellUnit) and clicked_item.cell_type == "enemy":
                self.drag_start_cell = clicked_item
                self.calculate_reachable_cells()  # Obliczamy możliwe komórki docelowe
            else:
                self.drag_start_cell = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_start_cell:
            self.drag_current_pos = event.scenePos()
            self.update()
        else:
            buttons = event.buttons()
            if buttons & Qt.LeftButton:
                connection_filter = "player"
            elif buttons & Qt.RightButton:
                connection_filter = "enemy"
            else:
                return super().mouseMoveEvent(event)
            P = event.scenePos()
            for conn in self.connections:
                if conn.connection_type == connection_filter:
                    # W trybie turowym pozwalamy na usunięcie tylko mostu aktywnej strony
                    if self.turn_based_mode and conn.connection_type != self.current_turn:
                        continue
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
                    if math.hypot(P.x() - Qx, P.y() - Qy) < 5:
                        if conn in self.connections:
                            self.connections.remove(conn)
                        if conn in conn.source_cell.connections:
                            conn.source_cell.connections.remove(conn)
                        if conn in conn.target_cell.connections:
                            conn.target_cell.connections.remove(conn)
                        cost = getattr(conn, "cost", 0)
                        source_points = round(t * cost)
                        target_points = cost - source_points
                        if conn.connection_type == "player":
                            if conn.target_cell.cell_type != "player":
                                conn.source_cell.points += source_points
                                conn.target_cell.points -= target_points
                                if conn.target_cell.points <= 0:
                                    conn.target_cell.cell_type = "player"
                                    conn.target_cell.points = abs(conn.target_cell.points)
                            else:
                                conn.source_cell.points += source_points
                                conn.target_cell.points += target_points
                        elif conn.connection_type == "enemy":
                            if conn.target_cell.cell_type != "enemy":
                                conn.source_cell.points += source_points
                                conn.target_cell.points -= target_points
                                if conn.target_cell.points <= 0:
                                    conn.target_cell.cell_type = "enemy"
                                    conn.target_cell.points = abs(conn.target_cell.points)
                            else:
                                conn.source_cell.points += source_points
                                conn.target_cell.points += target_points
                        conn.source_cell.strength = (conn.source_cell.points // 10) + 1
                        conn.target_cell.strength = (conn.target_cell.points // 10) + 1
                        conn.source_cell.update()
                        conn.target_cell.update()
                        # Po usunięciu mostu przełączamy turę
                        if self.turn_based_mode:
                            self.switch_turn()
                        break
            self.update()
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Na zakończenie przeciągania sprawdza, czy zwolniono przycisk nad inną komórką tego samego typu.
           Dla LPM mosty tworzy komórka gracza, a dla PPM – tymczasowo mosty przeciwnika."""
        # Resetujemy podświetlenie komórek
        for cell in self.reachable_cells:
            cell.setHighlighted(False)
        self.reachable_cells = []
        
        if self.drag_start_cell is None:
            return
        release_item = self.itemAt(event.scenePos(), QTransform())
        # Sprawdzenie, czy wykonujący ruch to aktywny gracz
        if self.turn_based_mode:
            if event.button() == Qt.LeftButton and self.current_turn != "player":
                return
            if event.button() == Qt.RightButton and self.current_turn != "enemy":
                return
        if event.button() == Qt.LeftButton:
            # Zmodyfikowano: akceptujemy każdą komórkę (o ile nie jest identyczna z komórką początkową)
            if isinstance(release_item, CellUnit) and release_item != self.drag_start_cell:
                dx = release_item.x - self.drag_start_cell.x
                dy = release_item.y - self.drag_start_cell.y
                distance = math.hypot(dx, dy)
                cost = int(distance / 20)
                if self.drag_start_cell.points >= cost:
                    self.drag_start_cell.points -= cost
                    self.drag_start_cell.strength = (self.drag_start_cell.points // 10) + 1
                    self.drag_start_cell.update()
                    exists = any(((conn.source_cell == self.drag_start_cell and conn.target_cell == release_item) or
                                  (conn.source_cell == release_item and conn.target_cell == self.drag_start_cell))
                                  for conn in self.connections)
                    if not exists:
                        new_conn = self.create_connection(self.drag_start_cell, release_item, "player")
                        new_conn.cost = cost
                        # Przełączenie tury po wykonaniu ruchu
                        if self.turn_based_mode:
                            self.switch_turn()
        elif event.button() == Qt.RightButton:
            # Zmieniony warunek: akceptujemy dowolną komórkę, która nie jest komórką początkową
            if isinstance(release_item, CellUnit) and release_item != self.drag_start_cell:
                dx = release_item.x - self.drag_start_cell.x
                dy = release_item.y - self.drag_start_cell.y
                distance = math.hypot(dx, dy)
                cost = int(distance / 20)
                if self.drag_start_cell.points >= cost:
                    self.drag_start_cell.points -= cost
                    self.drag_start_cell.strength = (self.drag_start_cell.points // 10) + 1
                    self.drag_start_cell.update()
                    exists = any(((conn.source_cell == self.drag_start_cell and conn.target_cell == release_item) or
                                  (conn.source_cell == release_item and conn.target_cell == self.drag_start_cell))
                                  for conn in self.connections)
                    if not exists:
                        new_conn = self.create_connection(self.drag_start_cell, release_item, "enemy")
                        new_conn.cost = cost
                        if self.turn_based_mode:
                            self.switch_turn()
        self.drag_start_cell = None
        self.drag_current_pos = None  # Reset pozycji kursora
        self.update()
        
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
        self.timer.stop()
        self.points_timer.stop()  # Dodano, aby zapauzować grę po zakończeniu
        self.game_over_text = "Wygrana!" if victory else "Przegrana!"
        self.update()
        
        # Dodanie przycisku powrotu do menu po 2 sekundach
        QTimer.singleShot(2000, self.show_return_button)
    
    def show_return_button(self):
        # Dodanie przycisku powrotu do menu
        if self.game_over_text:
            from PyQt5.QtWidgets import QPushButton
            parent_widget = self.views()[0] if self.views() else None
            if parent_widget and parent_widget.parent():
                msgBox = QMessageBox(parent_widget)
                msgBox.setWindowTitle("Koniec gry")
                msgBox.setText(self.game_over_text)
                msgBox.setStandardButtons(QMessageBox.Ok)
                msgBox.buttonClicked.connect(lambda btn: parent_widget.parent().show_menu())
                msgBox.exec_()
        
    def add_points(self):
        """Dodaje 1 punkt do każdej komórki (oprócz neutralnych) co sekundę oraz przesyła kropki przez mosty gracza"""
        for cell in self.cells:
            if cell.cell_type != "neutral":
                cell.add_point()
                
                if self.drag_start_cell == cell:
                    # Najpierw resetujemy poprzednie podświetlenia
                    for reach_cell in self.reachable_cells:
                        reach_cell.setHighlighted(False)
                    self.reachable_cells = []
                    
                    # Następnie obliczamy nowe podświetlenia
                    self.calculate_reachable_cells()
        
        # Dla każdego mostu gracza przesyłamy kropkę, jeśli komórka źródłowa ma wystarczająco punktów
        for conn in self.connections:
            if conn.connection_type in ["player", "enemy"]:
                if conn.source_cell.points >= 1:
                    conn.source_cell.points -= 1
                    conn.source_cell.strength = (conn.source_cell.points // 10) + 1
                    conn.source_cell.update()
                    conn.dots.append(0)  # nowa kropka z postępem 0
                    
                    # Jeśli ta komórka jest komórką źródłową mostu, który jest w trakcie budowy,
                    # ponownie obliczamy dostępne komórki po odjęciu punktu
                    if self.drag_start_cell == conn.source_cell:
                        # Najpierw resetujemy poprzednie podświetlenia
                        for reach_cell in self.reachable_cells:
                            reach_cell.setHighlighted(False)
                        self.reachable_cells = []
                        
                        # Następnie obliczamy nowe podświetlenia
                        self.calculate_reachable_cells()

    def drawForeground(self, painter, rect):
        # Rysowanie informacji o turze i czasie rundy
        if self.turn_based_mode and self.current_turn:
            info_text = f"Runda: {self.current_turn.upper()} - Pozostało: {self.round_time_remaining}s"
            font = QFont("Arial", 16, QFont.Bold)
            painter.setFont(font)
            painter.setPen(QPen(Qt.white))
            painter.drawText(rect.adjusted(10, 10, -10, -10), Qt.AlignTop | Qt.AlignHCenter, info_text)
        # Rysowanie linii dynamicznej tylko, gdy to tura aktywnego gracza
        if self.drag_start_cell and self.drag_current_pos:
            if self.turn_based_mode and self.drag_start_cell.cell_type != self.current_turn:
                # Nie rysujemy animacji mostu, bo to nie tura tej strony
                pass
            else:
                target_item = self.itemAt(self.drag_current_pos, QTransform())
                if isinstance(target_item, CellUnit) and target_item.cell_type == self.drag_start_cell.cell_type and target_item != self.drag_start_cell:
                    target_point = QPointF(target_item.x, target_item.y)
                else:
                    target_point = self.drag_current_pos
                dx = target_point.x() - self.drag_start_cell.x
                dy = target_point.y() - self.drag_start_cell.y
                distance = math.hypot(dx, dy)
                cost = int(distance / 20)
                if self.drag_start_cell.cell_type == "player":
                    line_color = QColor(0, 255, 0)
                else:
                    line_color = QColor(139, 0, 0)  # ciemno czerwony
                color = line_color if self.drag_start_cell.points >= cost else QColor(255, 0, 0)
                painter.setPen(QPen(color, 2))
                painter.drawLine(QPointF(self.drag_start_cell.x, self.drag_start_cell.y), target_point)
        # Rysowanie wszystkich mostów jako ciemnozielone linie
        for conn in self.connections:
            source = QPointF(conn.source_cell.x, conn.source_cell.y)
            target = QPointF(conn.target_cell.x, conn.target_cell.y)
            if conn.connection_type == "player":
                painter.setPen(QPen(QColor(0,100,0), 3))
            else:
                painter.setPen(QPen(QColor(139,0,0), 3))  # ciemno czerwony
            painter.drawLine(source, target)
            # Rysujemy animowane, jaśniejsze zielone kropki tylko dla mostów budowanych przez gracza
            if conn.connection_type == "player":
                dot_color = QColor(144,238,144)
            else:
                dot_color = QColor(255,99,71)  # jasno czerwony
            for progress in conn.dots:
                x = conn.source_cell.x + progress * (conn.target_cell.x - conn.source_cell.x)
                y = conn.source_cell.y + progress * (conn.target_cell.y - conn.source_cell.y)
                dot_radius = 4  # promień kropki
                painter.setPen(Qt.NoPen)
                painter.setBrush(dot_color)
                painter.drawEllipse(QRectF(x - dot_radius, y - dot_radius, dot_radius * 2, dot_radius * 2))
        # Dodano rysowanie komunikatu końca gry
        if self.game_over_text is not None:
            font = QFont("Arial", 36, QFont.Bold)
            painter.setFont(font)
            text = self.game_over_text
            scene_rect = self.sceneRect()
            text_rect = painter.boundingRect(scene_rect, Qt.AlignCenter, text)
            # Rysowanie obramowania: czarne przesunięcia
            offsets = [(-2, -2), (-2, 2), (2, -2), (2, 2)]
            painter.setPen(QPen(Qt.black, 2))
            for dx, dy in offsets:
                painter.drawText(text_rect.translated(dx, dy), Qt.AlignCenter, text)
            painter.setPen(QPen(Qt.white, 2))
            painter.drawText(text_rect, Qt.AlignCenter, text)
        
        # Rysowanie podpowiedzi, jeśli jest aktywna i widoczna
        if self.hint_active and self.hint_visible and self.hint_source and self.hint_target:
            source_point = QPointF(self.hint_source.x, self.hint_source.y)
            target_point = QPointF(self.hint_target.x, self.hint_target.y)
            
            # Rysowanie pulsującej linii podpowiedzi ze strzałką wskazującą kierunek
            hint_pen = QPen(QColor(255, 215, 0), 3, Qt.DashLine)  # Złota, przerywana linia
            painter.setPen(hint_pen)
            painter.drawLine(source_point, target_point)
            
            # Dodajemy strzałkę wskazującą kierunek mostu
            arrow_size = 15
            dx = target_point.x() - source_point.x()
            dy = target_point.y() - source_point.y()
            length = math.sqrt(dx * dx + dy * dy)
            if length > 0:
                # Normalizacja wektora kierunku
                dx, dy = dx / length, dy / length
                
                # Punkt na linii, gdzie rysujemy strzałkę (70% odległości)
                arrow_point_x = source_point.x() + dx * length * 0.7
                arrow_point_y = source_point.y() + dy * length * 0.7
                
                # Rysowanie strzałki
                painter.setBrush(QColor(255, 215, 0))
                points = [
                    QPointF(arrow_point_x, arrow_point_y),
                    QPointF(arrow_point_x - arrow_size * (dx + dy * 0.5), arrow_point_y - arrow_size * (dy - dx * 0.5)),
                    QPointF(arrow_point_x - arrow_size * (dx - dy * 0.5), arrow_point_y - arrow_size * (dy + dx * 0.5))
                ]
                painter.drawPolygon(points)
            
            # Dodajemy okręgi wokół komórek z różnymi kolorami dla źródła i celu
            source_color = QColor(255, 215, 0)  # Złoty dla źródła
            target_color = QColor(255, 100, 0)  # Pomarańczowy dla celu
            highlight_radius = 40
            
            # Okrąg źródłowy
            painter.setPen(QPen(source_color, 3, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(source_point, highlight_radius, highlight_radius)
            
            # Okrąg docelowy
            painter.setPen(QPen(target_color, 3, Qt.DashLine))
            painter.drawEllipse(target_point, highlight_radius, highlight_radius)
            
            # Dodajemy etykiety "OD" i "DO"
            font = QFont("Arial", 12, QFont.Bold)
            painter.setFont(font)
            
            # Etykieta "OD" przy źródle
            label_width = 40
            label_height = 25
            
            # Pozycja etykiety "OD" (nad komórką źródłową)
            source_label_rect = QRectF(
                source_point.x() - label_width/2, 
                source_point.y() - highlight_radius - label_height - 5,
                label_width, label_height
            )
            
            # Tło etykiety
            painter.setBrush(source_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(source_label_rect, 5, 5)
            
            # Tekst etykiety
            painter.setPen(Qt.black)
            painter.drawText(source_label_rect, Qt.AlignCenter, "OD")
            
            # Etykieta "DO" przy celu
            target_label_rect = QRectF(
                target_point.x() - label_width/2, 
                target_point.y() - highlight_radius - label_height - 5,
                label_width, label_height
            )
            
            # Tło etykiety
            painter.setBrush(target_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(target_label_rect, 5, 5)
            
            # Tekst etykiety
            painter.setPen(Qt.black)
            painter.drawText(target_label_rect, Qt.AlignCenter, "DO")
            
            # Dodajemy napis z kosztem na środku linii
            if self.hint_cost > 0:
                mid_x = (self.hint_source.x + self.hint_target.x) / 2
                mid_y = (self.hint_source.y + self.hint_target.y) / 2
                
                font = QFont("Arial", 12, QFont.Bold)
                painter.setFont(font)
                cost_text = f"Koszt: {self.hint_cost}"
                
                # Poprawione rysowanie tekstu używając QRectF zamiast współrzędnych float
                text_width = 80  # przybliżona szerokość tekstu
                text_height = 20  # przybliżona wysokość tekstu
                
                # Biały tekst z czarnym cieniem
                painter.setPen(QPen(Qt.black, 2))
                for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    text_rect = QRectF(mid_x + dx - text_width/2, mid_y + dy - text_height/2, text_width, text_height)
                    painter.drawText(text_rect, Qt.AlignCenter, cost_text)
                
                painter.setPen(QPen(Qt.white, 1))
                text_rect = QRectF(mid_x - text_width/2, mid_y - text_height/2, text_width, text_height)
                painter.drawText(text_rect, Qt.AlignCenter, cost_text)

    def update_hint_animation(self):
        """Aktualizacja animacji dla podpowiedzi (miganie)"""
        if self.hint_active:
            self.hint_visible = not self.hint_visible
            self.update()
            
            # Jeśli podpowiedź jest niewidoczna, zwiększ licznik (liczenie pełnych cykli)
            if not self.hint_visible:
                self.hint_blink_count += 1
                
            # Po 2 pełnych cyklach (2 razy zaświecenie i wygaszenie) wyłącz podpowiedź
            if self.hint_blink_count >= 2:
                self.hint_active = False
                self.hint_visible = False
                self.hint_blink_count = 0
                self.update()

    def show_hint(self):
        """Pokazuje podpowiedź strategiczną od AI"""
        best_move = self.game_ai.analyze_best_move()
        
        if best_move:
            self.hint_source, self.hint_target, self.hint_cost = best_move
            self.hint_active = True
            self.hint_visible = True  # Rozpocznij od widocznej podpowiedzi
            self.hint_blink_count = 0  # Resetuj licznik mrugnięć
            QMessageBox.information(None, "Podpowiedź", 
                f"Sugerowany ruch: Połącz komórkę z {self.hint_source.points} punktami "
                f"z komórką typu {self.hint_target.cell_type}. Koszt: {self.hint_cost}")
        else:
            self.hint_active = False
            self.hint_visible = False
            self.hint_blink_count = 0
            QMessageBox.information(None, "Podpowiedź", "Brak sugerowanych ruchów.")
        
        self.update()  # Odświeżenie sceny, aby pokazać podpowiedź

    def keyPressEvent(self, event):
        # Obsługa klawisza H - pokaż podpowiedź
        if event.key() == Qt.Key_H:
            self.show_hint()
            event.accept()
            return
        
        # Obsługa klawisza Escape - powrót do menu
        if event.key() == Qt.Key_Escape:
            # Zatrzymanie timerów
            self.timer.stop()
            self.points_timer.stop()
            
            # Powrót do menu głównego
            if self.views() and self.views()[0].parent():
                self.views()[0].parent().show_menu()
            event.accept()
            return
            
        # Dodajemy menu kontekstowe po wciśnięciu "i"
        if event.key() == Qt.Key_I:
            if self.views():
                view = self.views()[0]
                scene_pos = view.mapToScene(view.mapFromGlobal(QCursor.pos()))
            else:
                return super().keyPressEvent(event)
            item = self.itemAt(scene_pos, QTransform())
            if item and isinstance(item, CellUnit):
                menu = QMenu()
                action_info = menu.addAction("Informacje o komórce")
                action = menu.exec_(QCursor.pos())
                if action == action_info:
                    QMessageBox.information(None, "Komórka", 
                        f"Typ: {item.cell_type}\nPunkty: {item.points}\nSiła: {item.strength}")
            else:
                found_conn = None
                for conn in self.connections:
                    A = QPointF(conn.source_cell.x, conn.source_cell.y)
                    B = QPointF(conn.target_cell.x, conn.target_cell.y)
                    AP = QPointF(scene_pos.x() - A.x(), scene_pos.y() - A.y())
                    AB = QPointF(B.x() - A.x(), B.y() - A.y())
                    ab2 = AB.x() ** 2 + AB.y() ** 2
                    if ab2 == 0:
                        continue
                    t = (AP.x() * AB.x() + AP.y() * AB.y()) / ab2
                    if t < 0 or t > 1:
                        continue
                    Qx = A.x() + t * AB.x()
                    Qy = A.y() + t * AB.y()
                    if math.hypot(scene_pos.x() - Qx, scene_pos.y() - Qy) < 5:
                        found_conn = conn
                        break
                if found_conn:
                    menu = QMenu()
                    action_info = menu.addAction("Informacje o moście")
                    action = menu.exec_(QCursor.pos())
                    if action == action_info:
                        cost = getattr(found_conn, "cost", 0)
                        QMessageBox.information(None, "Most", 
                            f"Typ: {found_conn.connection_type}\nKoszt: {cost}")
            event.accept()
        else:
            super().keyPressEvent(event)

    # Metody obsługi zegara rundowego
    def start_turn_timer(self):
        self.current_turn = "player"  # Zaczynamy od gracza
        self.round_time_remaining = self.turn_duration
        self.turn_timer.timeout.connect(self.update_turn_timer)
        self.turn_timer.start(1000)
        self.update()
        
    def update_turn_timer(self):
        self.round_time_remaining -= 1
        if self.round_time_remaining <= 0:
            self.switch_turn()
        self.update()
        
    def switch_turn(self):
        if self.current_turn == "player":
            self.current_turn = "enemy"
        else:
            self.current_turn = "player"
        self.round_time_remaining = self.turn_duration
        self.update()