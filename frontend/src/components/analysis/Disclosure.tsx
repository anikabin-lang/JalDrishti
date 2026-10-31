import React, { useId, useState } from 'react';
import { Icon } from '../Icon';

export interface DisclosureProps {
  /** Always-visible row content. */
  summary: React.ReactNode;
  /** Right-aligned content in the summary row (badges, counts). */
  meta?: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  /** Hairline above the row; off when the parent already draws dividers. */
  rule?: boolean;
  className?: string;
}

/**
 * One expandable row. Collapsed content is kept in the DOM but made inert, and
 * the height change is a single grid-row transition, so opening never shifts
 * content above the row.
 */
export const Disclosure: React.FC<DisclosureProps> = ({ summary, meta, children, defaultOpen = false, rule = true, className = '' }) => {
  const [open, setOpen] = useState(defaultOpen);
  const id = useId();

  return (
    <div className={`${rule ? 'border-t border-ink-900/10' : ''} ${className}`}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        className="group flex w-full items-center gap-4 py-3 text-left text-sm text-ink-800 transition-colors duration-fast hover:text-ink-950"
      >
        <span className="min-w-0 flex-1">{summary}</span>
        {meta && <span className="flex shrink-0 flex-wrap items-center justify-end gap-2">{meta}</span>}
        <Icon
          name="arrowRight"
          className={`h-3.5 w-3.5 shrink-0 text-ink-500 transition-transform duration-fast group-hover:text-ink-800 motion-reduce:transition-none ${open ? 'rotate-90' : ''}`}
        />
      </button>
      <div
        id={id}
        role="region"
        className={`grid transition-[grid-template-rows] duration-base ease-out motion-reduce:transition-none ${open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}
        {...(open ? {} : { inert: '' })}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="pb-5 pt-1">{children}</div>
        </div>
      </div>
    </div>
  );
};

export default Disclosure;
