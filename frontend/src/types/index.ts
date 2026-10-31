/**
 * Jaldrishti Frontend Type Definitions
 *
 * Strictly aligned with backend shared JSON contracts in /contracts:
 * - contracts/analysis.schema.json
 * - contracts/vision_result.schema.json
 * - contracts/engineering_result.schema.json
 * - contracts/material_compatibility.schema.json
 * - contracts/restoration_result.schema.json
 *
 * Owned by: Anika Jain (Frontend / PWA / Digital Twin)
 */

export type StructureTypology = 'baoli' | 'bawari' | 'kund' | 'vav' | 'tank' | 'other';

export interface StructureContext {
  type: StructureTypology;
  name?: string;
  region?: string;
  source_images: string[];
}

export interface ImageDimensions {
  width_pixels: number;
  height_pixels: number;
}

export interface ScaleReference {
  calibrated?: boolean;
  pixels_per_millimeter?: number;
  method?: string;
}

export type DefectSeverity = 'low' | 'moderate' | 'severe';

export interface DetectionItem {
  class_name: string;
  confidence: number;
  bounding_box: [number, number, number, number]; // [x_min, y_min, x_max, y_max]
  segmentation_mask_reference?: string;
  pixel_area: number;
  coverage_ratio: number;
  component_count: number;
  total_length_pixels?: number;
  largest_component_length_pixels?: number;
  relative_severity?: DefectSeverity;
  burden_score?: number;
}

export interface VisionResultContract {
  structure_type: 'baoli' | 'bawari' | 'kund' | 'vav' | 'tank' | 'unknown';
  image_dimensions: ImageDimensions;
  scale_reference?: ScaleReference;
  detections: DetectionItem[];
  processing_metadata?: {
    inference_latency_ms?: number;
    model_version?: string;
  };
  relevance_status?: 'relevant' | 'uncertain' | 'irrelevant';
  relevance_confidence?: number;
  quality_status?: 'good' | 'blurred' | 'poor_lighting';
  rejection_reason?: string | null;
  needs_manual_review?: boolean;
  status_message?: string;
}

export interface MetricScore {
  value: number;
  scale_min: number;
  scale_max: number;
  method: string;
  confidence: number;
  limitations: string[];
}

export interface EngineeringSubScores {
  vegetation_intrusion_index?: MetricScore;
  masonry_integrity_index?: MetricScore;
  siltation_obstruction_index?: MetricScore;
  visual_crack_burden?: MetricScore;
}

export type RootCauseUrgency = 'low' | 'medium' | 'high' | 'critical';

export interface RootCauseItem {
  finding: string;
  probable_cause: string;
  evidence_rules: string[];
  urgency?: RootCauseUrgency;
  /** Fields below are sent by the live `/analyze` rule engine but absent from the fixture. */
  observed_indicator?: string;
  additional_investigation_required?: string[];
  expert_review_required?: boolean;
  expert_specialty?: string;
  supporting_sources?: string[];
  uncertainty_note?: string;
}

export interface EngineeringResultContract {
  visual_condition_score: MetricScore;
  water_functionality_score: MetricScore;
  restoration_priority_score: MetricScore;
  sub_scores?: EngineeringSubScores;
  root_cause_analysis?: RootCauseItem[];
  engineering_disclaimer: string;
}

export interface CompatibilityDimensions {
  mechanical: number; // 0-10
  moisture: number; // 0-10
  thermal: number; // 0-10
  chemical: number; // 0-10
  reversibility: number; // 0-10
  heritage: number; // 0-10
  visual: number; // 0-10
}

export type RecommendationLevel = 
  | 'strongly_recommended'
  | 'recommended'
  | 'acceptable_conditional'
  | 'prohibited_incompatible';

export interface CandidateIntervention {
  intervention_material: string;
  compatibility_score: number;
  compatibility_dimensions: CompatibilityDimensions;
  recommendation: RecommendationLevel;
  warnings: string[];
}

export interface MaterialCompatibilityContract {
  original_material: string;
  original_material_confidence: number;
  verification_required: boolean;
  recommended_tests?: string[];
  candidate_interventions: CandidateIntervention[];
}

export type RestorationPhase = 
  | 'phase_1_immediate_stabilization'
  | 'phase_2_hydrological_remediation'
  | 'phase_3_masonry_and_iks_consolidation'
  | 'phase_4_long_term_monitoring';

export type ActionUrgency = 'immediate' | 'high' | 'medium' | 'routine';

export interface PrioritizedAction {
  step: number;
  phase: RestorationPhase;
  action_title: string;
  target_defect: string;
  recommended_technique: string;
  material_specification: string;
  urgency: ActionUrgency;
  preconditions?: string[];
}

