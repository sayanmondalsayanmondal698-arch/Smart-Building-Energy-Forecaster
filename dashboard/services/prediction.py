
from pathlib import Path

import joblib
import pandas as pd


# Project base directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Machine Learning model directory
MODEL_DIR = BASE_DIR / "ml_models"

# Dataset location inside the web_app folder
DATA_PATH = BASE_DIR / "data" / "building_energy.csv"


# Load the trained Random Forest model
model = joblib.load(
    MODEL_DIR / "energy_forecasting_model.pkl"
)

# Load the model feature names
features = joblib.load(
    MODEL_DIR / "model_features.pkl"
)


def generate_predictions(weather_data, is_holiday=0):

    # Validate weather input
    if len(weather_data) != 24:
        raise ValueError(
            "Please provide exactly 24 hourly weather records."
        )

    # Check dataset availability
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Energy dataset not found: {DATA_PATH}"
        )

    # Load historical energy data
    df = pd.read_csv(DATA_PATH)

    # Process timestamps
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["timestamp", "kw_consumed"]
    )

    df = df.sort_values("timestamp")

    history = df["kw_consumed"].astype(float).tolist()

    if len(history) < 168:
        raise ValueError(
            "At least 168 historical hourly records are required."
        )

    predictions = []

    # Generate predictions for the next 24 hours
    for item in weather_data:

        timestamp = pd.Timestamp(
            item["timestamp"]
        )

        temperature = float(
            item["temperature"]
        )

        hour = timestamp.hour
        day_of_week = timestamp.dayofweek

        # Prepare prediction features
        row = {
            "temperature": temperature,
            "is_holiday": int(is_holiday),
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

        # Create input DataFrame in model feature order
        input_df = pd.DataFrame(
            [[row[column] for column in features]],
            columns=features
        )

        # Predict energy consumption
        prediction = float(
            model.predict(input_df)[0]
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

        # Use prediction as history for the next hour
        history.append(prediction)

    return predictions
