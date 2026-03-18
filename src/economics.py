"""ROI and savings calculator based on PRD 8.1/8.2."""

import pandas as pd

from src.config import COST_MODEL, REDUCTION_RATES
from src.database import load_incidents


def compute_economics() -> dict:
    """Compute economic impact of AI implementation.

    Returns before/after comparison with savings breakdown.
    """
    incidents = load_incidents()

    # Count by type (annualized)
    type_counts = incidents["type"].value_counts()

    # Determine data span in years for annualization
    incidents_copy = incidents.copy()
    incidents_copy["date"] = pd.to_datetime(incidents_copy["date"])
    date_range_days = (incidents_copy["date"].max() - incidents_copy["date"].min()).days
    years_span = max(date_range_days / 365.25, 1.0)
    incidents_per_year = len(incidents) / years_span

    # Combine related types for economic calculation
    annual_lti = (type_counts.get("lti", 0) + type_counts.get("nlti", 0)) / years_span
    annual_microtrauma = (type_counts.get("micro_trauma", 0) + type_counts.get("microtrauma", 0)) / years_span
    annual_near_miss = (type_counts.get("near_miss", 0) + type_counts.get("dangerous_situation", 0)) / years_span
    annual_first_aid = (type_counts.get("first_aid", 0) + type_counts.get("health_deterioration", 0)) / years_span
    annual_fire = (type_counts.get("fire", 0) + type_counts.get("dtp", 0) + type_counts.get("incident", 0)) / years_span

    # Before AI
    before = {
        "lti": round(annual_lti),
        "microtrauma": round(annual_microtrauma),
        "near_miss": round(annual_near_miss),
        "first_aid": round(annual_first_aid),
        "fire": round(annual_fire),
        "total": round(incidents_per_year),
    }

    # After AI (with reduction rates)
    prevented_lti = round(annual_lti * REDUCTION_RATES["lti"])
    prevented_microtrauma = round(annual_microtrauma * REDUCTION_RATES["microtrauma"])
    prevented_near_miss = round(annual_near_miss * REDUCTION_RATES["near_miss"])

    after = {
        "lti": before["lti"] - prevented_lti,
        "microtrauma": before["microtrauma"] - prevented_microtrauma,
        "near_miss": before["near_miss"] - prevented_near_miss,
        "first_aid": before["first_aid"],  # No specific reduction rate
        "fire": before["fire"],
    }
    after["total"] = sum(after.values())

    # Cost calculations
    lti_direct_savings = prevented_lti * COST_MODEL["lti_direct_cost"]
    lti_indirect_savings = lti_direct_savings * COST_MODEL["indirect_multiplier"]
    fine_savings = round(COST_MODEL["fine_per_violation"] * 10 * COST_MODEL["fine_reduction_pct"])  # ~10 fines/year
    investigation_savings = round(
        prevented_lti * COST_MODEL["investigation_hours_per_lti"]
        * COST_MODEL["hourly_rate"]
        * COST_MODEL["investigation_reduction_pct"]
    )
    audit_savings = COST_MODEL["audit_efficiency_gain"]

    total_savings = (
        lti_direct_savings
        + lti_indirect_savings
        + fine_savings
        + investigation_savings
        + audit_savings
    )

    savings_breakdown = {
        "lti_direct": {
            "label": "Прямые затраты на НС (мед., компенсации)",
            "amount": lti_direct_savings,
            "detail": f"{prevented_lti} предотвращённых НС × {COST_MODEL['lti_direct_cost']:,} ₸",
        },
        "lti_indirect": {
            "label": "Косвенные потери (простой, персонал, репутация)",
            "amount": lti_indirect_savings,
            "detail": f"200% от прямых затрат",
        },
        "fines": {
            "label": "Штрафы и предписания регулятора",
            "amount": fine_savings,
            "detail": f"Снижение на {COST_MODEL['fine_reduction_pct']*100:.0f}%",
        },
        "investigation": {
            "label": "Затраты на расследования и отчётность",
            "amount": investigation_savings,
            "detail": f"Снижение на {COST_MODEL['investigation_reduction_pct']*100:.0f}%",
        },
        "audit_efficiency": {
            "label": "Эффективность аудитов (Карта Коргау)",
            "amount": audit_savings,
            "detail": "Автоматизация процессов аудита",
        },
    }

    return {
        "before": before,
        "after": after,
        "prevented": {
            "lti": prevented_lti,
            "microtrauma": prevented_microtrauma,
            "near_miss": prevented_near_miss,
            "total_injuries": prevented_lti + prevented_microtrauma,
        },
        "savings_breakdown": savings_breakdown,
        "total_savings": total_savings,
        "total_savings_formatted": f"{total_savings:,.0f} ₸",
        "total_savings_usd": f"~{total_savings / 480:,.0f} USD",
    }
