import { useEffect, useState } from "react";
import { CATEGORY_OPTIONS } from "../lib/labels";
import { api } from "../services/api";
import type { CandidateProfile } from "../types/api";

interface CandidateProfileFormProps {
  onSaved?: () => void;
}

function listToText(values: string[]): string {
  return values.join(", ");
}

function textToList(value: string): string[] {
  return value
    .split(/[\n,;]+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

export function CandidateProfileForm({ onSaved }: CandidateProfileFormProps) {
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      setLoading(true);
      try {
        setProfile(await api.getProfile());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Profil yüklenemedi.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading || !profile) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-slate-500">Profil yükleniyor…</p>
      </section>
    );
  }

  const update = (patch: Partial<CandidateProfile>) => {
    setProfile({ ...profile, ...patch });
  };

  const toggleCategory = (value: string) => {
    const current = new Set(profile.target_categories);
    if (current.has(value)) current.delete(value);
    else current.add(value);
    update({ target_categories: Array.from(current) });
  };

  const toggleWorkModel = (value: string) => {
    const current = new Set(profile.preferred_work_models);
    if (current.has(value)) current.delete(value);
    else current.add(value);
    update({ preferred_work_models: Array.from(current) });
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.saveProfile(profile);
      setProfile(result.profile);
      setMessage(
        `Profil kaydedildi. ${result.rescore.jobs_total} ilan yeniden puanlandı (${result.rescore.jobs_updated} güncellendi).`,
      );
      onSaved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Profil kaydedilemedi.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <h2 className="text-base font-semibold text-slate-900">Aday Profilim</h2>
        <p className="mt-1 text-sm text-slate-600">
          Tek yerel profil. Kaydettiğinizde siteler yenilenmez; mevcut ilanlar
          yeniden puanlanır.
        </p>
      </div>

      {error && (
        <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>
      )}
      {message && (
        <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {message}
        </p>
      )}

      <Field
        label="Hedef Pozisyonlar"
        hint="Virgülle ayırın"
        value={listToText(profile.target_roles)}
        onChange={(value) => update({ target_roles: textToList(value) })}
      />

      <div>
        <p className="mb-2 text-sm font-medium text-slate-700">İş Alanları</p>
        <div className="flex flex-wrap gap-2">
          {CATEGORY_OPTIONS.filter((option) => option.value).map((option) => {
            const active = profile.target_categories.includes(option.value);
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => toggleCategory(option.value)}
                className={`rounded-lg border px-3 py-1.5 text-sm ${
                  active
                    ? "border-slate-900 bg-slate-900 text-white"
                    : "border-slate-300 bg-white text-slate-700"
                }`}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>

      <Field
        label="Yetkinlikler"
        hint="Python, SQL, React…"
        value={listToText(profile.skills)}
        onChange={(value) => update({ skills: textToList(value) })}
        rows={3}
      />
      <Field
        label="Deneyim Alanları"
        value={listToText(profile.experience_areas)}
        onChange={(value) => update({ experience_areas: textToList(value) })}
      />
      <Field
        label="Eğitim"
        value={profile.education}
        onChange={(value) => update({ education: value })}
      />

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Almanca Seviyesi</span>
          <select
            value={profile.german_level}
            onChange={(event) => update({ german_level: event.target.value })}
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
          >
            {["A1", "A2", "B1", "B2", "C1", "C2", "UNKNOWN"].map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">İngilizce Seviyesi</span>
          <select
            value={profile.english_level}
            onChange={(event) => update({ english_level: event.target.value })}
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
          >
            {["A1", "A2", "B1", "B2", "C1", "C2", "UNKNOWN"].map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="block text-sm">
        <span className="mb-1 block font-medium text-slate-700">
          Tercih Edilen Maksimum Deneyim (yıl)
        </span>
        <input
          type="number"
          min={0}
          max={15}
          value={profile.preferred_max_experience_years}
          onChange={(event) =>
            update({ preferred_max_experience_years: Number(event.target.value) || 0 })
          }
          className="w-full rounded-lg border border-slate-300 px-3 py-2"
        />
      </label>

      <div>
        <p className="mb-2 text-sm font-medium text-slate-700">
          Tercih Edilen Çalışma Modeli
        </p>
        <div className="flex flex-wrap gap-2">
          {[
            { value: "remote", label: "Uzaktan" },
            { value: "hybrid", label: "Hibrit" },
            { value: "onsite", label: "Ofisten" },
          ].map((option) => {
            const active = profile.preferred_work_models.includes(option.value);
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => toggleWorkModel(option.value)}
                className={`rounded-lg border px-3 py-1.5 text-sm ${
                  active
                    ? "border-slate-900 bg-slate-900 text-white"
                    : "border-slate-300 bg-white text-slate-700"
                }`}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </div>

      <Field
        label="Tercih Edilen Lokasyonlar"
        value={listToText(profile.preferred_locations)}
        onChange={(value) => update({ preferred_locations: textToList(value) })}
      />
      <Field
        label="İstenmeyen Pozisyonlar"
        hint="Senior, Lead…"
        value={listToText(profile.unwanted_roles)}
        onChange={(value) => update({ unwanted_roles: textToList(value) })}
      />

      <button
        type="button"
        onClick={() => void handleSave()}
        disabled={saving}
        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:bg-slate-400"
      >
        {saving ? "Kaydediliyor…" : "Profili Kaydet"}
      </button>
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
  hint,
  rows,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  hint?: string;
  rows?: number;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      {hint && <span className="mb-1 block text-xs text-slate-500">{hint}</span>}
      {rows && rows > 1 ? (
        <textarea
          value={value}
          rows={rows}
          onChange={(event) => onChange(event.target.value)}
          className="w-full rounded-lg border border-slate-300 px-3 py-2"
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="w-full rounded-lg border border-slate-300 px-3 py-2"
        />
      )}
    </label>
  );
}
