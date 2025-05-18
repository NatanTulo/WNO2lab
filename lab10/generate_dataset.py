import cv2
import os
import numpy as np
import random
from glob import glob
import json  # <-- nowy import

# Definicja ścieżek do folderów
backgrounds_dir = 'in/backgrounds'
komb_dir = 'in/komb'
miecz_dir = 'in/miecz'
srub_dir = 'in/srub'

# Zmiana definicji folderów wyjściowych, aby uwzględniały kategorie
output_base_dir = 'out'
tool_categories = ['komb', 'miecz', 'srub']

# Utworzenie folderów wyjściowych dla każdej kategorii (synthetic, masks i yolo)
for category in tool_categories:
    os.makedirs(os.path.join(output_base_dir, category, 'synthetic'), exist_ok=True)
    os.makedirs(os.path.join(output_base_dir, category, 'masks'), exist_ok=True)
    os.makedirs(os.path.join(output_base_dir, category, 'yolo'), exist_ok=True)

# Funkcja do wczytywania obrazów
def load_images(directory):
    images = []
    paths = glob(os.path.join(directory, '*.jpg')) + glob(os.path.join(directory, '*.png'))
    for path in paths:
        img = cv2.imread(path)
        if img is not None:
            images.append(img)
    return images

# Funkcja do wczytywania narzędzi z kanałem alpha
def load_tools(directory):
    tools = []
    paths = glob(os.path.join(directory, '*.png'))
    for path in paths:
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            # Jeśli obraz nie ma kanału alpha, dodaj go
            if len(img.shape) == 2 or img.shape[2] == 3:
                # Konwersja do skali szarości i stworzenie maski
                if len(img.shape) == 3:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                else:
                    gray = img.copy()
                _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
                
                # Dodanie kanału alpha
                if len(img.shape) == 2:
                    # Konwersja do BGR
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                else:
                    img_bgr = img
                
                # Dodanie kanału alpha
                rgba = np.zeros((img_bgr.shape[0], img_bgr.shape[1], 4), dtype=np.uint8)
                rgba[:, :, :3] = img_bgr
                rgba[:, :, 3] = mask
                img = rgba
            tools.append(img)
    return tools

# Wczytanie obrazów
bg_images = load_images(backgrounds_dir)
komb_tools = load_tools(komb_dir)
miecz_tools = load_tools(miecz_dir)
srub_tools = load_tools(srub_dir)

# Słownik mapujący narzędzia na ich kategorie
tool_category_map = {}
for tool in komb_tools:
    tool_category_map[id(tool)] = 'komb'
for tool in miecz_tools:
    tool_category_map[id(tool)] = 'miecz'
for tool in srub_tools:
    tool_category_map[id(tool)] = 'srub'

all_tools = komb_tools + miecz_tools + srub_tools

# Inicjalizacja struktur dla COCO
coco_images = []
coco_annotations = []
annotation_id = 1
category_mapping = {"komb": 1, "miecz": 2, "srub": 3}
categories = [{"id": 1, "name": "komb"},
              {"id": 2, "name": "miecz"},
              {"id": 3, "name": "srub"}]

# Funkcja do nakładania narzędzia na tło
def overlay_tool(background, tool, x, y):
    # Skopiowanie obrazów, aby uniknąć modyfikacji oryginałów
    bg = background.copy()
    bg_h, bg_w = bg.shape[:2]
    
    tool_h, tool_w = tool.shape[:2]
    
    # Przytnij narzędzie, jeśli wykracza poza granice tła
    tool_y1 = max(0, -y)
    tool_y2 = min(tool_h, bg_h - y)
    tool_x1 = max(0, -x)
    tool_x2 = min(tool_w, bg_w - x)
    
    # Oblicz współrzędne ROI na tle
    roi_y1 = max(0, y)
    roi_y2 = min(bg_h, y + tool_h)
    roi_x1 = max(0, x)
    roi_x2 = min(bg_w, x + tool_w)
    
    # Sprawdź, czy cokolwiek się nakłada
    if tool_y2 <= tool_y1 or tool_x2 <= tool_x1:
        return bg, np.zeros((bg_h, bg_w), dtype=np.uint8)
    
    # Przygotuj maskę dla całego obrazu
    mask = np.zeros((bg_h, bg_w), dtype=np.uint8)
    
    # Wytnij fragmenty narzędzia i jego kanału alpha
    tool_roi = tool[tool_y1:tool_y2, tool_x1:tool_x2]
    alpha = tool_roi[:, :, 3] / 255.0
    alpha_3d = np.stack([alpha] * 3, axis=2)
    
    # Nałóż narzędzie na tło z uwzględnieniem alpha
    bg_roi = bg[roi_y1:roi_y2, roi_x1:roi_x2]
    composed = (1 - alpha_3d) * bg_roi + alpha_3d * tool_roi[:, :, :3]
    bg[roi_y1:roi_y2, roi_x1:roi_x2] = composed.astype(np.uint8)
    
    # Zaktualizuj maskę
    mask[roi_y1:roi_y2, roi_x1:roi_x2] = (alpha * 255).astype(np.uint8)
    
    return bg, mask

