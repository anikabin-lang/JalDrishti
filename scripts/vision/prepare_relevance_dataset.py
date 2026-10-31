"""Prepare Heritage Image Relevance Classification Dataset.

Builds a balanced, leakage-safe dataset with:
- Positive Class (1: heritage_masonry): Real Indian heritage stepwells, ancient brick masonry, stone structures, weathered mortar.
- Negative Class (0: irrelevant): People, vehicles, animals, food, household furniture, documents, modern smooth walls, open nature.
"""

from __future__ import annotations

import json
import math
import random
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "relevance_dataset"


def generate_synthetic_negative(idx: int, neg_type: str, size: tuple[int, int] = (512, 512)) -> Image.Image:
    """Generate distinct, realistic synthetic negative images for various irrelevant categories."""
    im = Image.new("RGB", size, (240, 240, 240))
    draw = ImageDraw.Draw(im)
    w, h = size

    if neg_type == "vehicle":
        # Vehicle / car silhouette with metallic sheen, wheels, headlights
        im = Image.new("RGB", size, (random.randint(180, 220), random.randint(180, 220), random.randint(200, 240)))
        draw = ImageDraw.Draw(im)
        body_color = random.choice([(200, 30, 30), (30, 60, 180), (30, 30, 30), (220, 220, 220)])
        # Car body
        draw.rectangle([w * 0.15, h * 0.45, w * 0.85, h * 0.75], fill=body_color)
        draw.polygon([(w * 0.25, h * 0.45), (w * 0.4, h * 0.25), (w * 0.7, h * 0.25), (w * 0.8, h * 0.45)], fill=body_color)
        # Windows
        draw.polygon([(w * 0.28, h * 0.43), (w * 0.41, h * 0.28), (w * 0.52, h * 0.28), (w * 0.52, h * 0.43)], fill=(180, 220, 240))
        draw.polygon([(w * 0.55, h * 0.43), (w * 0.55, h * 0.28), (w * 0.68, h * 0.28), (w * 0.76, h * 0.43)], fill=(180, 220, 240))
        # Wheels
        draw.ellipse([w * 0.25, h * 0.65, w * 0.4, h * 0.85], fill=(20, 20, 20))
        draw.ellipse([w * 0.65, h * 0.65, w * 0.8, h * 0.85], fill=(20, 20, 20))

    elif neg_type == "person":
        # Human figure / portrait silhouette with skin tone, clothing
        skin_tone = random.choice([(235, 195, 160), (210, 160, 120), (140, 95, 65), (245, 215, 185)])
        cloth_color = random.choice([(50, 80, 160), (180, 40, 40), (40, 140, 60), (30, 30, 40)])
        # Background
        im = Image.new("RGB", size, (random.randint(210, 245), random.randint(210, 245), random.randint(210, 245)))
        draw = ImageDraw.Draw(im)
        # Head
        draw.ellipse([w * 0.35, h * 0.15, w * 0.65, h * 0.45], fill=skin_tone)
        # Hair
        draw.chord([w * 0.33, h * 0.12, w * 0.67, h * 0.35], start=180, end=0, fill=(30, 20, 15))
        # Torso / shoulders
        draw.polygon([(w * 0.15, h * 0.95), (w * 0.3, h * 0.48), (w * 0.7, h * 0.48), (w * 0.85, h * 0.95)], fill=cloth_color)

    elif neg_type == "furniture":
        # Modern room, table, chair, laptop / monitor
        im = Image.new("RGB", size, (230, 225, 215))
        draw = ImageDraw.Draw(im)
        # Floor
        draw.rectangle([0, h * 0.7, w, h], fill=(160, 110, 70))
        # Desk
        draw.rectangle([w * 0.2, h * 0.55, w * 0.8, h * 0.65], fill=(80, 50, 30))
        draw.rectangle([w * 0.25, h * 0.65, w * 0.28, h * 0.85], fill=(60, 40, 25))
        draw.rectangle([w * 0.72, h * 0.65, w * 0.75, h * 0.85], fill=(60, 40, 25))
        # Monitor
        draw.rectangle([w * 0.38, h * 0.35, w * 0.62, h * 0.55], fill=(20, 20, 20))
        draw.rectangle([w * 0.4, h * 0.37, w * 0.6, h * 0.53], fill=(70, 130, 220))
        draw.rectangle([w * 0.48, h * 0.55, w * 0.52, h * 0.58], fill=(40, 40, 40))

    elif neg_type == "document":
        # Scanned invoice, paper document, printed text rows
        im = Image.new("RGB", size, (250, 250, 248))
        draw = ImageDraw.Draw(im)
        for y in range(40, h - 40, 18):
            line_w = random.randint(int(w * 0.4), int(w * 0.85))
            draw.line([(40, y), (line_w, y)], fill=(40, 40, 45), width=2)
            if random.random() < 0.2:
                # Table column line
                draw.line([(w * 0.5, y - 6), (w * 0.5, y + 6)], fill=(120, 120, 120), width=1)

    elif neg_type == "food":
        # Plate with food / fruits / pizza
        im = Image.new("RGB", size, (235, 230, 220))
        draw = ImageDraw.Draw(im)
        # Plate
        draw.ellipse([w * 0.15, h * 0.15, w * 0.85, h * 0.85], fill=(245, 245, 250), outline=(200, 200, 210), width=4)
        # Food items
        draw.ellipse([w * 0.25, h * 0.25, w * 0.75, h * 0.75], fill=(210, 130, 40))
        for _ in range(8):
            px = random.randint(int(w * 0.3), int(w * 0.7))
            py = random.randint(int(h * 0.3), int(h * 0.7))
            draw.ellipse([px - 15, py - 15, px + 15, py + 15], fill=(180, 30, 30))

    elif neg_type == "modern_drywall":
        # Flat painted drywall without masonry joints or texture (difficult negative)
        color = random.choice([(230, 235, 240), (240, 235, 225), (210, 215, 220), (190, 205, 215)])
        arr = np.ones((h, w, 3), dtype=np.float32) * np.array(color, dtype=np.float32)
        # Add subtle paint roller stipple noise
        noise = np.random.normal(0, 3.0, (h, w, 3))
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        im = Image.fromarray(arr)

    elif neg_type == "open_landscape":
        # Natural sky + grass meadow without built structures
        im = Image.new("RGB", size, (135, 195, 245))
        draw = ImageDraw.Draw(im)
        # Hills / meadow
        draw.polygon([(0, h * 0.5), (w * 0.4, h * 0.45), (w * 0.8, h * 0.48), (w, h * 0.42), (w, h), (0, h)], fill=(80, 160, 40))
        # Sun
        draw.ellipse([w * 0.75, h * 0.1, w * 0.9, h * 0.25], fill=(255, 235, 120))

    return im


