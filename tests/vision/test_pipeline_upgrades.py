"""Automated tests for the upgraded 4-Stage Computer Vision Pipeline.

Validates:
1. Relevance Gatekeeper: Rejects non-heritage images (vehicles, people, documents, etc.) with ZERO detections.
2. Undamaged Heritage Masonry: Returns ZERO false cracks (no fabricated/fallback boxes).
3. Damaged Heritage Masonry: Accurately identifies candidate cracks and biological intrusions.
4. Image Quality Assessor: Flags blurry or low-light images.
5. End-to-End API Integration: /vision/analyze and /analyze endpoints.
"""

from __future__ import annotations

import io
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import pytest

from backend.app.main import app
from backend.app.schemas.vision import StructureType, VisionResult
from backend.app.services.vision_service import assess_image_quality, vision_service
from backend.app.utils.contracts import validate_model_against_contract

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def clean_masonry_bytes() -> bytes:
    """Load an authentic undamaged heritage masonry photograph."""
    p = PROJECT_ROOT / "vision" / "demo_assets" / "bg_1_orig.jpg"
    assert p.is_file(), "bg_1_orig.jpg demo asset must exist"
    return p.read_bytes()


@pytest.fixture
def crack_masonry_bytes() -> bytes:
    """Load an authentic damaged heritage masonry photograph."""
    p = PROJECT_ROOT / "vision" / "demo_assets" / "crack_2_orig.jpg"
    assert p.is_file(), "crack_2_orig.jpg demo asset must exist"
    return p.read_bytes()


@pytest.fixture
def vehicle_bytes() -> bytes:
    """Load a non-heritage vehicle photograph."""
    p = PROJECT_ROOT / "data" / "processed" / "relevance_dataset" / "val" / "irrelevant" / "neg_val_0000_vehicle.jpg"
    assert p.is_file(), "neg_val_0000_vehicle.jpg must exist"
    return p.read_bytes()


@pytest.fixture
def document_bytes() -> bytes:
    """Load a non-heritage document photograph."""
    p = PROJECT_ROOT / "data" / "processed" / "relevance_dataset" / "val" / "irrelevant" / "neg_val_0003_document.jpg"
    assert p.is_file(), "neg_val_0003_document.jpg must exist"
    return p.read_bytes()


def test_relevance_gatekeeper_rejects_non_heritage(vehicle_bytes: bytes, document_bytes: bytes) -> None:
    """Verify Stage 2 rejects non-heritage images and produces ZERO false detections."""
    for raw_bytes in [vehicle_bytes, document_bytes]:
        res = vision_service.analyze_image(
            image_bytes=raw_bytes,
            structure_type=StructureType.BAOLI,
        )
        assert res.relevance_status == "irrelevant"
        assert res.relevance_confidence >= 0.70
        assert res.rejection_reason is not None
        assert "suitable heritage structure" in res.rejection_reason.lower() or "does not depict heritage masonry" in res.rejection_reason.lower()
        # MUST HAVE ZERO DETECTIONS
        assert len(res.detections) == 0
        validate_model_against_contract(res, "vision_result.schema.json")


def test_undamaged_masonry_has_zero_false_cracks(clean_masonry_bytes: bytes) -> None:
    """Verify Stage 4 produces ZERO false cracks on pristine/undamaged heritage masonry."""
    res = vision_service.analyze_image(
        image_bytes=clean_masonry_bytes,
        structure_type=StructureType.BAOLI,
    )
    assert res.relevance_status == "relevant"
    # Pristine background must have 0 synthetic fallback cracks
    assert len(res.detections) == 0
    assert "no visible damage" in res.status_message.lower()
    validate_model_against_contract(res, "vision_result.schema.json")


def test_damaged_masonry_identifies_defects(crack_masonry_bytes: bytes) -> None:
    """Verify Stage 3 extracts real defects on known damaged heritage masonry."""
    res = vision_service.analyze_image(
        image_bytes=crack_masonry_bytes,
        structure_type=StructureType.BAOLI,
    )
    assert res.relevance_status == "relevant"
    assert len(res.detections) >= 1
    classes = [d.class_name for d in res.detections]
    assert "crack" in classes or "vegetation_root_intrusion" in classes
    for d in res.detections:
        assert d.confidence >= 0.30
        assert len(d.bounding_box) == 4
        assert d.bounding_box[2] > d.bounding_box[0]
        assert d.bounding_box[3] > d.bounding_box[1]
    validate_model_against_contract(res, "vision_result.schema.json")


def test_image_quality_assessor() -> None:
    """Verify Stage 1 flags blurred and extreme-lighting images."""
    # Create test image
    base = Image.new("RGB", (300, 300), color=(128, 128, 128))
    draw = ImageDraw.Draw(base)
    draw.rectangle([50, 50, 250, 250], fill=(200, 200, 200))

    # Test blur
    blurred = base.filter(ImageFilter.GaussianBlur(radius=8))
    q_blur = assess_image_quality(blurred)
    assert q_blur["quality_status"] == "blurred"
    assert q_blur["laplacian_variance"] < 12.0

    # Test underexposure
    dark = ImageEnhance.Brightness(base).enhance(0.1)
    q_dark = assess_image_quality(dark)
    assert q_dark["quality_status"] == "poor_lighting"
    assert q_dark["mean_luminance"] < 40.0

    # Test overexposure
    bright = ImageEnhance.Brightness(base).enhance(2.5)
    q_bright = assess_image_quality(bright)
    assert q_bright["quality_status"] == "poor_lighting"
    assert q_bright["mean_luminance"] > 220.0


def test_api_vision_analyze_relevance_rejection(vehicle_bytes: bytes) -> None:
    """Verify POST /vision/analyze returns rejected status for vehicle image."""
    files = {"images": ("car.jpg", vehicle_bytes, "image/jpeg")}
    response = client.post("/vision/analyze", files=files)
    assert response.status_code == 200

    data = response.json()
    model = VisionResult.model_validate(data)
    assert model.relevance_status == "irrelevant"
    assert len(model.detections) == 0
    assert model.rejection_reason is not None


def test_api_unified_analyze_clean_masonry(clean_masonry_bytes: bytes) -> None:
    """Verify POST /analyze completes full pipeline for clean masonry with 100 condition score."""
    files = {"images": ("clean_baoli.jpg", clean_masonry_bytes, "image/jpeg")}
    data = {"structure_type": "baoli", "name": "Adalaj Stepwell"}
    response = client.post("/analyze", data=data, files=files)
    assert response.status_code == 200

    res_json = response.json()
    assert res_json["vision"]["relevance_status"] == "relevant"
    assert len(res_json["vision"]["detections"]) == 0
    # Condition score is 100 for clean masonry with 0 defects
    assert res_json["visual_condition"]["value"] == 100.0

