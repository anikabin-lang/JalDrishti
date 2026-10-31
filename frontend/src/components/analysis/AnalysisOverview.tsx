import React from 'react';
import { AnalysisResultContract, MetricScore } from '../../types';
import { StatusBadge } from '../StatusBadge';
import { Meter, scaleFraction } from './Meter';
import { EXTENT_BADGE, isIncompatible, rankDetections, rankMaterials } from './presentation';
import { formatPercent, humanize, readMetric } from '../../utils/analysis';
import { useLanguage } from '../../i18n/LanguageContext';

export interface AnalysisOverviewProps {
  result: AnalysisResultContract;
  onJump: (sectionId: string) => void;
  className?: string;
}

const Indicator: React.FC<{ label: string; children: React.ReactNode; note: React.ReactNode }> = ({ label, children, note }) => (
  <div className="flex min-w-0 flex-col gap-3 py-4 lg:border-l lg:border-ink-900/10 lg:px-6 lg:py-0 lg:first:border-l-0 lg:first:pl-0">
    <p className="font-mono text-[0.6875rem] uppercase tracking-[0.12em] text-ink-500">{label}</p>
    {children}
    <p className="text-xs leading-relaxed text-ink-600">{note}</p>
  </div>
);

const ScoreIndicator: React.FC<{ label: string; metric: MetricScore | null; note: string; unavailable: string }> = ({
  label,
  metric,
  note,
  unavailable,
}) => (
  <Indicator label={label} note={metric ? note : unavailable}>
    {metric ? (
      <>
        <p className="text-[2rem] font-light leading-none text-ink-950 sm:text-[2.5rem]">
          {metric.value.toFixed(0)}
          <span className="ml-1 text-base font-normal text-ink-500">/ {metric.scale_max}</span>
        </p>
        <Meter fraction={scaleFraction(metric.value, metric.scale_min, metric.scale_max)} />
      </>
    ) : (
      <p className="text-lg text-ink-500">—</p>
    )}
  </Indicator>
);

/**
 * The first screen of the dashboard: the few numbers that describe the
 * observed condition, and one line each for the leading finding, the
 * top-ranked material and the planner's strategy, each linking to its section.
 */
