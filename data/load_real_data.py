"""ETL script to load real Excel data and convert to CSV format.

Reads:
- docs/prod-docs/Проишествия.xlsx (223 incidents)
- docs/prod-docs/<garbled_name>.xlsx (9917 korgau cards)

Outputs:
- data/incidents.csv
- data/korgau_cards.csv
- data/organizations.json
"""

import json
import glob
import sys
from pathlib import Path

import pandas as pd
import numpy as np

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DOCS_DIR = PROJECT_ROOT / "docs" / "prod-docs"
DATA_DIR = PROJECT_ROOT / "data"

# ---------------------------------------------------------------------------
# Incident type mapping
# ---------------------------------------------------------------------------

SEVERITY_MAP = {
    "Летальный случай (погиб)": 5,
    "Относится к тяжелым": 4,
    "Не относится к тяжелым": 2,
}

# Classification sub-type labels for OMP
OMP_CLASSIFICATION_MAP = {
    "Оказание медицинской помощи (без потери рабочего времени/микротравмы)": "micro_trauma",
    "Оказание медицинской помощи (Заболевание)": "health_deterioration",
    "Оказание медицинской помощи (Летальный случай по причине ухудшения здоровья)": "health_deterioration",
}

# Type labels in Russian
TYPE_LABELS = {
    "lti": "Несчастный случай (тяжёлый/летальный)",
    "nlti": "Несчастный случай (лёгкий)",
    "micro_trauma": "Микротравма / ОМП",
    "health_deterioration": "Ухудшение здоровья",
    "dtp": "Дорожно-транспортное происшествие",
    "incident": "Инцидент",
    "fire": "Пожар/возгорание",
    "dangerous_situation": "Опасная ситуация",
}

# Type severity defaults
TYPE_SEVERITY_DEFAULTS = {
    "lti": 5,
    "nlti": 3,
    "micro_trauma": 2,
    "health_deterioration": 2,
    "dtp": 3,
    "incident": 2,
    "fire": 4,
    "dangerous_situation": 1,
}


# ---------------------------------------------------------------------------
# Korgau obs_type mapping
# ---------------------------------------------------------------------------

KORGAU_OBS_TYPE_MAP = {
    "Хорошая практика": "good",
    "Предложение (инициатива)": "good",
}
# Everything else maps to "bad"


def _find_korgau_file() -> Path:
    """Find the korgau Excel file (garbled filename) in docs/prod-docs."""
    files = glob.glob(str(DOCS_DIR / "*.xlsx"))
    candidates = [f for f in files if "Проишествия" not in f]
    if not candidates:
        raise FileNotFoundError("Korgau Excel file not found in docs/prod-docs/")
    return Path(candidates[0])


def _generate_org_id(org_name: str, org_id_cache: dict) -> str:
    """Generate a stable org_id from org_name."""
    if org_name in org_id_cache:
        return org_id_cache[org_name]
    idx = len(org_id_cache) + 1
    org_id = f"org_{idx:03d}"
    org_id_cache[org_name] = org_id
    return org_id


def _determine_incident_type(row: pd.Series) -> str:
    """Determine incident type from binary flag columns."""
    severity_str = str(row.get("Тяжесть травмы", ""))

    # Check accident (NS)
    if pd.notna(row.get("Несчастный случай")):
        if severity_str in ("Летальный случай (погиб)", "Относится к тяжелым"):
            return "lti"
        return "nlti"

    # Check medical assistance / micro-trauma
    if pd.notna(row.get("Оказание Медицинской помощи/микротравма")):
        classification = str(row.get("Классификация ОМП", ""))
        mapped = OMP_CLASSIFICATION_MAP.get(classification, "micro_trauma")
        return mapped

    # Check DTP
    if pd.notna(row.get("Дорожно-транспортное происшествие")):
        return "dtp"

    # Check incident
    if pd.notna(row.get("Инцидент")):
        return "incident"

    # Check fire
    if pd.notna(row.get("Пожар/Возгорание")):
        return "fire"

    return "dangerous_situation"


