import { Link } from 'react-router-dom';
import type { CaseSummary } from '../types';

/** Header control: which case (engagement) case-scoped pages show. "Manage" opens the Cases page. */
export default function CaseSwitcher({
  cases,
  current,
  onSelect,
}: {
  cases: CaseSummary[];
  current: CaseSummary | null;
  onSelect: (id: number) => void;
}) {
  if (cases.length === 0) return null;
  return (
    <div className="flex min-w-0 items-center gap-1.5">
      <label htmlFor="case-switcher" className="sr-only">
        Case
      </label>
      <select
        id="case-switcher"
        value={current?.id ?? ''}
        onChange={(e) => onSelect(Number(e.target.value))}
        className="w-36 truncate rounded-md sm:w-44 border border-line bg-surface px-2 py-1 text-xs text-fg focus:border-accent focus:outline-none"
        title={current ? `${current.title} · your role: ${current.my_role ?? '—'}` : 'Choose a case'}
      >
        {cases.map((c) => (
          <option key={c.id} value={c.id}>
            {c.title}
            {c.status === 'closed' ? ' (closed)' : ''}
          </option>
        ))}
      </select>
      {current?.my_role && <span className="hidden text-[11px] text-subtle xl:inline">{current.my_role}</span>}
      <Link to="/cases" className="hidden shrink-0 text-[11px] text-accent-soft hover:underline lg:inline">
        Manage
      </Link>
    </div>
  );
}
