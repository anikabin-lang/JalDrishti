"""Heritage Image Relevance Inference Predictor.

Pre-screening gate determining whether an input photograph depicts historic masonry / stepwells
or unrelated content (people, vehicles, animals, furniture, food, documents).
"""

from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import models, transforms
from torchvision.transforms import functional as TF

logger = logging.getLogger(__name__)

RELEVANCE_FORMAT = "jaldrishti-relevance-classifier/1"

# Semantic category groupings for COCO pre-screening
DOMESTIC_OBJECTS: Set[str] = {
    "bed", "couch", "tv", "laptop", "keyboard", "mouse",
    "microwave", "oven", "refrigerator", "toilet", "cell phone",
}
VEHICLE_OBJECTS: Set[str] = {
    "car", "truck", "motorcycle", "bus", "airplane", "train",
}
ANIMAL_OBJECTS: Set[str] = {
    "cat", "dog", "bear",
}

_GLOBAL_COCO_MODEL: Optional[torch.nn.Module] = None
_GLOBAL_COCO_CATEGORIES: Optional[List[str]] = None


def _get_coco_detector(device: torch.device) -> Tuple[torch.nn.Module, List[str]]:
    """Lazy loader for cached COCO SSDLite320 detector for semantic pre-screening."""
    global _GLOBAL_COCO_MODEL, _GLOBAL_COCO_CATEGORIES
    if _GLOBAL_COCO_MODEL is None:
        try:
            from torchvision.models.detection import (
                SSDLite320_MobileNet_V3_Large_Weights,
                ssdlite320_mobilenet_v3_large,
            )

            weights = SSDLite320_MobileNet_V3_Large_Weights.DEFAULT
            model = ssdlite320_mobilenet_v3_large(weights=weights)
            model.to(device).eval()
            _GLOBAL_COCO_MODEL = model
            _GLOBAL_COCO_CATEGORIES = weights.meta["categories"]
            logger.info("Initialized COCO SSDLite320 semantic screener on %s.", device)
        except Exception as e:
            logger.warning("Could not initialize SSDLite320 semantic screener: %s", e)
            _GLOBAL_COCO_MODEL = None
            _GLOBAL_COCO_CATEGORIES = []
    return _GLOBAL_COCO_MODEL, _GLOBAL_COCO_CATEGORIES



@dataclass
class RelevanceResult:
    is_relevant: bool
    status: str  # "relevant", "uncertain", "irrelevant"
    confidence: float
    decision: str = "RELEVANT_HERITAGE"  # "RELEVANT_HERITAGE", "IRRELEVANT", "UNCERTAIN"
    rejection_reason: Optional[str] = None
    needs_manual_review: bool = False
    timing_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_relevant": self.is_relevant,
            "status": self.status,
            "decision": self.decision,
            "confidence": round(self.confidence, 4),
            "rejection_reason": self.rejection_reason,
            "needs_manual_review": self.needs_manual_review,
            "timing_ms": round(self.timing_ms, 2),
        }


