"""API router definition for JalDrishti backend.

Maintained by Swastik Parmar (Backend / Integration Engineer).
Integrates live Vision, Engineering, Material Compatibility, Restoration Planning,
and Knowledge subsystems.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Union
import uuid

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from backend.app.core.config import settings
from backend.app.core.security import rate_limit, require_admin_access
from backend.app.db.image_repository import (
    MetadataPersistenceError,
    image_repository,
)
from backend.app.schemas.analysis import AnalysisResult
from backend.app.schemas.engineering import EngineeringResult
from backend.app.schemas.health import HealthResponse
from backend.app.schemas.image import (
    CloudinarySearchResponse,
    HeritageImageSummary,
    ImageDeleteResponse,
    ImageMetadata,
    ImageUploadResponse,
    InspectionImagesListResponse,
    PaginatedImagesResponse,
    SiteListResponse,
    SiteSummary,
)
from backend.app.schemas.material import MaterialCompatibilityResult
from backend.app.schemas.requests import (
    AnalysisPipelineRequest,
    EngineeringAssessmentRequest,
    MaterialCompatibilityRequest,
    RestorationPlanRequest,
)
from backend.app.schemas.restoration import RestorationResult
from backend.app.schemas.vision import ImageDimensions, StructureType, VisionResult
from backend.app.services.analysis_service import analysis_service
from backend.app.services.cloudinary_service import (
    CloudinaryConfigError,
    CloudinaryDeleteError,
    CloudinarySearchError,
    CloudinaryUploadError,
    cloudinary_service,
)
from backend.app.services.engineering_service import engineering_service
from backend.app.services.vision_service import vision_service
from backend.app.utils.image_validator import (
    ImageDecodeError,
    ImageEmptyError,
    ImageFormatError,
    ImageSizeLimitError,
    ImageValidationError,
    read_and_validate_image_upload,
)
from engineering import (
    default_repository,
    evaluate_compatibility,
    get_source,
    get_structure,
    list_structures,
    plan_restoration,
)
from backend.app.db.heritage_repository import heritage_repo
from backend.app.services.document_extraction_service import document_extraction_service
from backend.app.services.pdf_report_service import pdf_report_service
from backend.app.schemas.heritage import (
    DefectObservationItem,
    DefectPassportItem,
    DocumentExtractionSummary,
    InspectionSummary,
    StructureCreate,
    StructureSummary,
    SupportedLanguage,
    UserLanguagePreference,
)

logger = logging.getLogger(__name__)

api_router = APIRouter()


@api_router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Verify backend service readiness and runtime configuration.",
    tags=["System"],
)
def get_health() -> HealthResponse:
    """Return service health and version metadata."""
    return HealthResponse(
        status="ok",
        project="jaldrishti",
        version="0.1.0",
    )


# -----------------------------------------------------------------------------
# Vision & Engineering Pipeline Endpoints
# -----------------------------------------------------------------------------


async def _extract_pipeline_request(
    request: Request,
) -> tuple[AnalysisPipelineRequest, Optional[bytes], Optional[List[float]]]:
    """Parse incoming pipeline request supporting both JSON payloads and multipart/form-data."""
    content_type = request.headers.get("content-type", "")
    image_bytes: Optional[bytes] = None
    roi_box: Optional[List[float]] = None

    if "application/json" in content_type:
        try:
            body_json = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON body") from exc
        try:
            req_model = AnalysisPipelineRequest.model_validate(body_json)
        except ValidationError as e:
            raise RequestValidationError(e.errors()) from e

        # If registered image_id is referenced, resolve metadata from repository
        if req_model.image_id:
            record = image_repository.get_by_id(req_model.image_id)
            if record:
                if req_model.source_images == ["survey_image_01.jpg"]:
                    req_model.source_images = [record.preview_url]
                if req_model.image_dimensions is None:
                    req_model.image_dimensions = ImageDimensions(
                        width_pixels=record.width,
                        height_pixels=record.height,
                    )
                # Ensure original-quality image is used for vision model inference
                if image_bytes is None and record.secure_url:
                    image_bytes = cloudinary_service.fetch_original_image_bytes(record.secure_url)
        return req_model, image_bytes, None

    # Handle multipart/form-data or application/x-www-form-urlencoded
    form = await request.form()
    uploaded_file = form.get("images") or form.get("file") or form.get("image")
    source_images: List[str] = ["survey_image_01.jpg"]

    form_image_id = form.get("image_id")
    resolved_dims: Optional[ImageDimensions] = None
    if form_image_id and isinstance(form_image_id, str):
        record = image_repository.get_by_id(form_image_id)
        if record:
            source_images = [record.preview_url]
            resolved_dims = ImageDimensions(
                width_pixels=record.width,
                height_pixels=record.height,
            )
            if image_bytes is None and record.secure_url:
                image_bytes = cloudinary_service.fetch_original_image_bytes(record.secure_url)

    if uploaded_file is not None and hasattr(uploaded_file, "read"):
        image_bytes = await uploaded_file.read()
        fname = getattr(uploaded_file, "filename", None)
        if fname:
            source_images = [fname]
    elif isinstance(uploaded_file, str) and uploaded_file:
        source_images = [uploaded_file]

    roi_str = form.get("roi_box")
    if roi_str:
        try:
            roi_box = json.loads(str(roi_str))
        except Exception:
            roi_box = None

    st_raw = form.get("structure_type", "baoli")
    try:
        st_enum = StructureType(st_raw)
    except ValueError:
        st_enum = StructureType.BAOLI

    req_dict: Dict[str, Any] = {
        "structure_type": st_enum,
        "name": form.get("name") or "Heritage Water Structure",
        "region": form.get("region") or "Northern India",
        "source_images": source_images,
    }

    if form_image_id and isinstance(form_image_id, str):
        req_dict["image_id"] = form_image_id
    if resolved_dims is not None:
        req_dict["image_dimensions"] = resolved_dims

    notes = form.get("notes")
    if notes:
        req_dict["inspection_data"] = {"notes": notes}

    try:
        req_model = AnalysisPipelineRequest.model_validate(req_dict)
    except ValidationError as e:
        raise RequestValidationError(e.errors()) from e

    return req_model, image_bytes, roi_box


@api_router.post(
    "/vision/analyze",
    response_model=VisionResult,
    status_code=status.HTTP_200_OK,
    summary="Vision Defect Analysis",
    description="Extract and normalize image-space defect segments from JSON or multipart image uploads.",
    tags=["Vision"],
    dependencies=[Depends(rate_limit("ai_analysis"))],
)
async def analyze_vision(
    request: Request,
) -> VisionResult:
    """Run computer vision defect extraction and spatial analysis."""
    req_model, image_bytes, roi_box = await _extract_pipeline_request(request)
    return vision_service.analyze_image(
        image_bytes=image_bytes,
        image_name=req_model.source_images[0] if req_model.source_images else None,
        source_images=req_model.source_images,
        structure_type=req_model.structure_type,
        image_dimensions=req_model.image_dimensions,
        scale_reference=req_model.scale_reference,
        detections=req_model.detections,
        roi_box=roi_box,
    )


@api_router.post(
    "/engineering",
    response_model=EngineeringResult,
    status_code=status.HTTP_200_OK,
    summary="Engineering Assessment",
    description="Calculate deterministic condition, functionality, and restoration priority scores.",
    tags=["Engineering"],
)
def assess_engineering(
    payload: Union[EngineeringAssessmentRequest, VisionResult] = Body(...),
) -> EngineeringResult:
    """Run deterministic engineering calculations on vision inspection outputs."""
    if isinstance(payload, EngineeringAssessmentRequest):
        if payload.vision is not None:
            vision_input = payload.vision
        else:
            st_type = payload.structure_type or StructureType.BAOLI
            vision_input = vision_service.analyze_image(
                structure_type=st_type,
                image_dimensions=payload.image_dimensions,
                detections=payload.detections,
            )
        return engineering_service.assess_vision_result(
            vision_result=vision_input,
            structure_name=payload.structure_name,
            region=payload.region,
            inspection_data=payload.inspection_data,
            inferred_material=payload.inferred_material,
            material_confidence=payload.material_confidence,
            candidate_materials=payload.candidate_materials,
            recent_repair_type=payload.recent_repair_type,
        )
    return engineering_service.assess_vision_result(vision_result=payload)


@api_router.post(
    "/material-compatibility",
    response_model=MaterialCompatibilityResult,
    status_code=status.HTTP_200_OK,
    summary="Material Compatibility Evaluation",
    description="Evaluate candidate intervention materials against historic substrates using deterministic rules.",
    tags=["Materials"],
)
def evaluate_material_compatibility(
    request: Optional[MaterialCompatibilityRequest] = Body(default=None),
) -> MaterialCompatibilityResult:
    """Evaluate candidate mortars and consolidants against historical substrates."""
    req = request or MaterialCompatibilityRequest()
    orig_mat = req.original_material
    if not orig_mat and req.structure_type:
        from engineering.service import TYPOLOGY_MATERIAL_DEFAULTS
        orig_mat = TYPOLOGY_MATERIAL_DEFAULTS.get(
            req.structure_type.value, "hydraulic_lime_mortar"
        )
    orig_mat = orig_mat or "hydraulic_lime_mortar"

    try:
        res_dict = evaluate_compatibility(
            original_material=orig_mat,
            candidate_materials=req.candidate_materials,
            original_material_confidence=req.original_material_confidence,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return MaterialCompatibilityResult.model_validate(res_dict)


@api_router.post(
    "/restore",
    response_model=RestorationResult,
    status_code=status.HTTP_200_OK,
    summary="Conservation Restoration Roadmap",
    description="Generate phased conservation interventions and traditional IKS restoration guidance.",
    tags=["Restoration"],
)
def generate_restoration_roadmap(
    request: Optional[RestorationPlanRequest] = Body(default=None),
) -> RestorationResult:
    """Plan phased conservation roadmap and apply IKS principles."""
    req = request or RestorationPlanRequest()
    st_val = req.structure_type.value if req.structure_type else "baoli"

    try:
        res_dict = plan_restoration(
            structure_type=st_val,
            visual_condition_score=req.visual_condition_score or 75.0,
            water_functionality_score=req.water_functionality_score or 60.0,
            crack_burden=req.crack_burden or 0.0,
            vegetation_burden=req.vegetation_burden or 0.0,
            spalling_burden=req.spalling_burden or 0.0,
            dislodgement_burden=req.dislodgement_burden or 0.0,
            siltation_level=req.siltation_level or "unknown",
            inlet_condition=req.inlet_condition or "unknown",
            inferred_material=req.inferred_material or "hydraulic_lime_mortar",
            root_causes=req.root_causes,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return RestorationResult.model_validate(res_dict)


@api_router.post(
    "/analyze",
    response_model=AnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Unified Analysis Pipeline",
    description="Orchestrates full end-to-end multi-disciplinary conservation pipeline from JSON or multipart form.",
    tags=["Pipeline"],
    dependencies=[Depends(rate_limit("ai_analysis"))],
)
async def analyze_structure(
    request: Request,
) -> AnalysisResult:
    """Execute end-to-end inspection pipeline (Vision -> Engineering -> Unified Contract)."""
    req_model, image_bytes, roi_box = await _extract_pipeline_request(request)
    return analysis_service.orchestrate_analysis(
        structure_type=req_model.structure_type,
        name=req_model.name,
        region=req_model.region,
        source_images=req_model.source_images,
        image_bytes=image_bytes,
        image_dimensions=req_model.image_dimensions,
        scale_reference=req_model.scale_reference,
        detections=req_model.detections,
        inspection_data=req_model.inspection_data,
        inferred_material=req_model.inferred_material,
        material_confidence=req_model.material_confidence,
        candidate_materials=req_model.candidate_materials,
        recent_repair_type=req_model.recent_repair_type,
        roi_box=roi_box,
    )


# -----------------------------------------------------------------------------
# Knowledge Base Lookup Endpoints
# -----------------------------------------------------------------------------


@api_router.get(
    "/knowledge/structures",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Known Water Structures",
    description="Retrieve all traditional water structure typology definitions and architectural profiles.",
    tags=["Knowledge"],
)
def get_known_structures() -> List[Dict[str, Any]]:
    """Return all catalogued water structure typologies."""
    return list_structures()


@api_router.get(
    "/knowledge/structures/{structure_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Structure Knowledge Details",
    description="Retrieve deep architectural, hydrological, and conservation metadata for a specific typology.",
    tags=["Knowledge"],
)
def get_structure_details(structure_id: str) -> Dict[str, Any]:
    """Return specific structure typology knowledge record."""
    try:
        return get_structure(structure_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Structure typology '{structure_id}' not found.",
        ) from exc


@api_router.get(
    "/knowledge/sources",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Literature and Research Sources",
    description="Retrieve references and academic sources underpinning conservation logic.",
    tags=["Knowledge"],
)
def get_literature_sources() -> List[Dict[str, Any]]:
    """Return bibliographic and heritage guidelines source catalog."""
    return default_repository.list_sources()


# -----------------------------------------------------------------------------
# Image Ingestion & Storage Endpoints (Cloudinary & Local Durability)
# -----------------------------------------------------------------------------


@api_router.post(
    "/images/upload",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Inspection Image",
    description=(
        "Uploads an inspection photograph through a backend-controlled workflow. "
        "Enforces streaming bounded reads, validates format and content decodability via Pillow, "
        "uploads to Cloudinary without exposing credentials, and durably records metadata."
    ),
    tags=["Images"],
    dependencies=[Depends(rate_limit("image_upload"))],
)
async def upload_inspection_image(
    request: Request,
    file: Optional[UploadFile] = File(default=None),
    images: Optional[UploadFile] = File(default=None),
    image: Optional[UploadFile] = File(default=None),
    inspection_id: Optional[str] = Form(default=None),
    site_id: Optional[str] = Form(default=None),
    structure_type: Optional[str] = Form(default=None),
    structure_name: Optional[str] = Form(default=None),
    notes: Optional[str] = Form(default=None),
) -> ImageUploadResponse:
    """Accept and validate image upload, store to Cloudinary, and persist metadata."""
    # Resolve uploaded file from available multipart fields
    target_file = file or images or image

    if target_file is None:
        # Check form dynamically in case of non-standard field naming
        try:
            form = await request.form()
            for key, val in form.items():
                if hasattr(val, "read") and hasattr(val, "filename"):
                    target_file = val
                    break
        except Exception:
            pass

    if target_file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file provided in multipart request. Use 'file' or 'images' form field.",
        )

    # 1. Bounded streaming read and strict image validation
    try:
        image_bytes, format_str, width, height = await read_and_validate_image_upload(
            target_file,
            max_size_bytes=settings.max_upload_size_bytes,
            allowed_formats=settings.allowed_image_formats,
        )
    except ImageEmptyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ImageSizeLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(e)
        )
    except ImageFormatError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ImageDecodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ImageValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 2. Check Cloudinary configuration
    if not cloudinary_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Image storage service is not configured. "
                "Required backend environment variables: "
                "CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET."
            ),
        )

    # 3. Generate stable identifiers and hierarchical public ID
    gen_image_id = f"img_{uuid.uuid4()}"
    assigned_inspection_id = inspection_id or f"insp_{uuid.uuid4()}"
    clean_site_id = re.sub(r"[^a-zA-Z0-9_\-]", "", site_id).strip() if site_id else None
    clean_insp_id = re.sub(r"[^a-zA-Z0-9_\-]", "", assigned_inspection_id).strip()

    # Predictable site-wise asset organization: jaldrishti/inspections/<site_id>/<inspection_id>/<image_id>
    if clean_site_id:
        public_id = f"{settings.cloudinary_folder}/{clean_site_id}/{clean_insp_id}/{gen_image_id}"
    else:
        public_id = f"{settings.cloudinary_folder}/{gen_image_id}"

    # 4. Upload to Cloudinary
    tags = ["jaldrishti", "heritage_water_structure"]
    if structure_type:
        tags.append(structure_type.lower())
    if clean_site_id:
        tags.append(f"site:{clean_site_id}")
    if clean_insp_id:
        tags.append(f"insp:{clean_insp_id}")

    context = {
        "image_id": gen_image_id,
        "inspection_id": assigned_inspection_id,
    }
    if clean_site_id:
        context["site_id"] = clean_site_id
    if structure_name:
        context["structure_name"] = structure_name

    try:
        upload_res = cloudinary_service.upload_image(
            image_bytes=image_bytes,
            public_id=public_id,
            folder=settings.cloudinary_folder,
            tags=tags,
            context=context,
        )
    except CloudinaryConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    except CloudinaryUploadError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloudinary image upload failed. Please verify storage availability and try again.",
        )
    except Exception as e:
        logger.error("Unexpected upload failure: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error processing image upload.",
        )

    # 5. Execute Image Inspection Gate
    gate_res = vision_service.inspect_image(image_bytes)

    # 6. Assemble persistent metadata
    now_iso = datetime.now(timezone.utc).isoformat()
    thumb_url = upload_res.get("thumbnail_url") or cloudinary_service.build_thumbnail_url(
        upload_res.get("public_id", public_id), format_str
    )
    metadata = ImageMetadata(
        image_id=gen_image_id,
        inspection_id=assigned_inspection_id,
        site_id=clean_site_id,
        public_id=upload_res.get("public_id", public_id),
        asset_id=upload_res.get("asset_id"),
        resource_type="image",
        format=format_str,
        width=width,
        height=height,
        bytes=len(image_bytes),
        created_at=now_iso,
        status="uploaded",
        structure_type=structure_type,
        original_filename=getattr(target_file, "filename", None),
        preview_url=upload_res.get("preview_url")
        or cloudinary_service.build_preview_url(
            upload_res.get("public_id", public_id), format_str
        ),
        thumbnail_url=thumb_url,
        secure_url=upload_res.get("secure_url")
        or cloudinary_service.build_original_url(
            upload_res.get("public_id", public_id), format_str
        ),
        inspection_status=gate_res.get("inspection_status", "uploaded"),
        relevance_confidence=gate_res.get("relevance_confidence"),
        rejection_reason=gate_res.get("rejection_reason"),
        needs_manual_review=gate_res.get("needs_manual_review", False),
        model_version=gate_res.get("model_version"),
    )

    # 7. Durably persist metadata in SQLite
    try:
        image_repository.save(metadata)
    except MetadataPersistenceError as e:
        # Partial failure handling: image was uploaded to Cloudinary, but DB write failed.
        logger.error(
            "Database persistence failed for image %s. Attempting Cloudinary rollback: %s",
            gen_image_id,
            e,
        )
        try:
            cloudinary_service.delete_image(metadata.public_id)
        except Exception as cleanup_err:
            logger.warning(
                "Rollback deletion in Cloudinary failed for %s: %s",
                metadata.public_id,
                cleanup_err,
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist image metadata. Upload rolled back.",
        )

    return metadata.to_upload_response()


@api_router.get(
    "/images",
    response_model=PaginatedImagesResponse,
    status_code=status.HTTP_200_OK,
    summary="List Stored Heritage Images",
    description="Retrieve paginated inspection photographs with site, inspection, and typology filtering.",
    tags=["Images"],
)
def list_images(
    site_id: Optional[str] = Query(default=None, description="Heritage site identifier"),
    inspection_id: Optional[str] = Query(default=None, description="Inspection session identifier"),
    structure_type: Optional[str] = Query(default=None, description="Architectural typology filter"),
    limit: int = Query(default=20, ge=1, le=100, description="Page size limit"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> PaginatedImagesResponse:
    """Retrieve filtered, paginated heritage inspection image records."""
    records, total = image_repository.list_images(
        site_id=site_id,
        inspection_id=inspection_id,
        structure_type=structure_type,
        limit=limit,
        offset=offset,
    )
    return PaginatedImagesResponse(
        total=total,
        limit=limit,
        offset=offset,
        site_id=site_id,
        inspection_id=inspection_id,
        images=[r.to_heritage_summary() for r in records],
    )


@api_router.get(
    "/images/cloud-search",
    response_model=CloudinarySearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search Cloudinary Assets",
    description="Perform structured live asset search directly against Cloudinary using official Search or Admin API.",
    tags=["Images"],
    dependencies=[Depends(rate_limit("cloud_search"))],
)
def search_cloudinary_assets(
    query: Optional[str] = Query(default=None, description="Cloudinary search expression or keywords"),
    site_id: Optional[str] = Query(default=None, description="Heritage site identifier"),
    inspection_id: Optional[str] = Query(default=None, description="Inspection identifier"),
    folder: Optional[str] = Query(default=None, description="Directory folder path"),
    tag: Optional[str] = Query(default=None, description="Search tag"),
    max_results: int = Query(default=20, ge=1, le=100, description="Max assets to return"),
    next_cursor: Optional[str] = Query(default=None, description="Pagination cursor"),
) -> CloudinarySearchResponse:
    """Execute authenticated Cloudinary asset search with cursor pagination."""
    if not cloudinary_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloudinary image storage service is not configured.",
        )

    tags_list = [tag] if tag else None
    try:
        search_res = cloudinary_service.search_assets(
            expression=query,
            folder=folder,
            tags=tags_list,
            site_id=site_id,
            inspection_id=inspection_id,
            max_results=max_results,
            next_cursor=next_cursor,
        )
        return CloudinarySearchResponse.model_validate(search_res)
    except CloudinaryConfigError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except CloudinarySearchError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cloudinary asset search failed: {e}",
        )
    except Exception as e:
        logger.error("Unexpected failure in Cloudinary asset search: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error processing asset search.",
        )


@api_router.get(
    "/sites",
    response_model=SiteListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Heritage Sites",
    description="Retrieve all heritage sites with recorded visual survey assets and inspection metrics.",
    tags=["Sites"],
)
def list_heritage_sites() -> SiteListResponse:
    """Retrieve aggregated heritage sites and survey counts."""
    sites_data = image_repository.list_sites()
    summaries = [SiteSummary.model_validate(s) for s in sites_data]
    return SiteListResponse(total_sites=len(summaries), sites=summaries)


@api_router.get(
    "/images/{image_id}",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Image Metadata",
    description="Retrieve stable metadata and delivery URLs for an uploaded inspection image.",
    tags=["Images"],
)
def get_image(image_id: str) -> ImageUploadResponse:
    """Retrieve image metadata by its application-level image identifier."""
    record = image_repository.get_by_id(image_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with id '{image_id}' not found.",
        )
    return record.to_upload_response()


@api_router.delete(
    "/images/{image_id}",
    response_model=ImageDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Image Asset",
    description=(
        "Remove image from Cloudinary storage and delete associated durable metadata record. "
        "Handles partial failures explicitly. Requires administrative credentials when configured."
    ),
    tags=["Images"],
    dependencies=[Depends(rate_limit("image_delete")), Depends(require_admin_access)],
)
def delete_image(image_id: str) -> ImageDeleteResponse:
    """Delete image asset from both Cloudinary and local metadata repository."""
    record = image_repository.get_by_id(image_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with id '{image_id}' not found.",
        )

    cloudinary_deleted = False
    metadata_deleted = False

    # Attempt Cloudinary deletion
    try:
        cloudinary_deleted = cloudinary_service.delete_image(record.public_id)
    except CloudinaryDeleteError as e:
        logger.error("Cloudinary deletion failed for %s: %s", record.public_id, e)
        cloudinary_deleted = False
    except CloudinaryConfigError:
        logger.warning(
            "Cloudinary credentials missing during deletion of %s.", record.public_id
        )
        cloudinary_deleted = False

    # Attempt database record deletion
    try:
        metadata_deleted = image_repository.delete(image_id)
    except MetadataPersistenceError as e:
        logger.error("Database deletion failed for %s: %s", image_id, e)
        metadata_deleted = False

    # Evaluate outcome and handle partial failures explicitly
    if not cloudinary_deleted and not metadata_deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete image from storage provider and metadata repository.",
        )
    if not cloudinary_deleted and metadata_deleted:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Partial deletion failure: database record removed, but Cloudinary asset could not be deleted.",
        )
    if cloudinary_deleted and not metadata_deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Partial deletion failure: Cloudinary asset removed, but database record could not be deleted.",
        )

    return ImageDeleteResponse(
        image_id=image_id,
        status="deleted",
        detail="Image asset deleted from Cloudinary and metadata repository.",
        cloudinary_deleted=True,
        metadata_deleted=True,
    )


@api_router.get(
    "/inspections/{inspection_id}/images",
    response_model=InspectionImagesListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Inspection Images",
    description="Retrieve all verified images registered to an inspection session.",
    tags=["Images"],
)
def list_inspection_images(inspection_id: str) -> InspectionImagesListResponse:
    """Retrieve all images associated with an inspection session."""
    records = image_repository.list_by_inspection_id(inspection_id)
    return InspectionImagesListResponse(
        inspection_id=inspection_id,
        total=len(records),
        images=[r.to_upload_response() for r in records],
    )


# ==============================================================================
# ENTERPRISE FEATURES: 15-LANGUAGE PREFERENCES, STRUCTURES, BASELINE & REPEAT
# ==============================================================================


@api_router.get(
    "/preferences/language",
    summary="Get User Language Preference",
    tags=["Preferences"],
)
def get_user_language() -> Dict[str, str]:
    """Return user's persisted language code out of the 15 supported languages."""
    return {"language": heritage_repo.get_user_language()}


