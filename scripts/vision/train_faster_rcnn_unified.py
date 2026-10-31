#!/usr/bin/env python3
"""Phase 3A: Fine-tune Faster R-CNN MobileNetV3-Large FPN on Unified Heritage Crack Dataset.

Starts from existing checkpoint: vision/models/crack_detector_pilot_v1/model.pt
Dataset: data/processed/unified_heritage_dataset/manifests/manifest_train.jsonl
Evaluates on: data/processed/unified_heritage_dataset/manifests/manifest_val.jsonl
Outputs to: vision/models/crack_detector_v2_unified/model.pt
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision.models.detection import fasterrcnn_mobilenet_v3_large_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.transforms.functional import pil_to_tensor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_CKPT = PROJECT_ROOT / "vision" / "models" / "crack_detector_pilot_v1" / "model.pt"
UNIFIED_DIR = PROJECT_ROOT / "data" / "processed" / "unified_heritage_dataset"
OUTPUT_DIR = PROJECT_ROOT / "vision" / "models" / "crack_detector_v2_unified"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class UnifiedDetectionDataset(Dataset):
    def __init__(self, manifest_file: Path, max_samples: int = 1500, is_train: bool = True):
        self.is_train = is_train
        self.items = []
        with open(manifest_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        # Filter crack items and verified background masonry
        crack_or_bg = [r for r in lines if any(obj["class_name"] == "crack" for obj in r["objects"]) or r.get("is_background")]
        random.seed(42)
        random.shuffle(crack_or_bg)
        self.items = crack_or_bg[:max_samples]

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Dict[str, torch.Tensor], str]:
        rec = self.items[idx]
        img_p = PROJECT_ROOT / rec["image_path"]
        with Image.open(img_p) as pil_img:
            img = pil_img.convert("RGB")
        w, h = img.size

        boxes = []
        labels = []
        for obj in rec["objects"]:
            if obj["class_name"] == "crack":
                bx = obj["bbox"]
                # Ensure valid box dimensions
                if bx[2] > bx[0] and bx[3] > bx[1]:
                    boxes.append(bx)
                    labels.append(1)  # 1: crack (0 is background in torchvision)

        if not boxes:
            boxes_tensor = torch.zeros((0, 4), dtype=torch.float32)
            labels_tensor = torch.zeros((0,), dtype=torch.int64)
        else:
            boxes_tensor = torch.as_tensor(boxes, dtype=torch.float32)
            labels_tensor = torch.as_tensor(labels, dtype=torch.int64)

        # Basic horizontal flip augmentation for training
        tensor_img = pil_to_tensor(img).float() / 255.0
        if self.is_train and random.random() < 0.5:
            tensor_img = tensor_img.flip(-1)
            if len(boxes_tensor) > 0:
                boxes_tensor[:, [0, 2]] = w - boxes_tensor[:, [2, 0]]

        target = {
            "boxes": boxes_tensor,
            "labels": labels_tensor,
            "image_id": torch.tensor([idx]),
        }
        return tensor_img, target, rec["image_path"]


def collate_fn(batch):
    return tuple(zip(*batch))


def compute_iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0


def evaluate_val(model, val_loader, device, score_thresh: float = 0.55):
    model.eval()
    tp, fp, fn = 0, 0, 0
    with torch.inference_mode():
        for imgs, targets, _ in val_loader:
            imgs = [img.to(device) for img in imgs]
            preds = model(imgs)

            for pred, target in zip(preds, targets):
                p_boxes = pred["boxes"].cpu().numpy()
                p_scores = pred["scores"].cpu().numpy()
                gt_boxes = target["boxes"].numpy()

                keep = p_scores >= score_thresh
                p_boxes = p_boxes[keep]

                matched_gt = set()
                for pb in p_boxes:
                    hit = False
                    for gi, gb in enumerate(gt_boxes):
                        if gi not in matched_gt and compute_iou(pb, gb) >= 0.50:
                            hit = True
                            matched_gt.add(gi)
                            break
                    if hit:
                        tp += 1
                    else:
                        fp += 1
                fn += len(gt_boxes) - len(matched_gt)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def main():
    print("=" * 70)
    print("PHASE 3A: FINE-TUNING FASTER R-CNN ON UNIFIED DATASET")
    print("=" * 70)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}")

    # Build model architecture (MobileNetV3-Large FPN)
    model = fasterrcnn_mobilenet_v3_large_fpn(min_size=512, max_size=512)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes=2)  # 0: bg, 1: crack

    # Load baseline weights if available
    if BASELINE_CKPT.exists():
        print(f"Loading baseline weights from: {BASELINE_CKPT}")
        ckpt = torch.load(BASELINE_CKPT, map_location="cpu", weights_only=True)
        if "state_dict" in ckpt:
            model.load_state_dict(ckpt["state_dict"])
            print("Loaded baseline state dict successfully.")
    else:
        print("Baseline checkpoint not found, initializing fresh.")

    model.to(device)

    # Datasets
    train_manifest = UNIFIED_DIR / "manifests" / "manifest_train.jsonl"
    val_manifest = UNIFIED_DIR / "manifests" / "manifest_val.jsonl"

    train_ds = UnifiedDetectionDataset(train_manifest, max_samples=1200, is_train=True)
    val_ds = UnifiedDetectionDataset(val_manifest, max_samples=300, is_train=False)

    train_loader = DataLoader(train_ds, batch_size=4, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_ds, batch_size=4, shuffle=False, collate_fn=collate_fn)

    print(f"Train samples: {len(train_ds)} | Val samples: {len(val_ds)}")

    # Initial baseline evaluation
    print("\nEvaluating baseline weights on validation set...")
    val_init = evaluate_val(model, val_loader, device)
    print(f"Initial Val -> Precision: {val_init['precision']:.3f}, Recall: {val_init['recall']:.3f}, F1: {val_init['f1']:.3f} (TP={val_init['tp']}, FP={val_init['fp']}, FN={val_init['fn']})")

    # Optimizer: fine-tune with small learning rate
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=1e-4, weight_decay=1e-4)

    best_f1 = val_init["f1"]
    epochs = 4

    t0 = time.time()
    for ep in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        batches = 0

        for imgs, targets, _ in train_loader:
            imgs = [img.to(device) for img in imgs]
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

            loss_dict = model(imgs, targets)
            losses = sum(loss for loss in loss_dict.values())

            optimizer.zero_grad()
            losses.backward()
            optimizer.step()

            total_loss += losses.item()
            batches += 1

        avg_loss = total_loss / batches
        val_metrics = evaluate_val(model, val_loader, device)
        print(f"Epoch {ep}/{epochs} - Loss: {avg_loss:.4f} | Val F1: {val_metrics['f1']:.3f} (P: {val_metrics['precision']:.3f}, R: {val_metrics['recall']:.3f})")

        if val_metrics["f1"] >= best_f1:
            best_f1 = val_metrics["f1"]
            save_payload = {
                "format": "jaldrishti-vision-detector/1",
                "meta": {
                    "model_name": "fasterrcnn_mobilenet_v3_large_fpn_unified_v2",
                    "model_version": "v2.0.0",
                    "arch": "fasterrcnn_mobilenet_v3_large_fpn",
                    "classes": ["crack"],
                    "image_size": 512,
                    "score_threshold": 0.55,
                    "preprocessing_version": "rgb-01-torchvision-rcnn-resize-v1",
                    "label_status": "fine_tuned_unified_heritage",
                    "best_f1": best_f1,
                    "epoch": ep,
                },
                "state_dict": model.state_dict(),
            }
            torch.save(save_payload, OUTPUT_DIR / "model.pt")
            print(f"  ⭐ Saved new best checkpoint (F1: {best_f1:.3f}) to {OUTPUT_DIR / 'model.pt'}")

    t_elapsed = time.time() - t0
    print(f"\nFaster R-CNN fine-tuning finished in {t_elapsed / 60:.2f} minutes.")
    print(f"Best Validation F1: {best_f1:.4f}")


if __name__ == "__main__":
    main()

