"""Security Controls and Abuse Prevention Verification Tests.

Verifies:
1. Sliding-window IP rate limiting (429 Too Many Requests with Retry-After).
2. Privileged access control on asset deletion (401 Unauthorized / 403 Forbidden with ADMIN_API_KEY).
3. Directory traversal prevention on PDF embedded image extraction.
4. Input validation and bounded payload limits on baseline inspections and survey uploads.
5. Duplicate photograph detection in multi-photo inspections.
"""

import io
from unittest.mock import MagicMock, patch
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.security import _global_limiter, SlidingWindowRateLimiter
from backend.app.services.document_extraction_service import document_extraction_service


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset rate limiter state before each test."""
    _global_limiter._history.clear()
    yield
    _global_limiter._history.clear()


def create_test_image_bytes(format="JPEG", size=(64, 64), color=(120, 100, 80)) -> bytes:
    """Helper to generate valid dummy image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


def test_rate_limiting_sliding_window_blocks_excessive_requests():
    """Verify that requests exceeding configured rate limit trigger HTTP 429."""
    client = TestClient(app)
    limiter = SlidingWindowRateLimiter(window_seconds=60)

    # Test standalone limiter behavior
    client_ip = "192.168.1.100"
    bucket = "test_bucket"
    limit = 5

    for _ in range(limit):
        allowed, retry_after = limiter.is_allowed(client_ip, bucket, limit)
        assert allowed is True
        assert retry_after == 0

    # Next request should be throttled
    allowed, retry_after = limiter.is_allowed(client_ip, bucket, limit)
    assert allowed is False
    assert retry_after > 0


def test_rate_limiting_endpoint_integration():
    """Verify endpoint returns HTTP 429 when bucket limit is exhausted."""
    client = TestClient(app)

    # Cloud search bucket has a limit of 30 req/min
    with patch("backend.app.services.cloudinary_service.cloudinary_service.is_configured", return_value=True), \
         patch("backend.app.services.cloudinary_service.cloudinary_service.search_assets", return_value={"total_count": 0, "resources": []}):

        # Send 30 allowed requests
        for _ in range(30):
            res = client.get("/images/cloud-search?query=test")
            assert res.status_code == 200

        # The 31st request must trigger HTTP 429
        res_blocked = client.get("/images/cloud-search?query=test")
        assert res_blocked.status_code == 429
        assert "Retry-After" in res_blocked.headers
        assert "Rate limit exceeded" in res_blocked.json()["detail"]


def test_privileged_delete_requires_admin_key_when_configured():
    """Verify that DELETE /images/{id} enforces ADMIN_API_KEY when set in config."""
    client = TestClient(app)

    with patch.object(settings, "admin_api_key", "super-secret-admin-token-12345"):
        # 1. Unauthenticated request -> 401 Unauthorized
        res_no_auth = client.delete("/images/img_test_123")
        assert res_no_auth.status_code == 401

        # 2. Invalid API key -> 403 Forbidden
        res_wrong_key = client.delete(
            "/images/img_test_123",
            headers={"X-API-Key": "wrong-key-value"}
        )
        assert res_wrong_key.status_code == 403

        # 3. Valid API key (mocking repo get so we don't depend on db row)
        with patch("backend.app.db.image_repository.image_repository.get_by_id", return_value=None):
            res_valid = client.delete(
                "/images/img_test_123",
                headers={"X-API-Key": "super-secret-admin-token-12345"}
            )
            # Passed auth, reached endpoint logic (404 since record doesn't exist)
            assert res_valid.status_code == 404


def test_pdf_extraction_prevents_path_traversal():
    """Verify that document extraction prevents directory traversal attacks via crafted image names."""
    # Create a minimal fake PDF with an image object named maliciously
    fake_pdf = b"%PDF-1.4\n%Fake PDF content for security traversal test\n%%EOF"

    # Mock pypdf reader to return an image with traversal path name
    mock_page = MagicMock()
    mock_img = MagicMock()
    mock_img.name = "../../../../../etc/passwd"
    mock_img.data = b"malicious binary payload"
    mock_page.images = [mock_img]
    mock_page.extract_text.return_value = "Test page text"

    with patch("pypdf.PdfReader") as mock_reader:
        instance = mock_reader.return_value
        instance.pages = [mock_page]

        result = document_extraction_service.extract_from_pdf_bytes(
            fake_pdf,
            filename="traversal_test.pdf"
        )

        # Confirm extracted image was saved safely inside storage_dir, NOT in /etc/
        assert len(result["extracted_images"]) <= 1
        if result["extracted_images"]:
            saved_path = result["extracted_images"][0]["path"]
            assert "/etc/passwd" not in saved_path
            assert "extracted_documents" in saved_path


def test_pdf_extraction_rejects_non_pdf():
    """Verify that files lacking %PDF- magic bytes are rejected."""
    non_pdf = b"NOT_A_PDF_FILE_HEADER"
    with pytest.raises(ValueError, match="Invalid PDF format"):
        document_extraction_service.extract_from_pdf_bytes(non_pdf, filename="fake.pdf")


def test_baseline_inspection_enforces_photo_limits():
    """Verify baseline inspection enforces minimum 3 and maximum 10 photographs."""
    client = TestClient(app)

    # Mock structure existence
    with patch("backend.app.db.heritage_repository.heritage_repo.get_structure", return_value={"structure_id": "struct_test", "typology": "baoli"}):
        res_under = client.post(
            "/structures/struct_test/inspections/baseline",
            files=[
                ("files", ("p1.jpg", create_test_image_bytes(), "image/jpeg")),
                ("files", ("p2.jpg", create_test_image_bytes(), "image/jpeg")),
            ]
        )
        assert res_under.status_code == 400
        assert "minimum of 3 photographs" in res_under.json()["detail"]

        # 2. More than 10 photos -> 400 Bad Request
        eleven_files = [
            ("files", (f"p{i}.jpg", create_test_image_bytes(), "image/jpeg"))
            for i in range(11)
        ]
        res_over = client.post(
            "/structures/struct_test/inspections/baseline",
            files=eleven_files
        )
        assert res_over.status_code == 400
        assert "Maximum 10 photographs" in res_over.json()["detail"]


def test_baseline_inspection_duplicate_detection():
    """Verify duplicate photos within a baseline inspection are flagged and rejected."""
    client = TestClient(app)
    identical_photo = create_test_image_bytes()

    with patch("backend.app.db.heritage_repository.heritage_repo.get_structure", return_value={"structure_id": "struct_test", "typology": "baoli"}), \
         patch("backend.app.db.heritage_repository.heritage_repo.create_inspection", return_value="insp_sec_test"), \
         patch("backend.app.db.heritage_repository.heritage_repo.add_inspection_image", return_value=True), \
         patch("backend.app.services.vision_service.vision_service.inspect_image", return_value={"inspection_status": "accepted", "relevance_confidence": 0.95}):

        files = [
            ("files", ("view1.jpg", identical_photo, "image/jpeg")),
            ("files", ("view2.jpg", identical_photo, "image/jpeg")),  # Duplicate!
            ("files", ("view3.jpg", create_test_image_bytes(color=(200, 200, 200)), "image/jpeg")),
        ]

        res = client.post(
            "/structures/struct_test/inspections/baseline",
            files=files
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "incomplete"
        # Only 2 distinct photos, so valid_images < 3
        assert data["baseline_completed"] is False
        assert any("Duplicate photograph detected" in (img.get("rejection_reason") or "") for img in data["images"])
