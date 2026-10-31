"""Tests for JalDrishti Enterprise Heritage AI Features:
1. 15-Language Preferences
2. Structure Registration
3. Mandatory 3-Photo Baseline Inspection Gate
4. Defect Passports & Repeat Inspection Matching
5. Multilingual PDF Generation
6. Historical PDF Extraction & Confirmation
"""

import io
from fastapi.testclient import TestClient
import pytest
from reportlab.pdfgen import canvas

from backend.app.main import app

client = TestClient(app)


def test_language_preferences():
    # 1. Default language
    res = client.get("/preferences/language")
    assert res.status_code == 200
    assert "language" in res.json()

    # 2. Update to Hindi
    res = client.put("/preferences/language", json={"language": "hi"})
    assert res.status_code == 200
    assert res.json()["language"] == "hi"

    # 3. Verify persistence
    res = client.get("/preferences/language")
    assert res.status_code == 200
    assert res.json()["language"] == "hi"

    # 4. Update to Urdu (RTL)
    res = client.put("/preferences/language", json={"language": "ur"})
    assert res.status_code == 200
    assert res.json()["language"] == "ur"


def test_structure_creation_and_listing():
    payload = {
        "name": "Raniji ki Baoli",
        "typology": "baoli",
        "location": "Bundi, Rajasthan",
        "region": "Northern India",
        "historical_period": "17th Century Rajput",
    }
    res = client.post("/structures", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "structure_id" in data
    assert data["name"] == "Raniji ki Baoli"
    assert data["baseline_completed"] is False

    structure_id = data["structure_id"]

    # Verify in list
    res_list = client.get("/structures")
    assert res_list.status_code == 200
    structures = res_list.json()
    assert any(s["structure_id"] == structure_id for s in structures)

    # Verify detail
    res_detail = client.get(f"/structures/{structure_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["structure"]["structure_id"] == structure_id


def test_baseline_inspection_enforces_minimum_3_photos():
    # Create structure
    res_str = client.post("/structures", json={"name": "Panna Meena ka Kund", "typology": "kund"})
    structure_id = res_str.json()["structure_id"]

    sample_image = open("vision/demo_assets/crack_2_orig.jpg", "rb").read()

    # Case A: Only 2 photos uploaded -> MUST FAIL with 400 Bad Request
    files_two = [
        ("files", ("photo1.jpg", sample_image, "image/jpeg")),
        ("files", ("photo2.jpg", sample_image, "image/jpeg")),
    ]
    res_fail = client.post(f"/structures/{structure_id}/inspections/baseline", files=files_two)
    assert res_fail.status_code == 400
    assert "minimum of 3 photographs" in res_fail.json()["detail"]

    # Case B: 3 valid photos uploaded -> MUST SUCCEED and finalize baseline
    sample_crack3 = open("vision/demo_assets/crack_3_orig.jpg", "rb").read()
    sample_veg = open("vision/demo_assets/veg_1_orig.jpg", "rb").read()

    files_three = [
        ("files", ("view_1.jpg", sample_image, "image/jpeg")),
        ("files", ("view_2.jpg", sample_crack3, "image/jpeg")),
        ("files", ("view_3.jpg", sample_veg, "image/jpeg")),
    ]
    res_success = client.post(f"/structures/{structure_id}/inspections/baseline", files=files_three)
    assert res_success.status_code == 200
    data = res_success.json()
    assert data["status"] == "completed"
    assert data["baseline_completed"] is True
    assert data["summary"]["valid_images"] == 3
    assert data["defects_registered"] > 0
    assert len(data["passports"]) > 0

    inspection_id = data["inspection_id"]

    # Verify Defect Passports exist in structure detail
    res_detail = client.get(f"/structures/{structure_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["structure"]["baseline_completed"] is True
    assert len(detail["passports"]) > 0

    # Repeat inspection matching
    repeat_files = [("files", ("repeat_view_1.jpg", sample_image, "image/jpeg"))]
    res_repeat = client.post(f"/structures/{structure_id}/inspections/repeat", files=repeat_files)
    assert res_repeat.status_code == 200
    rep_data = res_repeat.json()
    assert rep_data["status"] == "completed"
    assert rep_data["summary"]["valid_images"] == 1
    assert rep_data["summary"]["matched_defects"] >= 1


def test_multilingual_pdf_export():
    # Fetch latest inspection
    res_list = client.get("/structures")
    structures = res_list.json()
    valid_str = [s for s in structures if s.get("baseline_inspection_id")]
    if not valid_str:
        pytest.skip("No baseline inspection available to test PDF export.")

    inspection_id = valid_str[0]["baseline_inspection_id"]

    # Test PDF download in English
    res_en = client.get(f"/inspections/{inspection_id}/pdf?lang=en")
    assert res_en.status_code == 200
    assert res_en.headers["content-type"] == "application/pdf"
    assert len(res_en.content) > 1000

    # Test PDF download in Hindi
    res_hi = client.get(f"/inspections/{inspection_id}/pdf?lang=hi")
    assert res_hi.status_code == 200
    assert res_hi.headers["content-type"] == "application/pdf"
    assert len(res_hi.content) > 1000

    # Test PDF download in Urdu
    res_ur = client.get(f"/inspections/{inspection_id}/pdf?lang=ur")
    assert res_ur.status_code == 200
    assert res_ur.headers["content-type"] == "application/pdf"
    assert len(res_ur.content) > 1000


def test_historical_pdf_extraction_and_import():
    # 1. Create a dummy survey PDF using ReportLab in memory
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "Historic Inspection Survey Report for Agrasen ki Baoli")
    c.drawString(100, 720, "Survey Date: 12/04/2018")
    c.drawString(100, 690, "Severe structural crack observed along the southern subterranean corridor.")
    c.drawString(100, 660, "Extensive vegetation and fig roots penetrating upper arch stone masonry joints.")
    c.drawString(100, 630, "Action Required: Repoint decayed joints with lime-surkhi pozzolanic mortar.")
    c.save()
    pdf_bytes = buf.getvalue()

    # 2. Create structure
    res_str = client.post("/structures", json={"name": "Historical Test Baoli", "typology": "baoli"})
    structure_id = res_str.json()["structure_id"]

    # 3. Upload & extract
    res_doc = client.post(
        f"/structures/{structure_id}/documents/upload",
        files={"file": ("survey_2018.pdf", pdf_bytes, "application/pdf")},
    )
    assert res_doc.status_code == 200
    doc_data = res_doc.json()
    assert "document_id" in doc_data
    assert len(doc_data["extracted_defects"]) >= 1

    document_id = doc_data["document_id"]

    # 4. Confirm and import defects
    confirm_payload = [
        {
            "category": "crack",
            "severity": "severe",
            "description": "Severe structural crack along southern subterranean corridor",
            "page_number": 1,
        }
    ]
    res_import = client.post(
        f"/structures/{structure_id}/documents/{document_id}/import-defects",
        json=confirm_payload,
    )
    assert res_import.status_code == 200
    import_data = res_import.json()
    assert import_data["status"] == "success"
    assert import_data["imported_count"] == 1
    assert len(import_data["passports"]) == 1

    # Verify imported passport in structure
    res_detail = client.get(f"/structures/{structure_id}")
    assert res_detail.status_code == 200
    passports = res_detail.json()["passports"]
    assert any(p["defect_id"] == import_data["passports"][0] for p in passports)

