"""Default target profile for rule-based match scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class ScoringProfile:
    """Future-ready profile; MVP uses DEFAULT_SCORING_PROFILE."""

    target_categories: Sequence[str] = (
        "software_development",
        "it_support",
        "system_infrastructure",
        "network",
        "cybersecurity",
        "data_database",
        "bi_reporting",
        "decision_support",
        "business_analysis",
        "erp_sap_crm",
        "cloud_devops",
        "qa_testing",
        "digital_transformation",
        "project_pmo",
        "operations",
        "industrial_it",
        "consulting_implementation",
        "ai_ml",
        "system_administration",
        "application_support",
        "it_consulting",
    )
    preferred_experience_max_years: int = 2
    preferred_german_max_required: str = "B2"
    preferred_work_models: Sequence[str] = ("remote", "hybrid", "onsite")
    base_score: int = 40


DEFAULT_SCORING_PROFILE = ScoringProfile()

CEFR_RANK = {
    "A1": 1,
    "A2": 2,
    "B1": 3,
    "B2": 4,
    "C1": 5,
    "C2": 6,
}


def cefr_at_most(level: Optional[str], maximum: str) -> bool:
    if not level:
        return False
    return CEFR_RANK.get(level.upper(), 99) <= CEFR_RANK.get(maximum.upper(), 0)


TARGET_CATEGORY_LABELS_DE = {
    "software_development": "Softwareentwicklung",
    "it_support": "IT Support",
    "system_infrastructure": "System / Infrastruktur",
    "network": "Netzwerk",
    "cybersecurity": "Cybersecurity",
    "data_database": "Daten / Database",
    "bi_reporting": "BI / Reporting",
    "decision_support": "Decision Support",
    "business_analysis": "Business Analysis",
    "erp_sap_crm": "ERP / SAP / CRM",
    "cloud_devops": "Cloud / DevOps",
    "qa_testing": "QA / Testing",
    "digital_transformation": "Digitalisierung / Automation",
    "project_pmo": "Projekt / PMO",
    "product": "Product",
    "operations": "Operations",
    "industrial_it": "Industrial IT",
    "consulting_implementation": "Consulting / Implementation",
    "planning_performance": "Planning / Performance",
    "financial_analytics": "Financial Analytics",
    "supply_chain_analytics": "Supply Chain / Optimization",
    "ai_ml": "AI / ML",
    "other_technical": "Weitere Technik / Engineering",
    "system_administration": "Systemadministration",
    "application_support": "Application Support",
    "it_consulting": "IT Consulting",
    "other": "Sonstiges",
}
