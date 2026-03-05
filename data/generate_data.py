"""Synthetic data generator for HSE AI Analytics.

Generates:
- incidents.csv: 550+ rows over 3 years
- korgau_cards.csv: 1200+ rows over 3 years
- organizations.json: 8 orgs reference data

Key features:
- Seasonality: winter + summer peaks via sine modulation
- Korgau-incident correlation: violation clusters 2-4 weeks BEFORE incident spikes
- Russian-language descriptions
- Fixed seed for reproducibility
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import (
    CAUSE_TAGS,
    DATE_END,
    DATE_START,
    INCIDENT_TYPES,
    KORGAU_CATEGORIES,
    LOCATIONS,
    ORGANIZATIONS,
    SEED,
)

rng = np.random.default_rng(SEED)

# --- Russian description templates ---

INCIDENT_DESCRIPTIONS = {
    "near_miss": [
        "При проведении работ на буровой площадке обнаружена утечка газа в районе устья скважины.",
        "Падение предмета с высоты 5 метров в зоне проведения монтажных работ. Пострадавших нет.",
        "Автотранспорт проехал на красный сигнал светофора на территории месторождения.",
        "Обнаружено нарушение целостности ограждения котлована глубиной 3 метра.",
        "Работник обнаружил неисправность предохранительного клапана на ёмкости под давлением.",
        "При разгрузке труб произошло смещение груза на транспортном средстве.",
        "Обнаружено отсутствие заземления на передвижной электроустановке.",
        "Зафиксирован проезд спецтехники без сопровождения в тёмное время суток.",
        "При осмотре лесов обнаружены дефекты крепления настилов на высоте 8 метров.",
        "Работник сообщил о появлении запаха газа в районе технологической установки.",
        "Обнаружена трещина на корпусе задвижки высокого давления.",
        "При обходе территории обнаружен незакрытый люк колодца.",
        "Во время грозы работники не были эвакуированы с открытой площадки.",
        "Обнаружено несоответствие маркировки трубопровода фактическому содержимому.",
        "Зафиксирован случай работы крана вблизи ЛЭП без наряда-допуска.",
    ],
    "microtrauma": [
        "Работник получил порез пальца при замене уплотнительной прокладки без перчаток.",
        "Ушиб руки при работе с ручным инструментом. Оказана первая помощь на месте.",
        "Попадание инородного тела в глаз при зачистке сварного шва без защитных очков.",
        "Работник подвернул ногу на неровной поверхности рабочей площадки.",
        "Получена ссадина на руке при контакте с необработанным краем металлоконструкции.",
        "Термический ожог пальца при прикосновении к горячей трубе без теплоизоляции.",
        "Защемление пальца при закрытии крышки люка без использования специнструмента.",
        "Раздражение кожи рук при работе с химическим реагентом без защитных перчаток.",
        "Незначительный ушиб головы при контакте с низко расположенной конструкцией.",
        "Работник получил царапину при прохождении через проём с необработанными краями.",
    ],
    "first_aid": [
        "Растяжение связок голеностопа при спуске по обледенелой лестнице. Наложена повязка.",
        "Работник получил ожог предплечья при контакте с паром. Оказана первая помощь.",
        "Ушиб коленного сустава при падении на мокрой поверхности. Наложен холодный компресс.",
        "Попадание химического вещества на кожу руки. Проведена промывка, наложена повязка.",
        "Порез ладони при работе с режущим инструментом. Наложены швы в медпункте.",
        "Работник получил тепловой удар при работе на открытом воздухе в жару.",
        "Травма пальца при работе с пневмоинструментом. Перелом исключён рентгеном.",
        "Ушиб плеча при падении с лестницы высотой 1.5 м. Обработан в медпункте.",
    ],
    "lti": [
        "Падение работника с высоты 4 метра при демонтаже строительных лесов. Перелом руки.",
        "Травма спины при подъёме тяжёлого оборудования вручную. Госпитализация.",
        "Работник получил электротравму при работе на неотключённом оборудовании.",
        "Падение с лестницы при подъёме на площадку обслуживания. Перелом ноги.",
        "Травма руки при работе на токарном станке. Госпитализирован.",
        "Работник получил тяжёлую травму при обрушении грунта в котловане.",
        "Падение трубы на ногу работника при погрузочных работах. Перелом стопы.",
    ],
    "fire": [
        "Возгорание на технологической установке вследствие утечки углеводородов.",
        "Пожар в электрощитовой из-за короткого замыкания. Ликвидирован бригадой ДПД.",
        "Возгорание разлитого масла вблизи компрессорной станции.",
        "Загорание травы на территории промплощадки из-за проведения огневых работ.",
        "Возгорание в бытовом помещении из-за неисправности электропроводки.",
    ],
}

KORGAU_BAD_DESCRIPTIONS = [
    "Работник выполняет работу на высоте без страховочной привязи.",
    "Отсутствие защитных очков при проведении шлифовальных работ.",
    "Баллон с газом не закреплён в вертикальном положении.",
    "Электрический кабель проложен по земле без защиты.",
    "Работник не использует средства защиты органов слуха в шумной зоне.",
    "Открытый люк без ограждения и предупреждающих знаков.",
    "Использование неисправного ручного инструмента.",
    "Работа в замкнутом пространстве без газоанализатора и наблюдающего.",
    "Отсутствие знаков безопасности на участке проведения работ.",
    "Загромождение путей эвакуации строительными материалами.",
    "Сварочные работы проводятся без огнетушителя в зоне работ.",
    "Работник курит в неустановленном месте на территории объекта.",
    "Отсутствие блокировки энергоисточника при ремонте оборудования (LOTO).",
    "Работник поднимается по лестнице без трёх точек контакта.",
    "Разлив технической жидкости не убран и не обозначен.",
    "Контейнер с химикатами без маркировки и паспорта безопасности.",
    "Перегрузка грузоподъёмного механизма сверх паспортной грузоподъёмности.",
    "Работа на высоте без оформления наряда-допуска.",
    "Неправильное складирование материалов - риск обрушения.",
    "Средства пожаротушения с истёкшим сроком поверки.",
    "Использование повреждённых стропов при грузоподъёмных операциях.",
    "Работник без каски в зоне обязательного ношения СИЗ головы.",
    "Отсутствие аптечки первой помощи на рабочем участке.",
    "Нарушение правил безопасного вождения на территории объекта.",
    "Электрооборудование эксплуатируется с повреждённой изоляцией.",
    "Работник выполняет газоопасные работы без средств индивидуальной защиты органов дыхания.",
    "Строительные леса не имеют бирки о приёмке в эксплуатацию.",
    "Работник не прошёл инструктаж перед началом работ повышенной опасности.",
    "Траншея глубиной более 1.5 м без крепления стенок.",
    "Отсутствие заземления при проведении сварочных работ.",
]

KORGAU_GOOD_DESCRIPTIONS = [
    "Работник правильно использует страховочную привязь при работе на высоте.",
    "Отличное состояние рабочего места - порядок и чистота.",
    "Все средства пожаротушения проверены и находятся в исправном состоянии.",
    "Работник провёл качественный инструктаж для новых сотрудников.",
    "Блокировка энергоисточников (LOTO) выполнена в соответствии с процедурой.",
    "Работник остановил работу при обнаружении небезопасного условия.",
    "Газоанализатор используется перед входом в замкнутое пространство.",
    "Все знаки безопасности установлены и хорошо видны.",
    "Рабочая зона ограждена в соответствии с требованиями.",
    "Водитель соблюдает скоростной режим и правила движения на территории.",
]

CATEGORY_MAP = {
    "СИЗ (средства индивидуальной защиты)": ["Нарушение использования СИЗ"],
    "Работа на высоте": ["Нарушение правил работы на высоте"],
    "LOTO (блокировка/маркировка)": ["Несоблюдение процедуры LOTO"],
    "Порядок на рабочем месте": ["Скользкая поверхность", "Отсутствие ограждений/барьеров"],
    "Электробезопасность": ["Неисправность оборудования"],
    "Газоопасные работы": ["Отсутствие газоанализатора"],
    "Грузоподъёмные операции": ["Неисправность оборудования"],
    "Ограждения и барьеры": ["Отсутствие ограждений/барьеров"],
    "Пожарная безопасность": ["Нарушение наряда-допуска"],
    "Транспортная безопасность": ["Несоблюдение скоростного режима"],
}


def seasonal_rate(date: pd.Timestamp) -> float:
    """Return seasonal multiplier: peaks in winter (Jan-Feb) and summer (Jul-Aug)."""
    day_of_year = date.day_of_year
    # Two peaks via combined sine waves
    winter_peak = np.sin(2 * np.pi * (day_of_year - 15) / 365) * (-1)  # Peak near Jan
    summer_peak = np.sin(2 * np.pi * (day_of_year - 200) / 365)  # Peak near Jul
    return 1.0 + 0.3 * max(winter_peak, 0) + 0.2 * max(summer_peak, 0)


def generate_incidents() -> pd.DataFrame:
    """Generate 550+ incident records over 3 years."""
    dates = pd.date_range(DATE_START, DATE_END, freq="D")
    types = list(INCIDENT_TYPES.keys())
    weights = [INCIDENT_TYPES[t]["weight"] for t in types]

    records = []
    incident_id = 1

    for date in dates:
        rate = seasonal_rate(date)
        # Base: ~0.55 incidents per day -> ~600 over 3 years
        n_incidents = rng.poisson(0.55 * rate)
        for _ in range(n_incidents):
            inc_type = rng.choice(types, p=weights)
            org = rng.choice(ORGANIZATIONS, p=[o["risk_base"] / sum(o["risk_base"] for o in ORGANIZATIONS) for o in ORGANIZATIONS])
            location = rng.choice(LOCATIONS)
            description = rng.choice(INCIDENT_DESCRIPTIONS[inc_type])
            causes = rng.choice(CAUSE_TAGS, size=rng.integers(1, 4), replace=False).tolist()
            status = rng.choice(["closed", "closed", "closed", "investigating"], p=[0.7, 0.15, 0.1, 0.05])

            records.append({
                "id": f"INC-{incident_id:04d}",
                "date": date.strftime("%Y-%m-%d"),
                "type": inc_type,
                "type_label": INCIDENT_TYPES[inc_type]["label"],
                "severity": INCIDENT_TYPES[inc_type]["severity"],
                "org_id": org["id"],
                "org_name": org["name"],
                "location": location,
                "description": description,
                "causes": "|".join(causes),
                "status": status,
            })
            incident_id += 1

    return pd.DataFrame(records)


def generate_korgau_cards(incidents_df: pd.DataFrame) -> pd.DataFrame:
    """Generate 1200+ korgau cards with violation clusters preceding incident spikes."""
    dates = pd.date_range(DATE_START, DATE_END, freq="D")

    # Compute monthly incident counts to create correlated violations
    incidents_df["date_parsed"] = pd.to_datetime(incidents_df["date"])
    monthly_incidents = incidents_df.groupby(incidents_df["date_parsed"].dt.to_period("M")).size()

    records = []
    card_id = 1

    for date in dates:
        rate = seasonal_rate(date)

        # Check if incidents will spike in 2-4 weeks -> boost violations now
        future_dates = [date + pd.Timedelta(days=d) for d in range(14, 29)]
        future_month_periods = set()
        for fd in future_dates:
            if fd <= pd.Timestamp(DATE_END):
                future_month_periods.add(fd.to_period("M"))

        spike_boost = 1.0
        for period in future_month_periods:
            if period in monthly_incidents.index:
                month_count = monthly_incidents[period]
                avg_count = monthly_incidents.mean()
                if month_count > avg_count * 1.2:
                    spike_boost = max(spike_boost, 1.0 + (month_count - avg_count) / avg_count)

        # Base: ~1.1 korgau cards per day -> ~1200 over 3 years
        n_cards = rng.poisson(1.1 * rate * spike_boost)

        for _ in range(n_cards):
            org = rng.choice(ORGANIZATIONS, p=[o["risk_base"] / sum(o["risk_base"] for o in ORGANIZATIONS) for o in ORGANIZATIONS])
            is_bad = rng.random() < (0.6 + 0.1 * org["risk_base"])  # Higher risk orgs have more violations
            obs_type = "unsafe_condition" if is_bad else "safe_practice"
            category = rng.choice(KORGAU_CATEGORIES)
            description = rng.choice(KORGAU_BAD_DESCRIPTIONS if is_bad else KORGAU_GOOD_DESCRIPTIONS)

            # Overdue status for bad observations
            if is_bad:
                resolved = rng.choice(
                    ["resolved", "in_progress", "overdue"],
                    p=[0.5, 0.3, 0.2] if org["risk_base"] < 0.7 else [0.3, 0.3, 0.4],
                )
            else:
                resolved = "not_applicable"

            records.append({
                "id": f"KRG-{card_id:04d}",
                "date": date.strftime("%Y-%m-%d"),
                "obs_type": obs_type,
                "obs_type_label": "Опасное условие/действие" if is_bad else "Безопасная практика",
                "org_id": org["id"],
                "org_name": org["name"],
                "category": category,
                "description": description,
                "status": resolved,
            })
            card_id += 1

    return pd.DataFrame(records)


def save_organizations():
    """Save organizations reference data."""
    output_path = Path(__file__).parent / "organizations.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ORGANIZATIONS, f, ensure_ascii=False, indent=2)
    print(f"Organizations saved: {len(ORGANIZATIONS)} orgs -> {output_path}")


def main():
    output_dir = Path(__file__).parent

    print("Generating incidents...")
    incidents = generate_incidents()
    incidents_path = output_dir / "incidents.csv"
    incidents.to_csv(incidents_path, index=False, encoding="utf-8-sig")
    print(f"Incidents: {len(incidents)} rows -> {incidents_path}")

    print("Generating korgau cards...")
    korgau = generate_korgau_cards(incidents)
    korgau_path = output_dir / "korgau_cards.csv"
    korgau.to_csv(korgau_path, index=False, encoding="utf-8-sig")
    print(f"Korgau cards: {len(korgau)} rows -> {korgau_path}")

    save_organizations()
    print("Done!")


if __name__ == "__main__":
    main()
