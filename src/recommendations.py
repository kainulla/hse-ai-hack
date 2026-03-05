"""LLM + rule-based fallback recommendation system."""

import json
import os

import pandas as pd

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.database import load_incidents, load_korgau

# Rule-based recommendation mapping
RULE_RECOMMENDATIONS = {
    "СИЗ (средства индивидуальной защиты)": [
        {
            "title": "Проведение целевого инструктажа по применению СИЗ",
            "description": "Организовать обучение по правильному выбору и использованию средств индивидуальной защиты с практической демонстрацией.",
            "priority": "high",
        },
        {
            "title": "Усиление контроля за использованием СИЗ",
            "description": "Внедрить систему ежедневных проверок наличия и правильности применения СИЗ на рабочих местах.",
            "priority": "high",
        },
        {
            "title": "Обновление номенклатуры СИЗ",
            "description": "Пересмотреть перечень закупаемых СИЗ с учётом актуальных рисков и обратной связи от работников.",
            "priority": "medium",
        },
    ],
    "Работа на высоте": [
        {
            "title": "Инспекция средств защиты от падения с высоты",
            "description": "Провести полную проверку всех страховочных привязей, строп и анкерных точек с документированием результатов.",
            "priority": "high",
        },
        {
            "title": "Установка систем коллективной защиты",
            "description": "Установить защитные ограждения, сетки безопасности и леса на всех участках работ на высоте.",
            "priority": "high",
        },
        {
            "title": "Верификация компетенций работников",
            "description": "Провести аттестацию всех работников, выполняющих работы на высоте, с выдачей допусков.",
            "priority": "medium",
        },
    ],
    "LOTO (блокировка/маркировка)": [
        {
            "title": "Аудит процедур блокировки/маркировки",
            "description": "Провести комплексный аудит выполнения процедур LOTO на всех производственных участках.",
            "priority": "high",
        },
        {
            "title": "Обучение персонала процедурам LOTO",
            "description": "Организовать обучение с практическими упражнениями по правильному выполнению процедур блокировки/маркировки.",
            "priority": "high",
        },
        {
            "title": "Обеспечение замками и бирками",
            "description": "Закупить и распределить персональные замки и бирки для всех работников, выполняющих ремонтные работы.",
            "priority": "medium",
        },
    ],
    "Порядок на рабочем месте": [
        {
            "title": "Внедрение системы 5S на рабочих участках",
            "description": "Запустить программу 5S (сортировка, порядок, чистота, стандартизация, дисциплина) на производственных участках.",
            "priority": "medium",
        },
        {
            "title": "Устранение скользких поверхностей",
            "description": "Обеспечить противоскользящие покрытия и регулярную уборку в зонах с повышенным риском падений.",
            "priority": "high",
        },
    ],
    "Электробезопасность": [
        {
            "title": "Проверка электрооборудования",
            "description": "Провести плановую проверку всего электрооборудования, кабелей и заземления с устранением выявленных дефектов.",
            "priority": "high",
        },
        {
            "title": "Обучение по электробезопасности",
            "description": "Организовать обучение персонала по правилам безопасной эксплуатации электрооборудования.",
            "priority": "medium",
        },
    ],
    "Газоопасные работы": [
        {
            "title": "Обеспечение газоанализаторами",
            "description": "Обеспечить все бригады, работающие в зонах возможного скопления газов, портативными газоанализаторами.",
            "priority": "high",
        },
        {
            "title": "Обучение действиям при загазованности",
            "description": "Провести тренировки по действиям в аварийных ситуациях, связанных с загазованностью.",
            "priority": "high",
        },
    ],
    "Грузоподъёмные операции": [
        {
            "title": "Инспекция грузоподъёмного оборудования",
            "description": "Провести внеплановую проверку стропов, тросов и грузоподъёмных механизмов.",
            "priority": "high",
        },
        {
            "title": "Обучение стропальщиков",
            "description": "Организовать повышение квалификации стропальщиков с практическими занятиями.",
            "priority": "medium",
        },
    ],
    "Ограждения и барьеры": [
        {
            "title": "Установка недостающих ограждений",
            "description": "Провести обследование и установить защитные ограждения на всех опасных участках.",
            "priority": "high",
        },
        {
            "title": "Регулярная проверка ограждений",
            "description": "Ввести еженедельные осмотры состояния ограждений и барьеров безопасности.",
            "priority": "medium",
        },
    ],
    "Пожарная безопасность": [
        {
            "title": "Проверка средств пожаротушения",
            "description": "Провести инвентаризацию и проверку всех средств пожаротушения, заменить просроченные.",
            "priority": "high",
        },
        {
            "title": "Проведение противопожарных учений",
            "description": "Организовать практические учения по эвакуации и применению средств пожаротушения.",
            "priority": "medium",
        },
    ],
    "Транспортная безопасность": [
        {
            "title": "Контроль скоростного режима",
            "description": "Установить GPS-мониторинг и ограничители скорости на транспортных средствах.",
            "priority": "high",
        },
        {
            "title": "Обучение безопасному вождению",
            "description": "Организовать курсы защитного вождения для всех водителей компании.",
            "priority": "medium",
        },
    ],
}


