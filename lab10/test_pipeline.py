import os, random, argparse
import torch
import torchvision.ops                                  # <-- patch NMS jak wcześniej
import cv2                                              # <-- nowy import
import numpy as np                                      # <-- nowy import

# patch NMS na CPU
orig_nms = torchvision.ops.nms
def nms_cpu(boxes, scores, iou_threshold):
    return orig_nms(boxes.cpu(), scores.cpu(), iou_threshold).to(boxes.device)
torchvision.ops.nms = nms_cpu

from ultralytics import YOLO

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', type=str,
                        default='runs/detect/tool_detector/weights/best.pt',
                        help="ścieżka do wytrenowanych wag")
    parser.add_argument('--test_dir', type=str,
                        default='dataset/test/images',
                        help="folder ze zdjęciami testowymi")
    parser.add_argument('--device', type=str,
                        default='0' if torch.cuda.is_available() else 'cpu',
                        help="CUDA device id lub 'cpu'")
    parser.add_argument('--num', type=int, default=4,
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
        results = model.predict(
            source=img_path,
            device=f"cuda:{args.device}" if args.device!='cpu' else 'cpu',
            verbose=False
        )
        boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
        classes = results[0].boxes.cls.cpu().numpy().astype(int)
        confs = results[0].boxes.conf.cpu().numpy()              # <-- pobierz confidence
        for (x1, y1, x2, y2), cls, conf in zip(boxes, classes, confs):
            text = f"{model.names[int(cls)]} {conf:.2f}"
            # bbox
            cv2.rectangle(img, (x1, y1), (x2, y2), (0,255,0), 2)
            # większy font z obwódką
            font = cv2.FONT_HERSHEY_SIMPLEX
            fs = 1.0      # skalowanie tekstu
            th = 2        # grubość obwódki
            # czarna obwódka
            cv2.putText(img, text, (x1, y1-10), font, fs, (0,0,0), th*2, cv2.LINE_AA)
            # biały tekst
            cv2.putText(img, text, (x1, y1-10), font, fs, (255,255,255), th,   cv2.LINE_AA)
        annotated.append(img)

    # zbuduj siatkę 2x2
    row1 = np.hstack((annotated[0], annotated[1]))
    row2 = np.hstack((annotated[2], annotated[3]))
    grid = np.vstack((row1, row2))

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