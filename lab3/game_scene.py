import json
import math
import os
import time
import datetime

from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import QCursor, QColor, QLinearGradient, QPen, QFont, QTransform
from PyQt5.QtWidgets import (
    QGraphicsScene, QGraphicsDropShadowEffect, QGraphicsItem, QMenu, 
    QMessageBox, QGraphicsTextItem, QDialog, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QListWidget
)

import config
from game_ai import GameAI
from game_objects import CellUnit, CellConnection
import game_history

class GameScene(QGraphicsScene):
    """Main game scene class"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(0, 0, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
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
        self.points_timer.start(config.POINTS_INTERVAL_MS)
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
        self.current_turn = "player"  # Inicjalizacja z wartością domyślną zamiast None
        self.turn_duration = config.TURN_DURATION_SECONDS
        self.round_time_remaining = self.turn_duration
        self.turn_timer = QTimer()
        self.turn_timer.setInterval(1000)  # Ustawienie interwału na 1 sekundę

        self.logger = None
        self.powerup_active = None
        self.copy_source = None

        self.single_player = False
        self.enemy_timer = None
        self.move_history = []
        self.last_state_record = 0
        self.hover_connection = None  # Dodana zmienna do śledzenia mostu pod kursorem

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
                    
        if self.turn_based_mode:
            self.start_turn_timer()  # Inicjuj timer, aby ustawić start tury

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
        if source.cell_type != conn_type:
            if self.logger:
                self.logger.log(f"DEBUG: Niepoprawny typ mostu. Komórka ({source.x:.0f}, {source.y:.0f}) typu {source.cell_type} próbuje utworzyć most typu {conn_type}. Przypisano typ {source.cell_type}.")
            conn_type = source.cell_type
        connection = CellConnection(source, target, conn_type)
        connection.cost = cost
        for conn in self.connections:
            if conn.source_cell == target and conn.target_cell == source and conn.connection_type != conn_type:
                connection.conflict = True
                conn.conflict = True
                return
        if not hasattr(connection, 'conflict'):
            connection.conflict = False
        source.connections.append(connection)
        target.connections.append(connection)
        self.connections.append(connection)
        if self.logger:
            self.logger.log(f"GameScene: Utworzono most między komórkami przy ({source.x:.0f}, {source.y:.0f}) i ({target.x:.0f}, {target.y:.0f}) o koszcie {connection.cost}.")
        self.move_history.append({
            "timestamp": time.time(),
            "description": f"Utworzono most między ({source.x:.0f}, {source.y:.0f}) a ({target.x:.0f}, {target.y:.0f}) o koszcie {connection.cost}"
        })
        # Jeśli gra działa w trybie multiplayer, wyślij aktualizację do drugiego gracza
        # Dodajemy dodatkowy warunek, by uniknąć rekurencyjnego wysyłania wiadomości
        if hasattr(self, "network_send_callback") and self.network_send_callback and not hasattr(source, '_skip_network'):
            source._skip_network = True  # Oznaczamy komórkę jako przetwarzaną, by uniknąć ponownego wysłania
            try:
                msg = f"create_bridge;{source.x};{source.y};{target.x};{target.y};{cost}"
                self.network_send_callback(msg)
                if self.logger:
                    self.logger.log(f"GameScene: Wysłano informację o utworzeniu mostu: {msg}")
            finally:
                delattr(source, '_skip_network')  # Usuwamy tymczasowy atrybut
        return connection

    def process_network_message(self, message):
        """Analizuje odebrane dane i aktualizuje stan gry."""
        if message.startswith("snapshot_full;") or message.startswith("snapshot_part;"):
            try:
                parts = message.strip().split(";", 3 if message.startswith("snapshot_part;") else 1)
                
                if message.startswith("snapshot_full;"):
                    json_data = parts[1]
                    import json
                    snapshot = json.loads(json_data)
                    self.apply_game_state_snapshot(snapshot)
                    return
                else:  # Obsługa części snapshotu
                    part_number = int(parts[1])
                    total_parts = int(parts[2])
                    content = parts[3]
                    
                    # Tworzymy atrybut dla przechowywania części snapshotu
                    if not hasattr(self, '_snapshot_parts'):
                        self._snapshot_parts = {}
                    
                    # Zapisujemy część
                    self._snapshot_parts[part_number] = content
                    
                    # Sprawdzamy czy mamy wszystkie części
                    if len(self._snapshot_parts) == total_parts:
                        # Łączymy części
                        combined_json = "".join(self._snapshot_parts[i+1] for i in range(total_parts))
                        # Resetujemy części
                        self._snapshot_parts = {}
                        
                        # Parsujemy i stosujemy
                        import json
                        snapshot = json.loads(combined_json)
                        self.apply_game_state_snapshot(snapshot)
                        
                        if self.logger:
                            self.logger.log(f"GameScene: Połączono {total_parts} części snapshotu gry")
                    return
            except Exception as e:
                if self.logger:
                    self.logger.log(f"GameScene: Błąd podczas przetwarzania snapshotu: {e}")
                
        elif message.startswith("game_over;"):
            # Obsługa wiadomości o zakończeniu gry
            parts = message.strip().split(";")
            if len(parts) >= 2:
                winner = parts[1]
                if self.logger:
                    self.logger.log(f"GameScene: Otrzymano informację o zakończeniu gry, zwycięzca: {winner}")
                
                # Obliczamy czy to my wygraliśmy czy przeciwnik
                victory = (winner == self.multiplayer_role)
                
                # Ustawiamy tekst wyniku i zatrzymujemy grę
                final_result = "Wygrana!" if victory else "Przegrana!"
                self.game_over_text = final_result
                self.timer.stop()
                self.points_timer.stop()
                self.stop_all_timers()
                
                # Aktualizujemy widok
                self.update()

                # Zapisujemy stan końcowy meczu w historii
                self.move_history.append({
                    "timestamp": time.time(),
                    "description": f"Gra zakończona: {final_result}"
                })
                
                # Zapisujemy historię gry tak samo jak w metodzie game_over
                self.save_game_history()
                
                # Pokażemy przycisk powrotu do menu
                QTimer.singleShot(2000, self.show_return_button)
        parts = message.strip().split(";")
        if parts[0] == "create_bridge" and len(parts) == 6:
            try:
                source_x = float(parts[1])
                source_y = float(parts[2])
                target_x = float(parts[3])
                target_y = float(parts[4])
                cost = int(parts[5])
                source_cell = None
                target_cell = None
                # Znajdujemy komórki w pobliżu przekazanych współrzędnych - zwiększamy tolerancję
                for cell in self.cells:
                    if abs(cell.x - source_x) < 10 and abs(cell.y - source_y) < 10:
                        source_cell = cell
                    if abs(cell.x - target_x) < 10 and abs(cell.y - target_y) < 10:
                        target_cell = cell
                
                if source_cell and target_cell:
                    # Sprawdzamy czy połączenie już istnieje
                    exists = any(((conn.source_cell == source_cell and conn.target_cell == target_cell) or 
                                  (conn.source_cell == target_cell and conn.target_cell == source_cell))
                                  for conn in self.connections)
                    
                    if not exists:
                        # Określamy typ połączenia na podstawie typu komórki źródłowej
                        conn_type = source_cell.cell_type
                        
                        # Odejmujemy punkty tylko jeśli to nowe połączenie
                        source_cell.points -= cost
                        source_cell.strength = (source_cell.points // config.POINTS_PER_STRENGTH) + 1
                        source_cell.update()
                        
                        # Tworzymy połączenie z określonym typem
                        self.create_connection(source_cell, target_cell, conn_type, cost)
                        
                        if self.logger:
                            self.logger.log(f"GameScene: Utworzono most sieciowy między {conn_type} komórkami.")
                    else:
                        if self.logger:
                            self.logger.log("GameScene: Połączenie już istnieje, pomijam.")
                else:
                    if self.logger:
                        self.logger.log("GameScene: Nie znaleziono komórek dla aktualizacji create_bridge.")
                        self.logger.log(f"GameScene: Szukam: source({source_x},{source_y}), target({target_x},{target_y})")
                        for cell in self.cells:
                            self.logger.log(f"GameScene: Dostępna komórka: ({cell.x},{cell.y})")
            except Exception as e:
                if self.logger:
                    self.logger.log(f"GameScene: Błąd przetwarzania wiadomości create_bridge: {e}")
        elif parts[0] == "update_turn_time" and len(parts) == 2:
            try:
                time_remaining = int(parts[1])
                # Aktualizujemy czas tury tylko jeśli to tura przeciwnika
                if self.current_turn != self.multiplayer_role:
                    self.round_time_remaining = time_remaining
                    if self.logger:
                        self.logger.log(f"GameScene: Otrzymano aktualizację czasu tury: {time_remaining}s")
                    self.update()
            except Exception as e:
                if self.logger:
                    self.logger.log(f"GameScene: Błąd przetwarzania wiadomości update_turn_time: {e}")
        elif parts[0] == "switch_turn" and len(parts) >= 1:
            # Otrzymano żądanie przełączenia tury
            if self.turn_based_mode:
                if self.logger:
                    self.logger.log(f"GameScene: Otrzymano żądanie przełączenia tury. Aktualna tura: {self.current_turn}, rola: {self.multiplayer_role}")
                
                # KLUCZOWA POPRAWKA: Zawsze ustawiamy swoją turę jako aktywną gdy odbierzemy komunikat switch_turn
                self.current_turn = self.multiplayer_role
                
                # Resetujemy czas tury na pełną wartość
                self.round_time_remaining = self.turn_duration
                
                # Zatrzymujemy i resetujemy timer
                self.turn_timer.stop()
                try:
                    self.turn_timer.timeout.disconnect()
                except TypeError:
                    pass
                
                # Wysyłamy potwierdzenie przełączenia tury
                if hasattr(self, "network_send_callback") and self.network_send_callback:
                    self.network_send_callback(f"turn_confirm;{self.turn_duration}")
                    if self.logger:
                        self.logger.log(f"GameScene: Wysłano potwierdzenie przełączenia tury")
                
                # Ponownie uruchamiamy timer
                self.turn_timer.timeout.connect(self.update_turn_timer)
                self.turn_timer.start(1000)
                
                if self.logger:
                    self.logger.log(f"GameScene: Tura przełączona na {self.current_turn}, timer zresetowany")
                
                self.update()
        elif parts[0] == "turn_confirm" and len(parts) >= 2:
            try:
                # Otrzymano potwierdzenie przełączenia tury, z informacją o czasie
                if self.turn_based_mode:
                    # Upewniamy się że nie jesteśmy teraz aktywni
                    if self.current_turn == self.multiplayer_role:
                        if self.logger:
                            self.logger.log(f"GameScene: BŁĄD - otrzymano potwierdzenie przełączenia tury, ale nadal jest nasza tura")
                    else:
                        # Synchronizujemy pozostały czas
                        sync_time = int(parts[1])
                        if self.round_time_remaining != sync_time:
                            self.round_time_remaining = sync_time
                            if self.logger:
                                self.logger.log(f"GameScene: Zsynchronizowano czas tury z przeciwnikiem: {sync_time}s")
                        self.update()
            except Exception as e:
                if self.logger:
                    self.logger.log(f"GameScene: Błąd przetwarzania potwierdzenia tury: {e}")
        elif parts[0] == "set_role" and len(parts) == 2:
            role = parts[1].strip()
            # Ustawiamy rolę zgodnie z komunikatem
            if role in ["player", "enemy"]:
                # Sprawdzamy czy zmiana roli jest uprawniona
                # Jeśli gracz jest inicjatorem, to musi być zawsze player
                if hasattr(self, 'is_connection_initiator'):
                    if self.is_connection_initiator and role != "player":
                        if self.logger:
                            self.logger.log(f"GameScene: Odrzucono próbę zmiany roli z player na {role} dla inicjatora")
                        return
                    elif not self.is_connection_initiator and role != "enemy":
                        if self.logger:
                            self.logger.log(f"GameScene: Odrzucono próbę zmiany roli z enemy na {role} dla odbiorcy")
                        return
                
                self.multiplayer_role = role
                if self.logger:
                    self.logger.log(f"GameScene: Ustawiono rolę multiplayer: {self.multiplayer_role}")
            else:
                if self.logger:
                    self.logger.log(f"GameScene: Otrzymano nieprawidłową rolę: {role}")
        # Dodanie obsługi synchronizacji punktów z innym urządzeniem
        elif parts[0] == "sync_cell" and len(parts) >= 4:
            try:
                cell_index = int(parts[1])
                cell_type = parts[2]
                cell_points = int(parts[3])
                
                if 0 <= cell_index < len(self.cells):
                    cell = self.cells[cell_index]
                    # Aktualizujemy tylko komórki które nie są przechwycone
                    if cell.cell_type == "neutral" or cell.cell_type == cell_type:
                        cell.cell_type = cell_type
                        cell.points = cell_points
                        cell.strength = (cell.points // config.POINTS_PER_STRENGTH) + 1
                        cell.update()
                        if self.logger:
                            self.logger.log(f"GameScene: Zsynchronizowano komórkę {cell_index}: {cell_type}, {cell_points} punktów")
            except Exception as e:
                if self.logger:
                    self.logger.log(f"GameScene: Błąd synchronizacji komórki: {e}")
        # Dodajemy obsługę usuwania mostów przez sieć
        elif parts[0] == "remove_bridge" and len(parts) >= 5:
            try:
                source_x = float(parts[1])
                source_y = float(parts[2])
                target_x = float(parts[3])
                target_y = float(parts[4])
                
                # Znajdź most do usunięcia
                for conn in list(self.connections):
                    sx, sy = conn.source_cell.x, conn.source_cell.y
                    tx, ty = conn.target_cell.x, conn.target_cell.y
                    
                    # Sprawdź obie orientacje mostu (A->B lub B->A)
                    if ((abs(sx - source_x) < 10 and abs(sy - source_y) < 10 and 
                         abs(tx - target_x) < 10 and abs(ty - target_y) < 10) or
                        (abs(sx - target_x) < 10 and abs(sy - target_y) < 10 and 
                         abs(tx - source_x) < 10 and abs(ty - source_y) < 10)):
                        
                        # Usuń most z list
                        if conn in conn.source_cell.connections:
                            conn.source_cell.connections.remove(conn)
                        if conn in conn.target_cell.connections:
                            conn.target_cell.connections.remove(conn)
                        self.connections.remove(conn)
                        
                        # Zapisz informację o usunięciu mostu w historii
                        self.move_history.append({
                            "timestamp": time.time(),
                            "description": f"Usunięto most między ({conn.source_cell.x:.0f}, {conn.source_cell.y:.0f}) a ({conn.target_cell.x:.0f}, {conn.target_cell.y:.0f})"
                        })
                        
                        if self.logger:
                            self.logger.log(f"GameScene: Usunięto most przez komunikat sieciowy między ({source_x},{source_y}) a ({target_x},{target_y})")
                        break
                
            except Exception as e:
                if self.logger:
                    self.logger.log(f"GameScene: Błąd przetwarzania wiadomości remove_bridge: {e}")

    def update_game(self):
        for conn in list(self.connections):
            if conn.source_cell.cell_type != conn.connection_type:
                if self.logger:
                    self.logger.log(f"DEBUG: Usunięto niespójny most: Komórka ({conn.source_cell.x:.0f}, {conn.source_cell.y:.0f}) typu {conn.source_cell.cell_type} ma most typu {conn.connection_type}.")
                self.move_history.append({
                    "timestamp": time.time(),
                    "description": f"Usunięto most między ({conn.source_cell.x:.0f}, {conn.source_cell.y:.0f}) a ({conn.target_cell.x:.0f}, {conn.target_cell.y:.0f})"
                })
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
                            if conn.target_cell.points < config.MAX_CELL_POINTS:  # Sprawdzenie limitu punktów
                                conn.target_cell.points += 1
                        else:
                            conn.target_cell.points -= 1
                            if conn.target_cell.points <= 0:
                                captured = conn.target_cell
                                if self.logger:
                                    self.logger.log(f"DEBUG: Przechwytywanie komórki ({captured.x:.0f}, {captured.y:.0f}). Punkty przed przejęciem: {captured.points, conn.connection_type}.")
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
                        conn.target_cell.strength = (conn.target_cell.points // config.POINTS_PER_STRENGTH) + 1
                        conn.target_cell.update()
                        finished.append(i)

                for index in sorted(finished, reverse=True):
                    del conn.dots[index]

        for conn in self.connections:
            if hasattr(conn, 'conflict') and conn.conflict:
                if not hasattr(conn, 'conflict_progress'):
                    conn.conflict_progress = 0
                conn.conflict_progress += 0.016
                if conn.conflict_progress >= 1.0:
                    conn.source_cell.points -= 1
                    conn.target_cell.points -= 1
                    conn.source_cell.strength = (conn.source_cell.points // config.POINTS_PER_STRENGTH) + 1
                    conn.target_cell.strength = (conn.target_cell.points // config.POINTS_PER_STRENGTH) + 1
                    conn.source_cell.update()
                    conn.target_cell.update()

        for cell in self.cells:
            if cell.points <= 0:
                for conn in list(self.connections):
                    if hasattr(conn, 'conflict') and conn.conflict and (conn.source_cell == cell or conn.target_cell == cell):
                        refund = conn.cost // 2
                        cell.points += refund
                        self.move_history.append({
                            "timestamp": time.time(),
                            "description": f"Usunięto most między ({conn.source_cell.x:.0f}, {conn.source_cell.y:.0f}) a ({conn.target_cell.x:.0f}, {conn.target_cell.y:.0f})"
                        })
                        if conn in conn.source_cell.connections:
                            conn.source_cell.connections.remove(conn)
                        if conn in conn.target_cell.connections:
                            conn.target_cell.connections.remove(conn)
                        self.connections.remove(conn)
                        cell.update()

        now = time.time()
        if now - self.last_state_record >= 1.0:
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

            # Sprawdzamy czy istnieje już połączenie tego samego typu co drag_start_cell
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
        # Prawidłowe mapowanie przycisków w trybie sieciowym
        if hasattr(self, 'is_multiplayer') and self.is_multiplayer:
            if self.multiplayer_role == "player":
                actual_button = Qt.LeftButton  # Gracz zawsze używa lewego przycisku
            else:  # gdy multiplayer_role == "enemy"
                actual_button = Qt.RightButton  # Przeciwnik zawsze używa prawego przycisku
        else:
            actual_button = event.button()

        # Jeżeli tryb turowy i multiplayer – wykonywanie ruchu tylko w odpowiedniej turze
        if hasattr(self, 'is_multiplayer') and self.is_multiplayer:
            if self.turn_based_mode and self.current_turn != self.multiplayer_role:
                # Dodatkowy log dla lepszego debugowania
                if self.logger:
                    self.logger.log(f"GameScene: Tura zablokowana - teraz {self.current_turn}, twoja rola {self.multiplayer_role}")
                event.ignore()
                return

        if event.button() == Qt.RightButton and self.single_player:
            event.accept()
            return

        # Sprawdzenie czy w trybie turowym odpowiedni gracz wykonuje ruch
        if self.turn_based_mode:
            if (actual_button == Qt.LeftButton and self.current_turn != "player") or \
               (actual_button == Qt.RightButton and self.current_turn != "enemy"):
                if self.logger:
                    self.logger.log(f"GameScene: Teraz tura {self.current_turn}, nie można wykonać ruchu.")
                event.ignore()
                return

        if self.powerup_active is not None:
            clicked_item = self.itemAt(event.scenePos(), QTransform())
            if self.powerup_active == config.POWERUP_NEW_CELL:
                if self.copy_source is None:
                    if isinstance(clicked_item, CellUnit):
                        self.copy_source = clicked_item
                        if self.logger:
                            self.logger.log("GameScene: Komórka wybrana do kopiowania. Teraz wybierz miejsce, gdzie ją postawić.")
                        if hasattr(self, 'powerup_label'):
                            self.powerup_label.setPlainText("Wybierz miejsce: odległość ≥ 2*promień i ≤ {}*promień".format(config.NEW_CELL_COPY_RANGE_FACTOR))
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
                    max_dist = config.NEW_CELL_COPY_RANGE_FACTOR * radius
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
                if self.powerup_active == config.POWERUP_FREEZE:
                    if isinstance(clicked_item, CellUnit):
                        if clicked_item.cell_type == "enemy":
                            clicked_item.frozen = True
                            clicked_item.freeze_end_time = time.time() + config.FREEZE_DURATION_SECONDS
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
                elif self.powerup_active == config.POWERUP_TAKEOVER:
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
                elif self.powerup_active == config.POWERUP_ADD_POINTS:
                    if isinstance(clicked_item, CellUnit):
                        if clicked_item.cell_type in ["player", "enemy"]:
                            clicked_item.points = min(clicked_item.points + 10, config.MAX_CELL_POINTS)
                            clicked_item.strength = (clicked_item.points // config.POINTS_PER_STRENGTH) + 1
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

        if actual_button == Qt.LeftButton:
            if isinstance(clicked_item, CellUnit) and clicked_item.cell_type == "player":
                self.drag_start_cell = clicked_item
                self.calculate_reachable_cells()
            else:
                self.drag_start_cell = None
        # Dodajemy obsługę prawego przycisku myszy dla trybu 2 graczy (nie single_player)
        elif actual_button == Qt.RightButton and not self.single_player:
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
            # Znajdź most pod kursorem do podświetlenia
            # (Zawsze sprawdzaj, nawet jeśli nie wciskamy przycisku)
            P = event.scenePos()
            old_hover_connection = self.hover_connection
            self.hover_connection = None
            
            # Znajdź najbliższy most pod kursorem
            min_distance = 15.0  # Zwiększony próg wykrywania z 5 na 15 pikseli
            for conn in self.connections:
                if (self.turn_based_mode and self.current_turn != conn.connection_type and 
                    hasattr(self, 'is_multiplayer') and self.is_multiplayer):
                    continue  # Pomijamy mosty, których nie możemy usunąć w trybie sieciowym
                
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
                dist = math.hypot(P.x() - Qx, P.y() - Qy)
                
                if dist < min_distance:
                    min_distance = dist
                    self.hover_connection = conn
            
            # Aktualizuj widok, jeśli zmienił się podświetlony most
            if old_hover_connection != self.hover_connection:
                self.update()
            
            buttons = event.buttons()
            # Sprawdź, czy usuwamy most poprzez przeciągnięcie
            if buttons & Qt.LeftButton or buttons & Qt.RightButton:
                if buttons & Qt.RightButton and self.single_player:
                    return super().mouseMoveEvent(event)
                    
                # W trybie sieciowym, pozwalamy na usuwanie mostów lewym i prawym przyciskiem
                if hasattr(self, 'is_multiplayer') and self.is_multiplayer:
                    # Sprawdzamy tylko czy typ mostu zgadza się z rolą gracza
                    connection_filter = self.multiplayer_role
                else:
                    # W trybie lokalnym, zachowujemy oryginalne zachowanie
                    if buttons & Qt.LeftButton:
                        connection_filter = "player"
                    elif buttons & Qt.RightButton:
                        connection_filter = "enemy"
                    else:
                        return super().mouseMoveEvent(event)
                
                # Używamy już znalezionego mostu pod kursorem
                if self.hover_connection and self.hover_connection.connection_type == connection_filter:
                    conn = self.hover_connection
                    
                    # Dodatkowe sprawdzenie dla trybu sieciowego
                    if (hasattr(self, 'is_multiplayer') and self.is_multiplayer and 
                        self.turn_based_mode and conn.connection_type != self.multiplayer_role):
                        if self.logger:
                            self.logger.log(f"Nie można usunąć mostu w turze przeciwnika")
                        return super().mouseMoveEvent(event)
                    
                    # Może być potrzebne do obliczenia podziału punktów
                    P = event.scenePos()
                    A = QPointF(conn.source_cell.x, conn.source_cell.y)
                    B = QPointF(conn.target_cell.x, conn.target_cell.y)
                    AB = QPointF(B.x() - A.x(), B.y() - A.y())
                    AP = QPointF(P.x() - A.x(), P.y() - A.y())
                    ab2 = AB.x() ** 2 + AB.y() ** 2
                    t = (AP.x() * AB.x() + AP.y() * AB.y()) / ab2
                    if t < 0: t = 0
                    if t > 1: t = 1
                    
                    # Zapisz informację o usunięciu mostu
                    self.move_history.append({
                        "timestamp": time.time(),
                        "description": f"Usunięto most między ({conn.source_cell.x:.0f}, {conn.source_cell.y:.0f}) a ({conn.target_cell.x:.0f}, {conn.target_cell.y:.0f})"
                    })
                    
                    # Usuń most z list
                    if conn in self.connections:
                        self.connections.remove(conn)
                    if conn in conn.source_cell.connections:
                        conn.source_cell.connections.remove(conn)
                    if conn in conn.target_cell.connections:
                        conn.target_cell.connections.remove(conn)
                    
                    # Oblicz zwrot punktów
                    cost = getattr(conn, "cost", 0)
                    source_points = round(t * cost)
                    target_points = cost - source_points
                    
                    # Zwróć punkty odpowiednio komórkom
                    if conn.connection_type == "player":
                        if conn.target_cell.cell_type != "player":
                            conn.source_cell.points += source_points
                            conn.target_cell.points -= target_points
                            if conn.target_cell.points <= 0:
                                conn.target_cell.cell_type = "player"
                                conn.target_cell.points = abs(conn.target_cell.points)
                        else:
                            conn.source_cell.points = min(conn.source_cell.points + source_points, config.MAX_CELL_POINTS)
                            conn.target_cell.points = min(conn.target_cell.points + target_points, config.MAX_CELL_POINTS)
                    elif conn.connection_type == "enemy":
                        if conn.target_cell.cell_type != "enemy":
                            conn.source_cell.points += source_points
                            conn.target_cell.points -= target_points
                            if conn.target_cell.points <= 0:
                                conn.target_cell.cell_type = "enemy"
                                conn.target_cell.points = abs(conn.target_cell.points)
                        else:
                            conn.source_cell.points = min(conn.source_cell.points + source_points, config.MAX_CELL_POINTS)
                            conn.target_cell.points = min(conn.target_cell.points + target_points, config.MAX_CELL_POINTS)
                    
                    conn.source_cell.strength = (conn.source_cell.points // config.POINTS_PER_STRENGTH) + 1
                    conn.target_cell.strength = (conn.target_cell.points // config.POINTS_PER_STRENGTH) + 1
                    conn.source_cell.update()
                    conn.target_cell.update()
                    
                    # Wyślij informację o usunięciu mostu przez sieć
                    if hasattr(self, "network_send_callback") and self.network_send_callback:
                        msg = f"remove_bridge;{conn.source_cell.x};{conn.source_cell.y};{conn.target_cell.x};{conn.target_cell.y}"
                        self.network_send_callback(msg)
                        if self.logger:
                            self.logger.log(f"GameScene: Wysłano informację o usunięciu mostu: {msg}")
                    
                    # W trybie turowym przełączamy turę po usunięciu mostu
                    if self.turn_based_mode:
                        self.switch_turn()
                    
                    # Aktulizuj aktualnie wskazywany most, bo usunęliśmy właśnie ten
                    self.hover_connection = None
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # Prawidłowe mapowanie przycisków w trybie sieciowym
        if hasattr(self, 'is_multiplayer') and self.is_multiplayer:
            if self.multiplayer_role == "player":
                actual_button = Qt.LeftButton
            else:  # gdy multiplayer_role == "enemy"
                actual_button = Qt.RightButton
        else:
            actual_button = event.button()

        # Jeśli tryb turowy multiplayer – wykonywanie ruchu tylko, gdy tura zgadza się z lokalną rolą
        if hasattr(self, 'is_multiplayer') and self.is_multiplayer:
            if self.turn_based_mode and self.current_turn != self.multiplayer_role:
                if self.logger:
                    self.logger.log(f"GameScene: Zwolniono przycisk, ale teraz tura {self.current_turn}, ignorowanie.")
                self.drag_start_cell = None
                self.drag_current_pos = None
                self.update()
                return

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
        
        # Sprawdzenie czy w trybie turowym odpowiedni gracz wykonuje ruch
        if self.turn_based_mode:
            if (actual_button == Qt.LeftButton and self.current_turn != "player") or \
               (actual_button == Qt.RightButton and self.current_turn != "enemy"):
                self.drag_start_cell = None
                self.drag_current_pos = None
                self.update()
                return
            
        if actual_button == Qt.LeftButton:
            if isinstance(release_item, CellUnit) and release_item != self.drag_start_cell:
                dx = release_item.x - self.drag_start_cell.x
                dy = release_item.y - self.drag_start_cell.y
                distance = math.hypot(dx, dy)
                cost = int(distance / 20)
                if self.drag_start_cell.points >= cost:
                    exists = any(((conn.source_cell == self.drag_start_cell and conn.target_cell == release_item) or
                                  (conn.source_cell == release_item and conn.target_cell == self.drag_start_cell))
                                  and conn.connection_type == "player" for conn in self.connections)
                    if not exists:
                        self.drag_start_cell.points -= cost
                        self.drag_start_cell.strength = (self.drag_start_cell.points // config.POINTS_PER_STRENGTH) + 1
                        self.drag_start_cell.update()
                        new_conn = self.create_connection(self.drag_start_cell, release_item, "player", cost)
                        
                        # Przełączamy turę tylko jeśli most został faktycznie utworzony
                        if self.turn_based_mode and new_conn is not None:
                            self.switch_turn()  # natychmiastowe przełączenie tury po wykonanym ruchu
        # Dodanie obsługi prawego przycisku myszy dla komórek przeciwnika
        elif actual_button == Qt.RightButton and not self.single_player:
            if isinstance(release_item, CellUnit) and release_item != self.drag_start_cell:
                dx = release_item.x - self.drag_start_cell.x
                dy = release_item.y - self.drag_start_cell.y
                distance = math.hypot(dx, dy)
                cost = int(distance / 20)
                if self.drag_start_cell.points >= cost:
                    exists = any(((conn.source_cell == self.drag_start_cell and conn.target_cell == release_item) or
                                  (conn.source_cell == release_item and conn.target_cell == self.drag_start_cell))
                                  and conn.connection_type == "enemy" for conn in self.connections)
                    if not exists:
                        self.drag_start_cell.points -= cost
                        self.drag_start_cell.strength = (self.drag_start_cell.points // config.POINTS_PER_STRENGTH) + 1
                        self.drag_start_cell.update()
                        new_conn = self.create_connection(self.drag_start_cell, release_item, "enemy", cost)
                        
                        # Przełączamy turę tylko jeśli most został faktycznie utworzony
                        if self.turn_based_mode and new_conn is not None:
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
        points_status = "; ".join(
            f"({cell.cell_type} @ {int(cell.x)},{int(cell.y)}: {cell.points} pts)" for cell in self.cells
        )
        self.move_history.append({
            "timestamp": time.time(),
            "description": f"Status przed ostatnim ruchem: {points_status}"
        })
        self.move_history.append({
            "timestamp": time.time(),
            "description": f"Wynik: {final_result}"
        })
        final_status = "; ".join(
            f"({cell.cell_type} @ {int(cell.x)},{int(cell.y)}: {cell.points} pts)"
            for cell in self.cells
        )
        self.move_history.append({
            "timestamp": time.time(),
            "description": f"Status po ogłoszeniu wyniku: {final_status}"
        })
        
        # Dodajemy synchronizację końcowego stanu gry w trybie multiplayer
        if hasattr(self, 'is_multiplayer') and self.is_multiplayer and hasattr(self, "network_send_callback"):
            # Wysyłamy specjalną wiadomość informującą o końcu gry i zwycięzcy
            winner = "player" if victory and self.multiplayer_role == "player" else "enemy"
            self.network_send_callback(f"game_over;{winner}")
            
            # Wysyłamy ostateczny stan gry
            self.send_game_state_snapshot()
            
            if self.logger:
                self.logger.log(f"GameScene: Wysłano informację o zakończeniu gry, zwycięzca: {winner}")
        
        self.save_game_history()
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
                    conn.source_cell.strength = (conn.source_cell.points // config.POINTS_PER_STRENGTH) + 1
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
        # Rysowanie informacji o turze w górnej części ekranu zawsze, gdy tryb turowy jest aktywny
        if self.turn_based_mode:
            if hasattr(self, 'is_multiplayer') and self.is_multiplayer:
                if self.current_turn == self.multiplayer_role:
                    info_text = f"Twoja tura - Pozostało: {self.round_time_remaining}s"
                else:
                    info_text = f"Tura przeciwnika - Pozostało: {self.round_time_remaining}s"
            else:
                text_turn = self.current_turn.upper()  # Usunięto sprawdzanie czy self.current_turn is None
                info_text = f"Runda: {text_turn} - Pozostało: {self.round_time_remaining}s"
            font = QFont(config.FONT_FAMILY, config.GAME_TURN_FONT_SIZE, QFont.Bold)
            painter.setFont(font)
            painter.setPen(QPen(Qt.white))
            turn_rect = QRectF(rect.left(), rect.top(), rect.width(), 50)
            painter.drawText(turn_rect, Qt.AlignCenter, info_text)
            
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
            
            # Podświetlenie mostu pod kursorem
            if conn == self.hover_connection:
                # Rysuj grubszą, jaśniejszą linię dla podświetlonego mostu
                if conn.connection_type == "player":
                    painter.setPen(QPen(config.COLOR_CONN_PLAYER.lighter(150), 5))
                else:
                    painter.setPen(QPen(config.COLOR_CONN_ENEMY.lighter(150), 5))
                painter.drawLine(source, target)
            
            # Normalne rysowanie mostu
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
            font = QFont(config.FONT_FAMILY, config.GAME_OVER_FONT_SIZE, QFont.Bold)
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

        if (best_move):
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

    def stop_all_timers(self):
        """Zatrzymuje wszystkie timery aktywne w grze"""
        if self.timer:
            self.timer.stop()
            
        if self.points_timer:
            self.points_timer.stop()
        
        if hasattr(self, 'turn_timer') and self.turn_timer:
            self.turn_timer.stop()
            try:
                self.turn_timer.timeout.disconnect()
            except (TypeError, RuntimeError):
                pass  # Ignoruj błąd jeśli nie ma podłączonych sygnałów
                
        if self.enemy_timer:
            self.enemy_timer.stop()
            try:
                self.enemy_timer.timeout.disconnect()
            except (TypeError, RuntimeError):
                pass
                
        if self.hint_timer:
            self.hint_timer.stop()
            try:
                self.hint_timer.timeout.disconnect()
            except (TypeError, RuntimeError):
                pass
                
        if self.logger:
            self.logger.log("GameScene: Wszystkie timery zatrzymane.")

        # Zachowujemy tekst z rolą - dodajemy sprawdzenie czy istnieje w scenie
        if hasattr(self, 'role_info') and self.role_info and self.role_info.scene() == self:
            # Upewniamy się, że tekst z rolą jest na wierzchu
            self.role_info.setZValue(1000)  # Wysoki Z-index zapewnia wyświetlanie na wierzchu
            
    def keyPressEvent(self, event):
        if event.key() == config.KEY_ESCAPE:
            if self.logger:
                self.logger.log("GameScene: Gracz przerwał rozgrywkę.")
            self.stop_all_timers()  # Użyj nowej metody zamiast zatrzymywać tylko wybrane timery

            if self.views() and self.views()[0].parent():
                self.views()[0].parent().show_menu()
            event.accept()
            return
        if event.key() == config.KEY_HINT:
            self.show_hint()
            event.accept()
            return
        if event.key() == config.KEY_QUICKSAVE:
            self.quicksave()
            event.accept()
            return
        if event.key() == config.KEY_QUICKLOAD:
            self.quickload()
            event.accept()
            return

        if event.key() == config.KEY_INFO:
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
        """Restartuje timer dla trybu turowego"""
        try:
            # W trybie multiplayer pierwsza tura zależy od roli gracza
            if hasattr(self, 'is_multiplayer') and self.is_multiplayer:
                # Definiujemy wspólną zasadę - zawsze zaczyna gracz "player"
                self.current_turn = "player"
                
                # Zapewniamy że tylko jedna osoba ma rolę "player" a druga "enemy"
                if hasattr(self, 'is_connection_initiator'):
                    if self.is_connection_initiator:
                        # Inicjator jest zawsze "player"
                        self.multiplayer_role = "player"
                        if self.logger:
                            self.logger.log(f"GameScene: [Multiplayer] Jesteś inicjatorem - grasz jako 'player' - zaczynasz turę")
                    else:
                        # Odbiorca jest zawsze "enemy"
                        self.multiplayer_role = "enemy"
                        if self.logger:
                            self.logger.log(f"GameScene: [Multiplayer] Jesteś odbiorcą - grasz jako 'enemy' - czekasz na swoją turę")
                
                if self.logger:
                    self.logger.log(f"GameScene: [Multiplayer] Inicjalizacja tury jako {self.current_turn} dla roli {self.multiplayer_role}")
            else:
                # W trybie lokalnym zawsze zaczynamy od gracza
                self.current_turn = "player"
            
            self.round_time_remaining = self.turn_duration
            
            # Całkowicie zatrzymujemy i rozłączamy timer przed ponownym użyciem
            if self.turn_timer:
                self.turn_timer.stop()
                try:
                    self.turn_timer.timeout.disconnect()
                except (TypeError, RuntimeError):
                    # Ignorujemy błąd jeśli nie ma podłączonych sygnałów
                    if self.logger:
                        self.logger.log("GameScene: Brak podłączonych sygnałów do rozłączenia")
                    pass
            
            # Podłączamy funkcję i uruchamiamy timer z odpowiednim interwałem
            self.turn_timer.timeout.connect(self.update_turn_timer)
            self.turn_timer.start(1000)  # Aktualizacja co 1 sekundę
            
            if self.logger:
                self.logger.log(f"GameScene: Start timera tury, bieżąca tura: {self.current_turn}, czas: {self.round_time_remaining}s.")
            
            self.update()
            
        except Exception as e:
            if self.logger:
                self.logger.log(f"GameScene: Błąd podczas uruchamiania timera tury: {str(e)}")
                
            # Awaryjne uruchomienie timera
            try:
                if hasattr(self, 'turn_timer') and self.turn_timer:
                    self.turn_timer.stop()
                    self.turn_timer.timeout.connect(self.update_turn_timer)
                    self.turn_timer.start(1000)
                    if self.logger:
                        self.logger.log("GameScene: Awaryjne uruchomienie timera tury")
            except Exception as e2:
                if self.logger:
                    self.logger.log(f"GameScene: Krytyczny błąd timera: {str(e2)}")

    def update_turn_timer(self):
        # Odliczanie czasu tury
        if self.round_time_remaining > 0:
            self.round_time_remaining -= 1
            
            # W trybie sieciowym wysyłamy aktualizacje czasu gdy jest nasza tura
            if hasattr(self, 'is_multiplayer') and self.is_multiplayer and self.turn_based_mode:
                if self.current_turn == self.multiplayer_role and hasattr(self, "network_send_callback"):
                    # Zwiększamy częstotliwość aktualizacji czasu dla lepszej synchronizacji
                    # Wysyłamy aktualizację czasu co sekundę, zamiast co dwie sekundy
                    self.network_send_callback(f"update_turn_time;{self.round_time_remaining}")
                        
                    # Wysyłamy pełny snapshot częściej - co 3 sekundy zamiast co 5
                    if self.round_time_remaining % 3 == 0:
                        self.send_game_state_snapshot()
            
        # KLUCZOWA ZMIANA - osobno obsługujemy przypadek gdy czas się skończył
        if self.round_time_remaining <= 0:
            if self.logger:
                self.logger.log(f"GameScene: Koniec czasu tury dla {self.current_turn}")
            
            # Zabezpieczenie przed utknięciem - wymuszamy wartość minimalną 0
            self.round_time_remaining = 0
            
            # Przełączamy turę tylko jeśli to nasza tura (ważne dla multiplayer)
            if hasattr(self, 'is_multiplayer') and self.is_multiplayer:
                if self.current_turn == self.multiplayer_role:
                    if self.logger:
                        self.logger.log("GameScene: Przełączanie tury po końcu czasu (multiplayer)")
                    self.switch_turn()  # jeśli to nasza tura, przełączamy
            else:
                # W trybie lokalnym zawsze przełączamy
                self.switch_turn()
        
        self.update()

    def switch_turn(self):
        # Zatrzymujemy i rozłączamy timer przed ponownym użyciem
        self.turn_timer.stop()
        
        try:
            self.turn_timer.timeout.disconnect()
        except TypeError:
            # Ignorujemy błąd jeśli nie ma podłączonych sygnałów
            pass
        
        # W trybie multiplayer:
        if hasattr(self, 'is_multiplayer') and self.is_multiplayer and self.turn_based_mode:
            if self.current_turn == self.multiplayer_role:
                # Zmiana tury na przeciwnika - przestajemy być aktywni
                opposite_role = "player" if self.multiplayer_role == "enemy" else "enemy"
                self.current_turn = opposite_role
                
                if self.logger:
                    self.logger.log(f"GameScene: [Multiplayer] Zmiana tury z {self.multiplayer_role} na {opposite_role}")
                    
                # Reset czasu tury do pełnej wartości
                self.round_time_remaining = self.turn_duration
                
                # Wysyłamy komunikat do przeciwnika o przełączeniu tury
                if hasattr(self, "network_send_callback") and self.network_send_callback:
                    # Wysyłamy komunikat o przełączeniu tury
                    self.network_send_callback("switch_turn")
                    
                    # Wysyłamy pełny snapshot stanu gry
                    self.send_game_state_snapshot()
                    
                    if self.logger:
                        self.logger.log("GameScene: Wysłano żądanie przełączenia tury i synchronizację stanu")
            else:
                if self.logger:
                    self.logger.log(f"GameScene: Próbowano przełączyć turę gdy nie jest aktywna - ignoruję")
        else:
            # Standardowa zmiana tury dla trybu lokalnego
            if self.current_turn == "player":
                self.current_turn = "enemy"
                # W trybie jednego gracza uruchamiamy timer AI gdy tura przeciwnika
                if self.single_player and self.enemy_timer:
                    self.enemy_timer.start(3000)
            else:
                self.current_turn = "player"
                # W trybie jednego gracza zatrzymujemy timer AI gdy tura gracza
                if self.single_player and self.enemy_timer:
                    self.enemy_timer.stop()
                    
            # Reset czasu tury
            self.round_time_remaining = self.turn_duration
            
            if self.logger:
                self.logger.log(f"GameScene: Zmiana tury, teraz: {self.current_turn}, czas: {self.round_time_remaining}s.")
        
        # Ponowne uruchomienie timera po zmianie tury
        self.turn_timer.timeout.connect(self.update_turn_timer)
        self.turn_timer.start(1000)
        
        self.update()

    def start_enemy_timer(self):
        """Uruchomienie timera do wykonywania ruchów AI dla przeciwnika"""
        if self.enemy_timer:
            self.enemy_timer.stop()
        self.enemy_timer = QTimer()
        self.enemy_timer.timeout.connect(self.enemy_move)
        
        # W trybie turowym uruchamiamy timer tylko gdy tura jest przeciwnika
        if not self.turn_based_mode or (self.turn_based_mode and self.current_turn == "enemy"):
            self.enemy_timer.start(3000)

    def enemy_move(self):
        """Metoda wykonująca ruch przeciwnika przy użyciu AI"""
        if not self.single_player:
            return
            
        # W trybie turowym sprawdzamy, czy aktualna tura jest przeciwnika
        if self.turn_based_mode and self.current_turn != "enemy":
            return
            
        best_move = self.game_ai.analyze_best_move(cell_type="enemy")
        if best_move:
            source, target, cost = best_move
            if source.points >= cost:
                source.points -= cost
                source.strength = (source.points // config.POINTS_PER_STRENGTH) + 1
                new_conn = self.create_connection(source, target, "enemy", cost)
                
                # Jeśli jesteśmy w trybie turowym, przełączamy turę po wykonaniu ruchu
                if self.turn_based_mode and new_conn is not None:
                    if self.enemy_timer:
                        self.enemy_timer.stop()  # Zatrzymujemy timer przeciwnika żeby nie wykonał więcej ruchów
                    self.switch_turn()  # Przełączamy turę na gracza
                    
        self.update()

    def quicksave(self):
        saves_dir = "saves"
        if not os.path.exists(saves_dir):
            os.makedirs(saves_dir)
        xml_filename = os.path.join(saves_dir, f"quicksave_level{self.current_level}.xml")
        game_history.save_game_history(self, xml_filename)
        json_filename = os.path.join(saves_dir, f"quicksave_level{self.current_level}.json")
        game_history.save_game_history_json(self, json_filename)
        mongodb_id = game_history.save_game_history_mongodb(self, is_quicksave=True)
        if self.logger:
            self.logger.log(f"Quicksave wykonany: XML: {xml_filename}, JSON: {json_filename}, MongoDB id: {mongodb_id}")

    def quickload(self):
        level = self.current_level
        dialog = QDialog()
        dialog.setWindowTitle("Wczytaj quicksave")
        v_layout = QVBoxLayout(dialog)
        label = QLabel("Wybierz quicksave (tylko zapisy z flagą quicksave):")
        v_layout.addWidget(label)
        h_layout = QHBoxLayout()
        btn_xml = QPushButton("XML")
        btn_json = QPushButton("JSON")
        btn_nosql = QPushButton("NoSQL")
        h_layout.addWidget(btn_xml)
        h_layout.addWidget(btn_json)
        h_layout.addWidget(btn_nosql)
        v_layout.addLayout(h_layout)
        choice = [None]
        def select_xml():
            choice[0] = "XML"
            dialog.accept()
        def select_json():
            choice[0] = "JSON"
            dialog.accept()
        def select_nosql():
            choice[0] = "NoSQL"
            dialog.accept()
        btn_xml.clicked.connect(select_xml)
        btn_json.clicked.connect(select_json)
        btn_nosql.clicked.connect(select_nosql)
        if not dialog.exec_():
            return
        selected = choice[0]
        if not selected:
            return
        if selected == "XML":
            filename = os.path.join("saves", f"quicksave_level{level}.xml")
            state = game_history.load_game_history(filename)
            if not state or "final_state" not in state or "cells" not in state["final_state"]:
                if self.logger:
                    self.logger.log("Quicksave XML nie znaleziony lub uszkodzony.")
                QMessageBox.warning(None, "Błąd", "Quicksave XML nie znaleziony lub uszkodzony.")
                if self.views() and self.views()[0].parent():
                    self.views()[0].parent().show_menu()
                return False
        elif selected == "JSON":
            filename = os.path.join("saves", f"quicksave_level{level}.json")
            state = game_history.load_game_history_json(filename)
            if not state or "final_state" not in state or "cells" not in state["final_state"]:
                if self.logger:
                    self.logger.log("Quicksave JSON nie znaleziony lub uszkodzony.")
                QMessageBox.warning(None, "Błąd", "Quicksave JSON nie znaleziony lub uszkodzony.")
                if self.views() and self.views()[0].parent():
                    self.views()[0].parent().show_menu()
                return False
        elif selected == "NoSQL":
            level = self.current_level
            dialog = QDialog()
            dialog.setWindowTitle("Wybierz quicksave z MongoDB")
            layout = QVBoxLayout(dialog)
            lbl = QLabel("Wybierz quicksave (MongoDB):")
            layout.addWidget(lbl)
            list_widget = QListWidget()
            layout.addWidget(list_widget)
            items = []
            def update_list():
                list_widget.clear()
                items.clear()
                documents = list(game_history.replays_collection.find({"level": level, "is_quicksave": True}))
                documents = sorted(documents, key=lambda doc: doc.get("moves", [{}])[0].get("timestamp", 0), reverse=True)
                for doc in documents:
                    ts = doc.get("moves", [{}])[0].get("timestamp", 0)
                    try:
                        time_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        time_str = "Brak daty"
                    id_short = str(doc["_id"])[:8]
                    display_text = f"{time_str} - {id_short}"
                    list_widget.addItem(display_text)
                    items.append(doc)
            update_list()
            buttons_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Anuluj")
            buttons_layout.addWidget(ok_button)
            buttons_layout.addWidget(cancel_button)
            layout.addLayout(buttons_layout)
            selected_file = [None]
            def on_ok():
                idx = list_widget.currentRow()
                if idx >= 0:
                    selected_file[0] = items[idx]
                    dialog.accept()
            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(dialog.reject)
            if dialog.exec_() == QDialog.Accepted:
                state = selected_file[0]
                if state and "_id" in state:
                    state["_id"] = str(state["_id"])
            else:
                return
        self.clear()
        self.cells = []
        for cell_data in state["final_state"]["cells"]:
            cell = CellUnit(cell_data["x"], cell_data["y"], cell_data["type"], cell_data["points"])
            self.cells.append(cell)
            self.addItem(cell)
        if self.logger:
            self.logger.log(f"Quicksave wczytany z {selected}.")
        self.timer.start(16)
        self.points_timer.start(2000)
        return True

    def create_game_state_snapshot(self):
        """
        Tworzy snapshot aktualnego stanu gry, który może być przesłany
        w formacie podobnym do tego używanego w zapisie powtórek.
        """
        snapshot = {
            "cells": [
                {
                    "index": i,
                    "x": cell.x,
                    "y": cell.y,
                    "type": cell.cell_type,
                    "points": cell.points,
                    "frozen": cell.frozen
                } for i, cell in enumerate(self.cells)
            ],
            "connections": [
                {
                    "source_index": self.cells.index(conn.source_cell),
                    "target_index": self.cells.index(conn.target_cell),
                    "type": conn.connection_type,
                    "cost": getattr(conn, "cost", 0),
                    "dots": conn.dots  # Dodajemy informacje o kropkach na moście
                } for conn in self.connections
            ],
            "current_turn": self.current_turn,
            "round_time_remaining": self.round_time_remaining
        }
        return snapshot

    def send_game_state_snapshot(self):
        """
        Wysyła pełny snapshot stanu gry do drugiego gracza
        """
        if not hasattr(self, "network_send_callback") or not self.network_send_callback:
            return
        
        try:
            snapshot = self.create_game_state_snapshot()
            # Konwertujemy snapshot do formatu JSON
            import json
            snapshot_json = json.dumps(snapshot)
            
            # Wysyłamy snapshot w częściach, jeśli jest duży
            if len(snapshot_json) > 1000:
                chunks = [snapshot_json[i:i+1000] for i in range(0, len(snapshot_json), 1000)]
                for i, chunk in enumerate(chunks):
                    # Wysyłamy fragmenty z informacją o numeracji
                    self.network_send_callback(f"snapshot_part;{i+1};{len(chunks)};{chunk}")
            else:
                self.network_send_callback(f"snapshot_full;{snapshot_json}")
                
            if self.logger:
                self.logger.log(f"GameScene: Wysłano snapshot stanu gry o rozmiarze {len(snapshot_json)}")
        except Exception as e:
            if self.logger:
                self.logger.log(f"GameScene: Błąd podczas wysyłania snapshotu: {e}")

    def apply_game_state_snapshot(self, snapshot):
        """
        Stosuje otrzymany snapshot stanu gry
        """
        try:
            # Synchronizujemy komórki
            for cell_data in snapshot.get("cells", []):
                idx = cell_data.get("index", -1)
                if 0 <= idx < len(self.cells):
                    cell = self.cells[idx]
                    cell.cell_type = cell_data.get("type", cell.cell_type)
                    cell.points = cell_data.get("points", cell.points)
                    cell.frozen = cell_data.get("frozen", False)
                    cell.strength = (cell.points // config.POINTS_PER_STRENGTH) + 1
                    cell.update()
            
            # Synchronizujemy połączenia - usuwamy te, których nie ma w snapshocie
            connection_pairs = []
            for conn_data in snapshot.get("connections", []):
                source_idx = conn_data.get("source_index", -1)
                target_idx = conn_data.get("target_index", -1)
                if 0 <= source_idx < len(self.cells) and 0 <= target_idx < len(self.cells):
                    connection_pairs.append((source_idx, target_idx))
            
            # Usuwamy nieaktualne połączenia
            for conn in list(self.connections):
                source_idx = self.cells.index(conn.source_cell)
                target_idx = self.cells.index(conn.target_cell)
                
                if (source_idx, target_idx) not in connection_pairs and (target_idx, source_idx) not in connection_pairs:
                    if conn in conn.source_cell.connections:
                        conn.source_cell.connections.remove(conn)
                    if conn in conn.target_cell.connections:
                        conn.target_cell.connections.remove(conn)
                    self.connections.remove(conn)
            
            # Dodajemy nowe połączenia
            for conn_data in snapshot.get("connections", []):
                source_idx = conn_data.get("source_index", -1)
                target_idx = conn_data.get("target_index", -1)
                conn_type = conn_data.get("type", "neutral")
                cost = conn_data.get("cost", 0)
                dots = conn_data.get("dots", [])
                
                if 0 <= source_idx < len(self.cells) and 0 <= target_idx < len(self.cells):
                    source = self.cells[source_idx]
                    target = self.cells[target_idx]
                    
                    # Sprawdzamy czy połączenie już istnieje
                    existing_conn = None
                    for conn in self.connections:
                        if ((conn.source_cell == source and conn.target_cell == target) or 
                            (conn.source_cell == target and conn.target_cell == source)) and conn.connection_type == conn_type:
                            existing_conn = conn
                            break
                    
                    # Jeśli istnieje, aktualizujemy stan kropek
                    if existing_conn:
                        existing_conn.dots = dots
                    # Jeśli nie istnieje, tworzymy nowe
                    else:
                        source._skip_network = True  # Oznaczamy, by uniknąć wysłania wiadomości
                        try:
                            connection = self.create_connection(source, target, conn_type)
                            connection.cost = cost
                            connection.dots = dots  # Ustawiamy kropki na moście
                        finally:
                            delattr(source, '_skip_network')
            
            # Aktualizujemy stan tury i czas
            if "current_turn" in snapshot:
                self.current_turn = snapshot.get("current_turn")
            if "round_time_remaining" in snapshot:
                self.round_time_remaining = snapshot.get("round_time_remaining")
                
            if self.logger:
                self.logger.log("GameScene: Zastosowano snapshot stanu gry")
                
            # Wymuszamy aktualizację UI
            self.update()
        except Exception as e:
            if self.logger:
                self.logger.log(f"GameScene: Błąd podczas stosowania snapshotu: {e}")

    def save_game_history(self):
        """Zapisuje historię gry do plików i MongoDB"""
        # Ta metoda wykonuje zapis historii, który jest duplikowany w metodzie game_over
        # i w obsłudze wiadomości game_over
        if self.move_history and "timestamp" in self.move_history[0]:
            timestamp = datetime.datetime.fromtimestamp(self.move_history[0]["timestamp"]).strftime("%Y%m%d_%H%M%S")
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        replays_dir = "replays"
        if not os.path.exists(replays_dir):
            os.makedirs(replays_dir)
            
        xml_filename = os.path.join(replays_dir, f"replay_level{self.current_level}_{timestamp}.xml")
        json_filename = os.path.join(replays_dir, f"replay_level{self.current_level}_{timestamp}.json")
        
        game_history.save_game_history(self, xml_filename)
        game_history.save_game_history_json(self, json_filename)
        mongodb_id = game_history.save_game_history_mongodb(self)
        
        if self.logger:
            self.logger.log(f"Replay zapisany do MongoDB z id: {mongodb_id}")