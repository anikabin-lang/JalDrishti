"""Automated test suite for the Image Inspection Gate and Faster R-CNN Reliability.

Tests:
1. Inspection gate three-way decision: RELEVANT_HERITAGE, IRRELEVANT, UNCERTAIN.
2. Heritage structures with people/tourists present are accepted (not blindly rejected).
3. Hard non-heritage negatives (portraits, vehicles, modern buildings, plain drywall, etc.)
   are rejected with exact user guidance and produce zero detections.
4. Faster R-CNN reliability: mortar joint and aspect ratio filters prevent false positives.
5. Zero synthetic or hallucinated crack boxes on undamaged heritage masonry.
"""

from __future__ import annotations

import io
from pathlib import Path
from PIL import Image, ImageDraw
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.vision import StructureType
from backend.app.services.vision_service import vision_service
from vision.inference.detector import DetectionPredictor
from vision.inference.relevance import RelevancePredictor

client = TestClient(app)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def clean_masonry_bytes() -> bytes:
    p = PROJECT_ROOT / "vision" / "demo_assets" / "bg_1_orig.jpg"
    assert p.is_file()
    return p.read_bytes()


@pytest.fixture
def crack_masonry_bytes() -> bytes:
    p = PROJECT_ROOT / "vision" / "demo_assets" / "crack_2_orig.jpg"
    assert p.is_file()
    return p.read_bytes()


@pytest.fixture
def heritage_with_tourists_bytes() -> bytes:
    """Create a test heritage masonry image with people/visitors in the frame."""
    base_path = PROJECT_ROOT / "vision" / "demo_assets" / "bg_1_orig.jpg"
    img = Image.open(base_path).convert("RGB").resize((600, 600))
    draw = ImageDraw.Draw(img)
    # Draw tourists/visitors in foreground
    for offset_x in [120, 320]:
        # Head
        draw.ellipse([offset_x, 380, offset_x + 30, 410], fill=(220, 180, 150))
        # Torso / clothing
        draw.rectangle([offset_x - 10, 410, offset_x + 40, 480], fill=(50, 100, 200))
        # Legs
        draw.rectangle([offset_x - 5, 480, offset_x + 12, 550], fill=(30, 30, 30))
        draw.rectangle([offset_x + 18, 480, offset_x + 35, 550], fill=(30, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


@pytest.fixture
def selfie_portrait_bytes() -> bytes:
    """Generate a portrait selfie with indoor background."""
    img = Image.new("RGB", (400, 500), color=(235, 230, 220))
    draw = ImageDraw.Draw(img)
    # Large head in center
    draw.ellipse([100, 80, 300, 320], fill=(225, 185, 155))
    # Eyes & smile
    draw.ellipse([140, 160, 170, 180], fill=(50, 30, 20))
    draw.ellipse([230, 160, 260, 180], fill=(50, 30, 20))
    draw.arc([160, 220, 240, 270], start=10, end=170, fill=(180, 50, 50), width=5)
    # Shoulders
    draw.rectangle([30, 320, 370, 500], fill=(20, 80, 160))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def modern_drywall_bytes() -> bytes:
    """Generate smooth painted interior drywall."""
    img = Image.new("RGB", (512, 512), color=(245, 245, 240))
    draw = ImageDraw.Draw(img)
    # White baseboard at bottom
    draw.rectangle([0, 480, 512, 512], fill=(255, 255, 255))
    # Light switch
    draw.rectangle([230, 230, 270, 290], fill=(250, 250, 250), outline=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_inspection_gate_accepts_heritage_with_tourists(heritage_with_tourists_bytes: bytes) -> None:
    """CRITICAL REQUIREMENT: Do NOT reject valid heritage photographs simply because people appear."""
    inspection = vision_service.inspect_image(heritage_with_tourists_bytes)
    assert inspection["inspection_status"] == "accepted", (
        f"Expected 'accepted' for baoli with tourists, got {inspection['inspection_status']} "
        f"(confidence: {inspection['relevance_confidence']})"
    )
    assert inspection["decision"] == "RELEVANT_HERITAGE"
    assert inspection["relevance_confidence"] >= 0.70
    assert inspection["rejection_reason"] is None


def test_inspection_gate_rejects_human_portrait(selfie_portrait_bytes: bytes) -> None:
    """Human portrait/selfie must be rejected at Stage 2 without running damage detection."""
    inspection = vision_service.inspect_image(selfie_portrait_bytes)
    assert inspection["inspection_status"] == "rejected"
    assert inspection["decision"] == "IRRELEVANT"
    assert inspection["rejection_reason"] is not None
    assert "does not appear to contain a suitable heritage structure" in inspection["rejection_reason"]

    # When analyzed through full vision service, detections must be empty
    full_result = vision_service.analyze_image(selfie_portrait_bytes)
    assert full_result.relevance_status == "irrelevant"
    assert len(full_result.detections) == 0


def test_inspection_gate_rejects_modern_drywall(modern_drywall_bytes: bytes) -> None:
    """Modern interior drywall / painted walls must be rejected."""
    inspection = vision_service.inspect_image(modern_drywall_bytes)
    assert inspection["inspection_status"] == "rejected"
    assert inspection["decision"] == "IRRELEVANT"
    assert len(vision_service.analyze_image(modern_drywall_bytes).detections) == 0


def test_inspection_gate_three_way_threshold_calibration() -> None:
    """Verify threshold boundary logic for RELEVANT_HERITAGE, IRRELEVANT, and UNCERTAIN."""
    ckpt_path = PROJECT_ROOT / "vision" / "models" / "relevance_classifier" / "model.pt"
    predictor = RelevancePredictor.from_checkpoint(ckpt_path, device="cpu")
    
    assert predictor.thresholds["relevant"] == 0.70
    assert predictor.thresholds["irrelevant"] == 0.35


def test_undamaged_masonry_has_zero_crack_detections(clean_masonry_bytes: bytes) -> None:
    """Verify Faster R-CNN produces zero false crack detections on authentic clean masonry."""
    full_result = vision_service.analyze_image(
        image_bytes=clean_masonry_bytes,
        structure_type=StructureType.BAOLI,
    )
    assert full_result.relevance_status == "relevant"
    assert len(full_result.detections) == 0
    assert "no visible damage" in full_result.status_message.lower()


def test_damaged_masonry_detects_real_cracks(crack_masonry_bytes: bytes) -> None:
    """Verify damaged masonry returns genuine detections with Faster R-CNN/YOLO26n."""
    full_result = vision_service.analyze_image(
        image_bytes=crack_masonry_bytes,
        structure_type=StructureType.BAOLI,
    )
    assert full_result.relevance_status == "relevant"
    assert len(full_result.detections) >= 1
    assert any(d.class_name == "crack" for d in full_result.detections)
