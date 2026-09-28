"""Tests for multilingual role taxonomy classification and discovery relevance."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config.role_taxonomy import ROLE_FAMILIES, generate_search_terms, list_filter_groups
from app.services.role_classifier import (
    classify_job,
    detect_available_levels,
    detect_education_compatibility,
    detect_role_category,
    is_discovery_keep,
)
from app.services.scoring import score_job
from app.services.candidate_profile import get_default_profile
from app.sources.filters import matches_target_role
from app.sources.normalized_job import NormalizedJob


def test_taxonomy_has_core_families_and_languages() -> None:
    ids = {family.id for family in ROLE_FAMILIES}
    assert "software_engineering" in ids
    assert "decision_support" in ids
    assert "business_analysis" in ids
    assert "sap" in ids
    assert "digital_transformation" in ids
    assert "operations_analysis" in ids

    en = sum(len(f.titles_en) for f in ROLE_FAMILIES)
    de = sum(len(f.titles_de) for f in ROLE_FAMILIES)
    tr = sum(len(f.titles_tr) for f in ROLE_FAMILIES)
    assert en >= 40
    assert de >= 30
    assert tr >= 20
    assert len(list_filter_groups(include_legacy=False)) >= 20


def test_junior_software_and_it_support() -> None:
    soft = classify_job("Junior Software Developer", "Python and SQL development")
    assert soft.primary_role_family in {
        "software_engineering",
        "application_development",
        "backend_development",
    }
    assert soft.filter_group == "software_development"
    assert soft.discovery_relevance == "high"
    assert detect_role_category("Junior Software Developer") == "software_development"

    support = classify_job("IT Support Specialist", "Windows Active Directory help desk")
    assert support.filter_group == "it_support"
    assert support.discovery_relevance in {"high", "medium"}


def test_decision_support_multilevel_not_rejected() -> None:
    title = "Decision Support Junior / Specialist / Senior Specialist"
    result = classify_job(
        title,
        "SQL, Power BI dashboards, management reporting, karar destek analizleri",
    )
    assert result.primary_role_family == "decision_support"
    assert result.filter_group == "decision_support"
    assert "junior" in result.available_levels
    assert "senior" in result.available_levels
    assert is_discovery_keep(result)
    assert matches_target_role(
        {"title": title, "description": "SQL Power BI reporting"},
        [],
        ["decision_support"],
    )

    scored = score_job(
        NormalizedJob(
            source="test",
            title=title,
            description="SQL and Power BI. Junior or specialist track.",
            company="Firma",
            location="Berlin",
            job_url="https://example.com/ds",
        ),
        profile=get_default_profile(),
    )
    # Must not be discarded by senior word alone; score can still be moderate.
    assert scored.score >= 40


def test_business_analyst_and_reporting_bi() -> None:
    ba = classify_job("Business Analyst", "Requirements analysis, stakeholder workshops, SQL")
    assert ba.primary_role_family == "business_analysis"
    assert ba.discovery_relevance in {"high", "medium"}

    reporting = classify_job(
        "Reporting Specialist",
        "Build SQL datasets and Power BI dashboards for management reporting",
    )
    assert reporting.filter_group in {"bi_reporting", "decision_support", "data_database"}
    assert reporting.discovery_relevance in {"high", "medium"}
    assert reporting.primary_role_family in {
        "reporting",
        "business_intelligence",
        "data_analysis",
    }


def test_sap_and_digital_transformation() -> None:
    sap = classify_job("SAP Application Specialist", "SAP support and customization ABAP")
    assert sap.primary_role_family in {"sap", "application_support", "enterprise_applications"}
    assert sap.filter_group in {"erp_sap_crm", "application_support"}

    digital = classify_job(
        "Digital Transformation Specialist",
        "Digitalisierung, process automation, RPA rollout",
    )
    assert digital.filter_group == "digital_transformation"
    assert digital.discovery_relevance in {"high", "medium"}


def test_operations_analyst_with_sql_bi() -> None:
    result = classify_job(
        "Operations Analyst",
        "Use SQL and Power BI for operational reporting and process optimization",
    )
    assert result.primary_role_family in {"operations_analysis", "business_analytics", "reporting"}
    assert is_discovery_keep(result)


def test_senior_java_high_discovery_low_match() -> None:
    title = "Senior Java Developer"
    description = "7+ years Java Spring Boot required. Lead technical design."
    discovery = classify_job(title, description)
    assert discovery.discovery_relevance == "high"
    assert discovery.filter_group == "software_development"

    scored = score_job(
        NormalizedJob(
            source="test",
            title=title,
            description=description,
            company="Firma",
            location="München",
            job_url="https://example.com/java",
            experience_level="senior",
        ),
        profile=get_default_profile(),
    )
    assert scored.score < 70


def test_unrelated_engineering_and_accountant() -> None:
    mech = classify_job(
        "Mechanical Design Engineer",
        "SolidWorks CAD mechanical design only, no software development",
    )
    assert mech.discovery_relevance == "low"
    assert not is_discovery_keep(mech)

    civil = classify_job("Civil Engineer", "Structural concrete design Bauingenieur")
    assert civil.discovery_relevance == "low"

    accountant = classify_job(
        "Accountant",
        "Bookkeeping, invoices, DATEV accounting, no SQL or reporting systems",
    )
    assert accountant.discovery_relevance == "low"


def test_financial_reporting_with_tech_signals() -> None:
    result = classify_job(
        "Financial Reporting Specialist",
        "SQL, Power BI and SAP BW for financial reporting and large datasets",
    )
    assert result.discovery_relevance in {"medium", "high"}
    assert is_discovery_keep(result)


def test_project_engineer_with_integration() -> None:
    result = classify_job(
        "Project Engineer",
        "Software and system integration, API interfaces, technical documentation",
    )
    assert result.discovery_relevance in {"medium", "high"}
    assert is_discovery_keep(result)


def test_quality_engineer_software_vs_manufacturing() -> None:
    software_qa = classify_job(
        "Quality Engineer",
        "Software testing, test cases, Selenium automation, bug tracking",
    )
    assert software_qa.filter_group == "qa_testing"
    assert software_qa.discovery_relevance in {"high", "medium"}

    manufacturing = classify_job(
        "Quality Engineer",
        "Incoming inspection, welding quality, machining tolerances, manufacturing only",
    )
    assert manufacturing.discovery_relevance == "low"


def test_education_and_multilingual_titles() -> None:
    assert detect_education_compatibility(
        "abschluss in informatik oder computer engineering"
    ) == "compatible"
    assert detect_education_compatibility(
        "bilgisayar mühendisliği mezunu"
    ) == "compatible"

    de = classify_job("Softwareentwickler", "Java Entwicklung")
    tr = classify_job("Yazılım Geliştirici", "Python ile yazılım geliştirme")
    assert de.filter_group == "software_development"
    assert tr.filter_group == "software_development"


def test_available_levels_and_secondary_families() -> None:
    levels = detect_available_levels(
        "Decision Support Junior / Specialist / Senior Specialist"
    )
    assert "junior" in levels
    assert "specialist" in levels
    assert "senior" in levels

    result = classify_job(
        "BI Developer / Data Analyst",
        "Power BI, SQL, dashboards, business intelligence reporting",
    )
    assert result.primary_role_family
    assert isinstance(result.secondary_role_families, list)


def test_search_terms_from_taxonomy() -> None:
    terms = generate_search_terms(market="de")
    assert "Junior Softwareentwickler" in terms or "Softwareentwickler" in terms
    assert "Decision Support" in terms
    assert len(terms) == len({t.casefold() for t in terms})
    tr_terms = generate_search_terms(market="tr", language="tr")
    assert any("yazılım" in t.casefold() or "veri" in t.casefold() for t in tr_terms)


def run_all() -> None:
    test_taxonomy_has_core_families_and_languages()
    test_junior_software_and_it_support()
    test_decision_support_multilevel_not_rejected()
    test_business_analyst_and_reporting_bi()
    test_sap_and_digital_transformation()
    test_operations_analyst_with_sql_bi()
    test_senior_java_high_discovery_low_match()
    test_unrelated_engineering_and_accountant()
    test_financial_reporting_with_tech_signals()
    test_project_engineer_with_integration()
    test_quality_engineer_software_vs_manufacturing()
    test_education_and_multilingual_titles()
    test_available_levels_and_secondary_families()
    test_search_terms_from_taxonomy()
    print("Role classifier tests passed.")


if __name__ == "__main__":
    run_all()
