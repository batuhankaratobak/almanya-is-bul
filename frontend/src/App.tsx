import { useCallback, useEffect, useMemo, useState } from "react";
import { ApplicationsPanel } from "./components/ApplicationsPanel";
import { ApplyTodayPanel } from "./components/ApplyTodayPanel";
import { CandidateProfileForm } from "./components/CandidateProfileForm";
import { CvProfileForm } from "./components/CvProfileForm";
import { JobDetails } from "./components/JobDetails";
import { JobFilters } from "./components/JobFilters";
import { JobTable } from "./components/JobTable";
import { ManualPortals } from "./components/ManualPortals";
import { Pagination } from "./components/Pagination";
import { RefreshPanel } from "./components/RefreshPanel";
import { SourceStatus } from "./components/SourceStatus";
import { StatsCards } from "./components/StatsCards";
import { api } from "./services/api";
import type {
  ApplicationStatus,
  Job,
  JobFilters as Filters,
  RefreshResponse,
  SourceInfo,
  StatsResponse,
} from "./types/api";

type NavKey = "dashboard" | "jobs" | "applications" | "settings";

const NAV_ITEMS: Array<{ key: NavKey; label: string }> = [
  { key: "dashboard", label: "Özet" },
  { key: "jobs", label: "İlanlar" },
  { key: "applications", label: "Başvurular" },
  { key: "settings", label: "Profil" },
];

const DEFAULT_FILTERS: Filters = {
  limit: 25,
  offset: 0,
  sort: "score",
};

