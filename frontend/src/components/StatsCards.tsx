import type { JobFilters, StatsResponse } from "../types/api";

interface StatsCardsProps {
  stats: StatsResponse | null;
  loading: boolean;
  onFilter?: (patch: Partial<JobFilters>) => void;
}

const CARDS: Array<{
  key: keyof StatsResponse;
  label: string;
  filter?: Partial<JobFilters>;
}> = [
  { key: "total_jobs", label: "Toplam İlan", filter: { min_score: undefined, max_score: undefined, status: undefined } },
  {
    key: "excellent_matches",
    label: "Çok Uygun",
    filter: { min_score: 80, max_score: 100, status: undefined },
  },
  {
    key: "good_matches",
    label: "Uygun",
    filter: { min_score: 70, max_score: 79, status: undefined },
  },
  {
    key: "possible_matches",
    label: "Olası",
    filter: { min_score: 55, max_score: 69, status: undefined },
  },
  {
    key: "new",
    label: "Yeni",
    filter: { status: "new", min_score: undefined, max_score: undefined },
  },
  {
    key: "applied",
    label: "Başvuruldu",
    filter: { status: "applied", min_score: undefined, max_score: undefined },
  },
  {
    key: "interviews",
    label: "Mülakat",
    filter: { status: "interview", min_score: undefined, max_score: undefined },
  },
  {
    key: "offers",
    label: "Teklif",
    filter: { status: "offer", min_score: undefined, max_score: undefined },
  },
];

export function StatsCards({ stats, loading, onFilter }: StatsCardsProps) {
  return (
    <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
      {CARDS.map((card) => {
        const clickable = Boolean(onFilter && card.filter);
        return (
          <article
            key={card.key}
            className={`rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm ${
              clickable
                ? "cursor-pointer transition hover:border-slate-300 hover:bg-slate-50"
                : ""
            }`}
            onClick={() => {
              if (clickable && card.filter) onFilter?.(card.filter);
            }}
            onKeyDown={(event) => {
              if (!clickable || !card.filter) return;
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onFilter?.(card.filter);
              }
            }}
            role={clickable ? "button" : undefined}
            tabIndex={clickable ? 0 : undefined}
          >
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {card.label}
            </p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">
              {loading || !stats ? "…" : stats[card.key]}
            </p>
          </article>
        );
      })}
    </section>
  );
}
