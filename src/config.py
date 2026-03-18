"""Constants and configuration for the HSE AI Analytics system."""

import json
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "hse.db"

# Random seed for reproducibility
SEED = 42

# Date range for real data
DATE_START = "2025-01-01"
DATE_END = "2026-12-31"

# Organizations: loaded dynamically from organizations.json if available
_ORGS_JSON = DATA_DIR / "organizations.json"
if _ORGS_JSON.exists():
    with open(_ORGS_JSON, "r", encoding="utf-8") as _f:
        ORGANIZATIONS = json.load(_f)
else:
    ORGANIZATIONS = []

# Incident types matching real data ETL output
INCIDENT_TYPES = {
    "lti": {"label": "Несчастный случай (тяжёлый/летальный)", "weight": 0.05, "severity": 5},
    "nlti": {"label": "Несчастный случай (лёгкий)", "weight": 0.05, "severity": 3},
    "micro_trauma": {"label": "Микротравма / ОМП", "weight": 0.50, "severity": 2},
    "health_deterioration": {"label": "Ухудшение здоровья", "weight": 0.10, "severity": 2},
    "dtp": {"label": "Дорожно-транспортное происшествие", "weight": 0.05, "severity": 3},
    "incident": {"label": "Инцидент", "weight": 0.05, "severity": 2},
    "fire": {"label": "Пожар/возгорание", "weight": 0.02, "severity": 4},
    "dangerous_situation": {"label": "Опасная ситуация", "weight": 0.18, "severity": 1},
}

# Korgau card categories from real data
KORGAU_CATEGORIES = [
    "СИЗ / Средства по обеспечению безопасности",
    "Проскальзывание / Спотыкание / Падение",
    "Электрооборудование",
    "Рабочее место / Эргономика",
    "Поддержание чистоты и порядка",
    "Выполнение требований инструкций",
    "Целостность объекта / Оборудования",
    "Машины и оборудование",
    "Вождение",
    "Знаки безопасности / Предупредительные таблички",
    "Транспортировка",
    "Охрана окружающей среды",
    "Трубопроводы / Подземные коммуникации",
    "Работы на высоте / Строительные леса",
    "Наряд-допуск / Оценка риска",
    "Монтажные и грузоподъемные работы",
    "Взрыво- и пожароопасность",
    "Падающие предметы",
    "Работы в замкнутом пространстве",
    "Сварка / Шлифовка / Отжиг",
    "Перемещение грузов вручную",
    "Переносное оборудование / Ручные инструменты",
    "Опасные вещества/сероводород",
    "Земляные работы",
    "Аварийное реагирование / Готовность к ЧС",
    "Санитарно-бытовые помещения",
    "Опасные природные явления / Погодные условия",
    "Испытание под давлением",
    "Вывешивание плакатов",
    "Ионизирующее излучение",
    "Не указано",
]

# Cause tags (kept for rule-based recommendations compatibility)
CAUSE_TAGS = [
    "УХУДШЕНИЕ ЗДОРОВЬЯ",
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
