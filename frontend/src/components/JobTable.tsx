import { useState } from "react";
import {
  countryLabel,
  experienceLabel,
  formatDate,
  germanRequirementLabel,
  languageLabel,
  matchLabel,
  matchScoreTone,
  statusLabel,
  statusTone,
  workModelLabel,
} from "../lib/labels";
import { api } from "../services/api";
import type { ApplicationStatus, Job } from "../types/api";

interface JobTableProps {
  jobs: Job[];
  loading: boolean;
  error: string | null;
  updatingId: number | null;
  hasActiveFilters: boolean;
  resultCount?: number;
  onOpenDetails: (job: Job) => void;
  onStatusChange: (job: Job, status: ApplicationStatus) => void;
  onQuickApply?: (job: Job) => void;
  onRefresh: () => void;
}

export function JobTable({
  jobs,
  loading,
  error,
  updatingId,
  hasActiveFilters,
  resultCount,
  onOpenDetails,
  onStatusChange,
  onQuickApply,
  onRefresh,
}: JobTableProps) {
  const [docxId, setDocxId] = useState<number | null>(null);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white px-4 py-10 text-center text-sm text-slate-500 shadow-sm">
        İlanlar yükleniyor…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-8 text-center shadow-sm">
        <p className="text-sm font-medium text-rose-800">
          İlanlar yüklenirken bir hata oluştu.
        </p>
        <p className="mt-1 text-xs text-rose-700">{error}</p>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white px-4 py-10 text-center shadow-sm">
        <p className="text-sm font-medium text-slate-800">
          {hasActiveFilters
            ? "Bu filtrelere uygun ilan bulunamadı."
            : "Henüz iş ilanı bulunamadı."}
        </p>
        {!hasActiveFilters && (
          <button
            type="button"
            onClick={onRefresh}
            className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            İlanları Güncelle
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      {typeof resultCount === "number" && (
        <div className="border-b border-slate-100 px-4 py-2 text-sm text-slate-600">
          Bu sayfada {jobs.length} ilan · Filtre sonucu {resultCount}
        </div>
      )}
      <ul className="divide-y divide-slate-100">
        {jobs.map((job) => (
          <li key={job.id} className="px-4 py-4 hover:bg-slate-50/80">
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-start gap-3">
                <div
                  className={`shrink-0 rounded-lg px-2.5 py-1.5 text-xs font-semibold ring-1 ${matchScoreTone(job.match_score)}`}
                >
                  <div>{job.match_score}</div>
                  <div className="font-medium">{matchLabel(job.match_category)}</div>
                </div>

                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-semibold leading-snug text-slate-900 break-words">
                    {job.title}
                  </h3>
                  <p className="mt-1 text-sm text-slate-600 break-words">
                    {job.company || "—"}
                    {job.location ? ` · ${job.location}` : ""}
                    {job.country ? ` · ${countryLabel(job.country)}` : ""}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
                    <span>{job.primary_source}</span>
                    {job.source_references.length > 1 && (
                      <span>{job.source_references.length} kaynak</span>
                    )}
                    <span>{languageLabel(job.job_language)}</span>
                    <span>{germanRequirementLabel(job.german_requirement)}</span>
                    <span>{experienceLabel(job.experience_level)}</span>
                    <span>{workModelLabel(job.remote, job.hybrid)}</span>
                    <span>
                      {formatDate(job.date_posted || job.first_seen_at)}
                    </span>
                    {job.status !== "new" && (
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 font-medium ${statusTone(job.status)}`}
                      >
                        {statusLabel(job.status)}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap gap-1.5">
                <ActionButton
                  label="Başvur"
                  disabled={!(job.application_url || job.job_url)}
                  loading={updatingId === job.id}
                  primary
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
                    onStatusChange(job, "applied");
                  }}
                />
                <ActionButton
                  label="Detaylar"
                  onClick={() => onOpenDetails(job)}
                />
                <ActionButton
                  label="İlana özel CV"
                  loading={docxId === job.id}
                  onClick={() => {
                    setDocxId(job.id);
                    void api
                      .downloadTailoredCv(job.id)
                      .catch(() => undefined)
                      .finally(() => setDocxId(null));
                  }}
                />
                <ActionButton
                  label="İncele"
                  loading={updatingId === job.id}
                  onClick={() => onStatusChange(job, "reviewing")}
                />
                <ActionButton
                  label="Yoksay"
                  loading={updatingId === job.id}
                  onClick={() => onStatusChange(job, "ignored")}
                />
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ActionButton({
  label,
  onClick,
  disabled,
  loading,
  primary,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
  primary?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      onClick={onClick}
      className={
        primary
          ? "rounded-md bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
          : "rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
      }
    >
      {loading ? "…" : label}
    </button>
  );
}
