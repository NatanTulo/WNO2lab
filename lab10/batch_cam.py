import os
import random
import argparse
import cv2
import numpy as np
import math
import subprocess # Dodano import
import sys # Dodano import
from simple_grad_cam import SimpleGradCAM
from ultralytics import YOLO

def process_images(model_path, image_dir, num_images, layer, device, output_path):
    """Generuje mapy aktywacji dla wielu obrazów i tworzy siatkę z wynikami"""
    
    # Wczytaj wszystkie obrazy z katalogu
    image_files = [f for f in os.listdir(image_dir) 
                  if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
    
    if not image_files:
        print(f"Nie znaleziono obrazów w katalogu {image_dir}")
        return
    
    # Jeśli żądana liczba jest większa niż dostępna, użyj wszystkich
    if num_images > len(image_files):
        num_images = len(image_files)
        print(f"Znaleziono tylko {num_images} obrazów, używam wszystkich")
    
    # Losowo wybierz obrazy do przetworzenia
    selected_images = random.sample(image_files, num_images)
    print(f"Wybrano {num_images} obrazów do przetworzenia")
    
    # Inicjalizacja modelu i CAM
    model = YOLO(model_path)
    cam = SimpleGradCAM(model_path, layer, device)
    
    # Przetwórz każdy obraz
    processed_images = []
    for img_file in selected_images:
        img_path = os.path.join(image_dir, img_file)
        print(f"Przetwarzanie {img_file}...")
        
        # Generuj mapę aktywacji
        heatmap, img = cam.generate_cam(img_path)
        
        if heatmap is not None and img is not None:
            # Nałóż mapę cieplną
            result = cam.apply_heatmap(img, heatmap, alpha=0.5)
            
            # Dodaj etykietę z nazwą pliku na górze obrazu
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(result, img_file, (10, 30), font, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(result, img_file, (10, 30), font, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
            
            # Uruchom detekcję, aby dodać bounding boxy
            results = model(img_path)
            
            # Dodaj wyniki detekcji do obrazu
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    cls = int(box.cls.item())
                    conf = float(box.conf.item())
                    
                    # Narysuj bounding box
                    cv2.rectangle(result, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Dodaj etykietę
                    label = f"{model.names[cls]} {conf:.2f}"
                    (tw, th), _ = cv2.getTextSize(label, font, 0.6, 1)
                    cv2.rectangle(result, (x1, y1-th-5), (x1+tw, y1), (0, 255, 0), -1)
                    cv2.putText(result, label, (x1, y1-5), font, 0.6, (0, 0, 0), 1)
            
            # Dodaj do listy przetworzonych obrazów
            processed_images.append(result)
        else:
            print(f"Pominięto {img_file} - nie udało się wygenerować mapy aktywacji")
    
    if not processed_images:
        print("Nie udało się przetworzyć żadnego obrazu")
        return
        
    # Stwórz siatkę obrazów
    n = len(processed_images)
    cols = int(math.ceil(math.sqrt(n)))
    rows = int(math.ceil(n / cols))
    
    # Dostosuj wszystkie obrazy do jednakowego rozmiaru
    max_h = max(img.shape[0] for img in processed_images)
    max_w = max(img.shape[1] for img in processed_images)
    
    # Dopełnij do jednakowego rozmiaru
    resized_images = []
    for img in processed_images:
        h, w = img.shape[:2]
        canvas = np.zeros((max_h, max_w, 3), dtype=np.uint8)
        canvas[0:h, 0:w] = img
        resized_images.append(canvas)
    
    # Dopełnij siatkę pustymi obrazami, jeśli potrzeba
    blank = np.zeros((max_h, max_w, 3), dtype=np.uint8)
    resized_images += [blank] * (rows * cols - n)
    
    # Utwórz siatkę
    grid_rows = []
    for r in range(rows):
        row_imgs = resized_images[r*cols:(r+1)*cols]
        grid_rows.append(np.hstack(row_imgs))
    
    grid = np.vstack(grid_rows)
    
    # Zapisz wynik
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir): # Sprawdź, czy output_dir nie jest pusty
        os.makedirs(output_dir, exist_ok=True)
    
    cv2.imwrite(output_path, grid)
    print(f"Zapisano siatkę wyników do {output_path}")
    
    # Otwórz wynikowy obraz
    abs_output_path = os.path.abspath(output_path)
    try:
        if sys.platform == "win32":
            os.startfile(abs_output_path)
        elif sys.platform == "darwin": # macOS
            subprocess.run(["open", abs_output_path], check=True)
        else: # Linux and other Unix-like
            subprocess.run(["xdg-open", abs_output_path], check=True)
    except Exception as e:
        print(f"Nie udało się automatycznie otworzyć pliku: {abs_output_path}")
        print(f"Błąd: {e}")
        print("Upewnij się, że masz domyślną aplikację do otwierania obrazów .jpg skonfigurowaną w systemie.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generuje mapy aktywacji dla wielu obrazów")
    parser.add_argument("--model", type=str, default="best.pt", help="Ścieżka do modelu YOLO")
    parser.add_argument("--dir", type=str, default="test", help="Katalog z obrazami")
    parser.add_argument("--num", type=int, default=9, help="Liczba obrazów do przetworzenia")
    parser.add_argument("--layer", type=str, default="model.17", help="Nazwa warstwy")
    parser.add_argument("--device", type=str, default="cpu", help="Urządzenie (cpu lub cuda)")
    parser.add_argument("--output", type=str, default="runs/batch_cam.jpg", help="Ścieżka do pliku wynikowego")
    args = parser.parse_args()
    
    process_images(args.model, args.dir, args.num, args.layer, args.device, args.output)
