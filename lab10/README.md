# Projekt Detekcji Narzędzi z Wyjaśnialnością Modelu (XAI)

Ten projekt demonstruje kompletny potok uczenia maszynowego do detekcji obiektów (narzędzi) przy użyciu modeli YOLO, wraz z implementacją metod wyjaśnialnej sztucznej inteligencji (XAI) w postaci map aktywacji klas (CAM). Projekt zawiera narzędzia do pobierania danych, generowania syntetycznego zbioru danych, trenowania modelu, testowania oraz wizualizacji działania wewnętrznego modelu.

## Struktura Projektu

Główne komponenty projektu są dostępne poprzez interfejs graficzny (GUI) `gui.py`, który ułatwia uruchamianie poszczególnych skryptów.

-   `in/`: Katalog na wejściowe obrazy (tła, narzędzia).
-   `out/`: Katalog na wygenerowane dane syntetyczne (obrazy, maski, adnotacje).
-   `dataset/`: Katalog na podzielony zbiór danych (train, val, test) gotowy do trenowania.
-   `runs/`: Katalog na wyniki działania skryptów (np. wytrenowane modele, obrazy z detekcją, mapy CAM).
-   `test/`: Katalog na obrazy testowe generowane na potrzeby ewaluacji.

## Dostępne Skrypty (przez GUI)

Poniżej opisano funkcjonalność poszczególnych zakładek dostępnych w GUI (`gui.py`).

### 1. Downloader (`downloader.py`)

-   **Opis:** Pobiera losowe obrazy tła z internetu (picsum.photos) i zapisuje je w katalogu `in/backgrounds/`.
-   **Argumenty:** Brak konfigurowalnych argumentów z poziomu GUI. Domyślnie pobiera 20 obrazów.
-   **Cel:** Zgromadzenie różnorodnych teł do generowania syntetycznego zbioru danych.

### 2. Generate (`generate_dataset.py`)

-   **Opis:** Tworzy syntetyczny zbiór danych. Nakłada obrazy narzędzi (z kanałem alfa dla przezroczystości) na losowe tła. Generuje obrazy wynikowe, maski segmentacyjne dla narzędzi oraz adnotacje w formatach COCO JSON i YOLO TXT.
-   **Argumenty:** Brak konfigurowalnych argumentów z poziomu GUI dla standardowego generowania. Domyślnie generuje 400 obrazów.
-   **Wyjście:** Zapisuje dane w podkatalogach `out/{kategoria_narzędzia}/synthetic/`, `out/{kategoria_narzędzia}/masks/`, `out/{kategoria_narzędzia}/yolo/` oraz plik `out/annotations.json`.
-   **Kategorie narzędzi:** `komb`, `miecz`, `srub`.

### 3. Split (`split_dataset.py`)

-   **Opis:** Dzieli wygenerowany syntetyczny zbiór danych (obrazy i etykiety YOLO) na zestawy treningowy, walidacyjny i testowy.
-   **Argumenty:** Brak konfigurowalnych argumentów z poziomu GUI.
    -   Domyślny podział: 70% trening, 20% walidacja, 10% test.
-   **Wyjście:** Tworzy strukturę katalogów `dataset/train/`, `dataset/val/`, `dataset/test/` (każdy z podkatalogami `images/` i `labels/`).

### 4. Train YOLO (`train_yolo.py`)

-   **Opis:** Trenuje model detekcji obiektów YOLO na przygotowanym zbiorze danych.
-   **Argumenty (konfigurowalne w GUI):**
    -   `--model`: Ścieżka do wstępnie wytrenowanego modelu YOLO (np. `yolov8n.pt`).
    -   `--device`: Urządzenie do trenowania (`0` dla pierwszego GPU, `cpu`).
    -   `--epochs`: Liczba epok treningowych.
    -   `--batch`: Rozmiar paczki (batch size).
    -   `--imgsz`: Rozmiar obrazu wejściowego dla modelu.
    -   `--dropout`, `--weight_decay`: Parametry regularyzacji.
    -   `--hsv_h`, `--hsv_s`, `--hsv_v`: Parametry augmentacji HSV.
    -   `--mosaic`, `--mixup`: Parametry augmentacji mozaikowej i mixup.
    -   Możliwość użycia adnotacji COCO (`--use_coco`) lub YAML (`--data`).
    -   Opcja wyłączenia walidacji podczas treningu (`--no_val`) w celu uniknięcia potencjalnych spowolnień związanych z NMS na CPU.
-   **Wyjście:** Wytrenowany model (np. `runs/tool_detector/weights/best.pt`) oraz logi treningowe.

### 5. Generate Test Images (`generate_dataset.py` z flagą `--test_only`)

-   **Opis:** Generuje zestaw losowych, syntetycznych obrazów wyłącznie do celów testowych, bez tworzenia masek czy plików adnotacji.
-   **Argumenty (konfigurowalne w GUI):**
    -   `--test_only`: (Automatycznie ustawiane na `True`)
    -   `--test_count`: Liczba obrazów testowych do wygenerowania.
    -   `--test_dir`: Katalog docelowy dla obrazów testowych (domyślnie `test/`).