# Funkcja do sprawdzenia i przeskalowania narzędzia, jeśli jest za duże
def ensure_proper_size(tool, background_height, background_width, max_ratio=0.8):
    tool_h, tool_w = tool.shape[:2]
    bg_h, bg_w = background_height, background_width
    
    # Oblicz maksymalną dopuszczalną wysokość i szerokość narzędzia
    max_tool_h = int(bg_h * max_ratio)
    max_tool_w = int(bg_w * max_ratio)
    
    # Sprawdź czy narzędzie jest za duże
    if tool_h > max_tool_h or tool_w > max_tool_w:
        # Oblicz współczynnik skalowania
        scale_h = max_tool_h / tool_h if tool_h > max_tool_h else 1.0
        scale_w = max_tool_w / tool_w if tool_w > max_tool_w else 1.0
        scale = min(scale_h, scale_w)
        
        # Skaluj narzędzie
        new_height = int(tool_h * scale)
        new_width = int(tool_w * scale)
        resized_tool = cv2.resize(tool, (new_width, new_height), interpolation=cv2.INTER_AREA)
        return resized_tool
    
    return tool

# Funkcja do obracania obrazu z kanałem alpha bez przycinania
def rotate_image_with_alpha(image, angle):
    # Uzyskaj wymiary obrazu
    h, w = image.shape[:2]
    
    # Oblicz środek obrotu
    center = (w / 2, h / 2)
    
    # Oblicz nowy rozmiar obrazu po obrocie, aby nic nie zostało przycięte
    # Użyj równania dla maksymalnego rozmiaru obrazu po obrocie dowolnego kąta
    diagonal = np.sqrt(h**2 + w**2)
    new_h = int(diagonal)
    new_w = int(diagonal)
    
    # Macierz transformacji dla obrotu
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Dostosuj macierz transformacji, aby środek obrazu pozostał w środku
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]
    
    # Wykonaj obrót z zachowaniem całego obrazu
    return cv2.warpAffine(image, M, (new_w, new_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))

# Funkcja do skalowania obrazu z zachowaniem kanału alpha
def scale_image_with_alpha(image, scale_factor):
    h, w = image.shape[:2]
    new_h = int(h * scale_factor)
    new_w = int(w * scale_factor)
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

# Generowanie syntetycznych obrazów
num_images = 400
# Obliczanie liczby obrazów na kategorię
images_per_category = num_images // len(tool_categories)
remaining_images = num_images % len(tool_categories)

# Słownik przechowujący licznik obrazów dla każdej kategorii
category_counters = {category: 0 for category in tool_categories}

