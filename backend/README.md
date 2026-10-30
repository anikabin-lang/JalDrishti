# JalDrishti Backend Service

**Lead Engineer:** Swastik Parmar (Backend / Cloudinary & Integration Lead)  
**Team:** Team NeuralX  
**Primary Directory:** `/backend`  
**Shared Contracts Directory:** `/contracts`

---

## 1. Overview & Architecture

The JalDrishti backend serves as the central API gateway, image asset manager, and multi-disciplinary conservation pipeline orchestrator. Built with FastAPI and Pydantic, the service coordinates:

1. **Backend-Controlled Image Ingestion:** Validates incoming inspection imagery (size bounds, format whitelists, binary decodability) and uploads to Cloudinary using backend-only credentials.
2. **Durable Local Metadata Persistence:** Records stable application-level image and inspection identifiers, Cloudinary asset mappings, dimensions, and timestamps in SQLite.
3. **Responsive Delivery & Provenance Traceability:** Serves auto-optimized, responsive preview URLs for frontend visualization while preserving uncompressed originals for conservation audits and computer vision inference.
4. **Computer Vision Inference (Krish):** Forwards uncompressed image streams or references to the local YOLOv8 defect extraction pipeline without exposing Cloudinary SDK internals to model code.
5. **Engineering & IKS Assessment (Kirti Antil):** Feeds defect metrics and hydrological site notes into deterministic condition scoring, material compatibility, and phased restoration engines.
6. **Unified Contract Delivery (Anika Jain):** Assembles validated `AnalysisResult` payloads matching shared JSON schemas in `/contracts`.

```
                        +----------------------------+
                        |   Frontend PWA (Anika)     |
                        +--------------+-------------+
                                       │
                      1. POST /images/upload (multipart)
                      2. POST /analyze (JSON / image_id)
                                       │
                                       ▼
                        +----------------------------+
                        |      FastAPI Backend       |
                        |     (Swastik Parmar)       |
                        +---+--------------------+---+
                            │                    │
              Upload / Get  │                    │ Persist Metadata
                            ▼                    ▼
                 +-------------------+  +-------------------+
                 |    Cloudinary     |  |   SQLite Store    |
                 |  (Cloud Storage)  |  | (data/jaldrishti) |
                 +-------------------+  +-------------------+
                            │
               Original Raw │ Inspection Stream
                            ▼
                 +-------------------+
                 | Vision Pipeline   |
                 | (YOLOv8 - Krish)  |
                 +-------------------+
                            │
               Defect Stats │ (cracks, vegetation)
                            ▼
                 +-------------------+
                 |  Engineering/IKS  |
                 |  (Rules - Kirti)  |
                 +-------------------+
```

---

## 2. Environment Configuration

Configuration is managed via environment variables and loaded through `backend/app/core/config.py`.  
Copy `.env.example` to `.env` to configure your local environment:

```bash
cp .env.example .env
```

### Required Cloudinary Configuration (Backend Only)
Cloudinary credentials must reside **strictly on the backend**. Never expose API secrets to frontend client bundles or commit them to version control.

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `CLOUDINARY_CLOUD_NAME` | string | *None* | Cloudinary cloud account name |
| `CLOUDINARY_API_KEY` | string | *None* | Cloudinary account API key |
| `CLOUDINARY_API_SECRET` | string | *None* | Cloudinary API secret key (**NEVER leak or log**) |
| `CLOUDINARY_FOLDER` | string | `jaldrishti/inspections` | Folder namespace in Cloudinary media library |
| `CLOUDINARY_SECURE_DELIVERY` | bool | `true` | Enforce HTTPS delivery URLs |

### Storage & Upload Policies

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `MAX_UPLOAD_SIZE_BYTES` | int | `26214400` (25 MB) | Maximum upload size threshold |
| `ALLOWED_IMAGE_FORMATS` | csv | `jpeg,jpg,png,webp` | Whitelisted image file formats |
| `SQLITE_DB_PATH` | string | `data/jaldrishti.db` | Local SQLite database file location |