def prepare_dataset(num_pos_train: int = 400, num_neg_train: int = 400, num_val_each: int = 80) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val"):
        for cls_name in ("heritage_masonry", "irrelevant"):
            (OUT_DIR / split / cls_name).mkdir(parents=True, exist_ok=True)

    # 1. Harvest positive heritage masonry images
    train_source = PROJECT_ROOT / "Crack Data-Darbhanga Fort" / "train" / "images"
    val_source = PROJECT_ROOT / "Crack Data-Darbhanga Fort" / "val" / "images"

    pos_train_candidates = list(train_source.glob("*.jpg"))
    pos_val_candidates = list(val_source.glob("*.jpg"))

    random.seed(42)
    random.shuffle(pos_train_candidates)
    random.shuffle(pos_val_candidates)

    print(f"Sampling {num_pos_train} positive train images...")
    for idx, p in enumerate(pos_train_candidates[:num_pos_train]):
        dst = OUT_DIR / "train" / "heritage_masonry" / f"pos_train_{idx:04d}.jpg"
        shutil.copy2(p, dst)

    print(f"Sampling {num_val_each} positive val images...")
    for idx, p in enumerate(pos_val_candidates[:num_val_each]):
        dst = OUT_DIR / "val" / "heritage_masonry" / f"pos_val_{idx:04d}.jpg"
        shutil.copy2(p, dst)

    # Add demo stepwell assets to validation to ensure baoli generalization
    demo_dir = PROJECT_ROOT / "vision" / "demo_assets"
    for demo_p in demo_dir.glob("*_orig.jpg"):
        dst = OUT_DIR / "val" / "heritage_masonry" / f"stepwell_{demo_p.name}"
        shutil.copy2(demo_p, dst)

    # 2. Generate balanced negative samples across all irrelevant categories
    neg_categories = [
        "vehicle",
        "person",
        "furniture",
        "document",
        "food",
        "modern_drywall",
        "open_landscape",
    ]

    print(f"Generating {num_neg_train} negative train images...")
    for idx in range(num_neg_train):
        cat = neg_categories[idx % len(neg_categories)]
        img = generate_synthetic_negative(idx, cat)
        img.save(OUT_DIR / "train" / "irrelevant" / f"neg_train_{idx:04d}_{cat}.jpg", quality=90)

    print(f"Generating {num_val_each} negative val images...")
    for idx in range(num_val_each):
        cat = neg_categories[idx % len(neg_categories)]
        img = generate_synthetic_negative(idx, cat)
        img.save(OUT_DIR / "val" / "irrelevant" / f"neg_val_{idx:04d}_{cat}.jpg", quality=90)

    summary = {
        "train": {
            "heritage_masonry": len(list((OUT_DIR / "train" / "heritage_masonry").glob("*.jpg"))),
            "irrelevant": len(list((OUT_DIR / "train" / "irrelevant").glob("*.jpg"))),
        },
        "val": {
            "heritage_masonry": len(list((OUT_DIR / "val" / "heritage_masonry").glob("*.jpg"))),
            "irrelevant": len(list((OUT_DIR / "val" / "irrelevant").glob("*.jpg"))),
        },
        "negative_categories": neg_categories,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print("Dataset preparation complete:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    prepare_dataset()