def get_rule_based_recommendations(org_id: str) -> list[dict]:
    """Generate recommendations based on violation patterns for an org."""
    korgau = load_korgau(org_id=org_id)
    incidents = load_incidents(org_id=org_id)

    if len(korgau) == 0:
        return _default_recommendations()

    violations = korgau[korgau["obs_type"] == "unsafe_condition"]
    if len(violations) == 0:
        return _default_recommendations()

    # Find top violation categories
    top_categories = violations["category"].value_counts().head(3).index.tolist()

    recommendations = []
    for category in top_categories:
        if category in RULE_RECOMMENDATIONS:
            cat_recs = RULE_RECOMMENDATIONS[category]
            for rec in cat_recs[:2]:  # Top 2 per category
                recommendations.append({
                    **rec,
                    "category": category,
                    "source": "rule_based",
                })

    # Add incident-specific recommendations if causes available
    if len(incidents) > 0 and "causes" in incidents.columns:
        cause_counts = {}
        for causes_str in incidents["causes"].dropna():
            for cause in str(causes_str).split("|"):
                cause = cause.strip()
                if cause:
                    cause_counts[cause] = cause_counts.get(cause, 0) + 1

        if cause_counts:
            top_cause = max(cause_counts, key=cause_counts.get)
            recommendations.append({
                "title": f"Устранение корневой причины: {top_cause}",
                "description": f"Наиболее частая причина инцидентов - '{top_cause}' ({cause_counts[top_cause]} случаев). Рекомендуется разработать целевую программу по устранению данного фактора.",
                "priority": "high",
                "category": "Корневые причины",
                "source": "rule_based",
            })

    return recommendations[:7]


def _default_recommendations() -> list[dict]:
    """Return default recommendations when no data available."""
    return [
        {
            "title": "Проведение комплексного аудита безопасности",
            "description": "Организовать полный аудит условий труда и безопасности на всех рабочих участках.",
            "priority": "high",
            "category": "Общее",
            "source": "rule_based",
        },
        {
            "title": "Обучение персонала",
            "description": "Провести обучение работников по охране труда и промышленной безопасности.",
            "priority": "medium",
            "category": "Общее",
            "source": "rule_based",
        },
        {
            "title": "Развитие культуры безопасности",
            "description": "Внедрить программу развития культуры безопасности с вовлечением руководства.",
            "priority": "medium",
            "category": "Общее",
            "source": "rule_based",
        },
    ]


def get_llm_recommendations(org_id: str) -> list[dict] | None:
    """Generate recommendations using LLM (OpenAI). Returns None if unavailable."""
    api_key = os.getenv("OPENAI_API_KEY", "") or OPENAI_API_KEY
    if not api_key or api_key == "your-key-here":
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        korgau = load_korgau(org_id=org_id)
        incidents = load_incidents(org_id=org_id)

        violations = korgau[korgau["obs_type"] == "unsafe_condition"] if len(korgau) > 0 else pd.DataFrame()

        # Build context
        org_name = incidents["org_name"].iloc[0] if len(incidents) > 0 else org_id
        violation_summary = ""
        if len(violations) > 0:
            cat_counts = violations["category"].value_counts().head(5)
            violation_summary = "\n".join([f"- {cat}: {cnt} нарушений" for cat, cnt in cat_counts.items()])

        incident_summary = ""
        if len(incidents) > 0:
            type_counts = incidents["type_label"].value_counts()
            incident_summary = "\n".join([f"- {t}: {c} случаев" for t, c in type_counts.items()])

        prompt = f"""Ты - эксперт по охране труда и промышленной безопасности в нефтегазовой отрасли Казахстана.

Организация: {org_name}

Статистика нарушений (Карта Коргау):
{violation_summary or 'Данные отсутствуют'}

Статистика инцидентов:
{incident_summary or 'Данные отсутствуют'}

На основе данных сформируй 3-5 конкретных рекомендаций по повышению безопасности.

Ответ в формате JSON массива:
[
  {{
    "title": "Краткое название рекомендации",
    "description": "Подробное описание рекомендации с конкретными действиями",
    "priority": "high|medium|low",
    "category": "Категория"
  }}
]

Только JSON, без комментариев."""

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        # Extract JSON from response
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        recs = json.loads(content)
        for rec in recs:
            rec["source"] = "llm"
        return recs

    except Exception:
        return None


def get_recommendations(org_id: str) -> list[dict]:
    """Get recommendations: try LLM first, fallback to rules."""
    llm_recs = get_llm_recommendations(org_id)
    if llm_recs:
        return llm_recs
    return get_rule_based_recommendations(org_id)