function App() {
  const [nav, setNav] = useState<NavKey>("jobs");
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [refreshLoading, setRefreshLoading] = useState(false);
  const [refreshResult, setRefreshResult] = useState<RefreshResponse | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [applicationJobs, setApplicationJobs] = useState<Job[]>([]);
  const [applicationsLoading, setApplicationsLoading] = useState(false);
  const [applicationsError, setApplicationsError] = useState<string | null>(null);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedSearch(filters.search?.trim() ?? "");
    }, 300);
    return () => window.clearTimeout(handle);
  }, [filters.search]);

  const queryFilters = useMemo(
    () => ({
      ...filters,
      search: debouncedSearch || undefined,
    }),
    [filters, debouncedSearch],
  );

  const pageTitle = useMemo(
    () => NAV_ITEMS.find((item) => item.key === nav)?.label ?? "İş İlanları",
    [nav],
  );

  const checkHealth = useCallback(async () => {
    try {
      await api.getHealth();
      setApiOnline(true);
    } catch {
      setApiOnline(false);
    }
  }, []);

  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      setStats(await api.getStats());
    } catch {
      setStats(null);
    } finally {
      setStatsLoading(false);
    }
  }, []);

  const loadSources = useCallback(async () => {
    setSourcesLoading(true);
    try {
      const response = await api.getSources();
      setSources(response.sources);
    } catch {
      setSources([]);
    } finally {
      setSourcesLoading(false);
    }
  }, []);

  const loadJobs = useCallback(async () => {
    setJobsLoading(true);
    setJobsError(null);
    try {
      const response = await api.getJobs(queryFilters);
      setJobs(response.items);
      setTotal(response.total);
    } catch (error) {
      setJobs([]);
      setTotal(0);
      setJobsError(
        error instanceof Error
          ? error.message
          : "İlanlar yüklenirken bir hata oluştu.",
      );
    } finally {
      setJobsLoading(false);
    }
  }, [queryFilters]);

  useEffect(() => {
    void checkHealth();
    void loadStats();
    void loadSources();
  }, [checkHealth, loadStats, loadSources]);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  const loadApplications = useCallback(async () => {
    setApplicationsLoading(true);
    setApplicationsError(null);
    try {
      const statuses: ApplicationStatus[] = [
        "reviewing",
        "applied",
        "interview",
        "offer",
        "rejected",
      ];
      const pages = await Promise.all(
        statuses.map((status) =>
          api.getJobs({ status, limit: 100, offset: 0, sort: "newest" }),
        ),
      );
      const merged = pages.flatMap((page) => page.items);
      const unique = new Map<number, Job>();
      merged.forEach((job) => unique.set(job.id, job));
      setApplicationJobs(
        Array.from(unique.values()).sort(
          (a, b) => (b.match_score || 0) - (a.match_score || 0),
        ),
      );
    } catch (error) {
      setApplicationJobs([]);
      setApplicationsError(
        error instanceof Error
          ? error.message
          : "Başvurular yüklenirken bir hata oluştu.",
      );
    } finally {
      setApplicationsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (nav === "applications") {
      void loadApplications();
    }
  }, [nav, loadApplications]);

  const hasActiveFilters = Boolean(
    filters.search ||
      filters.category ||
      filters.status ||
      filters.language ||
      filters.german_level ||
      filters.work_model ||
      filters.source ||
      filters.min_score !== undefined ||
      filters.max_score !== undefined ||
      filters.location ||
      filters.country,
  );

  const handleRefresh = async () => {
    setRefreshLoading(true);
    setRefreshError(null);
    try {
      await checkHealth();
      const result = await api.refreshJobs();
      setRefreshResult(result);
      await Promise.all([loadJobs(), loadStats(), loadSources()]);
    } catch (error) {
      setRefreshError(
        error instanceof Error
          ? error.message
          : "İlanlar güncellenirken bir hata oluştu.",
      );
    } finally {
      setRefreshLoading(false);
    }
  };

  const handleStatusChange = async (job: Job, status: ApplicationStatus) => {
    setUpdatingId(job.id);
    try {
      const updated = await api.updateJobStatus(job.id, status);
      setJobs((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setApplicationJobs((current) => {
        const pipeline = new Set([
          "reviewing",
          "applied",
          "interview",
          "offer",
          "rejected",
        ]);
        if (!pipeline.has(updated.status)) {
          return current.filter((item) => item.id !== updated.id);
        }
        const exists = current.some((item) => item.id === updated.id);
        if (!exists) return [...current, updated];
        return current.map((item) => (item.id === updated.id ? updated : item));
      });
      if (selectedJob?.id === updated.id) {
        setSelectedJob(updated);
      }
      await loadStats();
    } catch (error) {
      setJobsError(
        error instanceof Error
          ? error.message
          : "Durum güncellenirken bir hata oluştu.",
      );
    } finally {
      setUpdatingId(null);
    }
  };

  const handleQuickApply = async (job: Job) => {
    const url = job.application_url || job.job_url;
    if (url) {
      window.open(url, "_blank", "noopener,noreferrer");
    }
    if (job.status !== "applied" && job.status !== "interview" && job.status !== "offer") {
      await handleStatusChange(job, "applied");
    }
  };

  const handleStatsFilter = (patch: Partial<Filters>) => {
    setNav("jobs");
    setFilters((current) => ({
      ...current,
      ...patch,
      offset: 0,
      limit: current.limit ?? 25,
      sort: current.sort ?? "score",
    }));
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-[1500px] flex-col bg-slate-100 shadow-2xl">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
            <div>
              <h1 className="text-xl font-semibold tracking-tight">
                Germany Job Hunter
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                {pageTitle}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <ConnectionBadge apiOnline={apiOnline} />
              <button
                type="button"
                onClick={() => void handleRefresh()}
                disabled={refreshLoading}
                className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {refreshLoading ? "Güncelleniyor" : "İlanları Güncelle"}
              </button>
            </div>
          </div>

          <nav className="flex gap-2 overflow-x-auto px-4 pb-4 sm:px-6 lg:px-8">
            {NAV_ITEMS.map((item) => {
              const active = nav === item.key;
              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setNav(item.key)}
                  className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                    active
                      ? "bg-slate-900 text-white"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </nav>
        </header>

        <div className="min-w-0 flex-1">
          {!apiOnline && apiOnline !== null && (
            <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 sm:px-6 lg:px-8">
              Backend bağlantısı kapalı görünüyor. Diğer terminalde{" "}
              <code className="rounded bg-amber-100 px-1.5 py-0.5">
                uvicorn app.main:app --reload
              </code>{" "}
              çalışıyor olmalı.
            </div>
          )}

          <main className="mx-auto max-w-7xl space-y-4 px-4 py-6 sm:px-6 lg:px-8">
            {(nav === "dashboard" || nav === "jobs") && (
              <>
                <StatsCards
                  stats={stats}
                  loading={statsLoading}
                  onFilter={handleStatsFilter}
                />
                <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
                  <div className="space-y-4">
                    <ApplyTodayPanel
                      onOpenDetails={setSelectedJob}
                      onQuickApply={(job) => void handleQuickApply(job)}
                      onApplied={() => {
                        void loadStats();
                        void loadJobs();
                        void loadApplications();
                      }}
                    />
                    <RefreshPanel
                      loading={refreshLoading}
                      result={refreshResult}
                      error={refreshError}
                      onRefresh={() => void handleRefresh()}
                    />
                    <ManualPortals />
                  </div>
                  <SourceStatus sources={sources} loading={sourcesLoading} />
                </div>
              </>
            )}

            {nav === "dashboard" && (
              <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-base font-semibold">Öne çıkan ilanlar</h2>
                    <p className="mt-1 text-sm text-slate-600">
                      En yüksek skorlu ilanları hızlıca gözden geçir.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    onClick={() => setNav("jobs")}
                  >
                    Tüm ilanları aç
                  </button>
                </div>
                <div className="mt-4">
                  <JobTable
                    jobs={jobs.slice(0, 5)}
                    loading={jobsLoading}
                    error={jobsError}
                    updatingId={updatingId}
                    hasActiveFilters={hasActiveFilters}
                    resultCount={Math.min(5, total)}
                    onOpenDetails={setSelectedJob}
                    onStatusChange={(job, status) =>
                      void handleStatusChange(job, status)
                    }
                    onQuickApply={(job) => void handleQuickApply(job)}
                    onRefresh={() => void handleRefresh()}
                  />
                </div>
              </section>
            )}

            {nav === "jobs" && (
              <>
                <JobFilters
                  filters={filters}
                  sources={sources.map((source) => source.name)}
                  onChange={setFilters}
                />
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm font-medium text-slate-700">
                    {total} ilan bulundu
                  </p>
                  {hasActiveFilters && (
                    <button
                      type="button"
                      className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                      onClick={() => setFilters(DEFAULT_FILTERS)}
                    >
                      Filtreleri Temizle
                    </button>
                  )}
                </div>
                <JobTable
                  jobs={jobs}
                  loading={jobsLoading}
                  error={jobsError}
                  updatingId={updatingId}
                  hasActiveFilters={hasActiveFilters}
                  resultCount={total}
                  onOpenDetails={setSelectedJob}
                  onStatusChange={(job, status) =>
                    void handleStatusChange(job, status)
                  }
                  onQuickApply={(job) => void handleQuickApply(job)}
                  onRefresh={() => void handleRefresh()}
                />
                <Pagination
                  total={total}
                  limit={filters.limit ?? 25}
                  offset={filters.offset ?? 0}
                  onChange={(offset) =>
                    setFilters((current) => ({ ...current, offset }))
                  }
                  onLimitChange={(limit) =>
                    setFilters((current) => ({ ...current, limit, offset: 0 }))
                  }
                />
              </>
            )}

            {nav === "applications" && (
              <ApplicationsPanel
                jobs={applicationJobs}
                loading={applicationsLoading}
                error={applicationsError}
                updatingId={updatingId}
                onOpenDetails={setSelectedJob}
                onStatusChange={(job, status) => void handleStatusChange(job, status)}
                onQuickApply={(job) => void handleQuickApply(job)}
                onGoToJobs={() => setNav("jobs")}
              />
            )}

            {nav === "settings" && (
              <div className="space-y-4">
                <CvProfileForm />
                <CandidateProfileForm
                  onSaved={() => {
                    void loadJobs();
                    void loadStats();
                  }}
                />
              </div>
            )}
          </main>
        </div>
      </div>

      <JobDetails
        job={selectedJob}
        onClose={() => setSelectedJob(null)}
        onQuickApply={(job) => void handleQuickApply(job)}
      />
    </div>
  );
}

function ConnectionBadge({ apiOnline }: { apiOnline: boolean | null }) {
  const label =
    apiOnline === null ? "Kontrol ediliyor" : apiOnline ? "Backend aktif" : "Backend kapalı";
  const tone =
    apiOnline === null
      ? "border-slate-700 bg-slate-900 text-slate-300"
      : apiOnline
        ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
        : "border-amber-400/30 bg-amber-400/10 text-amber-200";

  return (
    <div className={`rounded-lg border px-3 py-2 text-sm font-medium ${tone}`}>
      {label}
    </div>
  );
}

export default App;
