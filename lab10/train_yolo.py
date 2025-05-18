import argparse
import torch
import torchvision.ops  # importujemy by wypatchować NMS
import numpy as np                # <-- nowy import
import os
from ultralytics import YOLO

orig_nms = torchvision.ops.nms
def nms_cpu(boxes, scores, iou_threshold):
    return orig_nms(boxes.cpu(), scores.cpu(), iou_threshold).to(boxes.device)
torchvision.ops.nms = nms_cpu

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=str, default='dataset.yaml')
    parser.add_argument('--coco_json', type=str, default='out/annotations.json',
                        help="ścieżka do pliku COCO JSON z adnotacjami")
    parser.add_argument('--use_coco', action='store_true',
                        help="użyj zamiast YAML adnotacji COCO")
    parser.add_argument('--model', type=str, default='yolo11n.pt')  # zmieniono na istniejący plik
    parser.add_argument('--device', type=str, default='0',
                        help="CUDA device id lub 'cpu'")
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--batch', type=int, default=16)
    parser.add_argument('--imgsz', type=int, default=1024)
    parser.add_argument('--no_val', action='store_true',
                        help="wyłącz walidację, aby pominąć CPU-NMS w Train")
    args = parser.parse_args()

    # katalog skryptu
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # inicjalizacja modelu
    model = YOLO(args.model)

    # wybór źródła danych: YAML lub COCO JSON
    data_source = args.coco_json if args.use_coco else args.data

    # jeśli GPU dostępne i wybrane, użyj GPU, inaczej CPU
    device = f"cuda:{args.device}" if (args.device != 'cpu' and torch.cuda.is_available()) else 'cpu'

    # trenowanie z podanym device
    results = model.train(
        data=data_source,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=device,
        project=script_dir,
        name='tool_detector',
        val=not args.no_val
    )

    # wypisz metryki z DetMetrics.box
    box = results.box

    # uśrednij wektory metryk i skonwertuj na float
    p       = float(np.mean(box.p))
    r       = float(np.mean(box.r))
    map50   = float(np.mean(box.map50))    if hasattr(box, 'map50')    else None
    map50_95= float(np.mean(box.map50_95)) if hasattr(box, 'map50_95') else float(np.mean(box.map))

    print(f"Precision: {p:.3f}, Recall: {r:.3f}, mAP@0.5: {map50:.3f}, mAP@0.5-0.95: {map50_95:.3f}")