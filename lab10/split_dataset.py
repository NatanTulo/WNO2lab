import os, shutil, random, glob

# ścieżki
OUT_DIR = 'out'
SPLIT_DIR = 'dataset'
SETS = {'train': 0.7, 'val': 0.2, 'test': 0.1}

# przygotuj katalogi
for s in SETS:
    os.makedirs(f"{SPLIT_DIR}/{s}/images", exist_ok=True)
    os.makedirs(f"{SPLIT_DIR}/{s}/labels", exist_ok=True)

# zbierz wszystkie pary obraz–etykieta
pairs = []
for cat in os.listdir(OUT_DIR):
    img_dir = os.path.join(OUT_DIR, cat, 'synthetic')
    lbl_dir = os.path.join(OUT_DIR, cat, 'yolo')
    for img_path in glob.glob(f"{img_dir}/*.jpg"):
        lbl_path = os.path.join(lbl_dir, os.path.basename(img_path).replace('.jpg','.txt'))
        if os.path.isfile(lbl_path):
            pairs.append((img_path, lbl_path))

random.shuffle(pairs)
n = len(pairs)
idx = 0
for s, frac in SETS.items():
    cnt = int(n * frac) if s!='test' else n - idx
    for img_path, lbl_path in pairs[idx:idx+cnt]:
        dst_img = f"{SPLIT_DIR}/{s}/images/{os.path.basename(img_path)}"
        dst_lbl = f"{SPLIT_DIR}/{s}/labels/{os.path.basename(lbl_path)}"
        shutil.copy(img_path, dst_img)
        shutil.copy(lbl_path, dst_lbl)
    idx += cnt
print(f"Podział: train={int(n*SETS['train'])}, val={int(n*SETS['val'])}, test={n-idx+cnt}")
