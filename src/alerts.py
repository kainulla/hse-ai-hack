"""4-level alert system based on korgau card data."""

import pandas as pd

from src.config import ALERT_THRESHOLDS, VIOLATION_THRESHOLD_PER_MONTH
from src.database import load_korgau, load_incidents


def generate_alerts(org_id: str | None = None) -> list[dict]:
    """Generate alerts for all or specific organization.

    Alert levels:
    - Red: violations > 2x threshold in period
    - Orange: same type > 3 times in 30 days per org
    - Yellow: trend > 15% vs same period last year
    - Green: improvement notification
    """
    korgau = load_korgau(org_id=org_id)
    if len(korgau) == 0:
        return []

    korgau = korgau.copy()
    korgau["date"] = pd.to_datetime(korgau["date"])
    violations = korgau[korgau["obs_type"] == "unsafe_condition"]

    if len(violations) == 0:
        return []

    alerts = []
    orgs = violations["org_id"].unique()

    for oid in orgs:
        org_violations = violations[violations["org_id"] == oid]
        org_name = org_violations["org_name"].iloc[0]

        # Red alert: violations > 2x threshold in last month
        last_date = org_violations["date"].max()
        last_month = org_violations[org_violations["date"] > last_date - pd.DateOffset(months=1)]
        threshold = VIOLATION_THRESHOLD_PER_MONTH
        if len(last_month) > threshold * ALERT_THRESHOLDS["red"]["multiplier"]:
            alerts.append({
                "level": "red",
                "level_label": "Критический",
                "org_id": oid,
                "org_name": org_name,
                "message": f"Число нарушений ({len(last_month)}) превышает пороговое значение ({threshold}) в {len(last_month)/threshold:.1f}x за последний месяц",
                "count": len(last_month),
                "threshold": threshold,
                "date": last_date.strftime("%Y-%m-%d"),
            })

        # Orange alert: same category > 3 times in 30 days
        for category in org_violations["category"].unique():
            cat_violations = org_violations[
                (org_violations["category"] == category)
                & (org_violations["date"] > last_date - pd.DateOffset(days=30))
            ]
            if len(cat_violations) > ALERT_THRESHOLDS["orange"]["repeat_count"]:
                alerts.append({
                    "level": "orange",
                    "level_label": "Высокий",
                    "org_id": oid,
                    "org_name": org_name,
                    "message": f"Категория '{category}' зафиксирована {len(cat_violations)} раз за 30 дней",
                    "category": category,
                    "count": len(cat_violations),
                    "date": last_date.strftime("%Y-%m-%d"),
                })

        # Yellow / Green alert: trend comparison vs last year
        current_year = last_date.year
        current_half = org_violations[org_violations["date"].dt.year == current_year]
        previous_half = org_violations[org_violations["date"].dt.year == current_year - 1]
        if len(previous_half) > 0 and len(current_half) > 0:
            days_current = (current_half["date"].max() - current_half["date"].min()).days + 1
            days_previous = (previous_half["date"].max() - previous_half["date"].min()).days + 1
            if days_previous > 0 and days_current > 0:
                rate_current = len(current_half) / days_current
                rate_previous = len(previous_half) / days_previous
                if rate_previous > 0:
                    trend_pct = (rate_current - rate_previous) / rate_previous
                    if trend_pct > ALERT_THRESHOLDS["yellow"]["trend_pct"]:
                        alerts.append({
                            "level": "yellow",
                            "level_label": "Средний",
                            "org_id": oid,
                            "org_name": org_name,
                            "message": f"Тренд нарушений вырос на {trend_pct*100:.0f}% по сравнению с прошлым годом",
                            "trend_pct": round(trend_pct * 100, 1),
                            "date": last_date.strftime("%Y-%m-%d"),
                        })
                    elif trend_pct < -0.1:
                        alerts.append({
                            "level": "green",
                            "level_label": "Улучшение",
                            "org_id": oid,
                            "org_name": org_name,
                            "message": f"Показатели улучшились на {abs(trend_pct)*100:.0f}% по сравнению с прошлым годом",
                            "trend_pct": round(trend_pct * 100, 1),
                            "date": last_date.strftime("%Y-%m-%d"),
                        })

    # Sort by severity: red first, then orange, yellow, green
    level_order = {"red": 0, "orange": 1, "yellow": 2, "green": 3}
    alerts.sort(key=lambda a: level_order.get(a["level"], 99))

    return alerts
