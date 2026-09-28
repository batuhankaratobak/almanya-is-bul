import {
  countryLabel,
  formatDate,
  matchLabel,
  matchScoreTone,
  statusLabel,
  statusTone,
} from "../lib/labels";
import type { ApplicationStatus, Job } from "../types/api";

const PIPELINE: Array<{ status: ApplicationStatus; label: string }> = [
  { status: "reviewing", label: "İnceleniyor" },
  { status: "applied", label: "Başvuruldu" },
  { status: "interview", label: "Mülakat" },
  { status: "offer", label: "Teklif" },
  { status: "rejected", label: "Reddedildi" },
];

interface ApplicationsPanelProps {
  jobs: Job[];
  loading: boolean;
  error: string | null;
  updatingId: number | null;
  onOpenDetails: (job: Job) => void;
  onStatusChange: (job: Job, status: ApplicationStatus) => void;
  onQuickApply: (job: Job) => void;
  onGoToJobs: () => void;
}

export function ApplicationsPanel({
  jobs,
  loading,
  error,
  updatingId,
  onOpenDetails,
  onStatusChange,
  onQuickApply,
  onGoToJobs,
}: ApplicationsPanelProps) {
  const pipelineJobs = jobs.filter((job) =>
    PIPELINE.some((item) => item.status === job.status),
  );

  if (loading) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm text-slate-500">Başvurular yükleniyor…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-xl border border-rose-200 bg-rose-50 p-5 shadow-sm">
        <p className="text-sm text-rose-800">{error}</p>
      </section>
    );
  }

  if (pipelineJobs.length === 0) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-900">Başvurular</h2>
        <p className="mt-2 text-sm text-slate-600">
          Henüz başvuru sürecinde ilan yok. İş İlanları’nda uygun olanları açıp
          başvur, sonra burada takip et.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          Otomatik başvuru yok — sen başvurusunu yaparsın, uygulama takip eder.
        </p>
        <button
          type="button"
          onClick={onGoToJobs}
          className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          İlanlara Git
        </button>
      </section>
    );
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-base font-semibold text-slate-900">Başvuru Takibi</h2>
        <p className="mt-1 text-sm text-slate-600">
          {pipelineJobs.length} ilan süreçte. Otomatik gönderim yok; durumu buradan güncelle.
        </p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          {PIPELINE.map((item) => {
            const count = pipelineJobs.filter((job) => job.status === item.status).length;
            return (
              <span
                key={item.status}
                className={`rounded-full px-2.5 py-1 font-medium ${statusTone(item.status)}`}
              >
                {item.label}: {count}
              </span>
            );
          })}
        </div>
      </section>

      {PIPELINE.map((column) => {
        const rows = pipelineJobs.filter((job) => job.status === column.status);
        if (rows.length === 0) return null;
        return (
          <section
            key={column.status}
            className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
          >
            <div className="border-b border-slate-100 px-4 py-2 text-sm font-semibold text-slate-800">
              {column.label} ({rows.length})
            </div>
            <ul className="divide-y divide-slate-100">
              {rows.map((job) => (
                <li key={job.id} className="px-4 py-3">
                  <div className="flex flex-wrap items-start gap-3">
                    <div
                      className={`shrink-0 rounded-lg px-2 py-1 text-xs font-semibold ring-1 ${matchScoreTone(job.match_score)}`}
                    >
                      {job.match_score} · {matchLabel(job.match_category)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <h3 className="text-sm font-semibold text-slate-900">{job.title}</h3>
                      <p className="mt-1 text-sm text-slate-600">
                        {job.company || "—"}
                        {job.location ? ` · ${job.location}` : ""}
                        {job.country ? ` · ${countryLabel(job.country)}` : ""}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {job.primary_source} · {formatDate(job.date_posted || job.first_seen_at)} ·{" "}
                        {statusLabel(job.status)}
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    <Action
                      label="İlanı Aç / Başvur"
                      disabled={!(job.application_url || job.job_url)}
                      onClick={() => onQuickApply(job)}
                    />
                    <Action label="Detay" onClick={() => onOpenDetails(job)} />
                    {column.status === "reviewing" && (
                      <Action
                        label="Başvuruldu"
                        loading={updatingId === job.id}
                        onClick={() => onStatusChange(job, "applied")}
                      />
                    )}
                    {column.status === "applied" && (
                      <Action
                        label="Mülakat"
                        loading={updatingId === job.id}
                        onClick={() => onStatusChange(job, "interview")}
                      />
                    )}
                    {column.status === "interview" && (
                      <Action
                        label="Teklif"
                        loading={updatingId === job.id}
                        onClick={() => onStatusChange(job, "offer")}
                      />
                    )}
                    {(column.status === "applied" ||
                      column.status === "interview" ||
                      column.status === "reviewing") && (
                      <Action
                        label="Red"
                        loading={updatingId === job.id}
                        onClick={() => onStatusChange(job, "rejected")}
                      />
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

function Action({
  label,
  onClick,
  disabled,
  loading,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      onClick={onClick}
      className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
    >
      {loading ? "…" : label}
    </button>
  );
}