class RelevancePredictor:
    def __init__(self, model: torch.nn.Module, meta: Dict[str, Any], device: torch.device):
        self.model = model
        self.meta = meta
        self.device = device
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        self.thresholds = meta.get("thresholds", {
            "relevant": 0.70,
            "uncertain_low": 0.35,
            "uncertain_high": 0.70,
            "irrelevant": 0.35,
        })

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_path: Union[str, Path],
        device: Optional[str] = None,
    ) -> "RelevancePredictor":
        path = Path(checkpoint_path)
        if not path.is_file():
            raise FileNotFoundError(f"Relevance checkpoint not found: {path}")

        if device is None:
            dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        else:
            dev = torch.device(device)

        ckpt = torch.load(path, map_location=dev, weights_only=True)
        if ckpt.get("format") != RELEVANCE_FORMAT:
            raise ValueError(f"Invalid relevance checkpoint format: {ckpt.get('format')}")

        model = models.mobilenet_v3_small(weights=None)
        in_features = model.classifier[3].in_features
        model.classifier[3] = torch.nn.Sequential(
            torch.nn.Dropout(p=0.2),
            torch.nn.Linear(in_features, 2),
        )
        model.load_state_dict(ckpt["state_dict"])
        model.to(dev).eval()

        return cls(model=model, meta=ckpt, device=dev)

    def screen_semantics(self, pil_img: Image.Image, t0: float) -> Optional[RelevanceResult]:
        """Perform semantic COCO screening and texture variance checks."""
        # 1. Structural texture check: Reject completely flat / blank surfaces (drywall, digital solids)
        try:
            gray = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if laplacian_var < 35.0:
                t_elapsed = (time.perf_counter() - t0) * 1000.0
                return RelevanceResult(
                    is_relevant=False,
                    status="irrelevant",
                    decision="IRRELEVANT",
                    confidence=0.95,
                    rejection_reason=(
                        "This image does not appear to contain a suitable heritage structure for Jaldrishti inspection. "
                        "The photograph lacks structural masonry surface texture (smooth painted drywall, digital screenshot, or uniform solid). "
                        "Please upload a photograph of a baoli, stepwell, or heritage masonry surface."
                    ),
                    needs_manual_review=False,
                    timing_ms=t_elapsed,
                )
        except Exception as e:
            logger.debug("Texture variance check skipped: %s", e)

        # 2. Semantic COCO object screening (Person, domestic objects, vehicles, animals)
        detector, categories = _get_coco_detector(self.device)
        if detector is None or not categories:
            return None

        w, h = pil_img.size
        img_area = float(w * h)
        try:
            t_input = TF.to_tensor(pil_img).to(self.device)
            with torch.inference_mode():
                pred = detector([t_input])[0]

            boxes = pred["boxes"].cpu().numpy()
            labels = pred["labels"].cpu().numpy()
            scores = pred["scores"].cpu().numpy()

            person_boxes = []
            domestic_hits = []
            vehicle_hits = []
            animal_hits = []

            for box, label, score in zip(boxes, labels, scores):
                if score < 0.40:
                    continue
                if label >= len(categories):
                    continue
                cat = categories[label]
                bx1, by1, bx2, by2 = box
                bw = max(1.0, bx2 - bx1)
                bh = max(1.0, by2 - by1)
                area_ratio = (bw * bh) / img_area
                h_ratio = bh / h
                w_ratio = bw / w

                if cat == "person":
                    person_boxes.append((float(score), float(area_ratio), float(h_ratio), float(w_ratio)))
                elif cat in DOMESTIC_OBJECTS and (area_ratio > 0.05 or score >= 0.60):
                    domestic_hits.append((cat, float(score), float(area_ratio)))
                elif cat in VEHICLE_OBJECTS and area_ratio > 0.18:
                    vehicle_hits.append((cat, float(score), float(area_ratio)))
                elif cat in ANIMAL_OBJECTS and area_ratio > 0.18:
                    animal_hits.append((cat, float(score), float(area_ratio)))

            # Evaluate Human Portrait / Selfie criteria
            if person_boxes:
                max_person_area = max(p[1] for p in person_boxes)
                total_person_area = sum(p[1] for p in person_boxes)
                max_h_ratio = max(p[2] for p in person_boxes)
                max_w_ratio = max(p[3] for p in person_boxes)

                # Rejection condition: Selfie, portrait, or foreground humans dominating frame
                if max_person_area > 0.18 or (max_h_ratio > 0.50 and max_w_ratio > 0.25) or total_person_area > 0.35:
                    t_elapsed = (time.perf_counter() - t0) * 1000.0
                    return RelevanceResult(
                        is_relevant=False,
                        status="irrelevant",
                        decision="IRRELEVANT",
                        confidence=0.98,
                        rejection_reason=(
                            "This image does not appear to contain a suitable heritage structure for Jaldrishti inspection. "
                            f"The photograph is a human portrait or selfie (person occupies {max_person_area * 100:.1f}% of frame) "
                            "without dominant heritage masonry structure. "
                            "Please upload a photograph of a baoli, stepwell, or heritage masonry surface."
                        ),
                        needs_manual_review=False,
                        timing_ms=t_elapsed,
                    )

            if domestic_hits:
                dom_names = ", ".join({d[0] for d in domestic_hits})
                t_elapsed = (time.perf_counter() - t0) * 1000.0
                return RelevanceResult(
                    is_relevant=False,
                    status="irrelevant",
                    decision="IRRELEVANT",
                    confidence=0.96,
                    rejection_reason=(
                        "This image does not appear to contain a suitable heritage structure for Jaldrishti inspection. "
                        f"Image depicts an indoor domestic environment with household items ({dom_names}) "
                        "rather than outdoor heritage masonry architecture. "
                        "Please upload a photograph of a baoli, stepwell, or heritage masonry surface."
                    ),
                    needs_manual_review=False,
                    timing_ms=t_elapsed,
                )

            if vehicle_hits:
                v_names = ", ".join({v[0] for v in vehicle_hits})
                t_elapsed = (time.perf_counter() - t0) * 1000.0
                return RelevanceResult(
                    is_relevant=False,
                    status="irrelevant",
                    decision="IRRELEVANT",
                    confidence=0.95,
                    rejection_reason=(
                        "This image does not appear to contain a suitable heritage structure for Jaldrishti inspection. "
                        f"Image depicts modern vehicles or transportation equipment ({v_names}). "
                        "Please upload a photograph of a baoli, stepwell, or heritage masonry surface."
                    ),
                    needs_manual_review=False,
                    timing_ms=t_elapsed,
                )

            if animal_hits:
                a_names = ", ".join({a[0] for a in animal_hits})
                t_elapsed = (time.perf_counter() - t0) * 1000.0
                return RelevanceResult(
                    is_relevant=False,
                    status="irrelevant",
                    decision="IRRELEVANT",
                    confidence=0.95,
                    rejection_reason=(
                        "This image does not appear to contain a suitable heritage structure for Jaldrishti inspection. "
                        f"Photograph is an animal portrait ({a_names}). "
                        "Please upload a photograph of a baoli, stepwell, or heritage masonry surface."
                    ),
                    needs_manual_review=False,
                    timing_ms=t_elapsed,
                )

        except Exception as e:
            logger.warning("COCO semantic screening execution error: %s", e)

        return None

    def predict(self, source: Union[bytes, Image.Image, Path, str]) -> RelevanceResult:
        t0 = time.perf_counter()
        if isinstance(source, (bytes, bytearray)):
            pil_img = Image.open(io.BytesIO(source)).convert("RGB")
        elif isinstance(source, Image.Image):
            pil_img = source.convert("RGB")
        elif isinstance(source, (str, Path)):
            pil_img = Image.open(source).convert("RGB")
        else:
            raise TypeError(f"Unsupported image source type: {type(source)}")

        # Step 1: Semantic Pre-Screening Gate
        screen_res = self.screen_semantics(pil_img, t0)
        if screen_res is not None:
            return screen_res

        # Step 2: Fine-grained MobileNetV3 Heritage Relevance Classifier

        tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)[0]
            p_heritage = float(probs[1].item())

        t_elapsed = (time.perf_counter() - t0) * 1000.0

        th_rel = self.thresholds.get("relevant", 0.70)
        th_irr = self.thresholds.get("irrelevant", 0.35)

        if p_heritage >= th_rel:
            return RelevanceResult(
                is_relevant=True,
                status="relevant",
                decision="RELEVANT_HERITAGE",
                confidence=p_heritage,
                rejection_reason=None,
                needs_manual_review=False,
                timing_ms=t_elapsed,
            )
        elif p_heritage < th_irr:
            return RelevanceResult(
                is_relevant=False,
                status="irrelevant",
                decision="IRRELEVANT",
                confidence=1.0 - p_heritage,
                rejection_reason=(
                    "This image does not appear to contain a suitable heritage structure for Jaldrishti inspection. "
                    "Please upload a photograph of a baoli, stepwell, or heritage masonry surface."
                ),
                needs_manual_review=False,
                timing_ms=t_elapsed,
            )
        else:
            return RelevanceResult(
                is_relevant=True,  # Allow conditional triage
                status="uncertain",
                decision="UNCERTAIN",
                confidence=p_heritage,
                rejection_reason=(
                    "The image could not be confidently verified as a heritage structure. "
                    "Please review the image or upload a clearer photograph."
                ),
                needs_manual_review=True,
                timing_ms=t_elapsed,
            )