def _determine_severity(row: pd.Series, inc_type: str) -> int:
    """Determine severity score from row data."""
    severity_str = row.get("Тяжесть травмы")
    if pd.notna(severity_str) and str(severity_str) in SEVERITY_MAP:
        return SEVERITY_MAP[str(severity_str)]
    return TYPE_SEVERITY_DEFAULTS.get(inc_type, 1)


def load_incidents() -> pd.DataFrame:
    """Load and transform incidents from Excel to CSV schema."""
    filepath = DOCS_DIR / "Проишествия.xlsx"
    df = pd.read_excel(filepath)
    print(f"Read {len(df)} raw incident rows from {filepath.name}")

    org_id_cache = {}
    records = []

    for idx, row in df.iterrows():
        # Parse date
        date_val = row.get("Дата возникновения происшествия")
        if pd.isna(date_val):
            continue
        try:
            date_parsed = pd.Timestamp(date_val)
        except Exception:
            continue

        # Organization
        org_name_raw = row.get("Наименование организации ДЗО")
        if pd.isna(org_name_raw):
            org_name = "Неизвестная организация"
        else:
            org_name = str(org_name_raw).strip()
        org_id = _generate_org_id(org_name, org_id_cache)

        # Type and severity
        inc_type = _determine_incident_type(row)
        severity = _determine_severity(row, inc_type)
        type_label = TYPE_LABELS.get(inc_type, inc_type)

        # Location: prefer Место происшествия, fallback to Структурное подразделение
        location = row.get("Место происшествия")
        if pd.isna(location):
            location = row.get("Структурное подразделение")
        if pd.isna(location):
            location = "Не указано"
        location = str(location).strip()

        # Description
        description = row.get("Краткое описание происшествия")
        if pd.isna(description):
            description = row.get("Обстоятельства НС (Что произошло)")
        if pd.isna(description):
            description = ""
        description = str(description).strip()

        # Causes
        causes = row.get("Предварительные причины")
        if pd.isna(causes):
            causes = ""
        else:
            causes = str(causes).strip()

        # Status: all real incidents are effectively closed/reported
        status = "closed"

        records.append({
            "id": f"INC-{len(records) + 1:04d}",
            "date": date_parsed.strftime("%Y-%m-%d"),
            "type": inc_type,
            "type_label": type_label,
            "severity": severity,
            "org_id": org_id,
            "org_name": org_name,
            "location": location,
            "description": description,
            "causes": causes,
            "status": status,
        })

    result = pd.DataFrame(records)
    print(f"Transformed {len(result)} incident records")
    print(f"  Types: {result['type'].value_counts().to_dict()}")
    print(f"  Date range: {result['date'].min()} to {result['date'].max()}")
    print(f"  Organizations: {result['org_id'].nunique()}")
    return result


