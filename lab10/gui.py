import os, sys, subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

SCRIPTS = {
    "Downloader": {
        "script": "downloader.py",
        "args": [],
        "desc": "Pobiera losowe obrazy tła z internetu do folderu in/backgrounds."
    },
    "Generate": {
        "script": "generate_dataset.py",
        "args": [],
        "desc": "Tworzy syntetyczny zbiór obrazów z nałożonymi narzędziami oraz maskami i adnotacjami."
    },
    "Split": {
        "script": "split_dataset.py",
        "args": [],
        "desc": "Dzieli wygenerowany zbiór na zestawy train/val/test wewnątrz folderu dataset."
    },
    "Train YOLO": {
        "script": "train_yolo.py",
        "args": [
            ("--model", "yolov8n.pt"), # Zmieniono na yolo11n.pt -> yolov8n.pt jako popularniejszy standard
            ("--device", "0"),
            ("--epochs", "50"),
            ("--batch", "16"),
            ("--imgsz", "1024"),
            ("--dropout", "0.2"),
            ("--weight_decay", "0.0005"),
            ("--hsv_h", "0.015"),
            ("--hsv_s", "0.7"),
            ("--hsv_v", "0.4"),
            ("--mosaic", "1.0"),
            ("--mixup", "0.1")
        ],
        "desc": "Trenuje model YOLO z regularyzacją (Dropout, L2) i augmentacją danych dla lepszej generalizacji."
    },
    "Generate Test Images": {
        "script": "generate_dataset.py",
        "args": [
            ("--test_only", True, "bool"),
            ("--test_count", "200"),
            ("--test_dir", "test/")
        ],
        "desc": "Wygeneruj 200 losowych syntetycznych obrazów w folderze test/ bez masek i JSON"
    },
    "Test": {
        "script": "test_pipeline.py",
        "args": [
            ("--weights", "best.pt"),
            ("--test_dir", "test/"),
            ("--num", "9"),
            # Usunięto --use_cam i --cam_layer
            ("--device", "cpu"),
        ],
        "desc": "Uruchamia detekcję na kilku losowych obrazach i tworzy siatkę wyników."
    },
    "Batch CAM": {
        "script": "batch_cam.py",
        "args": [
            ("--model", "best.pt"),
            ("--dir", "test"),
            ("--num", "9"),
            ("--layer", "model.17"), # Użytkownik może potrzebować zmienić tę warstwę
            ("--device", "cpu"),
            ("--output", "runs/batch_cam.jpg"),
        ],
        "desc": "Generuje wizualizacje aktywacji warstwy dla wielu obrazów naraz i tworzy siatkę wyników. Używa SimpleGradCAM."
    },
    "List Layers": {
        "script": "simple_grad_cam.py", # Używa simple_grad_cam.py do listowania
        "args": [
            ("--model", "best.pt"),
            # --img nie jest już ściśle wymagany, jeśli --list_layers jest użyte
            ("--list_layers", True, "bool"), # Dodano argument do bezpośredniego listowania
            ("--layer", "model.17"), # Domyślna warstwa, nieużywana przy list_layers
            ("--device", "cpu")      # Dodano device dla spójności
        ],
        "desc": "Wyświetla listę dostępnych warstw modelu przy użyciu SimpleGradCAM."
    },
}

# -- nowe funkcje do okien dialogowych --
def browse_file(entry):
    path = filedialog.askopenfilename(initialdir=os.getcwd())
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)

def browse_dir(entry):
    path = filedialog.askdirectory(initialdir=os.getcwd())
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)

# klucze, dla których pokazujemy różne dialogi
PATH_FILE_KEYS = {"--data", "--coco_json", "--model", "--weights", "--img"}
PATH_DIR_KEYS  = {"--test_dir", "--output"}

