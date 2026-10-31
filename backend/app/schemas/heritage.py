"""Pydantic schemas for Heritage Structures, Inspections, Defect Passports, and Multilingual Reports.

Maintained for JalDrishti Enterprise Heritage Management System.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StructureTypology(str, Enum):
    BAOLI = "baoli"
    BAWARI = "bawari"
    KUND = "kund"
    VAV = "vav"
    TANK = "tank"
    HERITAGE_MASONRY = "heritage_masonry"
    UNKNOWN = "unknown"


class DefectStatus(str, Enum):
    ACTIVE = "active"
    MONITORING = "monitoring"
    REPAIRED = "repaired"
    CRITICAL = "critical"


class VerificationStatus(str, Enum):
    AI_DETECTED = "ai_detected"
    HUMAN_VERIFIED = "human_verified"
    REJECTED = "rejected"


class DefectSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    SEVERE = "severe"


class SupportedLanguage(str, Enum):
    EN = "en"
    HI = "hi"
    BN = "bn"
    TE = "te"
    MR = "mr"
    TA = "ta"
    UR = "ur"
    GU = "gu"
    KN = "kn"
    ML = "ml"
    OR = "or"
    PA = "pa"
    AS = "as"
    KS = "ks"
    SA = "sa"


class StructureCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(..., min_length=2, max_length=200, description="Name of the heritage water structure")
    typology: StructureTypology = Field(default=StructureTypology.BAOLI)
    location: Optional[str] = Field(default="", description="City or district")
    region: Optional[str] = Field(default="Northern India", description="Geographical or cultural region")
    historical_period: Optional[str] = Field(default="", description="e.g. 14th Century Sultanate, Medieval")
    notes: Optional[str] = Field(default="", description="Conservation notes or initial survey information")


class StructureSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    structure_id: str
    name: str
    typology: str
    location: str
    region: str
    historical_period: str
    baseline_completed: bool
    baseline_inspection_id: Optional[str] = None
    created_at: str
    updated_at: str
    total_defects: int = 0
    active_defects: int = 0
    total_inspections: int = 0


class DefectPassportItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    defect_id: str
    structure_id: str
    defect_category: str
    first_detected_date: str
    original_inspection_id: str
    original_image_id: str
    bounding_box: List[float]  # [xmin, ymin, xmax, ymax]
    confidence: float
    severity: str
    status: str
    verification_status: str
    repair_notes: Optional[str] = None
    created_at: str
    updated_at: str


class DefectObservationItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    observation_id: str
    defect_id: str
    inspection_id: str
    image_id: str
    bounding_box: List[float]
    confidence: float
    observed_status: str
    notes: Optional[str] = None
    created_at: str


class InspectionImageSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    image_id: str
    inspection_id: str
    structure_id: str
    original_filename: str
    preview_url: Optional[str] = None
    quality_status: str
    relevance_status: str
    relevance_confidence: float
    inspection_status: str
    rejection_reason: Optional[str] = None
    defects_count: int = 0
    results: Optional[Dict[str, Any]] = None
    created_at: str


class InspectionSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    inspection_id: str
    structure_id: str
    inspection_type: str  # 'baseline' or 'repeat'
    status: str  # 'in_progress', 'completed', 'failed'
    inspection_date: str
    total_images: int
    valid_images: int
    total_cracks: int
    vegetation_count: int
    summary_data: Optional[Dict[str, Any]] = None
    images: List[InspectionImageSummary] = Field(default_factory=list)
    created_at: str


class ExtractedDefectItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    description: str
    category: str
    severity: Optional[str] = "moderate"
    page_number: int = 1
    confirmed: bool = False


class DocumentExtractionSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    document_id: str
    structure_id: str
    filename: str
    status: str
    extracted_structure_name: Optional[str] = None
    extracted_inspection_date: Optional[str] = None
    extracted_defects: List[ExtractedDefectItem] = Field(default_factory=list)
    extracted_recommendations: List[str] = Field(default_factory=list)
    extracted_photos_count: int = 0
    created_at: str


class UserLanguagePreference(BaseModel):
    model_config = ConfigDict(extra="ignore")
    language: SupportedLanguage = Field(default=SupportedLanguage.EN)

