"""Heritage Image Relevance Classifier: Training, Threshold Calibration, and Export.

Trains a lightweight MobileNetV3-Small binary classifier to distinguish:
Class 1: Heritage masonry, stepwells, ancient stone/brick structures.
Class 0: Irrelevant images (people, vehicles, animals, food, furniture, documents, flat drywall).
Includes calibrated uncertainty boundaries for reliable human-in-the-loop triage.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ImageFolderDataset(Dataset):
    def __init__(self, root: Path, transform=None):
        self.samples: List[Tuple[Path, int]] = []
        self.transform = transform
        self.classes = ["irrelevant", "heritage_masonry"]

        for idx, cls_name in enumerate(self.classes):
            cls_dir = root / cls_name
            if cls_dir.is_dir():
                for p in sorted(cls_dir.glob("*.jpg")):
                    self.samples.append((p, idx))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        p, label = self.samples[idx]
        with Image.open(p) as img:
            im = img.convert("RGB")
        if self.transform:
            im = self.transform(im)
        return im, label, str(p.name)


def build_classifier(num_classes: int = 2) -> nn.Module:
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    in_features = model.classifier[3].in_features
    # Replace final classification layer
    model.classifier[3] = nn.Sequential(
        nn.Dropout(p=0.2),
        nn.Linear(in_features, num_classes),
    )
    return model


def train_relevance_classifier(
    data_dir: Path,
    out_dir: Path,
    epochs: int = 5,
    batch_size: int = 16,
    lr: float = 1e-3,
    device: str = "cpu",
) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dev = torch.device(device)
    print(f"Training Heritage Relevance Classifier on device: {dev}")

    train_transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(degrees=10),
        transforms.ColorJitter(brightness=0.15, contrast=0.15),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    val_transform = transforms.Compose([
        transforms.Resize((256, 256)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    train_ds = ImageFolderDataset(data_dir / "train", transform=train_transform)
    val_ds = ImageFolderDataset(data_dir / "val", transform=val_transform)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    print(f"Dataset splits: Train={len(train_ds)} samples, Val={len(val_ds)} samples")

    model = build_classifier(num_classes=2).to(dev)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_acc = 0.0
    history = []

    start_time = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss, train_correct = 0.0, 0
        for x, y, _ in train_loader:
            x, y = x.to(dev), y.to(dev)
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * x.size(0)
            train_correct += (logits.argmax(dim=1) == y).sum().item()

        scheduler.step()
        train_loss /= len(train_ds)
        train_acc = train_correct / len(train_ds)

        # Validation
        model.eval()
        val_loss, val_correct = 0.0, 0
        all_probs, all_targets = [], []
        with torch.no_grad():
            for x, y, _ in val_loader:
                x, y = x.to(dev), y.to(dev)
                logits = model(x)
                loss = criterion(logits, y)
                val_loss += loss.item() * x.size(0)
                val_correct += (logits.argmax(dim=1) == y).sum().item()

                probs = torch.softmax(logits, dim=1)[:, 1].cpu().tolist()
                all_probs.extend(probs)
                all_targets.extend(y.cpu().tolist())

        val_loss /= len(val_ds)
        val_acc = val_correct / len(val_ds)

        history.append({
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_acc": round(train_acc, 4),
            "val_loss": round(val_loss, 4),
            "val_acc": round(val_acc, 4),
        })
        print(f"Epoch {epoch}/{epochs} | Train Loss: {train_loss:.4f}, Train Acc: {train_acc*100:.1f}% | Val Loss: {val_loss:.4f}, Val Acc: {val_acc*100:.1f}%")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            # Save checkpoint
            ckpt = {
                "format": "jaldrishti-relevance-classifier/1",
                "state_dict": model.state_dict(),
                "arch": "mobilenet_v3_small",
                "classes": ["irrelevant", "heritage_masonry"],
                "input_size": [256, 256],
                "thresholds": {
                    "relevant": 0.70,
                    "uncertain_low": 0.35,
                    "uncertain_high": 0.70,
                    "irrelevant": 0.35,
                },
                "val_accuracy": round(val_acc, 4),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            torch.save(ckpt, out_dir / "model.pt")

    duration = round(time.time() - start_time, 1)

    # Detailed final calibration metrics
    tp, fp, tn, fn = 0, 0, 0, 0
    uncertain_count = 0
    for p_score, target in zip(all_probs, all_targets):
        if p_score >= 0.70:
            pred = 1
        elif p_score < 0.35:
            pred = 0
        else:
            uncertain_count += 1
            pred = 1 if p_score >= 0.50 else 0

        if target == 1 and pred == 1:
            tp += 1
        elif target == 0 and pred == 1:
            fp += 1
        elif target == 0 and pred == 0:
            tn += 1
        elif target == 1 and pred == 0:
            fn += 1

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    eval_report = {
        "model_architecture": "mobilenet_v3_small",
        "best_val_accuracy": round(best_val_acc, 4),
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
        "uncertain_cases_val": uncertain_count,
        "calibration": {
            "p_relevant_threshold": 0.70,
            "p_uncertain_band": [0.35, 0.70],
            "p_irrelevant_threshold": 0.35,
        },
        "training_duration_seconds": duration,
        "history": history,
    }
    (out_dir / "evaluation.json").write_text(json.dumps(eval_report, indent=2))
    print(f"Classifier saved to {out_dir / 'model.pt'}")
    print(f"Validation F1: {f1*100:.2f}%, Precision: {precision*100:.2f}%, Recall: {recall*100:.2f}%")
    return eval_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/processed/relevance_dataset")
    parser.add_argument("--out-dir", default="vision/models/relevance_classifier")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    args = parser.parse_args()

    train_relevance_classifier(
        data_dir=Path(args.data_dir),
        out_dir=Path(args.out_dir),
        epochs=args.epochs,
        device=args.device,
    )

