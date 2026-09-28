import {
  CATEGORY_OPTIONS,
  COUNTRY_OPTIONS,
  GERMAN_LEVEL_OPTIONS,
  LANGUAGE_OPTIONS,
  MATCH_BAND_OPTIONS,
  SORT_OPTIONS,
  STATUS_FILTER_OPTIONS,
  WORK_MODEL_OPTIONS,
} from "../lib/labels";
import type { JobFilters as Filters } from "../types/api";

interface JobFiltersProps {
  filters: Filters;
  sources: string[];
  onChange: (next: Filters) => void;
}

function matchBandValue(filters: Filters): string {
  const match = MATCH_BAND_OPTIONS.find(
    (option) =>
      option.min === filters.min_score && option.max === filters.max_score,
  );
  return match?.value ?? "";
}

export function JobFilters({ filters, sources, onChange }: JobFiltersProps) {
  const update = (patch: Partial<Filters>) => {
    onChange({ ...filters, ...patch, offset: 0 });
  };

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <label className="block text-sm md:col-span-2 xl:col-span-2">
          <span className="mb-1 block font-medium text-slate-700">Ara</span>
          <input
            type="search"
            value={filters.search ?? ""}
            onChange={(event) => update({ search: event.target.value })}
            placeholder="Pozisyon, şirket veya konum ara..."
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none ring-slate-400 focus:ring-2"
          />
        </label>

        <Select
          label="İş Alanı"
          value={filters.category ?? ""}
          onChange={(value) => update({ category: value || undefined })}
          options={CATEGORY_OPTIONS.map((o) => ({ ...o }))}
        />
        <Select
          label="Uygunluk"
          value={matchBandValue(filters)}
          onChange={(value) => {
            const band = MATCH_BAND_OPTIONS.find((option) => option.value === value);
            update({
              min_score: band?.min,
              max_score: band?.max,
            });
          }}
          options={MATCH_BAND_OPTIONS.map((o) => ({
            value: o.value,
            label: o.label,
          }))}
        />
        <Select
          label="Başvuru Durumu"
          value={filters.status ?? ""}
          onChange={(value) => update({ status: value || undefined })}
          options={STATUS_FILTER_OPTIONS.map((o) => ({ ...o }))}
        />
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Konum</span>
          <input
            type="text"
            value={filters.location ?? ""}
            onChange={(event) => update({ location: event.target.value })}
            placeholder="örn. Berlin"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none ring-slate-400 focus:ring-2"
          />
        </label>
        <Select
          label="Ülke"
          value={filters.country ?? ""}
          onChange={(value) => update({ country: value || undefined })}
          options={COUNTRY_OPTIONS.map((o) => ({ ...o }))}
        />
        <Select
          label="İlan Dili"
          value={filters.language ?? ""}
          onChange={(value) => update({ language: value || undefined })}
          options={LANGUAGE_OPTIONS.map((o) => ({ ...o }))}
        />
        <Select
          label="Almanca Seviyesi"
          value={filters.german_level ?? ""}
          onChange={(value) => update({ german_level: value || undefined })}
          options={GERMAN_LEVEL_OPTIONS.map((o) => ({ ...o }))}
        />
        <Select
          label="Çalışma Modeli"
          value={filters.work_model ?? ""}
          onChange={(value) => update({ work_model: value || undefined })}
          options={WORK_MODEL_OPTIONS.map((o) => ({ ...o }))}
        />
        <Select
          label="Kaynak"
          value={filters.source ?? ""}
          onChange={(value) => update({ source: value || undefined })}
          options={[
            { value: "", label: "Tümü" },
            ...sources.map((name) => ({ value: name, label: name })),
          ]}
        />
        <Select
          label="Sıralama"
          value={filters.sort ?? "score"}
          onChange={(value) =>
            update({ sort: (value as Filters["sort"]) || "score" })
          }
          options={SORT_OPTIONS.map((o) => ({ ...o }))}
        />
        <Select
          label="Sayfa Boyutu"
          value={String(filters.limit ?? 25)}
          onChange={(value) =>
            update({ limit: Number(value) || 25, offset: 0 })
          }
          options={[
            { value: "25", label: "25" },
            { value: "50", label: "50" },
            { value: "100", label: "100" },
          ]}
        />
      </div>
    </section>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none ring-slate-400 focus:ring-2"
      >
        {options.map((option) => (
          <option key={`${label}-${option.value}`} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
