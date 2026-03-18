"""Statistics, trends, risk scoring, and correlation analysis."""

import pandas as pd
import numpy as np

from src.config import RISK_WEIGHTS, VIOLATION_THRESHOLD_PER_MONTH
from src.database import load_incidents, load_korgau


def compute_incident_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Compute monthly incident counts with moving averages."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")

    monthly = df.groupby("month").size().reset_index(name="count")
    monthly["month_dt"] = monthly["month"].dt.to_timestamp()
    monthly["ma_3"] = monthly["count"].rolling(3, min_periods=1).mean()
    monthly["ma_6"] = monthly["count"].rolling(6, min_periods=1).mean()
    return monthly


def compute_risk_score(org_id: str) -> dict:
    """Compute weighted risk score for an organization.

    Score = 0.4*incident_rate + 0.25*violation_trend + 0.2*overdue_ratio + 0.15*severity
    All components normalized to [0, 1].
    """
    incidents = load_incidents(org_id=org_id)
    korgau = load_korgau(org_id=org_id)

    all_incidents = load_incidents()
    all_korgau = load_korgau()

    # Incident rate (relative to max org)
    org_inc_count = len(incidents)
    max_inc = all_incidents.groupby("org_id").size().max() if len(all_incidents) > 0 else 1
    incident_rate = min(org_inc_count / max(max_inc, 1), 1.0)

    # Violation trend (last 6 months vs previous 6 months)
    violation_trend = 0.5
    if len(korgau) > 0:
        korgau_copy = korgau.copy()
        korgau_copy["date"] = pd.to_datetime(korgau_copy["date"])
        violations = korgau_copy[korgau_copy["obs_type"] == "unsafe_condition"]
        if len(violations) > 0:
            max_date = violations["date"].max()
            mid_date = max_date - pd.DateOffset(months=6)
            start_date = max_date - pd.DateOffset(months=12)
            recent = len(violations[violations["date"] > mid_date])
            previous = len(violations[(violations["date"] > start_date) & (violations["date"] <= mid_date)])
            if previous > 0:
                trend = (recent - previous) / previous
                violation_trend = min(max((trend + 1) / 2, 0), 1.0)

    # Overdue ratio
    overdue_ratio = 0.0
    if len(korgau) > 0:
        violations = korgau[korgau["obs_type"] == "unsafe_condition"]
        if len(violations) > 0:
            overdue_count = len(violations[violations["status"].isin(["overdue", "open"])])
            overdue_ratio = overdue_count / len(violations)

    # Average severity
    severity_norm = 0.0
    if len(incidents) > 0:
        severity_norm = min(incidents["severity"].mean() / 5.0, 1.0)

    score = (
        RISK_WEIGHTS["incident_rate"] * incident_rate
        + RISK_WEIGHTS["violation_trend"] * violation_trend
        + RISK_WEIGHTS["overdue_ratio"] * overdue_ratio
        + RISK_WEIGHTS["severity"] * severity_norm
    )

    return {
        "org_id": org_id,
        "risk_score": round(score, 3),
        "incident_rate": round(incident_rate, 3),
        "violation_trend": round(violation_trend, 3),
        "overdue_ratio": round(overdue_ratio, 3),
        "severity_norm": round(severity_norm, 3),
        "total_incidents": org_inc_count,
        "total_violations": len(korgau[korgau["obs_type"] == "unsafe_condition"]) if len(korgau) > 0 else 0,
    }


def get_top_risk_zones(n: int = 5) -> list[dict]:
    """Return top N organizations by risk score."""
    all_incidents = load_incidents()
    org_ids = all_incidents["org_id"].unique()
    scores = [compute_risk_score(oid) for oid in org_ids]
    scores.sort(key=lambda x: x["risk_score"], reverse=True)

    # Add org name
    for s in scores:
        org_inc = all_incidents[all_incidents["org_id"] == s["org_id"]]
        if len(org_inc) > 0:
            s["org_name"] = org_inc["org_name"].iloc[0]
        else:
            s["org_name"] = s["org_id"]

    return scores[:n]


def compute_correlation() -> dict:
    """Compute Pearson correlation between monthly korgau violations and incidents."""
    incidents = load_incidents()
    korgau = load_korgau()

    incidents["date"] = pd.to_datetime(incidents["date"])
    korgau["date"] = pd.to_datetime(korgau["date"])

    monthly_inc = incidents.groupby(incidents["date"].dt.to_period("M")).size()
    violations = korgau[korgau["obs_type"] == "unsafe_condition"]
    monthly_viol = violations.groupby(violations["date"].dt.to_period("M")).size()

    # Align periods
    common_periods = monthly_inc.index.intersection(monthly_viol.index)
    if len(common_periods) < 3:
        return {"correlation": 0.0, "p_value": 1.0, "n_months": 0}

    inc_vals = monthly_inc[common_periods].values.astype(float)
    viol_vals = monthly_viol[common_periods].values.astype(float)

    correlation = np.corrcoef(inc_vals, viol_vals)[0, 1]

    return {
        "correlation": round(float(correlation), 3),
        "n_months": len(common_periods),
        "monthly_incidents": inc_vals.tolist(),
        "monthly_violations": viol_vals.tolist(),
        "periods": [str(p) for p in common_periods],
    }
