#!/usr/bin/env python3
"""Phase 2: Prepare Reproducible Unified Heritage Defect Dataset.

Combines:
1. Crack Data-Darbhanga Fort (brick masonry cracks + background masonry)
2. Historic_Place_Dataset (Living plant vegetation on historic masonry)
3. YTU-CrackIS (high-resolution crack polygon segmentations & boxes)
4. Historical Building Cracks (historical masonry crack close-ups & clean masonry negatives)

Target Taxonomy:
  Class 0: crack
  Class 1: vegetation

Outputs:
  - data/processed/unified_heritage_dataset/
      images/train/, images/val/, images/test/
      labels/train/, labels/val/, labels/test/ (YOLO format: bbox or polygon)
      manifests/train.jsonl, val.jsonl, test.jsonl (PyTorch / Faster R-CNN format with boxes & polygons)
      dataset.yaml (Ultralytics / YOLO format)
"""

from __future__ import annotations

import json
import os
import random
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "unified_heritage_dataset"

SEED = 42
random.seed(SEED)


def ensure_dirs() -> dict[str, Path]:
    paths = {
        "images_train": OUTPUT_DIR / "images" / "train",
        "images_val": OUTPUT_DIR / "images" / "val",
        "images_test": OUTPUT_DIR / "images" / "test",
        "labels_train": OUTPUT_DIR / "labels" / "train",
        "labels_val": OUTPUT_DIR / "labels" / "val",
        "labels_test": OUTPUT_DIR / "labels" / "test",
        "manifests": OUTPUT_DIR / "manifests",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def polygon_to_bbox(coords: list[float], img_w: int, img_h: int) -> tuple[float, float, float, float]:
    """Convert normalized [x1, y1, x2, y2, ...] to pixel [xmin, ymin, xmax, ymax]."""
    xs = coords[0::2]
    ys = coords[1::2]
    xmin = min(xs) * img_w
    xmax = max(xs) * img_w
    ymin = min(ys) * img_h
    ymax = max(ys) * img_h
    return max(0.0, xmin), max(0.0, ymin), min(float(img_w), xmax), min(float(img_h), ymax)


def yolo_bbox_to_pixels(xc: float, yc: float, w: float, h: float, img_w: int, img_h: int) -> tuple[float, float, float, float]:
    """Convert normalized xc, yc, w, h to pixel [xmin, ymin, xmax, ymax]."""
    xmin = (xc - w / 2.0) * img_w
    xmax = (xc + w / 2.0) * img_w
    ymin = (yc - h / 2.0) * img_h
    ymax = (yc + h / 2.0) * img_h
    return max(0.0, xmin), max(0.0, ymin), min(float(img_w), xmax), min(float(img_h), ymax)


def process_darbhanga(dirs: dict[str, Path], manifest_records: dict[str, list]) -> None:
    print("Processing Darbhanga Fort dataset...")
    darb_root = PROJECT_ROOT / "Crack Data-Darbhanga Fort"
    
    # Process train, val, test
    for split in ["train", "val", "test"]:
        src_split = darb_root / split
        img_dir = src_split / "images" if (src_split / "images").exists() else src_split
        lbl_dir = src_split / "labels" if (src_split / "labels").exists() else src_split

        images = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.jpeg")) + list(img_dir.glob("*.png"))
        print(f"  Darbhanga {split}: {len(images)} images")

        for img_p in images:
            out_split = split
            # Generate deterministic unique target name
            target_name = f"darb_{split}_{img_p.name}"
            target_img_p = dirs[f"images_{out_split}"] / target_name
            target_lbl_p = dirs[f"labels_{out_split}"] / f"{target_img_p.stem}.txt"

            # Check if matching label exists
            src_lbl = lbl_dir / f"{img_p.stem}.txt"
            label_lines = []
            boxes_pixel = []

            try:
                with Image.open(img_p) as pil_img:
                    w, h = pil_img.size
            except Exception:
                continue

            if src_lbl.exists():
                for line in src_lbl.read_text().splitlines():
                    parts = line.strip().split()
                    if not parts:
                        continue
                    # Darbhanga class 0 is crack
                    if len(parts) == 5:
                        xc, yc, bw, bh = map(float, parts[1:])
                        # Class 0: crack
                        label_lines.append(f"0 {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
                        xmin, ymin, xmax, ymax = yolo_bbox_to_pixels(xc, yc, bw, bh, w, h)
                        boxes_pixel.append({
                            "class_id": 1,  # 1 for Faster R-CNN (0 is background)
                            "class_name": "crack",
                            "bbox": [round(xmin, 1), round(ymin, 1), round(xmax, 1), round(ymax, 1)],
                        })

            # Copy image
            shutil.copy2(img_p, target_img_p)
            # Write label file (even if empty, indicates verified background image)
            target_lbl_p.write_text("\n".join(label_lines) + ("\n" if label_lines else ""))

            manifest_records[out_split].append({
                "image_path": str(target_img_p.relative_to(PROJECT_ROOT)),
                "width": w,
                "height": h,
                "dataset": "darbhanga_fort",
                "objects": boxes_pixel,
                "is_background": len(boxes_pixel) == 0,
            })


def process_historic_place(dirs: dict[str, Path], manifest_records: dict[str, list]) -> None:
    print("Processing Historic_Place_Dataset (Vegetation & Masonry)...")
    h_root = PROJECT_ROOT / "Historic_Place_Dataset"
    xml_dir = h_root / "xml_file_annotation"

    # Index all category images
    cat_images = {}
    for cat in ["Living plant", "Corroded brick", "Corroded plaster", "Fungus", "Artistic"]:
        for f in (h_root / cat).glob("*.*"):
            if f.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                cat_images[f.stem] = (cat, f)

    xml_files = sorted(list(xml_dir.glob("*.xml")))
    print(f"  Historic Place XMLs: {len(xml_files)}")

    # Split: 70% train, 15% val, 15% test
    for idx, xml_p in enumerate(xml_files):
        stem = xml_p.stem
        if stem not in cat_images:
            continue
        cat_name, img_p = cat_images[stem]

        if idx % 10 < 7:
            out_split = "train"
        elif idx % 10 < 8:
            out_split = "val"
        else:
            out_split = "test"

        try:
            tree = ET.parse(xml_p)
            root = tree.getroot()
            size = root.find("size")
            w = int(size.find("width").text)
            h = int(size.find("height").text)
        except Exception:
            continue

        label_lines = []
        boxes_pixel = []

        for obj in root.findall("object"):
            name = obj.find("name").text
            bnd = obj.find("bndbox")
            xmin = float(bnd.find("xmin").text)
            ymin = float(bnd.find("ymin").text)
            xmax = float(bnd.find("xmax").text)
            ymax = float(bnd.find("ymax").text)

            # Map Living plant -> vegetation (Class 1)
            if "plant" in name.lower() or name == "Living plant":
                xc = ((xmin + xmax) / 2.0) / w
                yc = ((ymin + ymax) / 2.0) / h
                bw = (xmax - xmin) / w
                bh = (ymax - ymin) / h
                label_lines.append(f"1 {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
                boxes_pixel.append({
                    "class_id": 2,  # 2 for Faster R-CNN (0: bg, 1: crack, 2: vegetation)
                    "class_name": "vegetation",
                    "bbox": [round(xmin, 1), round(ymin, 1), round(xmax, 1), round(ymax, 1)],
                })

        if not label_lines:
            continue

        target_name = f"histplace_{stem}.jpg"
        target_img_p = dirs[f"images_{out_split}"] / target_name
        target_lbl_p = dirs[f"labels_{out_split}"] / f"{target_img_p.stem}.txt"

        shutil.copy2(img_p, target_img_p)
        target_lbl_p.write_text("\n".join(label_lines) + "\n")

        manifest_records[out_split].append({
            "image_path": str(target_img_p.relative_to(PROJECT_ROOT)),
            "width": w,
            "height": h,
            "dataset": "historic_place_dataset",
            "objects": boxes_pixel,
            "is_background": False,
        })


def process_ytu_crackis(dirs: dict[str, Path], manifest_records: dict[str, list], max_samples_per_split: int = 400) -> None:
    print(f"Processing YTU-CrackIS (Polygon Crack Segmentations, balanced {max_samples_per_split} per split)...")
    ytu_root = PROJECT_ROOT / "YTU-CrackIS"

    # Mapping splits: train2017 -> train, val2017 -> val & test
    for src_split, out_splits in [("train2017", ["train"]), ("val2017", ["val", "test"])]:
        img_dir = ytu_root / "images" / src_split
        lbl_dir = ytu_root / "labels" / src_split

        img_files = sorted(list(img_dir.glob("*.JPG")) + list(img_dir.glob("*.jpg")))
        random.shuffle(img_files)
        selected_imgs = img_files[:max_samples_per_split * len(out_splits)]

        for idx, img_p in enumerate(selected_imgs):
            out_split = out_splits[idx % len(out_splits)]
            lbl_p = lbl_dir / f"{img_p.stem}.txt"
            if not lbl_p.exists():
                continue

            try:
                with Image.open(img_p) as pil_img:
                    w, h = pil_img.size
            except Exception:
                continue

            target_name = f"ytu_{src_split}_{img_p.name}"
            target_img_p = dirs[f"images_{out_split}"] / target_name
            target_lbl_p = dirs[f"labels_{out_split}"] / f"{target_img_p.stem}.txt"

            label_lines = []
            boxes_pixel = []

            for line in lbl_p.read_text().splitlines():
                parts = line.strip().split()
                if not parts:
                    continue
                # YOLO polygon format: 0 x1 y1 x2 y2 ... xn yn
                label_lines.append(line.strip())
                if len(parts) >= 5:
                    coords = list(map(float, parts[1:]))
                    xmin, ymin, xmax, ymax = polygon_to_bbox(coords, w, h)
                    boxes_pixel.append({
                        "class_id": 1,  # 1 for Faster R-CNN (0: bg, 1: crack)
                        "class_name": "crack",
                        "bbox": [round(xmin, 1), round(ymin, 1), round(xmax, 1), round(ymax, 1)],
                        "polygon": coords,
                    })

            shutil.copy2(img_p, target_img_p)
            target_lbl_p.write_text("\n".join(label_lines) + "\n")

            manifest_records[out_split].append({
                "image_path": str(target_img_p.relative_to(PROJECT_ROOT)),
                "width": w,
                "height": h,
                "dataset": "ytu_crackis",
                "objects": boxes_pixel,
                "is_background": len(boxes_pixel) == 0,
            })


def main() -> None:
    print("=" * 70)
    print("PHASE 2: PREPARING UNIFIED HERITAGE DEFECT DATASET")
    print("=" * 70)

    dirs = ensure_dirs()
    manifest_records = {"train": [], "val": [], "test": []}

    process_darbhanga(dirs, manifest_records)
    process_historic_place(dirs, manifest_records)
    process_ytu_crackis(dirs, manifest_records, max_samples_per_split=350)

    # Write manifests
    for split in ["train", "val", "test"]:
        manifest_path = dirs["manifests"] / f"manifest_{split}.jsonl"
        with open(manifest_path, "w", encoding="utf-8") as f:
            for rec in manifest_records[split]:
                f.write(json.dumps(rec) + "\n")
        print(f"Wrote {len(manifest_records[split])} records to {manifest_path}")

    # Write dataset.yaml for YOLO / Ultralytics
    yaml_content = f"""# JalDrishti Unified Heritage Defect Dataset
path: {OUTPUT_DIR.resolve()}
train: images/train
val: images/val
test: images/test

names:
  0: crack
  1: vegetation
"""
    yaml_path = OUTPUT_DIR / "dataset.yaml"
    yaml_path.write_text(yaml_content)
    print(f"Wrote Ultralytics config to {yaml_path}")

    print("\nDataset unification complete!")
    print(f"Train images: {len(manifest_records['train'])}")
    print(f"Val images:   {len(manifest_records['val'])}")
    print(f"Test images:  {len(manifest_records['test'])}")


if __name__ == "__main__":
    main()