export type IncompatibleSeverity = 'destructive' | 'high_risk' | 'moderate_risk';

export interface IncompatiblePractice {
  prohibited_action: string;
  failure_mechanism: string;
  severity: IncompatibleSeverity;
}

export interface IKSGuidelines {
  traditional_mortar_recipe: string;
  craftsmanship_references: string[];
  seasonal_curing_rules: string;
}

export type RestorationStrategy = 
  | 'minimal_stabilization'
  | 'material_consolidation'
  | 'hydrological_revival'
  | 'comprehensive_heritage_rehabilitation';

export interface RestorationResultContract {
  restoration_strategy: RestorationStrategy;
  prioritized_actions: PrioritizedAction[];
  incompatible_practices: IncompatiblePractice[];
  iks_guidelines: IKSGuidelines;
}

/** Shape returned by the live `/analyze` endpoint for `root_cause`. */
export interface RootCauseSummary {
  findings: RootCauseItem[];
  primary_cause?: string;
  count?: number;
}

export interface PipelineMetadata {
  created_at: string;
  pipeline_status: 'completed' | 'partial' | 'failed';
  orchestrated_by?: string;
}

/**
 * Unified contract representing contracts/analysis.schema.json
 */
export interface AnalysisResultContract {
  project_version: string;
  structure: StructureContext;
  vision: VisionResultContract;
  visual_condition: MetricScore | { score: MetricScore } | Record<string, unknown>;
  visual_crack_burden?: MetricScore;
  water_functionality: MetricScore | { score: MetricScore } | Record<string, unknown>;
  restoration_priority_score?: MetricScore;
  sub_scores?: EngineeringSubScores;
  material: MaterialCompatibilityContract;
  root_cause: RootCauseSummary | RootCauseItem[] | Record<string, unknown>;
  restoration: RestorationResultContract;
  metadata: PipelineMetadata;
}

/**
 * Frontend Navigation & Application State Types
 */
export type AppRoute = '/' | '/upload' | '/analysis' | '/knowledge' | '/report' | '/gallery';

/**
 * Mirrors contracts/image_upload_result.schema.json (POST /images/upload).
 * Cloudinary storage only; an uploaded image has not been analysed.
 */
export interface ImageUploadResult {
  image_id: string;
  inspection_id?: string | null;
  site_id?: string | null;
  status: 'uploaded' | 'processing' | 'ready' | 'failed' | string;
  preview_url: string;
  thumbnail_url?: string | null;
  original_url?: string | null;
  format: string;
  width: number;
  height: number;
  bytes: number;
  created_at: string;
  structure_type?: string | null;
  original_filename?: string | null;
  inspection_status?: 'accepted' | 'rejected' | 'uncertain' | 'uploaded' | string;
  relevance_confidence?: number | null;
  rejection_reason?: string | null;
  needs_manual_review?: boolean;
  model_version?: string | null;
}

export interface HeritageImageSummary {
  image_id: string;
  site_id?: string | null;
  inspection_id?: string | null;
  public_id: string;
  asset_id?: string | null;
  format: string;
  width: number;
  height: number;
  bytes: number;
  created_at: string;
  status: string;
  structure_type?: string | null;
  original_filename?: string | null;
  preview_url: string;
  thumbnail_url: string;
  original_url: string;
  inspection_status?: string | null;
  relevance_confidence?: number | null;
  rejection_reason?: string | null;
  needs_manual_review?: boolean;
  model_version?: string | null;
}

export interface PaginatedImagesResponse {
  total: number;
  limit: number;
  offset: number;
  site_id?: string | null;
  inspection_id?: string | null;
  images: HeritageImageSummary[];
}

export interface CloudinaryAssetItem {
  public_id: string;
  asset_id?: string | null;
  format: string;
  width: number;
  height: number;
  bytes: number;
  created_at: string;
  secure_url: string;
  preview_url: string;
  thumbnail_url: string;
  folder?: string | null;
  site_id?: string | null;
  inspection_id?: string | null;
  tags?: string[];
}

export interface CloudinarySearchResponse {
  total_count: number;
  next_cursor?: string | null;
  resources: CloudinaryAssetItem[];
}

export interface SiteSummary {
  site_id: string;
  site_name: string;
  structure_type?: string | null;
  total_images: number;
  total_inspections: number;
  latest_upload?: string | null;
  cover_thumbnail_url?: string | null;
}

export interface SiteListResponse {
  total_sites: number;
  sites: SiteSummary[];
}

/**
 * Where an analysis result came from. 'fixture' is the local development
 * sample and must never be presented as a real inspection.
 */
export type ResultProvenance = 'live' | 'fixture';

