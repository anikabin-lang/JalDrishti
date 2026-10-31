"""Vision Service providing multi-stage inference boundary and defect normalization.

Implements the complete 4-Stage Computer Vision Pipeline:
Stage 1: Image Quality Assessment (Blur, Low-light, Overexposure, Resolution validation)
Stage 2: Heritage Relevance Classification Gate (Rejects non-heritage assets to prevent false positives)
Stage 3: Multi-Class Damage Detection (Cracks and Vegetation using Faster R-CNN & YOLO26n)
Stage 4: Post-Processing & Validation (NMS, Aspect ratio sanity, Severity scoring, Zero-defect handling)

Maintained by Swastik Parmar (Backend / Integration Engineer).
Adheres strictly to contracts/vision_result.schema.json.
"""

from __future__ import annotations

import io
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from backend.app.schemas.vision import (
    DetectionItem,
    ImageDimensions,
    ProcessingMetadata,
    RelativeSeverity,
    ScaleReference,
    StructureType,
    VisionResult,
)
from backend.app.utils.image import get_image_dimensions_from_bytes

logger = logging.getLogger(__name__)

# Locate project root and model assets
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RELEVANCE_CHECKPOINT_PATH = PROJECT_ROOT / "vision" / "models" / "relevance_classifier" / "model.pt"
DETECTOR_V2_CHECKPOINT_PATH = PROJECT_ROOT / "vision" / "models" / "crack_detector_v2_unified" / "model.pt"
DETECTOR_CHECKPOINT_PATH = PROJECT_ROOT / "vision" / "models" / "crack_detector_pilot_v1" / "model.pt"
YOLO_UNIFIED_CHECKPOINT_PATH = PROJECT_ROOT / "vision" / "models" / "damage_detector_yolo26n_unified" / "model.pt"
YOLO26N_CHECKPOINT_PATH = PROJECT_ROOT / "vision" / "models" / "damage_detector_yolo26n" / "model.pt"
YOLO_BENCHMARK_PATH = PROJECT_ROOT / "vision" / "outputs" / "benchmarks" / "yolo26n" / "weights" / "best.pt"
PILOT_YOLO_PATH = PROJECT_ROOT / "vision" / "models" / "crack_pilot_yolov8n.pt"
DEMO_SUMMARY_PATH = PROJECT_ROOT / "vision" / "demo_assets" / "evaluation_summary.json"


def assess_image_quality(pil_img: Image.Image) -> Dict[str, Any]:
    """Stage 1: Evaluate image quality for blur, exposure extremes, and minimum resolution."""
    w, h = pil_img.size
    gray = np.array(pil_img.convert("L"), dtype=np.float32)

    # 3x3 Laplacian operator for spatial high-frequency blur estimation
    pad = np.pad(gray, 1, mode="edge")
    lap = (
        pad[0:h, 1 : w + 1]
        + pad[2 : h + 2, 1 : w + 1]
        + pad[1 : h + 1, 0:w]
        + pad[1 : h + 1, 2 : w + 2]
        - 4.0 * gray
    )
    lap_var = float(np.var(lap))
    mean_lum = float(np.mean(gray))

    status = "good"
    reasons = []

    if w < 128 or h < 128:
        status = "blurred"
        reasons.append(f"Image resolution ({w}x{h}) is too low for reliable defect analysis.")
    elif lap_var < 12.0:
        status = "blurred"
        reasons.append(
            f"Image appears significantly blurred (Laplacian variance {lap_var:.1f} < 12.0). "
            "Fine structural fissures may be indistinct."
        )

    if mean_lum < 40.0:
        status = "poor_lighting"
        reasons.append(
            f"Image is heavily underexposed (Mean luminance {mean_lum:.1f} < 40.0). "
            "Shadow regions may conceal masonry damage."
        )
    elif mean_lum > 220.0:
        status = "poor_lighting"
        reasons.append(
            f"Image is overexposed (Mean luminance {mean_lum:.1f} > 220.0). "
            "Surface wash-out impairs feature contrast."
        )

    return {
        "quality_status": status,
        "laplacian_variance": round(lap_var, 2),
        "mean_luminance": round(mean_lum, 2),
        "reasons": reasons,
    }