---

## 3. Image Upload & Management API

All image endpoints are served under `/images` and `/inspections`.

### A. Upload Inspection Image (`POST /images/upload`)

- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Supported File Field Names:** `file`, `images` (compatible with frontend `FormData`), or `image`
- **Supported Form Fields:**
  - `inspection_id` *(optional, string)*: Existing inspection session identifier
  - `structure_type` *(optional, string)*: Heritage typology (`baoli`, `bawari`, `kund`, `vav`, `tank`, `other`)
  - `structure_name` *(optional, string)*: Monument or site designation
  - `notes` *(optional, string)*: Surveyor field notes
- **Supported File Formats:** JPEG, PNG, WEBP
- **Maximum File Size:** 25 MB (configurable via `MAX_UPLOAD_SIZE_BYTES`)

#### Request Example (cURL):
```bash
curl -X POST http://127.0.0.1:8000/images/upload \
  -F "file=@survey_agrasen_01.jpg" \
  -F "structure_type=baoli" \
  -F "structure_name=Agrasen ki Baoli" \
  -F "inspection_id=insp_delhi_2026_01"
```

#### Successful Response (`201 Created`):
Conforms strictly to [`contracts/image_upload_result.schema.json`](file:///contracts/image_upload_result.schema.json).
```json
{
  "image_id": "img_f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "inspection_id": "insp_delhi_2026_01",
  "status": "uploaded",
  "preview_url": "https://res.cloudinary.com/test-cloud/image/upload/c_limit,w_800,q_auto,f_auto/v1/jaldrishti/inspections/img_f47ac10b-58cc-4372-a567-0e02b2c3d479.jpg",
  "original_url": "https://res.cloudinary.com/test-cloud/image/upload/v1/jaldrishti/inspections/img_f47ac10b-58cc-4372-a567-0e02b2c3d479.jpg",
  "format": "jpeg",
  "width": 1920,
  "height": 1080,
  "bytes": 245120,
  "created_at": "2026-10-19T07:15:00.123456+00:00"
}
```

#### Error Responses:
- **`400 Bad Request`**:
  - Empty file: `{"detail": "Uploaded file is empty (0 bytes)."}`
  - Unsupported format: `{"detail": "Unsupported image format 'gif'. Supported formats: jpeg, png, webp."}`
  - Corrupted content: `{"detail": "Corrupted or undecodable image file."}`
  - Missing upload: `{"detail": "No image file provided in multipart request. Use 'file' or 'images' form field."}`
- **`413 Content Too Large`**:
  - `{"detail": "File size exceeds maximum allowed limit of 10.0 MB (10485760 bytes)."}`
- **`502 Bad Gateway`**:
  - `{"detail": "Cloudinary image upload failed. Please verify storage availability and try again."}`
- **`503 Service Unavailable`**:
  - `{"detail": "Image storage service is not configured. Required backend environment variables: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET."}`
- **`500 Internal Server Error`**:
  - `{"detail": "Failed to persist image metadata. Upload rolled back."}`

---

### B. Retrieve Image Metadata (`GET /images/{image_id}`)

- **Method:** `GET`
- **Status Code:** `200 OK` (or `404 Not Found`)
- **Response:** Returns the `ImageUploadResponse` payload with registered preview and original URLs.

```bash
curl http://127.0.0.1:8000/images/img_f47ac10b-58cc-4372-a567-0e02b2c3d479
```

---

### C. Delete Image Asset (`DELETE /images/{image_id}`)

- **Method:** `DELETE`
- **Status Code:** `200 OK`
- **Behavior:**
  1. Locates metadata record in SQLite store.
  2. Issues asset destroy command to Cloudinary via `cloudinary.uploader.destroy`.
  3. Purges metadata row from database.
  4. Returns granular status reporting. Handles partial failures explicitly.

#### Successful Response:
```json
{
  "image_id": "img_f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "deleted",
  "detail": "Image asset deleted from Cloudinary and metadata repository.",
  "cloudinary_deleted": true,
  "metadata_deleted": true
}
```

#### Partial Failure Handling:
- If Cloudinary deletion fails while database cleanup succeeds, returns `HTTP 502 Bad Gateway` noting partial failure.
- If Cloudinary succeeds while database cleanup fails, returns `HTTP 500 Internal Server Error` noting partial failure.

---

### E. List Stored Images (`GET /images`)

- **Method:** `GET`
- **Status Code:** `200 OK`
- **Query Parameters:**
  - `site_id` *(optional, string)*: Filter by heritage site identifier
  - `inspection_id` *(optional, string)*: Filter by inspection session
  - `structure_type` *(optional, string)*: Filter by typology (`baoli`, `kund`, `vav`, etc.)
  - `limit` *(optional, int, default 20, max 100)*: Page size
  - `offset` *(optional, int, default 0)*: Number of records to skip
- **Response:**
```json
{
  "total": 42,
  "limit": 20,
  "offset": 0,
  "site_id": "agrasen_ki_baoli",
  "inspection_id": null,
  "images": [
    {
      "image_id": "img_f47ac10b-58cc-4372-a567-0e02b2c3d479",
      "site_id": "agrasen_ki_baoli",
      "inspection_id": "insp_delhi_2026_01",
      "public_id": "jaldrishti/inspections/agrasen_ki_baoli/insp_delhi_2026_01/img_f47ac10b...",
      "asset_id": "asset_12345",
      "format": "jpeg",
      "width": 1920,
      "height": 1080,
      "bytes": 245120,
      "created_at": "2026-10-19T07:15:00.123456+00:00",
      "status": "uploaded",
      "structure_type": "baoli",
      "original_filename": "survey_agrasen_01.jpg",
      "preview_url": "https://res.cloudinary.com/.../c_limit,w_800,q_auto,f_auto/...",
      "thumbnail_url": "https://res.cloudinary.com/.../c_fill,h_300,w_300,q_auto,f_auto/...",
      "original_url": "https://res.cloudinary.com/.../image/upload/..."
    }
  ]
}
```

---

### F. Live Cloudinary Asset Search (`GET /images/cloud-search`)

- **Method:** `GET`
- **Status Code:** `200 OK`
- **Query Parameters:**
  - `query` *(optional, string)*: Custom Cloudinary search expression or keywords
  - `site_id` *(optional, string)*: Filter by site
  - `inspection_id` *(optional, string)*: Filter by inspection session
  - `folder` *(optional, string)*: Target folder path
  - `tag` *(optional, string)*: Tag filter
  - `max_results` *(optional, int, default 20, max 100)*: Asset limit
  - `next_cursor` *(optional, string)*: Cursor for pagination
- **Response:**
```json
{
  "total_count": 85,
  "next_cursor": "cursor_token_next_page",
  "resources": [
    {
      "public_id": "jaldrishti/inspections/site_chand/insp_9/img_1",
      "asset_id": "asset_search_001",
      "format": "jpg",
      "width": 1280,
      "height": 960,
      "bytes": 524000,
      "created_at": "2026-10-20T10:00:00Z",
      "secure_url": "https://res.cloudinary.com/test-cloud/image/upload/v1/...",
      "preview_url": "https://res.cloudinary.com/.../c_limit,w_800,q_auto,f_auto/...",
      "thumbnail_url": "https://res.cloudinary.com/.../c_fill,h_300,w_300,q_auto,f_auto/...",
      "folder": "jaldrishti/inspections/site_chand/insp_9",
      "site_id": "site_chand",
      "inspection_id": "insp_9",
      "tags": ["jaldrishti", "baoli", "site:site_chand"]
    }
  ]
}
```

---

### G. List Registered Heritage Sites (`GET /sites`)

- **Method:** `GET`
- **Status Code:** `200 OK`
- **Response:**
```json
{
  "total_sites": 3,
  "sites": [
    {
      "site_id": "agrasen_ki_baoli",
      "site_name": "Agrasen Ki Baoli",
      "structure_type": "baoli",
      "total_images": 24,
      "total_inspections": 4,
      "latest_upload": "2026-10-25T14:20:00+00:00",
      "cover_thumbnail_url": "https://res.cloudinary.com/.../c_fill,h_300,w_300,q_auto,f_auto/..."
    }
  ]
}
```

---

## 4. Subsystem Integration Contracts

### A. Integration with Anika Jain (Frontend / PWA)
1. **Direct Upload:** When a surveyor snaps or selects a photo, POST it to `/images/upload` using `FormData.append('file', photoBlob)`. Pass `site_id` (e.g. `agrasen_ki_baoli`) to automatically organize assets within `jaldrishti/inspections/<site_id>/<inspection_id>/<image_id>`.
2. **Displaying Previews & Thumbnails:** Use `response.preview_url` for responsive headers and full previews, and `response.thumbnail_url` (`c_fill,w_300,h_300,q_auto,f_auto`) for fast grid card rendering in the Heritage Image Gallery (`/gallery`).
3. **Heritage Gallery Exploration (`05 / Gallery`):** Query stored photos through `GET /images` with site, inspection, or typology filters, or execute real-time queries across Cloudinary with `GET /images/cloud-search`.
4. **Triggering Analysis:** Call `POST /analyze` with the returned `image_id`:
   ```json
   {
     "image_id": "img_f47ac10b-58cc-4372-a567-0e02b2c3d479",
     "structure_type": "baoli",
     "name": "Agrasen ki Baoli",
     "region": "Delhi"
   }
   ```
   The backend orchestrator automatically resolves the image dimensions and preview URI from the persistent metadata store.

### B. Integration with Krish (Computer Vision / AI)
1. **Isolation from Storage Provider:** Model inference code (`vision/`) contains **zero Cloudinary SDK imports**.
2. **Raw Pixel Integrity:** Vision models receive uncorrupted raw bytes (`image_bytes: bytes`) or local file paths. Lossy preview compression is never applied to model input. When an `image_id` is supplied without re-uploading file bytes, the backend orchestrator downloads the full original asset (`fetch_original_image_bytes`) directly from Cloudinary's secure original URL, preserving native photographic resolution for Faster R-CNN and YOLO inference.
3. **Dimensions & Normalization:** Spatial dimensions are extracted deterministically and passed to the model service boundary (`vision_service.analyze_image`).

### C. Integration with Kirti Antil (Engineering & IKS)
1. Inferred defect metrics and hydrological indicators flow seamlessly from the resolved inspection into `engineering_service.assess_full_structure`.
2. No fabricated condition scores or intervention materials are introduced; deterministic rules govern all engineering assessments.

---

## 5. Security, Retention & Privacy Safeguards

- **Backend-Only Secrets:** Cloudinary API Secret is strictly confined to the backend process and never serialized in API responses or client logs.
- **Defense Against Memory Exhaustion:** Image streams are read in bounded 64 KB chunks. If total bytes exceed 10 MB, the stream is aborted immediately with HTTP 413 before memory is saturated.
- **Deep Content Validation:** Files are verified with Pillow (`Image.open().verify()`) to guard against header spoofing, polyglot payloads, and malformed binaries.
- **No Arbitrary URL Fetching:** Server-Side Request Forgery (SSRF) risk is prevented by refusing arbitrary remote URL download requests.
- **Retention Policy:** Uploaded inspection photos are preserved indefinitely for heritage archival and temporal degradation comparisons, unless explicitly removed via `DELETE /images/{image_id}`.

---

## 6. Automated Testing

All tests run locally using mocks without requiring live Cloudinary credentials or paid external calls.

Run backend and image upload test suites:
```bash
# Run image upload and Cloudinary mock tests
./.venv/bin/pytest tests/backend/test_image_upload.py

# Run all backend unit & integration tests
./.venv/bin/pytest tests/backend/

# Run complete repository test suite
./.venv/bin/pytest
```

---

## 7. Local Server Execution

```bash
./.venv/bin/uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
Verify the health check endpoint:
```bash
curl http://127.0.0.1:8000/health
```