@api_router.put(
    "/preferences/language",
    summary="Set User Language Preference",
    tags=["Preferences"],
)
def set_user_language(pref: UserLanguagePreference) -> Dict[str, str]:
    """Persist user language preference across sessions."""
    heritage_repo.set_user_language(pref.language.value)
    return {"language": pref.language.value, "status": "updated"}


@api_router.post(
    "/structures",
    summary="Register Heritage Structure",
    tags=["Heritage Structures"],
)
def create_structure(payload: StructureCreate) -> Dict[str, Any]:
    """Create a new heritage structure profile for baseline tracking."""
    structure = heritage_repo.create_structure(payload.model_dump())
    return structure


@api_router.get(
    "/structures",
    summary="List Heritage Structures",
    tags=["Heritage Structures"],
)
def list_heritage_structures() -> List[Dict[str, Any]]:
    """List all registered heritage structures with defect & inspection counts."""
    return heritage_repo.list_structures()


@api_router.get(
    "/structures/{structure_id}",
    summary="Get Heritage Structure Details",
    tags=["Heritage Structures"],
)
def get_heritage_structure(structure_id: str) -> Dict[str, Any]:
    """Retrieve structure profile, inspection history, and persistent Defect Passports."""
    structure = heritage_repo.get_structure(structure_id)
    if not structure:
        raise HTTPException(status_code=404, detail=f"Structure '{structure_id}' not found.")
    inspections = heritage_repo.list_structure_inspections(structure_id)
    passports = heritage_repo.list_defect_passports(structure_id)
    return {
        "structure": structure,
        "inspections": inspections,
        "passports": passports,
    }