for i in range(num_images):
    # Wybierz losowe tło
    bg_img = random.choice(bg_images)
    bg_h, bg_w = bg_img.shape[:2]
    
    # Wybieramy kategorię narzędzia aby zapewnić równomierny rozkład
    if i < images_per_category * len(tool_categories):
        # Wybieramy kategorię na podstawie indeksu, aby zapewnić równy rozkład
        category_index = i // images_per_category
        category = tool_categories[category_index]
        if category == 'komb':
            tool_img = random.choice(komb_tools).copy()
        elif category == 'miecz':
            tool_img = random.choice(miecz_tools).copy()
        else:  # srub
            tool_img = random.choice(srub_tools).copy()
    else:
        # Dla pozostałych obrazów wybieramy losowo
        tool_original = random.choice(all_tools)
        tool_img = tool_original.copy()
        category = tool_category_map[id(tool_original)]
    
    # Zwiększamy licznik dla wybranej kategorii
    category_counters[category] += 1
    
    # Losowe skalowanie między 30% a 100% oryginalnego rozmiaru
    scale_factor = random.uniform(0.3, 1.0)
    tool_scaled = scale_image_with_alpha(tool_img, scale_factor)
    
    # Losowy kąt obrotu
    angle = random.uniform(0, 360)
    tool_rotated = rotate_image_with_alpha(tool_scaled, angle)
    
    # Upewnij się, że narzędzie nie jest za duże względem tła
    tool_aug = ensure_proper_size(tool_rotated, bg_h, bg_w)
    
    # Losowa pozycja dla narzędzia
    tool_h, tool_w = tool_aug.shape[:2]
    
    # Zmienione - upewnij się, że narzędzie jest całkowicie widoczne na obrazie
    # Nie używamy już paddingu, który pozwalał na częściowe wyjście poza krawędź
    x_min = 0
    x_max = bg_w - tool_w
    y_min = 0
    y_max = bg_h - tool_h
    
    # Upewnij się, że mamy poprawny zakres dla randint
    # Jeśli narzędzie jest większe niż tło, umieść je na środku
    if x_min >= x_max:
        x = (bg_w - tool_w) // 2
    else:
        x = random.randint(x_min, x_max)
    
    if y_min >= y_max:
        y = (bg_h - tool_h) // 2
    else:
        y = random.randint(y_min, y_max)
    
    # Nałóż narzędzie na tło
    result_img, tool_mask = overlay_tool(bg_img, tool_aug, x, y)
    
    # Zapisz syntetyczny obraz
    image_filename = f'synthetic_{category_counters[category]:04d}.jpg'
    output_path = os.path.join(output_base_dir, category, 'synthetic', image_filename)
    cv2.imwrite(output_path, result_img)
    
    # Zapisz maskę narzędzia
    mask_filename = f'mask_{category_counters[category]:04d}.png'
    mask_path = os.path.join(output_base_dir, category, 'masks', mask_filename)
    cv2.imwrite(mask_path, tool_mask)

    # Dodaj obraz do listy COCO
    image_id = i + 1
    coco_images.append({
        "id": image_id,
        "file_name": os.path.join(category, 'synthetic', image_filename),
        "width": bg_w,
        "height": bg_h
    })
    
    # Wyznaczanie rzeczywistego bbox za pomocą maski
    ys, xs = np.where(tool_mask > 0)
    if xs.size and ys.size:
        x1, x2 = int(xs.min()), int(xs.max())
        y1, y2 = int(ys.min()), int(ys.max())
    else:
        # fallback na cały prostokąt narzędzia
        x1, y1 = x, y
        x2, y2 = x + tool_w - 1, y + tool_h - 1

    w_box = x2 - x1 + 1
    h_box = y2 - y1 + 1

    # COCO annotation
    bbox = [x1, y1, w_box, h_box]
    segmentation = [[x1, y1, x2, y1, x2, y2, x1, y2]]
    coco_annotations.append({
        "id": annotation_id,
        "image_id": image_id,
        "category_id": category_mapping[category],
        "bbox": bbox,
        "segmentation": segmentation,
        "area": w_box * h_box,
        "iscrowd": 0
    })
    annotation_id += 1

    # YOLO format (znormalizowane centroidy i wymiary)
    x_center = (x1 + w_box / 2) / bg_w
    y_center = (y1 + h_box / 2) / bg_h
    width_norm = w_box / bg_w
    height_norm = h_box / bg_h
    yolo_line = f"{category_mapping[category]-1} {x_center:.6f} {y_center:.6f} {width_norm:.6f} {height_norm:.6f}"
    yolo_filename = os.path.join(output_base_dir, category, 'yolo', image_filename.replace('.jpg', '.txt'))
    with open(yolo_filename, "w") as f:
        f.write(yolo_line)
    
    # Wyświetl informacje o postępie co 20 obrazów
    if (i + 1) % 20 == 0:
        print(f"Wygenerowano {i + 1}/{num_images} obrazów")

# Po zakończeniu pętli zapisz plik JSON z adnotacjami w formacie COCO
coco_output = {
    "info": {},
    "images": coco_images,
    "annotations": coco_annotations,
    "categories": categories
}
with open(os.path.join(output_base_dir, "annotations.json"), "w") as json_file:
    json.dump(coco_output, json_file)

# Wyświetl podsumowanie
print(f"Wygenerowano {num_images} syntetycznych obrazów z maskami oraz adnotacjami COCO i YOLO:")
for category, count in category_counters.items():
    print(f"- {category}: {count} obrazów")

