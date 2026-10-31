import React, { useEffect, useState } from 'react';
import { Button } from './Button';
import { Icon } from './Icon';
import { useLanguage } from '../i18n/LanguageContext';
import {
  fetchHeritageStructures,
  fetchHeritageStructureDetails,
  submitRepeatInspection,
} from '../services/api';
import { HeritageStructure, DefectPassport } from '../types';

export const DefectPassportRegistry: React.FC = () => {
  const { t } = useLanguage();
  const [structures, setStructures] = useState<HeritageStructure[]>([]);
  const [selectedStructureId, setSelectedStructureId] = useState<string>('');
  const [passports, setPassports] = useState<DefectPassport[]>([]);
  const [loading, setLoading] = useState(false);
  const [repeatFiles, setRepeatFiles] = useState<File[]>([]);
  const [repeatPreviews, setRepeatPreviews] = useState<string[]>([]);
  const [repeatLoading, setRepeatLoading] = useState(false);
  const [repeatResult, setRepeatResult] = useState<any>(null);
  const [showRepeatModal, setShowRepeatModal] = useState(false);

  useEffect(() => {
    loadStructures();
  }, []);

  useEffect(() => {
    if (selectedStructureId) {
      loadStructurePassports(selectedStructureId);
    }
  }, [selectedStructureId]);

  const loadStructures = async () => {
    try {
      const data = await fetchHeritageStructures();
      setStructures(data);
      if (data.length > 0 && !selectedStructureId) {
        setSelectedStructureId(data[0].structure_id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadStructurePassports = async (id: string) => {
    setLoading(true);
    try {
      const data = await fetchHeritageStructureDetails(id);
      setPassports(data.passports || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleRepeatFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const newFiles = Array.from(e.target.files);
    setRepeatFiles((prev) => [...prev, ...newFiles]);
    const urls = newFiles.map((f) => URL.createObjectURL(f));
    setRepeatPreviews((prev) => [...prev, ...urls]);
  };

  const handleRunRepeatInspection = async () => {
    if (repeatFiles.length === 0 || !selectedStructureId) return;
    setRepeatLoading(true);
    try {
      const res = await submitRepeatInspection(selectedStructureId, repeatFiles);
      setRepeatResult(res);
      loadStructurePassports(selectedStructureId);
    } catch (e: any) {
      alert(e.message || t('passports.errorRepeat', 'Repeat inspection failed'));
    } finally {
      setRepeatLoading(false);
    }
  };

  return (
    <div className="rounded-2xl border border-ws-border bg-ws-card p-6 shadow-xl">
      <div className="mb-6 flex flex-col gap-2 border-b border-ws-border pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <span className="font-mono text-xs uppercase tracking-wider text-ws-jade">
            {t('passports.featureBadge', 'Feature 5: Persistent Lifecycle Tracking')}
          </span>
          <h2 className="text-xl font-medium text-ws-text">{t('passports.title')}</h2>
          <p className="mt-1 text-xs text-ws-muted">{t('passports.subtitle')}</p>
        </div>

        <Button
          variant="primary"
          size="sm"
          onClick={() => setShowRepeatModal(true)}
          icon={<Icon name="refresh" className="h-3.5 w-3.5" />}
        >
          {t('passports.repeatInspection')}
        </Button>
      </div>

      {/* Structure Selector */}
      <div className="mb-6 max-w-sm">
        <label className="mb-1 block text-xs font-medium text-ws-muted">{t('passports.selectStructure', 'Select Structure')}</label>
        <select
          value={selectedStructureId}
          onChange={(e) => setSelectedStructureId(e.target.value)}
          className="w-full rounded-lg border border-ws-border bg-ws-bg px-3 py-2 text-sm text-ws-text focus:border-ws-jade focus:outline-none"
        >
          {structures.map((s) => (
            <option key={s.structure_id} value={s.structure_id}>
              {s.name} ({s.location || s.region})
            </option>
          ))}
        </select>
      </div>

      {/* Passports List */}
      {loading ? (
        <div className="py-8 text-center text-xs text-ws-faint">{t('passports.loading', 'Loading defect passports...')}</div>
      ) : passports.length === 0 ? (
        <div className="rounded-xl border border-dashed border-ws-border p-8 text-center">
          <p className="text-sm text-ws-muted">{t('passports.empty', 'No Defect Passports registered for this structure yet.')}</p>
          <p className="mt-1 text-xs text-ws-faint">
            {t('passports.emptyHint', 'Run a 3-photo baseline inspection to automatically register verified cracks and vegetation.')}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-ws-border text-ws-faint">
                <th className="pb-3 font-mono font-medium">{t('passports.id')}</th>
                <th className="pb-3 font-medium">{t('passports.category')}</th>
                <th className="pb-3 font-medium">{t('passports.severity')}</th>
                <th className="pb-3 font-medium">{t('passports.status')}</th>
                <th className="pb-3 font-mono font-medium">{t('passports.confidence')}</th>
                <th className="pb-3 font-medium">{t('passports.firstDetected')}</th>
                <th className="pb-3 font-medium">{t('passports.verification', 'Verification')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ws-border">
              {passports.map((p) => (
                <tr key={p.defect_id} className="hover:bg-ws-bg/40">
                  <td className="py-3 font-mono font-semibold text-ws-jade">{p.defect_id}</td>
                  <td className="py-3 font-medium capitalize text-ws-text">
                    <span
                      className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] ${
                        p.defect_category === 'crack'
                          ? 'bg-laterite-500/10 text-laterite-300'
                          : 'bg-emerald-500/10 text-emerald-300'
                      }`}
                    >
                      {t(`defect.${p.defect_category}`, p.defect_category)}
                    </span>
                  </td>
                  <td className="py-3 capitalize text-ws-text">
                    <span
                      className={`font-mono text-[11px] ${
                        p.severity === 'severe'
                          ? 'text-rose-400'
                          : p.severity === 'moderate'
                          ? 'text-amber-300'
                          : 'text-ws-muted'
                      }`}
                    >
                      {p.severity}
                    </span>
                  </td>
                  <td className="py-3">
                    <span className="rounded-full border border-ws-border bg-ws-bg px-2 py-0.5 font-mono text-[10px] uppercase text-ws-text">
                      {p.status}
                    </span>
                  </td>
                  <td className="py-3 font-mono text-ws-muted">
                    {(p.confidence * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 font-mono text-ws-faint">
                    {p.first_detected_date ? p.first_detected_date.split('T')[0] : '—'}
                  </td>
                  <td className="py-3 font-mono text-[10px] text-ws-faint">
                    {p.verification_status}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Repeat Inspection Modal */}
      {showRepeatModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
          <div className="relative max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl border border-ws-border bg-ws-card p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between border-b border-ws-border pb-3">
              <h3 className="text-base font-medium text-ws-text">
                {t('passports.repeatTitle', 'Repeat Inspection & Defect Evolution')}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setShowRepeatModal(false);
                  setRepeatResult(null);
                }}
                className="rounded p-1 text-ws-muted hover:text-ws-text"
              >
                <Icon name="close" className="h-4 w-4" />
              </button>
            </div>

            <p className="mb-4 text-xs text-ws-muted">
              {t(
                'passports.uploadRepeatViews',
                'Upload a recent photograph from a follow-up survey. The AI will match detected cracks and vegetation against existing Defect Passports to track growth, stability, or repair.'
              )}
            </p>

            <label className="mb-4 flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-ws-border bg-ws-bg/50 p-6 text-xs text-ws-muted transition hover:border-ws-jade">
              <Icon name="upload" className="h-5 w-5 text-ws-jade" />
              <span>
                {t('passports.repeatPrompt', 'Select follow-up photographs')} ({repeatFiles.length})
              </span>
              <input
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp"
                onChange={handleRepeatFileChange}
                className="sr-only"
              />
            </label>

            {repeatPreviews.length > 0 && (
              <div className="mb-4 grid grid-cols-3 gap-2">
                {repeatPreviews.map((url, i) => (
                  <img
                    key={i}
                    src={url}
                    alt={`Repeat photo ${i}`}
                    className="aspect-video w-full rounded-lg object-cover"
                  />
                ))}
              </div>
            )}

            {repeatResult && (
              <div className="mb-4 rounded-xl border border-ws-jade/30 bg-ws-jade/5 p-4 text-xs">
                <h4 className="font-medium text-ws-text">{t('passports.repeatSurveyResult', 'Repeat Survey Result')}</h4>
                <div className="mt-2 space-y-1 font-mono text-ws-faint">
                  <p>{t('passports.matchedExisting', 'Matched Existing Passports')}: {repeatResult.summary.matched_defects}</p>
                  <p>{t('passports.newPassports', 'New Defect Passports')}: {repeatResult.summary.new_defects}</p>
                  <p>{t('passports.totalCracksTracked', 'Total Cracks Tracked')}: {repeatResult.summary.total_cracks}</p>
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setShowRepeatModal(false);
                  setRepeatResult(null);
                }}
              >
                {t('common.close', 'Close')}
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={repeatFiles.length === 0 || repeatLoading}
                onClick={handleRunRepeatInspection}
                icon={repeatLoading ? <Icon name="refresh" className="h-3.5 w-3.5 animate-spin" /> : undefined}
              >
                {repeatLoading ? t('passports.matching', 'Matching Passports...') : t('passports.runRepeat', 'Run Repeat Analysis & Match Passports')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

