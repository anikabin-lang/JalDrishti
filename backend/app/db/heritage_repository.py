"""SQLite-based durable repository for Heritage Structures, Baseline Inspections, and Defect Passports.

Provides persistent multi-inspection tracking, Defect Passport registries,
and historical document records adhering to strict relational consistency.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class HeritageRepository:
    """Thread-safe SQLite repository for Heritage Structures and Defect Passports."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or settings.sqlite_db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        try:
            with self._get_connection() as conn:
                # 1. Heritage Structures
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS heritage_structures (
                        structure_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        typology TEXT NOT NULL,
                        location TEXT,
                        region TEXT,
                        historical_period TEXT,
                        notes TEXT,
                        baseline_completed INTEGER DEFAULT 0,
                        baseline_inspection_id TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    """
                )

                # 2. Inspections
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS inspections (
                        inspection_id TEXT PRIMARY KEY,
                        structure_id TEXT NOT NULL,
                        inspection_type TEXT NOT NULL DEFAULT 'baseline',
                        status TEXT NOT NULL DEFAULT 'in_progress',
                        inspection_date TEXT NOT NULL,
                        total_images INTEGER DEFAULT 0,
                        valid_images INTEGER DEFAULT 0,
                        total_cracks INTEGER DEFAULT 0,
                        vegetation_count INTEGER DEFAULT 0,
                        summary_json TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (structure_id) REFERENCES heritage_structures(structure_id) ON DELETE CASCADE
                    );
                    """
                )

                # 3. Inspection Images
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS inspection_images (
                        image_id TEXT PRIMARY KEY,
                        inspection_id TEXT NOT NULL,
                        structure_id TEXT NOT NULL,
                        original_filename TEXT NOT NULL,
                        preview_url TEXT,
                        secure_url TEXT,
                        quality_status TEXT DEFAULT 'good',
                        relevance_status TEXT DEFAULT 'relevant',
                        relevance_confidence REAL DEFAULT 1.0,
                        inspection_status TEXT DEFAULT 'accepted',
                        rejection_reason TEXT,
                        results_json TEXT,
                        image_order INTEGER DEFAULT 0,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (inspection_id) REFERENCES inspections(inspection_id) ON DELETE CASCADE,
                        FOREIGN KEY (structure_id) REFERENCES heritage_structures(structure_id) ON DELETE CASCADE
                    );
                    """
                )

                # 4. Defect Passports
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS defect_passports (
                        defect_id TEXT PRIMARY KEY,
                        structure_id TEXT NOT NULL,
                        defect_category TEXT NOT NULL,
                        first_detected_date TEXT NOT NULL,
                        original_inspection_id TEXT NOT NULL,
                        original_image_id TEXT NOT NULL,
                        bounding_box TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        severity TEXT DEFAULT 'moderate',
                        status TEXT DEFAULT 'active',
                        verification_status TEXT DEFAULT 'ai_detected',
                        repair_notes TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        FOREIGN KEY (structure_id) REFERENCES heritage_structures(structure_id) ON DELETE CASCADE
                    );
                    """
                )

                # 5. Defect Observations (Repeat inspections)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS defect_observations (
                        observation_id TEXT PRIMARY KEY,
                        defect_id TEXT NOT NULL,
                        inspection_id TEXT NOT NULL,
                        image_id TEXT NOT NULL,
                        bounding_box TEXT,
                        confidence REAL,
                        observed_status TEXT DEFAULT 'observed',
                        notes TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (defect_id) REFERENCES defect_passports(defect_id) ON DELETE CASCADE,
                        FOREIGN KEY (inspection_id) REFERENCES inspections(inspection_id) ON DELETE CASCADE
                    );
                    """
                )

                # 6. Uploaded Documents (Historical Reports)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS uploaded_documents (
                        document_id TEXT PRIMARY KEY,
                        structure_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        extracted_data_json TEXT,
                        status TEXT DEFAULT 'extracted',
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (structure_id) REFERENCES heritage_structures(structure_id) ON DELETE CASCADE
                    );
                    """
                )

                # 7. User Preferences (Language, etc.)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        user_id TEXT PRIMARY KEY,
                        preferred_language TEXT DEFAULT 'en',
                        updated_at TEXT NOT NULL
                    );
                    """
                )

                # Indices
                conn.execute("CREATE INDEX IF NOT EXISTS idx_insp_structure ON inspections(structure_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_img_inspection ON inspection_images(inspection_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_defect_structure ON defect_passports(structure_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_defect ON defect_observations(defect_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_structure ON uploaded_documents(structure_id);")
                conn.commit()
        except sqlite3.Error as e:
            logger.error("Failed to initialize heritage repository SQLite: %s", e)
            raise

    # -------------------------------------------------------------
    # Structure Management
    # -------------------------------------------------------------
    def create_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        structure_id = f"STR-{uuid.uuid4().hex[:8]}"
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO heritage_structures (
                    structure_id, name, typology, location, region, historical_period,
                    notes, baseline_completed, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    structure_id,
                    data["name"],
                    data.get("typology", "baoli"),
                    data.get("location", ""),
                    data.get("region", "Northern India"),
                    data.get("historical_period", ""),
                    data.get("notes", ""),
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_structure(structure_id)  # type: ignore[return-value]

    def list_structures(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.*,
                       COUNT(DISTINCT i.inspection_id) as total_inspections,
                       COUNT(DISTINCT d.defect_id) as total_defects,
                       SUM(CASE WHEN d.status = 'active' THEN 1 ELSE 0 END) as active_defects
                FROM heritage_structures s
                LEFT JOIN inspections i ON s.structure_id = i.structure_id
                LEFT JOIN defect_passports d ON s.structure_id = d.structure_id
                GROUP BY s.structure_id
                ORDER BY s.created_at DESC
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def get_structure(self, structure_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT s.*,
                       COUNT(DISTINCT i.inspection_id) as total_inspections,
                       COUNT(DISTINCT d.defect_id) as total_defects,
                       SUM(CASE WHEN d.status = 'active' THEN 1 ELSE 0 END) as active_defects
                FROM heritage_structures s
                LEFT JOIN inspections i ON s.structure_id = i.structure_id
                LEFT JOIN defect_passports d ON s.structure_id = d.structure_id
                WHERE s.structure_id = ?
                GROUP BY s.structure_id
                """,
                (structure_id,),
            ).fetchone()
            if not row:
                return None
            res = dict(row)
            res["baseline_completed"] = bool(res["baseline_completed"])
            return res

    # -------------------------------------------------------------
    # Inspection Management
    # -------------------------------------------------------------
    def create_inspection(self, structure_id: str, inspection_type: str = "baseline") -> str:
        now = datetime.now(timezone.utc).isoformat()
        inspection_id = f"INSP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO inspections (
                    inspection_id, structure_id, inspection_type, status,
                    inspection_date, created_at
                ) VALUES (?, ?, ?, 'in_progress', ?, ?)
                """,
                (inspection_id, structure_id, inspection_type, now, now),
            )
            conn.commit()
        return inspection_id

    def add_inspection_image(self, record: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO inspection_images (
                    image_id, inspection_id, structure_id, original_filename,
                    preview_url, secure_url, quality_status, relevance_status,
                    relevance_confidence, inspection_status, rejection_reason,
                    results_json, image_order, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["image_id"],
                    record["inspection_id"],
                    record["structure_id"],
                    record["original_filename"],
                    record.get("preview_url", ""),
                    record.get("secure_url", ""),
                    record.get("quality_status", "good"),
                    record.get("relevance_status", "relevant"),
                    record.get("relevance_confidence", 1.0),
                    record.get("inspection_status", "accepted"),
                    record.get("rejection_reason"),
                    json.dumps(record.get("results_json", {})),
                    record.get("image_order", 0),
                    now,
                ),
            )
            conn.commit()

    def finalize_inspection(self, inspection_id: str, summary_data: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE inspections
                SET status = 'completed',
                    total_images = ?,
                    valid_images = ?,
                    total_cracks = ?,
                    vegetation_count = ?,
                    summary_json = ?
                WHERE inspection_id = ?
                """,
                (
                    summary_data.get("total_images", 0),
                    summary_data.get("valid_images", 0),
                    summary_data.get("total_cracks", 0),
                    summary_data.get("vegetation_count", 0),
                    json.dumps(summary_data),
                    inspection_id,
                ),
            )
            # If baseline, mark structure baseline_completed = 1
            row = conn.execute("SELECT structure_id, inspection_type FROM inspections WHERE inspection_id = ?", (inspection_id,)).fetchone()
            if row and row["inspection_type"] == "baseline":
                conn.execute(
                    """
                    UPDATE heritage_structures
                    SET baseline_completed = 1,
                        baseline_inspection_id = ?,
                        updated_at = ?
                    WHERE structure_id = ?
                    """,
                    (inspection_id, now, row["structure_id"]),
                )
            conn.commit()

    def get_inspection(self, inspection_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM inspections WHERE inspection_id = ?", (inspection_id,)).fetchone()
            if not row:
                return None
            insp = dict(row)
            if insp.get("summary_json"):
                try:
                    insp["summary_data"] = json.loads(insp["summary_json"])
                except Exception:
                    insp["summary_data"] = None

            # Fetch images
            img_rows = conn.execute(
                "SELECT * FROM inspection_images WHERE inspection_id = ? ORDER BY image_order ASC",
                (inspection_id,),
            ).fetchall()
            images = []
            for ir in img_rows:
                d = dict(ir)
                if d.get("results_json"):
                    try:
                        d["results"] = json.loads(d["results_json"])
                    except Exception:
                        d["results"] = None
                images.append(d)
            insp["images"] = images
            return insp

    def list_structure_inspections(self, structure_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM inspections WHERE structure_id = ? ORDER BY created_at DESC",
                (structure_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # -------------------------------------------------------------
    # Defect Passport Management
    # -------------------------------------------------------------
    def create_defect_passport(self, data: Dict[str, Any]) -> str:
        now = datetime.now(timezone.utc).isoformat()
        defect_id = f"DEF-{uuid.uuid4().hex[:6]}"
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO defect_passports (
                    defect_id, structure_id, defect_category, first_detected_date,
                    original_inspection_id, original_image_id, bounding_box,
                    confidence, severity, status, verification_status, repair_notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    defect_id,
                    data["structure_id"],
                    data["defect_category"],
                    now,
                    data["original_inspection_id"],
                    data["original_image_id"],
                    json.dumps(data["bounding_box"]),
                    data["confidence"],
                    data.get("severity", "moderate"),
                    data.get("status", "active"),
                    data.get("verification_status", "ai_detected"),
                    data.get("repair_notes", ""),
                    now,
                    now,
                ),
            )
            conn.commit()
        return defect_id

    def list_defect_passports(self, structure_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM defect_passports WHERE structure_id = ? ORDER BY created_at DESC",
                (structure_id,),
            ).fetchall()
            res = []
            for r in rows:
                d = dict(r)
                try:
                    d["bounding_box"] = json.loads(d["bounding_box"])
                except Exception:
                    d["bounding_box"] = []
                res.append(d)
            return res

    def get_defect_passport(self, defect_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM defect_passports WHERE defect_id = ?", (defect_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["bounding_box"] = json.loads(d["bounding_box"])
            except Exception:
                d["bounding_box"] = []
            return d

    def record_defect_observation(self, data: Dict[str, Any]) -> str:
        now = datetime.now(timezone.utc).isoformat()
        obs_id = f"OBS-{uuid.uuid4().hex[:6]}"
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO defect_observations (
                    observation_id, defect_id, inspection_id, image_id,
                    bounding_box, confidence, observed_status, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    obs_id,
                    data["defect_id"],
                    data["inspection_id"],
                    data["image_id"],
                    json.dumps(data.get("bounding_box", [])),
                    data.get("confidence", 0.0),
                    data.get("observed_status", "observed"),
                    data.get("notes", ""),
                    now,
                ),
            )
            # Update updated_at on passport
            conn.execute(
                "UPDATE defect_passports SET updated_at = ? WHERE defect_id = ?",
                (now, data["defect_id"]),
            )
            conn.commit()
        return obs_id

    # -------------------------------------------------------------
    # Document Management (Historical PDFs)
    # -------------------------------------------------------------
    def save_document_record(self, data: Dict[str, Any]) -> str:
        now = datetime.now(timezone.utc).isoformat()
        doc_id = f"DOC-{uuid.uuid4().hex[:6]}"
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO uploaded_documents (
                    document_id, structure_id, filename, file_path,
                    extracted_data_json, status, created_at
                ) VALUES (?, ?, ?, ?, ?, 'extracted', ?)
                """,
                (
                    doc_id,
                    data["structure_id"],
                    data["filename"],
                    data["file_path"],
                    json.dumps(data.get("extracted_data", {})),
                    now,
                ),
            )
            conn.commit()
        return doc_id

    def get_document_record(self, document_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM uploaded_documents WHERE document_id = ?", (document_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["extracted_data"] = json.loads(d["extracted_data_json"])
            except Exception:
                d["extracted_data"] = {}
            return d

    # -------------------------------------------------------------
    # Language Preferences
    # -------------------------------------------------------------
    def get_user_language(self, user_id: str = "default_user") -> str:
        with self._get_connection() as conn:
            row = conn.execute("SELECT preferred_language FROM user_preferences WHERE user_id = ?", (user_id,)).fetchone()
            return row["preferred_language"] if row else "en"

    def set_user_language(self, lang: str, user_id: str = "default_user") -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user_preferences (user_id, preferred_language, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET preferred_language = excluded.preferred_language, updated_at = excluded.updated_at
                """,
                (user_id, lang, now),
            )
            conn.commit()


heritage_repo = HeritageRepository()

