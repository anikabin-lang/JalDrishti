import React, { useEffect, useId, useMemo, useState } from 'react';
import { PrioritizedAction, RestorationResultContract } from '../../types';
import { StatusBadge } from '../StatusBadge';
import { Disclosure } from './Disclosure';
import { ACTION_URGENCY_BADGE, ACTION_URGENCY_RANK, PHASES, PRACTICE_SEVERITY_BADGE } from './presentation';
import { humanize } from '../../utils/analysis';
import { useLanguage } from '../../i18n/LanguageContext';

interface PhaseGroup {
  id: string;
  label: string;
  actions: PrioritizedAction[];
}

const highestUrgency = (actions: PrioritizedAction[]) =>
  actions.reduce<string | null>((top, a) => ((ACTION_URGENCY_RANK[a.urgency] ?? 0) > (ACTION_URGENCY_RANK[top ?? ''] ?? 0) ? a.urgency : top), null);

/** Full instructions for one action. */
const ActionDetail: React.FC<{ action: PrioritizedAction }> = ({ action }) => {
  const { t } = useLanguage();
  const rows: [string, React.ReactNode][] = [
    [t('restoration.targets', 'Targets'), t('defect.' + action.target_defect, humanize(action.target_defect))],
    [t('restoration.technique', 'Technique'), action.recommended_technique],
    [t('restoration.materials', 'Materials'), action.material_specification],
  ];
  if (action.preconditions?.length) rows.push([t('restoration.beforeStarting', 'Before starting'), action.preconditions.join(' ')]);

  return (
    <article className="border-t border-ink-900/10 pt-5 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h4 className="text-base font-medium text-ink-950">
          <span className="mr-2 font-mono text-sm font-normal text-ink-500 tabular-nums">{String(action.step).padStart(2, '0')}</span>
          {action.action_title}
        </h4>
        <StatusBadge label={t('severity.' + action.urgency, humanize(action.urgency))} variant={ACTION_URGENCY_BADGE[action.urgency] ?? 'neutral'} />
      </div>
      <dl className="mt-4 grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[8rem_minmax(0,1fr)]">
        {rows.map(([label, value]) => (
          <React.Fragment key={String(label)}>
            <dt className="text-xs text-ink-500 sm:pt-0.5">{label}</dt>
            <dd className="leading-relaxed text-ink-700">{value}</dd>
          </React.Fragment>
        ))}
      </dl>
    </article>
  );
};

/**
 * The planner's phases as a connected timeline. Each node carries its first
 * action as the objective and the phase's highest urgency; choosing a node
 * opens every action in that phase below the timeline.
 */
