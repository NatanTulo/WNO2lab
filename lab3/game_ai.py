import math
import random
import time
from collections import defaultdict

from game_objects import CellUnit, CellConnection

class GameAI:
    """Zaawansowane AI do strategicznych podpowiedzi w grze, działające lokalnie"""

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.simulation_time = 0.5
        self.exploration_weight = 1.41

    def analyze_best_move(self):
        """Analiza obecnego stanu gry i sugestia najlepszego ruchu używając MCTS"""
        player_cells = [cell for cell in self.game_scene.cells if cell.cell_type == "player"]

        if not player_cells:
            return None

        mcts = MCTS(self.game_scene, self.exploration_weight)

        possible_moves = self._get_possible_moves(player_cells)

        if not possible_moves:
            return None

        best_move = mcts.search(possible_moves, self.simulation_time)

        return best_move

    def _get_possible_moves(self, player_cells):
        """Generuje listę wszystkich możliwych ruchów dla komórek gracza"""
        possible_moves = []

        for source_cell in player_cells:
            if source_cell.points < 2:
                continue

            for target_cell in self.game_scene.cells:
                if target_cell == source_cell:
                    continue

                connection_exists = any(
                    (conn.source_cell == source_cell and conn.target_cell == target_cell) or
                    (conn.source_cell == target_cell and conn.target_cell == source_cell)
                    for conn in self.game_scene.connections
                )

                if connection_exists:
                    continue

                dx = target_cell.x - source_cell.x
                dy = target_cell.y - source_cell.y
                distance = math.hypot(dx, dy)
                cost = int(distance / 20)

                if source_cell.points < cost:
                    continue

                possible_moves.append((source_cell, target_cell, cost))

        return possible_moves


class MCTS:
    """Implementacja algorytmu Monte Carlo Tree Search (MCTS)"""

    def __init__(self, game_scene, exploration_weight=1.41):
        self.game_scene = game_scene
        self.exploration_weight = exploration_weight
        self.Q = defaultdict(int)
        self.N = defaultdict(int)
        self.children = {}

    def search(self, possible_moves, time_limit):
        """Wyszukiwanie najlepszego ruchu z użyciem MCTS z limitem czasowym"""
        start_time = time.time()

        if not possible_moves:
            return None

        game_state = GameState(self.game_scene)

        num_rollouts = 0
        while time.time() - start_time < time_limit:
            path, leaf_state, move = self._select_and_expand(game_state, possible_moves)

            reward = self._simulate(leaf_state)

            self._backpropagate(path, reward)

            num_rollouts += 1

            if num_rollouts >= 100:
                break

        best_move = None
        best_value = float('-inf')

        for move in possible_moves:
            move_hash = self._move_hash(game_state, move)
            if move_hash in self.N:
                value = self.Q[move_hash] / self.N[move_hash]
                if value > best_value:
                    best_value = value
                    best_move = move

        if best_move is None and possible_moves:
            return random.choice(possible_moves)

        return best_move

    def _select_and_expand(self, state, possible_moves):
        """Wybiera ścieżkę poprzez drzewo i dodaje nowy liść"""
        path = []

        current_state = state

        while True:
            path.append(current_state)

            if current_state not in self.children:
                self.children[current_state] = []
                for move in possible_moves:
                    source_cell, target_cell, cost = move
                    if current_state.is_valid_move(source_cell, target_cell, cost):
                        new_state = current_state.apply_move(source_cell, target_cell, cost)
                        self.children[current_state].append((new_state, move))

                if not self.children[current_state]:
                    return path, current_state, None

                child_state, move = random.choice(self.children[current_state])
                path.append(child_state)
                return path, child_state, move

            unexplored = []
            for child_state, move in self.children[current_state]:
                move_hash = self._move_hash(current_state, move)
                if move_hash not in self.N:
                    unexplored.append((child_state, move))

            if unexplored:
                child_state, move = random.choice(unexplored)
                path.append(child_state)
                return path, child_state, move

            best_score = float('-inf')
            best_child = None
            best_move = None

            log_N_vertex = math.log(self.N[current_state])

            for child_state, move in self.children[current_state]:
                move_hash = self._move_hash(current_state, move)

                exploit = self.Q[move_hash] / self.N[move_hash]
                explore = self.exploration_weight * math.sqrt(log_N_vertex / self.N[move_hash])
                score = exploit + explore

                if score > best_score:
                    best_score = score
                    best_child = child_state
                    best_move = move

            current_state = best_child

    def _simulate(self, state):
        """Przeprowadza losową symulację z danego stanu i zwraca wynik"""
        for _ in range(20):
            game_outcome = state.check_game_outcome()
            if game_outcome is not None:
                return game_outcome

            possible_moves = state.get_possible_moves()

            if not possible_moves:
                break

            source_cell, target_cell, cost = random.choice(possible_moves)

            state = state.apply_move(source_cell, target_cell, cost)

        player_cells = sum(1 for cell in state.cells if cell.cell_type == "player")
        enemy_cells = sum(1 for cell in state.cells if cell.cell_type == "enemy")

        if player_cells == 0:
            return 0
        elif enemy_cells == 0:
            return 1
        else:
            total_cells = player_cells + enemy_cells
            return player_cells / total_cells

    def _backpropagate(self, path, reward):
        """Aktualizuje statystyki dla wszystkich stanów w ścieżce"""
        for state in reversed(path):
            self.N[state] += 1
            self.Q[state] += reward

    def _move_hash(self, state, move):
        """Tworzy unikalny hash dla danego ruchu w danym stanie"""
        if not move:
            return None
        source_cell, target_cell, cost = move
        return (hash(state), source_cell.x, source_cell.y, target_cell.x, target_cell.y, cost)


