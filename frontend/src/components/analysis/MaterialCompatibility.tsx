import React, { useEffect, useMemo, useState } from 'react';
import { CandidateIntervention, MaterialCompatibilityContract } from '../../types';
import { OriginTag, StatusBadge } from '../StatusBadge';
import { Disclosure } from './Disclosure';
import { Meter } from './Meter';
import { COMPARE_COLORS, DIMENSIONS, RECOMMENDATION, dimensionExtremes, isIncompatible, rankMaterials, splitWarning } from './presentation';
import { humanize } from '../../utils/analysis';
import { useLanguage } from '../../i18n/LanguageContext';

const MAX_COMPARE = 3;

const recommendationOf = (c: CandidateIntervention) =>
  RECOMMENDATION[c.recommendation] ?? { label: humanize(c.recommendation), variant: 'neutral' as const, bar: 'bg-ink-500' };

/** The assumption every score below depends on, kept visible. */
const AssumptionPanel: React.FC<{ material: MaterialCompatibilityContract }> = ({ material }) => {
  const { t } = useLanguage();
  const tests = material.recommended_tests ?? [];
  return (
    <aside className="rounded-md border border-ochre-500/30 bg-ochre-100/30 p-5">
      <p className="text-xs text-ink-600">{t('material.assumedOriginal', 'Assumed original material')}</p>
      <p className="mt-1 text-lg font-medium text-ink-950">{humanize(material.original_material)}</p>
      <div className="mt-3 flex items-center gap-3">
        <Meter fraction={material.original_material_confidence} tone="bg-ochre-500" className="max-w-[8rem]" />
        <span className="font-mono text-xs text-ink-700 tabular-nums">
          {(material.original_material_confidence * 100).toFixed(0)}% {t('dash.assumptionConfidence', 'assumption confidence')}
        </span>
      </div>
      {material.verification_required && <OriginTag kind="expert" className="mt-4" />}
      <p className="mt-4 text-sm leading-relaxed text-ink-700">
        {t(
          'dash.assumptionNote',
          'Inferred from structure characteristics, not identified from the photograph. Scores hold only if the assumption is confirmed.'
        )}
      </p>
      {tests.length > 0 && (
        <Disclosure
          className="mt-3"
          summary={<span className="text-xs font-medium">{t('material.recommendedTests', 'Recommended confirmation tests')}</span>}
          meta={<span className="font-mono text-xs text-ink-500 tabular-nums">{tests.length}</span>}
        >
          <ol className="space-y-1.5 text-xs leading-relaxed text-ink-700">
            {tests.map((test, i) => (
              <li key={test} className="flex gap-3">
                <span className="font-mono text-ink-500 tabular-nums">{String(i + 1).padStart(2, '0')}</span>
                <span>{test}</span>
              </li>
            ))}
          </ol>
        </Disclosure>
      )}
    </aside>
  );
};

interface RankingProps {
  ranked: CandidateIntervention[];
  focused: string;
  /** Comparison colour per ticked material; absent when not compared. */
  colorOf: (id: string) => string | undefined;
  onFocus: (id: string) => void;
  onToggleCompare: (id: string) => void;
}

