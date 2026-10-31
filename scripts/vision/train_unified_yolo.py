#!/usr/bin/env python3
"""Train/Fine-tune YOLO26n on Unified Heritage Defect Dataset (Crack + Vegetation).

Classes:
  0: crack
  1: vegetation

Hardware: MPS (Apple Silicon) if available, else CPU.
Saves model to: vision/models/damage_detector_yolo26n_unified/
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path
import torch
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_YAML = PROJECT_ROOT / "data" / "processed" / "unified_heritage_dataset" / "dataset.yaml"
OUTPUT_DIR = PROJECT_ROOT / "vision" / "models" / "damage_detector_yolo26n_unified"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    print("=" * 70)
    print("PHASE 3: TRAINING YOLO26n ON UNIFIED HERITAGE DEFECT DATASET")
    print("=" * 70)

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Hardware accelerator: {device}")

    # Use pretrained yolo26n or yolo11n base
    base_weights = PROJECT_ROOT / "yolo26n.pt"
    if not base_weights.exists():
        base_weights = PROJECT_ROOT / "yolo11n.pt"
    print(f"Base weights: {base_weights}")

    model = YOLO(str(base_weights))

    print(f"Starting training on {DATASET_YAML} for 5 epochs...")
    t0 = time.time()
    results = model.train(
        data=str(DATASET_YAML),
        epochs=5,
        imgsz=512,
        batch=16,
        device=device,
        workers=4,
        project=str(OUTPUT_DIR / "runs"),
        name="unified_yolo26n",
        exist_ok=True,
        save=True,
        verbose=True,
        patience=3,
    )
    t_train = time.time() - t0
    print(f"\nTraining completed in {t_train / 60:.2f} minutes.")

    # Save best weights to target directory
    best_pt = OUTPUT_DIR / "runs" / "unified_yolo26n" / "weights" / "best.pt"
    target_pt = OUTPUT_DIR / "model.pt"
    if best_pt.exists():
        shutil.copy2(best_pt, target_pt)
        print(f"Copied best model weights to: {target_pt}")

    # Evaluate on validation/test set
    print("\nEvaluating on validation split...")
    metrics = model.val(data=str(DATASET_YAML), split="val", imgsz=512, device=device)
    
    val_summary = {
        "mAP50": float(metrics.box.map50),
        "mAP50_95": float(metrics.box.map),
        "precision": float(metrics.box.mp),
        "recall": float(metrics.box.mr),
        "training_time_seconds": round(t_train, 2),
        "classes": ["crack", "vegetation"],
    }
    print(f"Validation mAP@50:    {val_summary['mAP50']:.4f}")
    print(f"Validation mAP@50-95: {val_summary['mAP50_95']:.4f}")
    print(f"Validation Precision: {val_summary['precision']:.4f}")
    print(f"Validation Recall:    {val_summary['recall']:.4f}")

    eval_json = OUTPUT_DIR / "eval_val.json"
    eval_json.write_text(json.dumps(val_summary, indent=2))
    print(f"Saved evaluation metrics to: {eval_json}")


if __name__ == "__main__":
    main()

