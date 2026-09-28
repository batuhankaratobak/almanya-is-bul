export type ApplicationStatus =
  | "new"
  | "reviewing"
  | "applied"
  | "interview"
  | "rejected"
  | "ignored"
  | "offer";

export type MatchCategory =
  | "Sehr passend"
  | "Gut passend"
  | "Möglich"
  | "Weniger passend"
  | string;

export type SourceDisplayStatus =
  | "active"
  | "error"
  | "not_implemented"
  | "disabled"
  | "idle"
  | string;

export interface SourceReference {
  source: string;
  source_job_id?: string | null;
  job_url: string;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  primary: boolean;
}

export interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  country?: string;
  description: string;
  primary_source: string;
  source_references: SourceReference[];
  job_url: string;
  application_url?: string | null;
  date_posted?: string | null;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  remote: boolean;
  hybrid: boolean;
  employment_type?: string | null;
  job_language?: string | null;
  german_requirement?: string | null;
  english_requirement?: string | null;
  experience_level?: string | null;
  category: string;
  role_family?: string | null;
  discovery_relevance?: string | null;
  match_score: number;
  match_category?: MatchCategory | null;
  status: ApplicationStatus | string;
  positive_reasons: string[];
  negative_reasons: string[];
  matched_skills?: string[];
  missing_skills?: string[];
}

export interface CandidateProfile {
  target_roles: string[];
  target_categories: string[];
  skills: string[];
  experience_areas: string[];
  education: string;
  german_level: string;
  english_level: string;
  preferred_max_experience_years: number;
  preferred_work_models: string[];
  preferred_locations: string[];
  unwanted_roles: string[];
}

export interface CvExperience {
  title: string;
  org: string;
  period: string;
  bullets: string[];
}

export interface CvProject {
  name: string;
  stack: string[];
  bullets: string[];
}

export interface CvEducation {
  school: string;
  degree: string;
  period: string;
  details?: string;
}

export interface CvLanguage {
  name: string;
  level: string;
}

export interface CvTranslationDe {
  source_fingerprint?: string;
  headline?: string;
  summary?: string;
  education?: CvEducation[];
  experiences?: CvExperience[];
  projects?: CvProject[];
}

export interface CvProfile {
  source_language?: string;
  full_name: string;
  email: string;
  phone: string;
  city: string;
  linkedin_or_github: string;
  headline: string;
  summary: string;
  education: CvEducation[];
  experiences: CvExperience[];
  projects: CvProject[];
  skills: string[];
  languages: CvLanguage[];
  translations?: {
    de?: CvTranslationDe;
  };
  translation_status?: string;
}

export interface ProfileSaveResponse {
  profile: CandidateProfile;
  rescore: {
    jobs_total: number;
    jobs_updated: number;
    profile_skills: number;
  };
}

export interface JobListResponse {
  items: Job[];
  total: number;
  limit: number;
  offset: number;
}

export interface StatsResponse {
  total_jobs: number;
  excellent_matches: number;
  good_matches: number;
  possible_matches: number;
  poor_matches: number;
  new: number;
  reviewing: number;
  applied: number;
  interviews: number;
  rejected: number;
  ignored: number;
  offers: number;
}

export interface SourceInfo {
  name: string;
  enabled: boolean;
  implemented: boolean;
  status: SourceDisplayStatus;
  last_error?: string | null;
  last_duration_seconds?: number | null;
}

export interface SourcesResponse {
  sources: SourceInfo[];
}

export interface SourceRefreshStat {
  status: string;
  jobs_found: number;
  error?: string | null;
  duration_seconds?: number;
}

export interface RefreshResponse {
  status: string;
  jobs_scanned: number;
  new_jobs: number;
  duplicates: number;
  updated_jobs: number;
  excellent_matches: number;
  duration_seconds?: number;
  sources: Record<string, SourceRefreshStat>;
}

export interface JobFilters {
  search?: string;
  category?: string;
  status?: string;
  language?: string;
  german_level?: string;
  work_model?: string;
  source?: string;
  min_score?: number;
  max_score?: number;
  location?: string;
  country?: string;
  limit?: number;
  offset?: number;
  sort?: "score" | "newest" | "oldest";
}

export interface ManualPortalLink {
  portal: string;
  market: string;
  label: string;
  query: string;
  url: string;
}

export interface ManualPortalsResponse {
  queries: string[];
  markets: string[];
  keyword_families: string[];
  portals: ManualPortalLink[];
}

export interface GermanyEssential {
  id: string;
  title: string;
  detail: string;
}

export interface ApplyQueueItem {
  id: number;
  title: string;
  company?: string | null;
  location?: string | null;
  match_score: number;
  match_category?: string | null;
  status: string;
  job_language?: string | null;
  suggested_lang: "en" | "de";
  application_url: string;
  source?: string | null;
  checklist: {
    lebenslauf: boolean;
    anschreiben: boolean;
    save_as_pdf: boolean;
    zeugnis_reminder: boolean;
  };
}

export interface OllamaStatus {
  enabled: boolean;
  running: boolean;
  model: string;
  model_ready?: boolean;
  models?: string[];
  detail?: string;
}

export interface ApplyQueueResponse {
  min_score: number;
  limit: number;
  total: number;
  germany_essentials: GermanyEssential[];
  ollama?: OllamaStatus;
  items: ApplyQueueItem[];
}
