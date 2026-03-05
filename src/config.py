"""Constants and configuration for the HSE AI Analytics system."""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "hse.db"

# Random seed for reproducibility
SEED = 42

# Date range for synthetic data (3 years)
DATE_START = "2023-01-01"
DATE_END = "2025-12-31"

# Organizations
ORGANIZATIONS = [
    {"id": "org_01", "name": "ТОО «КазМунайСервис»", "type": "contractor", "risk_base": 0.7},
    {"id": "org_02", "name": "АО «ПетроКазахстан»", "type": "operator", "risk_base": 0.4},
    {"id": "org_03", "name": "ТОО «ДриллТех»", "type": "contractor", "risk_base": 0.65},
    {"id": "org_04", "name": "ТОО «СтройМонтажСервис»", "type": "contractor", "risk_base": 0.8},
    {"id": "org_05", "name": "АО «ТенгизШеврОйл»", "type": "operator", "risk_base": 0.35},
    {"id": "org_06", "name": "ТОО «КаспийЭнерджи»", "type": "contractor", "risk_base": 0.6},
    {"id": "org_07", "name": "АО «СНПС-Актобемунайгаз»", "type": "operator", "risk_base": 0.45},
    {"id": "org_08", "name": "ТОО «НефтеСпецМонтаж»", "type": "contractor", "risk_base": 0.75},
]

# Locations (oil field sites)
LOCATIONS = [
    "Месторождение Тенгиз - Буровая площадка №3",
    "Месторождение Тенгиз - Компрессорная станция",
    "Месторождение Карачаганак - Участок ГПЗ",
    "Месторождение Карачаганак - Буровая площадка №7",
    "Месторождение Кашаган - Остров D",
    "Месторождение Кашаган - Морская платформа",
    "Месторождение Узень - Насосная станция №2",
    "Месторождение Узень - Резервуарный парк",
    "Месторождение Жанажол - Буровая площадка №1",
    "Месторождение Жанажол - Установка подготовки нефти",
    "Месторождение Актоты - Базовый лагерь",
    "Месторождение Актоты - Трубопроводная трасса",
    "НПЗ Атырау - Установка АВТ",
    "НПЗ Атырау - Резервуарный парк",
    "Месторождение Королёвское - Куст скважин №5",
    "База обслуживания - Мастерские",
    "Месторождение Дунга - Площадка ДНС",
    "Месторождение Кумколь - Буровая площадка №2",
]

# Incident types with distribution weights
INCIDENT_TYPES = {
    "near_miss": {"label": "Опасная ситуация", "weight": 0.45, "severity": 1},
    "microtrauma": {"label": "Микротравма", "weight": 0.25, "severity": 2},
    "first_aid": {"label": "Первая помощь", "weight": 0.15, "severity": 3},
    "lti": {"label": "Несчастный случай (НС)", "weight": 0.10, "severity": 4},
    "fire": {"label": "Пожар/возгорание", "weight": 0.05, "severity": 5},
}

# Korgau card categories
KORGAU_CATEGORIES = [
    "СИЗ (средства индивидуальной защиты)",
    "Работа на высоте",
    "LOTO (блокировка/маркировка)",
    "Порядок на рабочем месте",
    "Электробезопасность",
    "Газоопасные работы",
    "Грузоподъёмные операции",
    "Ограждения и барьеры",
    "Пожарная безопасность",
    "Транспортная безопасность",
]

# Cause tags
CAUSE_TAGS = [
    "Нарушение использования СИЗ",
    "Несоблюдение процедуры LOTO",
    "Скользкая поверхность",
    "Отсутствие ограждений/барьеров",
    "Усталость/переутомление",
    "Недостаточное обучение",
    "Неисправность оборудования",
    "Нарушение правил работы на высоте",
    "Несоблюдение скоростного режима",
    "Отсутствие газоанализатора",
    "Нарушение наряда-допуска",
    "Плохая видимость/освещение",
]

# Alert thresholds
ALERT_THRESHOLDS = {
    "red": {"multiplier": 2.0, "description": "Нарушений > 2x порогового значения"},
    "orange": {"repeat_count": 3, "days": 30, "description": "Одинаковый тип > 3 раз за 30 дней"},
    "yellow": {"trend_pct": 0.15, "description": "Тренд > 15% к прошлому году"},
    "green": {"description": "Улучшение показателей"},
}

# Violation threshold per org per month (baseline)
VIOLATION_THRESHOLD_PER_MONTH = 5

# Cost model (PRD 8.2) in tenge
COST_MODEL = {
    "lti_direct_cost": 5_000_000,        # Direct cost per LTI
    "indirect_multiplier": 2.0,           # Indirect = 2x direct
    "fine_per_violation": 500_000,        # Regulatory fine
    "investigation_hours_per_lti": 80,
    "hourly_rate": 12_500,               # tenge per hour
    "audit_efficiency_gain": 3_000_000,   # Annual
    "fine_reduction_pct": 0.30,
    "investigation_reduction_pct": 0.70,
}

# Reduction rates after AI implementation (PRD 8.1)
REDUCTION_RATES = {
    "lti": 0.38,          # 38% reduction in LTIs
    "microtrauma": 0.40,  # 40% reduction
    "near_miss": 0.50,    # 50% reduction
}

# Forecast horizons in months
FORECAST_HORIZONS = [3, 6, 12]

# Risk score weights
RISK_WEIGHTS = {
    "incident_rate": 0.40,
    "violation_trend": 0.25,
    "overdue_ratio": 0.20,
    "severity": 0.15,
}

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"
