"""Image and inspection metadata schemas for JalDrishti.

Maintained by Swastik Parmar (Backend / Integration Engineer).
Defines contracts for backend-controlled Cloudinary image ingestion,
responsive preview delivery, original inspection traceability,
and metadata persistence.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ImageUploadResponse(BaseModel):
    """Public contract returned to frontend upon successful image upload."""

    model_config = ConfigDict(extra="ignore")

    image_id: str = Field(
        ..., description="Stable internal application-level image identifier"
    )
    inspection_id: Optional[str] = Field(
        default=None, description="Associated inspection or survey identifier"
    )
    site_id: Optional[str] = Field(
        default=None, description="Associated heritage site identifier"
    )
    status: str = Field(
        default="uploaded", description="Current status of the image asset"
    )
    preview_url: str = Field(
        ..., description="Optimized responsive preview URL for frontend presentation"
    )
    thumbnail_url: Optional[str] = Field(
        default=None,
        description="Optimized square thumbnail URL for card and grid displays",
    )
    original_url: Optional[str] = Field(
        default=None,
        description="Secure delivery URL for the uncompressed original image",
    )
    format: str = Field(..., description="Verified image format (e.g. jpeg, png, webp)")
    width: int = Field(..., ge=1, description="Image width in pixels")
    height: int = Field(..., ge=1, description="Image height in pixels")
    bytes: int = Field(..., ge=0, description="Payload size in bytes")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")


class HeritageImageSummary(BaseModel):
    """Rich presentation summary of a heritage image for gallery and inspection exploration."""

    model_config = ConfigDict(extra="ignore")

    image_id: str = Field(..., description="Application-level image identifier")
    site_id: Optional[str] = Field(default=None, description="Heritage site identifier")
    inspection_id: Optional[str] = Field(
        default=None, description="Inspection session identifier"
    )
    public_id: str = Field(..., description="Cloudinary storage public ID")
    asset_id: Optional[str] = Field(
        default=None, description="Cloudinary asset identifier"
    )
    format: str = Field(..., description="File format extension")
    width: int = Field(..., ge=1, description="Image width in pixels")
    height: int = Field(..., ge=1, description="Image height in pixels")
    bytes: int = Field(..., ge=0, description="File size in bytes")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    status: str = Field(default="uploaded", description="Lifecycle status")
    structure_type: Optional[str] = Field(
        default=None, description="Heritage typology (e.g. baoli, kund, vav)"
    )
    original_filename: Optional[str] = Field(
        default=None, description="Original uploaded filename"
    )
    preview_url: str = Field(..., description="Optimized responsive preview URL")
    thumbnail_url: str = Field(
        ..., description="Optimized square thumbnail URL for gallery cards"
    )
    original_url: str = Field(
        ..., description="Uncompressed original delivery URL for detailed inspection"
    )


class ImageMetadata(BaseModel):
    """Full internal persistence record stored in SQLite metadata repository."""

    model_config = ConfigDict(extra="ignore")

    image_id: str = Field(..., description="Stable internal unique identifier")
    inspection_id: Optional[str] = Field(
        default=None, description="Associated inspection session identifier"
    )
    site_id: Optional[str] = Field(
        default=None, description="Associated heritage site identifier"
    )
    public_id: str = Field(
        ..., description="Cloudinary storage public_id (backend-controlled)"
    )
    asset_id: Optional[str] = Field(
        default=None, description="Cloudinary unique asset identifier"
    )
    resource_type: str = Field(default="image", description="Resource type in storage")
    format: str = Field(..., description="Verified file format extension")
    width: int = Field(..., ge=1, description="Image width in pixels")
    height: int = Field(..., ge=1, description="Image height in pixels")
    bytes: int = Field(..., ge=0, description="Payload size in bytes")
    created_at: str = Field(..., description="ISO 8601 upload timestamp")
    status: str = Field(default="uploaded", description="Lifecycle status")
    structure_type: Optional[str] = Field(
        default=None, description="Heritage typology (e.g. baoli, kund, vav)"
    )
    original_filename: Optional[str] = Field(
        default=None, description="Original uploaded filename"
    )
    preview_url: str = Field(
        ..., description="Optimized responsive preview URL"
    )
    thumbnail_url: Optional[str] = Field(
        default=None, description="Optimized square thumbnail URL"
    )
    secure_url: str = Field(
        ..., description="Cloudinary delivery / secure access URL"
    )

    def to_upload_response(self) -> ImageUploadResponse:
        """Project persistent metadata to public client response."""
        return ImageUploadResponse(
            image_id=self.image_id,
            inspection_id=self.inspection_id,
            site_id=self.site_id,
            status=self.status,
            preview_url=self.preview_url,
            thumbnail_url=self.thumbnail_url,
            original_url=self.secure_url,
            format=self.format,
            width=self.width,
            height=self.height,
            bytes=self.bytes,
            created_at=self.created_at,
        )

    def to_heritage_summary(self) -> HeritageImageSummary:
        """Project to rich gallery item summary."""
        return HeritageImageSummary(
            image_id=self.image_id,
            site_id=self.site_id,
            inspection_id=self.inspection_id,
            public_id=self.public_id,
            asset_id=self.asset_id,
            format=self.format,
            width=self.width,
            height=self.height,
            bytes=self.bytes,
            created_at=self.created_at,
            status=self.status,
            structure_type=self.structure_type,
            original_filename=self.original_filename,
            preview_url=self.preview_url,
            thumbnail_url=self.thumbnail_url or self.preview_url,
            original_url=self.secure_url,
        )


class PaginatedImagesResponse(BaseModel):
    """Paginated collection of registered heritage inspection images."""

    model_config = ConfigDict(extra="ignore")

    total: int = Field(..., ge=0, description="Total matching image count")
    limit: int = Field(..., ge=1, description="Page limit applied")
    offset: int = Field(..., ge=0, description="Offset applied")
    site_id: Optional[str] = Field(default=None, description="Applied site filter")
    inspection_id: Optional[str] = Field(
        default=None, description="Applied inspection filter"
    )
    images: List[HeritageImageSummary] = Field(
        default_factory=list, description="List of heritage image items"
    )


class CloudinaryAssetItem(BaseModel):
    """Representation of an asset directly retrieved from Cloudinary Search or Admin API."""

    model_config = ConfigDict(extra="ignore")

    public_id: str = Field(..., description="Cloudinary asset public ID")
    asset_id: Optional[str] = Field(
        default=None, description="Cloudinary unique asset ID"
    )
    format: str = Field(..., description="Format extension")
    width: int = Field(..., ge=1, description="Pixel width")
    height: int = Field(..., ge=1, description="Pixel height")
    bytes: int = Field(..., ge=0, description="File size in bytes")
    created_at: str = Field(..., description="Creation timestamp")
    secure_url: str = Field(..., description="Cloudinary delivery URL")
    preview_url: str = Field(..., description="Responsive preview URL")
    thumbnail_url: str = Field(..., description="Card thumbnail URL")
    folder: Optional[str] = Field(default=None, description="Storage folder")
    site_id: Optional[str] = Field(default=None, description="Inferred or tagged site")
    inspection_id: Optional[str] = Field(
        default=None, description="Inferred or tagged inspection"
    )
    tags: List[str] = Field(default_factory=list, description="Asset tags")


class CloudinarySearchResponse(BaseModel):
    """Response returned from Cloudinary Search API query."""

    model_config = ConfigDict(extra="ignore")

    total_count: int = Field(..., ge=0, description="Total matched assets in Cloudinary")
    next_cursor: Optional[str] = Field(
        default=None, description="Cursor for fetching next page of assets"
    )
    resources: List[CloudinaryAssetItem] = Field(
        default_factory=list, description="List of matched Cloudinary assets"
    )


class SiteSummary(BaseModel):
    """Aggregated summary of a heritage site and its visual survey assets."""

    model_config = ConfigDict(extra="ignore")

    site_id: str = Field(..., description="Site identifier")
    site_name: str = Field(..., description="Human-readable site designation")
    structure_type: Optional[str] = Field(
        default=None, description="Primary typology (e.g. baoli, kund, vav)"
    )
    total_images: int = Field(..., ge=0, description="Total recorded photographs")
    total_inspections: int = Field(..., ge=0, description="Distinct inspection sessions")
    latest_upload: Optional[str] = Field(
        default=None, description="Timestamp of most recent photo"
    )
    cover_thumbnail_url: Optional[str] = Field(
        default=None, description="Thumbnail URL of representative image"
    )


class SiteListResponse(BaseModel):
    """List of all registered heritage sites."""

    model_config = ConfigDict(extra="ignore")

    total_sites: int = Field(..., ge=0, description="Total registered sites")
    sites: List[SiteSummary] = Field(
        default_factory=list, description="List of site summaries"
    )


class ImageDeleteResponse(BaseModel):
    """Response returned upon image deletion request."""

    model_config = ConfigDict(extra="ignore")

    image_id: str = Field(..., description="Identifier of the deleted image")
    status: str = Field(..., description="Status ('deleted' or 'partial_failure')")
    detail: str = Field(..., description="Human-readable operational summary")
    cloudinary_deleted: bool = Field(
        ..., description="Whether Cloudinary asset was deleted"
    )
    metadata_deleted: bool = Field(
        ..., description="Whether persistent database record was deleted"
    )


class InspectionImagesListResponse(BaseModel):
    """List of all images associated with an inspection session."""

    model_config = ConfigDict(extra="ignore")

    inspection_id: str = Field(..., description="Inspection identifier")
    total: int = Field(..., ge=0, description="Total count of associated images")
    images: List[ImageUploadResponse] = Field(
        default_factory=list, description="Array of image descriptors"
    )
