import { useEffect, useState } from "react";
import { matchLabel } from "../lib/labels";
import { api } from "../services/api";
import type { ApplyQueueItem, ApplyQueueResponse, Job } from "../types/api";

interface ApplyTodayPanelProps {
  onOpenDetails: (job: Job) => void;
  onQuickApply: (job: Job) => void;
  onApplied?: () => void;
}

export function ApplyTodayPanel({
  onOpenDetails,
  onQuickApply,
  onApplied,
}: ApplyTodayPanelProps) {
  const [data, setData] = useState<ApplyQueueResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [checked, setChecked] = useState<Record<string, boolean>>(() => {
    try {
      return JSON.parse(localStorage.getItem("de_bewerbung_checklist") || "{}");
    } catch {
      return {};
    }
  });

  const reload = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.getApplyQueue(10, 70));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kuyruk yüklenemedi.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reload();
  }, []);

  const toggleCheck = (id: string) => {
    setChecked((prev) => {
      const next = { ...prev, [id]: !prev[id] };
      localStorage.setItem("de_bewerbung_checklist", JSON.stringify(next));
      return next;
    });
  };

  const handlePack = async (item: ApplyQueueItem) => {
    setBusyId(item.id);
    try {
      await api.downloadApplicationPack(item.id, item.suggested_lang || "auto");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Paket indirilemedi.");
    } finally {
      setBusyId(null);
    }
  };

  const handleApply = async (item: ApplyQueueItem) => {
    setBusyId(item.id);
    try {
      const job = await api.getJob(item.id);
      onQuickApply(job);
      onApplied?.();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Başvuru açılamadı.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Bugün Başvur
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Skoru yüksek ilanlar. Her biri için Lebenslauf + Anschreiben indir,
            PDF’ye çevir, başvur.
          </p>
          {data?.ollama && (
            <p className="mt-1 text-xs text-slate-500">
              {data.ollama.running && data.ollama.model_ready
                ? `Yerel Ollama hazır (${data.ollama.model}) — CV ve Anschreiben ilana göre yeniden yazılır.`
                : data.ollama.detail || "Yerel Ollama kapalı — kural tabanlı paket iner."}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => void reload()}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          Yenile
        </button>
      </div>

      {data?.germany_essentials && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50/70 p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">
            Almanya Bewerbung — olmazsa olmaz
          </p>
          <ul className="mt-2 space-y-2">
            {data.germany_essentials.map((item) => (
              <li key={item.id} className="flex gap-2 text-sm text-slate-800">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={Boolean(checked[item.id])}
                  onChange={() => toggleCheck(item.id)}
                />
                <div>
                  <p className="font-medium">{item.title}</p>
                  <p className="text-xs text-slate-600">{item.detail}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {loading && (
        <p className="mt-4 text-sm text-slate-500">Kuyruk yükleniyor…</p>
      )}
      {error && <p className="mt-4 text-sm text-rose-700">{error}</p>}

      {!loading && data && data.items.length === 0 && (
        <p className="mt-4 text-sm text-slate-600">
          70+ skorlu, henüz başvurulmamış uygun ilan yok. İlanları güncelle veya
          eşiği düşür.
        </p>
      )}

      {!loading && data && data.items.length > 0 && (
        <div className="mt-4 space-y-3">
          {data.items.map((item) => (
            <div
              key={item.id}
              className="rounded-lg border border-slate-200 p-3"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-slate-900">{item.title}</p>
                  <p className="text-sm text-slate-600">
                    {[item.company, item.location].filter(Boolean).join(" · ")}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {item.match_score} · {matchLabel(item.match_category)} · dil{" "}
                    {item.suggested_lang.toUpperCase()} · {item.source}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busyId === item.id}
                    onClick={() => void handlePack(item)}
                    className="rounded-md border border-slate-300 px-2.5 py-1.5 text-xs font-medium hover:bg-slate-50 disabled:opacity-50"
                  >
                    {busyId === item.id ? "…" : "CV + Anschreiben"}
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      void api.getJob(item.id).then(onOpenDetails)
                    }
                    className="rounded-md border border-slate-300 px-2.5 py-1.5 text-xs font-medium hover:bg-slate-50"
                  >
                    Detay
                  </button>
                  <button
                    type="button"
                    disabled={busyId === item.id}
                    onClick={() => void handleApply(item)}
                    className="rounded-md bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                  >
                    Başvur
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
