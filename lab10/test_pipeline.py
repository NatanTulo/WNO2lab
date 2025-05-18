import os, random, argparse
import torch
import torchvision.ops                                  # <-- patch NMS jak wcześniej
import cv2                                              # <-- nowy import
import numpy as np                                      # <-- nowy import
import math                                             # <-- nowy import

# patch NMS na CPU
orig_nms = torchvision.ops.nms
def nms_cpu(boxes, scores, iou_threshold):
    return orig_nms(boxes.cpu(), scores.cpu(), iou_threshold).to(boxes.device)
torchvision.ops.nms = nms_cpu

from ultralytics import YOLO

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', type=str,
                        default='best3yolo11n.pt',
                        help="ścieżka do wytrenowanych wag")
    parser.add_argument('--test_dir', type=str,
                        default='test/',
                        help="folder ze zdjęciami testowymi")
    parser.add_argument('--device', type=str,
                        default='0' if torch.cuda.is_available() else 'cpu',
                        help="CUDA device id lub 'cpu'")
    parser.add_argument('--num', type=int, default=9,    # <-- nowa domyślna wartość
                        help="liczba losowych obrazów do przetestowania")
    args = parser.parse_args()

    # zbierz wszystkie obrazy testowe
    imgs = [os.path.join(args.test_dir, f) 
            for f in os.listdir(args.test_dir) 
            if f.lower().endswith(('.jpg','.png'))]
    if len(imgs) < args.num:
        raise ValueError(f"Brakuje obrazów w {args.test_dir}")

    # wybierz losowo args.num plików
    sample = random.sample(imgs, args.num)

    # wczytaj model z wytrenowanymi wagami
    model = YOLO(args.weights)

    # inferencja i przygotowanie obrazów z anotacjami
    annotated = []
    for img_path in sample:
        img = cv2.imread(img_path)
        h_img, w_img = img.shape[:2]
        results = model.predict(
            source=img_path,
            device=f"cuda:{args.device}" if args.device!='cpu' else 'cpu',
            verbose=False
        )
        boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
        classes = results[0].boxes.cls.cpu().numpy().astype(int)
        confs = results[0].boxes.conf.cpu().numpy()              # <-- pobierz confidence
        for (x1, y1, x2, y2), cls, conf in zip(boxes, classes, confs):
            # narysuj bounding box
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # przygotuj i oblicz pozycję tekstu
            text = f"{model.names[int(cls)]} {conf:.2f}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            fs, th = 1.0, 2
            (tw, th_text), _ = cv2.getTextSize(text, font, fs, th)
            margin = 10
            tx = x1
            ty = y1 - margin
            if ty - th_text < 0:
                ty = y2 + margin + th_text
            if ty > h_img:
                ty = h_img - 1
            if tx + tw > w_img:
                tx = w_img - tw - 1

            # czarna obwódka
            cv2.putText(img, text, (tx, ty), font, fs, (0,0,0), th*3, cv2.LINE_AA)
            # biały tekst
            cv2.putText(img, text, (tx, ty), font, fs, (255,255,255), th,   cv2.LINE_AA)
        annotated.append(img)

    # automatyczne obliczenie wymiarów siatki
    n = len(annotated)
    cols = int(math.ceil(math.sqrt(n)))
    rows = int(math.ceil(n / cols))
    # dopełnienie pustymi obrazami, jeśli potrzeba
    blank = np.zeros_like(annotated[0])
    annotated += [blank] * (rows * cols - n)

    # budowa siatki
    row_images = []
    for r in range(rows):
        row_slice = annotated[r*cols:(r+1)*cols]
        row_images.append(np.hstack(row_slice))
    grid = np.vstack(row_images)

    # przygotuj katalog zapisu
    save_dir = os.path.join('runs', 'detect')
    os.makedirs(save_dir, exist_ok=True)

    # znajdź pierwszą wolną nazwę pliku
    base = 'test_summary'
    ext = '.jpg'
    idx = 0
    while True:
        fname = f"{base}{ext}" if idx == 0 else f"{base}_{idx}{ext}"
        summary_path = os.path.join(save_dir, fname)
        if not os.path.exists(summary_path):
            break
        idx += 1

    # zapisz podsumowującą grafikę
    cv2.imwrite(summary_path, grid)
    print(f"Zapisano siatkę wyników do {summary_path}")