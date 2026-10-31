import React, { useEffect, useId, useRef, useState } from 'react';
import { PageContainer } from '../components/PageContainer';
import { UploadZone, SelectedImage } from '../components/UploadZone';
import { ROISelector } from '../components/ROISelector';
import { PipelineStages, PipelineStage, StageStatus } from '../components/PipelineStages';
import { Button } from '../components/Button';
import { Icon } from '../components/Icon';
import {
  AnalysisResultContract,
  AppRoute,
  ImageUploadResult,
  InspectionROI,
  InspectionSession,
  StructureTypology,
} from '../types';
import { ApiError, deleteInspectionImage, submitAnalysisRequest, uploadInspectionImage } from '../services/api';
import { formatBytes } from '../utils/analysis';
import { BaselineInspectionWizard } from '../components/BaselineInspectionWizard';
import { DefectPassportRegistry } from '../components/DefectPassportRegistry';
import { HistoricalPdfExtractor } from '../components/HistoricalPdfExtractor';
import { useLanguage } from '../i18n/LanguageContext';

export interface UploadPageProps {
  onComplete: (session: InspectionSession) => void;
  onRouteChange: (route: AppRoute) => void;
}

const TYPOLOGIES: { value: StructureTypology; label: string }[] = [
  { value: 'baoli', label: 'Baoli — stepwell' },
  { value: 'bawari', label: 'Bawari — stepped reservoir' },
  { value: 'vav', label: 'Vav — Gujarati stepwell' },
  { value: 'kund', label: 'Kund — stepped tank' },
  { value: 'tank', label: 'Tank' },
  { value: 'other', label: 'Other water structure' },
];

const REGION_SUGGESTIONS = [
  'Delhi NCR',
  'Rajasthan',
  'Gujarat',
  'Haryana',
  'Uttar Pradesh',
  'Madhya Pradesh',
  'Maharashtra',
  'Karnataka',
  'Bihar',
];

interface StageState {
  status: StageStatus;
  progress?: number;
  error?: string;
  code?: number;
}

const formatErrorText = (error: unknown, t: (key: string, fallback?: string) => string) => {
  if (error instanceof Error) {
    if (error.message.includes('Could not reach the JalDrishti API')) {
      return t('error.couldNotReachApi', 'Could not reach the JalDrishti API. Check that the backend is running.');
    }
    return error.message;
  }
  return t('error.requestFailed', 'The request failed. Check the network and backend service.');
};