/** Ranked compatibility: one row per material, score bar coloured by its recommendation. */
const MaterialRankingChart: React.FC<RankingProps> = ({ ranked, focused, colorOf, onFocus, onToggleCompare }) => {
  const { t } = useLanguage();
  return (
    <figure>
      <figcaption className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-sm font-medium text-ink-900">{t('dash.rankingTitle', 'Compatibility ranking')}</span>
        <span className="text-xs text-ink-500">{t('dash.rankingHint', 'Select a material for its profile · tick to compare')}</span>
      </figcaption>
      <ul className="divide-y divide-ink-900/10 border-y border-ink-900/10">
        {ranked.map((c, rank) => {
          const id = c.intervention_material;
          const rec = recommendationOf(c);
          const selected = focused === id;
          const compareColor = colorOf(id);
          const concerns = c.warnings?.length ?? 0;
          return (
            <li key={id} className={`flex items-stretch transition-colors duration-fast ${selected ? 'bg-stone-100' : 'hover:bg-stone-100/50'}`}>
              <button
                type="button"
                onClick={() => onFocus(id)}
                aria-pressed={selected}
                className="grid min-w-0 flex-1 grid-cols-[1.5rem_minmax(0,1fr)_3.25rem] items-center gap-x-3 gap-y-2 py-3 pl-3 text-left sm:grid-cols-[1.5rem_minmax(0,14rem)_minmax(5rem,1fr)_3.25rem_auto]"
              >
                <span className="font-mono text-xs text-ink-500 tabular-nums">{rank + 1}</span>
                <span className="min-w-0">
                  <span className={`line-clamp-2 text-sm leading-snug ${selected ? 'font-medium text-ink-950' : 'text-ink-800'}`}>{humanize(id)}</span>
                  {concerns > 0 && (
                    <span className="block text-[0.6875rem] text-danger-700">
                      {concerns} {concerns === 1 ? t('dash.concern', 'concern') : t('dash.concerns', 'concerns')}
                    </span>
                  )}
                </span>
                <span className="relative col-span-3 col-start-1 row-start-2 h-2 sm:col-span-1 sm:col-start-3 sm:row-start-1" aria-hidden="true">
                  <span className="absolute inset-0 rounded-r-[4px] bg-ink-900/[0.06]" />
                  <span className={`absolute inset-y-0 left-0 rounded-r-[4px] ${rec.bar}`} style={{ width: `${Math.min(100, Math.max(0, c.compatibility_score))}%` }} />
                </span>
                <span className="text-right font-mono text-sm text-ink-950 tabular-nums sm:col-start-4">{c.compatibility_score.toFixed(1)}</span>
                <span className="hidden whitespace-nowrap sm:block">
                  <StatusBadge label={t('material.' + c.recommendation, rec.label)} variant={rec.variant} />
                </span>
              </button>
              <label className="flex w-12 shrink-0 cursor-pointer items-center justify-center" title={t('dash.compare', 'Compare')}>
                <input
                  type="checkbox"
                  checked={!!compareColor}
                  onChange={() => onToggleCompare(id)}
                  className="peer sr-only"
                  aria-label={`${t('dash.compare', 'Compare')} ${humanize(id)}`}
                />
                <span
                  className="flex h-4 w-4 items-center justify-center rounded-sm border border-ink-900/30 peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-laterite-400"
                  style={compareColor ? { backgroundColor: compareColor, borderColor: compareColor } : undefined}
                  aria-hidden="true"
                >
                  {compareColor && <span className="text-[0.625rem] leading-none text-[#0e0c0a]">✓</span>}
                </span>
              </label>
            </li>
          );
        })}
      </ul>
      <p className="mt-2 text-xs text-ink-500">{t('dash.rankingScale', 'Overall compatibility, 0–100, from the rule-based engine.')}</p>
    </figure>
  );
};

/** Seven-dimension profile of up to three materials on one shared 0–10 scale. */
const MaterialComparisonChart: React.FC<{ materials: { candidate: CandidateIntervention; color: string }[] }> = ({ materials }) => {
  const { t } = useLanguage();
  const [hovered, setHovered] = useState<string | null>(null);

  if (materials.length === 0) {
    return (
      <p className="rounded-md border border-dashed border-ink-900/15 p-6 text-sm text-ink-600">
        {t('dash.compareEmpty', 'Tick up to three materials in the ranking to compare their profiles.')}
      </p>
    );
  }

  return (
    <figure>
      <figcaption className="mb-4">
        <p className="text-sm font-medium text-ink-900">{t('dash.profileTitle', 'Compatibility profile')}</p>
        <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-ink-700">
          {materials.map(({ candidate: m, color }) => (
            <li key={m.intervention_material} className="flex items-center gap-2">
              <span className="h-2 w-3 rounded-[1px]" style={{ backgroundColor: color }} aria-hidden="true" />
              {humanize(m.intervention_material)}
            </li>
          ))}
        </ul>
      </figcaption>

      <div className="relative">
        <div className="pointer-events-none absolute inset-y-0 left-[6.75rem] right-0" aria-hidden="true">
          {[0, 5, 10].map((tick) => (
            <span key={tick} className="absolute inset-y-0 w-px bg-ink-900/[0.07]" style={{ left: `${tick * 10}%` }} />
          ))}
        </div>
        <dl className="relative space-y-3">
          {DIMENSIONS.map(({ key, label, meaning }) => {
            const active = hovered === key;
            return (
              <div
                key={key}
                tabIndex={0}
                onMouseEnter={() => setHovered(key)}
                onMouseLeave={() => setHovered(null)}
                onFocus={() => setHovered(key)}
                onBlur={() => setHovered(null)}
                className="group relative grid grid-cols-[6.25rem_minmax(0,1fr)] items-center gap-2 rounded-sm focus:outline-none focus-visible:bg-stone-100"
              >
                <dt className="text-xs text-ink-700" title={meaning}>
                  {t('material.' + key, label)}
                </dt>
                <dd className="space-y-[2px]">
                  {materials.map(({ candidate: m, color }) => {
                    const value = m.compatibility_dimensions?.[key];
                    return (
                      <span key={m.intervention_material} className="relative block h-1.5">
                        {typeof value === 'number' && (
                          <span
                            className="absolute inset-y-0 left-0 rounded-r-[4px]"
                            style={{ width: `${Math.min(10, Math.max(0, value)) * 10}%`, backgroundColor: color, minWidth: 2 }}
                          />
                        )}
                        <span className="sr-only">
                          {humanize(m.intervention_material)}: {typeof value === 'number' ? `${value.toFixed(1)} / 10` : t('dash.notAvailableShort', 'not available')}
                        </span>
                      </span>
                    );
                  })}
                </dd>
                <span
                  role="tooltip"
                  className={`pointer-events-none absolute right-0 top-full z-10 mt-1 min-w-[13rem] rounded-md border border-ink-900/15 bg-stone-100 p-3 text-xs shadow-overlay transition-opacity duration-fast ${active ? 'opacity-100' : 'opacity-0'}`}
                >
                  <span className="block font-medium text-ink-900">{t('material.' + key, label)}</span>
                  <span className="mt-0.5 block text-ink-500">{meaning}</span>
                  <span className="mt-2 grid grid-cols-[auto_1fr_auto] items-center gap-x-2 gap-y-1">
                    {materials.map(({ candidate: m, color }) => {
                      const value = m.compatibility_dimensions?.[key];
                      return (
                        <React.Fragment key={m.intervention_material}>
                          <span className="h-2 w-2 rounded-[1px]" style={{ backgroundColor: color }} />
                          <span className="truncate text-ink-700">{humanize(m.intervention_material)}</span>
                          <span className="font-mono text-ink-900 tabular-nums">{typeof value === 'number' ? value.toFixed(1) : '—'}</span>
                        </React.Fragment>
                      );
                    })}
                  </span>
                </span>
              </div>
            );
          })}
        </dl>
        <div className="mt-2 grid grid-cols-[6.25rem_minmax(0,1fr)] gap-2" aria-hidden="true">
          <span />
          <span className="relative h-4 font-mono text-[0.625rem] text-ink-500 tabular-nums">
            {[0, 5, 10].map((tick) => (
              <span key={tick} className={`absolute top-0 ${tick === 0 ? '' : tick === 10 ? '-translate-x-full' : '-translate-x-1/2'}`} style={{ left: `${tick * 10}%` }}>
                {tick}
              </span>
            ))}
          </span>
        </div>
      </div>
      <p className="mt-2 text-xs text-ink-500">{t('dash.profileScale', 'Each dimension scored 0–10. Hover or focus a row for exact values.')}</p>
    </figure>
  );
};