export interface InspectionSession {
  result: AnalysisResultContract;
  provenance: ResultProvenance;
  /** Present only when the image was stored through the backend Cloudinary workflow. */
  image?: ImageUploadResult;
  /** Local object URL of the inspected file, used for overlays when no stored preview exists. */
  localPreviewUrl?: string;
}

/**
 * Region of Interest (ROI) coordinates for focused defect inspection
 */
export interface InspectionROI {
  x: number; // percentage (0-100) or pixel coordinate
  y: number;
  width: number;
  height: number;
  isNormalized?: boolean;
}

export interface AnalysisRequestPayload {
  imageFile?: File;
  /** Backend image id from POST /images/upload, when the image was stored. */
  imageId?: string;
  imagePreviewUrl?: string;
  structureType: StructureTypology;
  structureName?: string;
  region?: string;
  notes?: string;
  roi?: InspectionROI;
}

/**
 * Knowledge base records served by GET /knowledge/structures (knowledge/structures/*.json).
 */
export interface EngineeringPrincipleRecord {
  principle: string;
  what?: string;
  why?: string;
  how?: string;
  engineering_significance?: string;
}

export interface WaterManagementPrincipleRecord {
  principle: string;
  description?: string;
  hydrological_mechanism?: string;
}

export interface TraditionalMaterialRecord {
  material_family: string;
  usage?: string;
  traditional_role?: string;
}

export interface StructureKnowledgeRecord {
  id: string;
  name: string;
  alternate_names?: string[];
  regions?: string[];
  traditional_function?: string[];
  engineering_principles?: EngineeringPrincipleRecord[];
  water_management_principles?: WaterManagementPrincipleRecord[];
  environmental_adaptations?: string[];
  traditional_materials?: TraditionalMaterialRecord[];
  construction_features?: string[];
  common_deterioration_factors?: string[];
  conservation_considerations?: string[];
  sources?: string[];
  limitations?: string[];
}

/** GET /knowledge/sources (knowledge/sources/sources_index.json). */
export interface KnowledgeSource {
  source_id: string;
  title: string;
  publisher?: string;
  year?: number;
  url?: string;
  topic?: string;
  claim_supported?: string;
  claims_supported?: string[];
}

// ==============================================================================
// ENTERPRISE EXTENSIONS: HERITAGE STRUCTURES, BASELINE & DEFECT PASSPORTS
// ==============================================================================

export interface HeritageStructure {
  structure_id: string;
  name: string;
  typology: string;
  location: string;
  region: string;
  historical_period: string;
  notes: string;
  baseline_completed: boolean;
  baseline_inspection_id?: string | null;
  created_at: string;
  updated_at: string;
  total_defects?: number;
  active_defects?: number;
  total_inspections?: number;
}

export interface DefectPassport {
  defect_id: string;
  structure_id: string;
  defect_category: 'crack' | 'vegetation' | string;
  first_detected_date: string;
  original_inspection_id: string;
  original_image_id: string;
  bounding_box: [number, number, number, number];
  confidence: number;
  severity: 'low' | 'moderate' | 'severe' | string;
  status: 'active' | 'monitoring' | 'repaired' | 'critical' | string;
  verification_status: 'ai_detected' | 'human_verified' | 'rejected' | string;
  repair_notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DefectObservation {
  observation_id: string;
  defect_id: string;
  inspection_id: string;
  image_id: string;
  bounding_box: [number, number, number, number];
  confidence: number;
  observed_status: string;
  notes?: string | null;
  created_at: string;
}

export interface InspectionImageRecord {
  image_id: string;
  inspection_id: string;
  structure_id: string;
  original_filename: string;
  preview_url?: string;
  quality_status: string;
  relevance_status: string;
  relevance_confidence: number;
  inspection_status: string;
  rejection_reason?: string | null;
  results_json?: Record<string, any>;
  image_order: number;
}

export interface BaselineInspectionResult {
  inspection_id: string;
  structure_id: string;
  status: 'completed' | 'incomplete';
  baseline_completed: boolean;
  summary: {
    status: string;
    total_images: number;
    valid_images: number;
    rejected_images: number;
    total_cracks: number;
    vegetation_count: number;
    message: string;
  };
  images: InspectionImageRecord[];
  defects_registered: number;
  passports?: string[] | DefectPassport[];
}

export interface ExtractedDefect {
  description: string;
  category: string;
  severity: string;
  page_number: number;
  confirmed?: boolean;
}

export interface DocumentExtractionResult {
  document_id: string;
  structure_id: string;
  filename: string;
  status: string;
  total_pages: number;
  extracted_structure_name?: string | null;
  extracted_inspection_date?: string | null;
  extracted_defects: ExtractedDefect[];
  extracted_recommendations: string[];
  extracted_photos_count: number;
}
