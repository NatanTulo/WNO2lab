from game_objects import CellUnit, CellConnection
import math

class GameAI:
    """Klasa implementująca strategiczne podpowiedzi w grze"""
    
    def __init__(self, game_scene):
        self.game_scene = game_scene
    
    def analyze_best_move(self):
        """Analiza obecnego stanu gry i sugestia najlepszego ruchu"""
        # Pobierz komórki gracza
        player_cells = [cell for cell in self.game_scene.cells if cell.cell_type == "player"]
        
        if not player_cells:
            return None  # Brak komórek gracza do wykonania ruchu
        
        best_move = None
        best_score = float('-inf')
        
        # Dla każdej komórki gracza, oceniamy możliwe ruchy
        for source_cell in player_cells:
            # Pomijamy komórki z niewystarczającą liczbą punktów
            if source_cell.points < 2:  # Potrzeba minimum 2 punktów na połączenie
                continue
            
            # Oceniamy połączenia z każdą inną komórką
            for target_cell in self.game_scene.cells:
                if target_cell == source_cell:
                    continue
                    
                # Sprawdzamy czy połączenie już istnieje
                connection_exists = any(
                    (conn.source_cell == source_cell and conn.target_cell == target_cell) or
                    (conn.source_cell == target_cell and conn.target_cell == source_cell)
                    for conn in self.game_scene.connections
                )
                
                if connection_exists:
                    continue
                
                # Obliczamy koszt tego połączenia
                dx = target_cell.x - source_cell.x
                dy = target_cell.y - source_cell.y
                distance = math.hypot(dx, dy)
                cost = int(distance / 20)
                
                # Pomijamy jeśli nie ma wystarczającej liczby punktów
                if source_cell.points < cost:
                    continue
                
                # Oceniamy ten ruch
                score = self._evaluate_move(source_cell, target_cell, cost)
                
                if score > best_score:
                    best_score = score
                    best_move = (source_cell, target_cell, cost)
        
        return best_move
    
    def _evaluate_move(self, source_cell, target_cell, cost):
        """Ocena potencjalnego ruchu między source_cell a target_cell"""
        score = 0
        
        # Preferujemy przejmowanie neutralnych komórek
        if target_cell.cell_type == "neutral":
            score += 50
        
        # Preferujemy przejmowanie komórek wroga jeśli mają mało punktów
        elif target_cell.cell_type == "enemy":
            if target_cell.points < cost:  # Można natychmiast przejąć
                score += 100
            else:
                score += 25
        
        # Preferujemy łączenie z przyjaznymi komórkami jeśli mają mało punktów
        elif target_cell.cell_type == "player":
            if target_cell.points < 5:  # Wspieramy słabe własne komórki
                score += 40
            else:
                score += 10
        
        # Dostosowujemy wynik na podstawie efektywności ruchu
        # Wyższe punkty dla ruchów efektywnie wykorzystujących zasoby
        efficiency = target_cell.points / cost if cost > 0 else 0
        score += efficiency * 20
        
        # Preferujemy ruchy wzmacniające naszą pozycję
        strategic_value = self._calculate_strategic_value(source_cell, target_cell)
        score += strategic_value
        
        return score
    
    def _calculate_strategic_value(self, source_cell, target_cell):
        """Obliczanie wartości strategicznej połączenia między komórkami"""
        # Liczymy pobliskie komórki każdego typu
        nearby_friendly = 0
        nearby_enemy = 0
        nearby_neutral = 0
        
        # Definiujemy "pobliskie" jako w zasięgu 200 jednostek
        nearby_threshold = 200
        
        for cell in self.game_scene.cells:
            if cell == source_cell or cell == target_cell:
                continue
                
            # Obliczamy odległość do docelowej komórki
            dx = cell.x - target_cell.x
            dy = cell.y - target_cell.y
            distance = math.hypot(dx, dy)
            
            if distance <= nearby_threshold:
                if cell.cell_type == "player":
                    nearby_friendly += 1
                elif cell.cell_type == "enemy":
                    nearby_enemy += 1
                else:  # neutral
                    nearby_neutral += 1
        
        # Oceniamy pozycję strategiczną
        strategic_value = 0
        
        # Dobrze mieć przyjazne wsparcie w pobliżu
        strategic_value += nearby_friendly * 10
        
        # Przejmowanie komórek na terytorium wroga jest ryzykowne, ale wartościowe
        if target_cell.cell_type == "enemy" or target_cell.cell_type == "neutral":
            if nearby_enemy > nearby_friendly:
                # Wysokie ryzyko, wysoka nagroda
                strategic_value += (nearby_enemy - nearby_friendly) * 15
        
        # Preferujemy ekspansję w kierunku neutralnych komórek
        strategic_value += nearby_neutral * 5
        
        return strategic_value