/** The focused material: score, verdict, dimension breakdown and its warnings on demand. */
const MaterialDetailPanel: React.FC<{ candidate: CandidateIntervention }> = ({ candidate }) => {
  const { t } = useLanguage();
  const rec = recommendationOf(candidate);
  const incompatible = isIncompatible(candidate);
  const { weakest, strongest } = dimensionExtremes(candidate);
  const low = DIMENSIONS.filter((d) => (candidate.compatibility_dimensions?.[d.key] ?? 10) < 4);
  const warnings = candidate.warnings ?? [];

  return (
    <article className={`rounded-md border p-5 ${incompatible ? 'border-danger-500/40 bg-danger-100/30' : 'border-ink-900/15 bg-stone-100/50'}`}>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs text-ink-500">{t('dash.selectedMaterial', 'Selected material')}</p>
          <h4 className="mt-1 text-lg font-medium text-ink-950">{humanize(candidate.intervention_material)}</h4>
        </div>
        <StatusBadge label={t('material.' + candidate.recommendation, rec.label)} variant={rec.variant} dot />
      </header>

      <p className="mt-4 text-[2.5rem] font-light leading-none text-ink-950">
        {candidate.compatibility_score.toFixed(1)}
        <span className="ml-1.5 text-base font-normal text-ink-500">/ 100</span>
      </p>

      <p className="mt-3 text-sm leading-relaxed text-ink-700">
        {incompatible
          ? low.length > 0
            ? `${t('dash.scoresBelow', 'Scores below 4 / 10 on')} ${low.map((d) => t('material.' + d.key, d.label).toLowerCase()).join(', ')}.`
            : t('dash.flaggedIncompatible', 'Flagged incompatible by the rule engine.')
          : weakest && strongest
            ? `${t('dash.strongest', 'Strongest on')} ${t('material.' + strongest.key, strongest.label).toLowerCase()} (${strongest.value.toFixed(1)}); ${t('dash.weakest', 'weakest on')} ${t('material.' + weakest.key, weakest.label).toLowerCase()} (${weakest.value.toFixed(1)}).`
            : null}
      </p>

      <dl className="mt-5 grid grid-cols-[6rem_minmax(0,1fr)_2rem] items-center gap-x-3 gap-y-2 text-xs">
        {DIMENSIONS.map(({ key, label }) => {
          const value = candidate.compatibility_dimensions?.[key];
          if (typeof value !== 'number') return null;
          return (
            <React.Fragment key={key}>
              <dt className="text-ink-600">{t('material.' + key, label)}</dt>
              <dd>
                <Meter fraction={value / 10} tone={value < 4 ? 'bg-danger-500' : value < 7 ? 'bg-ochre-500' : 'bg-jade-400'} />
              </dd>
              <dd className="text-right font-mono text-ink-900 tabular-nums">{value.toFixed(1)}</dd>
            </React.Fragment>
          );
        })}
      </dl>

      {warnings.length > 0 && (
        <div className="mt-5">
          <p className="mb-1 text-xs font-medium text-danger-700">
            {warnings.length} {warnings.length === 1 ? t('dash.concern', 'concern') : t('dash.concerns', 'concerns')}
          </p>
          {warnings.map((warning) => {
            const { title, body } = splitWarning(warning);
            return (
              <Disclosure
                key={warning}
                summary={<span className="line-clamp-1 text-xs text-ink-800">{title ?? body}</span>}
              >
                <p className="text-sm leading-relaxed text-ink-700">{body}</p>
              </Disclosure>
            );
          })}
        </div>
      )}

      {!incompatible && (
        <p className="mt-5 text-xs leading-relaxed text-ink-500">
          {t('dash.rankCaveat', 'A high score reflects compatibility with the assumed original material only; it is not a universal endorsement.')}
        </p>
      )}
    </article>
  );
};