export const AnalysisOverview: React.FC<AnalysisOverviewProps> = ({ result, onJump, className = '' }) => {
  const { t } = useLanguage();
  const detections = result.vision.detections;
  const gateRejected = result.vision.relevance_status === 'irrelevant';
  const visual = readMetric(result.visual_condition);
  const water = readMetric(result.water_functionality);

  const lead = detections.length > 0 ? detections[rankDetections(detections)[0]] : null;
  const classes = new Set(detections.map((d) => d.class_name)).size;
  const peakConfidence = detections.reduce((max, d) => Math.max(max, d.confidence), 0);

  const materials = rankMaterials(result.material?.candidate_interventions ?? []);
  const topMaterial = materials.find((m) => !isIncompatible(m)) ?? null;
  const avoided = materials.filter(isIncompatible);
  const strategy = result.restoration?.restoration_strategy;

  const takeaways: { key: string; label: string; section: string; body: React.ReactNode }[] = [
    {
      key: 'finding',
      label: t('dash.leadFinding', 'Most extensive finding'),
      section: 'findings',
      body: lead ? (
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <span className="text-ink-950">{t('defect.' + lead.class_name, humanize(lead.class_name))}</span>
          {lead.relative_severity && (
            <StatusBadge
              label={`${t('severity.' + lead.relative_severity, humanize(lead.relative_severity))} ${t('dash.extent', 'extent')}`}
              variant={EXTENT_BADGE[lead.relative_severity] ?? 'neutral'}
            />
          )}
        </span>
      ) : (
        <span className="text-ink-600">
          {gateRejected ? t('dash.analysisSuspended', 'Analysis suspended by the inspection gate') : t('dash.noDetections', 'No defect regions returned')}
        </span>
      ),
    },
    {
      key: 'material',
      label: t('dash.topMaterial', 'Top-ranked repair material'),
      section: 'materials',
      body: topMaterial ? (
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <span className="text-ink-950">{humanize(topMaterial.intervention_material)}</span>
          <span className="font-mono text-xs text-ink-600 tabular-nums">{topMaterial.compatibility_score.toFixed(1)} / 100</span>
          {avoided.length > 0 && (
            <span className="text-xs text-ink-600">
              · {t('dash.avoid', 'Avoid')} {avoided.map((m) => humanize(m.intervention_material)).join(', ')}
            </span>
          )}
        </span>
      ) : (
        <span className="text-ink-600">{t('dash.noMaterials', 'No compatible material returned')}</span>
      ),
    },
    {
      key: 'strategy',
      label: t('dash.strategy', 'Restoration strategy'),
      section: 'restoration',
      body: strategy ? (
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <span className="text-ink-950">{t('strategy.' + strategy, humanize(strategy))}</span>
          <span className="text-xs text-ink-600">
            {result.restoration.prioritized_actions?.length ?? 0} {t('dash.phasedActions', 'phased actions')}
          </span>
        </span>
      ) : (
        <span className="text-ink-600">{t('dash.noStrategy', 'No strategy returned')}</span>
      ),
    },
  ];

  return (
    <section id="overview" aria-labelledby="overview-title" className={className}>
      <header className="mb-8 max-w-prose">
        <p className="font-mono text-[0.6875rem] uppercase tracking-[0.18em] text-ink-500">{t('dash.overviewEyebrow', 'At a glance')}</p>
        <h2 id="overview-title" className="mt-2 font-display text-[2rem] font-medium leading-tight text-ink-950">
          {t('dash.overviewTitle', 'Structural assessment overview')}
        </h2>
        <p className="mt-2 text-[0.9375rem] leading-relaxed text-ink-600">
          {t(
            'dash.overviewDesc',
            'A consolidated view of detected conditions, structural concerns, and recommended conservation priorities.'
          )}
        </p>
      </header>

      <div className="grid grid-cols-2 gap-x-6 gap-y-2 border-y border-ink-900/15 py-2 sm:gap-x-8 lg:grid-cols-4 lg:gap-x-0 lg:py-6">
        <ScoreIndicator
          label={t('dash.visualCondition', 'Visual condition')}
          metric={visual}
          note={t('dash.visualConditionNote', 'Higher indicates better observed surface condition.')}
          unavailable={t('dash.notAvailable', 'Not available in this result.')}
        />
        <ScoreIndicator
          label={t('dash.waterFunctionality', 'Water functionality')}
          metric={water}
          note={t('dash.waterFunctionalityNote', 'Higher indicates better observed hydrological function.')}
          unavailable={t('dash.notAvailable', 'Not available in this result.')}
        />
        <Indicator
          label={t('dash.detectedClasses', 'Detected conditions')}
          note={
            gateRejected
              ? t('dash.gateNote', 'The image was not accepted as a heritage structure.')
              : t('dash.detectedNote', 'Distinct defect classes found in this photograph.')
          }
        >
          <p className="text-[2rem] font-light leading-none text-ink-950 sm:text-[2.5rem]">{gateRejected ? '—' : classes}</p>
          {!gateRejected && classes > 0 && (
            <div className="flex gap-1" aria-hidden="true">
              {rankDetections(detections).map((i) => detections[i]).map((d, i) => (
                <span
                  key={i}
                  className={`h-1 flex-1 rounded-full ${d.relative_severity === 'severe' ? 'bg-danger-500' : d.relative_severity === 'moderate' ? 'bg-ochre-500' : 'bg-jade-400'}`}
                />
              ))}
            </div>
          )}
        </Indicator>
        <Indicator
          label={t('dash.peakConfidence', 'Peak detection confidence')}
          note={t('dash.confidenceNote', 'Model certainty that a region belongs to its class — not how serious it is.')}
        >
          <p className="text-[2rem] font-light leading-none text-ink-950 sm:text-[2.5rem]">{detections.length ? formatPercent(peakConfidence, 0) : '—'}</p>
          {detections.length > 0 && <Meter fraction={peakConfidence} tone="bg-ink-600" />}
        </Indicator>
      </div>

      <ul className="mt-6 grid gap-px overflow-hidden rounded-md border border-ink-900/10 bg-ink-900/10 md:grid-cols-3">
        {takeaways.map((item) => (
          <li key={item.key} className="bg-stone-50">
            <a
              href={`#${item.section}`}
              onClick={(event) => {
                event.preventDefault();
                onJump(item.section);
              }}
              className="group flex h-full flex-col gap-2 p-4 text-sm transition-colors duration-fast hover:bg-stone-100 sm:p-5"
            >
              <span className="flex items-center justify-between gap-3 text-xs text-ink-500">
                {item.label}
                <span aria-hidden="true" className="transition-transform duration-fast group-hover:translate-x-0.5">→</span>
              </span>
              {item.body}
            </a>
          </li>
        ))}
      </ul>

      {topMaterial && (
        <p className="mt-3 text-xs text-ink-500">
          {t('dash.materialCaveat', 'Material ranking assumes the original material is')} {humanize(result.material.original_material)}
          {result.material.verification_required ? ` — ${t('dash.unconfirmed', 'not yet confirmed by testing')}.` : '.'}
        </p>
      )}
    </section>
  );
};

export default AnalysisOverview;
