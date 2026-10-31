import React from 'react';
import { RootCauseItem } from '../../types';
import { StatusBadge } from '../StatusBadge';
import { Disclosure } from './Disclosure';
import { URGENCY_BADGE, rankCauses, splitEvidence } from './presentation';
import { humanize } from '../../utils/analysis';
import { useLanguage } from '../../i18n/LanguageContext';

/** A rule chain exactly as the engine wrote it, drawn as connected steps. */
export const CauseFlow: React.FC<{ steps: string[] }> = ({ steps }) => (
  <ol className="flex flex-wrap items-center gap-y-2 text-[0.6875rem]" aria-label={steps.join(' leads to ')}>
    {steps.map((step, i) => (
      <li key={`${step}-${i}`} className="flex items-center">
        <span className="rounded-sm border border-ink-900/15 px-2 py-1 font-mono uppercase tracking-[0.06em] text-ink-700">{step.toLowerCase()}</span>
        {i < steps.length - 1 && (
          <span className="flex w-6 items-center" aria-hidden="true">
            <span className="h-px flex-1 bg-ink-900/25" />
            <span className="-ml-1 text-ink-500">›</span>
          </span>
        )}
      </li>
    ))}
  </ol>
);

const DetailList: React.FC<{ title: string; items: string[] }> = ({ title, items }) =>
  items.length === 0 ? null : (
    <div>
      <p className="text-xs font-medium text-ink-800">{title}</p>
      <ul className="mt-1.5 space-y-1 text-sm leading-relaxed text-ink-700">
        {items.map((item) => (
          <li key={item} className="flex gap-2.5">
            <span className="mt-[0.7rem] h-px w-2 shrink-0 bg-ink-500" aria-hidden="true" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );

export interface ProbableCausesProps {
  causes: RootCauseItem[];
}

/**
 * Probable causes ranked by the urgency the rule engine declared. The
 * collapsed row carries the cause, its urgency and the rule chain; the full
 * mechanism, evidence and verification needs open on demand.
 */
export const ProbableCauses: React.FC<ProbableCausesProps> = ({ causes }) => {
  const { t } = useLanguage();

  if (causes.length === 0) {
    return <p className="text-sm text-ink-600">{t('rootcause.noCauses', 'The rule engine did not infer any probable causes from these findings.')}</p>;
  }

  return (
    <ol className="divide-y divide-ink-900/10 border-y border-ink-900/15">
      {rankCauses(causes).map((cause, i) => {
        const { chains, evidence } = splitEvidence(cause.evidence_rules ?? []);
        return (
          <li key={`${cause.finding}-${i}`} className="grid gap-x-6 gap-y-3 py-6 md:grid-cols-[3rem_minmax(0,1fr)]">
            <span className="font-display text-2xl leading-none text-ink-500 tabular-nums">{String(i + 1).padStart(2, '0')}</span>
            <div className="min-w-0 space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <h4 className="max-w-[48rem] text-base font-medium leading-snug text-ink-950">{cause.finding}</h4>
                {cause.urgency && (
                  <StatusBadge
                    label={`${t('severity.' + cause.urgency, humanize(cause.urgency))} ${t('rootcause.urgency', 'urgency')}`}
                    variant={URGENCY_BADGE[cause.urgency] ?? 'neutral'}
                    dot
                  />
                )}
              </div>

              <p className="line-clamp-2 max-w-[60rem] text-sm leading-relaxed text-ink-700">
                <span className="text-ink-500">{t('dash.hypothesis', 'Hypothesis')} — </span>
                {cause.probable_cause}
              </p>

              {chains.length > 0 && (
                <div className="space-y-2">
                  <p className="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-ink-500">{t('dash.ruleChain', 'Rule chain · to verify on site')}</p>
                  {chains.map((steps) => (
                    <CauseFlow key={steps.join('>')} steps={steps} />
                  ))}
                </div>
              )}

              <Disclosure
                summary={<span className="text-xs font-medium">{t('dash.reasoning', 'Full reasoning & verification needs')}</span>}
                meta={cause.expert_review_required ? <StatusBadge label={t('origin.expert', 'Requires expert verification')} variant="ochre" /> : undefined}
              >
                <div className="grid gap-6 lg:grid-cols-2">
                  <div className="space-y-4">
                    <div>
                      <p className="text-xs font-medium text-ink-800">{t('rootcause.probableCause', 'Probable cause')}</p>
                      <p className="mt-1.5 text-sm leading-relaxed text-ink-700">{cause.probable_cause}</p>
                    </div>
                    {cause.observed_indicator && (
                      <div>
                        <p className="text-xs font-medium text-ink-800">{t('dash.observedIndicator', 'Observed indicator')}</p>
                        <p className="mt-1.5 text-sm leading-relaxed text-ink-700">{cause.observed_indicator}</p>
                      </div>
                    )}
                    <DetailList title={t('dash.evidenceUsed', 'Evidence used by the rule engine')} items={evidence} />
                  </div>
                  <div className="space-y-4">
                    <DetailList title={t('dash.investigation', 'Further investigation required')} items={cause.additional_investigation_required ?? []} />
                    {cause.uncertainty_note && (
                      <div className="border-l-2 border-ochre-500/50 pl-3">
                        <p className="text-xs font-medium text-ink-800">{t('dash.limitations', 'Limitations')}</p>
                        <p className="mt-1 text-sm leading-relaxed text-ink-700">{cause.uncertainty_note}</p>
                      </div>
                    )}
                    {cause.expert_specialty && (
                      <p className="text-xs text-ink-600">
                        {t('dash.reviewBy', 'Review by')}: <span className="text-ink-800">{cause.expert_specialty}</span>
                      </p>
                    )}
                    {!cause.observed_indicator && !cause.uncertainty_note && (cause.additional_investigation_required ?? []).length === 0 && (
                      <p className="text-xs leading-relaxed text-ink-500">
                        {t('dash.hypothesisNote', 'A rule-based hypothesis from image evidence. Confirm on site before acting on it.')}
                      </p>
                    )}
                  </div>
                </div>
              </Disclosure>
            </div>
          </li>
        );
      })}
    </ol>
  );
};

export default ProbableCauses;
