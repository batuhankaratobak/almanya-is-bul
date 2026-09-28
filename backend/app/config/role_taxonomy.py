"""Centralized multilingual role taxonomy for discovery + classification.

Search terms, classification, and UI filter groups all derive from this module.
Do not scatter role keywords across source adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class RoleFamily:
    id: str
    filter_group: str
    label_tr: str
    titles_en: Tuple[str, ...] = ()
    titles_de: Tuple[str, ...] = ()
    titles_tr: Tuple[str, ...] = ()
    skills: Tuple[str, ...] = ()
    responsibilities: Tuple[str, ...] = ()
    degrees: Tuple[str, ...] = ()
    related: Tuple[str, ...] = ()
    enabled: bool = True
    # Base discovery weight when this family matches (high|medium).
    default_discovery: str = "high"


@dataclass(frozen=True)
class FilterGroup:
    id: str
    label_tr: str
    # Countries/markets this group is intended for (classification itself is global).
    markets: Tuple[str, ...] = ("de", "tr")


FILTER_GROUPS: Tuple[FilterGroup, ...] = (
    FilterGroup("software_development", "Yazılım"),
    FilterGroup("it_support", "IT Destek"),
    FilterGroup("system_infrastructure", "Sistem / Altyapı"),
    FilterGroup("network", "Ağ"),
    FilterGroup("cybersecurity", "Siber Güvenlik"),
    FilterGroup("data_database", "Veri / Database"),
    FilterGroup("bi_reporting", "BI / Raporlama"),
    FilterGroup("decision_support", "Karar Destek"),
    FilterGroup("business_analysis", "İş Analizi"),
    FilterGroup("erp_sap_crm", "ERP / SAP / CRM"),
    FilterGroup("cloud_devops", "Cloud / DevOps"),
    FilterGroup("qa_testing", "QA / Test"),
    FilterGroup("digital_transformation", "Dijital Dönüşüm / Otomasyon"),
    FilterGroup("project_pmo", "Proje / PMO"),
    FilterGroup("product", "Ürün"),
    FilterGroup("operations", "Operasyon"),
    FilterGroup("industrial_it", "Endüstriyel IT"),
    FilterGroup("consulting_implementation", "Danışmanlık / Implementasyon"),
    FilterGroup("planning_performance", "Planlama / Performans"),
    FilterGroup("financial_analytics", "Analitik Finans"),
    FilterGroup("supply_chain_analytics", "Supply Chain / Optimizasyon"),
    FilterGroup("ai_ml", "AI / ML"),
    FilterGroup("other_technical", "Diğer Teknik / Mühendislik"),
    # Legacy aliases kept for existing profile/API values.
    FilterGroup("system_administration", "Sistem Yönetimi"),
    FilterGroup("application_support", "Uygulama Desteği"),
    FilterGroup("it_consulting", "IT Danışmanlık"),
)

# Map legacy / alias filter groups onto canonical ones for matching.
FILTER_GROUP_ALIASES: Dict[str, str] = {
    "system_administration": "system_infrastructure",
    "application_support": "erp_sap_crm",
    "it_consulting": "consulting_implementation",
}


def _f(
    id: str,
    group: str,
    label_tr: str,
    *,
    en: Sequence[str] = (),
    de: Sequence[str] = (),
    tr: Sequence[str] = (),
    skills: Sequence[str] = (),
    resp: Sequence[str] = (),
    degrees: Sequence[str] = (),
    related: Sequence[str] = (),
    discovery: str = "high",
) -> RoleFamily:
    return RoleFamily(
        id=id,
        filter_group=group,
        label_tr=label_tr,
        titles_en=tuple(en),
        titles_de=tuple(de),
        titles_tr=tuple(tr),
        skills=tuple(skills),
        responsibilities=tuple(resp),
        degrees=tuple(degrees),
        related=tuple(related),
        default_discovery=discovery,
    )


COMMON_CS_DEGREES = (
    "computer engineering",
    "computer science",
    "software engineering",
    "information technology",
    "informatics",
    "informatik",
    "wirtschaftsinformatik",
    "information systems",
    "management information systems",
    "bilgisayar mühendisliği",
    "yazılım mühendisliği",
    "bilişim sistemleri",
    "yönetim bilişim sistemleri",
)

SOFTWARE_SKILLS = (
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "node.js",
    "sql",
    "git",
    "docker",
    "api",
    "rest",
    "c++",
    "c#",
    ".net",
)

ROLE_FAMILIES: Tuple[RoleFamily, ...] = (
    # --- Software / Development ---
    _f(
        "software_engineering",
        "software_development",
        "Yazılım Mühendisliği",
        en=("software engineer", "software developer", "software development"),
        de=("softwareentwickler", "software engineer", "entwicklungsingenieur software"),
        tr=("yazılım mühendisi", "yazılım geliştirici"),
        skills=SOFTWARE_SKILLS,
        resp=("software development", "application development", "coding", "programmieren", "yazılım geliştirme"),
        degrees=COMMON_CS_DEGREES,
        related=("backend_development", "frontend_development", "fullstack_development"),
    ),
    _f(
        "frontend_development",
        "software_development",
        "Frontend",
        en=("frontend developer", "frontend engineer", "front-end developer", "ui developer"),
        de=("frontend entwickler", "frontend developer", "frontendentwickler"),
        tr=("frontend geliştirici", "ön yüz geliştirici"),
        skills=("react", "angular", "vue", "javascript", "typescript", "html", "css"),
        resp=("frontend", "user interface", "web ui"),
    ),
    _f(
        "backend_development",
        "software_development",
        "Backend",
        en=("backend developer", "backend engineer", "back-end developer"),
        de=("backend entwickler", "backend developer", "backendentwickler"),
        tr=("backend geliştirici", "arka yüz geliştirici"),
        skills=("python", "java", "node.js", "sql", "fastapi", "spring", "api"),
        resp=("backend", "server-side", "api development", "microservices"),
    ),
    _f(
        "fullstack_development",
        "software_development",
        "Full Stack",
        en=("full stack developer", "fullstack developer", "full-stack engineer"),
        de=("full stack entwickler", "fullstack entwickler", "full-stack developer"),
        tr=("full stack geliştirici", "fullstack geliştirici"),
        skills=SOFTWARE_SKILLS,
        resp=("full stack", "frontend and backend"),
    ),
    _f(
        "web_development",
        "software_development",
        "Web Geliştirme",
        en=("web developer", "web engineer", "web development"),
        de=("webentwickler", "web developer", "web entwicklung"),
        tr=("web geliştirici", "web yazılımcı"),
        skills=("javascript", "html", "css", "react", "php"),
        resp=("web development", "website development", "web uygulamaları"),
    ),
    _f(
        "mobile_development",
        "software_development",
        "Mobil Geliştirme",
        en=("mobile developer", "android developer", "ios developer", "mobile engineer"),
        de=("mobile entwickler", "android entwickler", "ios entwickler"),
        tr=("mobil geliştirici", "android geliştirici", "ios geliştirici"),
        skills=("kotlin", "swift", "react native", "flutter", "android", "ios"),
        resp=("mobile development", "mobile app", "mobil uygulama"),
    ),
    _f(
        "application_development",
        "software_development",
        "Uygulama Geliştirme",
        en=("application developer", "application engineer", "app developer"),
        de=("anwendungsentwickler", "applikationsentwickler", "anwendungsentwicklung"),
        tr=("uygulama geliştirici", "uygulama yazılımcısı"),
        skills=SOFTWARE_SKILLS,
        resp=("application development", "anwendungsentwicklung", "uygulama geliştirme"),
    ),
    _f(
        "api_development",
        "software_development",
        "API Geliştirme",
        en=("api developer", "api engineer"),
        de=("api entwickler", "schnittstellenentwickler"),
        tr=("api geliştirici",),
        skills=("api", "rest", "graphql", "openapi"),
        resp=("api development", "api integration", "schnittstellen"),
    ),
    _f(
        "software_architecture",
        "software_development",
        "Yazılım Mimarisi",
        en=("software architect", "solution architect", "systems architect"),
        de=("softwarearchitekt", "lösungsarchitekt"),
        tr=("yazılım mimarı", "çözüm mimarı"),
        skills=("architecture", "microservices", "cloud"),
        resp=("software architecture", "system design"),
        discovery="medium",
    ),
    _f(
        "software_integration",
        "software_development",
        "Yazılım Entegrasyonu",
        en=("integration engineer", "integration specialist", "systems integration engineer"),
        de=("integrationsingenieur", "systemintegration", "schnittstellen"),
        tr=("entegrasyon mühendisi", "sistem entegrasyonu"),
        skills=("api", "etl", "middleware", "esb"),
        resp=("system integration", "api integration", "integration"),
    ),
    _f(
        "software_implementation",
        "consulting_implementation",
        "Yazılım İmplementasyonu",
        en=("implementation engineer", "implementation specialist"),
        de=("implementierungsspezialist", "implementierungsingenieur"),
        tr=("implementasyon uzmanı",),
        skills=("erp", "sap", "crm", "configuration"),
        resp=("implementation", "implementierung", "rollout"),
    ),
    _f(
        "embedded_software",
        "software_development",
        "Gömülü Yazılım",
        en=("embedded software engineer", "embedded developer", "embedded systems engineer"),
        de=("embedded software", "embedded entwickler", "firmwareentwickler"),
        tr=("gömülü yazılım", "gömülü sistemler"),
        skills=("c", "c++", "rtos", "microcontroller", "firmware"),
        resp=("embedded software", "firmware", "real-time"),
    ),
    _f(
        "firmware",
        "software_development",
        "Firmware",
        en=("firmware engineer", "firmware developer"),
        de=("firmware engineer", "firmwareentwickler"),
        tr=("firmware mühendisi",),
        skills=("c", "c++", "firmware"),
        resp=("firmware development", "firmware"),
    ),
    _f(
        "computer_vision",
        "ai_ml",
        "Bilgisayarlı Görü",
        en=("computer vision engineer", "vision engineer"),
        de=("computer vision", "bildverarbeitung"),
        tr=("bilgisayarlı görü", "görüntü işleme mühendisi"),
        skills=("opencv", "python", "deep learning", "tensorflow", "pytorch"),
        resp=("computer vision", "image recognition", "görüntü işleme"),
    ),
    _f(
        "image_processing",
        "ai_ml",
        "Görüntü İşleme",
        en=("image processing engineer", "image processing specialist"),
        de=("bildverarbeitungsingenieur", "bildverarbeitung"),
        tr=("görüntü işleme uzmanı",),
        skills=("opencv", "python", "matlab"),
        resp=("image processing", "bildverarbeitung"),
    ),
    _f(
        "game_development",
        "software_development",
        "Oyun Geliştirme",
        en=("game developer", "game engineer", "unity developer"),
        de=("game developer", "spieleentwickler"),
        tr=("oyun geliştirici",),
        skills=("unity", "unreal", "c#", "c++"),
        resp=("game development", "spieleentwicklung"),
        discovery="medium",
    ),
    # --- IT Support / Systems ---
    _f(
        "it_support",
        "it_support",
        "IT Destek",
        en=("it support", "it specialist", "it support specialist", "technical support"),
        de=("it support", "it-support", "it mitarbeiter", "technischer support", "it techniker"),
        tr=("it destek", "bilgi işlem uzmanı", "teknik destek uzmanı", "sistem destek uzmanı"),
        skills=("windows", "active directory", "office 365", "ticketing", "hardware"),
        resp=("technical support", "user support", "incident", "anwendersupport", "kullanıcı desteği"),
        degrees=COMMON_CS_DEGREES,
    ),
    _f(
        "technical_support",
        "it_support",
        "Teknik Destek",
        en=("technical support specialist", "technical support engineer"),
        de=("technischer supporter", "technischer support"),
        tr=("teknik destek",),
        skills=("windows", "linux", "networking"),
        resp=("technical support", "troubleshooting", "ticket"),
    ),
    _f(
        "help_desk",
        "it_support",
        "Help Desk",
        en=("help desk", "helpdesk analyst", "help desk specialist"),
        de=("helpdesk", "help desk"),
        tr=("yardım masası",),
        skills=("servicenow", "jira", "windows"),
        resp=("help desk", "service requests", "first level support"),
    ),
    _f(
        "service_desk",
        "it_support",
        "Service Desk",
        en=("service desk", "service desk analyst"),
        de=("service desk", "servicedesk"),
        tr=("servis masası",),
        skills=("itil", "ticketing"),
        resp=("service desk", "incident management"),
    ),
    _f(
        "desktop_support",
        "it_support",
        "Desktop Destek",
        en=("desktop support", "endpoint support", "workplace support"),
        de=("desktop support", "client support", "arbeitsplatzbetreuung"),
        tr=("masaüstü destek", "uç nokta destek"),
        skills=("windows", "macos", "intune", "sccm"),
        resp=("desktop support", "client management"),
    ),
    _f(
        "application_support",
        "application_support",
        "Uygulama Desteği",
        en=("application support", "application support engineer", "application specialist"),
        de=("anwendungsbetreuer", "applikationsbetreuer", "anwendungssupport"),
        tr=("uygulama destek uzmanı", "uygulama uzmanı"),
        skills=("sql", "erp", "sap", "crm"),
        resp=("application support", "anwendungsbetreuung", "uygulama desteği"),
        related=("erp", "sap", "crm"),
    ),
    _f(
        "system_administration",
        "system_infrastructure",
        "Sistem Yönetimi",
        en=("system administrator", "sysadmin", "it administrator"),
        de=("systemadministrator", "it-administrator", "fachinformatiker systemintegration"),
        tr=("sistem yöneticisi", "sistem uzmanı"),
        skills=("linux", "windows server", "active directory", "powershell", "virtualization"),
        resp=("system administration", "server administration", "systemverwaltung"),
    ),
    _f(
        "system_engineering",
        "system_infrastructure",
        "Sistem Mühendisliği",
        en=("system engineer", "systems engineer", "it system engineer"),
        de=("systemingenieur", "system engineer"),
        tr=("sistem mühendisi",),
        skills=("linux", "networking", "virtualization", "monitoring"),
        resp=("system engineering", "infrastructure"),
    ),
    _f(
        "network_administration",
        "network",
        "Ağ Yönetimi",
        en=("network administrator", "network admin"),
        de=("netzwerkadministrator", "netzwerk admin"),
        tr=("ağ yöneticisi", "network uzmanı"),
        skills=("tcp/ip", "cisco", "firewall", "vpn", "switching"),
        resp=("network administration", "netzwerkadministration", "ağ yönetimi"),
    ),
    _f(
        "network_engineering",
        "network",
        "Ağ Mühendisliği",
        en=("network engineer", "network specialist"),
        de=("netzwerkingenieur", "network engineer"),
        tr=("ağ mühendisi",),
        skills=("routing", "switching", "firewall", "lan", "wan"),
        resp=("network engineering", "netzwerk"),
    ),
    _f(
        "it_infrastructure",
        "system_infrastructure",
        "IT Altyapı",
        en=("infrastructure engineer", "it infrastructure", "infra engineer"),
        de=("it-infrastruktur", "infrastruktur engineer"),
        tr=("it altyapı", "altyapı uzmanı"),
        skills=("vmware", "hyper-v", "storage", "backup", "linux"),
        resp=("infrastructure", "infrastruktur", "altyapı"),
    ),
    _f(
        "it_operations",
        "operations",
        "IT Operasyon",
        en=("it operations", "it operations specialist", "ops engineer"),
        de=("it-betrieb", "it operations"),
        tr=("it operasyon", "teknik operasyon uzmanı"),
        skills=("monitoring", "linux", "incident", "on-call"),
        resp=("it operations", "operations support", "betrieb"),
    ),
    _f(
        "workplace_it",
        "it_support",
        "Workplace IT",
        en=("workplace it", "end user computing", "euc specialist"),
        de=("workplace it", "endgerätebetreuung"),
        tr=("işyeri bilişim",),
        skills=("intune", "office 365", "windows"),
        resp=("workplace", "end user computing"),
    ),
    _f(
        "field_it_support",
        "it_support",
        "Saha IT Destek",
        en=("field it support", "field technician", "onsite it support"),
        de=("vor-ort-support", "field service it"),
        tr=("saha destek", "yerinde it destek"),
        skills=("hardware", "networking", "windows"),
        resp=("onsite support", "field support"),
        discovery="medium",
    ),
    # --- Cybersecurity ---
    _f(
        "cybersecurity",
        "cybersecurity",
        "Siber Güvenlik",
        en=("cyber security", "cybersecurity", "cyber security analyst", "security analyst"),
        de=("cyber security", "cybersicherheit", "it-sicherheit", "informationssicherheit"),
        tr=("siber güvenlik", "siber güvenlik uzmanı", "bilgi güvenliği"),
        skills=("siem", "soc", "firewall", "vulnerability", "incident response"),
        resp=("information security", "security monitoring", "threat"),
        degrees=COMMON_CS_DEGREES,
    ),
    _f(
        "soc",
        "cybersecurity",
        "SOC",
        en=("soc analyst", "security operations center", "soc engineer"),
        de=("soc analyst", "security operations"),
        tr=("soc analisti",),
        skills=("siem", "splunk", "qradar", "edr"),
        resp=("security operations", "alert triage", "incident response"),
    ),
    _f(
        "security_engineering",
        "cybersecurity",
        "Güvenlik Mühendisliği",
        en=("security engineer", "security engineering"),
        de=("security engineer", "sicherheitsingenieur"),
        tr=("güvenlik mühendisi",),
        skills=("iam", "cloud security", "hardening"),
        resp=("security engineering", "secure configuration"),
    ),
    _f(
        "grc",
        "cybersecurity",
        "GRC / Uyum",
        en=("grc analyst", "grc specialist", "it compliance", "isms specialist", "it auditor", "it risk analyst"),
        de=("grc", "isms", "it-compliance", "it-revision", "informationssicherheitsbeauftragter"),
        tr=("grc uzmanı", "bilgi güvenliği uyum", "it denetçi"),
        skills=("iso 27001", "nist", "risk", "audit", "policy"),
        resp=("governance", "compliance", "risk management", "isms"),
        discovery="medium",
    ),
    _f(
        "identity_access_management",
        "cybersecurity",
        "IAM",
        en=("iam analyst", "identity and access management", "identity access management"),
        de=("iam", "identitätsmanagement", "berechtigungsmanagement"),
        tr=("kimlik ve erişim yönetimi", "iam uzmanı"),
        skills=("active directory", "azure ad", "okta", "rbac"),
        resp=("access management", "identity", "berechtigungen"),
    ),
    _f(
        "vulnerability_management",
        "cybersecurity",
        "Zafiyet Yönetimi",
        en=("vulnerability management", "vulnerability analyst"),
        de=("vulnerability management", "schwachstellenmanagement"),
        tr=("zafiyet yönetimi",),
        skills=("nessus", "qualys", "cve"),
        resp=("vulnerability scanning", "patch management"),
    ),
    # --- Data / BI ---
    _f(
        "data_analysis",
        "data_database",
        "Veri Analizi",
        en=("data analyst", "data analysis specialist"),
        de=("datenanalyst", "data analyst", "datenanalyse"),
        tr=("veri analisti", "veri analizi uzmanı"),
        skills=("sql", "python", "excel", "tableau", "power bi"),
        resp=("data analysis", "datenanalyse", "veri analizi", "reporting"),
        degrees=COMMON_CS_DEGREES + ("statistics", "mathematics"),
    ),
    _f(
        "data_engineering",
        "data_database",
        "Veri Mühendisliği",
        en=("data engineer", "data engineering"),
        de=("data engineer", "dateningenieur"),
        tr=("veri mühendisi",),
        skills=("sql", "python", "spark", "etl", "airflow", "kafka"),
        resp=("data pipelines", "etl", "data warehouse"),
    ),
    _f(
        "database_administration",
        "data_database",
        "Veritabanı Yönetimi",
        en=("database administrator", "dba", "database engineer"),
        de=("datenbankadministrator", "datenbankadministratorin", "dba"),
        tr=("veritabanı uzmanı", "veritabanı yöneticisi"),
        skills=("sql", "postgresql", "mysql", "oracle", "mssql"),
        resp=("database management", "datenbank", "backup recovery"),
    ),
    _f(
        "database_development",
        "data_database",
        "Veritabanı Geliştirme",
        en=("sql developer", "database developer"),
        de=("sql entwickler", "datenbankentwickler"),
        tr=("sql geliştirici", "veritabanı geliştirici"),
        skills=("sql", "t-sql", "pl/sql", "etl"),
        resp=("database development", "stored procedures"),
    ),
    _f(
        "business_intelligence",
        "bi_reporting",
        "İş Zekası",
        en=("bi analyst", "bi developer", "business intelligence specialist", "business intelligence"),
        de=("business intelligence", "bi entwickler", "bi analyst"),
        tr=("iş zekası uzmanı", "bi uzmanı"),
        skills=("power bi", "tableau", "sql", "ssis", "ssrs", "dax"),
        resp=("business intelligence", "dashboard", "reporting", "kpi"),
    ),
    _f(
        "reporting",
        "bi_reporting",
        "Raporlama",
        en=("reporting specialist", "reporting analyst", "management reporting"),
        de=("reporting specialist", "berichtswesen", "management reporting"),
        tr=("raporlama uzmanı", "raporlama analisti"),
        skills=("sql", "power bi", "excel", "sap"),
        resp=("reporting", "dashboard creation", "berichtswesen", "raporlama"),
    ),
    _f(
        "data_management",
        "data_database",
        "Veri Yönetimi",
        en=("data management", "data governance", "master data", "master data specialist"),
        de=("datenmanagement", "master data", "stammdaten"),
        tr=("veri yönetimi", "ana veri uzmanı"),
        skills=("sql", "mdm", "data quality"),
        resp=("data governance", "master data", "data quality"),
        discovery="medium",
    ),
    _f(
        "data_science",
        "ai_ml",
        "Veri Bilimi",
        en=("data scientist", "data science"),
        de=("data scientist", "datenwissenschaftler"),
        tr=("veri bilimci",),
        skills=("python", "machine learning", "statistics", "pandas"),
        resp=("predictive modeling", "statistical analysis"),
    ),
    _f(
        "machine_learning",
        "ai_ml",
        "Makine Öğrenmesi",
        en=("machine learning engineer", "ml engineer", "ai engineer", "ai engineering"),
        de=("machine learning engineer", "ki engineer"),
        tr=("makine öğrenmesi mühendisi", "yapay zeka mühendisi"),
        skills=("python", "tensorflow", "pytorch", "mlops"),
        resp=("machine learning", "model training", "yapay zeka"),
    ),
    # --- Decision support / BA ---
    _f(
        "decision_support",
        "decision_support",
        "Karar Destek",
        en=(
            "decision support",
            "decision support specialist",
            "decision support analyst",
            "decision support junior",
            "decision scientist",
        ),
        de=("decision support", "entscheidungsunterstützung"),
        tr=("karar destek uzmanı", "karar destek analisti", "karar destek"),
        skills=("sql", "power bi", "excel", "python", "sap", "tableau"),
        resp=(
            "decision support",
            "business case analysis",
            "performance analysis",
            "reporting",
            "dashboard",
            "karar destek",
        ),
        degrees=COMMON_CS_DEGREES + ("industrial engineering", "business analytics"),
        related=("business_analytics", "reporting", "business_intelligence"),
    ),
    _f(
        "business_analytics",
        "decision_support",
        "İş Analitiği",
        en=("business analytics", "business analytics specialist", "business performance analyst", "performance analyst"),
        de=("business analytics", "business performance"),
        tr=("iş analitiği uzmanı", "performans analisti"),
        skills=("sql", "power bi", "python", "excel"),
        resp=("business analytics", "performance analysis", "kpi analysis"),
    ),
    _f(
        "management_information",
        "decision_support",
        "Yönetim Bilgi Sistemleri",
        en=("mis specialist", "management information systems", "management information"),
        de=("management information", "führungsinformationssystem"),
        tr=("yönetim bilgi sistemleri uzmanı", "ybs uzmanı"),
        skills=("sql", "reporting", "erp", "excel"),
        resp=("management reporting", "mis", "information systems"),
    ),
    _f(
        "business_analysis",
        "business_analysis",
        "İş Analizi",
        en=("business analyst", "it business analyst", "requirements analyst"),
        de=("business analyst", "it business analyst", "anforderungsanalyst"),
        tr=("iş analisti", "iş analizi uzmanı"),
        skills=("sql", "jira", "confluence", "uml", "bpmn"),
        resp=("requirements analysis", "stakeholder", "anforderungsanalyse", "iş analizi"),
        degrees=COMMON_CS_DEGREES,
    ),
    _f(
        "system_analysis",
        "business_analysis",
        "Sistem Analizi",
        en=("systems analyst", "system analyst"),
        de=("systemanalytiker", "system analyst"),
        tr=("sistem analisti",),
        skills=("uml", "sql", "requirements"),
        resp=("system analysis", "requirements", "process modeling"),
    ),
    _f(
        "process_analysis",
        "business_analysis",
        "Süreç Analizi",
        en=(
            "process analyst",
            "process improvement specialist",
            "business process specialist",
            "business process management",
        ),
        de=("prozessanalyst", "prozessmanager", "prozessoptimierung"),
        tr=("süreç analisti", "süreç geliştirme uzmanı", "iş süreçleri uzmanı"),
        skills=("bpmn", "lean", "six sigma", "visio"),
        resp=("process analysis", "process improvement", "continuous improvement", "prozessanalyse"),
        discovery="medium",
    ),
    # --- ERP / SAP / CRM ---
    _f(
        "erp",
        "erp_sap_crm",
        "ERP",
        en=("erp specialist", "erp support", "erp consultant", "junior erp consultant"),
        de=("erp specialist", "erp berater", "erp betreuer"),
        tr=("erp uzmanı", "erp danışmanı"),
        skills=("erp", "sql", "sap"),
        resp=("erp support", "erp implementation", "enterprise applications"),
    ),
    _f(
        "sap",
        "erp_sap_crm",
        "SAP",
        en=("sap specialist", "sap support", "sap consultant", "sap application specialist"),
        de=("sap berater", "sap betreuer", "sap specialist", "sap beratung"),
        tr=("sap uzmanı", "sap danışmanı"),
        skills=("sap", "abap", "fiori", "hana"),
        resp=("sap support", "sap implementation", "sap customization"),
    ),
    _f(
        "crm",
        "erp_sap_crm",
        "CRM",
        en=("crm specialist", "crm support", "crm consultant"),
        de=("crm specialist", "crm berater"),
        tr=("crm uzmanı",),
        skills=("salesforce", "dynamics", "crm"),
        resp=("crm support", "customer relationship"),
    ),
    _f(
        "enterprise_applications",
        "erp_sap_crm",
        "Kurumsal Uygulamalar",
        en=("enterprise applications", "business applications", "application consulting"),
        de=("unternehmensanwendungen", "business applications"),
        tr=("kurumsal uygulamalar", "iş uygulamaları"),
        skills=("erp", "sap", "crm"),
        resp=("application specialist", "anwendungsbetreuung"),
    ),
    # --- Cloud / DevOps ---
    _f(
        "cloud_engineering",
        "cloud_devops",
        "Cloud",
        en=("cloud engineer", "junior cloud engineer", "cloud operations"),
        de=("cloud engineer", "cloud architekt"),
        tr=("cloud mühendisi", "bulut mühendisi"),
        skills=("aws", "azure", "gcp", "terraform", "kubernetes"),
        resp=("cloud", "infrastructure as code", "cloud operations"),
    ),
    _f(
        "devops",
        "cloud_devops",
        "DevOps",
        en=("devops engineer", "junior devops engineer", "devops specialist"),
        de=("devops engineer", "devops spezialist"),
        tr=("devops mühendisi",),
        skills=("ci/cd", "docker", "kubernetes", "jenkins", "git"),
        resp=("ci/cd", "deployment", "automation", "release"),
    ),
    _f(
        "platform_engineering",
        "cloud_devops",
        "Platform",
        en=("platform engineer", "platform engineering"),
        de=("platform engineer",),
        tr=("platform mühendisi",),
        skills=("kubernetes", "terraform", "observability"),
        resp=("platform engineering", "developer platform"),
    ),
    _f(
        "site_reliability",
        "cloud_devops",
        "SRE",
        en=("site reliability engineer", "sre"),
        de=("site reliability engineer",),
        tr=("sre", "güvenilirlik mühendisi"),
        skills=("monitoring", "kubernetes", "python", "linux"),
        resp=("reliability", "observability", "on-call"),
        discovery="medium",
    ),
    _f(
        "release_engineering",
        "cloud_devops",
        "Release",
        en=("release engineer", "release engineering", "deployment engineer"),
        de=("release manager", "release engineer"),
        tr=("release mühendisi",),
        skills=("ci/cd", "git", "jenkins"),
        resp=("release", "deployment"),
        discovery="medium",
    ),
    # --- QA ---
    _f(
        "software_testing",
        "qa_testing",
        "Yazılım Test",
        en=("software tester", "software test engineer", "qa engineer", "quality assurance engineer"),
        de=("softwaretester", "software tester", "testingenieur", "qualitätssicherung software"),
        tr=("yazılım test uzmanı", "test mühendisi", "kalite güvence"),
        skills=("selenium", "cypress", "jira", "test cases", "manual testing"),
        resp=("software testing", "test cases", "bug tracking", "quality assurance", "testautomation"),
        degrees=COMMON_CS_DEGREES,
    ),
    _f(
        "test_automation",
        "qa_testing",
        "Test Otomasyon",
        en=("test automation engineer", "automation tester", "qa automation"),
        de=("testautomatisierung", "test automation"),
        tr=("test otomasyon mühendisi",),
        skills=("selenium", "playwright", "python", "java", "ci/cd"),
        resp=("test automation", "automated testing"),
    ),
    _f(
        "validation",
        "qa_testing",
        "Validasyon",
        en=("validation engineer", "software validation"),
        de=("validierungsingenieur", "software validierung"),
        tr=("validasyon mühendisi",),
        skills=("gxp", "documentation", "testing"),
        resp=("validation", "verification"),
        discovery="medium",
    ),
    # --- Digital transformation ---
    _f(
        "digital_transformation",
        "digital_transformation",
        "Dijital Dönüşüm",
        en=("digital transformation specialist", "digitalization specialist", "technology transformation"),
        de=("digitalisierungsmanager", "digitalisierung", "digitale transformation"),
        tr=("dijital dönüşüm uzmanı", "dijitalleşme uzmanı"),
        skills=("process automation", "rpa", "erp", "change management"),
        resp=("digital transformation", "digitalization", "digitalisierung", "dijital dönüşüm"),
    ),
    _f(
        "process_automation",
        "digital_transformation",
        "Süreç Otomasyonu",
        en=("process automation specialist", "business automation", "automation specialist"),
        de=("prozessautomatisierung", "automatisierung", "geschäftsprozessautomatisierung"),
        tr=("otomasyon uzmanı", "süreç otomasyonu"),
        skills=("rpa", "power automate", "python", "uipath", "automation anywhere"),
        resp=("process automation", "automatisierung", "otomasyon"),
    ),
    _f(
        "rpa",
        "digital_transformation",
        "RPA",
        en=("rpa developer", "rpa specialist", "rpa engineer"),
        de=("rpa entwickler", "rpa specialist"),
        tr=("rpa geliştirici", "rpa uzmanı"),
        skills=("uipath", "blue prism", "power automate", "rpa"),
        resp=("robotic process automation", "rpa"),
    ),
    # --- Project / Product ---
    _f(
        "it_project",
        "project_pmo",
        "IT Proje",
        en=(
            "it project specialist",
            "it project coordinator",
            "technical project coordinator",
            "project engineer",
        ),
        de=("it projektmitarbeiter", "projektkoordinator it", "projektingenieur"),
        tr=("it proje uzmanı", "proje koordinatörü"),
        skills=("jira", "ms project", "agile", "scrum"),
        resp=("project coordination", "project planning", "stakeholder"),
        discovery="medium",
    ),
    _f(
        "pmo",
        "project_pmo",
        "PMO",
        en=("pmo analyst", "pmo specialist", "project management office"),
        de=("pmo", "project management office"),
        tr=("pmo uzmanı", "pmo analisti"),
        skills=("reporting", "excel", "jira"),
        resp=("project portfolio", "status reporting"),
        discovery="medium",
    ),
    _f(
        "product_analysis",
        "product",
        "Ürün Analizi",
        en=("product analyst", "product operations", "technical product specialist", "junior product owner"),
        de=("product analyst", "product owner", "produktanalyst"),
        tr=("ürün analisti", "ürün sahibi"),
        skills=("sql", "analytics", "jira", "figma"),
        resp=("product analysis", "backlog", "user stories"),
        discovery="medium",
    ),
    # --- Operations ---
    _f(
        "operations_analysis",
        "operations",
        "Operasyon Analizi",
        en=("operations analyst", "business operations analyst", "operations engineer"),
        de=("operations analyst", "betriebsanalyst"),
        tr=("operasyon analisti", "iş operasyonları analisti"),
        skills=("sql", "excel", "power bi", "python"),
        resp=("operations analysis", "operational reporting", "process optimization"),
        discovery="medium",
    ),
    _f(
        "technical_operations",
        "operations",
        "Teknik Operasyon",
        en=("technical operations specialist", "service operations", "operations support"),
        de=("technical operations", "service operations"),
        tr=("teknik operasyon uzmanı",),
        skills=("monitoring", "incident", "sql"),
        resp=("technical operations", "service operations"),
    ),
    # --- Industrial IT ---
    _f(
        "industrial_it",
        "industrial_it",
        "Endüstriyel IT",
        en=("industrial it", "manufacturing it", "production it", "ot/it", "mes specialist"),
        de=("industrie-it", "fertigung-it", "mes spezialist", "produktions-it"),
        tr=("endüstriyel it", "üretim sistemleri", "mes uzmanı"),
        skills=("mes", "scada", "opc", "sql", "plc"),
        resp=("manufacturing systems", "production systems", "ot/it"),
        discovery="medium",
    ),
    _f(
        "iot",
        "industrial_it",
        "IoT",
        en=("iot engineer", "iot specialist", "internet of things"),
        de=("iot engineer", "internet der dinge"),
        tr=("iot mühendisi",),
        skills=("mqtt", "python", "embedded", "sensors"),
        resp=("iot", "connected devices"),
    ),
    _f(
        "industrial_automation",
        "industrial_it",
        "Endüstriyel Otomasyon",
        en=("industrial automation", "automation engineer"),
        de=("industrieautomatisierung", "automatisierungsingenieur"),
        tr=("endüstriyel otomasyon", "otomasyon mühendisi"),
        skills=("plc", "scada", "python", "sql"),
        resp=("automation", "control systems"),
        discovery="medium",
    ),
    # --- Consulting ---
    _f(
        "it_consulting",
        "consulting_implementation",
        "IT Danışmanlık",
        en=(
            "it consultant",
            "junior it consultant",
            "technical consultant",
            "technology consultant",
            "solutions engineer",
            "solutions consultant",
            "pre-sales engineer",
        ),
        de=("it-berater", "it berater", "technical consultant", "solution engineer"),
        tr=("it danışmanı", "teknoloji danışmanı", "çözüm mühendisi"),
        skills=("erp", "cloud", "sql", "presentation"),
        resp=("consulting", "solution design", "implementation", "customer success"),
        degrees=COMMON_CS_DEGREES,
    ),
    # --- Planning / Finance analytics (tech-gated) ---
    _f(
        "business_planning",
        "planning_performance",
        "İş Planlama",
        en=("planning analyst", "business planning specialist", "performance management"),
        de=("planungsanalyst", "business planning"),
        tr=("planlama analisti", "iş planlama uzmanı"),
        skills=("excel", "sql", "power bi", "sap"),
        resp=("planning", "forecasting", "performance management"),
        discovery="medium",
    ),
    _f(
        "financial_analysis",
        "financial_analytics",
        "Finansal Analitik",
        en=(
            "financial analyst",
            "fp&a analyst",
            "fp and a",
            "cost analyst",
            "budget & reporting",
            "commercial analyst",
            "revenue analyst",
        ),
        de=("financial analyst", "controlling analyst", "kostenanalyst"),
        tr=("finansal analist", "bütçe raporlama", "maliyet analisti"),
        skills=("sql", "power bi", "sap", "excel", "python"),
        resp=("financial analysis", "budget reporting", "forecasting", "commercial analytics"),
        discovery="medium",
    ),
    # --- Supply chain analytics ---
    _f(
        "supply_chain_analysis",
        "supply_chain_analytics",
        "Tedarik Zinciri Analitiği",
        en=("supply chain analyst", "logistics analyst", "optimization analyst", "operations research"),
        de=("supply chain analyst", "logistikanalyst", "operations research"),
        tr=("tedarik zinciri analisti", "lojistik analisti"),
        skills=("sql", "python", "optimization", "excel", "power bi"),
        resp=("supply chain analysis", "optimization", "operations research"),
        discovery="medium",
    ),
)


# Signals used for broad engineering discovery (not automatic acceptance).
TECH_RESPONSIBILITY_SIGNALS: Tuple[str, ...] = (
    "software",
    "application development",
    "data analysis",
    "reporting",
    "dashboard",
    "business intelligence",
    "database",
    "sql",
    "automation",
    "process optimization",
    "requirements analysis",
    "system administration",
    "technical support",
    "network",
    "information security",
    "system integration",
    "api",
    "erp",
    "sap",
    "crm",
    "project coordination",
    "digital transformation",
    "digitalisierung",
    "informatik",
    "it systems",
    "business systems",
    "programmieren",
    "entwicklung von software",
    "veri analizi",
    "yazılım",
    "raporlama",
    "otomasyon",
)

ANALYTICAL_TECH_SIGNALS: Tuple[str, ...] = (
    "sql",
    "power bi",
    "tableau",
    "python",
    "data analysis",
    "reporting",
    "business intelligence",
    "dashboard",
    "automation",
    "sap",
    "large datasets",
    "etl",
    "datenanalyse",
    "berichtswesen",
)

UNRELATED_ENGINEERING_SIGNALS: Tuple[str, ...] = (
    "civil engineer",
    "structural engineer",
    "chemical engineer",
    "bauingenieur",
    "hochbau",
    "tiefbau",
    "hvac",
    "heating ventilation",
    "mechanical design",
    "konstruktion mechanik",
    "cad only",
    "solidworks only",
    "catia only",
    "inşaat mühendisi",
    "makine tasarım",
    "statik",
    "beton",
    "stahlbau",
)

GENERIC_ENGINEERING_TITLE_SIGNALS: Tuple[str, ...] = (
    "project engineer",
    "systems engineer",
    "development engineer",
    "r&d engineer",
    "test engineer",
    "automation engineer",
    "application engineer",
    "solutions engineer",
    "integration engineer",
    "quality engineer",
    "technical engineer",
    "projektingenieur",
    "systementwickler",
    "entwicklungsingenieur",
    "prüfingenieur",
    "automatisierungsingenieur",
    "anwendungsingenieur",
    "qualitätsingenieur",
)

MANUFACTURING_QA_SIGNALS: Tuple[str, ...] = (
    "incoming inspection",
    "dimensional inspection",
    "gd&t",
    "fmea manufacturing",
    "production quality",
    "fertigungqualität",
    "werkstoff",
    "machining",
    "welding quality",
    "iso 9001 production",
)

EDUCATION_COMPATIBLE_TERMS: Tuple[str, ...] = COMMON_CS_DEGREES + (
    "engineering degree",
    "technical university",
    "stem",
    "mint",
    "related technical field",
    "related engineering",
    "engineering",
    "mühendislik fakültesi",
    "ilgili mühendislik",
    "sayısal bölümler",
    "teknik bölümler",
    "technische informatik",
    "elektrotechnik/informatik",
)

# Preferred search queries per filter group for Germany (DE+EN), kept short.
GERMANY_SEARCH_SEED: Dict[str, Tuple[str, ...]] = {
    "software_development": (
        "Junior Softwareentwickler",
        "Softwareentwickler",
        "Anwendungsentwickler",
        "Junior Software Developer",
        "Full Stack Developer",
    ),
    "it_support": (
        "IT Support",
        "IT Support Specialist",
        "Helpdesk",
        "Technischer Support",
    ),
    "system_infrastructure": (
        "Systemadministrator",
        "Fachinformatiker Systemintegration",
        "IT Administrator",
        "System Engineer",
    ),
    "network": (
        "Netzwerkadministrator",
        "Network Engineer",
    ),
    "cybersecurity": (
        "IT Sicherheit",
        "SOC Analyst",
        "Junior Cyber Security Analyst",
        "Informationssicherheit",
    ),
    "data_database": (
        "Data Analyst",
        "Datenanalyst",
        "Data Engineer",
        "Datenbankadministrator",
        "SQL Developer",
    ),
    "bi_reporting": (
        "Business Intelligence",
        "BI Analyst",
        "Reporting Specialist",
        "Power BI",
    ),
    "decision_support": (
        "Decision Support",
        "Decision Support Analyst",
        "Business Analytics",
        "Karar Destek",
    ),
    "business_analysis": (
        "Business Analyst",
        "IT Business Analyst",
        "System Analyst",
        "Prozessanalyst",
    ),
    "erp_sap_crm": (
        "SAP Berater",
        "SAP Support",
        "ERP Consultant",
        "Anwendungsbetreuer",
        "CRM Specialist",
    ),
    "cloud_devops": (
        "Cloud Engineer",
        "DevOps Engineer",
        "Junior DevOps",
    ),
    "qa_testing": (
        "Softwaretester",
        "QA Engineer",
        "Test Engineer",
        "Testautomatisierung",
    ),
    "digital_transformation": (
        "Digitalisierung",
        "Digital Transformation",
        "RPA Developer",
        "Prozessautomatisierung",
    ),
    "project_pmo": (
        "IT Projektkoordinator",
        "PMO Analyst",
        "Technical Project Coordinator",
    ),
    "product": (
        "Product Analyst",
        "Junior Product Owner",
    ),
    "operations": (
        "Operations Analyst",
        "IT Operations",
    ),
    "industrial_it": (
        "Industrial IT",
        "MES Specialist",
        "IoT Engineer",
    ),
    "consulting_implementation": (
        "IT Berater",
        "Junior IT Consultant",
        "Solutions Engineer",
        "Implementation Specialist",
    ),
    "planning_performance": (
        "Planning Analyst",
        "Performance Analyst",
    ),
    "financial_analytics": (
        "Financial Analyst SQL",
        "FP&A Analyst Power BI",
    ),
    "supply_chain_analytics": (
        "Supply Chain Analyst",
        "Logistics Analyst",
    ),
    "ai_ml": (
        "Machine Learning Engineer",
        "Data Scientist",
        "Computer Vision",
    ),
    "application_support": (
        "Anwendungsbetreuer",
        "Application Support",
        "Applikationsbetreuer",
    ),
    "system_administration": (
        "Systemadministrator",
        "Fachinformatiker Systemintegration",
    ),
    "it_consulting": (
        "IT Berater",
        "Junior IT Consultant",
    ),
}


def list_filter_groups(*, include_legacy: bool = True) -> List[FilterGroup]:
    groups = list(FILTER_GROUPS)
    if include_legacy:
        return groups
    legacy = set(FILTER_GROUP_ALIASES)
    return [g for g in groups if g.id not in legacy]


def get_filter_group(group_id: str) -> Optional[FilterGroup]:
    for group in FILTER_GROUPS:
        if group.id == group_id:
            return group
    return None


def canonicalize_filter_group(group_id: str) -> str:
    return FILTER_GROUP_ALIASES.get(group_id, group_id)


def get_role_family(family_id: str) -> Optional[RoleFamily]:
    for family in ROLE_FAMILIES:
        if family.id == family_id:
            return family
    return None


def families_for_filter_group(group_id: str) -> List[RoleFamily]:
    canonical = canonicalize_filter_group(group_id)
    # Include direct group id matches and legacy aliases that point to canonical.
    matched: List[RoleFamily] = []
    for family in ROLE_FAMILIES:
        if not family.enabled:
            continue
        if family.filter_group == group_id or family.filter_group == canonical:
            matched.append(family)
        elif canonicalize_filter_group(family.filter_group) == canonical:
            matched.append(family)
    # Also include families whose filter_group is an alias of requested id.
    if group_id in FILTER_GROUP_ALIASES:
        target = FILTER_GROUP_ALIASES[group_id]
        for family in ROLE_FAMILIES:
            if family.enabled and family.filter_group == target and family not in matched:
                matched.append(family)
    return matched


def all_title_terms(family: RoleFamily) -> List[str]:
    return list(family.titles_en) + list(family.titles_de) + list(family.titles_tr)


def generate_search_terms(
    *,
    filter_group: Optional[str] = None,
    language: Optional[str] = None,
    market: str = "de",
) -> List[str]:
    """
    Derive deduplicated search terms from the taxonomy.

    market='de' → German + English
    market='tr' → Turkish + English
    language overrides market language selection when set to de|en|tr.
    """
    if filter_group:
        families = families_for_filter_group(filter_group)
        seeds = list(GERMANY_SEARCH_SEED.get(filter_group, ()))
        if filter_group in FILTER_GROUP_ALIASES:
            seeds.extend(GERMANY_SEARCH_SEED.get(FILTER_GROUP_ALIASES[filter_group], ()))
    else:
        families = [f for f in ROLE_FAMILIES if f.enabled]
        seeds = []
        for group in list_filter_groups(include_legacy=False):
            seeds.extend(GERMANY_SEARCH_SEED.get(group.id, ()))

    terms: List[str] = []
    # Prefer curated seeds first (keeps request volume reasonable).
    terms.extend(seeds)

    langs: Sequence[str]
    if language:
        langs = (language,)
    elif market == "tr":
        langs = ("tr", "en")
    else:
        langs = ("de", "en")

    for family in families:
        if "en" in langs:
            terms.extend(family.titles_en[:4])
        if "de" in langs:
            terms.extend(family.titles_de[:4])
        if "tr" in langs:
            terms.extend(family.titles_tr[:4])

    return _unique(terms)


def filter_group_label_tr(group_id: str) -> str:
    group = get_filter_group(group_id)
    return group.label_tr if group else group_id


def _unique(terms: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for term in terms:
        cleaned = term.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out