export const UploadPage: React.FC<UploadPageProps> = ({ onComplete, onRouteChange }) => {
  const formId = useId();
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<'baseline' | 'passports' | 'historical' | 'single'>('baseline');
  const [selected, setSelected] = useState<SelectedImage | null>(null);
  const [structureType, setStructureType] = useState<StructureTypology>('baoli');
  const [structureName, setStructureName] = useState('');
  const [region, setRegion] = useState('');
  const [notes, setNotes] = useState('');
  const [roiEnabled, setRoiEnabled] = useState(false);
  const [roi, setRoi] = useState<InspectionROI | null>(null);

  const [storage, setStorage] = useState<StageState>({ status: 'pending' });
  const [analysis, setAnalysis] = useState<StageState>({ status: 'pending' });
  const [stored, setStored] = useState<ImageUploadResult | null>(null);
  const [result, setResult] = useState<AnalysisResultContract | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const openFindingsRef = useRef<HTMLButtonElement>(null);
  const statusRef = useRef<HTMLElement>(null);

  const busy = storage.status === 'active' || analysis.status === 'active';
  const fileLocked = busy || stored !== null;

  useEffect(() => {
    if (result) openFindingsRef.current?.focus();
  }, [result]);

  // A failure must not go unseen below the fold.
  const failed = storage.status === 'failed' || analysis.status === 'failed';
  useEffect(() => {
    if (!failed) return;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    statusRef.current?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'nearest' });
  }, [failed]);

  const resetPipeline = () => {
    setStorage({ status: 'pending' });
    setAnalysis({ status: 'pending' });
    setResult(null);
    setNotice(null);
  };

  const handleSelect = (image: SelectedImage) => {
    if (selected && !result) URL.revokeObjectURL(selected.previewUrl);
    setSelected(image);
    setRoi(null);
    resetPipeline();
  };

  const handleClear = () => {
    if (selected && !result) URL.revokeObjectURL(selected.previewUrl);
    setSelected(null);
    setRoi(null);
    setRoiEnabled(false);
    resetPipeline();
  };

  const runAnalysis = async (image: ImageUploadResult | null) => {
    if (!selected) return;
    setAnalysis({ status: 'active' });
    try {
      const response = await submitAnalysisRequest({
        imageFile: selected.file,
        imageId: image?.image_id,
        structureType,
        structureName: structureName.trim() || undefined,
        region: region.trim() || undefined,
        notes: notes.trim() || undefined,
        roi: roiEnabled && roi && roi.width > 0 ? roi : undefined,
      });
      setResult(response);
      setAnalysis({ status: 'done' });
    } catch (error) {
      setAnalysis({ status: 'failed', error: formatErrorText(error, t) });
    }
  };

  const runStorage = async () => {
    if (!selected) return;
    setNotice(null);
    setStorage({ status: 'active', progress: 0 });
    setAnalysis({ status: 'pending' });
    try {
      const derivedSiteId = structureName.trim()
        ? structureName.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
        : undefined;

      const image = await uploadInspectionImage(
        selected.file,
        {
          structureType,
          structureName: structureName.trim() || undefined,
          siteId: derivedSiteId,
          notes: notes.trim() || undefined,
        },
        (fraction) => setStorage({ status: 'active', progress: fraction }),
      );
      setStored(image);
      setStorage({ status: 'done' });
      await runAnalysis(image);
    } catch (error) {
      setStorage({
        status: 'failed',
        error: formatErrorText(error, t),
        code: error instanceof ApiError ? error.statusCode : undefined,
      });
    }
  };

  const handleStart = () => {
    if (stored) {
      void runAnalysis(stored);
    } else {
      void runStorage();
    }
  };

  const handleContinueWithoutStoring = () => {
    setStorage({ status: 'skipped' });
    void runAnalysis(null);
  };

  const handleDeleteStored = async () => {
    if (!stored) return;
    setDeleting(true);
    setNotice(null);
    try {
      await deleteInspectionImage(stored.image_id);
      setStored(null);
      resetPipeline();
      setNotice(t('upload.deleteSuccess', 'The stored image and its metadata record were deleted.'));
    } catch (error) {
      setNotice(`${t('upload.deleteFailed', 'Deletion failed')}: ${formatErrorText(error, t)}`);
    } finally {
      setDeleting(false);
    }
  };

  const handleOpenFindings = () => {
    if (!result || !selected) return;
    onComplete({
      result,
      provenance: 'live',
      image: stored ?? undefined,
      localPreviewUrl: selected.previewUrl,
    });
  };

  const stages: PipelineStage[] = [
    {
      id: 'store',
      title: t('pipeline.storeImage', 'Store image'),
      description: t(
        'pipeline.storeImageDesc',
        'Sent to the JalDrishti API, validated, and stored in Cloudinary. Storage alone does not analyse the image.'
      ),
      status: storage.status,
      progress: storage.progress,
      activeLabel:
        storage.progress !== undefined && storage.progress >= 1
          ? t('pipeline.waitingValidation', 'Uploaded — waiting for the server to validate and store')
          : t('pipeline.uploading', 'Uploading'),
      error: storage.error,
      detail:
        storage.status === 'failed' ? (
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={handleStart} icon={<Icon name="refresh" className="h-3.5 w-3.5" />}>
              {t('pipeline.retryStorage', 'Retry storage')}
            </Button>
            <Button size="sm" variant="quiet" onClick={handleContinueWithoutStoring}>
              {t('pipeline.continueWithoutStoring', 'Continue without storing')}
            </Button>
          </div>
        ) : stored ? (
          <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-[0.8125rem]">
            <dt className="text-ws-faint">{t('pipeline.imageId', 'Image ID')}</dt>
            <dd className="truncate font-mono text-ws-text">{stored.image_id}</dd>
            {stored.inspection_id && (
              <>
                <dt className="text-ws-faint">{t('pipeline.inspectionId', 'Inspection ID')}</dt>
                <dd className="truncate font-mono text-ws-text">{stored.inspection_id}</dd>
              </>
            )}
            <dt className="text-ws-faint">{t('pipeline.stored', 'Stored')}</dt>
            <dd className="font-mono tabular-nums text-ws-text">
              {stored.width} × {stored.height} · {stored.format} · {formatBytes(stored.bytes)}
            </dd>
          </dl>
        ) : storage.status === 'skipped' ? (
          <p className="text-[0.8125rem] text-ws-muted">
            {t('pipeline.skippedNote', 'This image was analysed without being stored. It will not appear in inspection history.')}
          </p>
        ) : undefined,
    },
    {
      id: 'analyse',
      title: t('pipeline.analyse', 'Analyse'),
      description: t(
        'pipeline.analyseDesc',
        'Vision detection, then rule-based engineering, material compatibility and restoration planning.'
      ),
      status: analysis.status,
      activeLabel: t('pipeline.waitingAnalysis', 'Waiting for the analysis service to respond'),
      error: analysis.error,
      detail:
        analysis.status === 'failed' ? (
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="secondary" onClick={() => void runAnalysis(stored)} icon={<Icon name="refresh" className="h-3.5 w-3.5" />}>
                {t('pipeline.retryAnalysis', 'Retry analysis')}
              </Button>
            </div>
            <p className="text-[0.8125rem] leading-relaxed text-ws-muted">
              {t('pipeline.noResult', 'No result was produced. To explore the interface with the labelled development sample instead, ')}
              <button type="button" className="font-medium text-ws-text underline underline-offset-2" onClick={() => onRouteChange('/analysis')}>
                {t('pipeline.openFindingsPage', 'open the Findings page')}
              </button>
              .
            </p>
          </div>
        ) : undefined,
    },
    {
      id: 'ready',
      title: t('pipeline.resultsReady', 'Results ready'),
      description: t('pipeline.resultsReadyDesc', 'Shown only once the API has returned a complete response.'),
      status: result ? 'done' : 'pending',
      detail: result ? (
        <p className="text-[0.8125rem] text-ws-muted">
          {result.vision.detections.length === 0
            ? t('pipeline.noDetections', 'The vision service returned no detections for this image.')
            : `${result.vision.detections.length} ${t('pipeline.detectionsReturned', 'detections returned.')}`}
        </p>
      ) : undefined,
    },
  ];

  const startLabel = stored
    ? t('upload.analyseStored', 'Analyse stored image')
    : t('upload.storeAndAnalyse', 'Store and analyse');

  return (
    <PageContainer
      eyebrow={t('upload.eyebrow', 'JalDrishti / Inspection')}
      title={t('upload.title', 'Inspect a heritage water structure.')}
      subtitle={t(
        'upload.subtitle',
        'Document a traditional water structure through photographs and contextual observations, creating a useful starting point for closer examination — not a diagnosis.'
      )}
      plate="stepwell-reflection"
      treatment="panel"
      ground="dark"
    >
      <div className="mb-8 flex flex-wrap items-center gap-2 border-b border-[var(--ws-line-dark)] pb-4">
        <button
          type="button"
          onClick={() => setActiveTab('baseline')}
          className={`flex items-center gap-2 rounded-full px-4 py-2 text-xs font-medium transition ${
            activeTab === 'baseline'
              ? 'bg-ws-text text-ws-stone shadow-md'
              : 'border border-ws-border text-ws-muted hover:bg-ws-card hover:text-ws-text'
          }`}
        >
          <Icon name="upload" className="h-3.5 w-3.5" />
          <span>{t('nav.baseline')}</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('passports')}
          className={`flex items-center gap-2 rounded-full px-4 py-2 text-xs font-medium transition ${
            activeTab === 'passports'
              ? 'bg-ws-text text-ws-stone shadow-md'
              : 'border border-ws-border text-ws-muted hover:bg-ws-card hover:text-ws-text'
          }`}
        >
          <Icon name="book" className="h-3.5 w-3.5" />
          <span>{t('nav.passports')}</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('historical')}
          className={`flex items-center gap-2 rounded-full px-4 py-2 text-xs font-medium transition ${
            activeTab === 'historical'
              ? 'bg-ws-text text-ws-stone shadow-md'
              : 'border border-ws-border text-ws-muted hover:bg-ws-card hover:text-ws-text'
          }`}
        >
          <Icon name="document" className="h-3.5 w-3.5" />
          <span>{t('nav.historical')}</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('single')}
          className={`flex items-center gap-2 rounded-full px-4 py-2 text-xs font-medium transition ${
            activeTab === 'single'
              ? 'bg-ws-text text-ws-stone shadow-md'
              : 'border border-ws-border text-ws-muted hover:bg-ws-card hover:text-ws-text'
          }`}
        >
          <Icon name="image" className="h-3.5 w-3.5" />
          <span>{t('nav.single', 'Single Photo Quick Scan')}</span>
        </button>
      </div>

      {activeTab === 'baseline' && <BaselineInspectionWizard onInspectComplete={() => {}} />}
      {activeTab === 'passports' && <DefectPassportRegistry />}
      {activeTab === 'historical' && <HistoricalPdfExtractor />}

      {activeTab === 'single' && (
        <>
          <div className="grid gap-x-16 gap-y-12 lg:grid-cols-12">
        <section aria-labelledby={`${formId}-photo`} className="lg:col-span-7">
          <h2 id={`${formId}-photo`} className="mb-5 font-display text-[1.75rem] font-medium leading-tight text-ws-text">
            {t('upload.photoSection', 'Photograph')}
          </h2>

          <UploadZone
            selected={selected}
            onSelect={handleSelect}
            onClear={handleClear}
            locked={fileLocked}
            lockedReason={stored ? t('upload.lockedStored', 'Stored — delete the stored image to replace it.') : busy ? t('upload.lockedRunning', 'Locked while the pipeline runs.') : undefined}
            previewSlot={
              selected && roiEnabled ? (
                <ROISelector
                  imageSrc={selected.previewUrl}
                  naturalWidth={selected.width}
                  naturalHeight={selected.height}
                  roi={roi}
                  onChangeROI={setRoi}
                />
              ) : undefined
            }
          />

          {selected && (
            <label className="mt-6 flex cursor-pointer items-start gap-3 border-t border-[var(--ws-line-dark)] pt-5">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 accent-ws-moss"
                checked={roiEnabled}
                disabled={busy}
                onChange={(event) => {
                  setRoiEnabled(event.target.checked);
                  if (!event.target.checked) setRoi(null);
                }}
              />
              <span>
                <span className="block text-[0.9375rem] font-medium text-ws-text">
                  {t('upload.limitRegion', 'Limit analysis to a region (optional)')}
                </span>
                <span className="mt-1 block text-[0.8125rem] leading-relaxed text-ws-muted">
                  {t(
                    'upload.limitRegionDesc',
                    'Off by default — the whole photograph is analysed. If enabled, drag on the image or type pixel values.'
                  )}
                </span>
              </span>
            </label>
          )}
        </section>

        <div className="lg:col-span-5">
          <section aria-labelledby={`${formId}-details`}>
            <h2 id={`${formId}-details`} className="mb-5 font-display text-[1.75rem] font-medium leading-tight text-ws-text">
              {t('upload.detailsSection', 'About the structure')}
            </h2>
            <form
              id={formId}
              onSubmit={(event) => {
                event.preventDefault();
                handleStart();
              }}
            >
              <fieldset disabled={busy} className="space-y-5">
                <legend className="sr-only">{t('upload.structureDetails', 'Structure details')}</legend>
                <div>
                  <label htmlFor={`${formId}-type`} className="field-label">
                    {t('upload.typology', 'Typology')}
                  </label>
                  <select
                    id={`${formId}-type`}
                    className="field"
                    value={structureType}
                    onChange={(event) => setStructureType(event.target.value as StructureTypology)}
                  >
                    {TYPOLOGIES.map((top) => (
                      <option key={top.value} value={top.value}>
                        {t(`typology.${top.value}`, top.label)}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid gap-5 sm:grid-cols-2">
                  <div>
                    <label htmlFor={`${formId}-name`} className="field-label">
                      {t('upload.structureName', 'Name')}{' '}
                      <span className="text-ws-faint">{t('upload.optional', '(optional)')}</span>
                    </label>
                    <input
                      id={`${formId}-name`}
                      className="field"
                      value={structureName}
                      placeholder={t('upload.namePlaceholder', 'e.g. Agrasen ki Baoli')}
                      onChange={(event) => setStructureName(event.target.value)}
                    />
                  </div>
                  <div>
                    <label htmlFor={`${formId}-region`} className="field-label">
                      {t('upload.region', 'Region')}{' '}
                      <span className="text-ws-faint">{t('upload.optional', '(optional)')}</span>
                    </label>
                    <input
                      id={`${formId}-region`}
                      className="field"
                      list={`${formId}-regions`}
                      value={region}
                      placeholder={t('upload.regionPlaceholder', 'e.g. Delhi NCR')}
                      onChange={(event) => setRegion(event.target.value)}
                    />
                    <datalist id={`${formId}-regions`}>
                      {REGION_SUGGESTIONS.map((r) => (
                        <option key={r} value={r} />
                      ))}
                    </datalist>
                  </div>
                </div>
                <div>
                  <label htmlFor={`${formId}-notes`} className="field-label">
                    {t('upload.fieldNotes', 'Field notes')}{' '}
                    <span className="text-ws-faint">{t('upload.optional', '(optional)')}</span>
                  </label>
                  <textarea
                    id={`${formId}-notes`}
                    className="field h-28 resize-y py-2.5 leading-relaxed"
                    value={notes}
                    placeholder={t('upload.notesPlaceholder', 'Observed water level, recent repairs, access conditions…')}
                    onChange={(event) => setNotes(event.target.value)}
                  />
                </div>
              </fieldset>

              <div className="mt-7 flex flex-wrap items-center gap-x-5 gap-y-3">
                <Button
                  type="submit"
                  size="lg"
                  className="min-w-[13rem]"
                  disabled={!selected || busy || result !== null || (roiEnabled && !roi)}
                  isLoading={busy}
                >
                  {busy ? t('upload.running', 'Running…') : startLabel}
                </Button>
                {!selected && (
                  <p className="text-[0.8125rem] text-ws-muted">
                    {t('upload.addPhotoPrompt', 'Add a photograph to begin.')}
                  </p>
                )}
                {roiEnabled && !roi && selected && (
                  <p className="text-[0.8125rem] text-ws-muted">
                    {t('upload.drawRegionPrompt', 'Draw a region on the image, or switch the region option off.')}
                  </p>
                )}
              </div>
            </form>
          </section>
        </div>
      </div>

      <section ref={statusRef} aria-labelledby={`${formId}-status`} className="mt-14 scroll-mb-8">
        <div className="ws-terrace mb-7 text-ws-sandstone/80" aria-hidden="true">
          <span />
        </div>
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <h2 id={`${formId}-status`} className="font-display text-[1.75rem] font-medium leading-tight text-ws-text">
              {t('upload.status', 'Status')}
            </h2>
            <p className="text-[0.8125rem] text-ws-faint">
              {t('upload.statusDesc', 'Storing an image and analysing it are separate steps; each shows the API’s real response.')}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {stored && (
              <Button
                size="sm"
                variant="danger"
                onClick={handleDeleteStored}
                isLoading={deleting}
                disabled={busy}
                icon={<Icon name="trash" className="h-3.5 w-3.5" />}
              >
                {t('upload.deleteStored', 'Delete stored image')}
              </Button>
            )}
            {result && (
              <Button ref={openFindingsRef} onClick={handleOpenFindings} size="lg">
                {t('upload.openFindings', 'Open findings')}
                <Icon name="arrowRight" className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
        <PipelineStages stages={stages} tone="dark" orientation="horizontal" />
        {notice && (
          <p role="status" className="mt-6 text-[0.8125rem] text-ws-muted">
            {notice}
          </p>
        )}
      </section>
        </>
      )}

      <section aria-labelledby={`${formId}-limits`} className="mt-20 border-t border-[var(--ws-line-dark)] pt-10">
        <h2 id={`${formId}-limits`} className="font-display text-[1.75rem] font-medium leading-tight text-ws-text">
          {t('upload.whatPilotSees', 'What the current pilot can see')}
        </h2>
        <dl className="mt-6 grid gap-x-12 gap-y-6 text-[0.9375rem] md:grid-cols-3">
          <div>
            <dt className="font-medium text-ws-text">{t('upload.liveDetection', 'Live detection')}</dt>
            <dd className="mt-1.5 leading-relaxed text-ws-muted">
              {t(
                'upload.liveDetectionDesc',
                'Unified YOLO26n and fine-tuned Faster R-CNN damage models for crack and vegetation localization. Review boxes with engineering discretion.'
              )}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-ws-text">{t('upload.imageSpaceOnly', 'Image-space only')}</dt>
            <dd className="mt-1.5 leading-relaxed text-ws-muted">
              {t(
                'upload.imageSpaceDesc',
                'Measurements are in pixels of this photograph. Without a calibrated scale they are not physical dimensions.'
              )}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-ws-text">{t('upload.betterPhotos', 'Better photographs')}</dt>
            <dd className="mt-1.5 leading-relaxed text-ws-muted">
              {t(
                'upload.betterPhotosDesc',
                'Face the wall squarely, use even daylight, keep the surface sharp, and avoid strong shadow across joints.'
              )}
            </dd>
          </div>
        </dl>
      </section>
    </PageContainer>
  );
};

export default UploadPage;
