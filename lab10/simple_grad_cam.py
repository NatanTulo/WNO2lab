import torch
import cv2
import numpy as np
import argparse
import os, sys
import subprocess # Upewnienie się, że jest importowany (choć był już używany niżej)
from ultralytics import YOLO

class SimpleGradCAM:
    """Uproszczona implementacja aktywacji warstw modelu YOLO - bez gradientów"""
    
    def __init__(self, model_path, target_layer_name='model.17', device='cpu'):
        self.device = device
        print(f"Inicjalizacja SimpleGradCAM na urządzeniu {device}")
        
        # Wczytaj model
        try:
            self.model = YOLO(model_path)
            self.model.to(device)
        except Exception as e:
            print(f"Błąd wczytywania modelu: {e}")
            self._print_available_layers_fallback() # Spróbuj wypisać warstwy nawet przy błędzie modelu
            raise
            
        # Przechowanie aktywacji
        self.activations = None
        self.hook_handle = None # Do przechowywania uchwytu do haka
        
        # Znajdź warstwę docelową
        self.target_layer = self._find_layer(target_layer_name)
        if self.target_layer is None:
            print(f"Nie znaleziono warstwy {target_layer_name}. Próba wyświetlenia dostępnych warstw.")
            self._print_available_layers()
            # Jeśli warstwa nie została znaleziona, nie rejestrujemy haka
            # Użytkownik będzie musiał podać poprawną nazwę warstwy
        else:
            print(f"Znaleziono warstwę {target_layer_name}: {type(self.target_layer).__name__}")
            self._register_hook()
    
    def _find_layer(self, layer_name):
        """Znajduje warstwę po nazwie"""
        # Sprawdzenie dla standardowej struktury modelu YOLO (np. model.model.17)
        if hasattr(self.model, 'model') and hasattr(self.model.model, 'model'):
            current_module = self.model.model.model
            parts = layer_name.split('.')
            
            # Jeśli nazwa to np. "model.10"
            if len(parts) == 2 and parts[0] == 'model' and parts[1].isdigit():
                try:
                    idx = int(parts[1])
                    if isinstance(current_module, list) and 0 <= idx < len(current_module):
                        return current_module[idx]
                except ValueError:
                    pass # Ignoruj błąd konwersji, spróbuj innych metod

            # Bardziej ogólne przeszukiwanie po nazwie
            for name, layer_candidate in self.model.model.named_modules():
                if name == layer_name: # Dopasowanie pełnej nazwy np. model.model.17.conv
                    return layer_candidate
            
            # Jeśli powyższe zawiodło, spróbuj iterować po częściach nazwy
            # (to jest bardziej ryzykowne i może wymagać dostosowania)
            # Na razie pozostajemy przy prostszym wyszukiwaniu po indeksie lub pełnej nazwie
            
        print(f"Nie udało się zlokalizować warstwy '{layer_name}' za pomocą standardowych metod.")
        return None
    
    def _print_available_layers_fallback(self):
        """Awaryjne listowanie warstw, jeśli model nie załadował się poprawnie."""
        print("Nie można załadować modelu, więc nie można wylistować warstw.")

    def _print_available_layers(self):
        """Wyświetla dostępne warstwy modelu"""
        if not hasattr(self.model, 'model'):
            print("Model nie ma atrybutu 'model'. Nie można wylistować warstw.")
            return
            
        print("Dostępne warstwy (nazwa: typ):")
        # Standardowa struktura YOLOv8
        if hasattr(self.model.model, 'model') and isinstance(self.model.model.model, torch.nn.Sequential):
            for i, layer in enumerate(self.model.model.model):
                print(f"  model.{i}: {type(layer).__name__}")
                # Można dodać rekurencyjne listowanie, jeśli warstwy są zagnieżdżone
                # for sub_name, sub_layer in layer.named_modules():
                #     print(f"    model.{i}.{sub_name}: {type(sub_layer).__name__}")
        # Alternatywnie, jeśli model.model jest listą modułów
        elif hasattr(self.model.model, 'model') and isinstance(self.model.model.model, list):
             for i, layer in enumerate(self.model.model.model):
                print(f"  model.{i}: {type(layer).__name__}")
        # Ogólne listowanie nazwanych modułów
        elif hasattr(self.model.model, 'named_modules'):
            for name, layer in self.model.model.named_modules():
                if "." not in name: # Pokaż tylko warstwy najwyższego poziomu w sekwencji
                    print(f"  {name}: {type(layer).__name__}")
        else:
            print("Nie można zidentyfikować struktury warstw modelu do wyświetlenia.")

    def _register_hook(self):
        """Rejestruje hook do przechwytywania aktywacji"""
        if self.target_layer is None:
            print("Warstwa docelowa nie jest ustawiona, nie można zarejestrować haka.")
            return
        
        # Usuń stary hook, jeśli istnieje
        if self.hook_handle is not None:
            self.hook_handle.remove()
            
        def save_activations(module, input, output):
            # Zapisz aktywacje jako kopię, aby uniknąć problemów z gradientami
            if isinstance(output, tuple):
                self.activations = output[0].detach().cpu()
            else:
                self.activations = output.detach().cpu()
        