const PhaseTimeline: React.FC<{ phases: PhaseGroup[] }> = ({ phases }) => {
  const { t } = useLanguage();
  const firstWithActions = phases.find((p) => p.actions.length > 0)?.id ?? null;
  const [selected, setSelected] = useState<string | null>(firstWithActions);
  const key = phases.map((p) => `${p.id}:${p.actions.length}`).join('|');

  useEffect(() => setSelected(firstWithActions), [key]); // eslint-disable-line react-hooks/exhaustive-deps

  const current = phases.find((p) => p.id === selected);
  const panelId = useId();

  return (
    <div>
      <ol className="relative grid gap-3 md:grid-cols-4 md:gap-0" aria-label={t('dash.phases', 'Restoration phases')}>
        {/* Connector through the phase markers. */}
        <span className="absolute left-[1.0625rem] top-4 bottom-4 w-px bg-ink-900/15 md:left-4 md:right-[calc(25%-1.0625rem)] md:top-[1.0625rem] md:bottom-auto md:h-px md:w-auto" aria-hidden="true" />
        {phases.map((phase, i) => {
          const empty = phase.actions.length === 0;
          const active = phase.id === selected;
          const urgency = highestUrgency(phase.actions);
          return (
            <li key={phase.id} className="relative md:pr-4">
              <button
                type="button"
                aria-pressed={active}
                aria-controls={empty ? undefined : panelId}
                disabled={empty}
                onClick={() => setSelected(phase.id)}
                className={`group flex w-full gap-3 rounded-md p-1 text-left transition-colors duration-fast md:flex-col md:gap-4 ${empty ? 'cursor-default' : 'hover:bg-stone-100/60'}`}
              >
                <span
                  className={`relative z-[1] flex h-7 w-7 shrink-0 items-center justify-center rounded-full border font-mono text-xs tabular-nums transition-colors duration-fast ${
                    active
                      ? 'border-jade-300 bg-jade-300 text-[#0e0c0a]'
                      : empty
                        ? 'border-dashed border-ink-900/25 bg-stone-50 text-ink-500'
                        : 'border-ink-900/30 bg-stone-50 text-ink-800 group-hover:border-ink-900/60'
                  }`}
                >
                  {i + 1}
                </span>
                <span className="min-w-0 space-y-1.5 md:pr-2">
                  <span className={`block font-display text-lg leading-tight ${empty ? 'text-ink-500' : 'text-ink-950'}`}>
                    {t('restoration.' + phase.id.replace(/^phase_\d+_/, ''), phase.label)}
                  </span>
                  {empty ? (
                    <span className="block text-xs text-ink-500">{t('dash.noPhaseAction', 'No action proposed for this phase')}</span>
                  ) : (
                    <>
                      <span className="line-clamp-2 text-xs leading-relaxed text-ink-600">{phase.actions[0].action_title}</span>
                      <span className="flex flex-wrap items-center gap-2">
                        {urgency && <StatusBadge label={t('severity.' + urgency, humanize(urgency))} variant={ACTION_URGENCY_BADGE[urgency] ?? 'neutral'} />}
                        {phase.actions.length > 1 && (
                          <span className="font-mono text-[0.625rem] text-ink-500">
                            {phase.actions.length} {t('dash.actions', 'actions')}
                          </span>
                        )}
                      </span>
                    </>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ol>

      {current && current.actions.length > 0 && (
        <div id={panelId} role="region" aria-live="polite" className="mt-8 space-y-5 rounded-md border border-ink-900/10 bg-stone-100/40 p-5 sm:p-6">
          {current.actions.map((action) => (
            <ActionDetail key={action.step} action={action} />
          ))}
        </div>
      )}
    </div>
  );
};

export interface RestorationStrategyProps {
  restoration: RestorationResultContract;
}

/** Timeline, the practices to avoid, and traditional conservation guidance. */
export const RestorationStrategy: React.FC<RestorationStrategyProps> = ({ restoration }) => {
  const { t } = useLanguage();
  const actions = useMemo(() => [...(restoration.prioritized_actions ?? [])].sort((a, b) => a.step - b.step), [restoration]);

  const phases: PhaseGroup[] = useMemo(() => {
    const known = new Set<string>(PHASES.map((p) => p.id));
    const extra = Array.from(new Set(actions.map((a) => a.phase)))
      .filter((p) => !known.has(p))
      .map((p) => ({ id: p as string, label: humanize(p) }));
    return [...PHASES, ...extra].map((p) => ({ ...p, actions: actions.filter((a) => a.phase === p.id) }));
  }, [actions]);

  const practices = restoration.incompatible_practices ?? [];
  const iks = restoration.iks_guidelines;

  return (
    <div className="space-y-12">
      <div>
        <p className="mb-6 text-sm text-ink-700">
          {t('restoration.strategy', 'Strategy')}:{' '}
          <span className="font-medium text-ink-950">{t('strategy.' + restoration.restoration_strategy, humanize(restoration.restoration_strategy))}</span>
        </p>
        {actions.length === 0 ? (
          <p className="text-sm text-ink-600">{t('restoration.noActions', 'The planner returned no prioritised actions.')}</p>
        ) : (
          <PhaseTimeline phases={phases} />
        )}
      </div>

      {practices.length > 0 && (
        <div>
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-base font-medium text-ink-950">{t('restoration.practicesToAvoid', 'Practices to avoid')}</h3>
            <span className="text-xs text-ink-500">{t('dash.expandRisk', 'Expand for the failure mechanism')}</span>
          </div>
          <div className="overflow-hidden rounded-md border border-danger-500/25">
            {practices.map((p, i) => (
              <Disclosure
                key={p.prohibited_action}
                rule={i > 0}
                className="px-4"
                summary={
                  <span className="flex items-start gap-3">
                    <span className="mt-[0.45rem] h-1.5 w-1.5 shrink-0 rounded-full bg-danger-500" aria-hidden="true" />
                    <span className="text-sm text-ink-900">{p.prohibited_action}</span>
                  </span>
                }
                meta={<StatusBadge label={t('severity.' + p.severity, humanize(p.severity))} variant={PRACTICE_SEVERITY_BADGE[p.severity] ?? 'neutral'} />}
              >
                <p className="pl-[1.125rem] text-sm leading-relaxed text-ink-700">{p.failure_mechanism}</p>
              </Disclosure>
            ))}
          </div>
        </div>
      )}

      {iks && (iks.traditional_mortar_recipe || iks.seasonal_curing_rules) && (
        <div>
          <h3 className="mb-1 text-base font-medium text-ink-950">{t('dash.traditionalPractices', 'Traditional conservation practices')}</h3>
          <p className="mb-4 text-xs text-ink-500">
            {t('dash.traditionalNote', 'Regional guidance from the knowledge base; verify proportions against tests of the original mortar.')}
          </p>
          <div className="grid gap-x-10 md:grid-cols-2">
            {iks.traditional_mortar_recipe && (
              <Disclosure
                summary={
                  <span className="block">
                    <span className="block font-medium text-ink-900">{t('restoration.traditionalMortar', 'Traditional mortar')}</span>
                    <span className="mt-1 line-clamp-1 text-xs text-ink-600">{iks.traditional_mortar_recipe}</span>
                  </span>
                }
              >
                <p className="text-sm leading-relaxed text-ink-700">{iks.traditional_mortar_recipe}</p>
              </Disclosure>
            )}
            {iks.seasonal_curing_rules && (
              <Disclosure
                summary={
                  <span className="block">
                    <span className="block font-medium text-ink-900">{t('restoration.seasonalCuring', 'Seasonal curing')}</span>
                    <span className="mt-1 line-clamp-1 text-xs text-ink-600">{iks.seasonal_curing_rules}</span>
                  </span>
                }
              >
                <p className="text-sm leading-relaxed text-ink-700">{iks.seasonal_curing_rules}</p>
              </Disclosure>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default RestorationStrategy;
