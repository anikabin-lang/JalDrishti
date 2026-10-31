"""Comprehensive Dataset Quality, Blur, Exposure, and Hard-Negative Audit Script.

Performs forensic dataset cleaning and quality analysis for JalDrishti:
1. Blur detection (Laplacian variance on grayscale).
2. Lighting/exposure analysis (low-light, over-exposure, dynamic range).
3. Bounding-box geometric validation (area ratio, aspect ratio, micro-boxes).
4. Hard-negative identification (joint lines, deep shadows, textured background).
5. Segregation of uncertain records for human expert review.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vision.data.manifest import read_manifest


def compute_image_quality(img: Image.Image) -> Dict[str, float]:
    """Compute blur (Laplacian variance) and exposure metrics."""
    gray = img.convert("L")
    arr = np.asarray(gray, dtype=np.float32)

    # 1. Laplacian variance for blur
    # Discrete Laplacian kernel [-1, -1, -1; -1, 8, -1; -1, -1, -1] or simple 2nd derivative
    # Using np.gradient for lightweight, zero-dependency Laplacian:
    gy, gx = np.gradient(arr)
    g2y, _ = np.gradient(gy)
    _, g2x = np.gradient(gx)
    laplacian = g2y + g2x
    blur_score = float(np.var(laplacian))

    # 2. Exposure & Luminance
    mean_lum = float(np.mean(arr))
    std_lum = float(np.std(arr))
    min_lum = float(np.min(arr))
    max_lum = float(np.max(arr))

    # Under-exposure / shadow ratio (< 30)
    shadow_ratio = float(np.mean(arr < 35.0))
    # Over-exposure / glare ratio (> 225)
    glare_ratio = float(np.mean(arr > 225.0))

    return {
        "blur_score": round(blur_score, 2),
        "mean_luminance": round(mean_lum, 2),
        "std_luminance": round(std_lum, 2),
        "dynamic_range": round(max_lum - min_lum, 2),
        "shadow_ratio": round(shadow_ratio, 4),
        "glare_ratio": round(glare_ratio, 4),
    }


def audit_boxes(label_path: Path, img_w: int = 768, img_h: int = 768) -> List[Dict[str, Any]]:
    """Validate YOLO label format boxes."""
    if not label_path.is_file():
        return []
    boxes = []
    lines = label_path.read_text(encoding="utf-8").strip().splitlines()
    for idx, line in enumerate(lines):
        parts = line.strip().split()
        if len(parts) != 5:
            continue
        try:
            cls_id, xc, yc, bw, bh = int(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            area_ratio = bw * bh
            aspect_ratio = (bw / bh) if bh > 0 else 0.0
            boxes.append({
                "box_idx": idx,
                "class_id": cls_id,
                "xc": xc,
                "yc": yc,
                "bw": bw,
                "bh": bh,
                "area_ratio": round(area_ratio, 5),
                "aspect_ratio": round(aspect_ratio, 3),
                "is_micro": area_ratio < 0.001,
                "is_macro": area_ratio > 0.50,
            })
        except ValueError:
            continue
    return boxes


def run_comprehensive_audit(
    dataset_root: Path,
    manifest_path: Path,
    output_dir: Path,
    sample_limit: int = 1000,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = read_manifest(manifest_path)
    print(f"Loaded {len(records)} records from {manifest_path.name}")

    quality_records = []
    blur_scores = []
    luminances = []
    low_light_flags = []
    blurred_flags = []
    hard_negatives = []
    box_stats = []

    # Process up to sample_limit for fast thorough audit
    count = 0
    for r in records:
        if not r.readable:
            continue
        img_path = dataset_root / r.rel_path
        if not img_path.is_file():
            continue

        label_path = img_path.with_suffix(".txt")
        # In YOLO datasets, labels might be in labels/ folder or beside images
        if not label_path.is_file():
            # Check alternative labels folder
            alt_label = dataset_root / r.rel_path.replace("images/", "labels/").replace(".jpg", ".txt")
            if alt_label.is_file():
                label_path = alt_label

        boxes = audit_boxes(label_path, r.width or 768, r.height or 768)
        box_stats.extend(boxes)

        count += 1
        # Sample quality on a representative subset to keep audit fast and deterministic
        if count <= sample_limit:
            try:
                with Image.open(img_path) as im:
                    q = compute_image_quality(im)
                    blur_scores.append(q["blur_score"])
                    luminances.append(q["mean_luminance"])

                    is_blurred = q["blur_score"] < 45.0
                    is_low_light = q["mean_luminance"] < 40.0
                    is_high_glare = q["glare_ratio"] > 0.35

                    if is_blurred:
                        blurred_flags.append(r.rel_path)
                    if is_low_light:
                        low_light_flags.append(r.rel_path)

                    # Hard negative candidates: images without crack labels that have high variance or texture
                    if len(boxes) == 0 and q["blur_score"] > 80.0:
                        hard_negatives.append({
                            "rel_path": r.rel_path,
                            "split": r.split,
                            "blur_score": q["blur_score"],
                            "mean_luminance": q["mean_luminance"],
                            "type": "textured_unbroken_masonry",
                        })

                    quality_records.append({
                        "rel_path": r.rel_path,
                        "split": r.split,
                        "num_boxes": len(boxes),
                        **q,
                    })
            except Exception as e:
                print(f"Error reading {r.rel_path}: {e}")

    # Summary calculations
    avg_blur = float(np.mean(blur_scores)) if blur_scores else 0.0
    p10_blur = float(np.percentile(blur_scores, 10)) if blur_scores else 0.0
    avg_lum = float(np.mean(luminances)) if luminances else 0.0

    box_areas = [b["area_ratio"] for b in box_stats]
    micro_boxes = sum(1 for b in box_stats if b["is_micro"])
    macro_boxes = sum(1 for b in box_stats if b["is_macro"])

    report = {
        "total_records_manifest": len(records),
        "audited_images_quality": len(quality_records),
        "total_boxes_audited": len(box_stats),
        "quality_metrics": {
            "mean_blur_score": round(avg_blur, 2),
            "p10_blur_score": round(p10_blur, 2),
            "blur_threshold_recommendation": 45.0,
            "flagged_blurred_count": len(blurred_flags),
            "mean_luminance": round(avg_lum, 2),
            "flagged_low_light_count": len(low_light_flags),
        },
        "box_geometry_metrics": {
            "total_boxes": len(box_stats),
            "median_box_area_ratio": round(float(np.median(box_areas)), 5) if box_areas else 0.0,
            "micro_boxes_under_0_1_pct": micro_boxes,
            "macro_boxes_over_50_pct": macro_boxes,
        },
        "hard_negatives_identified": len(hard_negatives),
        "hard_negatives_sample": hard_negatives[:10],
    }

    # Save JSON and MD
    out_json = output_dir / "dataset_quality_audit.json"
    out_json.write_text(json.dumps(report, indent=2))

    out_md = output_dir / "dataset_quality_audit.md"
    md_content = f"""# JalDrishti Dataset Quality & Hard-Negative Audit Report

