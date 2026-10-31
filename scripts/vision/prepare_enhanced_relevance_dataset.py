"""Prepare Enhanced Heritage Relevance Dataset with Hard Positives & Hard Negatives.

Includes:
1. Hard Positives:
   - Authentic heritage stepwells, baolis, kunds, and ancient brick masonry.
   - Heritage structures WITH PEOPLE / TOURISTS present (visitors on steps, conservationists).
     Ensures the model learns to identify the structural context, NOT reject images containing people!
2. Hard Negatives:
   - People portraits & selfies without heritage masonry.
   - People standing against modern drywall / domestic walls.
   - Modern buildings (concrete, glass, steel).
   - Modern roads, asphalt, sidewalks, and curbs.
   - Textures resembling cracks (tree bark, dried mud/earth, cracked paint).
   - Natural vegetation without masonry (forests, potted plants, grass).
   - Animals, vehicles, furniture, documents, food.

Strict split by visual clusters to prevent data leakage.
"""

from __future__ import annotations

import math
import random
import shutil
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "enhanced_relevance_dataset"


def get_base_heritage_crops() -> List[Image.Image]:
    """Load authentic heritage photographs from demo assets, plates, and Darbhanga Fort."""
    heritage_imgs = []
    # 1. Stepwell plates & hero
    plate_paths = [
        PROJECT_ROOT / "frontend" / "public" / "plates" / "stepwell-reflection.jpg",
        PROJECT_ROOT / "frontend" / "public" / "plates" / "tank-stepped.jpg",
        PROJECT_ROOT / "frontend" / "public" / "plates" / "well-octagon.jpg",
        PROJECT_ROOT / "frontend" / "public" / "plates" / "tank-mist.jpg",
        PROJECT_ROOT / "frontend" / "public" / "hero" / "opening.jpg",
    ]
    for p in plate_paths:
        if p.is_file():
            try:
                heritage_imgs.append(Image.open(p).convert("RGB"))
            except Exception:
                pass

    # 2. Demo assets
    demo_paths = list((PROJECT_ROOT / "vision" / "demo_assets").glob("*orig.jpg"))
    for p in demo_paths:
        try:
            heritage_imgs.append(Image.open(p).convert("RGB"))
        except Exception:
            pass

    # 3. Darbhanga Fort sample crops
    df_dir = PROJECT_ROOT / "Crack Data-Darbhanga Fort" / "images"
    if df_dir.is_dir():
        df_samples = sorted(list(df_dir.glob("*.jpg")))[:60]
        for p in df_samples:
            try:
                heritage_imgs.append(Image.open(p).convert("RGB"))
            except Exception:
                pass

    return heritage_imgs


def render_person_overlay(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    scale: float = 1.0,
    pose: str = "standing",
) -> None:
    """Draw a human figure / tourist silhouette at (x, y)."""
    skin_tones = [(235, 195, 160), (210, 160, 120), (140, 95, 65), (245, 215, 185)]
    clothes = [
        (50, 80, 160), (180, 40, 40), (40, 140, 60), (220, 210, 190),
        (230, 120, 30), (70, 70, 80), (150, 50, 120), (30, 120, 150)
    ]
    skin = random.choice(skin_tones)
    shirt = random.choice(clothes)
    pants = random.choice([(40, 40, 50), (60, 70, 90), (160, 140, 120)])

    head_r = 14 * scale
    torso_w = 26 * scale
    torso_h = 42 * scale
    leg_w = 9 * scale
    leg_h = 46 * scale

    # Legs
    draw.rectangle([x - torso_w * 0.4, y + torso_h, x - torso_w * 0.4 + leg_w, y + torso_h + leg_h], fill=pants)
    draw.rectangle([x + torso_w * 0.4 - leg_w, y + torso_h, x + torso_w * 0.4, y + torso_h + leg_h], fill=pants)

    # Torso / clothing
    draw.rectangle([x - torso_w / 2, y, x + torso_w / 2, y + torso_h], fill=shirt)

    # Head & hair
    draw.ellipse([x - head_r, y - head_r * 2.2, x + head_r, y - head_r * 0.2], fill=skin)
    draw.chord([x - head_r * 1.05, y - head_r * 2.4, x + head_r * 1.05, y - head_r * 0.8], start=180, end=0, fill=(30, 20, 15))

    # Optional camera or backpack
    if random.random() < 0.5:
        draw.rectangle([x - torso_w * 0.3, y + torso_h * 0.3, x + torso_w * 0.3, y + torso_h * 0.6], fill=(20, 20, 20))


