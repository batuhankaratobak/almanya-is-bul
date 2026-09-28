import type { ApplicationStatus, MatchCategory } from "../types/api";

export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  new: "Yeni",
  reviewing: "İnceleniyor",
  applied: "Başvuruldu",
  interview: "Mülakat",
  rejected: "Reddedildi",
  ignored: "Yoksayıldı",
  offer: "Teklif",
};

export const MATCH_LABELS: Record<string, string> = {
  "Mükemmel Eşleşme": "Mükemmel Eşleşme",
  "Çok Uygun": "Çok Uygun",
  Uygun: "Uygun",
  Olası: "Olası",
  "Düşük Uygunluk": "Düşük Uygunluk",
  // Legacy rows before recalibration
  "Sehr passend": "Çok Uygun",
  "Gut passend": "Uygun",
  Möglich: "Olası",
  "Weniger passend": "Düşük Uygunluk",
};

export const CATEGORY_OPTIONS = [
  { value: "", label: "Tümü" },
  { value: "software_development", label: "Yazılım" },
  { value: "it_support", label: "IT Destek" },
  { value: "system_infrastructure", label: "Sistem / Altyapı" },
  { value: "network", label: "Ağ" },
  { value: "cybersecurity", label: "Siber Güvenlik" },
  { value: "data_database", label: "Veri / Database" },
  { value: "bi_reporting", label: "BI / Raporlama" },
  { value: "decision_support", label: "Karar Destek" },
  { value: "business_analysis", label: "İş Analizi" },
  { value: "erp_sap_crm", label: "ERP / SAP / CRM" },
  { value: "cloud_devops", label: "Cloud / DevOps" },
  { value: "qa_testing", label: "QA / Test" },
  { value: "digital_transformation", label: "Dijital Dönüşüm / Otomasyon" },
  { value: "project_pmo", label: "Proje / PMO" },
  { value: "product", label: "Ürün" },
  { value: "operations", label: "Operasyon" },
  { value: "industrial_it", label: "Endüstriyel IT" },
  { value: "consulting_implementation", label: "Danışmanlık / Implementasyon" },
  { value: "planning_performance", label: "Planlama / Performans" },
  { value: "financial_analytics", label: "Analitik Finans" },
  { value: "supply_chain_analytics", label: "Supply Chain / Optimizasyon" },
  { value: "ai_ml", label: "AI / ML" },
  { value: "other_technical", label: "Diğer Teknik / Mühendislik" },
] as const;

export const LANGUAGE_OPTIONS = [
  { value: "", label: "Tümü" },
  { value: "de", label: "Almanca" },
  { value: "en", label: "İngilizce" },
  { value: "de/en", label: "Almanca + İngilizce" },
  { value: "unknown", label: "Bilinmiyor" },
] as const;

export const GERMAN_LEVEL_OPTIONS = [
  { value: "", label: "Tümü" },
  { value: "not_required", label: "Almanca gerekmiyor" },
  { value: "preferred", label: "Almanca tercih sebebi" },
  { value: "A1", label: "A1" },
  { value: "A2", label: "A2" },
  { value: "B1", label: "B1" },
  { value: "B2", label: "B2" },
  { value: "C1", label: "C1" },
  { value: "C2", label: "C2" },
] as const;

export const WORK_MODEL_OPTIONS = [
  { value: "", label: "Tümü" },
  { value: "onsite", label: "Ofisten" },
  { value: "hybrid", label: "Hibrit" },
  { value: "remote", label: "Uzaktan" },
] as const;

export const COUNTRY_OPTIONS = [
  { value: "", label: "Tümü" },
  { value: "DE", label: "Almanya" },
  { value: "CH", label: "İsviçre" },
  { value: "FR", label: "Fransa" },
  { value: "NL", label: "Hollanda" },
  { value: "EU", label: "Uzaktan / Avrupa" },
] as const;