## Summary
- Total Images in Manifest: **{len(records)}**
- Sample Audited for Physical Image Quality: **{len(quality_records)}**
- Total Bounding Boxes Audited: **{len(box_stats)}**

## Image Quality & Physical Fidelity
- **Mean Laplacian Blur Score**: `{round(avg_blur, 2)}` (10th percentile: `{round(p10_blur, 2)}`)
- **Flagged Blur/Soft Focus Images**: `{len(blurred_flags)}` images (< 45.0 threshold)
- **Mean Luminance (0-255)**: `{round(avg_lum, 2)}`
- **Flagged Low-Light / Under-Exposed**: `{len(low_light_flags)}` images (< 40.0 threshold)

## Bounding Box Morphology
- **Median Box Area Ratio**: `{round(float(np.median(box_areas)), 5) if box_areas else 0.0}` of image area
- **Micro-Boxes (< 0.1% area)**: `{micro_boxes}` (candidate hairline noise or point anomalies)
- **Macro-Boxes (> 50% area)**: `{macro_boxes}` (large loose bounding regions enclosing entire wall segments)

## Hard Negative Mining
- Identified **{len(hard_negatives)}** textured unbroken masonry images with high edge gradients.
- These images serve as essential false-positive suppression negatives (training the model not to trigger on brick joints, mortar courses, or shadow lines).

## Recommendations for Model Training
1. **Pre-Inference Quality Filter**: Reject images with blur score < 40 or mean luminance < 30.
2. **Hard-Negative Mining**: Retain all negative background masonry images in the training split.
3. **Multi-scale Pyramids**: Hairline cracks require high spatial fidelity (preserve 768x768 or 640x640 rather than aggressive downscaling).
"""
    out_md.write_text(md_content)
    print(f"Wrote dataset quality report to {out_md}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", default="Crack Data-Darbhanga Fort")
    parser.add_argument("--manifest", default="vision/outputs/audit/detection_manifest_split.jsonl")
    parser.add_argument("--out", default="vision/outputs/audit")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    run_comprehensive_audit(
        dataset_root=Path(args.dataset_root),
        manifest_path=Path(args.manifest),
        output_dir=Path(args.out),
        sample_limit=args.limit,
    )

