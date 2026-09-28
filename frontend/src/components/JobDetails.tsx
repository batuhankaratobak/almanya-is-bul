import {
  countryLabel,
  employmentLabel,
  experienceLabel,
  formatDate,
  germanRequirementLabel,
  languageLabel,
  matchLabel,
  matchScoreTone,
  statusLabel,
  translateReason,
  workModelLabel,
} from "../lib/labels";
import { useState } from "react";
import { api } from "../services/api";
import type { Job } from "../types/api";

interface JobDetailsProps {
  job: Job | null;
  onClose: () => void;
  onQuickApply?: (job: Job) => void;
}

export function JobDetails({ job, onClose, onQuickApply }: JobDetailsProps) {
  const [docxLoading, setDocxLoading] = useState(false);
  const [letterLoading, setLetterLoading] = useState(false);
  const [packLoading, setPackLoading] = useState(false);
  const [docxError, setDocxError] = useState<string | null>(null);

  if (!job) return null;

  const handleDownloadDocx = async () => {
    setDocxLoading(true);
    setDocxError(null);
    try {
      await api.downloadTailoredCv(job.id);
    } catch (error) {
      setDocxError(
        error instanceof Error ? error.message : "Word indirilemedi.",
      );
    } finally {
      setDocxLoading(false);
    }
  };

  const handleDownloadLetter = async () => {
    setLetterLoading(true);
    setDocxError(null);
    try {
      await api.downloadAnschreiben(job.id);
    } catch (error) {
      setDocxError(
        error instanceof Error ? error.message : "Anschreiben indirilemedi.",
      );
    } finally {
      setLetterLoading(false);
    }
  };

  const handleDownloadPack = async () => {
    setPackLoading(true);
    setDocxError(null);
    try {
      await api.downloadApplicationPack(job.id);
    } catch (error) {
      setDocxError(
        error instanceof Error ? error.message : "Başvuru paketi indirilemedi.",
      );
    } finally {
      setPackLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4 sm:p-8">
      <div className="w-full max-w-3xl rounded-2xl bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{job.title}</h2>
            <p className="mt-1 text-sm text-slate-600">
              {job.company || "—"} · {job.location || "—"}
              {job.country ? ` · ${countryLabel(job.country)}` : ""}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          >
            Kapat
          </button>
        </div>

        <div className="space-y-6 px-5 py-5">
          <div className="grid gap-3 sm:grid-cols-2">
            <Detail
              label="Kaynak"
              value={
                job.source_references.length > 1
                  ? `${job.primary_source} (+${job.source_references.length - 1} kaynak)`
                  : job.primary_source
              }
            />
            <Detail
              label="Yayın Tarihi"
              value={formatDate(job.date_posted || job.first_seen_at)}
            />
            <Detail label="İlan Dili" value={languageLabel(job.job_language)} />
            <Detail
              label="Almanca Gereksinimi"
              value={germanRequirementLabel(job.german_requirement)}
            />
            <Detail
              label="İngilizce Gereksinimi"
              value={germanRequirementLabel(job.english_requirement)}
            />
            <Detail
              label="Deneyim Seviyesi"
              value={experienceLabel(job.experience_level)}
            />
            <Detail
              label="Çalışma Modeli"
              value={workModelLabel(job.remote, job.hybrid)}
            />
            <Detail
              label="Çalışma Türü"
              value={employmentLabel(job.employment_type)}
            />
            <Detail label="Durum" value={statusLabel(job.status)} />
            <Detail label="Ülke" value={countryLabel(job.country)} />
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Uygunluk Skoru
              </p>
              <div
                className={`mt-1 inline-flex rounded-lg px-2 py-1 text-sm font-semibold ring-1 ${matchScoreTone(job.match_score)}`}
              >
                {job.match_score} · {matchLabel(job.match_category)}
              </div>
            </div>
          </div>

          <section>
            <h3 className="text-sm font-semibold text-slate-900">Neden uygun?</h3>
            {job.positive_reasons.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">Olumlu gerekçe yok.</p>
            ) : (
              <ul className="mt-2 space-y-1">
                {job.positive_reasons.map((reason) => (
                  <li key={reason} className="text-sm text-emerald-800">
                    ✓ {translateReason(reason)}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h3 className="text-sm font-semibold text-slate-900">
              Dikkat Edilmesi Gerekenler
            </h3>
            {job.negative_reasons.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">Olumsuz gerekçe yok.</p>
            ) : (
              <ul className="mt-2 space-y-1">
                {job.negative_reasons.map((reason) => (
                  <li key={reason} className="text-sm text-amber-800">
                    ⚠ {translateReason(reason)}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {(job.matched_skills?.length || job.missing_skills?.length) && (
            <section className="grid gap-4 sm:grid-cols-2">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">Eşleşen Yetkinlikler</h3>
                <p className="mt-2 text-sm text-slate-700">
                  {(job.matched_skills || []).join(", ") || "—"}
                </p>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">Eksik Yetkinlikler</h3>
                <p className="mt-2 text-sm text-slate-700">
                  {(job.missing_skills || []).join(", ") || "—"}
                </p>
              </div>
            </section>
          )}

          <section>
            <h3 className="text-sm font-semibold text-slate-900">
              Orijinal İlan Açıklaması
            </h3>
            <div className="mt-2 max-h-80 overflow-y-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm leading-relaxed text-slate-800">
              {job.description?.trim()
                ? job.description
                : "Açıklama bulunamadı."}
            </div>
          </section>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!(job.application_url || job.job_url)}
              onClick={() => {
                if (onQuickApply) {
                  onQuickApply(job);
                  return;
                }
                window.open(
                  job.application_url || job.job_url,
                  "_blank",
                  "noopener,noreferrer",
                );
              }}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-40"
            >
              Başvur (ilanı aç)
            </button>
            <button
              type="button"
              disabled={docxLoading}
              onClick={() => void handleDownloadDocx()}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              {docxLoading ? "CV hazırlanıyor…" : "Lebenslauf (CV)"}
            </button>
            <button
              type="button"
              disabled={letterLoading}
              onClick={() => void handleDownloadLetter()}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              {letterLoading ? "Anschreiben…" : "Anschreiben"}
            </button>
            <button
              type="button"
              disabled={packLoading}
              onClick={() => void handleDownloadPack()}
              className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-900 hover:bg-emerald-100 disabled:opacity-40"
            >
              {packLoading ? "Paket…" : "CV + Anschreiben"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Kapat
            </button>
          </div>
          {docxError && (
            <p className="text-sm text-rose-700">{docxError}</p>
          )}
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-1 text-sm text-slate-900">{value}</p>
    </div>
  );
}
