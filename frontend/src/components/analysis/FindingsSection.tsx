import React from 'react';
import { DetectionItem, ScaleReference } from '../../types';
import { StatusBadge } from '../StatusBadge';
import { VisualMetricsPanel } from '../VisualMetricsPanel';
import { Disclosure } from './Disclosure';
import { EXTENT_BADGE, rankDetections } from './presentation';
import { defectColor, formatNumber, formatPercent, humanize } from '../../utils/analysis';
import { useLanguage } from '../../i18n/LanguageContext';

interface LinkedProps {
  detections: DetectionItem[];
  order: number[];
  highlighted: number | null;
  onHighlight: (index: number | null) => void;
}

const AXIS_STEPS = [0.01, 0.02, 0.05, 0.1, 0.2, 0.25, 0.5, 1];

/** Smallest round axis maximum that holds the largest coverage share. */
const axisMax = (detections: DetectionItem[]) => {
  const peak = detections.reduce((max, d) => Math.max(max, d.coverage_ratio), 0);
  return AXIS_STEPS.find((step) => step >= peak) ?? 1;
};

/**
 * Image-space coverage per detected class. Classes can overlap in the frame,
 * so shares are drawn as independent bars against a 0–100% axis, never as
 * parts of one whole.
 */
export const FindingsDistributionChart: React.FC<LinkedProps> = ({ detections, order, highlighted, onHighlight }) => {
  const { t } = useLanguage();
  const max = axisMax(detections);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * max);
  return (
    <figure>
      <figcaption className="mb-4">
        <p className="text-sm font-medium text-ink-900">{t('dash.coverageTitle', 'Image-space coverage by class')}</p>
        <p className="mt-0.5 text-xs leading-relaxed text-ink-500">
          {t('dash.coverageDesc', 'Share of the photograph each class occupies. Regions can overlap, so shares need not sum to 100%.')}
          {max < 1 && ` ${t('dash.axisTo', 'Axis runs to')} ${formatPercent(max, 0)}.`}
        </p>
      </figcaption>

      <div className="relative">
        {/* Gridlines sit behind the bar column only. */}
        <div className="pointer-events-none absolute inset-y-0 left-[8.5rem] right-[4rem] sm:left-[11.5rem]" aria-hidden="true">
          {ticks.map((tick) => (
            <span key={tick} className="absolute inset-y-0 w-px bg-ink-900/[0.07]" style={{ left: `${(tick / max) * 100}%` }} />
          ))}
        </div>

        <ul className="relative space-y-1">
          {order.map((index) => {
            const d = detections[index];
            const active = highlighted === index;
            const dimmed = highlighted !== null && !active;
            return (
              <li
                key={index}
                tabIndex={0}
                onMouseEnter={() => onHighlight(index)}
                onMouseLeave={() => onHighlight(null)}
                onFocus={() => onHighlight(index)}
                onBlur={() => onHighlight(null)}
                aria-label={`${humanize(d.class_name)}: ${formatPercent(d.coverage_ratio, 1)} ${t('dash.ofImage', 'of the image')}, ${formatPercent(d.confidence, 0)} ${t('dash.confidence', 'confidence')}`}
                className={`group relative grid grid-cols-[8rem_minmax(0,1fr)_3.5rem] items-center gap-2 rounded-sm py-2 transition-opacity duration-fast focus:outline-none focus-visible:bg-stone-100 sm:grid-cols-[11rem_minmax(0,1fr)_3.5rem] ${dimmed ? 'opacity-45' : ''}`}
              >
                <span className="flex min-w-0 items-center gap-2 text-sm text-ink-800">
                  <span className="h-2 w-2 shrink-0 rounded-[1px]" style={{ backgroundColor: defectColor(d.class_name) }} aria-hidden="true" />
                  <span className="leading-snug">{t('defect.' + d.class_name, humanize(d.class_name))}</span>
                </span>
                <span className="relative h-2.5">
                  <span
                    className="absolute inset-y-0 left-0 rounded-r-[4px]"
                    style={{ width: `${Math.min(1, d.coverage_ratio / max) * 100}%`, backgroundColor: defectColor(d.class_name), minWidth: 2 }}
                  />
                </span>
                <span className="text-right font-mono text-xs text-ink-900 tabular-nums">{formatPercent(d.coverage_ratio, 1)}</span>

                <span
                  role="tooltip"
                  className={`pointer-events-none absolute left-[8.5rem] top-full z-10 mt-1 w-56 rounded-md border border-ink-900/15 bg-stone-100 p-3 text-xs text-ink-700 shadow-overlay transition-opacity duration-fast sm:left-[11.5rem] ${active ? 'opacity-100' : 'opacity-0'}`}
                >
                  <span className="block font-medium text-ink-900">{t('defect.' + d.class_name, humanize(d.class_name))}</span>
                  <span className="mt-1.5 grid grid-cols-[1fr_auto] gap-x-3 gap-y-0.5 font-mono tabular-nums">
                    <span className="font-sans text-ink-500">{t('dash.coverage', 'Coverage')}</span>
                    <span>{formatPercent(d.coverage_ratio, 2)}</span>
                    <span className="font-sans text-ink-500">{t('dash.confidenceLabel', 'Confidence')}</span>
                    <span>{formatPercent(d.confidence, 1)}</span>
                    <span className="font-sans text-ink-500">{t('dash.area', 'Area')}</span>
                    <span>{formatNumber(d.pixel_area)} px²</span>
                    <span className="font-sans text-ink-500">{t('dash.components', 'Components')}</span>
                    <span>{d.component_count}</span>
                  </span>
                </span>
              </li>
            );
          })}
        </ul>

        <div className="mt-1 grid grid-cols-[8rem_minmax(0,1fr)_3.5rem] gap-2 sm:grid-cols-[11rem_minmax(0,1fr)_3.5rem]" aria-hidden="true">
          <span />
          <span className="relative h-4 font-mono text-[0.625rem] text-ink-500 tabular-nums">
            {ticks.map((tick, i) => (
              <span
                key={tick}
                className={`absolute top-0 ${i === 0 ? '' : i === ticks.length - 1 ? '-translate-x-full' : '-translate-x-1/2'}`}
                style={{ left: `${(tick / max) * 100}%` }}
              >
                {formatPercent(tick, Number.isInteger(Math.round(tick * 1000) / 10) ? 0 : 1)}
              </span>
            ))}
          </span>
        </div>
      </div>
    </figure>
  );
};

