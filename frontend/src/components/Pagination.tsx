interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
  onLimitChange?: (limit: number) => void;
}

export function Pagination({
  total,
  limit,
  offset,
  onChange,
  onLimitChange,
}: PaginationProps) {
  const page = Math.floor(offset / Math.max(limit, 1)) + 1;
  const totalPages = Math.max(1, Math.ceil(total / Math.max(limit, 1)));
  const canPrev = offset > 0;
  const canNext = offset + limit < total;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="space-y-1">
        <p className="text-sm font-medium text-slate-900">
          {total} ilan bulundu
        </p>
        <p className="text-sm text-slate-600">
          {total > 0 ? `${from}–${to} gösteriliyor · Sayfa ${page}/${totalPages}` : "Sayfa 0/0"}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {onLimitChange && (
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <span>Sayfa başına</span>
            <select
              value={limit}
              onChange={(event) => onLimitChange(Number(event.target.value))}
              className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm"
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </label>
        )}
        <button
          type="button"
          disabled={!canPrev}
          onClick={() => onChange(Math.max(0, offset - limit))}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Önceki
        </button>
        <button
          type="button"
          disabled={!canNext}
          onClick={() => onChange(offset + limit)}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Sonraki
        </button>
      </div>
    </div>
  );
}