def load_korgau() -> pd.DataFrame:
    """Load and transform korgau cards from Excel to CSV schema."""
    filepath = _find_korgau_file()
    df = pd.read_excel(filepath)
    print(f"Read {len(df)} raw korgau rows from {filepath.name}")

    org_id_cache = {}
    records = []

    for idx, row in df.iterrows():
        # Parse date
        date_val = row.get("Дата")
        if pd.isna(date_val):
            continue
        try:
            date_parsed = pd.Timestamp(date_val)
        except Exception:
            continue

        # Filter unreasonable dates (keep 2024-2026)
        if date_parsed.year < 2024 or date_parsed.year > 2026:
            continue

        # Organization
        org_name_raw = row.get("Организация")
        if pd.isna(org_name_raw):
            org_name = "Неизвестная организация"
        else:
            org_name = str(org_name_raw).strip()
        org_id = _generate_org_id(org_name, org_id_cache)

        # Observation type
        obs_type_raw = str(row.get("Тип наблюдения", "")).strip()
        obs_type = KORGAU_OBS_TYPE_MAP.get(obs_type_raw, "bad")
        # Map to existing schema values
        if obs_type == "bad":
            obs_type_code = "unsafe_condition"
            obs_type_label = obs_type_raw if obs_type_raw else "Небезопасное условие"
        else:
            obs_type_code = "safe_practice"
            obs_type_label = obs_type_raw if obs_type_raw else "Хорошая практика"

        # Category: take first one if comma-separated
        category_raw = row.get("Категория наблюдения")
        if pd.isna(category_raw):
            category = "Не указано"
        else:
            category = str(category_raw).split(",")[0].strip()

        # Description: combine observation + consequences
        desc_parts = []
        obs_desc = row.get("Опишите ваше наблюдение/предложение")
        if pd.notna(obs_desc):
            desc_parts.append(str(obs_desc).strip())
        consequences = row.get(
            "Какие возможные последствия наблюдения или преимущества хорошей практики / вашего предложения?"
        )
        if pd.notna(consequences):
            desc_parts.append(str(consequences).strip())
        description = " | ".join(desc_parts) if desc_parts else ""

        # Status
        status_raw = row.get(
            "Было ли небезопасное условие / поведение исправлено и опасность устранена?"
        )
        if obs_type_code == "safe_practice":
            status = "not_applicable"
        elif pd.isna(status_raw):
            status = "in_progress"
        elif status_raw is True or str(status_raw).lower() == "true":
            status = "resolved"
        else:
            status = "open"

        records.append({
            "id": f"KRG-{len(records) + 1:05d}",
            "date": date_parsed.strftime("%Y-%m-%d"),
            "obs_type": obs_type_code,
            "obs_type_label": obs_type_label,
            "org_id": org_id,
            "org_name": org_name,
            "category": category,
            "description": description,
            "status": status,
        })

    result = pd.DataFrame(records)
    print(f"Transformed {len(result)} korgau records (after date filtering)")
    print(f"  Obs types: {result['obs_type'].value_counts().to_dict()}")
    print(f"  Date range: {result['date'].min()} to {result['date'].max()}")
    print(f"  Organizations: {result['org_id'].nunique()}")
    print(f"  Categories: {result['category'].nunique()}")
    return result


def build_organizations(incidents_df: pd.DataFrame, korgau_df: pd.DataFrame) -> list[dict]:
    """Build unified organizations list from both datasets."""
    org_map = {}

    for df in [incidents_df, korgau_df]:
        for _, row in df[["org_id", "org_name"]].drop_duplicates().iterrows():
            oid = row["org_id"]
            if oid not in org_map:
                org_map[oid] = {
                    "id": oid,
                    "name": row["org_name"],
                    "type": "contractor",
                    "risk_base": 0.5,
                }

    orgs = sorted(org_map.values(), key=lambda o: o["id"])
    print(f"Built {len(orgs)} organizations")
    return orgs


def main():
    print("=" * 60)
    print("Loading real data from Excel files")
    print("=" * 60)

    # Load and transform
    incidents = load_incidents()
    korgau = load_korgau()

    # Save CSVs
    incidents_path = DATA_DIR / "incidents.csv"
    incidents.to_csv(incidents_path, index=False, encoding="utf-8-sig")
    print(f"\nSaved incidents: {len(incidents)} rows -> {incidents_path}")

    korgau_path = DATA_DIR / "korgau_cards.csv"
    korgau.to_csv(korgau_path, index=False, encoding="utf-8-sig")
    print(f"Saved korgau cards: {len(korgau)} rows -> {korgau_path}")

    # Build and save organizations
    orgs = build_organizations(incidents, korgau)
    orgs_path = DATA_DIR / "organizations.json"
    with open(orgs_path, "w", encoding="utf-8") as f:
        json.dump(orgs, f, ensure_ascii=False, indent=2)
    print(f"Saved organizations: {len(orgs)} orgs -> {orgs_path}")

    # Delete old DB so it gets rebuilt on next app start
    db_path = DATA_DIR / "hse.db"
    if db_path.exists():
        db_path.unlink()
        print(f"Deleted old database: {db_path}")

    print("\nDone!")
    print("=" * 60)


if __name__ == "__main__":
    main()