def run_script(name, entries):
    cmd = [sys.executable, os.path.join(os.getcwd(), SCRIPTS[name]["script"])]
    current_script_cfg = SCRIPTS[name]

    for key, default, *rest in current_script_cfg["args"]:
        is_bool_flag = rest and rest[0] == "bool"
        
        if is_bool_flag:
            # Dla flag boolowskich, dodaj klucz tylko jeśli zaznaczone
            if entries[key].get():
                cmd.append(key)
        else:
            value = entries[key].get()
            # Sprawdzenie dla "List Layers" - jeśli --list_layers jest True, niektóre inne argumenty mogą być opcjonalne
            if name == "List Layers" and key == "--img" and entries.get("--list_layers", tk.BooleanVar(value=False)).get():
                if not value: # Jeśli --list_layers jest aktywne i --img jest puste, nie dodawaj --img
                    continue 
            
            if key == "--img" and not value and name != "List Layers": # --img jest wymagane dla innych skryptów CAM
                 # Sprawdź, czy skrypt to batch_cam.py, który nie używa --img
                if current_script_cfg["script"] not in ["batch_cam.py", "simple_grad_cam.py"] or \
                  (current_script_cfg["script"] == "simple_grad_cam.py" and not entries.get("--list_layers", tk.BooleanVar(value=False)).get()):
                    messagebox.showerror("Błąd", f"Proszę wybrać plik obrazu dla {name} (argument {key})")
                    return

            # Dla Batch CAM sprawdź czy katalog istnieje
            if key == "--dir" and current_script_cfg["script"] == "batch_cam.py" and (not value or not os.path.isdir(value)):
                messagebox.showerror("Błąd", f"Katalog '{value}' dla argumentu {key} nie istnieje lub nie został podany.")
                return
            
            # Dodaj klucz i wartość, jeśli wartość nie jest pusta lub jeśli argument jest wymagany
            # (to uproszczenie, można dodać bardziej szczegółową logikę walidacji)
            if value or not (name == "List Layers" and key == "--img" and entries.get("--list_layers", tk.BooleanVar(value=False)).get()):
                            cmd += [key, value]


    # uruchom w nowym oknie cmd i zostaw otwarte po zakończeniu
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                ["cmd.exe", "/k"] + cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        elif sys.platform == "darwin": # macOS
            # Dla macOS, tworzymy skrypt tymczasowy do uruchomienia w Terminal.app
            # To obejście problemu z przekazywaniem wielu argumentów do 'open -a Terminal'
            script_content = f"#!/bin/bash\n{' '.join(cmd)}\nread -p 'Press Enter to close terminal...'"
            script_path = os.path.join(os.getcwd(), "run_script_macos.sh")
            with open(script_path, "w") as f:
                f.write(script_content)
            os.chmod(script_path, 0o755)
            subprocess.Popen(["open", "-a", "Terminal", script_path])
            # Można dodać opóźnienie i usunięcie skryptu, ale dla prostoty zostawiamy
        else: # Linux i inne systemy Unix-podobne
            # Próba z xterm, jeśli dostępny
            try:
                subprocess.Popen(["xterm", "-hold", "-e"] + cmd)
            except FileNotFoundError:
                # Jeśli xterm nie jest dostępny, spróbuj gnome-terminal
                try:
                    # gnome-terminal oczekuje, że polecenie będzie pojedynczym argumentem po '--'
                    # lub używa opcji -e (starsze wersje) lub --command (nowsze)
                    # Najbezpieczniej jest przekazać całe polecenie jako string do sh -c
                    terminal_cmd = ["gnome-terminal", "--", "bash", "-c", f"{' '.join(cmd)}; exec bash"]
                    subprocess.Popen(terminal_cmd)
                except FileNotFoundError:
                    messagebox.showerror("Błąd", "Nie znaleziono xterm ani gnome-terminal. Uruchom skrypt ręcznie w terminalu.")
                    print(f"Polecenie do uruchomienia: {' '.join(cmd)}")
    except Exception as e:
        messagebox.showerror("Błąd uruchamiania", f"Nie udało się uruchomić skryptu w nowym oknie: {e}")
        print(f"Polecenie do uruchomienia: {' '.join(cmd)}")


root = tk.Tk()
root.title("Lab10 Launcher")
nb = ttk.Notebook(root)

for tab_name, cfg in SCRIPTS.items():
    frame = tk.Frame(nb, padx=10, pady=10)
    entries = {}
    ttk.Label(frame, text=f"Skrypt: {cfg['script']}", font=("Arial",10,"bold")).pack(anchor="w")
    ttk.Label(frame, text=cfg.get("desc",""), foreground="gray", wraplength=500).pack(anchor="w", pady=2)
    if cfg["args"]:
        for key, default, *rest in cfg["args"]:
            row = tk.Frame(frame); row.pack(fill="x", pady=2)
            ttk.Label(row, text=key).pack(side="left")
            if rest and rest[0]=="bool":
                var = tk.BooleanVar(value=default)
                ttk.Checkbutton(row, variable=var).pack(side="right")
                entries[key] = var
            else:
                ent = ttk.Entry(row); ent.pack(side="right", fill="x", expand=True)
                ent.insert(0, default)
                entries[key] = ent
                if key in PATH_FILE_KEYS:
                    ttk.Button(row, text="…", width=3, command=lambda e=ent: browse_file(e)).pack(side="right",padx=2)
                if key in PATH_DIR_KEYS:
                    ttk.Button(row, text="…", width=3, command=lambda e=ent: browse_dir(e)).pack(side="right",padx=2)
    else:
        ttk.Label(frame, text="brak argumentów", foreground="gray").pack(anchor="w", pady=5)
    ttk.Button(frame, text="Run", command=lambda n=tab_name, e=entries: run_script(n,e)).pack(pady=5)
    nb.add(frame, text=tab_name)

nb.pack(fill="both", expand=True)
root.mainloop()
