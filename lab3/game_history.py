import os
import xml.etree.ElementTree as ET

def save_game_history(game_scene, filename):
    """
    Zapisuje historię rozgrywki do pliku XML.
    W zapisie znajduje się początkowy stan (lista komórek i powiązań)
    oraz lista ruchów zapisanych w atrybucie move_history (jeśli istnieje).
    """
    root = ET.Element("GameHistory")

    # Zapis stanu początkowego
    initial_state = ET.SubElement(root, "InitialState")
    cells_el = ET.SubElement(initial_state, "Cells")
    for cell in game_scene.cells:
        cell_el = ET.SubElement(cells_el, "Cell")
        cell_el.set("x", str(cell.x))
        cell_el.set("y", str(cell.y))
        cell_el.set("type", str(cell.cell_type))
        cell_el.set("points", str(cell.points))
    connections_el = ET.SubElement(initial_state, "Connections")
    for conn in game_scene.connections:
        conn_el = ET.SubElement(connections_el, "Connection")
        # Zakładamy, że scena zachowuje listę komórek jako game_scene.cells;
        # zapamiętujemy indeksy komórek tworzących połączenie.
        try:
            src_index = game_scene.cells.index(conn.source_cell)
            tgt_index = game_scene.cells.index(conn.target_cell)
        except ValueError:
            src_index = -1
            tgt_index = -1
        conn_el.set("source_index", str(src_index))
        conn_el.set("target_index", str(tgt_index))
        conn_el.set("type", str(conn.connection_type))
        conn_el.set("cost", str(getattr(conn, "cost", 0)))

    # Zapis ruchów
    moves_el = ET.SubElement(root, "Moves")
    if hasattr(game_scene, "move_history"):
        for move in game_scene.move_history:
            move_el = ET.SubElement(moves_el, "Move")
            move_el.set("timestamp", str(move.get("timestamp", 0)))
            move_el.text = move.get("description", "")
    # Zapis do pliku z czytelnym formatowaniem
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")  # dodanie wcięć dla czytelności XML-a
    tree.write(filename, encoding="utf-8", xml_declaration=True)

def load_game_history(filename):
    """
    Odczytuje historię rozgrywki zapisaną w formacie XML
    i zwraca słownik z kluczami:
      - "initial_state": zawiera listy komórek (każda jako słownik) 
                         i połączeń (jako słownik z indeksami i danymi)
      - "moves": lista ruchów, każdy jako słownik (timestamp, description)
    """
    # Dodane zabezpieczenie przed brakiem pliku
    if not os.path.exists(filename):
        return {"initial_state": {"cells": [], "connections": []}, "moves": []}
    tree = ET.parse(filename)
    root = tree.getroot()

    history = {"initial_state": {}, "moves": []}

    init_state = root.find("InitialState")
    if init_state is not None:
        cells_el = init_state.find("Cells")
        cells = []
        if cells_el is not None:
            for cell_el in cells_el.findall("Cell"):
                cell = {
                    "x": float(cell_el.get("x", 0)),
                    "y": float(cell_el.get("y", 0)),
                    "type": cell_el.get("type", "neutral"),
                    "points": int(cell_el.get("points", 0))
                }
                cells.append(cell)
        connections = []
        conns_el = init_state.find("Connections")
        if conns_el is not None:
            for conn_el in conns_el.findall("Connection"):
                conn = {
                    "source_index": int(conn_el.get("source_index", -1)),
                    "target_index": int(conn_el.get("target_index", -1)),
                    "type": conn_el.get("type", "neutral"),
                    "cost": int(conn_el.get("cost", 0))
                }
                connections.append(conn)
        history["initial_state"]["cells"] = cells
        history["initial_state"]["connections"] = connections

    moves_el = root.find("Moves")
    if moves_el is not None:
        for move_el in moves_el.findall("Move"):
            move = {
                "timestamp": float(move_el.get("timestamp", 0)),
                "description": move_el.text or ""
            }
            history["moves"].append(move)

    return history