@api_router.post(
    "/structures/{structure_id}/inspections/baseline",
    summary="Execute Baseline Heritage Inspection (Min 3 Photos Required)",
    tags=["Inspections"],
    dependencies=[Depends(rate_limit("baseline_inspection"))],
)
async def execute_baseline_inspection(
    structure_id: str,
    files: List[UploadFile] = File(...),
) -> Dict[str, Any]:
    """Execute mandatory 3-photo baseline inspection with independent AI processing.

    Enforces minimum 3 photographs (up to max 10 per batch). Validates image quality
    and heritage relevance gates on every photo independently. Creates persistent
    Defect Passports for detected cracks and vegetation. Rejects baseline finalization
    if <3 valid photos or if duplicates are submitted.
    """
    structure = heritage_repo.get_structure(structure_id)
    if not structure:
        raise HTTPException(status_code=404, detail=f"Structure '{structure_id}' not found.")

    if len(files) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Baseline inspection requires a mandatory minimum of 3 photographs. Received {len(files)}.",
        )
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum 10 photographs can be processed in a single inspection batch. Received {len(files)}.",
        )

    inspection_id = heritage_repo.create_inspection(structure_id, inspection_type="baseline")

    processed_images: List[Dict[str, Any]] = []
    created_defects: List[Dict[str, Any]] = []
    seen_hashes: set[str] = set()
    total_cracks = 0
    total_veg = 0
    valid_count = 0

    for idx, upload in enumerate(files, start=1):
        image_id = f"img_{uuid.uuid4().hex[:10]}"

        # 0. Defensive bounded streaming read & image format/decodability check
        try:
            content, _, _, _ = await read_and_validate_image_upload(upload)
        except ImageValidationError as val_err:
            img_rec = {
                "image_id": image_id,
                "inspection_id": inspection_id,
                "structure_id": structure_id,
                "original_filename": upload.filename or f"image_{idx}.jpg",
                "quality_status": "corrupt",
                "relevance_status": "rejected",
                "relevance_confidence": 0.0,
                "inspection_status": "rejected",
                "rejection_reason": f"File validation failed: {val_err}",
                "results_json": {"inspection_gate": {"inspection_status": "rejected", "status_message": str(val_err)}},
                "image_order": idx,
            }
            heritage_repo.add_inspection_image(img_rec)
            processed_images.append(img_rec)
            continue

        # Check for duplicate image uploads within this inspection
        content_hash = hashlib.sha256(content).hexdigest()
        if content_hash in seen_hashes:
            img_rec = {
                "image_id": image_id,
                "inspection_id": inspection_id,
                "structure_id": structure_id,
                "original_filename": upload.filename or f"image_{idx}.jpg",
                "quality_status": "duplicate",
                "relevance_status": "rejected",
                "relevance_confidence": 0.0,
                "inspection_status": "rejected",
                "rejection_reason": "Duplicate photograph detected. Baseline requires independent views.",
                "results_json": {"inspection_gate": {"inspection_status": "rejected", "status_message": "Duplicate photograph detected."}},
                "image_order": idx,
            }
            heritage_repo.add_inspection_image(img_rec)
            processed_images.append(img_rec)
            continue
        seen_hashes.add(content_hash)

        # 1. Independent Inspection Gate (Quality & Heritage Relevance)
        gate_res = vision_service.inspect_image(content)

        if gate_res.get("inspection_status") in ("rejected", "uncertain"):
            # Image rejected or held for manual review by quality or relevance gate
            status_val = gate_res.get("inspection_status", "rejected")
            img_rec = {
                "image_id": image_id,
                "inspection_id": inspection_id,
                "structure_id": structure_id,
                "original_filename": upload.filename or f"image_{idx}.jpg",
                "quality_status": gate_res.get("quality_status", "unknown"),
                "relevance_status": gate_res.get("decision", "unknown").lower(),
                "relevance_confidence": gate_res.get("relevance_confidence", 0.0),
                "inspection_status": status_val,
                "rejection_reason": gate_res.get("rejection_reason") or gate_res.get("status_message") or (
                    "Image requires manual expert review" if status_val == "uncertain" else "Failed heritage inspection gate"
                ),
                "results_json": {"inspection_gate": gate_res},
                "image_order": idx,
            }
            heritage_repo.add_inspection_image(img_rec)
            processed_images.append(img_rec)
            continue

        # 2. Independent Crack and Vegetation Detection
        analysis_res = vision_service.analyze_image(
            content,
            structure_type=structure.get("typology", "baoli"),
        )
        valid_count += 1

        # 3. Create Persistent Defect Passports
        detections = analysis_res.detections
        img_cracks = 0
        img_veg = 0
        for det in detections:
            cat = "crack" if "crack" in det.class_name.lower() else "vegetation"
            if cat == "crack":
                img_cracks += 1
                total_cracks += 1
            else:
                img_veg += 1
                total_veg += 1

            passport = heritage_repo.create_defect_passport({
                "structure_id": structure_id,
                "defect_category": cat,
                "original_inspection_id": inspection_id,
                "original_image_id": image_id,
                "bounding_box": det.bounding_box,
                "confidence": det.confidence,
                "severity": det.relative_severity or "moderate",
                "status": "active",
                "verification_status": "ai_detected",
                "repair_notes": f"Detected in baseline photo {upload.filename}",
            })
            created_defects.append(passport)

        img_rec = {
            "image_id": image_id,
            "inspection_id": inspection_id,
            "structure_id": structure_id,
            "original_filename": upload.filename or f"image_{idx}.jpg",
            "quality_status": "good",
            "relevance_status": "relevant",
            "relevance_confidence": gate_res.get("relevance_confidence", 1.0),
            "inspection_status": "accepted",
            "rejection_reason": None,
            "results_json": analysis_res.model_dump(),
            "image_order": idx,
        }
        heritage_repo.add_inspection_image(img_rec)
        processed_images.append(img_rec)

    # 4. Mandatory 3 Valid Heritage Photos Rule Check
    if valid_count < 3:
        summary_data = {
            "status": "incomplete_insufficient_valid_images",
            "total_images": len(files),
            "valid_images": valid_count,
            "rejected_images": len(files) - valid_count,
            "total_cracks": total_cracks,
            "vegetation_count": total_veg,
            "message": f"Baseline inspection could not be finalized: only {valid_count} of {len(files)} uploaded photos passed quality and heritage relevance checks. At least 3 valid photos are required.",
        }
        return {
            "inspection_id": inspection_id,
            "structure_id": structure_id,
            "status": "incomplete",
            "baseline_completed": False,
            "summary": summary_data,
            "images": processed_images,
            "defects_registered": len(created_defects),
        }

    # Finalize baseline inspection
    summary_data = {
        "status": "completed",
        "total_images": len(files),
        "valid_images": valid_count,
        "rejected_images": len(files) - valid_count,
        "total_cracks": total_cracks,
        "vegetation_count": total_veg,
        "message": f"Baseline inspection completed successfully with {valid_count} verified heritage photos.",
    }
    heritage_repo.finalize_inspection(inspection_id, summary_data)

    return {
        "inspection_id": inspection_id,
        "structure_id": structure_id,
        "status": "completed",
        "baseline_completed": True,
        "summary": summary_data,
        "images": processed_images,
        "defects_registered": len(created_defects),
        "passports": created_defects,
    }