export interface MaterialCompatibilityProps {
  material: MaterialCompatibilityContract;
}

/** Assumption, ranking, side-by-side profile and the selected material's detail. */
export const MaterialCompatibility: React.FC<MaterialCompatibilityProps> = ({ material }) => {
  const { t } = useLanguage();
  const ranked = useMemo(() => rankMaterials(material.candidate_interventions ?? []), [material]);
  const ids = ranked.map((c) => c.intervention_material).join('|');

  const defaults = () => {
    const top = ranked[0]?.intervention_material;
    const bottom = ranked[ranked.length - 1]?.intervention_material;
    const ids = [top, bottom].filter((id, i, all): id is string => !!id && all.indexOf(id) === i);
    return { focused: top ?? '', compared: ids.map((id, slot) => ({ id, slot })) };
  };
  const [focused, setFocused] = useState(() => defaults().focused);
  // Each ticked material keeps its colour slot until unticked, so others never repaint.
  const [compared, setCompared] = useState<{ id: string; slot: number }[]>(() => defaults().compared);

  // A new result resets the selection.
  useEffect(() => {
    const next = defaults();
    setFocused(next.focused);
    setCompared(next.compared);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ids]);

  const toggleCompare = (id: string) =>
    setCompared((prev) => {
      if (prev.some((c) => c.id === id)) return prev.filter((c) => c.id !== id);
      const kept = prev.length >= MAX_COMPARE ? prev.slice(1) : prev;
      const slot = [0, 1, 2].find((s) => !kept.some((c) => c.slot === s)) ?? 0;
      return [...kept, { id, slot }];
    });
  const colorOf = (id: string) => {
    const entry = compared.find((c) => c.id === id);
    return entry ? COMPARE_COLORS[entry.slot] : undefined;
  };

  if (ranked.length === 0) {
    return (
      <div className="grid gap-8 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <AssumptionPanel material={material} />
        </div>
        <p className="text-sm text-ink-600 lg:col-span-8">{t('dash.noCandidates', 'The engine returned no candidate materials.')}</p>
      </div>
    );
  }

  const focusedCandidate = ranked.find((c) => c.intervention_material === focused) ?? ranked[0];
  const comparedCandidates = compared.flatMap(({ id, slot }) => {
    const candidate = ranked.find((c) => c.intervention_material === id);
    return candidate ? [{ candidate, color: COMPARE_COLORS[slot] }] : [];
  });

  return (
    <div className="space-y-10">
      <div className="grid gap-8 lg:grid-cols-12 lg:items-start">
        <div className="lg:col-span-4">
          <AssumptionPanel material={material} />
        </div>
        <div className="lg:col-span-8">
          <MaterialRankingChart
            ranked={ranked}
            focused={focusedCandidate.intervention_material}
            colorOf={colorOf}
            onFocus={setFocused}
            onToggleCompare={toggleCompare}
          />
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-12 lg:items-start">
        <div className="lg:col-span-7">
          <MaterialComparisonChart materials={comparedCandidates} />
        </div>
        <div className="lg:col-span-5">
          <MaterialDetailPanel candidate={focusedCandidate} />
        </div>
      </div>
    </div>
  );
};

export default MaterialCompatibility;
