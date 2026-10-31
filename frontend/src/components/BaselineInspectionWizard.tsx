import React, { useEffect, useState } from 'react';
import { Button } from './Button';
import { Icon } from './Icon';
import { useLanguage } from '../i18n/LanguageContext';
import {
  fetchHeritageStructures,
  createHeritageStructure,
  submitBaselineInspection,
  downloadInspectionPdf,
} from '../services/api';
import { HeritageStructure, BaselineInspectionResult } from '../types';

export const BaselineInspectionWizard: React.FC<{
  onInspectComplete?: (result: any) => void;
}> = ({ onInspectComplete }) => {
  const { t, language } = useLanguage();
  const [structures, setStructures] = useState<HeritageStructure[]>([]);
  const [selectedStructureId, setSelectedStructureId] = useState<string>('');
  const [showNewStructureModal, setShowNewStructureModal] = useState(false);

  // New structure form
  const [newName, setNewName] = useState('');
  const [newTypology, setNewTypology] = useState('baoli');
  const [newLocation, setNewLocation] = useState('');
  const [newRegion, setNewRegion] = useState('Northern India');

  // Photo uploads (Min 3 required)
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [baselineResult, setBaselineResult] = useState<BaselineInspectionResult | null>(null);

  useEffect(() => {
    loadStructures();
  }, []);

  const loadStructures = async () => {
    try {
      const data = await fetchHeritageStructures();
      setStructures(data);
      if (data.length > 0 && !selectedStructureId) {
        setSelectedStructureId(data[0].structure_id);
      }
    } catch (e: any) {
      console.error(e);
    }
  };

  const handleCreateStructure = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      const created = await createHeritageStructure({
        name: newName.trim(),
        typology: newTypology,
        location: newLocation.trim(),
        region: newRegion.trim(),
      });
      setStructures((prev) => [created, ...prev]);
      setSelectedStructureId(created.structure_id);
      setShowNewStructureModal(false);
      setNewName('');
      setNewLocation('');
    } catch (err: any) {
      setError(err.message || t('baseline.errorRegister', 'Failed to register structure'));
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const newFiles = Array.from(e.target.files);
    const combined = [...files, ...newFiles];
    setFiles(combined);

    const newPreviews = newFiles.map((file) => URL.createObjectURL(file));
    setPreviews((prev) => [...prev, ...newPreviews]);
    setError(null);
  };

  const handleRemovePhoto = (index: number) => {
    URL.revokeObjectURL(previews[index]);
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const handleRunBaseline = async () => {
    if (files.length < 3) {
      setError(t('baseline.insufficientPhotos'));
      return;
    }
    if (!selectedStructureId) {
      setError(t('baseline.errorSelectStructure', 'Please select or register a heritage structure first.'));
      return;
    }

    setLoading(true);
    setError(null);
    setBaselineResult(null);

    try {
      const res = await submitBaselineInspection(selectedStructureId, files);
      setBaselineResult(res);
      if (onInspectComplete) {
        onInspectComplete(res);
      }
      loadStructures();
    } catch (err: any) {
      setError(err.message || t('baseline.errorFailed', 'Baseline inspection failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-2xl border border-ws-border bg-ws-card p-6 shadow-xl">
      <div className="mb-6 flex flex-col gap-2 border-b border-ws-border pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <span className="font-mono text-xs uppercase tracking-wider text-ws-jade">
            {t('baseline.mandatoryGate', 'Feature 2 & 3: Mandatory Baseline Gate')}
          </span>
          <h2 className="text-xl font-medium text-ws-text">{t('baseline.title')}</h2>
          <p className="mt-1 text-xs text-ws-muted">{t('baseline.subtitle')}</p>
        </div>

        <button
          type="button"
          onClick={() => setShowNewStructureModal(true)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-ws-border bg-ws-bg px-3 py-1.5 text-xs text-ws-text transition hover:border-ws-jade-light/40"
        >
          <Icon name="plus" className="h-3.5 w-3.5 text-ws-jade" />
          {t('baseline.createNew')}
        </button>
      </div>

      {/* Structure Selector */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-ws-muted">
            {t('baseline.step1')}
          </label>
          <select
            value={selectedStructureId}
            onChange={(e) => setSelectedStructureId(e.target.value)}
            className="w-full rounded-lg border border-ws-border bg-ws-bg px-3 py-2 text-sm text-ws-text focus:border-ws-jade focus:outline-none"
          >
            {structures.map((s) => (
              <option key={s.structure_id} value={s.structure_id}>
                {s.name} ({t(`typology.${s.typology}`, s.typology)}) —{' '}
                {s.baseline_completed ? t('baseline.verifiedBadge', '✓ Baseline Verified') : t('baseline.pendingBadge', 'Pending Baseline')}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-end">
          <label className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-ws-border bg-ws-bg/50 px-4 py-2 text-xs font-medium text-ws-text transition hover:border-ws-jade">
            <Icon name="upload" className="h-4 w-4 text-ws-jade" />
            <span>
              {t('baseline.addPhotosBtn', 'Add Photographs')} ({files.length} {t('baseline.selectedMin3', 'selected, min 3')})
            </span>
            <input
              type="file"
              multiple
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFileChange}
              className="sr-only"
            />
          </label>
        </div>
      </div>

      {/* Photo Grid Preview */}
      {files.length > 0 && (
        <div className="mb-6">
          <div className="mb-2 flex items-center justify-between text-xs text-ws-faint">
            <span>
              {t('baseline.uploadedViews', 'Uploaded Views')} ({files.length})
            </span>
            {files.length < 3 && (
              <span className="font-mono text-laterite-300">
                ⚠️ {t('baseline.needMorePhotos', 'Need more photo(s) to satisfy baseline threshold')} ({3 - files.length})
              </span>
            )}
            {files.length >= 3 && (
              <span className="font-mono text-ws-jade">
                {t('baseline.photosSatisfied', '✓ Minimum 3 photos threshold satisfied')}
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
            {files.map((file, idx) => (
              <div
                key={idx}
                className="group relative flex flex-col overflow-hidden rounded-xl border border-ws-border bg-ws-bg"
              >
                <div className="relative aspect-video w-full overflow-hidden bg-black/40">
                  <img
                    src={previews[idx]}
                    alt={file.name}
                    className="h-full w-full object-cover"
                  />
                  <button
                    type="button"
                    onClick={() => handleRemovePhoto(idx)}
                    className="absolute right-1.5 top-1.5 rounded-full bg-black/70 p-1 text-white opacity-0 transition group-hover:opacity-100 hover:bg-rose-600"
                    title={t('baseline.removePhoto', 'Remove photograph')}
                  >
                    <Icon name="close" className="h-3.5 w-3.5" />
                  </button>
                  <span className="absolute bottom-1 left-1.5 rounded bg-black/60 px-1.5 py-0.5 font-mono text-[10px] text-white">
                    {t('baseline.view', 'View')} #{idx + 1}
                  </span>
                </div>
                <div className="p-2 text-[11px]">
                  <p className="truncate font-medium text-ws-text">{file.name}</p>
                  <p className="font-mono text-[10px] text-ws-faint">
                    {(file.size / 1024).toFixed(0)} KB
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-5 flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
          <Icon name="alert" className="h-4 w-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Action Button */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <span className="text-xs text-ws-faint">
          {t('baseline.gateNotice', 'Every photo is independently routed through Image Quality & Relevance Gates.')}
        </span>

        <Button
          variant="primary"
          size="md"
          disabled={files.length < 3 || loading || !selectedStructureId}
          onClick={handleRunBaseline}
          icon={loading ? <Icon name="refresh" className="h-4 w-4 animate-spin" /> : <Icon name="upload" className="h-4 w-4" />}
        >
          {loading ? t('baseline.analyzingPhotos', 'Analyzing Photographs...') : t('baseline.runInspection')}
        </Button>
      </div>

      {/* Baseline Result View */}
      {baselineResult && (
        <div
          className={`mt-8 rounded-xl border p-5 ${
            baselineResult.baseline_completed
              ? 'border-ws-jade/30 bg-ws-jade/5'
              : 'border-laterite-400/40 bg-laterite-400/5'
          }`}
        >
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <span
                className={`font-mono text-xs uppercase tracking-wider ${
                  baselineResult.baseline_completed ? 'text-ws-jade' : 'text-laterite-300'
                }`}
              >
                {baselineResult.baseline_completed
                  ? `${t('baseline.dossier', 'Baseline Dossier')}: ${baselineResult.inspection_id}`
                  : `${t('baseline.dossierIncomplete', 'Baseline Incomplete')}: ${baselineResult.inspection_id}`}
              </span>
              <h3
                className={`text-base font-medium ${
                  baselineResult.baseline_completed ? 'text-ws-text' : 'text-laterite-200'
                }`}
              >
                {baselineResult.baseline_completed
                  ? `${t('baseline.completedSuccess', 'Baseline inspection completed successfully with verified heritage photos.')} (${baselineResult.summary.valid_images} / ${baselineResult.summary.total_images})`
                  : `${t('baseline.incompleteInsufficient', 'Baseline inspection could not be finalized: insufficient valid heritage photos passed quality and relevance checks.')} (${baselineResult.summary.valid_images} / ${baselineResult.summary.total_images} ${t('baseline.validCountLabel', 'valid')})`}
              </h3>
            </div>

            {baselineResult.baseline_completed && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => downloadInspectionPdf(baselineResult.inspection_id, language)}
                icon={<Icon name="download" className="h-3.5 w-3.5" />}
              >
                {t('pdf.download')}
              </Button>
            )}
          </div>

          {!baselineResult.baseline_completed && (
            <div className="mb-4 flex items-start gap-2.5 rounded-lg border border-laterite-400/30 bg-laterite-500/10 p-3 text-xs text-laterite-200">
              <Icon name="alert" className="mt-0.5 h-4 w-4 shrink-0 text-laterite-400" />
              <div>
                <p className="font-medium text-laterite-100">
                  {t('baseline.thresholdFailedTitle', 'Heritage Verification Gate Rejected Non-Heritage Content')}
                </p>
                <p className="mt-0.5 text-ws-muted">
                  {t(
                    'baseline.thresholdFailedDesc',
                    'Photographs of human selfies, portraits, and indoor domestic scenes are rejected to prevent false defect registration. Please upload at least 3 genuine photographs of a baoli, stepwell, or heritage masonry structure.'
                  )}
                </p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-lg border border-ws-border bg-ws-card p-3">
              <span className="text-xs text-ws-faint">{t('baseline.totalPhotos', 'Total Photographs')}</span>
              <p className="mt-1 font-mono text-lg font-semibold text-ws-text">
                {baselineResult.summary.total_images}
              </p>
            </div>
            <div className="rounded-lg border border-ws-border bg-ws-card p-3">
              <span className="text-xs text-ws-faint">{t('baseline.validViews', 'Valid Heritage Views')}</span>
              <p
                className={`mt-1 font-mono text-lg font-semibold ${
                  baselineResult.summary.valid_images >= 3 ? 'text-ws-jade' : 'text-laterite-300'
                }`}
              >
                {baselineResult.summary.valid_images}
              </p>
            </div>
            <div className="rounded-lg border border-ws-border bg-ws-card p-3">
              <span className="text-xs text-ws-faint">{t('baseline.totalCracks', 'Total Cracks Detected')}</span>
              <p className="mt-1 font-mono text-lg font-semibold text-laterite-300">
                {baselineResult.summary.total_cracks}
              </p>
            </div>
            <div className="rounded-lg border border-ws-border bg-ws-card p-3">
              <span className="text-xs text-ws-faint">{t('baseline.passportsRegistered', 'Defect Passports Registered')}</span>
              <p className="mt-1 font-mono text-lg font-semibold text-ws-jade">
                {baselineResult.defects_registered}
              </p>
            </div>
          </div>

          {/* Individual Photo Breakdown */}
          <div className="mt-5 space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-ws-muted">
              {t('baseline.independentBreakdown', 'Independent View Breakdown')}
            </h4>
            <div className="space-y-2">
              {baselineResult.images.map((img, i) => (
                <div
                  key={i}
                  className="flex flex-col gap-2 rounded-lg border border-ws-border bg-ws-card px-4 py-3 text-xs sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-ws-faint">#{i + 1}</span>
                    <span className="font-medium text-ws-text">{img.original_filename}</span>
                    <span
                      className={`rounded px-2 py-0.5 font-mono text-[10px] ${
                        img.inspection_status === 'accepted'
                          ? 'bg-ws-jade/10 text-ws-jade'
                          : img.inspection_status === 'uncertain'
                          ? 'bg-amber-500/15 text-amber-300'
                          : 'bg-rose-500/15 text-rose-300'
                      }`}
                    >
                      {img.inspection_status === 'accepted'
                        ? t('baseline.gateAccepted', 'Gate Accepted')
                        : img.inspection_status === 'uncertain'
                        ? t('baseline.gateUncertain', 'Needs Manual Review')
                        : t('baseline.gateRejected', 'Gate Rejected')}
                    </span>
                  </div>
                  <div className="text-xs">
                    {img.inspection_status === 'accepted' ? (
                      <span className="text-ws-jade">{t('baseline.verified', 'Cracks & Vegetation verified')}</span>
                    ) : img.inspection_status === 'uncertain' ? (
                      <span className="text-amber-300/90 leading-relaxed">
                        {img.rejection_reason || t('baseline.uncertainReason', 'Intermediate confidence. Queued for expert inspection review.')}
                      </span>
                    ) : (
                      <span className="text-rose-300/90 leading-relaxed">
                        {img.rejection_reason || t('baseline.gateRejectedDesc', 'Image rejected by heritage relevance gate.')}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Modal to Register New Structure */}
      {showNewStructureModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-md rounded-2xl border border-ws-border bg-ws-card p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between border-b border-ws-border pb-3">
              <h3 className="text-base font-medium text-ws-text">{t('baseline.registerModalTitle', 'Register Heritage Structure')}</h3>
              <button
                type="button"
                onClick={() => setShowNewStructureModal(false)}
                className="rounded p-1 text-ws-muted hover:text-ws-text"
              >
                <Icon name="close" className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateStructure} className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-ws-muted">
                  {t('baseline.structureName', 'Structure Name')} *
                </label>
                <input
                  type="text"
                  required
                  placeholder={t('baseline.namePlaceholder', 'e.g. Chand Baori, Abhaneri')}
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full rounded-lg border border-ws-border bg-ws-bg px-3 py-2 text-sm text-ws-text focus:border-ws-jade focus:outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-ws-muted">{t('baseline.typology', 'Typology')}</label>
                <select
                  value={newTypology}
                  onChange={(e) => setNewTypology(e.target.value)}
                  className="w-full rounded-lg border border-ws-border bg-ws-bg px-3 py-2 text-sm text-ws-text focus:border-ws-jade focus:outline-none"
                >
                  <option value="baoli">{t('typology.baoli', 'Baoli — Stepwell')}</option>
                  <option value="bawari">{t('typology.bawari', 'Bawari — Stepped Reservoir')}</option>
                  <option value="vav">{t('typology.vav', 'Vav — Gujarati Stepwell')}</option>
                  <option value="kund">{t('typology.kund', 'Kund — Stepped Tank')}</option>
                  <option value="tank">{t('typology.tank', 'Tank / Hauz')}</option>
                  <option value="heritage_masonry">{t('typology.heritage_masonry', 'Heritage Masonry Wall')}</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-ws-muted">
                  {t('baseline.location', 'City / Location')}
                </label>
                <input
                  type="text"
                  placeholder={t('baseline.locationPlaceholder', 'e.g. Dausa District, Rajasthan')}
                  value={newLocation}
                  onChange={(e) => setNewLocation(e.target.value)}
                  className="w-full rounded-lg border border-ws-border bg-ws-bg px-3 py-2 text-sm text-ws-text focus:border-ws-jade focus:outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-ws-muted">
                  {t('baseline.region', 'Geographical Region')}
                </label>
                <input
                  type="text"
                  placeholder={t('baseline.regionPlaceholder', 'e.g. Northern India, Rajasthan')}
                  value={newRegion}
                  onChange={(e) => setNewRegion(e.target.value)}
                  className="w-full rounded-lg border border-ws-border bg-ws-bg px-3 py-2 text-sm text-ws-text focus:border-ws-jade focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowNewStructureModal(false)}
                >
                  {t('baseline.cancel', 'Cancel')}
                </Button>
                <Button type="submit" variant="primary" size="sm">
                  {t('baseline.submitRegister', 'Register Structure')}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
