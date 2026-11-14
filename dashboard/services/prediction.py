
from pathlib import Path
from functools import lru_cache
import math

import joblib
import pandas as pd


# Project base directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Machine Learning model directory
MODEL_DIR = BASE_DIR / "ml_models"

# Historical energy dataset
DATA_PATH = BASE_DIR / "data" / "building_energy.csv"


# Load the trained Random Forest model once
model = joblib.load(
    MODEL_DIR / "energy_forecasting_model.pkl"
)

# Load model feature names once
features = joblib.load(
    MODEL_DIR / "model_features.pkl"
)

# Check model features once during startup
required_model_features = {
    "temperature",
    "is_holiday",
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "lag_24",
    "lag_48",
    "lag_168",
    "rolling_24",
    "rolling_168",
}

missing_model_features = (
    required_model_features - set(features)
)

if missing_model_features:
    raise ValueError(
        f"Model is missing required features: "
        f"{sorted(missing_model_features)}"
    )


@lru_cache(maxsize=1)
def load_historical_energy():
    """
    Load historical energy readings once per server process.
    Cache the readings to avoid repeatedly reading the CSV.
    """

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Energy dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(
        DATA_PATH,
        usecols=["timestamp", "kw_consumed"]
    )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    df["kw_consumed"] = pd.to_numeric(
        df["kw_consumed"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["timestamp", "kw_consumed"]
    )

    df = df.sort_values("timestamp")

    history = tuple(
        df["kw_consumed"].astype(float).tolist()
    )

    if len(history) < 168:
        raise ValueError(
            "At least 168 historical hourly records are required."
        )

    return history


def generate_predictions(weather_data, is_holiday=0):
    """
    Generate recursive 24-hour energy predictions
    using the trained Random Forest model.
    """

    # Validate weather input
    if not isinstance(weather_data, (list, tuple)):
        raise ValueError(
            "Weather data must be a list of hourly records."
        )

    if len(weather_data) != 24:
        raise ValueError(
            "Please provide exactly 24 hourly weather records."
        )

    # Validate holiday input
    try:
        is_holiday = int(is_holiday)
    except (TypeError, ValueError):
        raise ValueError(
            "Holiday value must be 0 or 1."
        )

    if is_holiday not in (0, 1):
        raise ValueError(
            "Holiday value must be 0 or 1."
        )

    # Get cached historical readings
    history = list(load_historical_energy())

    predictions = []

    # Generate the next 24 hourly predictions
    for item in weather_data:

        if not isinstance(item, dict):
            raise ValueError(
                "Each weather record must be a dictionary."
            )

        try:
            timestamp = pd.Timestamp(
                item["timestamp"]
            )

            temperature = float(
                item["temperature"]
            )

        except (KeyError, TypeError, ValueError):
            raise ValueError(
                "Weather record contains an invalid timestamp "
                "or temperature."
            )

        if pd.isna(timestamp):
            raise ValueError(
                "Weather record contains an invalid timestamp."
            )

        if not math.isfinite(temperature):
            raise ValueError(
                "Weather temperature must be a finite number."
            )

        hour = timestamp.hour
        day_of_week = timestamp.dayofweek

        # Prepare model input features
        row = {
            "temperature": temperature,
            "is_holiday": is_holiday,
            "hour": hour,
            "day_of_week": day_of_week,
            "month": timestamp.month,
            "is_weekend": int(day_of_week >= 5),
            "lag_24": history[-24],
            "lag_48": history[-48],
            "lag_168": history[-168],
            "rolling_24": sum(history[-24:]) / 24,
            "rolling_168": sum(history[-168:]) / 168,
        }

        # Maintain the original model feature order
        input_df = pd.DataFrame(
            [[row[column] for column in features]],
            columns=features
        )

        # Generate energy prediction
        prediction = float(
            model.predict(input_df)[0]
        )

        # Prevent negative or invalid predictions
        if not math.isfinite(prediction):
            raise ValueError(
                "The model generated an invalid prediction."
            )

        prediction = max(0, prediction)

        # Store prediction result
        predictions.append({
            "timestamp": timestamp.strftime(
                "%Y-%m-%d %H:%M"
            ),
            "hour": hour,
            "temperature": round(temperature, 2),
            "predicted_energy": round(prediction, 2)
        })

        # Add prediction to history for recursive forecasting
        history.append(prediction)

    return predictions