export function countryLabel(code?: string | null): string {
  const match = COUNTRY_OPTIONS.find((option) => option.value === (code || ""));
  if (match && match.value) return match.label;
  return code || "—";
}

export const SORT_OPTIONS = [
  { value: "score", label: "En Uygun" },
  { value: "newest", label: "En Yeni" },
  { value: "oldest", label: "En Eski" },
] as const;

export const STATUS_FILTER_OPTIONS = [
  { value: "", label: "Tümü" },
  { value: "new", label: "Yeni" },
  { value: "reviewing", label: "İnceleniyor" },
  { value: "applied", label: "Başvuruldu" },
  { value: "interview", label: "Mülakat" },
  { value: "rejected", label: "Reddedildi" },
  { value: "ignored", label: "Yoksayıldı" },
  { value: "offer", label: "Teklif" },
] as const;

/** Exact score bands matching GET /stats counters. */
export const MATCH_BAND_OPTIONS = [
  { value: "", label: "Tümü", min: undefined, max: undefined },
  { value: "excellent", label: "Çok Uygun (80–100)", min: 80, max: 100 },
  { value: "good", label: "Uygun (70–79)", min: 70, max: 79 },
  { value: "possible", label: "Olası (55–69)", min: 55, max: 69 },
] as const;

const REASON_TRANSLATIONS: Record<string, string> = {
  "Junior / Berufseinsteiger": "Junior / Yeni Mezun Seviyesi",
  "Passender IT-Bereich": "Hedef IT alanıyla uyumlu",
  "0-2 Jahre Berufserfahrung": "0-2 yıl deneyim",
  "1-3 Jahre Berufserfahrung": "1-3 yıl deneyim",
  "Deutsch B1 ausreichend": "Almanca B1 yeterli",
  "Deutsch B2 ausreichend": "Almanca B2 yeterli",
  "Englisch akzeptiert": "İngilizce kabul ediliyor",
  "Hybrid verfügbar": "Hibrit çalışma mevcut",
  "Remote verfügbar": "Uzaktan çalışma mevcut",
  "Trainee- / Graduate-Programm": "Trainee / Graduate programı",
  "Passender Studienabschluss genannt": "Uygun bölüm/diploma belirtilmiş",
  "Senior-Niveau": "Senior seviye",
  "Lead-/Principal-Niveau": "Lead / Principal seviye",
  "5+ Jahre Berufserfahrung erforderlich": "5+ yıl deneyim zorunlu",
  "4+ Jahre Berufserfahrung erforderlich": "4+ yıl deneyim zorunlu",
  "3 Jahre Berufserfahrung gewünscht": "3+ yıl deneyim isteniyor",
  "Deutsch C1 verpflichtend": "Almanca C1 zorunlu",
  "Deutsch C2 verpflichtend": "Almanca C2 zorunlu",
  "Führungsverantwortung gefordert": "Yönetim sorumluluğu isteniyor",
  "Rolle außerhalb der Zielbereiche": "Hedef alanların dışında bir rol",
};

const EXPERIENCE_LABELS: Record<string, string> = {
  internship: "Staj",
  entry_level: "Giriş seviyesi",
  junior: "Junior",
  mid: "Orta seviye",
  senior: "Senior",
  lead: "Lead",
  unknown: "Bilinmiyor",
};

const EMPLOYMENT_LABELS: Record<string, string> = {
  full_time: "Tam zamanlı",
  part_time: "Yarı zamanlı",
  working_student: "Working student",
  internship: "Staj",
  apprenticeship: "Meslek eğitimi",
  temporary: "Geçici",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status as ApplicationStatus] ?? status;
}

export function matchLabel(category?: MatchCategory | null): string {
  if (!category) return "—";
  return MATCH_LABELS[category] ?? category;
}