@api_router.post(
    "/structures/{structure_id}/inspections/repeat",
    summary="Execute Repeat Inspection with Defect Evolution Tracking",
    tags=["Inspections"],
    dependencies=[Depends(rate_limit("baseline_inspection"))],
)
async def execute_repeat_inspection(
    structure_id: str,
    files: List[UploadFile] = File(...),
) -> Dict[str, Any]:
    """Execute repeat inspection matching against existing Defect Passports."""
    structure = heritage_repo.get_structure(structure_id)
    if not structure:
        raise HTTPException(status_code=404, detail=f"Structure '{structure_id}' not found.")

    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum 10 photographs can be processed in a single inspection batch. Received {len(files)}.",
        )

    existing_passports = heritage_repo.list_defect_passports(structure_id)
    inspection_id = heritage_repo.create_inspection(structure_id, inspection_type="repeat")

    processed_images: List[Dict[str, Any]] = []
    matched_observations: List[Dict[str, Any]] = []
    new_defects: List[Dict[str, Any]] = []
    seen_hashes: set[str] = set()
    total_cracks = 0
    total_veg = 0
    valid_count = 0

    for idx, upload in enumerate(files, start=1):
        image_id = f"img_{uuid.uuid4().hex[:10]}"

        try:
            content, _, _, _ = await read_and_validate_image_upload(upload)
        except ImageValidationError as val_err:
            img_rec = {
                "image_id": image_id,
                "inspection_id": inspection_id,
                "structure_id": structure_id,
                "original_filename": upload.filename or f"image_{idx}.jpg",
                "quality_status": "corrupt",
                "relevance_status": "rejected",
                "relevance_confidence": 0.0,
                "inspection_status": "rejected",
                "rejection_reason": f"File validation failed: {val_err}",
                "results_json": {"inspection_gate": {"inspection_status": "rejected", "status_message": str(val_err)}},
                "image_order": idx,
            }
            heritage_repo.add_inspection_image(img_rec)
            processed_images.append(img_rec)
            continue

        content_hash = hashlib.sha256(content).hexdigest()
        if content_hash in seen_hashes:
            img_rec = {
                "image_id": image_id,
                "inspection_id": inspection_id,
                "structure_id": structure_id,
                "original_filename": upload.filename or f"image_{idx}.jpg",
                "quality_status": "duplicate",
                "relevance_status": "rejected",
                "relevance_confidence": 0.0,
                "inspection_status": "rejected",
                "rejection_reason": "Duplicate photograph detected.",
                "results_json": {"inspection_gate": {"inspection_status": "rejected", "status_message": "Duplicate photograph detected."}},
                "image_order": idx,
            }
            heritage_repo.add_inspection_image(img_rec)
            processed_images.append(img_rec)
            continue
        seen_hashes.add(content_hash)

        gate_res = vision_service.inspect_image(content)
        if gate_res.get("inspection_status") in ("rejected", "uncertain"):
            status_val = gate_res.get("inspection_status", "rejected")
            img_rec = {
                "image_id": image_id,
                "inspection_id": inspection_id,
                "structure_id": structure_id,
                "original_filename": upload.filename or f"image_{idx}.jpg",
                "quality_status": gate_res.get("quality_status", "unknown"),
                "relevance_status": gate_res.get("decision", "unknown").lower(),
                "relevance_confidence": gate_res.get("relevance_confidence", 0.0),
                "inspection_status": status_val,
                "rejection_reason": gate_res.get("rejection_reason") or gate_res.get("status_message") or (
                    "Image requires manual expert review" if status_val == "uncertain" else "Failed heritage inspection gate"
                ),
                "results_json": {"inspection_gate": gate_res},
                "image_order": idx,
            }
            heritage_repo.add_inspection_image(img_rec)
            processed_images.append(img_rec)
            continue

        analysis_res = vision_service.analyze_image(
            content,
            structure_type=structure.get("typology", "baoli"),
        )
        valid_count += 1

        for det in analysis_res.detections:
            cat = "crack" if "crack" in det.class_name.lower() else "vegetation"
            if cat == "crack":
                total_cracks += 1
            else:
                total_veg += 1

            # Match against existing passports
            matched_passport = None
            for p in existing_passports:
                if p["defect_category"] == cat:
                    pb = p["bounding_box"]
                    db = det.bounding_box
                    # Check box center distance proximity
                    if len(pb) == 4 and len(db) == 4:
                        pcx, pcy = (pb[0] + pb[2]) / 2, (pb[1] + pb[3]) / 2
                        dcx, dcy = (db[0] + db[2]) / 2, (db[1] + db[3]) / 2
                        dist = ((pcx - dcx) ** 2 + (pcy - dcy) ** 2) ** 0.5
                        if dist < 120.0:
                            matched_passport = p
                            break

            if matched_passport:
                obs_id = heritage_repo.record_defect_observation({
                    "defect_id": matched_passport["defect_id"],
                    "inspection_id": inspection_id,
                    "image_id": image_id,
                    "bounding_box": det.bounding_box,
                    "confidence": det.confidence,
                    "observed_status": "stable",
                    "notes": f"Confirmed active in repeat survey photo {upload.filename}",
                })
                matched_observations.append({
                    "observation_id": obs_id,
                    "defect_id": matched_passport["defect_id"],
                    "evolution": "stable",
                })
            else:
                new_p = heritage_repo.create_defect_passport({
                    "structure_id": structure_id,
                    "defect_category": cat,
                    "original_inspection_id": inspection_id,
                    "original_image_id": image_id,
                    "bounding_box": det.bounding_box,
                    "confidence": det.confidence,
                    "severity": det.relative_severity or "moderate",
                    "status": "active",
                    "verification_status": "ai_detected",
                    "repair_notes": f"Newly appeared in repeat survey photo {upload.filename}",
                })
                new_defects.append(new_p)

        img_rec = {
            "image_id": image_id,
            "inspection_id": inspection_id,
            "structure_id": structure_id,
            "original_filename": upload.filename or f"image_{idx}.jpg",
            "quality_status": "good",
            "relevance_status": "relevant",
            "relevance_confidence": gate_res.get("relevance_confidence", 1.0),
            "inspection_status": "accepted",
            "rejection_reason": None,
            "results_json": analysis_res.model_dump(),
            "image_order": idx,
        }
        heritage_repo.add_inspection_image(img_rec)
        processed_images.append(img_rec)

    summary_data = {
        "status": "completed",
        "total_images": len(files),
        "valid_images": valid_count,
        "rejected_images": len(files) - valid_count,
        "total_cracks": total_cracks,
        "vegetation_count": total_veg,
        "matched_defects": len(matched_observations),
        "new_defects": len(new_defects),
    }
    heritage_repo.finalize_inspection(inspection_id, summary_data)

    return {
        "inspection_id": inspection_id,
        "structure_id": structure_id,
        "status": "completed",
        "summary": summary_data,
        "matched_observations": matched_observations,
        "new_defects": new_defects,
        "images": processed_images,
    }


