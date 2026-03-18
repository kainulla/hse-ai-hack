"""HSE AI Analytics Dashboard - Streamlit application with 5 pages."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv()

from src.database import init_db, load_incidents, load_korgau, get_organizations
from src.analytics import compute_incident_trends, get_top_risk_zones, compute_correlation
from src.prediction import forecast, backtest
from src.alerts import generate_alerts
from src.recommendations import get_recommendations
from src.economics import compute_economics
from src.config import INCIDENT_TYPES, KORGAU_CATEGORIES, FORECAST_HORIZONS

# --- Page config ---
st.set_page_config(
    page_title="HSE AI Analytics",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Init DB ---
init_db()

# --- Sidebar navigation ---
st.sidebar.title("🛡️ HSE AI Analytics")
st.sidebar.markdown("AI-аналитика охраны труда")

page = st.sidebar.radio(
    "Навигация",
    ["📊 Обзор", "📈 Прогнозы", "🔔 Алерты Коргау", "💡 Рекомендации", "💰 Экономический эффект"],
)

# --- Sidebar filters ---
st.sidebar.markdown("---")
st.sidebar.markdown("### Фильтры")

orgs = get_organizations()
org_options = {"Все организации": None}
for o in orgs:
    org_options[o["org_name"]] = o["org_id"]

selected_org_name = st.sidebar.selectbox("Организация", list(org_options.keys()))
selected_org = org_options[selected_org_name]

date_col1, date_col2 = st.sidebar.columns(2)
date_from = date_col1.date_input("С", value=pd.Timestamp("2024-01-01"))
date_to = date_col2.date_input("По", value=pd.Timestamp("2026-12-31"))

selected_type = st.sidebar.selectbox(
    "Тип происшествия",
    ["Все"] + [v["label"] for v in INCIDENT_TYPES.values()],
)
type_key = None
if selected_type != "Все":
    for k, v in INCIDENT_TYPES.items():
        if v["label"] == selected_type:
            type_key = k
            break


def load_filtered_incidents():
    return load_incidents(
        org_id=selected_org,
        incident_type=type_key,
        date_from=str(date_from),
        date_to=str(date_to),
    )


def load_filtered_korgau():
    return load_korgau(
        org_id=selected_org,
        date_from=str(date_from),
        date_to=str(date_to),
    )


# ============================================================
# PAGE 1: Overview
# ============================================================
if page == "📊 Обзор":
    st.title("📊 Обзор происшествий")

    incidents = load_filtered_incidents()
    korgau = load_filtered_korgau()

    # KPI cards
    col1, col2, col3, col4 = st.columns(4)

    total = len(incidents)
    # Trend: compare last 6 months vs previous 6 months
    if len(incidents) > 0:
        incidents["date"] = pd.to_datetime(incidents["date"])
        max_date = incidents["date"].max()
        mid_date = max_date - pd.DateOffset(months=6)
        recent = len(incidents[incidents["date"] > mid_date])
        previous = len(incidents[incidents["date"] <= mid_date])
        trend_pct = ((recent - previous) / max(previous, 1)) * 100
    else:
        trend_pct = 0

    alerts = generate_alerts(org_id=selected_org)
    active_alerts = len([a for a in alerts if a["level"] in ("red", "orange")])

    risk_zones = get_top_risk_zones(n=1)
    top_risk = risk_zones[0]["risk_score"] if risk_zones else 0

    col1.metric("Всего происшествий", total, f"{trend_pct:+.0f}% тренд")
    col2.metric("Критических алертов", active_alerts)
    col3.metric("Макс. риск-скор", f"{top_risk:.2f}")
    violations_count = len(korgau[korgau["obs_type"] == "unsafe_condition"]) if len(korgau) > 0 else 0
    col4.metric("Нарушений (Коргау)", violations_count)

    st.markdown("---")

    # Charts row 1
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Динамика происшествий")
        if len(incidents) > 0:
            trends = compute_incident_trends(incidents)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trends["month_dt"], y=trends["count"],
                mode="lines+markers", name="Количество",
                line=dict(color="#1f77b4"),
            ))
            fig.add_trace(go.Scatter(
                x=trends["month_dt"], y=trends["ma_3"],
                mode="lines", name="СС (3 мес.)",
                line=dict(color="#ff7f0e", dash="dash"),
            ))
            fig.update_layout(
                xaxis_title="Месяц", yaxis_title="Количество",
                height=400, margin=dict(l=20, r=20, t=30, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных для отображения")

    with chart_col2:
        st.subheader("По типам происшествий")
        if len(incidents) > 0:
            type_counts = incidents["type_label"].value_counts().reset_index()
            type_counts.columns = ["Тип", "Количество"]
            fig = px.bar(
                type_counts, x="Количество", y="Тип",
                orientation="h",
                color="Количество",
                color_continuous_scale="Reds",
            )
            fig.update_layout(
                height=400, margin=dict(l=20, r=20, t=30, b=20),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных")

    # Charts row 2
    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.subheader("По организациям")
        if len(incidents) > 0:
            org_counts = incidents["org_name"].value_counts().head(8).reset_index()
            org_counts.columns = ["Организация", "Количество"]
            fig = px.bar(
                org_counts, x="Количество", y="Организация",
                orientation="h",
                color="Количество",
                color_continuous_scale="Blues",
            )
            fig.update_layout(
                height=400, margin=dict(l=20, r=20, t=30, b=20),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных")

    with chart_col4:
        st.subheader("Топ-5 зон риска")
        risk_zones = get_top_risk_zones(n=5)
        if risk_zones:
            rz_df = pd.DataFrame(risk_zones)
            fig = px.bar(
                rz_df, x="risk_score", y="org_name",
                orientation="h",
                color="risk_score",
                color_continuous_scale="YlOrRd",
                labels={"risk_score": "Риск-скор", "org_name": "Организация"},
            )
            fig.update_layout(
                height=400, margin=dict(l=20, r=20, t=30, b=20),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PAGE 2: Predictions
# ============================================================
elif page == "📈 Прогнозы":
    st.title("📈 Предиктивная аналитика")

    incidents = load_filtered_incidents()

    col1, col2 = st.columns([3, 1])
    with col2:
        horizon = st.selectbox("Горизонт прогноза (мес.)", FORECAST_HORIZONS, index=2)

    if len(incidents) > 0:
        with st.spinner("Построение прогноза..."):
            forecast_df = forecast(incidents, horizon_months=horizon)

        st.subheader(f"Прогноз инцидентов на {horizon} месяцев")
        fig = go.Figure()

        # Historical
        hist = forecast_df[~forecast_df["is_forecast"]]
        fig.add_trace(go.Scatter(
            x=hist["ds"], y=hist["yhat"],
            mode="lines", name="Исторические данные",
            line=dict(color="#1f77b4"),
        ))

        # Forecast
        fc = forecast_df[forecast_df["is_forecast"]]
        fig.add_trace(go.Scatter(
            x=fc["ds"], y=fc["yhat"],
            mode="lines+markers", name="Прогноз",
            line=dict(color="#ff7f0e"),
        ))

        # Confidence interval
        fig.add_trace(go.Scatter(
            x=pd.concat([fc["ds"], fc["ds"][::-1]]),
            y=pd.concat([fc["yhat_upper"], fc["yhat_lower"][::-1]]),
            fill="toself",
            fillcolor="rgba(255, 127, 14, 0.15)",
            line=dict(color="rgba(255,127,14,0)"),
            name="Доверительный интервал (80%)",
        ))

        fig.update_layout(
            xaxis_title="Месяц", yaxis_title="Количество инцидентов",
            height=500, margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Backtest metrics
        st.subheader("Валидация модели (бэктест)")
        with st.spinner("Бэктестирование..."):
            bt = backtest(incidents, test_months=6)

        if bt.get("mae") is not None:
            m1, m2, m3 = st.columns(3)
            m1.metric("MAE", f"{bt['mae']:.2f}")
            m2.metric("MAPE", f"{bt['mape']:.1f}%")
            m3.metric("Тестовый период", f"{bt['test_months']} мес.")

            # Backtest chart
            bt_df = pd.DataFrame({
                "Месяц": bt["dates"],
                "Факт": bt["actual"],
                "Прогноз": bt["predicted"],
            })
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=bt_df["Месяц"], y=bt_df["Факт"], name="Факт", marker_color="#1f77b4"))
            fig2.add_trace(go.Bar(x=bt_df["Месяц"], y=bt_df["Прогноз"], name="Прогноз", marker_color="#ff7f0e"))
            fig2.update_layout(barmode="group", height=350)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning(bt.get("message", "Недостаточно данных"))

        # Top risk zones
        st.subheader("Топ-5 зон риска")
        risk_zones = get_top_risk_zones(n=5)
        rz_df = pd.DataFrame(risk_zones)[["org_name", "risk_score", "total_incidents", "total_violations", "overdue_ratio"]]
        rz_df.columns = ["Организация", "Риск-скор", "Инциденты", "Нарушения", "Доля просроченных"]
        st.dataframe(rz_df, use_container_width=True, hide_index=True)
    else:
        st.info("Нет данных для прогнозирования")

# ============================================================
# PAGE 3: Korgau Alerts
# ============================================================
elif page == "🔔 Алерты Коргау":
    st.title("🔔 Аналитика Карт Коргау")

    # Alert panel
    st.subheader("Активные алерты")
    alerts = generate_alerts(org_id=selected_org)

    if alerts:
        for alert in alerts:
            level = alert["level"]
            emoji = {"red": "🔴", "orange": "🟠", "yellow": "🟡", "green": "🟢"}.get(level, "⚪")
            color = {"red": "#ff4b4b", "orange": "#ffa500", "yellow": "#ffd700", "green": "#00cc00"}.get(level, "#888")

            st.markdown(
                f"""<div style="border-left: 4px solid {color}; padding: 10px 15px; margin: 8px 0; background: rgba(0,0,0,0.02); border-radius: 4px;">
                <strong>{emoji} {alert['level_label']}</strong> — {alert['org_name']}<br/>
                {alert['message']}
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.success("Нет активных алертов")

    st.markdown("---")

    # Violation trends
    korgau = load_filtered_korgau()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Динамика нарушений")
        if len(korgau) > 0:
            korgau_copy = korgau.copy()
            korgau_copy["date"] = pd.to_datetime(korgau_copy["date"])
            violations = korgau_copy[korgau_copy["obs_type"] == "unsafe_condition"]
            if len(violations) > 0:
                monthly = violations.groupby(violations["date"].dt.to_period("M")).size().reset_index(name="count")
                monthly["month"] = monthly["date"].dt.to_timestamp()
                fig = px.line(monthly, x="month", y="count", markers=True)
                fig.update_layout(
                    xaxis_title="Месяц", yaxis_title="Нарушения",
                    height=400, margin=dict(l=20, r=20, t=30, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Рейтинг организаций по нарушениям")
        if len(korgau) > 0:
            violations = korgau[korgau["obs_type"] == "unsafe_condition"]
            if len(violations) > 0:
                org_ranking = violations["org_name"].value_counts().reset_index()
                org_ranking.columns = ["Организация", "Нарушения"]
                fig = px.bar(
                    org_ranking, x="Нарушения", y="Организация",
                    orientation="h", color="Нарушения",
                    color_continuous_scale="Reds",
                )
                fig.update_layout(
                    height=400, margin=dict(l=20, r=20, t=30, b=20),
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

    # Correlation scatter
    st.subheader("Корреляция: нарушения → инциденты")
    corr = compute_correlation()
    if corr["n_months"] > 0:
        c1, c2 = st.columns([3, 1])
        with c2:
            st.metric("Коэффициент Пирсона", f"{corr['correlation']:.3f}")
            st.metric("Месяцев в анализе", corr["n_months"])

        with c1:
            fig = px.scatter(
                x=corr["monthly_violations"],
                y=corr["monthly_incidents"],
                labels={"x": "Нарушения (Коргау)", "y": "Инциденты"},
                trendline="ols",
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PAGE 4: Recommendations
# ============================================================
elif page == "💡 Рекомендации":
    st.title("💡 Рекомендации по безопасности")

    # Org selector
    rec_org_name = st.selectbox(
        "Выберите организацию",
        [o["org_name"] for o in orgs],
        key="rec_org",
    )
    rec_org_id = None
    for o in orgs:
        if o["org_name"] == rec_org_name:
            rec_org_id = o["org_id"]
            break

    if rec_org_id:
        with st.spinner("Генерация рекомендаций..."):
            recommendations = get_recommendations(rec_org_id)

        source = recommendations[0].get("source", "rule_based") if recommendations else "rule_based"
        st.caption(f"Источник: {'🤖 AI (LLM)' if source == 'llm' else '📋 Правила (rule-based)'}")

        for i, rec in enumerate(recommendations, 1):
            priority = rec.get("priority", "medium")
            priority_colors = {
                "high": ("🔴", "#ff4b4b"),
                "medium": ("🟡", "#ffd700"),
                "low": ("🟢", "#00cc00"),
            }
            emoji, color = priority_colors.get(priority, ("⚪", "#888"))
            priority_label = {"high": "Высокий", "medium": "Средний", "low": "Низкий"}.get(priority, priority)
            category = rec.get("category", "")

            st.markdown(
                f"""<div style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 12px 0; border-left: 5px solid {color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0;">{i}. {rec['title']}</h4>
                    <span style="background: {color}22; color: {color}; padding: 2px 10px; border-radius: 12px; font-size: 0.85em;">
                        {emoji} {priority_label}
                    </span>
                </div>
                <p style="color: #666; font-size: 0.85em; margin: 4px 0;">{category}</p>
                <p style="margin: 8px 0 0 0;">{rec['description']}</p>
                </div>""",
                unsafe_allow_html=True,
            )

# ============================================================
# PAGE 5: Economic Impact
# ============================================================
elif page == "💰 Экономический эффект":
    st.title("💰 Экономический эффект от внедрения AI")

    with st.spinner("Расчёт экономического эффекта..."):
        econ = compute_economics()

    # KPI cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Предотвращённых НС",
        f"{econ['prevented']['lti']}",
        "в год",
    )
    col2.metric(
        "Предотвращённых микротравм",
        f"{econ['prevented']['microtrauma']}",
        "в год",
    )
    col3.metric(
        "Годовая экономия",
        econ["total_savings_formatted"],
    )
    col4.metric(
        "В долларах",
        econ["total_savings_usd"],
    )

    st.markdown("---")

    # Before/After table
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("До / После внедрения AI")
        comparison = pd.DataFrame({
            "Показатель": ["НС (LTI)", "Микротравмы", "Опасные ситуации", "Первая помощь", "Пожары", "ИТОГО"],
            "До AI (в год)": [
                econ["before"]["lti"], econ["before"]["microtrauma"],
                econ["before"]["near_miss"], econ["before"]["first_aid"],
                econ["before"]["fire"], econ["before"]["total"],
            ],
            "После AI (в год)": [
                econ["after"]["lti"], econ["after"]["microtrauma"],
                econ["after"]["near_miss"], econ["after"]["first_aid"],
                econ["after"]["fire"], econ["after"]["total"],
            ],
        })
        comparison["Снижение"] = comparison["До AI (в год)"] - comparison["После AI (в год)"]
        st.dataframe(comparison, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Структура экономии")
        breakdown = econ["savings_breakdown"]
        savings_data = pd.DataFrame([
            {"Статья": v["label"], "Сумма (₸)": v["amount"], "Детали": v["detail"]}
            for v in breakdown.values()
        ])
        fig = px.pie(
            savings_data, values="Сумма (₸)", names="Статья",
            color_discrete_sequence=px.colors.sequential.RdBu,
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Detailed breakdown
    st.subheader("Детализация экономии")
    for key, item in econ["savings_breakdown"].items():
        st.markdown(
            f"""<div style="display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #eee;">
            <div>
                <strong>{item['label']}</strong><br/>
                <span style="color: #888; font-size: 0.85em;">{item['detail']}</span>
            </div>
            <div style="text-align: right; font-size: 1.2em; font-weight: bold; color: #2ecc71;">
                {item['amount']:,.0f} ₸
            </div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""<div style="display: flex; justify-content: space-between; padding: 15px; background: #f0f9f0; border-radius: 8px; margin-top: 10px;">
        <div style="font-size: 1.3em; font-weight: bold;">ИТОГО годовая экономия</div>
        <div style="font-size: 1.5em; font-weight: bold; color: #27ae60;">{econ['total_savings_formatted']}</div>
        </div>""",
        unsafe_allow_html=True,
    )
