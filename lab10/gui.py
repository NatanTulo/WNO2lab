import os, sys, subprocess
import tkinter as tk
from tkinter import ttk, filedialog

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
            ("--model", "yolo11n.pt"),
            ("--device", "0"),
            ("--epochs", "50"),
            ("--batch", "16"),
            ("--imgsz", "1024"),
        ],
        "desc": "Trenuje model YOLO na przygotowanych adnotacjach (YAML lub COCO) i wypisuje metryki."
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
        ],
        "desc": "Uruchamia detekcję na kilku losowych obrazach i tworzy siatkę wyników."
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
PATH_FILE_KEYS = {"--data", "--coco_json", "--model", "--weights"}
PATH_DIR_KEYS  = {"--test_dir"}

def run_script(name, entries):
    cmd = [sys.executable, os.path.join(os.getcwd(), SCRIPTS[name]["script"])]
    for key, default, *rest in SCRIPTS[name]["args"]:
        if rest and rest[0] == "bool":
            if entries[key].get():
                cmd.append(key)
        else:
            cmd += [key, entries[key].get()]
    # uruchom w nowym oknie cmd i zostaw otwarte po zakończeniu
    subprocess.Popen(
        ["cmd.exe", "/k"] + cmd,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

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
                if key in {"--data","--coco_json","--model","--weights"}:
                    ttk.Button(row, text="…", width=3, command=lambda e=ent: browse_file(e)).pack(side="right",padx=2)
                if key in {"--test_dir"}:
                    ttk.Button(row, text="…", width=3, command=lambda e=ent: browse_dir(e)).pack(side="right",padx=2)
    else:
        ttk.Label(frame, text="brak argumentów", foreground="gray").pack(anchor="w", pady=5)
    ttk.Button(frame, text="Run", command=lambda n=tab_name, e=entries: run_script(n,e)).pack(pady=5)
    nb.add(frame, text=tab_name)

nb.pack(fill="both", expand=True)
root.mainloop()
