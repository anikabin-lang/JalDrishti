"""Prepare Multi-Class YOLO Benchmark Dataset (Crack + Vegetation).

Extracts and validates:
Class 0: crack (from verified Darbhanga Fort labels)
Class 1: vegetation (from Excess-Green biological colonization clusters)
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "Crack Data-Darbhanga Fort"
SPLIT_MANIFEST = PROJECT_ROOT / "vision" / "outputs" / "audit" / "detection_manifest_split.jsonl"
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "yolo_benchmark"


def extract_vegetation_box(img_path: Path) -> list[str]:
    """Extract vegetation bounding box if vegetative colonization exists."""
    boxes = []
    try:
        with Image.open(img_path) as im:
            arr = np.asarray(im, dtype=np.float32)
            exg = 2.0 * arr[:, :, 1] - arr[:, :, 0] - arr[:, :, 2]
            veg_mask = exg > 25.0
            veg_ratio = float(np.mean(veg_mask))
            if veg_ratio > 0.04:
                vy, vx = np.where(veg_mask)
                w, h = float(im.width), float(im.height)
                xmin, xmax = max(0.0, float(np.percentile(vx, 5))), min(w, float(np.percentile(vx, 95)))
                ymin, ymax = max(0.0, float(np.percentile(vy, 5))), min(h, float(np.percentile(vy, 95)))
                xc = (xmin + xmax) / 2.0 / w
                yc = (ymin + ymax) / 2.0 / h
                bw = max(0.02, (xmax - xmin) / w)
                bh = max(0.02, (ymax - ymin) / h)
                boxes.append(f"1 {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")
    except Exception:
        pass
    return boxes


def main():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for s in ("train", "val", "test"):
        (OUT_DIR / "images" / s).mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "labels" / s).mkdir(parents=True, exist_ok=True)

    with open(SPLIT_MANIFEST, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    counts = {"train": 0, "val": 0, "test": 0}
    crack_box_count = 0
    veg_box_count = 0

    print("Building multi-class YOLO benchmark dataset with symlinks & extracted vegetation...")
    for idx, r in enumerate(records):
        split = r.get("split")
        if not split or split not in counts:
            continue

        rel_path = r["rel_path"]
        src_img = RAW_ROOT / rel_path
        if not src_img.is_file():
            continue

        sample_name = f"{src_img.parent.name}_{src_img.name}"
        dst_img = OUT_DIR / "images" / split / sample_name
        if not dst_img.exists():
            dst_img.symlink_to(src_img)

        # Label resolution
        label_lines = []
        # Check label in labels/ directory first
        cand_label = src_img.parent.parent / "labels" / f"{src_img.stem}.txt"
        if not cand_label.is_file():
            cand_label = src_img.with_suffix(".txt")

        if cand_label.is_file():
            raw_lines = cand_label.read_text(encoding="utf-8").strip().splitlines()
            for l in raw_lines:
                parts = l.strip().split()
                if len(parts) == 5:
                    label_lines.append(f"0 {parts[1]} {parts[2]} {parts[3]} {parts[4]}")
                    crack_box_count += 1

        # Extract vegetation
        veg_lines = extract_vegetation_box(src_img)
        label_lines.extend(veg_lines)
        veg_box_count += len(veg_lines)

        dst_label = OUT_DIR / "labels" / split / f"{dst_img.stem}.txt"
        dst_label.write_text("\n".join(label_lines) + ("\n" if label_lines else ""))
        counts[split] += 1

    print(f"Dataset summary:")
    print(f"  Images per split: {counts}")
    print(f"  Total crack boxes: {crack_box_count}")
    print(f"  Total vegetation boxes: {veg_box_count}")

    yaml_content = f"""# JalDrishti Multi-Class Heritage Defect Benchmark Dataset
path: {OUT_DIR.resolve()}
train: images/train
val: images/val
test: images/test

names:
  0: crack
  1: vegetation
"""
    yaml_path = OUT_DIR / "heritage_defect.yaml"
    yaml_path.write_text(yaml_content)
    print(f"Dataset YAML written to {yaml_path}")


if __name__ == "__main__":
    main()
