#!/usr/bin/env python3
"""Interactive test tool for JalDrishti Image Inspection Gate & Vision Pipeline.

Usage:
    # Test a specific image:
    python scripts/vision/test_single_image.py path/to/your/image.jpg

    # Run quick test on representative demo assets across categories:
    python scripts/vision/test_single_image.py
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.schemas.vision import StructureType
from backend.app.services.vision_service import vision_service


def print_banner(text: str) -> None:
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)


def test_image(image_path: Path, label: str = "") -> dict:
    if not image_path.is_file():
        print(f"❌ Error: File not found: {image_path}")
        return {}

    image_bytes = image_path.read_bytes()
    header = f"TESTING: {image_path.name}"
    if label:
        header += f" [{label}]"
    print_banner(header)

    # 1. Test Stage 1 & 2 Fast Inspection Gate
    t0 = time.perf_counter()
    gate_res = vision_service.inspect_image(image_bytes)
    t_gate_ms = (time.perf_counter() - t0) * 1000.0

    print("🔎 STAGE 1 & 2: IMAGE INSPECTION GATE")
    decision = gate_res["decision"]
    if decision == "RELEVANT_HERITAGE":
        status_icon = "✅"
    elif decision == "IRRELEVANT":
        status_icon = "🛑"
    else:
        status_icon = "⚠️"

    print(f"   Decision:              {status_icon} {decision}")
    print(f"   Inspection Status:     {gate_res['inspection_status']}")
    print(f"   Relevance Confidence: {gate_res['relevance_confidence']:.2%}")
    print(f"   Quality Status:        {gate_res['quality_status']}")
    if gate_res.get("quality_warnings"):
        print(f"   Quality Warnings:      {gate_res['quality_warnings']}")
    if gate_res.get("rejection_reason"):
        print(f"   Rejection Reason:      \"{gate_res['rejection_reason']}\"")
    print(f"   Needs Manual Review:   {gate_res['needs_manual_review']}")
    print(f"   Gate Latency:          {t_gate_ms:.1f} ms")

    # 2. Test Full Vision Pipeline (Stage 3 & 4 Damage Detection)
    print("\n🔬 FULL VISION PIPELINE (Stages 1-4)")
    t0 = time.perf_counter()
    full_res = vision_service.analyze_image(image_bytes=image_bytes, structure_type=StructureType.BAOLI)
    t_full_ms = (time.perf_counter() - t0) * 1000.0

    print(f"   Structure Type:        {full_res.structure_type.value}")
    print(f"   Relevance Status:      {full_res.relevance_status}")
    print(f"   Defect Detections:     {len(full_res.detections)} detected")
    for idx, d in enumerate(full_res.detections, 1):
        box_str = f"[{d.bounding_box[0]:.1f}, {d.bounding_box[1]:.1f}, {d.bounding_box[2]:.1f}, {d.bounding_box[3]:.1f}]"
        print(f"     #{idx}: {d.class_name} | conf: {d.confidence:.2%} | box: {box_str}")
    print(f"   Status Message:        \"{full_res.status_message}\"")
    print(f"   Total Analysis Time:   {t_full_ms:.1f} ms")

    return {
        "decision": decision,
        "detections": len(full_res.detections),
        "gate_latency_ms": t_gate_ms,
        "total_latency_ms": t_full_ms,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Test JalDrishti Inspection Gate & Pipeline")
    parser.add_argument("image_path", nargs="?", help="Path to image file to test")
    args = parser.parse_args()

    if args.image_path:
        test_image(Path(args.image_path))
    else:
        print_banner("RUNNING MULTI-CATEGORY DEMO VERIFICATION")
        print("No image path provided. Testing representative sample across 5 key categories:")

        demos = [
            (PROJECT_ROOT / "vision" / "demo_assets" / "crack_2_orig.jpg", "Heritage Masonry with Cracks"),
            (PROJECT_ROOT / "vision" / "demo_assets" / "bg_1_orig.jpg", "Undamaged Heritage Masonry"),
            (PROJECT_ROOT / "data" / "processed" / "enhanced_relevance_dataset" / "val" / "heritage_masonry" / "pos_tourist_0003.jpg", "Baoli / Heritage with Tourists & People"),
            (PROJECT_ROOT / "data" / "processed" / "enhanced_relevance_dataset" / "val" / "irrelevant" / "neg_portrait_selfie_0003.jpg", "Human Portrait / Selfie (Hard Negative)"),
            (PROJECT_ROOT / "data" / "processed" / "enhanced_relevance_dataset" / "val" / "irrelevant" / "neg_vehicle_0011.jpg", "Vehicle / Car (Irrelevant Non-Heritage)"),
        ]

        for p, label in demos:
            if p.is_file():
                test_image(p, label)
            else:
                print(f"⚠️ Demo file not found: {p}")

        print_banner("DEMO VERIFICATION COMPLETE")
        print("To test any custom image, run:")
        print("  python scripts/vision/test_single_image.py /path/to/any_image.jpg\n")


if __name__ == "__main__":
    main()