/** One detected class: extent, confidence, coverage and component count, restated in one sentence. */
export const FindingCard: React.FC<{
  detection: DetectionItem;
  lead: boolean;
  active: boolean;
  onHighlight: (on: boolean) => void;
}> = ({ detection: d, lead, active, onHighlight }) => {
  const { t } = useLanguage();
  const extent = d.relative_severity;
  return (
    <article
      tabIndex={0}
      onMouseEnter={() => onHighlight(true)}
      onMouseLeave={() => onHighlight(false)}
      onFocus={() => onHighlight(true)}
      onBlur={() => onHighlight(false)}
      className={`relative flex flex-col gap-4 rounded-md border p-4 transition-colors duration-fast focus:outline-none sm:p-5 ${
        active ? 'border-ink-900/30 bg-stone-100' : lead ? 'border-ink-900/20 bg-stone-100/60' : 'border-ink-900/10'
      }`}
    >
      <span className="absolute inset-y-4 left-0 w-[3px] rounded-r-full" style={{ backgroundColor: defectColor(d.class_name) }} aria-hidden="true" />
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          {lead && <p className="mb-1 font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-500">{t('dash.leadFindingShort', 'Most extensive')}</p>}
          <h4 className={`font-medium text-ink-950 ${lead ? 'text-lg' : 'text-base'}`}>{t('defect.' + d.class_name, humanize(d.class_name))}</h4>
        </div>
        {extent ? (
          <StatusBadge
            label={`${t('severity.' + extent, humanize(extent))} ${t('dash.extent', 'extent')}`}
            variant={EXTENT_BADGE[extent] ?? 'neutral'}
          />
        ) : (
          <StatusBadge label={t('dash.extentNotReported', 'Extent not reported')} />
        )}
      </header>

      <dl className="grid grid-cols-3 gap-3">
        {[
          [formatPercent(d.confidence, 0), t('dash.confidenceLabel', 'Confidence')],
          [formatPercent(d.coverage_ratio, 1), t('dash.coverage', 'Coverage')],
          [String(d.component_count), t('dash.components', 'Components')],
        ].map(([value, label]) => (
          <div key={label} className="flex min-w-0 flex-col-reverse">
            <dt className="mt-0.5 text-[0.6875rem] text-ink-500">{label}</dt>
            <dd className="text-xl font-light text-ink-950">{value}</dd>
          </div>
        ))}
      </dl>

      <p className="text-xs leading-relaxed text-ink-600">
        {d.component_count} {d.component_count === 1 ? t('dash.region', 'connected region') : t('dash.regions', 'connected regions')}{' '}
        {t('dash.covering', 'covering')} {formatPercent(d.coverage_ratio, 1)} {t('dash.ofFrame', 'of the frame')}
        {typeof d.total_length_pixels === 'number' ? `, ${formatNumber(d.total_length_pixels)} px ${t('dash.totalLength', 'total length')}` : ''}.
      </p>
    </article>
  );
};

export interface FindingsSectionProps {
  detections: DetectionItem[];
  scaleReference?: ScaleReference;
  highlighted: number | null;
  onHighlight: (index: number | null) => void;
  /** The annotated photograph and its class toggles. */
  canvas: React.ReactNode;
}

/** Key findings: photograph, coverage chart, ranked finding cards and the full measurement table on demand. */
export const FindingsSection: React.FC<FindingsSectionProps> = ({ detections, scaleReference, highlighted, onHighlight, canvas }) => {
  const { t } = useLanguage();
  const order = rankDetections(detections);

  return (
    <div className="space-y-8">
      <div className="grid gap-8 lg:grid-cols-12 lg:items-start">
        <div className="lg:col-span-7">{canvas}</div>
        <div className="space-y-8 lg:col-span-5">
          {detections.length === 0 ? (
            <p className="border-y border-ink-900/10 py-6 text-sm leading-relaxed text-ink-700">
              {t(
                'metrics.noDetectionsNote',
                'The vision service returned no detections for this image. This does not mean the structure is free of defects — only that none were identified in this photograph by the current model.'
              )}
            </p>
          ) : (
            <>
              <FindingsDistributionChart detections={detections} order={order} highlighted={highlighted} onHighlight={onHighlight} />
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
                {order.map((index, rank) => (
                  <FindingCard
                    key={index}
                    detection={detections[index]}
                    lead={rank === 0 && order.length > 1}
                    active={highlighted === index}
                    onHighlight={(on) => onHighlight(on ? index : null)}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {detections.length > 0 && (
        <Disclosure
          summary={<span className="font-medium">{t('dash.detailedMeasurements', 'View detailed measurements')}</span>}
          meta={<span className="text-xs text-ink-500">{t('dash.imageSpace', 'Image-space · pixels')}</span>}
        >
          <VisualMetricsPanel detections={detections} scaleReference={scaleReference} highlighted={highlighted} onHighlight={onHighlight} />
        </Disclosure>
      )}
    </div>
  );
};

export default FindingsSection;
