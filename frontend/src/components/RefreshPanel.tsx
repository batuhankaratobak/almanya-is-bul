import { refreshSourceLabel } from "../lib/labels";
import type { RefreshResponse } from "../types/api";

interface RefreshPanelProps {
  loading: boolean;
  result: RefreshResponse | null;
  error: string | null;
  onRefresh: () => void;
}

export function RefreshPanel({
  loading,
  result,
  error,
  onRefresh,
}: RefreshPanelProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">İlan Güncelleme</h2>
          <p className="mt-1 text-sm text-slate-500">
            Kayıtlı kaynaklardan ilanları kontrol eder.
          </p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {loading ? "İlanlar güncelleniyor..." : "İlanları Güncelle"}
        </button>
      </div>

      {error && (
        <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-4 space-y-3">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
            <SummaryItem label="Taranan İlan" value={result.jobs_scanned} />
            <SummaryItem label="Yeni İlan" value={result.new_jobs} />
            <SummaryItem label="Tekrarlanan" value={result.duplicates} />
            <SummaryItem label="Güncellenen" value={result.updated_jobs} />
            <SummaryItem label="Çok Uygun" value={result.excellent_matches} />
            <SummaryItem
              label="Süre"
              value={
                typeof result.duration_seconds === "number"
                  ? `${result.duration_seconds.toFixed(1)}s`
                  : "—"
              }
            />
          </div>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Kaynak Sonuçları
            </h3>
            <ul className="mt-2 space-y-1">
              {Object.entries(result.sources).map(([name, stat]) => (
                <li
                  key={name}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 px-3 py-2 text-sm"
                >
                  <span className="min-w-0 font-medium text-slate-800">{name}</span>
                  <span className="shrink-0 text-slate-600">
                    {refreshSourceLabel(stat.status)}
                    {stat.status === "success"
                      ? ` · ${stat.jobs_found} ilan`
                      : ""}
                    {typeof stat.duration_seconds === "number"
                      ? ` · ${stat.duration_seconds.toFixed(1)}s`
                      : ""}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
}

function SummaryItem({
  label,
  value,
}: {
  label: string;
  value: number | string;
}) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-900">{value}</p>
    </div>
  );
}
