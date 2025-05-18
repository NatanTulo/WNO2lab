import os, sys, glob
import cv2
import numpy as np
from PIL import Image
from icrawler.builtin import GoogleImageCrawler

def analyze_images(paths):
    """Prosta analiza: liczba i wymiary obrazów."""
    print(f"[ANALYSIS] Pobrano {len(paths)} obrazów:")
    for p in paths:
        try:
            im = Image.open(p)
            print(f"  {os.path.basename(p)} – {im.size[0]}x{im.size[1]}")
        except:
            print(f"  [ERROR] nie można odczytać {p}")

def fetch_images(query, out_dir, num=10):
    """Pobiera num obrazów z Google Images korzystając z icrawler."""
    crawler = GoogleImageCrawler(storage={'root_dir': out_dir})
    crawler.crawl(keyword=query, max_num=num)
    # zwróć listę pobranych plików
    return [os.path.join(out_dir, f) for f in os.listdir(out_dir) if os.path.isfile(os.path.join(out_dir, f))]

def process_image(path, out_dir, size=(256,256)):
    # wczytanie przez PIL (usuwa ICC profile)
    try:
        pil_img = Image.open(path).convert('RGBA')
    except Exception as e:
        print(f"[WARNING] {path}: błąd PIL.open – {e}")
        return
    data = np.array(pil_img)
    img = data[..., [2,1,0,3]]  # RGBA->BGRA

    # tworzenie maski: jeśli obraz ma przezroczyste tło, użyj kan. alfa, w przeciwnym razie Otsu
    alpha_chan = img[...,3]
    if (alpha_chan < 255).any():
        mask_full = (alpha_chan > 0).astype(np.uint8) * 255
    else:
        gray = cv2.cvtColor(img[..., :3], cv2.COLOR_BGR2GRAY)
        # adaptacyjne progowanie + morfologia
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        mask_full = cv2.adaptiveThreshold(
            blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11, 2
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
        mask_full = cv2.morphologyEx(mask_full, cv2.MORPH_CLOSE, kernel, iterations=2)
    cnts, _ = cv2.findContours(mask_full, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        print(f"[WARNING] {path}: brak wykrytych konturów")
        return
    c = max(cnts, key=cv2.contourArea)
    x,y,w,h = cv2.boundingRect(c)
    # przygotuj maskę tylko z największym konturem, wypełnioną w środku
    c_roi = c - np.array([[x, y]], dtype=np.int32)
    mask_crop = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(mask_crop, [c_roi], -1, 255, -1)
    # wytnij obszar i zastosuj maskę, zachowując oryginalne piksele
    roi = img[y:y+h, x:x+w]
    cropped = cv2.bitwise_and(roi, roi, mask=mask_crop)
    rgba = cv2.cvtColor(cropped[..., :3], cv2.COLOR_BGR2BGRA)
    rgba[...,3] = mask_crop

    # padding przed rotacją, aby nie obcinać treści
    h0, w0 = rgba.shape[:2]
    diag = int(np.ceil(np.sqrt(h0*h0 + w0*w0)))
    pad_v = (diag - h0) // 2
    pad_h = (diag - w0) // 2
    rgba = cv2.copyMakeBorder(rgba,
                              pad_v, diag - h0 - pad_v,
                              pad_h, diag - w0 - pad_h,
                              cv2.BORDER_CONSTANT, value=(0,0,0,0))
    mask_crop = cv2.copyMakeBorder(mask_crop,
                                   pad_v, diag - h0 - pad_v,
                                   pad_h, diag - w0 - pad_h,
                                   cv2.BORDER_CONSTANT, value=0)

    # obrót optymalny: minAreaRect, uwzględniając padding dla maksymalnej widoczności
    c_roi = c - np.array([[x, y]], dtype=np.int32) + np.array([[pad_h, pad_v]], dtype=np.int32)
    rect = cv2.minAreaRect(c_roi)
    angle = rect[2]
    w_rect, h_rect = rect[1]
    if h_rect < w_rect:
        angle += 90
    center = rect[0]
    M = cv2.getRotationMatrix2D(tuple(center), angle, 1.0)
    h_img, w_img = rgba.shape[:2]
    rgba = cv2.warpAffine(rgba, M, (w_img, h_img),
                          borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
    mask_full = cv2.warpAffine(mask_crop, M, (w_img, h_img),
                               flags=cv2.INTER_NEAREST)

    # sprawdzenie, by 'rączka' była na dole
    h2 = mask_full.shape[0] // 2
    if np.count_nonzero(mask_full[h2:]) < np.count_nonzero(mask_full[:h2]):
        rgba = cv2.flip(rgba, 0)
        mask_full = cv2.flip(mask_full, 0)

    # przycięcie z fallbackiem, gdy maska jest pusta
    ys, xs = np.where(mask_full > 0)
    if ys.size and xs.size:
        y0,y1 = ys.min(), ys.max(); x0,x1 = xs.min(), xs.max()
    else:
        y0,y1 = 0, rgba.shape[0]-1; x0,x1 = 0, rgba.shape[1]-1
    rgba = rgba[y0:y1+1, x0:x1+1]

    # ostateczna korekta: rączka w dół po PCA (dokładne wyrównanie)
    mask_c = rgba[...,3]
    h2 = mask_c.shape[0] // 2
    if np.count_nonzero(mask_c[h2:]) < np.count_nonzero(mask_c[:h2]):
        rgba = cv2.flip(rgba, 0)

    # zapis przetworzonego obrazu
    name = os.path.splitext(os.path.basename(path))[0] + "_proc.png"
    b,g,r,a = cv2.split(rgba)
    rgba_pil = cv2.merge([r,g,b,a])
    Image.fromarray(rgba_pil).save(os.path.join(out_dir, name))

def main():
     if len(sys.argv) < 2:
         print("Użycie: python main.py <katalog_z_obrazami> lub google:<zapytanie>")
         return
     arg = sys.argv[1]
     if arg.startswith("google:"):
         query = arg.split(":",1)[1]
         raw_dir = os.path.join(os.getcwd(), f"google_{query.replace(' ','_')}_raw")
         os.makedirs(raw_dir, exist_ok=True)
         print(f"[INFO] Pobieranie 10 obrazów dla zapytania '{query}' …")
         paths = fetch_images(query, raw_dir, 10)
         if not paths:
             print(f"[ERROR] Nie pobrano żadnych obrazów dla zapytania '{query}' – zakończenie.")
             return
         analyze_images(paths)
         src = raw_dir
     else:
         src = arg
     # Zmiana: używamy nazwy folderu wejściowego przy tworzeniu folderu wyjściowego
     folder_name = os.path.basename(os.path.normpath(src))
     out = os.path.join(os.getcwd(), "out", folder_name)
     os.makedirs(out, exist_ok=True)
     files = [f for f in glob.glob(os.path.join(src, "*.*")) if os.path.isfile(f)]
     for f in files:
         try:
             process_image(f, out)
         except Exception as e:
             print(f"[ERROR] podczas przetwarzania {f}: {e}")

if __name__ == "__main__":
    main()
