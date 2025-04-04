import json
import math
import os
import time

from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import QCursor, QColor, QLinearGradient, QPen, QFont, QTransform
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsDropShadowEffect, QGraphicsItem, QMenu, QMessageBox, QGraphicsTextItem

import config
from config import (WINDOW_WIDTH, WINDOW_HEIGHT, FRAME_INTERVAL_MS, POINTS_INTERVAL_MS,
                    TURN_TIMER_INTERVAL_MS, TURN_DURATION_SECONDS, FONT_FAMILY, GAME_TURN_FONT_SIZE,
                    GAME_OVER_FONT_SIZE, FREEZE_DURATION_SECONDS, POWERUP_FREEZE, POWERUP_TAKEOVER,
                    POWERUP_ADD_POINTS, POWERUP_NEW_CELL, NEW_CELL_COPY_RANGE_FACTOR, POINTS_PER_STRENGTH)
from game_ai import GameAI
from game_objects import CellUnit, CellConnection
import game_history  # dodany import do zapisu replay

class GameScene(QGraphicsScene):
    """Main game scene class"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.cells = []
        self.connections = []
        self.current_level = 1
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.drag_start_cell = None
        self.drag_current_pos = None
        self.reachable_cells = []

        self.points_timer = QTimer()
        self.points_timer.timeout.connect(self.add_points)
        self.points_timer.start(POINTS_INTERVAL_MS)
        self.game_over_text = None

        self.game_ai = GameAI(self)
        self.hint_active = False
        self.hint_source = None
        self.hint_target = None
        self.hint_cost = 0
        self.hint_timer = QTimer()
        self.hint_timer.timeout.connect(self.update_hint_animation)
        self.hint_timer.start(500)
        self.hint_visible = False
        self.hint_blink_count = 0

        self.turn_based_mode = False
        self.current_turn = None
        self.turn_duration = TURN_DURATION_SECONDS
        self.round_time_remaining = self.turn_duration
        self.turn_timer = QTimer()

        self.logger = None
        self.powerup_active = None
        self.copy_source = None

        self.single_player = False  # nowa flaga dla trybu 1 gracz
        self.enemy_timer = None
        self.move_history = []  # dodana historia ruchów do replay
        self.last_state_record = 0  # nowa zmienna do kontrolowania interwału zapisu stanu

    def drawBackground(self, painter, rect):
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, config.COLOR_BG_TOP)
        gradient.setColorAt(1, config.COLOR_BG_BOTTOM)
        painter.fillRect(rect, gradient)

    def initialize_level(self, level_number):
        """Set up cells and connections for a specific level"""
        if self.enemy_timer:
            self.enemy_timer.stop()
        self.clear()
        self.cells = []
        self.connections = []
        self.current_level = level_number

        level_data = self.load_level_data(level_number)

        if self.logger:
            self.logger.log(f"GameScene: Inicjalizacja poziomu {level_number}.")

        if level_data:
            for cell_data in level_data.get("cells", []):
                cell = CellUnit(
                    cell_data.get("x", 0),
                    cell_data.get("y", 0),
                    cell_data.get("type", "neutral"),
                    cell_data.get("points", 2)
                )
                self.cells.append(cell)
                self.addItem(cell)
            if self.cells:
                min_x = min(cell.x for cell in self.cells)
                max_x = max(cell.x for cell in self.cells)
                min_y = min(cell.y for cell in self.cells)
                max_y = max(cell.y for cell in self.cells)
                level_center = ((min_x + max_x) / 2, (min_y + max_y) / 2)
                scene_center = self.sceneRect().center()
                offset_x = scene_center.x() - level_center[0]
                offset_y = scene_center.y() - level_center[1]
                for cell in self.cells:
                    cell.x += offset_x
                    cell.y += offset_y
                    cell.update()

            for conn_data in level_data.get("connections", []):
                source_idx = conn_data.get("source", 0)
                target_idx = conn_data.get("target", 0)
                conn_type = conn_data.get("type", "neutral")

                if 0 <= source_idx < len(self.cells) and 0 <= target_idx < len(self.cells):
                    source = self.cells[source_idx]
                    target = self.cells[target_idx]
                    connection = self.create_connection(source, target, conn_type, cost=conn_data.get("cost", 0))
        else:
            self._initialize_default_level(level_number)
            if self.cells:
                min_x = min(cell.x for cell in self.cells)
                max_x = max(cell.x for cell in self.cells)
                min_y = min(cell.y for cell in self.cells)
                max_y = max(cell.y for cell in self.cells)
                level_center = ((min_x + max_x) / 2, (min_y + max_y) / 2)
                scene_center = self.sceneRect().center()
                offset_x = scene_center.x() - level_center[0]
                offset_y = scene_center.y() - level_center[1]
                for cell in self.cells:
                    cell.x += offset_x
                    cell.y += offset_y
                    cell.update()

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
            player_cell1 = CellUnit(200, 300, "player", 30)
            player_cell2 = CellUnit(150, 450, "player", 2)

            enemy_cell1 = CellUnit(600, 250, "enemy", 30)
            enemy_cell2 = CellUnit(500, 400, "enemy", 2)

            neutral_cell = CellUnit(350, 350, "neutral", 2)

            for cell in [player_cell1, player_cell2, enemy_cell1, enemy_cell2, neutral_cell]:
                self.cells.append(cell)
                self.addItem(cell)

    def create_connection(self, source, target, conn_type, cost=0):
        # Wymuszamy spójność – typ mostu zawsze zgodny z typem komórki źródłowej
        if source.cell_type != conn_type:
            if self.logger:
                self.logger.log(f"DEBUG: Niepoprawny typ mostu. Komórka ({source.x:.0f}, {source.y:.0f}) typu {source.cell_type} próbuje utworzyć most typu {conn_type}. Przypisano typ {source.cell_type}.")
            conn_type = source.cell_type
        connection = CellConnection(source, target, conn_type)
        connection.cost = cost
        # Dodajemy mechanizm konfliktu, jeśli istnieje most z przeciwnym typem
        for conn in self.connections:
            if conn.source_cell == target and conn.target_cell == source and conn.connection_type != conn_type:
                connection.conflict = True
                conn.conflict = True
                break
        if not hasattr(connection, 'conflict'):
            connection.conflict = False
        source.connections.append(connection)
        target.connections.append(connection)
        self.connections.append(connection)
        if self.logger:
            self.logger.log(f"GameScene: Utworzono most między komórkami przy ({source.x:.0f}, {source.y:.0f}) i ({target.x:.0f}, {target.y:.0f}) o koszcie {connection.cost}.")
        # Zapisujemy ruch w historii
        self.move_history.append({
            "timestamp": time.time(),
            "description": f"Utworzono most między ({source.x:.0f}, {source.y:.0f}) a ({target.x:.0f}, {target.y:.0f}) o koszcie {connection.cost}"
        })
        return connection

    def update_game(self):
        # Przed rozpoczęciem aktualizacji, usuwamy niespójne mosty
        for conn in list(self.connections):
            if conn.source_cell.cell_type != conn.connection_type:
                if self.logger:
                    self.logger.log(f"DEBUG: Usunięto niespójny most: Komórka ({conn.source_cell.x:.0f}, {conn.source_cell.y:.0f}) typu {conn.source_cell.cell_type} ma most typu {conn.connection_type}.")
                if conn in conn.source_cell.connections:
                    conn.source_cell.connections.remove(conn)
                if conn in conn.target_cell.connections:
                    conn.target_cell.connections.remove(conn)
                self.connections.remove(conn)
        """Main game update loop"""
        for cell in self.cells:
            cell.update()

        for conn in self.connections:
            if conn.connection_type in ["player", "enemy"] and not conn.conflict:
                if conn.source_cell.frozen or conn.target_cell.frozen:
                    continue
                finished = []
                for i in range(len(conn.dots)):
                    conn.dots[i] += 0.016
                    if conn.dots[i] >= 1.0:
                        if conn.connection_type == conn.target_cell.cell_type:
                            conn.target_cell.points += 1
                        else:
                            conn.target_cell.points -= 1
                            if conn.target_cell.points <= 0:
                                captured = conn.target_cell
                                if self.logger:
                                    self.logger.log(f"DEBUG: Przechwytywanie komórki ({captured.x:.0f}, {captured.y:.0f}). Punkty przed przejęciem: {captured.points}, typ docelowy: {conn.connection_type}.")
                                captured.cell_type = conn.connection_type
                                captured.points = 1
                                if self.logger:
                                    self.logger.log(f"DEBUG: Komórka przejęta. Nowy typ: {captured.cell_type}, punkty zresetowane do {captured.points}. Próba usunięcia mostów wychodzących...")
                                removed_count = 0
                                for rem_conn in list(self.connections):
                                    if rem_conn.source_cell == captured:
                                        if rem_conn in captured.connections:
                                            captured.connections.remove(rem_conn)
                                        if rem_conn in rem_conn.target_cell.connections:
                                            rem_conn.target_cell.connections.remove(rem_conn)
                                        self.connections.remove(rem_conn)
                                        removed_count += 1
                                if self.logger:
                                    self.logger.log(f"DEBUG: Usunięto {removed_count} mostów wychodzących z przejętej komórki ({captured.x:.0f}, {captured.y:.0f}).")
                        conn.target_cell.strength = (conn.target_cell.points // POINTS_PER_STRENGTH) + 1
                        conn.target_cell.update()
                        finished.append(i)

                for index in sorted(finished, reverse=True):
                    del conn.dots[index]

        # Now processing mosty konfliktowe
        for conn in self.connections:
            if hasattr(conn, 'conflict') and conn.conflict:
                if not hasattr(conn, 'conflict_progress'):
                    conn.conflict_progress = 0
                conn.conflict_progress += 0.016
                if conn.conflict_progress >= 1.0:
                    conn.source_cell.points -= 1
                    conn.target_cell.points -= 1
                    conn.source_cell.strength = (conn.source_cell.points // POINTS_PER_STRENGTH) + 1
                    conn.target_cell.strength = (conn.target_cell.points // POINTS_PER_STRENGTH) + 1
                    conn.source_cell.update()
                    conn.target_cell.update()
                    conn.conflict_progress = 0

        # Sprawdzenie czy którejś z komórek skończyły się punkty – usuwamy wszystkie konfliktowe mosty z nią związane
        for cell in self.cells:
            if cell.points <= 0:
                for conn in list(self.connections):
                    if hasattr(conn, 'conflict') and conn.conflict and (conn.source_cell == cell or conn.target_cell == cell):
                        refund = conn.cost // 2
                        cell.points += refund
                        if conn in conn.source_cell.connections:
                            conn.source_cell.connections.remove(conn)
                        if conn in conn.target_cell.connections:
                            conn.target_cell.connections.remove(conn)
                        self.connections.remove(conn)
                        cell.update()

        # Po zakończeniu przetwarzania stanów komórek i mostów, zapisujemy stan pośredni
        now = time.time()
        if now - self.last_state_record >= 1.0:  # co 1 s zapisujemy stan
            points_status = "; ".join(
                f"({cell.cell_type} @ {int(cell.x)},{int(cell.y)}: {cell.points} pts)"
                for cell in self.cells
            )
            self.move_history.append({
                "timestamp": now,
                "description": f"Status punktowy: {points_status}"
            })
            self.last_state_record = now

        self.check_game_state()

    def calculate_reachable_cells(self):
        """Oblicza i oznacza komórki, do których można stworzyć most"""
        if not self.drag_start_cell:
            return

        if self.turn_based_mode and self.drag_start_cell.cell_type != self.current_turn:
            return
            
        if not self.drag_start_cell.can_create_new_connection():
            if self.logger:
                self.logger.log(f"GameScene: Komórka osiągnęła maksymalną liczbę mostów ({self.drag_start_cell.strength}).")
            return

        self.reachable_cells = []
        available_points = self.drag_start_cell.points

        for cell in self.cells:
            if cell == self.drag_start_cell:
                continue

            # Uaktualniony warunek: pomijamy istniejące mosty tylko, gdy ich connection_type odpowiada typowi początkowej komórki.
            exists = any(
                (((conn.source_cell == self.drag_start_cell and conn.target_cell == cell) or
                  (conn.source_cell == cell and conn.target_cell == self.drag_start_cell))
                 and conn.connection_type == self.drag_start_cell.cell_type)
                for conn in self.connections
            )
            if exists:
                continue

            dx = cell.x - self.drag_start_cell.x
            dy = cell.y - self.drag_start_cell.y
            distance = math.hypot(dx, dy)
            cost = int(distance / 20)

            if cost <= available_points:
                self.reachable_cells.append(cell)
                cell.setHighlighted(True)

        self.update()

    def mousePressEvent(self, event):
        # W trybie, gdy gramy w 1 gracz (self.single_player True) ignorujemy interakcję prawym przyciskiem
        if event.button() == Qt.RightButton and self.single_player:
            event.accept()
            return

        if self.powerup_active is not None:
            clicked_item = self.itemAt(event.scenePos(), QTransform())
            if self.powerup_active == POWERUP_NEW_CELL:
                if self.copy_source is None:
                    if isinstance(clicked_item, CellUnit):
                        self.copy_source = clicked_item
                        if self.logger:
                            self.logger.log("GameScene: Komórka wybrana do kopiowania. Teraz wybierz miejsce, gdzie ją postawić.")
                        if hasattr(self, 'powerup_label'):
                            self.powerup_label.setPlainText("Wybierz miejsce: odległość ≥ 2*promień i ≤ {}*promień".format(NEW_CELL_COPY_RANGE_FACTOR))
                        event.accept()
                        return
                    else:
                        if self.powerup_label is None:
                            self.powerup_label = QGraphicsTextItem("Wybierz komórkę do skopiowania.")
                            self.powerup_label.setDefaultTextColor(Qt.white)
                            self.powerup_label.setFont(QFont("Arial", 16))
                            label_width = self.powerup_label.boundingRect().width()
                            scene_center = self.sceneRect().center().x()
                            self.powerup_label.setPos(scene_center - label_width/2, 10)
                            self.addItem(self.powerup_label)
                        else:
                            self.powerup_label.setPlainText("Wybierz komórkę do skopiowania.")
                        event.accept()
                        return
                else:
                    pos = event.scenePos()
                    dx = pos.x() - self.copy_source.x
                    dy = pos.y() - self.copy_source.y
                    distance = math.hypot(dx, dy)
                    radius = self.copy_source.radius
                    min_dist = 2 * radius
                    max_dist = NEW_CELL_COPY_RANGE_FACTOR * radius
                    if distance < min_dist or distance > max_dist:
                        if self.powerup_label is None:
                            self.powerup_label = QGraphicsTextItem("Błędna odległość. Wybierz miejsce między {} a {} pikseli.".format(min_dist, max_dist))
                            self.powerup_label.setDefaultTextColor(Qt.white)
                            self.powerup_label.setFont(QFont("Arial", 16))
                            label_width = self.powerup_label.boundingRect().width()
                            scene_center = self.sceneRect().center().x()
                            self.powerup_label.setPos(scene_center - label_width/2, 10)
                            self.addItem(self.powerup_label)
                        else:
                            self.powerup_label.setPlainText("Błędna odległość. Wybierz miejsce między {} a {} pikseli.".format(min_dist, max_dist))
                        event.accept()
                        return
                    new_cell = CellUnit(pos.x(), pos.y(), "player", self.copy_source.points)
                    self.cells.append(new_cell)
                    self.addItem(new_cell)
                    if self.logger:
                        self.logger.log("GameScene: Nowa komórka skopiowana z komórki o {} punktach.".format(self.copy_source.points))
                    self.copy_source = None
                    self.powerup_active = None
                    if hasattr(self, 'powerup_label'):
                        self.removeItem(self.powerup_label)
                        self.powerup_label = None
                    self.update()
                    event.accept()
                    return
            elif isinstance(clicked_item, QGraphicsItem):
                if self.powerup_active == POWERUP_FREEZE:
                    if isinstance(clicked_item, CellUnit):
                        if clicked_item.cell_type == "enemy":
                            clicked_item.frozen = True
                            clicked_item.freeze_end_time = time.time() + FREEZE_DURATION_SECONDS
                            if self.logger:
                                self.logger.log("GameScene: Komórka przeciwnika zamrożona.")
                            if hasattr(self, 'powerup_label') and self.powerup_label is not None:
                                self.removeItem(self.powerup_label)
                                self.powerup_label = None
                        else:
                            if self.powerup_label is None:
                                self.powerup_label = QGraphicsTextItem("Wybierz komórkę przeciwnika do zamrożenia.")
                                self.powerup_label.setDefaultTextColor(Qt.white)
                                self.powerup_label.setFont(QFont("Arial", 16))
                                label_width = self.powerup_label.boundingRect().width()
                                scene_center = self.sceneRect().center().x()
                                self.powerup_label.setPos(scene_center - label_width/2, 10)
                                self.addItem(self.powerup_label)
                            else:
                                self.powerup_label.setPlainText("Wybierz komórkę przeciwnika do zamrożenia.")
                    self.powerup_active = None
                    self.update()
                    event.accept()
                    return
                elif self.powerup_active == POWERUP_TAKEOVER:
                    if isinstance(clicked_item, CellUnit):
                        if clicked_item.cell_type == "enemy":
                            clicked_item.cell_type = "player"
                            clicked_item.update()
                            if self.logger:
                                self.logger.log("GameScene: Komórka przeciwnika przejęta.")
                            if hasattr(self, 'powerup_label') and self.powerup_label is not None:
                                self.removeItem(self.powerup_label)
                                self.powerup_label = None
                        else:
                            if self.powerup_label is None:
                                self.powerup_label = QGraphicsTextItem("Wybierz komórkę przeciwnika do przejęcia.")
                                self.powerup_label.setDefaultTextColor(Qt.white)
                                self.powerup_label.setFont(QFont("Arial", 16))
                                label_width = self.powerup_label.boundingRect().width()
                                scene_center = self.sceneRect().center().x()
                                self.powerup_label.setPos(scene_center - label_width/2, 10)
                                self.addItem(self.powerup_label)
                            else:
                                self.powerup_label.setPlainText("Wybierz komórkę przeciwnika do przejęcia.")
                    self.powerup_active = None
                    self.update()
                    event.accept()
                    return
                elif self.powerup_active == POWERUP_ADD_POINTS:
                    if isinstance(clicked_item, CellUnit):
                        if clicked_item.cell_type in ["player", "enemy"]:
                            clicked_item.points += 10
                            clicked_item.strength = (clicked_item.points // 10) + 1
                            clicked_item.update()
                            if self.logger:
                                self.logger.log("GameScene: Dodano 10 punktów do komórki.")
                            if hasattr(self, 'powerup_label') and self.powerup_label is not None:
                                self.removeItem(self.powerup_label)
                                self.powerup_label = None
                    self.powerup_active = None
                    self.update()
                    event.accept()
                    return
            else:
                if self.powerup_label is None:
                    self.powerup_label = QGraphicsTextItem("Nie kliknięto na komórkę. Wybierz komórkę docelową.")
                    self.powerup_label.setDefaultTextColor(Qt.white)
                    self.powerup_label.setFont(QFont("Arial", 16))
                    label_width = self.powerup_label.boundingRect().width()
                    scene_center = self.sceneRect().center().x()
                    self.powerup_label.setPos(scene_center - label_width/2, 10)
                    self.addItem(self.powerup_label)
                else:
                    self.powerup_label.setPlainText("Nie kliknięto na komórkę. Wybierz komórkę docelową.")
            self.powerup_active = None
            self.update()
            event.accept()
            return

        clicked_item = self.itemAt(event.scenePos(), QTransform())

        for cell in self.reachable_cells:
            cell.setHighlighted(False)
        self.reachable_cells = []

        if event.button() == Qt.LeftButton:
            if isinstance(clicked_item, CellUnit) and clicked_item.cell_type == "player":
                self.drag_start_cell = clicked_item
                self.calculate_reachable_cells()
            else:
                self.drag_start_cell = None
        elif event.button() == Qt.RightButton:
            if isinstance(clicked_item, CellUnit) and clicked_item.cell_type == "enemy":
                self.drag_start_cell = clicked_item
                self.calculate_reachable_cells()
            else:
                self.drag_start_cell = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_start_cell:
            if not self.drag_start_cell.can_create_new_connection():
                self.drag_start_cell = None
                self.drag_current_pos = None
                for cell in self.reachable_cells:
                    cell.setHighlighted(False)
                self.reachable_cells = []
                self.update()
                return
                
            self.drag_current_pos = event.scenePos()
            self.update()
        else:
            buttons = event.buttons()
            # W trybie 1 gracz (self.single_player True) ignorujemy interakcje z PPM
            if buttons & Qt.RightButton and self.single_player:
                return super().mouseMoveEvent(event)
            if buttons & Qt.LeftButton:
                connection_filter = "player"
            elif buttons & Qt.RightButton:
                connection_filter = "enemy"
            else:
                return super().mouseMoveEvent(event)
            P = event.scenePos()
            for conn in self.connections:
                if conn.connection_type == connection_filter:
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
                        # Dodajemy logowanie usunięcia mostu
                        self.move_history.append({
                            "timestamp": time.time(),
                            "description": f"Usunięto most między ({conn.source_cell.x:.0f}, {conn.source_cell.y:.0f}) a ({conn.target_cell.x:.0f}, {conn.target_cell.y:.0f})"
                        })
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
                        if self.turn_based_mode:
                            self.switch_turn()
                        break
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Na zakończenie przeciągania sprawdza, czy zwolniono przycisk nad inną komórką tego samego typu.
           Dla LPM mosty tworzy komórka gracza, a dla PPM – tymczasowo mosty przeciwnika."""
        for cell in self.reachable_cells:
            cell.setHighlighted(False)
        self.reachable_cells = []

        if self.drag_start_cell is None:
            return
            
        if not self.drag_start_cell.can_create_new_connection():
            self.drag_start_cell = None
            self.drag_current_pos = None
            self.update()
            return
            
        release_item = self.itemAt(event.scenePos(), QTransform())
        if self.turn_based_mode:
            if event.button() == Qt.LeftButton and self.current_turn != "player":
                return
            if event.button() == Qt.RightButton and self.current_turn != "enemy":
                return
        if event.button() == Qt.LeftButton:
            if isinstance(release_item, CellUnit) and release_item != self.drag_start_cell:
                dx = release_item.x - self.drag_start_cell.x
                dy = release_item.y - self.drag_start_cell.y
                distance = math.hypot(dx, dy)
                cost = int(distance / 20)
                if self.drag_start_cell.points >= cost:
                    # Tylko jeśli nie ma już mostu o tym samym typie (np. "player")
                    exists = any(((conn.source_cell == self.drag_start_cell and conn.target_cell == release_item) or
                                  (conn.source_cell == release_item and conn.target_cell == self.drag_start_cell))
                                  and conn.connection_type == "player" for conn in self.connections)
                    if not exists:
                        self.drag_start_cell.points -= cost
                        self.drag_start_cell.strength = (self.drag_start_cell.points // POINTS_PER_STRENGTH) + 1
                        self.drag_start_cell.update()
                        new_conn = self.create_connection(self.drag_start_cell, release_item, "player", cost)
                        if self.turn_based_mode:
                            self.switch_turn()
        elif event.button() == Qt.RightButton:
            if isinstance(release_item, CellUnit) and release_item != self.drag_start_cell:
                dx = release_item.x - self.drag_start_cell.x
                dy = release_item.y - self.drag_start_cell.y
                distance = math.hypot(dx, dy)
                cost = int(distance / 20)
                if self.drag_start_cell.points >= cost:
                    # Tylko jeśli nie ma już mostu o tym samym typie ("enemy")
                    exists = any(((conn.source_cell == self.drag_start_cell and conn.target_cell == release_item) or
                                  (conn.source_cell == release_item and conn.target_cell == self.drag_start_cell))
                                  and conn.connection_type == "enemy" for conn in self.connections)
                    if not exists:
                        self.drag_start_cell.points -= cost
                        self.drag_start_cell.strength = (self.drag_start_cell.points // POINTS_PER_STRENGTH) + 1
                        self.drag_start_cell.update()
                        new_conn = self.create_connection(self.drag_start_cell, release_item, "enemy", cost)
                        if self.turn_based_mode:
                            self.switch_turn()
        self.drag_start_cell = None
        self.drag_current_pos = None
        self.update()

    def check_game_state(self):
        """Check if player has won or lost the level"""
        player_cells = sum(1 for cell in self.cells if cell.cell_type == "player")
        enemy_cells = sum(1 for cell in self.cells if cell.cell_type == "enemy")

        if player_cells == 0:
            self.game_over(False)
        elif enemy_cells == 0:
            self.game_over(True)

    def game_over(self, victory):
        self.timer.stop()
        self.points_timer.stop()
        final_result = "Wygrana!" if victory else "Przegrana!"
        self.game_over_text = final_result
        if self.logger:
            self.logger.log(f"GameScene: Gra zakończona - {self.game_over_text}.")
        # Zapis stanu przed ostatnim ruchem
        points_status = "; ".join(
            f"({cell.cell_type} @ {int(cell.x)},{int(cell.y)}: {cell.points} pts)"
            for cell in self.cells
        )
        self.move_history.append({
            "timestamp": time.time(),
            "description": f"Status przed ostatnim ruchem: {points_status}"
        })
        # Zapis ostatecznego wyniku
        self.move_history.append({
            "timestamp": time.time(),
            "description": f"Wynik: {final_result}"
        })
        # Dodane: ponowny zapis finalnego stanu po ogłoszeniu wyniku
        final_status = "; ".join(
            f"({cell.cell_type} @ {int(cell.x)},{int(cell.y)}: {cell.points} pts)"
            for cell in self.cells
        )
        self.move_history.append({
            "timestamp": time.time(),
            "description": f"Status po ogłoszeniu wyniku: {final_status}"
        })
        self.update()
        game_history.save_game_history(self, "replay.xml")  # automatyczny zapis replay
        QTimer.singleShot(2000, self.show_return_button)

    def show_return_button(self):
        if self.game_over_text:
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
                    for reach_cell in self.reachable_cells:
                        reach_cell.setHighlighted(False)
                    self.reachable_cells = []

                    self.calculate_reachable_cells()

        for conn in self.connections:
            if conn.connection_type in ["player", "enemy"]:
                if conn.source_cell.frozen or conn.target_cell.frozen:
                    continue
                if conn.source_cell.points >= 1:
                    conn.source_cell.points -= 1
                    conn.source_cell.strength = (conn.source_cell.points // POINTS_PER_STRENGTH) + 1
                    conn.source_cell.update()
                    conn.dots.append(0)

                    if self.drag_start_cell == conn.source_cell:
                        for reach_cell in self.reachable_cells:
                            reach_cell.setHighlighted(False)
                        self.reachable_cells = []

                        self.calculate_reachable_cells()
        points_status = "; ".join(
            f"({cell.cell_type} @ {int(cell.x)},{int(cell.y)}: {cell.points} pts)"
            for cell in self.cells
        )
        self.move_history.append({
            "timestamp": time.time(),
            "description": f"Status punktowy: {points_status}"
        })

    def drawForeground(self, painter, rect):
        if self.turn_based_mode and self.current_turn:
            info_text = f"Runda: {self.current_turn.upper()} - Pozostało: {self.round_time_remaining}s"
            font = QFont(FONT_FAMILY, GAME_TURN_FONT_SIZE, QFont.Bold)
            painter.setFont(font)
            painter.setPen(QPen(Qt.white))
            painter.drawText(rect.adjusted(10, 10, -10, -10), Qt.AlignTop | Qt.AlignHCenter, info_text)
        if self.drag_start_cell and self.drag_current_pos:
            if self.turn_based_mode and self.drag_start_cell.cell_type != self.current_turn:
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
                    line_color = config.COLOR_CONN_PLAYER
                else:
                    line_color = config.COLOR_CONN_ENEMY
                color = line_color if self.drag_start_cell.points >= cost else QColor(255, 0, 0)
                painter.setPen(QPen(color, 2))
                painter.drawLine(QPointF(self.drag_start_cell.x, self.drag_start_cell.y), target_point)
        for conn in self.connections:
            source = QPointF(conn.source_cell.x, conn.source_cell.y)
            target = QPointF(conn.target_cell.x, conn.target_cell.y)
            if hasattr(conn, 'conflict') and conn.conflict:
                mid_point = QPointF((source.x() + target.x()) / 2, (source.y() + target.y()) / 2)
                painter.setPen(QPen(config.COLOR_CONN_CONFLICT_LEFT, 3))
                painter.drawLine(source, mid_point)
                painter.setPen(QPen(config.COLOR_CONN_CONFLICT_RIGHT, 3))
                painter.drawLine(mid_point, target)
            else:
                if conn.connection_type == "player":
                    painter.setPen(QPen(config.COLOR_CONN_PLAYER, 3))
                else:
                    painter.setPen(QPen(config.COLOR_CONN_ENEMY, 3))
                painter.drawLine(source, target)
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
        if self.game_over_text is not None:
            font = QFont(FONT_FAMILY, GAME_OVER_FONT_SIZE, QFont.Bold)
            painter.setFont(font)
            text = self.game_over_text
            scene_rect = self.sceneRect()
            text_rect = painter.boundingRect(scene_rect, Qt.AlignCenter, text)
            offsets = [(-2, -2), (-2, 2), (2, -2), (2, 2)]
            painter.setPen(QPen(Qt.black, 2))
            for dx, dy in offsets:
                painter.drawText(text_rect.translated(dx, dy), Qt.AlignCenter, text)
            painter.setPen(QPen(Qt.white, 2))
            painter.drawText(text_rect, Qt.AlignCenter, text)

        if self.hint_active and self.hint_visible and self.hint_source and self.hint_target:
            source_point = QPointF(self.hint_source.x, self.hint_source.y)
            target_point = QPointF(self.hint_target.x, self.hint_target.y)

            hint_pen = QPen(config.COLOR_HINT_PRIMARY, 3, Qt.DashLine)
            painter.setPen(hint_pen)
            painter.drawLine(source_point, target_point)

            arrow_size = 15
            dx = target_point.x() - source_point.x()
            dy = target_point.y() - source_point.y()
            length = math.sqrt(dx * dx + dy * dy)
            if length > 0:
                dx, dy = dx / length, dy / length

                arrow_point_x = source_point.x() + dx * length * 0.7
                arrow_point_y = source_point.y() + dy * length * 0.7

                painter.setBrush(config.COLOR_HINT_PRIMARY)
                points = [
                    QPointF(arrow_point_x, arrow_point_y),
                    QPointF(arrow_point_x - arrow_size * (dx + dy * 0.5), arrow_point_y - arrow_size * (dy - dx * 0.5)),
                    QPointF(arrow_point_x - arrow_size * (dx - dy * 0.5), arrow_point_y - arrow_size * (dy + dx * 0.5))
                ]
                painter.drawPolygon(points)

            painter.setPen(QPen(config.COLOR_HINT_PRIMARY, 3, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            highlight_radius = 40
            painter.drawEllipse(source_point, highlight_radius, highlight_radius)

            painter.setPen(QPen(config.COLOR_HINT_SECONDARY, 3, Qt.DashLine))
            painter.drawEllipse(target_point, highlight_radius, highlight_radius)

            font = QFont("Arial", 12, QFont.Bold)
            painter.setFont(font)

            label_width = 40
            label_height = 25

            source_label_rect = QRectF(
                source_point.x() - label_width/2,
                source_point.y() - highlight_radius - label_height - 5,
                label_width, label_height
            )

            painter.setBrush(config.COLOR_HINT_PRIMARY)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(source_label_rect, 5, 5)

            painter.setPen(Qt.black)
            painter.drawText(source_label_rect, Qt.AlignCenter, "OD")

            target_label_rect = QRectF(
                target_point.x() - label_width/2,
                target_point.y() - highlight_radius - label_height - 5,
                label_width, label_height
            )

            painter.setBrush(config.COLOR_HINT_SECONDARY)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(target_label_rect, 5, 5)

            painter.setPen(Qt.black)
            painter.drawText(target_label_rect, Qt.AlignCenter, "DO")

            if self.hint_cost > 0:
                mid_x = (self.hint_source.x + self.hint_target.x) / 2
                mid_y = (self.hint_source.y + self.hint_target.y) / 2

                font = QFont("Arial", 12, QFont.Bold)
                painter.setFont(font)
                cost_text = f"Koszt: {self.hint_cost}"

                text_width = 80
                text_height = 20

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

            if not self.hint_visible:
                self.hint_blink_count += 1

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
            self.hint_visible = True
            self.hint_blink_count = 0
            QMessageBox.information(None, "Podpowiedź",
                f"Sugerowany ruch: Połącz komórkę z {self.hint_source.points} punktami "
                f"z komórką typu {self.hint_target.cell_type}. Koszt: {self.hint_cost}")
        else:
            self.hint_active = False
            self.hint_visible = False
            self.hint_blink_count = 0
            QMessageBox.information(None, "Podpowiedź", "Brak sugerowanych ruchów.")

        self.update()

    def activate_powerup(self, powerup_type):
        self.powerup_active = powerup_type
        if self.logger:
            self.logger.log(f"GameScene: Powerup {powerup_type} aktywowany. Kliknij na docelową komórkę.")
        if hasattr(self, 'powerup_label') and self.powerup_label is not None:
            self.removeItem(self.powerup_label)
        self.powerup_label = QGraphicsTextItem(f"Powerup {powerup_type} aktywowany. Wybierz komórkę docelową.")
        self.powerup_label.setDefaultTextColor(Qt.white)
        self.powerup_label.setFont(QFont("Arial", 16))
        effect = QGraphicsDropShadowEffect()
        effect.setOffset(0, 0)
        effect.setBlurRadius(3)
        effect.setColor(Qt.black)
        self.powerup_label.setGraphicsEffect(effect)
        label_width = self.powerup_label.boundingRect().width()
        scene_center = self.sceneRect().center().x()
        self.powerup_label.setPos(scene_center - label_width/2, 10)
        self.addItem(self.powerup_label)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_H:
            self.show_hint()
            event.accept()
            return

        if event.key() == Qt.Key_Escape:
            if self.logger:
                self.logger.log("GameScene: Gracz przerwał rozgrywkę.")
            self.timer.stop()
            self.points_timer.stop()

            if self.views() and self.views()[0].parent():
                self.views()[0].parent().show_menu()
            event.accept()
            return

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

    def start_turn_timer(self):
        self.current_turn = "player"
        self.round_time_remaining = self.turn_duration
        self.turn_timer.timeout.connect(self.update_turn_timer)
        self.turn_timer.start(TURN_TIMER_INTERVAL_MS)
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
        if self.logger:
            self.logger.log(f"GameScene: Zmiana tury, teraz: {self.current_turn}.")
        self.update()

    def start_enemy_timer(self):
        """Uruchomienie timera do wykonywania ruchów AI dla przeciwnika"""
        if self.enemy_timer:
            self.enemy_timer.stop()
        self.enemy_timer = QTimer()
        self.enemy_timer.timeout.connect(self.enemy_move)
        self.enemy_timer.start(3000)  # interwał 3000 ms

    def enemy_move(self):
        """Metoda wykonująca ruch przeciwnika przy użyciu AI"""
        if not self.single_player:
            return
        best_move = self.game_ai.analyze_best_move(cell_type="enemy")
        if best_move:
            source, target, cost = best_move
            if source.points >= cost:
                source.points -= cost
                source.strength = (source.points // POINTS_PER_STRENGTH) + 1
                self.create_connection(source, target, "enemy", cost)
        self.update()