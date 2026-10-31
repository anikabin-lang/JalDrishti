import React from 'react';
import { LabelledMetric, humanize } from '../../utils/analysis';
import { Disclosure } from './Disclosure';
import { Meter, scaleFraction } from './Meter';
import { useLanguage } from '../../i18n/LanguageContext';

const PRIMARY = new Set(['visual_condition', 'water_functionality']);

export const AssessmentMetric: React.FC<{ item: LabelledMetric; primary: boolean }> = ({ item, primary }) => {
  const { t } = useLanguage();
  const { metric } = item;
  const span = metric.scale_max - metric.scale_min;
  const digits = span <= 1 ? 2 : 0;
  return (
    <article className={`flex flex-col gap-3 ${primary ? 'py-1' : ''}`}>
      <div className="flex items-baseline justify-between gap-3">
        <h4 className={`${primary ? 'text-base' : 'text-sm'} font-medium text-ink-900`}>{t('metric.' + item.key, item.label)}</h4>
        <span className="font-mono text-[0.625rem] text-ink-500 tabular-nums">
          {t('dash.engine', 'engine')} {(metric.confidence * 100).toFixed(0)}%
        </span>
      </div>
      <p className={`font-light leading-none text-ink-950 ${primary ? 'text-[3.25rem]' : 'text-[2rem]'}`}>
        {metric.value.toFixed(digits)}
        <span className="ml-1.5 text-base font-normal text-ink-500">/ {metric.scale_max}</span>
      </p>
      <Meter
        fraction={scaleFraction(metric.value, metric.scale_min, metric.scale_max)}
        tone={item.direction === 'higher_better' ? 'bg-jade-300' : 'bg-laterite-300'}
        size={primary ? 'md' : 'sm'}
      />
      <p className="text-xs text-ink-600">
        {item.direction === 'higher_better'
          ? t('score.higherBetter', 'Higher indicates better observed condition')
          : t('score.higherWorse', 'Higher indicates greater burden or urgency')}
      </p>
    </article>
  );
};

const LADDER: { key: string; label: string; detail: string; state: 'done' | 'partial' | 'open' }[] = [
  { key: 'observed', label: 'Observed', detail: 'Defect regions the vision model found in the photograph.', state: 'done' },
  { key: 'inferred', label: 'Inferred', detail: 'Scores computed by deterministic rules from that image evidence.', state: 'partial' },
  { key: 'verified', label: 'Verified', detail: 'Structural condition confirmed on site by a qualified engineer. Not established by this analysis.', state: 'open' },
];

export interface EngineeringAssessmentProps {
  metrics: LabelledMetric[];
}

/**
 * Rule-based scores with a strong numeric hierarchy, framed by an evidence
 * ladder that keeps observation, inference and verified condition apart.
 * Methods, engine confidence and every limitation sit in one disclosure.
 */
export const EngineeringAssessment: React.FC<EngineeringAssessmentProps> = ({ metrics }) => {
  const { t } = useLanguage();
  const primary = metrics.filter((m) => PRIMARY.has(m.key));
  const secondary = metrics.filter((m) => !PRIMARY.has(m.key));

  return (
    <div className="space-y-10">
      <ol className="grid overflow-hidden rounded-md border border-ink-900/10 md:grid-cols-3" aria-label={t('dash.evidenceLadder', 'Evidence ladder')}>
        {LADDER.map((step, i) => (
          <li
            key={step.key}
            className={`relative flex gap-3 p-4 ${i > 0 ? 'border-t border-ink-900/10 md:border-l md:border-t-0' : ''} ${step.state === 'open' ? 'bg-transparent' : 'bg-stone-100/60'}`}
          >
            <span
              className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${
                step.state === 'done' ? 'bg-jade-300' : step.state === 'partial' ? 'bg-ochre-500' : 'border border-dashed border-ink-500'
              }`}
              aria-hidden="true"
            />
            <div>
              <p className="text-sm font-medium text-ink-900">
                {t('dash.ladder.' + step.key, step.label)}
                {step.state === 'open' && <span className="ml-2 font-mono text-[0.625rem] uppercase tracking-[0.12em] text-ochre-700">{t('dash.notYet', 'Not yet')}</span>}
              </p>
              <p className="mt-1 text-xs leading-relaxed text-ink-600">{t('dash.ladder.' + step.key + 'Desc', step.detail)}</p>
            </div>
          </li>
        ))}
      </ol>

      {metrics.length === 0 ? (
        <p className="text-sm text-ink-600">{t('analysis.noEngineeringScores', 'The response contained no engineering scores.')}</p>
      ) : (
        <>
          {primary.length > 0 && (
            <div className="grid gap-x-12 gap-y-8 sm:grid-cols-2">
              {primary.map((m) => (
                <AssessmentMetric key={m.key} item={m} primary />
              ))}
            </div>
          )}
          {secondary.length > 0 && (
            <div className="grid gap-x-10 gap-y-8 border-t border-ink-900/10 pt-8 sm:grid-cols-2 lg:grid-cols-4">
              {secondary.map((m) => (
                <AssessmentMetric key={m.key} item={m} primary={false} />
              ))}
            </div>
          )}

          <Disclosure
            summary={<span className="font-medium">{t('dash.methodology', 'Methodology & assessment limitations')}</span>}
            meta={<span className="text-xs text-ink-500">{metrics.length} {t('dash.methods', 'methods')}</span>}
          >
            <div className="grid gap-8 md:grid-cols-2">
              {metrics.map(({ key, label, metric }) => (
                <div key={key} className="space-y-3">
                  <p className="text-sm font-medium text-ink-900">{t('metric.' + key, label)}</p>
                  <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 text-xs">
                    <dt className="text-ink-500">{t('score.method', 'Method')}</dt>
                    <dd className="break-words font-mono text-ink-700">{metric.method}</dd>
                    <dt className="text-ink-500">{t('score.confidence', 'Engine confidence')}</dt>
                    <dd className="font-mono text-ink-700 tabular-nums">{(metric.confidence * 100).toFixed(0)}%</dd>
                    <dt className="text-ink-500">{t('score.scale', 'scale')}</dt>
                    <dd className="font-mono text-ink-700 tabular-nums">
                      {metric.scale_min}–{metric.scale_max}
                    </dd>
                  </dl>
                  {metric.limitations.length > 0 && (
                    <ul className="space-y-1.5 text-sm leading-relaxed text-ink-700">
                      {metric.limitations.map((item) => (
                        <li key={item} className="flex gap-2.5">
                          <span className="mt-[0.7rem] h-px w-2 shrink-0 bg-ink-500" aria-hidden="true" />
                          <span>{humanize(item)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </Disclosure>
        </>
      )}
    </div>
  );
};

export default EngineeringAssessment;
