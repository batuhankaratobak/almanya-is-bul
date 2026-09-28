import type {
  CandidateProfile,
  CvProfile,
  Job,
  JobFilters,
  JobListResponse,
  ManualPortalsResponse,
  ProfileSaveResponse,
  RefreshResponse,
  ApplyQueueResponse,
  SourcesResponse,
  StatsResponse,
} from "../types/api";

const API_BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    let detail = `İstek başarısız (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      }
    } catch {
      // keep generic message
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

function toQuery(filters: JobFilters): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const api = {
  getHealth: () => request<{ status: string; database: string }>("/health"),
  getStats: () => request<StatsResponse>("/stats"),
  getSources: () => request<SourcesResponse>("/sources"),
  getJobs: (filters: JobFilters = {}) =>
    request<JobListResponse>(`/jobs${toQuery(filters)}`),
  getJob: (id: number) => request<Job>(`/jobs/${id}`),
  updateJobStatus: (id: number, status: string) =>
    request<Job>(`/jobs/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  refreshJobs: () =>
    request<RefreshResponse>("/jobs/refresh", {
      method: "POST",
    }),
  getProfile: () => request<CandidateProfile>("/profile"),
  saveProfile: (profile: CandidateProfile) =>
    request<ProfileSaveResponse>("/profile", {
      method: "PUT",
      body: JSON.stringify(profile),
    }),
  getManualPortals: (markets?: string[]) => {
    const params = new URLSearchParams();
    (markets || []).forEach((market) => params.append("markets", market));
    const query = params.toString();
    return request<ManualPortalsResponse>(
      `/manual-portals${query ? `?${query}` : ""}`,
    );
  },
  getCvProfile: () => request<CvProfile>("/cv-profile"),
  saveCvProfile: (profile: CvProfile) =>
    request<CvProfile>("/cv-profile", {
      method: "PUT",
      body: JSON.stringify(profile),
    }),
  translateCvProfile: () =>
    request<CvProfile>("/cv-profile/translate", {
      method: "POST",
    }),
  getApplyQueue: (limit = 10, minScore = 70) =>
    request<ApplyQueueResponse>(
      `/apply-queue?limit=${limit}&min_score=${minScore}`,
    ),
  downloadTailoredCv: async (
    jobId: number,
    lang: "auto" | "en" | "de" = "auto",
  ) => {
    const params = new URLSearchParams({ lang });
    await downloadDocx(
      `/jobs/${jobId}/tailored-cv.docx?${params}`,
      `CV_${jobId}.docx`,
    );
  },
  downloadAnschreiben: async (
    jobId: number,
    lang: "auto" | "en" | "de" = "auto",
  ) => {
    const params = new URLSearchParams({ lang });
    await downloadDocx(
      `/jobs/${jobId}/anschreiben.docx?${params}`,
      `Anschreiben_${jobId}.docx`,
    );
  },
  downloadApplicationPack: async (
    jobId: number,
    lang: "auto" | "en" | "de" = "auto",
  ) => {
    await downloadDocx(
      `/jobs/${jobId}/tailored-cv.docx?${new URLSearchParams({ lang })}`,
      `CV_${jobId}.docx`,
    );
    await downloadDocx(
      `/jobs/${jobId}/anschreiben.docx?${new URLSearchParams({ lang })}`,
      `Anschreiben_${jobId}.docx`,
    );
  },
};

async function downloadDocx(path: string, fallbackName: string) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      Accept:
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
  });
  if (!response.ok) {
    throw new Error(`Word indirilemedi (${response.status})`);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = /filename="([^"]+)"/.exec(disposition);
  const filename = match?.[1] || fallbackName;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