# Zarejestruj hook
        self.hook_handle = self.target_layer.register_forward_hook(save_activations)
        print(f"Zarejestrowano hook dla warstwy: {type(self.target_layer).__name__}")
    
    def generate_cam(self, img_path):
        """Generuje mapę aktywacji dla obrazu - bez wstecznej propagacji"""
        if self.target_layer is None:
            print("Warstwa docelowa nie jest ustawiona. Nie można wygenerować CAM.")
            print("Proszę podać poprawną nazwę warstwy przy inicjalizacji SimpleGradCAM.")
            self._print_available_layers()
            # Próba odczytu obrazu, aby zwrócić go, nawet jeśli CAM się nie powiedzie
            if os.path.exists(img_path):
                img = cv2.imread(img_path)
                if img is not None:
                    return None, img.copy()
            return None, None

        if not os.path.exists(img_path):
            print(f"Nie znaleziono pliku: {img_path}")
            return None, None
        
        # Wczytaj obraz
        img = cv2.imread(img_path)
        if img is None:
            print(f"Nie można odczytać obrazu: {img_path}")
            return None, None
        
        raw_img = img.copy()
        
        # Uruchom model, aby uzyskać aktywacje
        try:
            # Upewnij się, że hook jest zarejestrowany, jeśli warstwa została znaleziona
            if self.target_layer and self.hook_handle is None:
                self._register_hook()

            with torch.no_grad():  # Wyłączamy śledzenie gradientów, bo korzystamy tylko z aktywacji
                results = self.model.predict(
                    source=img_path,
                    verbose=False,
                    device=self.device # Upewnij się, że predykcja używa właściwego urządzenia
                )
        except Exception as e:
            print(f"Błąd podczas predykcji: {e}")
            import traceback
            traceback.print_exc()
            return None, raw_img
        
        # Sprawdź, czy mamy aktywacje
        if self.activations is None:
            print("Brak aktywacji - sprawdź, czy warstwa docelowa jest poprawna i czy hook działa.")
            self._print_available_layers()
            return None, raw_img
        
        # Przekształć aktywacje na mapę cieplną
        try:
            # Uśredniamy po kanałach
            heatmap = torch.mean(self.activations, dim=1).squeeze().numpy()
            
            # ReLU na mapie cieplnej - pozostawiamy tylko dodatnie wartości
            heatmap = np.maximum(heatmap, 0)
            
            # Normalizacja mapy cieplnej do zakresu [0, 1]
            if np.max(heatmap) > 0:
                heatmap = (heatmap - np.min(heatmap)) / (np.max(heatmap) - np.min(heatmap))
            
            # Przeskalowanie mapy cieplnej do rozmiaru obrazu
            heatmap = cv2.resize(heatmap, (img.shape[1], img.shape[0]))
            
            return heatmap, raw_img
        except Exception as e:
            print(f"Błąd podczas generowania mapy cieplnej: {e}")
            import traceback
            traceback.print_exc()
            return None, raw_img
    
    def apply_heatmap(self, img, heatmap, alpha=0.5):
        """Nakłada mapę cieplną na obraz"""
        if heatmap is None:
            return img
        
        # Konwersja mapy cieplnej na kolorowy obraz
        heatmap_colored = cv2.applyColorMap(np.uint8(255 * heatmap), cv2.COLORMAP_JET)
        
        # Nałożenie mapy cieplnej na obraz
        output = cv2.addWeighted(img, 1 - alpha, heatmap_colored, alpha, 0)
        
        return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple CAM for YOLO models - bez gradientów")
    parser.add_argument("--model", type=str, required=True, help="Path to YOLO model")
    parser.add_argument("--img", type=str, help="Path to input image (opcjonalne, jeśli tylko listujemy warstwy)")
    parser.add_argument("--layer", type=str, default="model.17", help="Target layer name")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu or cuda)")
    parser.add_argument("--output", type=str, default="cam_output.jpg", help="Output file name")
    parser.add_argument("--list_layers", action="store_true", help="List available layers and exit")
    args = parser.parse_args()
    
    # Inicjalizacja Grad-CAM
    try:
        cam = SimpleGradCAM(args.model, args.layer, args.device)
        
        if args.list_layers:
            print("Listowanie dostępnych warstw:")
            cam._print_available_layers()
            sys.exit(0) # Ta instrukcja return powinna być tutaj

        if not args.img:
            parser.error("--img jest wymagany, chyba że używasz --list_layers")

        # Generowanie mapy CAM
        print(f"Generowanie mapy aktywacji dla {args.img}...")
        heatmap, img = cam.generate_cam(args.img)
        
        if heatmap is not None and img is not None:
            # Nałóż mapę cieplną na obraz
            output = cam.apply_heatmap(img, heatmap)
            
            # Zapisz wynik
            # Upewnij się, że katalog docelowy istnieje
            output_dir = os.path.dirname(args.output)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            cv2.imwrite(args.output, output)
            print(f"Zapisano wynik do {args.output}")
            
            # Zapisz również mapę cieplną
            heatmap_filename_dir = os.path.dirname(args.output) or '.'
            heatmap_filename = os.path.join(heatmap_filename_dir,
                                          f"heatmap_{os.path.basename(args.output)}")
            if heatmap_filename_dir and not os.path.exists(heatmap_filename_dir):
                os.makedirs(heatmap_filename_dir)
            cv2.imwrite(heatmap_filename, np.uint8(255 * heatmap))
            print(f"Zapisano mapę cieplną do {heatmap_filename}")
            
            # Otwórz wynikowy obraz
            abs_output_path = os.path.abspath(args.output)
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
        else:
            print("Nie udało się wygenerować mapy aktywacji.")
    except Exception as e:
        print(f"Wystąpił błąd: {e}")
        import traceback
        traceback.print_exc()