-   **Wyjście:** Obrazy JPG w podanym katalogu testowym.

### 6. Test (`test_pipeline.py`)

-   **Opis:** Uruchamia detekcję przy użyciu wytrenowanego modelu YOLO na kilku losowo wybranych obrazach z podanego katalogu testowego. Tworzy siatkę (grid) z wynikami detekcji (obrazy z nałożonymi ramkami i etykietami).
-   **Argumenty (konfigurowalne w GUI):**
    -   `--weights`: Ścieżka do wytrenowanych wag modelu (np. `best.pt`).
    -   `--test_dir`: Katalog z obrazami testowymi.
    -   `--num`: Liczba losowych obrazów do przetworzenia i wyświetlenia w siatce.
    -   `--device`: Urządzenie do przeprowadzenia inferencji (`cpu` lub ID GPU).
-   **Wyjście:** Obraz JPG (`runs/test_summary*.jpg`) zawierający siatkę przetworzonych obrazów.

### 7. Batch CAM (`batch_cam.py`)

-   **Opis:** Generuje wizualizacje map aktywacji klas (CAM) dla wielu obrazów z podanego katalogu. Wykorzystuje uproszczoną implementację CAM (`SimpleGradCAM`), która wizualizuje aktywacje wybranej warstwy konwolucyjnej bez użycia gradientów. Wyniki są prezentowane jako siatka obrazów, gdzie na każdy oryginalny obraz nałożona jest mapa cieplna oraz wyniki detekcji.
-   **Argumenty (konfigurowalne w GUI):**
    -   `--model`: Ścieżka do modelu YOLO (np. `best.pt`).
    -   `--dir`: Katalog z obrazami do przetworzenia.
    -   `--num`: Liczba losowych obrazów do przetworzenia.
    -   `--layer`: Nazwa warstwy docelowej do generowania CAM (np. `model.17`).
    -   `--device`: Urządzenie do inferencji i generowania CAM.
    -   `--output`: Ścieżka do zapisu wynikowej siatki obrazów.
-   **Wyjście:** Obraz JPG (`runs/batch_cam.jpg` lub inna podana ścieżka) z siatką obrazów z nałożonymi mapami CAM.

### 8. List Layers (`simple_grad_cam.py` z flagą `--list_layers`)

-   **Opis:** Wyświetla listę dostępnych warstw w podanym modelu YOLO. Jest to przydatne do zidentyfikowania odpowiedniej nazwy warstwy konwolucyjnej dla skryptu "Batch CAM".
-   **Argumenty (konfigurowalne w GUI):**
    -   `--model`: Ścieżka do modelu YOLO.
    -   `--list_layers`: (Automatycznie ustawiane na `True`)
    -   `--layer`: Nazwa warstwy (nieużywana przy listowaniu, ale obecna w GUI).
    -   `--device`: Urządzenie.
-   **Wyjście:** Lista warstw (nazwa i typ) wypisywana w konsoli.

## Inne Ważne Skrypty

-   **`simple_grad_cam.py`**: Stanowi rdzeń funkcjonalności generowania map aktywacji (CAM) używanej przez "Batch CAM" oraz "List Layers". Implementuje logikę przechwytywania aktywacji z określonej warstwy modelu i tworzenia z nich mapy cieplnej.

## Uruchamianie

1.  Upewnij się, że masz zainstalowane wszystkie wymagane biblioteki (głównie `torch`, `torchvision`, `ultralytics`, `opencv-python`, `numpy`, `requests`).
2.  Przygotuj obrazy narzędzi w formacie PNG (z przezroczystością lub jednolitym tłem do usunięcia) w katalogach `in/komb/`, `in/miecz/`, `in/srub/`.
3.  Uruchom interfejs graficzny:
    ```bash
    python gui.py
    ```
4.  Korzystaj z zakładek w GUI, aby wykonać poszczególne kroki projektu, zaczynając od "Downloader" i "Generate", a kończąc na "Train YOLO", "Test" i "Batch CAM".

## Kompatybilność Systemowa

Projekt został przetestowany na systemie Windows. Dołożono starań, aby zapewnić kompatybilność z systemami Linux:
-   Użycie `os.path.join` do manipulacji ścieżkami plików.
-   Wykrywanie systemu operacyjnego (`sys.platform`) do odpowiedniego otwierania plików wynikowych i uruchamiania skryptów w nowych oknach konsoli.
    -   Windows: `cmd.exe /k`
    -   Linux: Próba z `xterm -hold -e`, a następnie `gnome-terminal -- bash -c "command; exec bash"`
    -   macOS: Użycie skryptu tymczasowego z `open -a Terminal`

W przypadku problemów z automatycznym otwieraniem okien terminala na systemach innych niż Windows, skrypty wypiszą w konsoli polecenie, które można uruchomić ręcznie.