"""Service for extracting text, structure metadata, historical defects, and embedded photographs from heritage survey PDFs.

Part of JalDrishti Enterprise Feature 6 (Historical PDF Report Extraction & Defect Migration).
"""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid

import pypdf

logger = logging.getLogger(__name__)


class DocumentExtractionService:
    """Extracts metadata, past defect findings, and embedded photographs from historical inspection PDFs."""

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        self.storage_dir = Path(storage_dir or "data/extracted_documents")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def extract_from_pdf_bytes(
        self,
        pdf_bytes: bytes,
        filename: str,
        structure_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract metadata, defects, recommendations, and embedded images from a PDF file.

        Enforces security bounds:
        - Validates magic PDF header bytes (b'%PDF-').
        - Restricts maximum PDF file size to 25 MB.
        - Limits maximum pages processed (50 pages) to prevent CPU/memory exhaustion.
        - Sanitizes embedded image filenames against path traversal.
        - Caps extracted image count to prevent disk space exhaustion.
        """
        # 1. Payload size check (25 MB max)
        max_bytes = 25 * 1024 * 1024
        if len(pdf_bytes) > max_bytes:
            raise ValueError(f"PDF exceeds maximum permitted size of 25 MB ({len(pdf_bytes)} bytes).")

        # 2. Magic header check (must contain %PDF- in the header)
        if b"%PDF-" not in pdf_bytes[:1024]:
            raise ValueError("Invalid PDF format: File header does not match standard PDF magic bytes.")

        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        output_image_dir = (self.storage_dir / doc_id / "images").resolve()
        output_image_dir.mkdir(parents=True, exist_ok=True)

        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        except Exception as e:
            raise ValueError(f"Corrupted or unreadable PDF document: {e}") from e

        total_pages = len(reader.pages)
        if total_pages > 50:
            raise ValueError(f"PDF exceeds maximum page limit (50 pages). Document has {total_pages} pages.")

        extracted_text_pages: List[str] = []
        extracted_images: List[Dict[str, Any]] = []
        max_images = 30

        for page_idx, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            extracted_text_pages.append(page_text)

            # Extract embedded images with traversal prevention
            try:
                for img_idx, img_obj in enumerate(page.images, start=1):
                    if len(extracted_images) >= max_images:
                        break

                    # Defensive extension and filename sanitation
                    raw_name = getattr(img_obj, "name", "image.jpg")
                    ext = "jpg"
                    if "." in raw_name:
                        candidate_ext = raw_name.rsplit(".", 1)[-1].lower()
                        if candidate_ext in ("jpg", "jpeg", "png", "webp"):
                            ext = candidate_ext

                    safe_suffix = uuid.uuid4().hex[:8]
                    img_filename = f"page_{page_idx}_img_{img_idx}_{safe_suffix}.{ext}"
                    img_path = (output_image_dir / img_filename).resolve()

                    # Enforce strict directory containment
                    if not str(img_path).startswith(str(output_image_dir)):
                        logger.warning("Path traversal attempt blocked for image: %s", raw_name)
                        continue

                    with open(img_path, "wb") as f_img:
                        f_img.write(img_obj.data)

                    extracted_images.append(
                        {
                            "image_id": f"img_extracted_{uuid.uuid4().hex[:8]}",
                            "page": page_idx,
                            "filename": img_filename,
                            "path": str(img_path),
                            "format": ext,
                            "size_bytes": len(img_obj.data),
                        }
                    )
            except Exception as e:
                logger.warning("Could not extract images from page %d: %s", page_idx, e)

        full_text = "\n".join(extracted_text_pages)

        # Parse structure name
        structure_name = self._parse_structure_name(full_text)
        # Parse inspection date
        inspection_date = self._parse_date(full_text)
        # Parse defects
        defects = self._parse_defects(extracted_text_pages)
        # Parse recommendations / repairs
        recommendations = self._parse_recommendations(full_text)

        return {
            "document_id": doc_id,
            "structure_id": structure_id or "",
            "filename": filename,
            "status": "extracted",
            "total_pages": total_pages,
            "extracted_structure_name": structure_name,
            "extracted_inspection_date": inspection_date,
            "extracted_defects": defects,
            "extracted_recommendations": recommendations,
            "extracted_photos_count": len(extracted_images),
            "extracted_images": extracted_images,
        }

    def _parse_structure_name(self, text: str) -> Optional[str]:
        patterns = [
            r"(?:Structure|Monument|Site|Building|Asset)\s*(?:Name)?\s*[:\-]\s*([^\n\r,;.]+)",
            r"(?:Baoli|Stepwell|Kund|Vav|Bawari)\s*(?:Name)?\s*[:\-]?\s*([A-Za-z0-9\s\-]+?)(?:\n|\r|,|;)",
            r"(?:Inspection\s+Report\s+(?:for|of)\s+)([^\n\r,;.]+)",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if 3 < len(candidate) < 80:
                    return candidate
        return None

    def _parse_date(self, text: str) -> Optional[str]:
        date_patterns = [
            r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
            r"\b(\d{4}-\d{2}-\d{2})\b",
            r"\b(?:Date|Survey\s+Date|Inspection\s+Date)\s*[:\-]\s*([A-Za-z0-9\s,]+?)(?:\n|\r|$)",
        ]
        for pat in date_patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _parse_defects(self, pages: List[str]) -> List[Dict[str, Any]]:
        defect_keywords = {
            "crack": ["crack", "fracture", "fissure", "structural separation", "shear crack", "split"],
            "vegetation": ["vegetation", "plant", "biological growth", "moss", "lichen", "roots", "shrub", "weed"],
            "dampness": ["damp", "seepage", "moisture", "water infiltration", "waterlogging", "leakage"],
            "spalling": ["spall", "flaking", "delamination", "stone loss", "detachment", "weathering"],
            "mortar_decay": ["joint decay", "mortar washout", "missing mortar", "cement pointing", "eroded joint"],
            "efflorescence": ["salt efflorescence", "salts", "subflorescence", "white encrustation"],
        }

        found_defects: List[Dict[str, Any]] = []
        seen_descriptions = set()

        for page_idx, page_text in enumerate(pages, start=1):
            sentences = re.split(r"(?<=[.!?\n])\s+", page_text)
            for sentence in sentences:
                sentence_clean = sentence.strip()
                if len(sentence_clean) < 15 or len(sentence_clean) > 250:
                    continue

                sentence_lower = sentence_clean.lower()
                for category, kws in defect_keywords.items():
                    if any(kw in sentence_lower for kw in kws):
                        severity = "moderate"
                        if any(w in sentence_lower for w in ["severe", "deep", "major", "critical", "heavy", "extensive"]):
                            severity = "severe"
                        elif any(w in sentence_lower for w in ["hairline", "minor", "slight", "surface", "light"]):
                            severity = "low"

                        norm_desc = re.sub(r"\s+", " ", sentence_clean)
                        if norm_desc not in seen_descriptions:
                            seen_descriptions.add(norm_desc)
                            found_defects.append(
                                {
                                    "description": norm_desc,
                                    "category": category,
                                    "severity": severity,
                                    "page_number": page_idx,
                                    "confirmed": False,
                                }
                            )
                        break

        return found_defects

    def _parse_recommendations(self, text: str) -> List[str]:
        recommendations: List[str] = []
        rec_patterns = [
            r"(?:Recommendation|Action\s+Required|Proposed\s+Intervention|Preservation\s+Measure)\s*[:\-]\s*([^\n\r]+)",
            r"(?:Repoint[a-z\s]+with\s+lime\s+mortar[^\n\r.]+)",
            r"(?:Remove[a-z\s]+vegetation[^\n\r.]+)",
            r"(?:Desilt[a-z\s]+basin[^\n\r.]+)",
        ]
        for pat in rec_patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                item = m.group(0).strip()
                if item and item not in recommendations and len(item) < 200:
                    recommendations.append(item)

        return recommendations[:10]


document_extraction_service = DocumentExtractionService()