@api_router.get(
    "/inspections/{inspection_id}",
    summary="Get Detailed Inspection Record",
    tags=["Inspections"],
)
def get_inspection_record(inspection_id: str) -> Dict[str, Any]:
    """Retrieve full details of an inspection session with all images and summary."""
    if inspection_id == "latest":
        with heritage_repo._get_connection() as conn:
            row = conn.execute("SELECT inspection_id FROM inspections ORDER BY created_at DESC LIMIT 1").fetchone()
            if row:
                inspection_id = row["inspection_id"]

    insp = heritage_repo.get_inspection(inspection_id)
    if not insp:
        raise HTTPException(status_code=404, detail=f"Inspection '{inspection_id}' not found.")
    return insp


@api_router.get(
    "/inspections/{inspection_id}/pdf",
    summary="Export Inspection Report as Multilingual PDF",
    tags=["Reports"],
)
def export_inspection_pdf(
    inspection_id: str,
    lang: Optional[str] = Query(default=None, description="One of 15 supported languages (en, hi, bn, te, mr, ta, ur, gu, kn, ml, or, pa, as, ks, sa)"),
) -> Response:
    """Generate and return official conservation PDF dossier in the selected language."""
    if inspection_id == "latest":
        with heritage_repo._get_connection() as conn:
            row = conn.execute("SELECT inspection_id FROM inspections ORDER BY created_at DESC LIMIT 1").fetchone()
            if row:
                inspection_id = row["inspection_id"]

    insp = heritage_repo.get_inspection(inspection_id)
    if not insp:
        raise HTTPException(status_code=404, detail=f"Inspection '{inspection_id}' not found.")
    structure = heritage_repo.get_structure(insp["structure_id"]) or {}
    passports = heritage_repo.list_defect_passports(insp["structure_id"])

    target_lang = lang or heritage_repo.get_user_language() or "en"
    pdf_bytes = pdf_report_service.generate_inspection_pdf(structure, insp, passports, lang=target_lang)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=jaldrishti_{insp['structure_id']}_{inspection_id}_{target_lang}.pdf"
        },
    )


