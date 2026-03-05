"""Prophet forecasting and backtesting for incident prediction."""

import warnings

import pandas as pd
import numpy as np

warnings.filterwarnings("ignore", category=FutureWarning)


def prepare_prophet_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare monthly incident data for Prophet."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    monthly = df.groupby(df["date"].dt.to_period("M")).size().reset_index(name="y")
    monthly["ds"] = monthly["date"].dt.to_timestamp()
    return monthly[["ds", "y"]]


def forecast(df: pd.DataFrame, horizon_months: int = 12) -> pd.DataFrame:
    """Run Prophet forecast on incident data.

    Returns DataFrame with ds, yhat, yhat_lower, yhat_upper.
    """
    from prophet import Prophet

    prophet_df = prepare_prophet_data(df)

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.8,
        seasonality_mode="multiplicative",
        changepoint_prior_scale=0.1,
    )
    model.fit(prophet_df)

    future = model.make_future_dataframe(periods=horizon_months, freq="MS")
    prediction = model.predict(future)

    result = prediction[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    result["yhat"] = result["yhat"].clip(lower=0).round(1)
    result["yhat_lower"] = result["yhat_lower"].clip(lower=0).round(1)
    result["yhat_upper"] = result["yhat_upper"].clip(lower=0).round(1)

    # Mark historical vs forecast
    last_date = prophet_df["ds"].max()
    result["is_forecast"] = result["ds"] > last_date

    return result


def backtest(df: pd.DataFrame, test_months: int = 6) -> dict:
    """Backtest Prophet model: train on all but last N months, evaluate on held-out."""
    from prophet import Prophet

    prophet_df = prepare_prophet_data(df)

    if len(prophet_df) <= test_months:
        return {"mae": None, "mape": None, "message": "Not enough data for backtesting"}

    train = prophet_df.iloc[:-test_months]
    test = prophet_df.iloc[-test_months:]

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode="multiplicative",
        changepoint_prior_scale=0.1,
    )
    model.fit(train)

    future = model.make_future_dataframe(periods=test_months, freq="MS")
    prediction = model.predict(future)

    # Get predictions for test period
    pred_test = prediction[prediction["ds"].isin(test["ds"])]
    merged = test.merge(pred_test[["ds", "yhat"]], on="ds")

    mae = np.abs(merged["y"] - merged["yhat"]).mean()
    mape = (np.abs(merged["y"] - merged["yhat"]) / merged["y"].clip(lower=1)).mean() * 100

    return {
        "mae": round(float(mae), 2),
        "mape": round(float(mape), 1),
        "test_months": test_months,
        "actual": merged["y"].tolist(),
        "predicted": merged["yhat"].round(1).tolist(),
        "dates": [d.strftime("%Y-%m") for d in merged["ds"]],
    }
