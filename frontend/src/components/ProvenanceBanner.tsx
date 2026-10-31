import React from 'react';
import { InspectionSession } from '../types';
import { Icon } from './Icon';
import { formatTimestamp, visionModelRan } from '../utils/analysis';
import { useLanguage } from '../i18n/LanguageContext';

/** States plainly whether the result is a live API response or the development sample. */
export const ProvenanceBanner: React.FC<{ session: InspectionSession }> = ({ session }) => {
  const { t } = useLanguage();
  const { result } = session;

  if (session.provenance === 'fixture') {
    return (
      <div role="note" className="flex gap-3 rounded-sm border border-ochre-500/50 bg-ochre-100 px-4 py-3.5 text-sm text-ochre-700 print:border-2">
        <Icon name="alert" className="mt-0.5 h-4 w-4 shrink-0" />
        <p>
          <strong className="font-semibold">{t('provenance.fixtureTitle', 'Development sample — not a real inspection.')}</strong>{' '}
          {t('provenance.fixtureDesc', 'These values are a fixed fixture bundled with the frontend for interface review. They were not produced by the model or the engines.')}
        </p>
      </div>
    );
  }

  const model = result.vision.processing_metadata?.model_version;
  const latency = result.vision.processing_metadata?.inference_latency_ms;

  const meta = (
    <div role="note" className="flex flex-wrap items-center gap-x-6 gap-y-1 border-y border-ink-900/10 py-3 font-mono text-[0.6875rem] uppercase tracking-[0.06em] text-ink-600">
      <span className="flex items-center gap-2 text-jade-700">
        <span className="h-1.5 w-1.5 rounded-full bg-jade-500" aria-hidden="true" />
        {t('provenance.apiReturned', 'Returned by the JalDrishti API')}
      </span>
      <span>{formatTimestamp(result.metadata.created_at)}</span>
      {model && <span>{t('provenance.model', 'Model')} {model}</span>}
      {typeof latency === 'number' && <span className="tabular-nums">{t('provenance.vision', 'Vision')} {latency.toFixed(0)} ms</span>}
      <span>{t('provenance.pipeline', 'Pipeline')} {result.metadata.pipeline_status}</span>
      {session.image ? <span className="normal-case">{t('pipeline.imageId', 'Image')} {session.image.image_id}</span> : <span>{t('provenance.imageNotStored', 'Image not stored')}</span>}
    </div>
  );

  if (result.vision.relevance_status === 'irrelevant') {
    return (
      <div className="space-y-3">
        <div role="alert" className="flex gap-3 rounded-sm border border-danger-500/50 bg-danger-100 px-4 py-3.5 text-sm text-danger-700 print:border-2">
          <Icon name="alert" className="mt-0.5 h-4 w-4 shrink-0 text-danger-600" />
          <div>
            <strong className="font-semibold">
              {t('provenance.gateRejectedTitle', 'Image Inspection Gate: Defect Detection Withheld')}
            </strong>
            <p className="mt-1 leading-relaxed text-danger-800">
              {result.vision.rejection_reason ||
                t(
                  'provenance.gateRejectedDesc',
                  'This photograph was rejected by the MobileNetV3 Heritage Relevance Inspection Gate as non-heritage subject matter. Automated defect localization was withheld to prevent generating false damage records.'
                )}
            </p>
          </div>
        </div>
        {meta}
      </div>
    );
  }

  if (result.vision.relevance_status === 'uncertain') {
    return (
      <div className="space-y-3">
        <div role="alert" className="flex gap-3 rounded-sm border border-ochre-500/50 bg-ochre-100 px-4 py-3.5 text-sm text-ochre-700 print:border-2">
          <Icon name="alert" className="mt-0.5 h-4 w-4 shrink-0 text-ochre-600" />
          <div>
            <strong className="font-semibold">
              {t('provenance.gateUncertainTitle', 'Image Inspection Gate: Needs Manual Review')}
            </strong>
            <p className="mt-1 leading-relaxed text-ochre-800">
              {result.vision.rejection_reason ||
                t(
                  'provenance.gateUncertainDesc',
                  'The image could not be confidently verified as an authentic heritage water structure. Queued for manual expert review.'
                )}
            </p>
          </div>
        </div>
        {meta}
      </div>
    );
  }

  if (visionModelRan(result)) return meta;

  return (
    <div className="space-y-3">
      <div role="alert" className="flex gap-3 rounded-sm border border-ochre-500/50 bg-ochre-100 px-4 py-3.5 text-sm text-ochre-700 print:border-2">
        <Icon name="alert" className="mt-0.5 h-4 w-4 shrink-0" />
        <p>
          <strong className="font-semibold">{t('provenance.noModelTitle', 'The vision model did not run for this analysis.')}</strong>{' '}
          {t('provenance.noModelDesc', 'The API did not report a loaded detection model, so the regions below come from precomputed demo results or fallback logic.')}
        </p>
      </div>
      {meta}
    </div>
  );
};

export default ProvenanceBanner;
