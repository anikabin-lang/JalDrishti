"""SQLite-based durable metadata repository for JalDrishti inspection imagery.

Maintained by Swastik Parmar (Backend / Integration Engineer).
Minimal, robust, zero-daemon persistence adhering to project constraints.
Persists application-level identifiers, Cloudinary public/asset IDs,
dimensions, status, timestamps, and inspection associations.
"""

import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.config import settings
from backend.app.schemas.image import ImageMetadata

logger = logging.getLogger(__name__)


class MetadataPersistenceError(Exception):
    """Raised when image metadata cannot be durably written or retrieved."""
    pass


class ImageRepository:
    """Thread-safe SQLite repository managing image metadata persistence."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or settings.sqlite_db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Establish a SQLite connection with row factory enabled."""
        if self.db_path != ":memory:":
            path = Path(self.db_path)
            path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create necessary tables and indices if not already present, with auto-migration."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS image_metadata (
                        image_id TEXT PRIMARY KEY,
                        inspection_id TEXT,
                        site_id TEXT,
                        public_id TEXT NOT NULL,
                        asset_id TEXT,
                        resource_type TEXT NOT NULL DEFAULT 'image',
                        format TEXT NOT NULL,
                        width INTEGER NOT NULL,
                        height INTEGER NOT NULL,
                        bytes INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'uploaded',
                        structure_type TEXT,
                        original_filename TEXT,
                        preview_url TEXT NOT NULL,
                        thumbnail_url TEXT,
                        secure_url TEXT NOT NULL
                    );
                    """
                )
                # Auto-migrate columns for existing SQLite tables
                cursor = conn.execute("PRAGMA table_info(image_metadata);")
                columns = [row["name"] for row in cursor.fetchall()]
                if "site_id" not in columns:
                    conn.execute("ALTER TABLE image_metadata ADD COLUMN site_id TEXT;")
                if "thumbnail_url" not in columns:
                    conn.execute("ALTER TABLE image_metadata ADD COLUMN thumbnail_url TEXT;")

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_image_inspection 
                    ON image_metadata(inspection_id);
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_image_public_id 
                    ON image_metadata(public_id);
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_image_site 
                    ON image_metadata(site_id);
                    """
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error("Failed to initialize SQLite database at %s: %s", self.db_path, e)
            raise MetadataPersistenceError(f"Database initialization failed: {e}") from e

    def save(self, metadata: ImageMetadata) -> ImageMetadata:
        """Durably persist or update an image metadata record.

        Args:
            metadata: ImageMetadata instance to store.

        Returns:
            ImageMetadata: The persisted record.

        Raises:
            MetadataPersistenceError: If the record could not be written.
        """
        sql = """
        INSERT INTO image_metadata (
            image_id, inspection_id, site_id, public_id, asset_id, resource_type,
            format, width, height, bytes, created_at, status,
            structure_type, original_filename, preview_url, thumbnail_url, secure_url
        ) VALUES (
            :image_id, :inspection_id, :site_id, :public_id, :asset_id, :resource_type,
            :format, :width, :height, :bytes, :created_at, :status,
            :structure_type, :original_filename, :preview_url, :thumbnail_url, :secure_url
        )
        ON CONFLICT(image_id) DO UPDATE SET
            inspection_id = excluded.inspection_id,
            site_id = excluded.site_id,
            public_id = excluded.public_id,
            asset_id = excluded.asset_id,
            resource_type = excluded.resource_type,
            format = excluded.format,
            width = excluded.width,
            height = excluded.height,
            bytes = excluded.bytes,
            created_at = excluded.created_at,
            status = excluded.status,
            structure_type = excluded.structure_type,
            original_filename = excluded.original_filename,
            preview_url = excluded.preview_url,
            thumbnail_url = excluded.thumbnail_url,
            secure_url = excluded.secure_url;
        """
        try:
            with self._get_connection() as conn:
                conn.execute(sql, metadata.model_dump())
                conn.commit()
            return metadata
        except sqlite3.Error as e:
            logger.error("Failed to persist image metadata for image_id %s: %s", metadata.image_id, e)
            raise MetadataPersistenceError(f"Metadata persistence failed: {e}") from e
        try:
            with self._get_connection() as conn:
                conn.execute(sql, metadata.model_dump())
                conn.commit()
            return metadata
        except sqlite3.Error as e:
            logger.error("Failed to persist image metadata for image_id %s: %s", metadata.image_id, e)
            raise MetadataPersistenceError(f"Metadata persistence failed: {e}") from e

    def get_by_id(self, image_id: str) -> Optional[ImageMetadata]:
        """Retrieve image metadata by its application-level image_id."""
        sql = "SELECT * FROM image_metadata WHERE image_id = ?;"
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(sql, (image_id,))
                row = cursor.fetchone()
                if row:
                    return ImageMetadata.model_validate(dict(row))
                return None
        except sqlite3.Error as e:
            logger.error("Failed to query image metadata for image_id %s: %s", image_id, e)
            raise MetadataPersistenceError(f"Metadata query failed: {e}") from e

    def get_by_public_id(self, public_id: str) -> Optional[ImageMetadata]:
        """Retrieve image metadata by its Cloudinary public_id."""
        sql = "SELECT * FROM image_metadata WHERE public_id = ?;"
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(sql, (public_id,))
                row = cursor.fetchone()
                if row:
                    return ImageMetadata.model_validate(dict(row))
                return None
        except sqlite3.Error as e:
            logger.error("Failed to query image metadata for public_id %s: %s", public_id, e)
            raise MetadataPersistenceError(f"Metadata query failed: {e}") from e

    def list_by_inspection_id(self, inspection_id: str) -> List[ImageMetadata]:
        """Retrieve all images associated with a given inspection session."""
        sql = "SELECT * FROM image_metadata WHERE inspection_id = ? ORDER BY created_at ASC;"
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(sql, (inspection_id,))
                rows = cursor.fetchall()
                return [ImageMetadata.model_validate(dict(r)) for r in rows]
        except sqlite3.Error as e:
            logger.error("Failed to list images for inspection_id %s: %s", inspection_id, e)
            raise MetadataPersistenceError(f"Metadata listing failed: {e}") from e

    def list_images(
        self,
        site_id: Optional[str] = None,
        inspection_id: Optional[str] = None,
        structure_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[ImageMetadata], int]:
        """Query images with optional site, inspection, or typology filtering and pagination.

        Args:
            site_id: Optional heritage site identifier filter.
            inspection_id: Optional inspection session identifier filter.
            structure_type: Optional architectural typology filter.
            limit: Maximum records to return.
            offset: Number of records to skip.

        Returns:
            Tuple[List[ImageMetadata], int]: Paginated records and total match count.
        """
        clauses: List[str] = []
        params: List[Any] = []

        if site_id:
            clauses.append("site_id = ?")
            params.append(site_id)
        if inspection_id:
            clauses.append("inspection_id = ?")
            params.append(inspection_id)
        if structure_type:
            clauses.append("LOWER(structure_type) = ?")
            params.append(structure_type.lower())

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        count_sql = f"SELECT COUNT(*) FROM image_metadata {where_clause};"
        data_sql = f"SELECT * FROM image_metadata {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?;"

        try:
            with self._get_connection() as conn:
                count_cur = conn.execute(count_sql, tuple(params))
                total = count_cur.fetchone()[0]

                data_params = tuple(params) + (limit, offset)
                data_cur = conn.execute(data_sql, data_params)
                rows = data_cur.fetchall()
                records = [ImageMetadata.model_validate(dict(r)) for r in rows]
                return records, total
        except sqlite3.Error as e:
            logger.error("Failed to list images with filters: %s", e)
            raise MetadataPersistenceError(f"Image query failed: {e}") from e

    def list_sites(self) -> List[Dict[str, Any]]:
        """Retrieve aggregated heritage sites and summary metrics."""
        sql = """
        SELECT 
            COALESCE(NULLIF(site_id, ''), 'unassigned') AS site_id,
            COALESCE(MAX(structure_type), 'baoli') AS structure_type,
            COUNT(image_id) AS total_images,
            COUNT(DISTINCT inspection_id) AS total_inspections,
            MAX(created_at) AS latest_upload,
            MAX(thumbnail_url) AS cover_thumbnail_url
        FROM image_metadata
        GROUP BY COALESCE(NULLIF(site_id, ''), 'unassigned')
        ORDER BY total_images DESC;
        """
        try:
            with self._get_connection() as conn:
                cur = conn.execute(sql)
                rows = cur.fetchall()
                results = []
                for r in rows:
                    row_dict = dict(r)
                    sid = row_dict["site_id"]
                    site_name = (
                        sid.replace("_", " ").replace("-", " ").title()
                        if sid != "unassigned"
                        else "General Inspections"
                    )
                    row_dict["site_name"] = site_name
                    results.append(row_dict)
                return results
        except sqlite3.Error as e:
            logger.error("Failed to query site summaries: %s", e)
            raise MetadataPersistenceError(f"Site query failed: {e}") from e

    def delete(self, image_id: str) -> bool:
        """Delete an image record from the database.

        Returns:
            bool: True if row existed and was deleted, False otherwise.
        """
        sql = "DELETE FROM image_metadata WHERE image_id = ?;"
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(sql, (image_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error("Failed to delete image record %s: %s", image_id, e)
            raise MetadataPersistenceError(f"Metadata deletion failed: {e}") from e

    def clear(self) -> None:
        """Clear all records (primarily for testing isolation)."""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM image_metadata;")
                conn.commit()
        except sqlite3.Error as e:
            logger.error("Failed to clear image_metadata table: %s", e)
            raise MetadataPersistenceError(f"Table clear failed: {e}") from e


image_repository = ImageRepository()
