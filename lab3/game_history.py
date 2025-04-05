import os
import re
import xml.etree.ElementTree as ET
import json

def save_game_history(game_scene, filename):
    """
    Zapisuje historię rozgrywki do pliku XML.
    W zapisie znajduje się początkowy stan (lista komórek i połączeń),
    lista ruchów oraz stan końcowy.
    """
    root = ET.Element("GameHistory")

    # Zapis stanu początkowego – tylko komórki
    initial_state = ET.SubElement(root, "InitialState")
    cells_el = ET.SubElement(initial_state, "Cells")
    for cell in game_scene.cells:
        cell_el = ET.SubElement(cells_el, "Cell")
        cell_el.set("x", str(cell.x))
        cell_el.set("y", str(cell.y))
        cell_el.set("type", str(getattr(cell, 'initial_type', cell.cell_type)))
        cell_el.set("points", str(cell.points))
    # Usunięto zapis połączeń z początkowego stanu, ponieważ na starcie nie powinno ich być.

    # Zapis ruchów – bardziej strukturalny
    moves_el = ET.SubElement(root, "Moves")
    if hasattr(game_scene, "move_history"):
        for move in game_scene.move_history:
            move_el = ET.SubElement(moves_el, "Move")
            move_el.set("timestamp", str(move.get("timestamp", 0)))
            description = move.get("description", "")
            if description.startswith("Utworzono most"):
                create_el = ET.SubElement(move_el, "CreateBridge")
                m = re.search(r"Utworzono most między \(([\d.]+), ([\d.]+)\) a \(([\d.]+), ([\d.]+)\) o koszcie (\d+)", description)
                if m:
                    ET.SubElement(create_el, "Source").text = f"{m.group(1)},{m.group(2)}"
                    ET.SubElement(create_el, "Target").text = f"{m.group(3)},{m.group(4)}"
                    ET.SubElement(create_el, "Cost").text = m.group(5)
                else:
                    ET.SubElement(create_el, "Info").text = description
            elif description.startswith("Usunięto most"):
                remove_el = ET.SubElement(move_el, "RemoveBridge")
                m = re.search(r"Usunięto most między \(([\d.]+), ([\d.]+)\) a \(([\d.]+), ([\d.]+)\)", description)
                if m:
                    ET.SubElement(remove_el, "Source").text = f"{m.group(1)},{m.group(2)}"
                    ET.SubElement(remove_el, "Target").text = f"{m.group(3)},{m.group(4)}"
                else:
                    ET.SubElement(remove_el, "Info").text = description
            elif description.startswith("Status punktowy:"):
                status_el = ET.SubElement(move_el, "Status")
                parts = description.replace("Status punktowy:", "").split(";")
                for part in parts:
                    part = part.strip()
                    if part:
                        m = re.search(r"\((\w+)\s+@\s+([\d.]+),([\d.]+):\s+(\d+)\s+pts\)", part)
                        if m:
                            cell_status = ET.SubElement(status_el, "Cell")
                            cell_status.set("type", m.group(1))
                            cell_status.set("x", m.group(2))
                            cell_status.set("y", m.group(3))
                            cell_status.set("points", m.group(4))
                        else:
                            ET.SubElement(status_el, "Info").text = part
            elif description.startswith("Status przed ostatnim ruchem:"):
                pre_final_el = ET.SubElement(move_el, "PreFinalStatus")
                parts = description.replace("Status przed ostatnim ruchem:", "").split(";")
                for part in parts:
                    part = part.strip()
                    if part:
                        m = re.search(r"\((\w+)\s+@\s+([\d.]+),([\d.]+):\s+(\d+)\s+pts\)", part)
                        if m:
                            cell_status = ET.SubElement(pre_final_el, "Cell")
                            cell_status.set("type", m.group(1))
                            cell_status.set("x", m.group(2))
                            cell_status.set("y", m.group(3))
                            cell_status.set("points", m.group(4))
                        else:
                            ET.SubElement(pre_final_el, "Info").text = part
            elif description.startswith("Wynik:"):
                result_el = ET.SubElement(move_el, "Result")
                result_el.text = description.replace("Wynik:", "").strip()
            else:
                ET.SubElement(move_el, "Description").text = description

    # Zapis stanu końcowego – tylko komórki
    final_state = ET.SubElement(root, "FinalState")
    final_cells_el = ET.SubElement(final_state, "Cells")
    for cell in game_scene.cells:
        cell_el = ET.SubElement(final_cells_el, "Cell")
        cell_el.set("x", str(cell.x))
        cell_el.set("y", str(cell.y))
        cell_el.set("type", cell.cell_type)
        cell_el.set("points", str(cell.points))
    # Usunięto zapis połączeń z końcowego stanu, ponieważ na końcu gry nie powinny być mosty.

    # Zapis do pliku z czytelnym formatowaniem
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")
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
            timestamp = float(move_el.get("timestamp", 0))
            # Jeśli <Move> posiada dzieci, złożymy opis z podtagów
            if len(move_el):
                description_parts = []
                for child in move_el:
                    if child.tag == "CreateBridge":
                        source = child.find("Source").text if child.find("Source") is not None else ""
                        target = child.find("Target").text if child.find("Target") is not None else ""
                        cost = child.find("Cost").text if child.find("Cost") is not None else ""
                        description_parts.append(f"Utworzono most między ({source}) a ({target}) o koszcie {cost}")
                    elif child.tag == "RemoveBridge":
                        source = child.find("Source").text if child.find("Source") is not None else ""
                        target = child.find("Target").text if child.find("Target") is not None else ""
                        description_parts.append(f"Usunięto most między ({source}) a ({target})")
                    elif child.tag == "Status":
                        cell_parts = []
                        for cell in child.findall("Cell"):
                            typ = cell.get("type", "neutral")
                            x = cell.get("x", "0")
                            y = cell.get("y", "0")
                            points = cell.get("points", "0")
                            cell_parts.append(f"({typ} @ {x},{y}: {points} pts)")
                        description_parts.append("Status punktowy: " + "; ".join(cell_parts))
                    elif child.tag == "PreFinalStatus":
                        cell_parts = []
                        for cell in child.findall("Cell"):
                            typ = cell.get("type", "neutral")
                            x = cell.get("x", "0")
                            y = cell.get("y", "0")
                            points = cell.get("points", "0")
                            cell_parts.append(f"({typ} @ {x},{y}: {points} pts)")
                        description_parts.append("Status przed ostatnim ruchem: " + "; ".join(cell_parts))
                    elif child.tag == "Result":
                        result_text = child.text.strip() if child.text else ""
                        description_parts.append("Wynik: " + result_text)
                    else:
                        if child.text:
                            description_parts.append(child.text.strip())
                full_description = "\n".join(description_parts)
            else:
                full_description = (move_el.text or "").strip()
            move = {
                "timestamp": timestamp,
                "description": full_description.strip()
            }
            history["moves"].append(move)

    return history

def save_game_history_json(game_scene, filename):
    # Przygotowanie słownika do zapisu
    data = {}
    # Zapis początkowego stanu – tylko komórki
    data["initial_state"] = {
        "cells": [
            {
                "x": cell.x,
                "y": cell.y,
                "type": str(getattr(cell, 'initial_type', cell.cell_type)),
                "points": cell.points
            } for cell in game_scene.cells
        ]
    }
    # Zapis ruchów
    data["moves"] = game_scene.move_history

    # Zapis stanu końcowego – tylko komórki
    data["final_state"] = {
        "cells": [
            {
                "x": cell.x,
                "y": cell.y,
                "type": cell.cell_type,
                "points": cell.points
            } for cell in game_scene.cells
        ]
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_game_history_json(filename):
    if not os.path.exists(filename):
        return {"initial_state": {"cells": []}, "moves": []}
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data