export function languageLabel(language?: string | null): string {
  switch (language) {
    case "de":
      return "Almanca";
    case "en":
      return "İngilizce";
    case "de/en":
      return "Almanca + İngilizce";
    case "unknown":
      return "Bilinmiyor";
    default:
      return language || "—";
  }
}

export function workModelLabel(remote: boolean, hybrid: boolean): string {
  if (hybrid) return "Hibrit";
  if (remote) return "Uzaktan";
  return "Ofisten";
}

export function experienceLabel(level?: string | null): string {
  if (!level) return "—";
  return EXPERIENCE_LABELS[level] ?? level;
}

export function employmentLabel(type?: string | null): string {
  if (!type) return "—";
  return EMPLOYMENT_LABELS[type] ?? type;
}

export function germanRequirementLabel(value?: string | null): string {
  if (!value) return "—";
  const [level, status] = value.split("|");
  const levelText = !level || level === "null" ? "" : level;
  const statusText =
    status === "required"
      ? "zorunlu"
      : status === "preferred"
        ? "tercih"
        : status === "not_required"
          ? "gerekmiyor"
          : status === "unknown"
            ? "belirsiz"
            : status || "";
  if (levelText && statusText) return `${levelText} (${statusText})`;
  if (levelText) return levelText;
  if (statusText) return statusText;
  return value;
}

export function translateReason(reason: string): string {
  if (REASON_TRANSLATIONS[reason]) return REASON_TRANSLATIONS[reason];
  if (reason.startsWith("Deutsch ") && reason.endsWith(" ausreichend")) {
    const level = reason.replace("Deutsch ", "").replace(" ausreichend", "");
    return `Almanca ${level} yeterli`;
  }
  return reason;
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("tr-TR");
}

export function sourceStatusLabel(source: {
  enabled: boolean;
  implemented: boolean;
  status?: string;
}): string {
  switch (source.status) {
    case "active":
      return "Aktif";
    case "error":
      return "Hata";
    case "not_implemented":
      return "Henüz eklenmedi";
    case "disabled":
      return "Devre dışı";
    case "idle":
      // Implemented, but no successful live request recorded yet.
      // Not "Devre dışı" (that is only for explicitly disabled sources).
      return "Hata";
    default:
      break;
  }
  if (!source.enabled) return "Devre dışı";
  if (!source.implemented) return "Henüz eklenmedi";
  return "Hata";
}

export function sourceStatusTone(status?: string): string {
  switch (status) {
    case "active":
      return "bg-emerald-50 text-emerald-800";
    case "error":
      return "bg-rose-50 text-rose-800";
    case "disabled":
      return "bg-slate-100 text-slate-600";
    case "not_implemented":
      return "bg-amber-50 text-amber-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export function refreshSourceLabel(status: string): string {
  switch (status) {
    case "success":
      return "Başarılı";
    case "not_implemented":
      return "Henüz eklenmedi";
    case "disabled":
      return "Devre dışı";
    case "failed":
      return "Hata";
    default:
      return status;
  }
}

export function matchScoreTone(score: number): string {
  if (score >= 90) return "bg-emerald-50 text-emerald-800 ring-emerald-200";
  if (score >= 80) return "bg-emerald-50 text-emerald-800 ring-emerald-200";
  if (score >= 70) return "bg-sky-50 text-sky-800 ring-sky-200";
  if (score >= 55) return "bg-amber-50 text-amber-800 ring-amber-200";
  return "bg-slate-100 text-slate-700 ring-slate-200";
}

export function statusTone(status: string): string {
  switch (status) {
    case "applied":
      return "bg-blue-50 text-blue-800";
    case "interview":
      return "bg-violet-50 text-violet-800";
    case "offer":
      return "bg-emerald-50 text-emerald-800";
    case "rejected":
      return "bg-rose-50 text-rose-800";
    case "ignored":
      return "bg-slate-100 text-slate-600";
    case "reviewing":
      return "bg-amber-50 text-amber-800";
    default:
      return "bg-slate-50 text-slate-700";
  }
}
