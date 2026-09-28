import { sourceStatusLabel, sourceStatusTone } from "../lib/labels";
import type { SourceInfo } from "../types/api";

interface SourceStatusProps {
  sources: SourceInfo[];
  loading: boolean;
}

export function SourceStatus({ sources, loading }: SourceStatusProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-900">Kaynaklar</h2>
      <div className="mt-3 grid max-h-[28rem] grid-cols-1 gap-2 overflow-y-auto pr-1">
        {loading && (
          <p className="text-sm text-slate-500">Kaynaklar yükleniyor…</p>
        )}
        {!loading &&
          sources.map((source) => {
            const label = sourceStatusLabel(source);
            const tone = sourceStatusTone(source.status);
            return (
              <div
                key={source.name}
                className="flex min-w-0 items-start gap-2 rounded-lg border border-slate-100 px-3 py-2"
              >
                <span className="min-w-0 flex-1 break-words text-sm font-medium leading-snug text-slate-800">
                  {source.name}
                </span>
                <span
                  className={`shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-xs ${tone}`}
                >
                  {label}
                </span>
              </div>
            );
          })}
      </div>
    </section>
  );
}
