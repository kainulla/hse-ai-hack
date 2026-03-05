"""FastAPI REST endpoints for HSE AI Analytics."""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from src.database import init_db, load_incidents, load_korgau, get_organizations
from src.analytics import compute_incident_trends, get_top_risk_zones, compute_correlation
from src.prediction import forecast, backtest
from src.alerts import generate_alerts
from src.recommendations import get_recommendations
from src.economics import compute_economics

app = FastAPI(
    title="HSE AI Analytics API",
    description="AI-аналитика для системы охраны труда в нефтегазовой отрасли",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/orgs")
def api_orgs():
    """Get list of organizations."""
    return get_organizations()


@app.get("/api/incidents")
def api_incidents(
    org_id: str | None = Query(None),
    type: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    """Get incidents with optional filters."""
    df = load_incidents(org_id=org_id, incident_type=type, date_from=date_from, date_to=date_to)
    return df.to_dict("records")


@app.get("/api/korgau")
def api_korgau(
    org_id: str | None = Query(None),
    category: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    """Get korgau cards with optional filters."""
    df = load_korgau(org_id=org_id, category=category, date_from=date_from, date_to=date_to)
    return df.to_dict("records")


@app.get("/api/forecast/{horizon}")
def api_forecast(horizon: int = 12):
    """Get incident forecast for given horizon (months)."""
    df = load_incidents()
    result = forecast(df, horizon_months=horizon)
    return result.to_dict("records")


@app.get("/api/risk-zones")
def api_risk_zones(n: int = Query(5)):
    """Get top N risk zones by risk score."""
    return get_top_risk_zones(n=n)


@app.get("/api/alerts")
def api_alerts(org_id: str | None = Query(None)):
    """Get active alerts."""
    return generate_alerts(org_id=org_id)


@app.get("/api/recommendations/{org_id}")
def api_recommendations(org_id: str):
    """Get recommendations for an organization."""
    return get_recommendations(org_id)


@app.get("/api/economics")
def api_economics():
    """Get economic impact analysis."""
    return compute_economics()


@app.get("/api/correlation")
def api_correlation():
    """Get correlation between violations and incidents."""
    return compute_correlation()