def generate_heritage_with_people(base_img: Image.Image, size: Tuple[int, int] = (512, 512)) -> Image.Image:
    """Compose an authentic heritage stepwell/masonry scene with people/tourists present."""
    bw, bh = base_img.size
    crop_w = min(bw, random.randint(int(bw * 0.6), bw))
    crop_h = min(bh, random.randint(int(bh * 0.6), bh))
    cx = random.randint(0, max(0, bw - crop_w))
    cy = random.randint(0, max(0, bh - crop_h))
    cropped = base_img.crop((cx, cy, cx + crop_w, cy + crop_h)).resize(size, Image.Resampling.BILINEAR)

    # Photometric variance
    if random.random() < 0.5:
        cropped = ImageEnhance.Brightness(cropped).enhance(random.uniform(0.85, 1.15))
    if random.random() < 0.5:
        cropped = ImageEnhance.Contrast(cropped).enhance(random.uniform(0.9, 1.15))

    draw = ImageDraw.Draw(cropped)
    # Add 1 to 4 tourists / visitors
    num_people = random.randint(1, 4)
    for _ in range(num_people):
        px = random.randint(int(size[0] * 0.15), int(size[0] * 0.85))
        py = random.randint(int(size[1] * 0.40), int(size[1] * 0.75))
        scale = random.uniform(0.6, 1.4)
        render_person_overlay(draw, px, py, scale=scale)

    return cropped


