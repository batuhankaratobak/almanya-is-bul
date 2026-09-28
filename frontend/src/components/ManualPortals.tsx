import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { ManualPortalLink } from "../types/api";

export function ManualPortals() {
  const [portals, setPortals] = useState<ManualPortalLink[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void api
      .getManualPortals(["DE"])
      .then((response) => {
        if (cancelled) return;
        setPortals(response.portals);
        setQuery(response.queries[0] || "");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setPortals([]);
        setError(err instanceof Error ? err.message : "Manuel linkler yüklenemedi");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div>
        <h2 className="text-sm font-semibold text-slate-900">Almanya’da Dışarıda Ara</h2>
        <p className="mt-1 text-xs text-slate-600">
          StepStone, Indeed, LinkedIn, Glassdoor tarayıcıda açılır.
          {query ? ` Sorgu: ${query}` : ""}
        </p>
      </div>

      {loading && (
        <p className="mt-3 text-sm text-slate-500">Linkler hazırlanıyor…</p>
      )}
      {error && <p className="mt-3 text-sm text-rose-700">{error}</p>}
      {!loading && !error && (
        <div className="mt-3 flex flex-wrap gap-2">
          {portals.map((portal) => (
            <a
              key={`${portal.portal}-${portal.url}`}
              href={portal.url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-800 hover:bg-slate-50"
            >
              {portal.label}
            </a>
          ))}
        </div>
      )}
    </section>
  );
}
