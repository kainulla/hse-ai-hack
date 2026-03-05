# Implementation Steps (High-Level)

## Tech Stack

- **Backend/ML**: Python (FastAPI + pandas + scikit-learn + Prophet)
- **NLP**: OpenAI/Claude API for text classification & recommendations
- **Frontend**: Streamlit (fastest for hackathon) or Next.js + Recharts
- **DB**: SQLite or PostgreSQL for structured data

---

## Step 1: Data Layer

Load `incidents.csv` and `korgau_cards.csv` into structured storage. Clean dates, normalize categories, handle missing values. Create joined views linking violations to incidents by org/location/time.

## Step 2: EDA & Pattern Analysis

Basic statistics: incidents by type, org, location, time (season/weekday/hour). Korgau cards: violation frequency by category, org, trend over time. Find correlation between korgau violation spikes and subsequent incidents.

## Step 3: ML Models

- **Classification (F-01, F-15)**: Use LLM API to classify incident descriptions by type and korgau observations by thematic cluster (PPE, LOTO, heights, etc.)
- **Time Series Prediction (F-06)**: Prophet model on monthly incident counts. Output: forecast for 3/6/12 months with confidence intervals.
- **Risk Scoring (F-02, F-03)**: Score each org/location based on incident history + korgau violations. Simple weighted formula: `risk = w1*incident_count + w2*violation_trend + w3*severity_avg`
- **Correlation (F-13)**: Pearson/Spearman between korgau violation rate and incident rate per org. Show: "orgs with rising violations have X% higher incident probability"

## Step 4: Recommendations Engine

Use LLM (Claude/GPT) with a prompt template:
- Input: top risk factors for org/location, recent violations, incident history
- Output: 3-5 specific actionable safety recommendations with priority

Fallback: rule-based recommendations from a predefined mapping (violation category -> standard safety measures).

## Step 5: Alert System

Simple threshold logic on korgau data:
- Red: violations > 2x threshold in period
- Orange: same violation type > 3 times in 30 days per org
- Yellow: trend growing > 15% vs same period last year
- Green: improvement notification

Store alerts, show on dashboard, optionally push to Telegram via bot API.

## Step 6: Economic Impact Calculator

Predefined cost model from PRD section 8.2:
- Cost per incident by type (NS = 5M tenge, mictrauma = X, etc.)
- Calculate: `savings = prevented_incidents * cost_per_incident * (1 + indirect_multiplier)`
- Show KPI cards: "7 prevented accidents", "~121M tenge saved/year"

## Step 7: Dashboard UI

**Page 1 - Overview**: KPI cards (total incidents, trends, risk level, economic impact). Charts: incidents over time, by type, by org.

**Page 2 - Predictions**: Prophet forecast chart with confidence bands. Top-5 risk zones table (org + location + risk score).

**Page 3 - Korgau Analytics**: Violation trends, org ranking, active alerts (color-coded). Correlation chart: violations vs incidents.

**Page 4 - Recommendations**: AI-generated recommendations per org/location. Priority-sorted list with rationale.

**Page 5 - Economic Effect**: Before/after comparison table. ROI calculation, savings breakdown.

## Step 8: Integration & Polish

- FastAPI endpoints for all analytics (for future HSE system integration)
- PDF export of key reports (weasyprint or reportlab)
- Prepare demo scenario & presentation

---

## Simplified Architecture

```
CSV files
  |
  v
Python ETL (pandas) --> SQLite/PostgreSQL
  |
  v
ML Layer (Prophet + sklearn + LLM API)
  |
  v
FastAPI (REST endpoints)
  |
  v
Streamlit Dashboard (charts, tables, KPIs, alerts)
```

## Priority Order for Hackathon

1. Data loading + EDA (foundation for everything)
2. Dashboard with basic stats (visible result fast)
3. Prediction model (core differentiator, 25% of score)
4. Alert system (15% of score)
5. Recommendations via LLM (20% of score)
6. Economic calculator (10% of score)
7. Polish UI/UX (15% of score)
8. API docs + integration story (15% of score)