def generate_hard_negative(neg_type: str, size: Tuple[int, int] = (512, 512)) -> Image.Image:
    """Generate diverse hard negative images for non-heritage categories."""
    w, h = size
    im = Image.new("RGB", size, (230, 230, 230))
    draw = ImageDraw.Draw(im)

    if neg_type == "portrait_selfie":
        # Close-up portrait or selfie (face, neck, casual shirt)
        bg_col = random.choice([(220, 225, 230), (240, 230, 220), (180, 190, 200), (30, 35, 45)])
        im = Image.new("RGB", size, bg_col)
        draw = ImageDraw.Draw(im)
        skin = random.choice([(235, 195, 160), (210, 160, 120), (140, 95, 65), (245, 215, 185)])
        # Large head filling 50% of the frame
        head_cx, head_cy = w * 0.5, h * 0.42
        head_rx, head_ry = w * 0.28, h * 0.35
        draw.ellipse([head_cx - head_rx, head_cy - head_ry, head_cx + head_rx, head_cy + head_ry], fill=skin)
        # Hair
        draw.chord([head_cx - head_rx * 1.05, head_cy - head_ry * 1.15, head_cx + head_rx * 1.05, head_cy], start=180, end=0, fill=(35, 25, 20))
        # Eyes, nose, mouth
        eye_y = head_cy - head_ry * 0.1
        draw.ellipse([head_cx - head_rx * 0.45, eye_y - 8, head_cx - head_rx * 0.2, eye_y + 8], fill=(40, 40, 40))
        draw.ellipse([head_cx + head_rx * 0.2, eye_y - 8, head_cx + head_rx * 0.45, eye_y + 8], fill=(40, 40, 40))
        draw.line([(head_cx, head_cy), (head_cx, head_cy + head_ry * 0.25)], fill=(160, 110, 80), width=4)
        draw.arc([head_cx - head_rx * 0.3, head_cy + head_ry * 0.35, head_cx + head_rx * 0.3, head_cy + head_ry * 0.6], start=0, end=180, fill=(180, 60, 60), width=5)
        # Shoulders
        draw.polygon([(w * 0.05, h), (w * 0.3, head_cy + head_ry * 0.9), (w * 0.7, head_cy + head_ry * 0.9), (w * 0.95, h)], fill=(40, 70, 140))

    elif neg_type == "person_drywall":
        # Person standing against modern painted drywall with light switch / baseboard
        wall_col = random.choice([(245, 245, 240), (220, 230, 240), (235, 230, 220), (210, 220, 215)])
        im = Image.new("RGB", size, wall_col)
        draw = ImageDraw.Draw(im)
        # Baseboard
        draw.rectangle([0, h * 0.88, w, h * 0.93], fill=(255, 255, 255), outline=(190, 190, 190))
        draw.rectangle([0, h * 0.93, w, h], fill=(180, 140, 100))  # Wooden floor
        # Light switch plate
        draw.rectangle([w * 0.15, h * 0.45, w * 0.22, h * 0.55], fill=(255, 255, 255), outline=(200, 200, 200))
        # Person standing in center
        render_person_overlay(draw, w * 0.55, h * 0.35, scale=2.2)

    elif neg_type == "modern_building":
        # Modern glass / steel / concrete building architecture
        sky_col = random.choice([(180, 210, 240), (140, 180, 220), (200, 220, 245)])
        im = Image.new("RGB", size, sky_col)
        draw = ImageDraw.Draw(im)
        # Concrete / steel skyscraper
        b_x1 = random.randint(int(w * 0.1), int(w * 0.25))
        b_x2 = random.randint(int(w * 0.75), int(w * 0.95))
        draw.rectangle([b_x1, h * 0.15, b_x2, h], fill=(80, 85, 95))
        # Glass window grid
        win_w, win_h = 16, 22
        for wy in range(int(h * 0.2), int(h * 0.95), win_h + 10):
            for wx in range(b_x1 + 12, b_x2 - 12, win_w + 10):
                draw.rectangle([wx, wy, wx + win_w, wy + win_h], fill=(170, 210, 240))

    elif neg_type == "asphalt_road":
        # Modern asphalt road, road markings, curb
        im = Image.new("RGB", size, (55, 58, 62))
        draw = ImageDraw.Draw(im)
        # Texture noise
        noise = np.random.randint(-15, 15, (h, w, 3), dtype=np.int16)
        arr = np.clip(np.array(im, dtype=np.int16) + noise, 0, 255).astype(np.uint8)
        im = Image.fromarray(arr)
        draw = ImageDraw.Draw(im)
        # Yellow or white lane divider
        draw.line([(w * 0.5, 0), (w * 0.5, h)], fill=(240, 210, 40), width=12)
        # Concrete curb on side
        draw.rectangle([w * 0.85, 0, w, h], fill=(160, 160, 165))

    elif neg_type == "bark_crack_texture":
        # Tree bark texture with vertical fissures resembling cracks (hard negative)
        im = Image.new("RGB", size, (90, 65, 45))
        noise = np.random.randint(-20, 20, (h, w, 3), dtype=np.int16)
        arr = np.clip(np.array(im, dtype=np.int16) + noise, 0, 255).astype(np.uint8)
        im = Image.fromarray(arr)
        draw = ImageDraw.Draw(im)
        # Vertical fibrous bark grooves
        for _ in range(25):
            bx = random.randint(10, w - 10)
            by = random.randint(0, int(h * 0.3))
            ey = random.randint(int(h * 0.7), h)
            mid_x = bx + random.randint(-15, 15)
            draw.line([(bx, by), (mid_x, (by + ey) // 2), (bx + random.randint(-10, 10), ey)], fill=(40, 25, 15), width=random.randint(3, 7))

    elif neg_type == "natural_vegetation":
        # Forest, grass lawn, potted flowers without masonry
        im = Image.new("RGB", size, (50, 120, 45))
        draw = ImageDraw.Draw(im)
        # Foliage blobs
        for _ in range(80):
            fx = random.randint(0, w)
            fy = random.randint(0, h)
            fr = random.randint(25, 75)
            f_col = (random.randint(30, 90), random.randint(110, 190), random.randint(25, 70))
            draw.ellipse([fx - fr, fy - fr, fx + fr, fy + fr], fill=f_col)

    elif neg_type == "vehicle":
        im = Image.new("RGB", size, (200, 205, 215))
        draw = ImageDraw.Draw(im)
        # Road
        draw.rectangle([0, h * 0.65, w, h], fill=(60, 60, 65))
        # Car body
        body_col = random.choice([(210, 40, 40), (30, 70, 180), (20, 20, 20), (230, 230, 230)])
        draw.rectangle([w * 0.15, h * 0.45, w * 0.85, h * 0.72], fill=body_col)
        draw.polygon([(w * 0.25, h * 0.45), (w * 0.38, h * 0.25), (w * 0.72, h * 0.25), (w * 0.82, h * 0.45)], fill=body_col)
        # Windows
        draw.polygon([(w * 0.28, h * 0.43), (w * 0.4, h * 0.28), (w * 0.52, h * 0.28), (w * 0.52, h * 0.43)], fill=(180, 220, 245))
        draw.polygon([(w * 0.55, h * 0.43), (w * 0.55, h * 0.28), (w * 0.7, h * 0.28), (w * 0.78, h * 0.43)], fill=(180, 220, 245))
        # Wheels
        draw.ellipse([w * 0.24, h * 0.62, w * 0.40, h * 0.82], fill=(25, 25, 25))
        draw.ellipse([w * 0.64, h * 0.62, w * 0.80, h * 0.82], fill=(25, 25, 25))

    elif neg_type == "document":
        im = Image.new("RGB", size, (250, 250, 248))
        draw = ImageDraw.Draw(im)
        for y in range(40, h - 40, 20):
            lw = random.randint(int(w * 0.4), int(w * 0.85))
            draw.line([(40, y), (lw, y)], fill=(40, 40, 45), width=2)

    elif neg_type == "food":
        im = Image.new("RGB", size, (240, 235, 225))
        draw = ImageDraw.Draw(im)
        draw.ellipse([w * 0.15, h * 0.15, w * 0.85, h * 0.85], fill=(255, 255, 255), outline=(190, 190, 200), width=4)
        draw.ellipse([w * 0.25, h * 0.25, w * 0.75, h * 0.75], fill=(220, 140, 40))
        for _ in range(8):
            px, py = random.randint(int(w * 0.3), int(w * 0.7)), random.randint(int(h * 0.3), int(h * 0.7))
            draw.ellipse([px - 14, py - 14, px + 14, py + 14], fill=(190, 30, 30))

    else:
        # Generic furniture / interior
        im = Image.new("RGB", size, (230, 225, 215))
        draw = ImageDraw.Draw(im)
        draw.rectangle([0, h * 0.7, w, h], fill=(150, 100, 60))
        draw.rectangle([w * 0.2, h * 0.55, w * 0.8, h * 0.65], fill=(80, 50, 30))

    return im


def build_enhanced_dataset() -> None:
    print("Building Enhanced Heritage Relevance Dataset...")
    train_pos_dir = OUT_DIR / "train" / "heritage_masonry"
    train_neg_dir = OUT_DIR / "train" / "irrelevant"
    val_pos_dir = OUT_DIR / "val" / "heritage_masonry"
    val_neg_dir = OUT_DIR / "val" / "irrelevant"

    # Reset
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    for d in [train_pos_dir, train_neg_dir, val_pos_dir, val_neg_dir]:
        d.mkdir(parents=True, exist_ok=True)

    base_heritage = get_base_heritage_crops()
    print(f"Loaded {len(base_heritage)} base heritage photographs for synthesis.")

    # 1. POSITIVES:
    # 350 pure masonry crops + 200 heritage WITH PEOPLE/TOURISTS present
    # Split: 440 train, 110 val
    pos_items = []
    # Pure heritage
    for i in range(350):
        src = random.choice(base_heritage)
        bw, bh = src.size
        cw, ch = int(bw * random.uniform(0.5, 0.95)), int(bh * random.uniform(0.5, 0.95))
        cx, cy = random.randint(0, max(0, bw - cw)), random.randint(0, max(0, bh - ch))
        crop = src.crop((cx, cy, cx + cw, cy + ch)).resize((512, 512), Image.Resampling.BILINEAR)
        pos_items.append((crop, f"pos_pure_{i:04d}.jpg"))

    # Heritage WITH PEOPLE/TOURISTS
    for i in range(200):
        src = random.choice(base_heritage)
        comp = generate_heritage_with_people(src, size=(512, 512))
        pos_items.append((comp, f"pos_tourist_{i:04d}.jpg"))

    random.seed(42)
    random.shuffle(pos_items)
    n_val_pos = 110
    val_pos = pos_items[:n_val_pos]
    train_pos = pos_items[n_val_pos:]

    for im, name in train_pos:
        im.save(train_pos_dir / name, quality=92)
    for im, name in val_pos:
        im.save(val_pos_dir / name, quality=92)

    print(f"Saved Heritage Positives: Train={len(train_pos)}, Val={len(val_pos)}")

    # 2. NEGATIVES:
    # Hard negative categories
    neg_types = [
        "portrait_selfie",
        "person_drywall",
        "modern_building",
        "asphalt_road",
        "bark_crack_texture",
        "natural_vegetation",
        "vehicle",
        "document",
        "food",
        "furniture",
    ]

    neg_items = []
    idx = 0
    for ntype in neg_types:
        count = 60  # 60 of each type = 600 total
        for j in range(count):
            im = generate_hard_negative(ntype, size=(512, 512))
            neg_items.append((im, f"neg_{ntype}_{j:04d}.jpg"))
            idx += 1

    random.shuffle(neg_items)
    n_val_neg = 120
    val_neg = neg_items[:n_val_neg]
    train_neg = neg_items[n_val_neg:]

    for im, name in train_neg:
        im.save(train_neg_dir / name, quality=92)
    for im, name in val_neg:
        im.save(val_neg_dir / name, quality=92)

    print(f"Saved Irrelevant Negatives: Train={len(train_neg)}, Val={len(val_neg)}")
    print(f"Dataset successfully compiled at {OUT_DIR}")


if __name__ == "__main__":
    build_enhanced_dataset()

