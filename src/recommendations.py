"""LLM + rule-based fallback recommendation system."""

import json
import os

import pandas as pd

from src.config import OPENAI_API_KEY, OPENAI_MODEL
from src.database import load_incidents, load_korgau

# Rule-based recommendation mapping (keys match real korgau categories)
RULE_RECOMMENDATIONS = {
    "СИЗ / Средства по обеспечению безопасности": [
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
    "Работы на высоте / Строительные леса": [
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
    "Наряд-допуск / Оценка риска": [
        {
            "title": "Аудит процедур наряд-допуска и оценки рисков",
            "description": "Провести комплексный аудит выполнения процедур наряд-допуска и оценки рисков на всех производственных участках.",
            "priority": "high",
        },
        {
            "title": "Обучение персонала процедурам наряд-допуска",
            "description": "Организовать обучение с практическими упражнениями по правильному оформлению наряд-допуска и оценке рисков.",
            "priority": "high",
        },
    ],
    "Поддержание чистоты и порядка": [
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
    "Электрооборудование": [
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
    "Проскальзывание / Спотыкание / Падение": [
        {
            "title": "Устранение факторов скольжения и спотыкания",
            "description": "Провести обследование рабочих зон и устранить все факторы, способствующие скольжению, спотыканию и падению.",
            "priority": "high",
        },
        {
            "title": "Установка противоскользящих покрытий",
            "description": "Обеспечить противоскользящие покрытия и поручни в зонах с повышенным риском падений.",
            "priority": "high",
        },
    ],
    "Рабочее место / Эргономика": [
        {
            "title": "Эргономическая оценка рабочих мест",
            "description": "Провести эргономическую оценку рабочих мест и внедрить корректирующие меры для снижения нагрузки.",
            "priority": "medium",
        },
        {
            "title": "Обучение по эргономике и безопасным методам работы",
            "description": "Организовать обучение работников правильным приёмам работы для снижения физической нагрузки.",
            "priority": "medium",
        },
    ],
    "Выполнение требований инструкций": [
        {
            "title": "Актуализация инструкций по охране труда",
            "description": "Пересмотреть и актуализировать все инструкции по охране труда с учётом выявленных нарушений.",
            "priority": "high",
        },
        {
            "title": "Контроль выполнения инструкций",
            "description": "Усилить контроль за соблюдением инструкций по охране труда на рабочих местах.",
            "priority": "high",
        },
    ],
    "Целостность объекта / Оборудования": [
        {
            "title": "Программа профилактического обслуживания",
            "description": "Разработать и внедрить программу профилактического обслуживания оборудования для предотвращения отказов.",
            "priority": "high",
        },
        {
            "title": "Инспекция целостности оборудования",
            "description": "Провести внеплановую проверку состояния оборудования и конструкций с устранением дефектов.",
            "priority": "high",
        },
    ],
    "Машины и оборудование": [
        {
            "title": "Инспекция машин и оборудования",
            "description": "Провести полную проверку технического состояния всех машин и оборудования на объекте.",
            "priority": "high",
        },
        {
            "title": "Обучение операторов техники",
            "description": "Организовать повышение квалификации операторов машин и оборудования.",
            "priority": "medium",
        },
    ],
    "Вождение": [
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
    "Монтажные и грузоподъемные работы": [
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
    "Взрыво- и пожароопасность": [
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
    "Транспортировка": [
        {
            "title": "Контроль безопасности транспортировки грузов",
            "description": "Усилить контроль за соблюдением правил безопасной транспортировки грузов.",
            "priority": "high",
        },
        {
            "title": "Проверка крепления грузов",
            "description": "Внедрить систему обязательной проверки крепления грузов перед транспортировкой.",
            "priority": "medium",
        },
    ],
    "Знаки безопасности / Предупредительные таблички": [
        {
            "title": "Аудит знаков безопасности",
            "description": "Провести полный аудит наличия и состояния знаков безопасности на всех участках.",
            "priority": "medium",
        },
        {
            "title": "Установка недостающих знаков",
            "description": "Обеспечить установку всех необходимых знаков безопасности и предупредительных табличек.",
            "priority": "medium",
        },
    ],
    "Падающие предметы": [
        {
            "title": "Обеспечение защиты от падающих предметов",
            "description": "Установить защитные козырьки и сетки на участках с риском падения предметов с высоты.",
            "priority": "high",
        },
        {
            "title": "Контроль складирования на высоте",
            "description": "Внедрить правила безопасного складирования материалов и инструментов на высоте.",
            "priority": "high",
        },
    ],
    "Опасные вещества/сероводород": [
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
    "Работы в замкнутом пространстве": [
        {
            "title": "Усиление контроля работ в замкнутых пространствах",
            "description": "Обеспечить постоянный контроль при работах в замкнутых пространствах: газоанализ, наблюдающий, наряд-допуск.",
            "priority": "high",
        },
        {
            "title": "Обучение работам в замкнутых пространствах",
            "description": "Провести обучение по безопасному выполнению работ в замкнутых пространствах с практическими упражнениями.",
            "priority": "high",
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
