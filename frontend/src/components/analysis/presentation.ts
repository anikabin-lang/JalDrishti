/**
 * Presentation helpers for the Findings & Analysis dashboard. Everything here
 * orders, labels or restates values already present in the analysis payload;
 * nothing derives new engineering judgements.
 */

import {
  CandidateIntervention,
  CompatibilityDimensions,
  DetectionItem,
  RecommendationLevel,
  RestorationPhase,
  RootCauseItem,
} from '../../types';
import { BadgeVariant } from '../StatusBadge';

export const EXTENT_RANK: Record<string, number> = { severe: 3, moderate: 2, low: 1 };

export const EXTENT_BADGE: Record<string, BadgeVariant> = {
  severe: 'danger',
  moderate: 'ochre',
  low: 'jade',
};

/** Detection indices ordered by relative image-space extent, then coverage. */
export const rankDetections = (detections: DetectionItem[]): number[] =>
  detections
    .map((_, i) => i)
    .sort((a, b) => {
      const da = detections[a];
      const db = detections[b];
      const byExtent = (EXTENT_RANK[db.relative_severity ?? ''] ?? 0) - (EXTENT_RANK[da.relative_severity ?? ''] ?? 0);
      return byExtent !== 0 ? byExtent : db.coverage_ratio - da.coverage_ratio;
    });

export const URGENCY_RANK: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };

export const URGENCY_BADGE: Record<string, BadgeVariant> = {
  critical: 'danger',
  high: 'danger',
  medium: 'ochre',
  low: 'neutral',
};

/** Causes ordered by declared urgency; the engine's own order breaks ties. */
export const rankCauses = (causes: RootCauseItem[]): RootCauseItem[] =>
  causes
    .map((cause, i) => ({ cause, i }))
    .sort((a, b) => (URGENCY_RANK[b.cause.urgency ?? ''] ?? 0) - (URGENCY_RANK[a.cause.urgency ?? ''] ?? 0) || a.i - b.i)
    .map(({ cause }) => cause);

/**
 * Splits evidence rules into the rule chain (`Rule: A → B → C`) and the plain
 * evidence lines the engine measured. The chain is drawn exactly as written.
 */
export const splitEvidence = (rules: string[]): { chains: string[][]; evidence: string[] } => {
  const chains: string[][] = [];
  const evidence: string[] = [];
  rules.forEach((rule) => {
    const body = rule.replace(/^\s*rule\s*:\s*/i, '');
    const steps = body.split(/\s*(?:→|->)\s*/).filter(Boolean);
    if (steps.length >= 2) chains.push(steps);
    else evidence.push(rule);
  });
  return { chains, evidence };
};

export const RECOMMENDATION: Record<RecommendationLevel, { label: string; variant: BadgeVariant; bar: string }> = {
  strongly_recommended: { label: 'Strongly recommended', variant: 'jade', bar: 'bg-jade-400' },
  recommended: { label: 'Recommended', variant: 'jade', bar: 'bg-jade-400' },
  acceptable_conditional: { label: 'Conditional', variant: 'ochre', bar: 'bg-ochre-500' },
  prohibited_incompatible: { label: 'Incompatible', variant: 'danger', bar: 'bg-danger-500' },
};

export const isIncompatible = (c: CandidateIntervention) => c.recommendation === 'prohibited_incompatible';

export const rankMaterials = (candidates: CandidateIntervention[]): CandidateIntervention[] =>
  [...candidates].sort((a, b) => b.compatibility_score - a.compatibility_score);

export const DIMENSIONS: { key: keyof CompatibilityDimensions; label: string; meaning: string }[] = [
  { key: 'mechanical', label: 'Mechanical', meaning: 'Strength and stiffness relative to the original' },
  { key: 'moisture', label: 'Moisture', meaning: 'Vapour permeability and water behaviour' },
  { key: 'thermal', label: 'Thermal', meaning: 'Expansion under heating and cooling' },
  { key: 'chemical', label: 'Chemical', meaning: 'Salt and binder compatibility' },
  { key: 'reversibility', label: 'Reversibility', meaning: 'Can be removed without harming the original' },
  { key: 'heritage', label: 'Heritage', meaning: 'Consistency with traditional practice' },
  { key: 'visual', label: 'Visual', meaning: 'Colour and texture match' },
];

/** Validated categorical slots for the material comparison (dark ground, all six checks pass). */
export const COMPARE_COLORS = ['#3A9A7B', '#B98A2E', '#9A7BC0'];

/** Present dimensions, weakest first. */
export const dimensionExtremes = (c: CandidateIntervention) => {
  const present = DIMENSIONS.filter((d) => typeof c.compatibility_dimensions?.[d.key] === 'number').map((d) => ({
    ...d,
    value: c.compatibility_dimensions[d.key],
  }));
  const sorted = [...present].sort((a, b) => a.value - b.value);
  return { weakest: sorted[0], strongest: sorted[sorted.length - 1] };
};

/** `MECHANICAL MISMATCH: text` → { title: 'Mechanical mismatch', body: 'text' }. */
export const splitWarning = (warning: string): { title: string | null; body: string } => {
  const match = warning.match(/^([A-Z][A-Z &/'-]{3,}):\s*(.+)$/s);
  if (!match) return { title: null, body: warning };
  const title = match[1].trim().toLowerCase();
  return { title: title.charAt(0).toUpperCase() + title.slice(1), body: match[2] };
};

export const PHASES: { id: RestorationPhase; label: string }[] = [
  { id: 'phase_1_immediate_stabilization', label: 'Immediate stabilisation' },
  { id: 'phase_2_hydrological_remediation', label: 'Hydrological remediation' },
  { id: 'phase_3_masonry_and_iks_consolidation', label: 'Masonry and traditional consolidation' },
  { id: 'phase_4_long_term_monitoring', label: 'Long-term monitoring' },
];

export const ACTION_URGENCY_RANK: Record<string, number> = { immediate: 4, high: 3, medium: 2, routine: 1 };

export const ACTION_URGENCY_BADGE: Record<string, BadgeVariant> = {
  immediate: 'danger',
  high: 'ochre',
  medium: 'neutral',
  routine: 'jade',
};

export const PRACTICE_SEVERITY_BADGE: Record<string, BadgeVariant> = {
  destructive: 'danger',
  high_risk: 'danger',
  moderate_risk: 'ochre',
};
