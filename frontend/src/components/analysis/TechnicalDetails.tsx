import React from 'react';
import { AnalysisResultContract, RootCauseItem } from '../../types';
import { Disclosure } from './Disclosure';
import { formatPercent, formatTimestamp, humanize } from '../../utils/analysis';
import { useLanguage } from '../../i18n/LanguageContext';

export interface TechnicalDetailsProps {
  result: AnalysisResultContract;
  causes: RootCauseItem[];
}

/** Pipeline provenance on demand, and every reference the planner and rule engine cited, always visible. */
export const TechnicalDetails: React.FC<TechnicalDetailsProps> = ({ result, causes }) => {
  const { t } = useLanguage();
  const vision = result.vision;
  const meta = vision.processing_metadata;

  const plannerRefs = result.restoration?.iks_guidelines?.craftsmanship_references ?? [];
  const ruleRefs = Array.from(new Set(causes.flatMap((c) => c.supporting_sources ?? []))).filter((ref) => !plannerRefs.includes(ref));

  const provenance: [string, string | null][] = [
    [t('dash.modelVersion', 'Vision model'), meta?.model_version ?? null],
    [t('dash.latency', 'Inference latency'), typeof meta?.inference_latency_ms === 'number' ? `${meta.inference_latency_ms.toFixed(0)} ms` : null],
    [
      t('dash.relevance', 'Inspection gate'),
      vision.relevance_status
        ? `${humanize(vision.relevance_status)}${typeof vision.relevance_confidence === 'number' ? ` · ${formatPercent(vision.relevance_confidence, 0)}` : ''}`
        : null,
    ],
    [t('dash.quality', 'Image quality'), vision.quality_status ? humanize(vision.quality_status) : null],
    [t('dash.dimensions', 'Image size'), `${vision.image_dimensions.width_pixels} × ${vision.image_dimensions.height_pixels} px`],
    [
      t('dash.scale', 'Physical scale'),
      vision.scale_reference?.calibrated
        ? `${vision.scale_reference.pixels_per_millimeter} px/mm`
        : t('dash.noScale', 'Not supplied — measurements are image-space only'),
    ],
    [t('dash.pipeline', 'Pipeline status'), result.metadata?.pipeline_status ? humanize(result.metadata.pipeline_status) : null],
    [t('dash.orchestrator', 'Orchestrated by'), result.metadata?.orchestrated_by ?? null],
    [t('dash.created', 'Analysed'), result.metadata?.created_at ? formatTimestamp(result.metadata.created_at) : null],
    [t('dash.contract', 'Contract version'), result.project_version ?? null],
  ];

  return (
    <div className="grid gap-10 lg:grid-cols-12">
      <div className="lg:col-span-5">
        <Disclosure
          summary={<span className="font-medium">{t('dash.provenance', 'Pipeline provenance')}</span>}
          meta={<span className="text-xs text-ink-500">{t('dash.provenanceMeta', 'Model, gate, scale')}</span>}
        >
          <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2 text-xs">
            {provenance.map(([label, value]) => (
              <React.Fragment key={label}>
                <dt className="text-ink-500">{label}</dt>
                <dd className="break-words font-mono text-ink-700">{value ?? t('dash.notAvailableShort', 'not available')}</dd>
              </React.Fragment>
            ))}
          </dl>
        </Disclosure>
        {vision.status_message && <p className="mt-4 text-xs leading-relaxed text-ink-500">{vision.status_message}</p>}
      </div>

      <div className="space-y-8 lg:col-span-7">
        {[
          { title: t('restoration.referencesCited', 'References cited by the planner'), refs: plannerRefs },
          { title: t('dash.ruleSources', 'Sources cited by the rule engine'), refs: ruleRefs },
        ]
          .filter((group) => group.refs.length > 0)
          .map((group) => (
            <div key={group.title}>
              <h3 className="text-sm font-medium text-ink-900">{group.title}</h3>
              <ol className="mt-3 divide-y divide-ink-900/10 border-y border-ink-900/10">
                {group.refs.map((ref, i) => (
                  <li key={ref} className="flex gap-4 py-2.5 text-sm leading-relaxed text-ink-700">
                    <span className="font-mono text-xs leading-6 text-ink-500 tabular-nums">{String(i + 1).padStart(2, '0')}</span>
                    <span>{ref}</span>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        {plannerRefs.length === 0 && ruleRefs.length === 0 && (
          <p className="text-sm text-ink-600">{t('dash.noReferences', 'This result cites no references.')}</p>
        )}
      </div>
    </div>
  );
};

export default TechnicalDetails;
