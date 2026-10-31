import React, { useEffect, useState } from 'react';
import { Button } from './Button';
import { Icon } from './Icon';
import { useLanguage } from '../i18n/LanguageContext';
import {
  fetchHeritageStructures,
  uploadHistoricalSurveyPdf,
  importHistoricalDefects,
} from '../services/api';
import { HeritageStructure, DocumentExtractionResult, ExtractedDefect } from '../types';

export const HistoricalPdfExtractor: React.FC = () => {
  const { t } = useLanguage();
  const [structures, setStructures] = useState<HeritageStructure[]>([]);
  const [selectedStructureId, setSelectedStructureId] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<DocumentExtractionResult | null>(null);
  const [selectedDefects, setSelectedDefects] = useState<Record<number, boolean>>({});
  const [importSuccess, setImportSuccess] = useState<string | null>(null);

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
    } catch (e) {
      console.error(e);
    }
  };

  const handleUploadPdf = async () => {
    if (!file || !selectedStructureId) return;
    setLoading(true);
    setImportSuccess(null);
    try {
      const res = await uploadHistoricalSurveyPdf(selectedStructureId, file);
      setResult(res);
      // Default all extracted defects to selected
      const initial: Record<number, boolean> = {};
      res.extracted_defects.forEach((_, idx) => {
        initial[idx] = true;
      });
      setSelectedDefects(initial);
    } catch (e: any) {
      alert(e.message || t('historical.errorPdfExtract', 'PDF extraction failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmImport = async () => {
    if (!result || !selectedStructureId) return;
    const toImport: ExtractedDefect[] = result.extracted_defects.filter(
      (_, idx) => selectedDefects[idx],
    );
    if (toImport.length === 0) {
      alert(t('historical.alertSelectDefect', 'Please select at least one defect to import.'));
      return;
    }

    setImporting(true);
    try {
      const res = await importHistoricalDefects(
        selectedStructureId,
        result.document_id,
        toImport,
      );
      setImportSuccess(
        `${t('historical.importSuccess', 'Successfully imported historical defects into permanent Defect Passports!')} (${res.imported_count})`,
      );
    } catch (e: any) {
      alert(e.message || t('historical.errorImport', 'Import failed'));
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="rounded-2xl border border-ws-border bg-ws-card p-6 shadow-xl">
      <div className="mb-6 flex flex-col gap-2 border-b border-ws-border pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <span className="font-mono text-xs uppercase tracking-wider text-ws-jade">
            {t('historical.featureBadge', 'Feature 6: Historical Dossier Migration')}
          </span>
          <h2 className="text-xl font-medium text-ws-text">{t('historical.title')}</h2>
          <p className="mt-1 text-xs text-ws-muted">{t('historical.subtitle')}</p>
        </div>
      </div>

      {/* Structure Selector */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-ws-muted">{t('historical.selectStructure', 'Select Structure')}</label>
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

        <div>
          <label className="mb-1 block text-xs font-medium text-ws-muted">
            {t('historical.uploadPrompt', 'Upload Historical PDF Report')}
          </label>
          <div className="flex items-center gap-2">
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full rounded-lg border border-ws-border bg-ws-bg px-3 py-1.5 text-xs text-ws-text file:mr-2 file:rounded file:border-0 file:bg-ws-card file:px-2 file:py-1 file:text-xs file:text-ws-text"
            />
            <Button
              variant="primary"
              size="sm"
              disabled={!file || loading}
              onClick={handleUploadPdf}
              icon={loading ? <Icon name="refresh" className="h-3.5 w-3.5 animate-spin" /> : <Icon name="upload" className="h-3.5 w-3.5" />}
            >
              {loading ? t('historical.extracting', 'Extracting...') : t('historical.extractBtn', 'Extract')}
            </Button>
          </div>
        </div>
      </div>

      {/* Extraction Results */}
      {result && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 rounded-xl border border-ws-border bg-ws-bg p-4 sm:grid-cols-4">
            <div>
              <span className="text-[11px] text-ws-faint">{t('historical.docId', 'Document ID')}</span>
              <p className="font-mono text-xs font-semibold text-ws-text">{result.document_id}</p>
            </div>
            <div>
              <span className="text-[11px] text-ws-faint">{t('historical.totalPages', 'Total Pages')}</span>
              <p className="font-mono text-xs text-ws-text">{result.total_pages}</p>
            </div>
            <div>
              <span className="text-[11px] text-ws-faint">{t('historical.surveyDate', 'Survey Date')}</span>
              <p className="font-mono text-xs text-ws-jade">
                {result.extracted_inspection_date || t('historical.undated', 'Undated')}
              </p>
            </div>
            <div>
              <span className="text-[11px] text-ws-faint">{t('historical.extractedFindingsCount', 'Extracted Findings')}</span>
              <p className="font-mono text-xs font-semibold text-laterite-300">
                {result.extracted_defects.length} {t('historical.defects', 'defects')}
              </p>
            </div>
          </div>

          {/* Defect Confirmation Table */}
          <div>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-medium text-ws-text">
                {t('historical.extractedDefects', 'Extracted Defects (Requires Conservation Architect Review)')}
              </h3>
              <span className="text-xs text-ws-faint">
                {t('historical.verified', 'Human architect validation required before permanent migration.')}
              </span>
            </div>

            <div className="overflow-x-auto rounded-xl border border-ws-border bg-ws-bg">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-ws-border text-ws-faint">
                    <th className="px-4 py-3">{t('common.confirm', 'Confirm')}</th>
                    <th className="py-3 font-medium">{t('historical.findingDesc', 'Finding Description')}</th>
                    <th className="py-3 font-medium">{t('passports.category', 'Category')}</th>
                    <th className="py-3 font-medium">{t('passports.severity', 'Severity')}</th>
                    <th className="py-3 font-mono font-medium">{t('historical.page', 'Page')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ws-border">
                  {result.extracted_defects.map((d, idx) => (
                    <tr key={idx} className="hover:bg-ws-card/50">
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={Boolean(selectedDefects[idx])}
                          onChange={(e) =>
                            setSelectedDefects((prev) => ({
                              ...prev,
                              [idx]: e.target.checked,
                            }))
                          }
                          className="h-4 w-4 rounded border-ws-border text-ws-jade focus:ring-ws-jade"
                        />
                      </td>
                      <td className="py-3 font-medium text-ws-text">{d.description}</td>
                      <td className="py-3 capitalize">
                        <span className="rounded bg-ws-card px-2 py-0.5 text-[11px] text-ws-muted">
                          {t(`defect.${d.category}`, d.category)}
                        </span>
                      </td>
                      <td className="py-3 capitalize">
                        <span
                          className={`font-mono text-[11px] ${
                            d.severity === 'severe'
                              ? 'text-rose-400'
                              : d.severity === 'moderate'
                              ? 'text-amber-300'
                              : 'text-ws-muted'
                          }`}
                        >
                          {d.severity}
                        </span>
                      </td>
                      <td className="py-3 font-mono text-ws-faint">p. {d.page_number}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {importSuccess && (
            <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300">
              <Icon name="check" className="h-4 w-4 text-emerald-400" />
              <span>{importSuccess}</span>
            </div>
          )}

          <div className="flex justify-end">
            <Button
              variant="primary"
              size="md"
              disabled={importing || result.extracted_defects.length === 0}
              onClick={handleConfirmImport}
              icon={importing ? <Icon name="refresh" className="h-4 w-4 animate-spin" /> : <Icon name="check" className="h-4 w-4" />}
            >
              {importing ? t('historical.importing', 'Importing Passports...') : t('historical.importSelected', 'Import Selected Defects into Passports')}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