@api_router.post(
    "/structures/{structure_id}/documents/upload",
    summary="Upload and Extract Historical Survey PDF",
    tags=["Historical Documents"],
    dependencies=[Depends(rate_limit("document_upload"))],
)
async def upload_historical_survey(
    structure_id: str,
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    """Parse historical survey PDF, extract past defects, dates, recommendations and photographs."""
    structure = heritage_repo.get_structure(structure_id)
    if not structure:
        raise HTTPException(status_code=404, detail=f"Structure '{structure_id}' not found.")

    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF survey documents are supported.")

    max_pdf_bytes = 25 * 1024 * 1024
    buffer = bytearray()
    chunk_size = 64 * 1024
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > max_pdf_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF document exceeds maximum permitted size of 25 MB.",
            )

    content = bytes(buffer)
    try:
        extraction = document_extraction_service.extract_from_pdf_bytes(
            content,
            filename=file.filename or "historical_survey.pdf",
            structure_id=structure_id,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.error("Document extraction error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse and extract survey document.",
        ) from exc

    doc_id = heritage_repo.save_document_record({
        "structure_id": structure_id,
        "filename": file.filename or "historical_survey.pdf",
        "file_path": "",
        "extracted_data": extraction,
    })
    extraction["document_id"] = doc_id
    return extraction


@api_router.post(
    "/structures/{structure_id}/documents/{document_id}/import-defects",
    summary="Confirm and Import Historical Defects into Defect Passports",
    tags=["Historical Documents"],
)
def import_historical_defects(
    structure_id: str,
    document_id: str,
    confirmed_defects: List[Dict[str, Any]] = Body(...),
) -> Dict[str, Any]:
    """Allow conservation architect to confirm and import historical defects into permanent Defect Passports."""
    doc = heritage_repo.get_document_record(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    imported_passports = []
    for defect in confirmed_defects:
        passport = heritage_repo.create_defect_passport({
            "structure_id": structure_id,
            "defect_category": defect.get("category", "crack"),
            "original_inspection_id": document_id,
            "original_image_id": f"{document_id}_p{defect.get('page_number', 1)}",
            "bounding_box": [0.0, 0.0, 100.0, 100.0],
            "confidence": 0.90,
            "severity": defect.get("severity", "moderate"),
            "status": "active",
            "verification_status": "human_verified",
            "repair_notes": defect.get("description", "Imported from historical survey archive"),
        })
        imported_passports.append(passport)

    return {
        "status": "success",
        "imported_count": len(imported_passports),
        "passports": imported_passports,
    }


