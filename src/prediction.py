"""Time series forecasting and backtesting for incident prediction.

Uses statsmodels ExponentialSmoothing (Holt-Winters) for reliable deployment
on Streamlit Cloud without heavy dependencies like Prophet/cmdstan.
"""

import warnings

import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing

warnings.filterwarnings("ignore", category=FutureWarning)


def prepare_ts_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare monthly incident data for forecasting."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    monthly = df.groupby(df["date"].dt.to_period("M")).size().reset_index(name="y")
    monthly["ds"] = monthly["date"].dt.to_timestamp()
    return monthly[["ds", "y"]]


def forecast(df: pd.DataFrame, horizon_months: int = 12) -> pd.DataFrame:
    """Run Holt-Winters forecast on incident data.

    Returns DataFrame with ds, yhat, yhat_lower, yhat_upper.
    Adapts model complexity based on available data length.
    """
    ts_df = prepare_ts_data(df)

    y = ts_df.set_index("ds")["y"].asfreq("MS").fillna(0)

    # Adapt model to data length: need >= 2 full seasonal cycles (24 months) for seasonal
    n_months = len(y)
    if n_months >= 24:
        seasonal = "mul"
        seasonal_periods = 12
        trend = "add"
    elif n_months >= 6:
        seasonal = None
        seasonal_periods = None
        trend = "add"
    else:
        seasonal = None
        seasonal_periods = None
        trend = None

    model = ExponentialSmoothing(
        y,
        trend=trend,
        seasonal=seasonal,
        seasonal_periods=seasonal_periods,
        initialization_method="estimated",
    ).fit(optimized=True)

    # Forecast
    pred = model.forecast(horizon_months)

    # Build result with confidence intervals (approx +/- 1.28 * residual std = 80% CI)
    residuals = model.resid
    std = residuals.std()

    # Historical fitted values
    hist = pd.DataFrame({
        "ds": y.index,
        "yhat": model.fittedvalues.clip(lower=0).round(1),
        "yhat_lower": (model.fittedvalues - 1.28 * std).clip(lower=0).round(1),
        "yhat_upper": (model.fittedvalues + 1.28 * std).clip(lower=0).round(1),
        "is_forecast": False,
    })

    # Future predictions
    future = pd.DataFrame({
        "ds": pred.index,
        "yhat": pred.clip(lower=0).round(1),
        "yhat_lower": (pred - 1.28 * std).clip(lower=0).round(1),
        "yhat_upper": (pred + 1.28 * std).clip(lower=0).round(1),
        "is_forecast": True,
    })

    result = pd.concat([hist, future], ignore_index=True)
    return result


def backtest(df: pd.DataFrame, test_months: int = 6) -> dict:
    """Backtest model: train on all but last N months, evaluate on held-out."""
    ts_df = prepare_ts_data(df)

    if len(ts_df) <= test_months:
        return {"mae": None, "mape": None, "message": "Not enough data for backtesting"}

    y = ts_df.set_index("ds")["y"].asfreq("MS").fillna(0)

    train = y.iloc[:-test_months]
    test = y.iloc[-test_months:]

    # Adapt model to training data length
    n_train = len(train)
    if n_train >= 24:
        seasonal = "mul"
        seasonal_periods = 12
        trend = "add"
    elif n_train >= 6:
        seasonal = None
        seasonal_periods = None
        trend = "add"
    else:
        seasonal = None
        seasonal_periods = None
        trend = None

    model = ExponentialSmoothing(
        train,
        trend=trend,
        seasonal=seasonal,
        seasonal_periods=seasonal_periods,
        initialization_method="estimated",
    ).fit(optimized=True)

    pred = model.forecast(test_months)

    mae = np.abs(test.values - pred.values).mean()
    mape = (np.abs(test.values - pred.values) / np.clip(test.values, 1, None)).mean() * 100

    return {
        "mae": round(float(mae), 2),
        "mape": round(float(mape), 1),
        "test_months": test_months,
        "actual": test.values.tolist(),
        "predicted": pred.round(1).values.tolist(),
        "dates": [d.strftime("%Y-%m") for d in test.index],
    }