def compute_iou(box_a: List[float], box_b: List[float]) -> float:
    """Compute Intersection-over-Union between two [x1, y1, x2, y2] bounding boxes."""
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(1.0, (box_a[2] - box_a[0]) * (box_a[3] - box_a[1]))
    area_b = max(1.0, (box_b[2] - box_b[0]) * (box_b[3] - box_b[1]))
    union_area = area_a + area_b - inter_area
    return inter_area / union_area if union_area > 0 else 0.0


def apply_non_max_suppression(
    items: List[DetectionItem], iou_threshold: float = 0.50
) -> List[DetectionItem]:
    """Remove redundant overlapping candidate detections of the same defect class."""
    if not items:
        return []

    # Sort descending by confidence
    sorted_items = sorted(items, key=lambda x: x.confidence, reverse=True)
    kept: List[DetectionItem] = []

    for item in sorted_items:
        overlap = False
        for k in kept:
            if k.class_name == item.class_name:
                if compute_iou(k.bounding_box, item.bounding_box) > iou_threshold:
                    overlap = True
                    break
        if not overlap:
            kept.append(item)

    return kept


class VisionService:
    """Service boundary for computer vision defect extraction and spatial analysis."""

    def __init__(self, model_version: str = "jaldrishti-vision-v0.3.0") -> None:
        self.model_version = model_version
        self._relevance_predictor: Any = None
        self._detector: Any = None
        self._yolo26_model: Any = None
        self._yolo_model: Any = None
        self._demo_evaluations: Dict[str, Dict[str, Any]] = {}
        self._load_demo_evaluations()

    def _load_demo_evaluations(self) -> None:
        """Load Krish's evaluation summary if present for offline/demo verification."""
        if DEMO_SUMMARY_PATH.is_file():
            try:
                with open(DEMO_SUMMARY_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        img_key = item.get("image", "").lower()
                        src_key = item.get("source_file", "").lower()
                        if img_key:
                            self._demo_evaluations[img_key] = item
                            self._demo_evaluations[Path(img_key).stem] = item
                        if src_key:
                            self._demo_evaluations[src_key] = item
                            self._demo_evaluations[Path(src_key).stem] = item
            except Exception as e:
                logger.warning("Failed to load demo evaluations: %s", e)

    def _get_relevance_predictor(self) -> Any:
        """Lazy loader for MobileNetV3-Small Heritage Relevance Classifier."""
        if self._relevance_predictor is None and RELEVANCE_CHECKPOINT_PATH.is_file():
            try:
                from vision.inference.relevance import RelevancePredictor

                self._relevance_predictor = RelevancePredictor.from_checkpoint(
                    RELEVANCE_CHECKPOINT_PATH, device="cpu"
                )
                logger.info("Loaded Heritage Relevance Classifier successfully.")
            except Exception as e:
                logger.warning("Could not initialize RelevancePredictor: %s", e)
        return self._relevance_predictor

    def _get_detector(self) -> Any:
        """Lazy loader for Faster R-CNN crack DetectionPredictor."""
        target_path = DETECTOR_V2_CHECKPOINT_PATH if DETECTOR_V2_CHECKPOINT_PATH.is_file() else DETECTOR_CHECKPOINT_PATH
        if self._detector is None and target_path.is_file():
            try:
                from vision.inference.detector import DetectionPredictor

                self._detector = DetectionPredictor.from_checkpoint(
                    target_path, device="cpu"
                )
                logger.info(
                    "Loaded Faster R-CNN crack detection model (%s) successfully from %s.",
                    self._detector.meta.get("model_version", "pilot_v1"),
                    target_path.name,
                )
            except Exception as e:
                logger.warning(
                    "Could not initialize DetectionPredictor from %s: %s",
                    target_path,
                    e,
                )
        return self._detector

    def _get_yolo26_model(self) -> Any:
        """Lazy loader for multi-class YOLO26n damage detector."""
        target_path = None
        if YOLO_UNIFIED_CHECKPOINT_PATH.is_file():
            target_path = YOLO_UNIFIED_CHECKPOINT_PATH
        elif YOLO26N_CHECKPOINT_PATH.is_file():
            target_path = YOLO26N_CHECKPOINT_PATH
        elif YOLO_BENCHMARK_PATH.is_file():
            target_path = YOLO_BENCHMARK_PATH

        if self._yolo26_model is None and target_path is not None:
            try:
                from ultralytics import YOLO

                self._yolo26_model = YOLO(str(target_path))
                logger.info("Loaded YOLO26n multi-class defect detector successfully from %s.", target_path.name)
            except Exception as e:
                logger.warning("Could not initialize YOLO26n model: %s", e)
        return self._yolo26_model

    def _get_yolo_model(self) -> Any:
        """Lazy loader for legacy Ultralytics YOLOv8 crack pilot."""
        if self._yolo_model is None and PILOT_YOLO_PATH.is_file():
            try:
                from ultralytics import YOLO

                self._yolo_model = YOLO(str(PILOT_YOLO_PATH))
                logger.info("Loaded legacy YOLOv8 crack pilot model.")
            except Exception as e:
                logger.warning("Could not initialize legacy YOLO model: %s", e)
        return self._yolo_model

    def inspect_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """Run Stage 1 (Quality Check) and Stage 2 (Heritage Relevance Gate) rapidly.

        Returns:
            dict containing:
                inspection_status: "accepted" | "rejected" | "uncertain"
                decision: "RELEVANT_HERITAGE" | "IRRELEVANT" | "UNCERTAIN"
                relevance_confidence: float
                quality_status: "good" | "blurred" | "poor_lighting"
                quality_warnings: list[str]
                rejection_reason: str or None
                needs_manual_review: bool
                status_message: str
                model_version: str
        """
        try:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            return {
                "inspection_status": "rejected",
                "decision": "IRRELEVANT",
                "relevance_confidence": 0.0,
                "quality_status": "poor_lighting",
                "quality_warnings": [f"Image could not be parsed: {e}"],
                "rejection_reason": "Uploaded image payload is corrupted or unreadable.",
                "needs_manual_review": False,
                "status_message": "Image payload is unreadable.",
                "model_version": self.model_version,
            }

        q_info = assess_image_quality(pil_img)
        quality_status = q_info["quality_status"]
        quality_warnings = q_info["reasons"]

        rel_clf = self._get_relevance_predictor()
        if rel_clf is None:
            return {
                "inspection_status": "uncertain",
                "decision": "UNCERTAIN",
                "relevance_confidence": 0.0,
                "quality_status": quality_status,
                "quality_warnings": quality_warnings,
                "rejection_reason": "Heritage relevance classification model is unavailable. Image held for manual verification.",
                "needs_manual_review": True,
                "status_message": "Relevance classifier unavailable. Image held for manual expert verification.",
                "model_version": self.model_version,
            }

        rel_res = rel_clf.predict(pil_img)
        if rel_res.status == "irrelevant":
            inspection_status = "rejected"
            decision = "IRRELEVANT"
            status_message = (
                "This image does not appear to contain a suitable heritage structure for Jaldrishti inspection. "
                "Please upload a photograph of a baoli, stepwell, or heritage masonry surface."
            )
        elif rel_res.status == "uncertain":
            inspection_status = "uncertain"
            decision = "UNCERTAIN"
            status_message = (
                "The image could not be confidently verified as a heritage structure. "
                "Please review the image or upload a clearer photograph."
            )
        else:
            inspection_status = "accepted"
            decision = "RELEVANT_HERITAGE"
            status_message = "Image verified as authentic heritage masonry structure. Proceeding to structural damage inspection."

        return {
            "inspection_status": inspection_status,
            "decision": decision,
            "relevance_confidence": round(rel_res.confidence, 4),
            "quality_status": quality_status,
            "quality_warnings": quality_warnings,
            "rejection_reason": rel_res.rejection_reason,
            "needs_manual_review": rel_res.needs_manual_review,
            "status_message": status_message,
            "model_version": f"{self.model_version}+relevance_gate",
        }

    def analyze_image(
        self,
        image_bytes: Optional[bytes] = None,
        image_name: Optional[str] = None,
        source_images: Optional[List[str]] = None,
        structure_type: StructureType = StructureType.BAOLI,
        image_dimensions: Optional[ImageDimensions] = None,
        scale_reference: Optional[ScaleReference] = None,
        detections: Optional[List[DetectionItem]] = None,
        roi_box: Optional[List[float]] = None,
    ) -> VisionResult:
        """Process image input through the 4-Stage Conservation Vision Pipeline.

        Stage 1: Image Quality Assessment
        Stage 2: Heritage Relevance Gatekeeper
        Stage 3: Multi-Class Defect Extraction
        Stage 4: Post-Processing, Severity Assessment & Verification
        """
        start_time = time.perf_counter()

        # Resolve image dimensions & load PIL image if bytes provided
        pil_img: Optional[Image.Image] = None
        if image_bytes:
            try:
                pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            except Exception as e:
                logger.warning("Could not parse image bytes with PIL: %s", e)

        resolved_dimensions = image_dimensions
        if resolved_dimensions is None and pil_img is not None:
            resolved_dimensions = ImageDimensions(
                width_pixels=pil_img.width,
                height_pixels=pil_img.height,
            )
        elif resolved_dimensions is None and image_bytes is not None:
            extracted = get_image_dimensions_from_bytes(image_bytes)
            if extracted:
                resolved_dimensions = ImageDimensions(
                    width_pixels=extracted[0],
                    height_pixels=extracted[1],
                )

        if resolved_dimensions is None:
            resolved_dimensions = ImageDimensions(width_pixels=1920, height_pixels=1080)

        img_w = float(resolved_dimensions.width_pixels)
        img_h = float(resolved_dimensions.height_pixels)
        total_img_area = max(1.0, img_w * img_h)

        # -------------------------------------------------------------------------
        # STAGE 1: Image Quality Assessment
        # -------------------------------------------------------------------------
        quality_status = "good"
        quality_warnings: List[str] = []
        if pil_img is not None:
            q_info = assess_image_quality(pil_img)
            quality_status = q_info["quality_status"]
            quality_warnings = q_info["reasons"]

        # -------------------------------------------------------------------------
        # STAGE 2: Heritage Relevance Classification Gate
        # -------------------------------------------------------------------------
        relevance_status = "relevant"
        relevance_confidence = 1.0
        rejection_reason: Optional[str] = None
        needs_manual_review = False

        rel_clf = self._get_relevance_predictor()
        if rel_clf is not None and pil_img is not None:
            try:
                rel_res = rel_clf.predict(pil_img)
                relevance_status = rel_res.status
                relevance_confidence = rel_res.confidence
                rejection_reason = rel_res.rejection_reason
                needs_manual_review = rel_res.needs_manual_review

                # HARD REJECTION FOR IRRELEVANT ASSETS (Vehicles, People, Documents, etc.)
                if relevance_status == "irrelevant":
                    latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                    return VisionResult(
                        structure_type=structure_type,
                        image_dimensions=resolved_dimensions,
                        scale_reference=scale_reference,
                        detections=[],
                        processing_metadata=ProcessingMetadata(
                            inference_latency_ms=latency_ms,
                            model_version=f"{self.model_version}+relevance_gate",
                        ),
                        relevance_status="irrelevant",
                        relevance_confidence=relevance_confidence,
                        quality_status=quality_status,
                        rejection_reason=rejection_reason,
                        needs_manual_review=False,
                        status_message=(
                            "This image does not appear to contain a suitable heritage structure for Jaldrishti inspection. "
                            "Please upload a photograph of a baoli, stepwell, or heritage masonry surface."
                        ),
                    )
            except Exception as e:
                logger.warning("Heritage relevance classification failed: %s", e)

        # -------------------------------------------------------------------------
        # STAGE 3: Multi-Class Damage Detection
        # -------------------------------------------------------------------------
        raw_detections: List[DetectionItem] = []
        model_tag_suffix = "ensemble"

        # 1. Explicit pre-detected items
        if detections:
            raw_detections.extend(detections)
            model_tag_suffix = "manual_annotations"

        # 2. Offline / Demo evaluation assets (ONLY used when no real image payload is uploaded)
        if image_bytes is None and not raw_detections:
            demo_match: Optional[Dict[str, Any]] = None
            candidate_names = []
            if image_name:
                candidate_names.append(image_name)
            if source_images:
                candidate_names.extend(source_images)

            for name in candidate_names:
                key = name.lower()
                stem = Path(name).stem.lower()
                if key in self._demo_evaluations:
                    demo_match = self._demo_evaluations[key]
                    break
                if stem in self._demo_evaluations:
                    demo_match = self._demo_evaluations[stem]
                    break

            if demo_match:
                crack_info = demo_match.get("crack", {})
                if crack_info.get("detected"):
                    bbox = crack_info.get("bbox") or [10.0, 10.0, 200.0, 200.0]
                    conf = float(crack_info.get("confidence", 0.82))
                    bw = max(1.0, float(bbox[2] - bbox[0]))
                    bh = max(1.0, float(bbox[3] - bbox[1]))
                    area = round(bw * bh, 1)
                    cov = round(min(1.0, area / total_img_area), 4)
                    length = round(max(bw, bh), 1)

                    raw_detections.append(
                        DetectionItem(
                            class_name="crack",
                            confidence=conf,
                            bounding_box=[float(v) for v in bbox],
                            pixel_area=area,
                            coverage_ratio=cov,
                            component_count=1,
                            total_length_pixels=length,
                            largest_component_length_pixels=length,
                            relative_severity=(
                                RelativeSeverity.SEVERE
                                if cov > 0.15
                                else (RelativeSeverity.MODERATE if cov > 0.05 else RelativeSeverity.LOW)
                            ),
                        )
                    )

                veg_info = demo_match.get("vegetation", {})
                if veg_info.get("visual_indicator"):
                    cov = float(veg_info.get("coverage_ratio", 0.08))
                    area = round(cov * total_img_area, 1)
                    raw_detections.append(
                        DetectionItem(
                            class_name="vegetation_root_intrusion",
                            confidence=0.85,
                            bounding_box=[0.0, 0.0, img_w, round(img_h * 0.4, 1)],
                            pixel_area=area,
                            coverage_ratio=round(min(1.0, cov), 4),
                            component_count=2,
                            total_length_pixels=round(img_w * 0.3, 1),
                            largest_component_length_pixels=round(img_w * 0.2, 1),
                            relative_severity=(
                                RelativeSeverity.SEVERE
                                if cov > 0.12
                                else (RelativeSeverity.MODERATE if cov > 0.04 else RelativeSeverity.LOW)
                            ),
                        )
                    )
                model_tag_suffix = "demo_verified"

        # 3. Live Faster R-CNN Detection (Primary High-Precision Crack Detector)
        detector = self._get_detector()
        if detector is not None and image_bytes:
            try:
                # Use calibrated operating threshold (0.55) to maximize F1 and capture thin cracks
                res = detector.predict(image_bytes, score_threshold=0.55)
                if res.status == "ok" and res.detections:
                    for det in res.detections:
                        xmin, ymin, xmax, ymax = [float(v) for v in det.bbox]
                        bw = max(1.0, xmax - xmin)
                        bh = max(1.0, ymax - ymin)
                        # Filter horizontal masonry mortar courses lacking fissure variance
                        if bw > 350.0 and bh < 6.0:
                            continue
                        area = round(bw * bh, 1)
                        cov = round(min(1.0, area / total_img_area), 4)
                        length = round(max(bw, bh), 1)

                        raw_detections.append(
                            DetectionItem(
                                class_name=det.class_name or "crack",
                                confidence=round(float(det.confidence), 3),
                                bounding_box=[xmin, ymin, xmax, ymax],
                                pixel_area=area,
                                coverage_ratio=cov,
                                component_count=1,
                                total_length_pixels=length,
                                largest_component_length_pixels=length,
                                relative_severity=(
                                    RelativeSeverity.SEVERE
                                    if cov > 0.15
                                    else (RelativeSeverity.MODERATE if cov > 0.05 else RelativeSeverity.LOW)
                                ),
                            )
                        )
                    faster_detected = True
            except Exception as e:
                logger.warning("Faster R-CNN DetectionPredictor live inference failed: %s", e)

        # 4. Multi-class YOLO26n Detection (Cracks & Vegetation)
        yolo_detected = False
        yolo26 = self._get_yolo26_model()
        if pil_img is not None and yolo26 is not None:
            try:
                yolo_res = yolo26.predict(source=pil_img, conf=0.30, verbose=False)
                if yolo_res and len(yolo_res[0].boxes) > 0:
                    yolo_detected = True
                    for box in yolo_res[0].boxes:
                        xyxy = [float(v) for v in box.xyxy[0].cpu().numpy().tolist()]
                        conf = float(box.conf[0].cpu().numpy().item())
                        cls_idx = int(box.cls[0].cpu().numpy().item())
                        label = "vegetation_root_intrusion" if cls_idx == 1 else "crack"

                        bw = max(1.0, xyxy[2] - xyxy[0])
                        bh = max(1.0, xyxy[3] - xyxy[1])
                        area = round(bw * bh, 1)
                        cov = round(min(1.0, area / total_img_area), 4)
                        length = round(max(bw, bh), 1)

                        raw_detections.append(
                            DetectionItem(
                                class_name=label,
                                confidence=round(conf, 3),
                                bounding_box=xyxy,
                                pixel_area=area,
                                coverage_ratio=cov,
                                component_count=1,
                                total_length_pixels=length,
                                largest_component_length_pixels=length,
                                relative_severity=(
                                    RelativeSeverity.SEVERE
                                    if cov > 0.15
                                    else (RelativeSeverity.MODERATE if cov > 0.05 else RelativeSeverity.LOW)
                                ),
                            )
                        )
            except Exception as e:
                logger.warning("YOLO26n defect detection failed: %s", e)

        if image_bytes:
            model_tag_suffix = "fasterrcnn_live+yolo26n_unified"

        # 5. Chromatic Excess-Green Vegetation Extractor (Biological intrusion specialist)
        if pil_img is not None:
            try:
                rgb_arr = np.array(pil_img, dtype=np.float32)
                # Excess green index = 2G - R - B
                exg = 2.0 * rgb_arr[:, :, 1] - rgb_arr[:, :, 0] - rgb_arr[:, :, 2]
                sum_rgb = rgb_arr[:, :, 0] + rgb_arr[:, :, 1] + rgb_arr[:, :, 2] + 1e-5
                norm_exg = exg / sum_rgb

                # Chlorophyll HSV verification: green hue [35..85], saturation >= 45, brightness >= 40
                img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
                green_hsv = (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] >= 45) & (hsv[:, :, 2] >= 40)

                veg_mask = (exg > 30.0) & (norm_exg > 0.15) & green_hsv
                veg_ratio = float(np.mean(veg_mask))

                if veg_ratio > 0.02:
                    vy, vx = np.where(veg_mask)
                    v_xmin = max(0.0, float(np.percentile(vx, 5)))
                    v_xmax = min(img_w, float(np.percentile(vx, 95)))
                    v_ymin = max(0.0, float(np.percentile(vy, 5)))
                    v_ymax = min(img_h, float(np.percentile(vy, 95)))

                    v_bw = max(12.0, v_xmax - v_xmin)
                    v_bh = max(12.0, v_ymax - v_ymin)
                    v_area = round(v_bw * v_bh, 1)
                    v_cov = round(min(1.0, veg_ratio), 4)
                    v_length = round(max(v_bw, v_bh), 1)

                    raw_detections.append(
                        DetectionItem(
                            class_name="vegetation_root_intrusion",
                            confidence=min(0.96, round(0.82 + veg_ratio * 0.4, 3)),
                            bounding_box=[round(v_xmin, 1), round(v_ymin, 1), round(v_xmax, 1), round(v_ymax, 1)],
                            pixel_area=v_area,
                            coverage_ratio=v_cov,
                            component_count=2,
                            total_length_pixels=v_length,
                            largest_component_length_pixels=v_length,
                            relative_severity=(
                                RelativeSeverity.SEVERE
                                if v_cov > 0.12
                                else (RelativeSeverity.MODERATE if v_cov > 0.04 else RelativeSeverity.LOW)
                            ),
                        )
                    )
            except Exception as e:
                logger.warning("Chromatic vegetation detection failed: %s", e)

        # 6. User-specified ROI bounding region
        if not raw_detections and roi_box and len(roi_box) >= 4:
            rx, ry, rw, rh = [float(v) for v in roi_box[:4]]
            x_min = max(0.0, rx)
            y_min = max(0.0, ry)
            x_max = max(x_min + 1.0, min(img_w, rx + rw))
            y_max = max(y_min + 1.0, min(img_h, ry + rh))
            area = round(max(1.0, (x_max - x_min) * (y_max - y_min)), 1)
            cov = round(min(1.0, area / total_img_area), 4)
            length = round(max(x_max - x_min, y_max - y_min), 1)

            raw_detections.append(
                DetectionItem(
                    class_name="crack",
                    confidence=0.84,
                    bounding_box=[x_min, y_min, x_max, y_max],
                    pixel_area=area,
                    coverage_ratio=cov,
                    component_count=1,
                    total_length_pixels=length,
                    largest_component_length_pixels=length,
                    relative_severity=(
                        RelativeSeverity.SEVERE
                        if cov > 0.15
                        else (RelativeSeverity.MODERATE if cov > 0.05 else RelativeSeverity.LOW)
                    ),
                )
            )
            model_tag_suffix = "user_roi"

        # 7. Adaptive computer vision fallback if no deep models detected anything
        if not raw_detections and image_bytes:
            extracted_items = self._extract_adaptive_cv_defects(
                image_bytes=image_bytes,
                img_w=img_w,
                img_h=img_h,
                total_img_area=total_img_area,
            )
            if extracted_items:
                raw_detections.extend(extracted_items)
                model_tag_suffix = "adaptive_cv"

        # -------------------------------------------------------------------------
        # STAGE 4: Post-Processing, NMS & False-Positive Elimination
        # -------------------------------------------------------------------------
        # Apply NMS to remove redundant boxes
        validated_detections = apply_non_max_suppression(raw_detections, iou_threshold=0.45)

        # Calibrated spatial filters:
        # - Remove degenerate boxes (width < 1 or height < 1)
        # - Filter straight mortar course lines without fissure variance
        # - Remove full-image false positives (>95% coverage unless vegetation)
        cleaned_detections: List[DetectionItem] = []
        for det in validated_detections:
            bx1, by1, bx2, by2 = det.bounding_box
            bw = bx2 - bx1
            bh = by2 - by1
            if bw < 1.0 or bh < 1.0:
                continue
            if det.class_name == "crack" and bw > 300.0 and bh < 6.0:
                continue
            if det.coverage_ratio > 0.95 and det.class_name == "crack":
                continue
            cleaned_detections.append(det)

        validated_detections = cleaned_detections

        # Status message synthesis
        if relevance_status == "uncertain":
            status_msg = (
                "The image could not be confidently verified as a heritage structure. "
                "Please review the image or upload a clearer photograph."
            )
        elif validated_detections:
            status_msg = f"Detected {len(validated_detections)} candidate defect region(s) on structural masonry."
        else:
            status_msg = "No visible damage detected with current confidence thresholds."

        if quality_warnings:
            status_msg += f" Note: {'; '.join(quality_warnings)}"

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        model_tag = f"{self.model_version}+{model_tag_suffix}"

        return VisionResult(
            structure_type=structure_type,
            image_dimensions=resolved_dimensions,
            scale_reference=scale_reference,
            detections=validated_detections,
            processing_metadata=ProcessingMetadata(
                inference_latency_ms=latency_ms,
                model_version=model_tag,
            ),
            relevance_status=relevance_status,
            relevance_confidence=round(relevance_confidence, 4),
            quality_status=quality_status,
            rejection_reason=rejection_reason,
            needs_manual_review=needs_manual_review,
            status_message=status_msg,
        )

    def _extract_adaptive_cv_defects(
        self, image_bytes: bytes, img_w: float, img_h: float, total_img_area: float
    ) -> List[DetectionItem]:
        """Extract empirical structural crack and vegetative intrusion defects from image pixels."""
        from PIL import ImageFilter

        items: List[DetectionItem] = []
        try:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            w, h = pil_img.size

            # 1. Crack / fissure detection via local gradient and dark ridge enhancement
            gray = pil_img.convert("L")
            gray_arr = np.array(gray, dtype=np.float32)
            blur = np.array(gray.filter(ImageFilter.GaussianBlur(radius=5)), dtype=np.float32)
            edges = np.array(gray.filter(ImageFilter.FIND_EDGES), dtype=np.float32)
            diff = blur - gray_arr

            crack_mask = (diff > 14.0) & (edges > 22.0)
            y_idx, x_idx = np.where(crack_mask)

            # Requires significant connected fissure density (> 100 px) to avoid stone joint triggers
            if len(x_idx) > 100:
                xmin = max(0.0, float(np.percentile(x_idx, 5)))
                xmax = min(float(w), float(np.percentile(x_idx, 95)))
                ymin = max(0.0, float(np.percentile(y_idx, 5)))
                ymax = min(float(h), float(np.percentile(y_idx, 95)))

                bw = max(12.0, xmax - xmin)
                bh = max(12.0, ymax - ymin)
                area = round(bw * bh, 1)
                cov = round(min(1.0, area / total_img_area), 4)
                length = round(max(bw, bh), 1)
                conf = min(0.92, round(0.75 + min(0.15, len(x_idx) / 5000.0), 3))

                items.append(
                    DetectionItem(
                        class_name="crack",
                        confidence=conf,
                        bounding_box=[round(xmin, 1), round(ymin, 1), round(xmax, 1), round(ymax, 1)],
                        pixel_area=area,
                        coverage_ratio=cov,
                        component_count=max(1, int(len(x_idx) / 800)),
                        total_length_pixels=length,
                        largest_component_length_pixels=length,
                        relative_severity=(
                            RelativeSeverity.SEVERE
                            if cov > 0.15
                            else (RelativeSeverity.MODERATE if cov > 0.05 else RelativeSeverity.LOW)
                        ),
                    )
                )

            # 2. Vegetation and root intrusion detection via chromatic index (Excess Green: 2G - R - B)
            rgb_arr = np.array(pil_img, dtype=np.float32)
            exg = 2.0 * rgb_arr[:, :, 1] - rgb_arr[:, :, 0] - rgb_arr[:, :, 2]
            sum_rgb = rgb_arr[:, :, 0] + rgb_arr[:, :, 1] + rgb_arr[:, :, 2] + 1e-5
            norm_exg = exg / sum_rgb

            img_cv = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
            green_hsv = (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] >= 45) & (hsv[:, :, 2] >= 40)

            veg_mask = (exg > 30.0) & (norm_exg > 0.15) & green_hsv
            veg_ratio = float(np.mean(veg_mask))

            if veg_ratio > 0.025:
                vy, vx = np.where(veg_mask)
                v_xmin = max(0.0, float(np.percentile(vx, 5)))
                v_xmax = min(float(w), float(np.percentile(vx, 95)))
                v_ymin = max(0.0, float(np.percentile(vy, 5)))
                v_ymax = min(float(h), float(np.percentile(vy, 95)))

                v_bw = max(12.0, v_xmax - v_xmin)
                v_bh = max(12.0, v_ymax - v_ymin)
                v_area = round(v_bw * v_bh, 1)
                v_cov = round(min(1.0, veg_ratio), 4)
                v_length = round(max(v_bw, v_bh), 1)

                items.append(
                    DetectionItem(
                        class_name="vegetation_root_intrusion",
                        confidence=min(0.95, round(0.82 + veg_ratio * 0.4, 3)),
                        bounding_box=[round(v_xmin, 1), round(v_ymin, 1), round(v_xmax, 1), round(v_ymax, 1)],
                        pixel_area=v_area,
                        coverage_ratio=v_cov,
                        component_count=2,
                        total_length_pixels=v_length,
                        largest_component_length_pixels=v_length,
                        relative_severity=(
                            RelativeSeverity.SEVERE
                            if v_cov > 0.12
                            else (RelativeSeverity.MODERATE if v_cov > 0.04 else RelativeSeverity.LOW)
                        ),
                    )
                )
        except Exception as exc:
            logger.warning("Adaptive CV defect extraction encountered error: %s", exc)

        return items


vision_service = VisionService()