class SimpleCell:
    """Uproszczona reprezentacja komórki dla celów symulacji AI"""
    def __init__(self, x, y, cell_type, points, radius=30, original_cell=None):
        self.x = x
        self.y = y
        self.cell_type = cell_type
        self.points = points
        self.strength = (points // 10) + 1
        self.radius = radius
        self.original_cell = original_cell
        self.connections = []

class SimpleConnection:
    """Uproszczona reprezentacja połączenia dla celów symulacji AI"""
    def __init__(self, source_cell, target_cell, connection_type, cost=0):
        self.source_cell = source_cell
        self.target_cell = target_cell
        self.connection_type = connection_type
        self.cost = cost
        self.dots = []

class GameState:
    """Klasa reprezentująca stan gry dla symulatora MCTS"""

    def __init__(self, game_scene=None):
        if game_scene:
            self.cells = []
            self.cell_map = {}

            for cell in game_scene.cells:
                simple_cell = SimpleCell(
                    cell.x, cell.y, cell.cell_type, cell.points,
                    getattr(cell, 'radius', 30), cell
                )
                self.cells.append(simple_cell)
                self.cell_map[cell] = simple_cell

            self.connections = []
            for conn in game_scene.connections:
                source = self.cell_map.get(conn.source_cell)
                target = self.cell_map.get(conn.target_cell)
                if source and target:
                    simple_conn = SimpleConnection(
                        source, target, conn.connection_type,
                        getattr(conn, 'cost', 0)
                    )
                    self.connections.append(simple_conn)
                    source.connections.append(simple_conn)
                    target.connections.append(simple_conn)
        else:
            self.cells = []
            self.connections = []
            self.cell_map = {}

    def __hash__(self):
        """Unikalny hash stanu gry bazujący na stanie komórek"""
        h = 0
        for cell in self.cells:
            cell_hash = hash((cell.x, cell.y, cell.cell_type, cell.points))
            h = h ^ cell_hash
        return h

    def __eq__(self, other):
        """Porównanie stanów gry"""
        if not isinstance(other, GameState):
            return False

        if len(self.cells) != len(other.cells):
            return False

        for cell1, cell2 in zip(sorted(self.cells, key=lambda c: (c.x, c.y)),
                               sorted(other.cells, key=lambda c: (c.x, c.y))):
            if (cell1.x != cell2.x or cell1.y != cell2.y or
                cell1.cell_type != cell2.cell_type or cell1.points != cell2.points):
                return False

        return True

    def _copy_cells(self):
        """Tworzy płytką kopię listy komórek"""
        copied_cells = []
        cell_map = {}

        for cell in self.cells:
            new_cell = SimpleCell(cell.x, cell.y, cell.cell_type, cell.points, cell.radius)
            copied_cells.append(new_cell)
            cell_map[cell] = new_cell

        return copied_cells, cell_map

    def is_valid_move(self, source_cell, target_cell, cost):
        """Sprawdza czy ruch jest możliwy w tym stanie"""
        source = None
        target = None

        if hasattr(source_cell, 'original_cell') and source_cell.original_cell:
            source = self.cell_map.get(source_cell.original_cell)
        else:
            for cell in self.cells:
                if cell.x == source_cell.x and cell.y == source_cell.y:
                    source = cell
                    break

        if hasattr(target_cell, 'original_cell') and target_cell.original_cell:
            target = self.cell_map.get(target_cell.original_cell)
        else:
            for cell in self.cells:
                if cell.x == target_cell.x and cell.y == target_cell.y:
                    target = cell
                    break

        if not source or not target:
            return False

        if source.points < cost:
            return False

        for conn in self.connections:
            if ((conn.source_cell == source and conn.target_cell == target) or
                (conn.source_cell == target and conn.target_cell == source)):
                return False

        return True

    def apply_move(self, source_cell, target_cell, cost):
        """Tworzy nowy stan po wykonaniu ruchu"""
        new_state = GameState()
        new_cells, new_cell_map = self._copy_cells()
        new_state.cells = new_cells

        source = new_cell_map.get(self._find_cell(source_cell.x, source_cell.y))
        target = new_cell_map.get(self._find_cell(target_cell.x, target_cell.y))

        if not source or not target:
            return new_state

        source.points -= cost
        source.strength = (source.points // 10) + 1

        connection = SimpleConnection(source, target, source.cell_type, cost)
        new_state.connections.append(connection)

        points_to_transfer = min(5, source.points)

        if source.cell_type == target.cell_type:
            target.points += points_to_transfer
        else:
            target.points -= points_to_transfer
            if target.points <= 0:
                target.cell_type = source.cell_type
                target.points = abs(target.points) + 1

        target.strength = (target.points // 10) + 1

        return new_state

    def _find_cell(self, x, y):
        """Znajduje komórkę o podanych współrzędnych"""
        for cell in self.cells:
            if cell.x == x and cell.y == y:
                return cell
        return None

    def check_game_outcome(self):
        """Sprawdza czy gra się zakończyła i zwraca wynik"""
        player_cells = sum(1 for cell in self.cells if cell.cell_type == "player")
        enemy_cells = sum(1 for cell in self.cells if cell.cell_type == "enemy")

        if player_cells == 0:
            return 0
        elif enemy_cells == 0:
            return 1
        else:
            return None

    def get_possible_moves(self):
        """Generuje listę wszystkich możliwych ruchów w tym stanie"""
        possible_moves = []
        player_cells = [cell for cell in self.cells if cell.cell_type == "player"]

        for source_cell in player_cells:
            if source_cell.points < 2:
                continue

            for target_cell in self.cells:
                if target_cell == source_cell:
                    continue

                connection_exists = False
                for conn in self.connections:
                    if ((conn.source_cell == source_cell and conn.target_cell == target_cell) or
                        (conn.source_cell == target_cell and conn.target_cell == source_cell)):
                        connection_exists = True
                        break

                if connection_exists:
                    continue

                dx = target_cell.x - source_cell.x
                dy = target_cell.y - source_cell.y
                distance = math.hypot(dx, dy)
                cost = int(distance / 20)

                if source_cell.points >= cost:
                    possible_moves.append((source_cell, target_cell, cost))

        return possible_moves