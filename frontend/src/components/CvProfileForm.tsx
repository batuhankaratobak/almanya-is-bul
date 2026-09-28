import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { CvExperience, CvProfile, CvProject } from "../types/api";

interface CvProfileFormProps {
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

export function CvProfileForm({ onSaved }: CvProfileFormProps) {
  const [profile, setProfile] = useState<CvProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      setLoading(true);
      try {
        setProfile(await api.getCvProfile());
      } catch (err) {
        setError(err instanceof Error ? err.message : "CV profili yüklenemedi.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading || !profile) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-slate-500">CV profili yükleniyor…</p>
      </section>
    );
  }

  const update = (patch: Partial<CvProfile>) => {
    setProfile({ ...profile, ...patch });
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const saved = await api.saveCvProfile(profile);
      setProfile(saved);
      setMessage(
        "Kaydedildi ve Almanca çeviri güncellendi. Word indirmede ilan diline göre EN/DE seçilir.",
      );
      onSaved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "CV profili kaydedilemedi.");
    } finally {
      setSaving(false);
    }
  };

  const handleTranslate = async () => {
    setTranslating(true);
    setError(null);
    setMessage(null);
    try {
      const saved = await api.translateCvProfile();
      setProfile(saved);
      setMessage("Almanca çeviri yenilendi.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Çeviri yapılamadı.");
    } finally {
      setTranslating(false);
    }
  };

  const experienceText = (profile.experiences || [])
    .map((exp) => {
      const head = [exp.title, exp.org, exp.period].filter(Boolean).join(" | ");
      const bullets = (exp.bullets || []).map((b) => `- ${b}`).join("\n");
      return [head, bullets].filter(Boolean).join("\n");
    })
    .join("\n\n");

  const projectsText = (profile.projects || [])
    .map((project) => {
      const head = [project.name, (project.stack || []).join(", ")]
        .filter(Boolean)
        .join(" | ");
      const bullets = (project.bullets || []).map((b) => `- ${b}`).join("\n");
      return [head, bullets].filter(Boolean).join("\n");
    })
    .join("\n\n");

  const parseExperiences = (value: string): CvExperience[] => {
    const chunks = value
      .split(/\n\s*\n/)
      .map((chunk) => chunk.trim())
      .filter(Boolean);
    return chunks.map((chunk) => {
      const lines = chunk.split("\n").map((line) => line.trim()).filter(Boolean);
      const head = lines[0] || "";
      const bullets = lines
        .slice(1)
        .map((line) => line.replace(/^[-*•]\s*/, "").trim())
        .filter(Boolean);
      const parts = head.split("|").map((part) => part.trim());
      return {
        title: parts[0] || "",
        org: parts[1] || "",
        period: parts[2] || "",
        bullets,
      };
    });
  };

  const parseProjects = (value: string): CvProject[] => {
    const chunks = value
      .split(/\n\s*\n/)
      .map((chunk) => chunk.trim())
      .filter(Boolean);
    return chunks.map((chunk) => {
      const lines = chunk.split("\n").map((line) => line.trim()).filter(Boolean);
      const head = lines[0] || "";
      const bullets = lines
        .slice(1)
        .map((line) => line.replace(/^[-*•]\s*/, "").trim())
        .filter(Boolean);
      const parts = head.split("|").map((part) => part.trim());
      return {
        name: parts[0] || "",
        stack: parts[1] ? textToList(parts[1]) : [],
        bullets,
      };
    });
  };

  const deSummary = profile.translations?.de?.summary || "";

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-slate-900">A4 Başvuru CV’si</h2>
      <p className="mt-1 text-sm text-slate-600">
        Bunu bir kez <strong>İngilizce</strong> doldur (master CV). Kaydedince
        Almanca otomatik üretilir. Her ilanda “İlana özel CV” basınca sistem
        başlık, skill, deneyim ve projeleri o ilana göre otomatik seçer/sıralar.
      </p>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <Field
          label="Full name"
          value={profile.full_name}
          onChange={(value) => update({ full_name: value })}
        />
        <Field
          label="Email"
          value={profile.email}
          onChange={(value) => update({ email: value })}
        />
        <Field
          label="Phone"
          value={profile.phone}
          onChange={(value) => update({ phone: value })}
        />
        <Field
          label="City"
          value={profile.city}
          onChange={(value) => update({ city: value })}
        />
        <Field
          label="LinkedIn / GitHub"
          value={profile.linkedin_or_github}
          onChange={(value) => update({ linkedin_or_github: value })}
        />
        <Field
          label="Headline (EN)"
          value={profile.headline}
          onChange={(value) => update({ headline: value })}
        />
      </div>

      <label className="mt-3 block text-sm">
        <span className="mb-1 block font-medium text-slate-700">Summary (EN)</span>
        <textarea
          value={profile.summary}
          onChange={(event) => update({ summary: event.target.value })}
          rows={3}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none ring-slate-400 focus:ring-2"
        />
      </label>

      {deSummary ? (
        <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50/60 px-3 py-2">
          <p className="text-xs font-medium uppercase tracking-wide text-emerald-800">
            German preview (auto)
            {profile.translation_status
              ? ` · ${profile.translation_status}`
              : ""}
          </p>
          <p className="mt-1 text-sm text-slate-700">{deSummary}</p>
          {profile.translations?.de?.headline ? (
            <p className="mt-1 text-xs text-slate-500">
              {profile.translations.de.headline}
            </p>
          ) : null}
        </div>
      ) : null}

      <label className="mt-3 block text-sm">
        <span className="mb-1 block font-medium text-slate-700">
          Skills (comma-separated)
        </span>
        <textarea
          value={listToText(profile.skills || [])}
          onChange={(event) => update({ skills: textToList(event.target.value) })}
          rows={2}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none ring-slate-400 focus:ring-2"
        />
      </label>

      <label className="mt-3 block text-sm">
        <span className="mb-1 block font-medium text-slate-700">
          Experience (EN) — blank line between blocks; line1: Title | Org | Period
        </span>
        <textarea
          value={experienceText}
          onChange={(event) =>
            update({ experiences: parseExperiences(event.target.value) })
          }
          rows={7}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs outline-none ring-slate-400 focus:ring-2"
        />
      </label>

      <label className="mt-3 block text-sm">
        <span className="mb-1 block font-medium text-slate-700">
          Projects (EN) — blank line between blocks; line1: Name | stack1, stack2
        </span>
        <textarea
          value={projectsText}
          onChange={(event) =>
            update({ projects: parseProjects(event.target.value) })
          }
          rows={7}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs outline-none ring-slate-400 focus:ring-2"
        />
      </label>

      {message && <p className="mt-3 text-sm text-emerald-700">{message}</p>}
      {error && <p className="mt-3 text-sm text-rose-700">{error}</p>}

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={saving}
          onClick={() => void handleSave()}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {saving ? "Saving + translating…" : "Save (EN → DE auto)"}
        </button>
        <button
          type="button"
          disabled={translating}
          onClick={() => void handleTranslate()}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-50"
        >
          {translating ? "Translating…" : "Re-translate to German"}
        </button>
      </div>
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none ring-slate-400 focus:ring-2"
      />
    </label>
  );
}
