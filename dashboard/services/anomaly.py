
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sklearn.ensemble import IsolationForest

from dashboard.services.prediction import DATA_PATH


# Required dataset columns
REQUIRED_COLUMNS = [
    "timestamp",
    "temperature",
    "is_holiday",
    "hvac_state",
    "kw_consumed"
]


@lru_cache(maxsize=1)
def analyze_energy_anomalies():
    """
    Analyze historical energy data once per server process.
    Cache the completed Isolation Forest analysis.
    """

    # 1. Check dataset availability
    if not Path(DATA_PATH).exists():
        raise FileNotFoundError(
            f"Energy dataset not found: {DATA_PATH}"
        )

    # 2. Load only required columns
    df = pd.read_csv(
        DATA_PATH,
        usecols=REQUIRED_COLUMNS
    )

    # 3. Convert timestamp
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    # 4. Convert numeric columns safely
    numeric_columns = [
        "temperature",
        "is_holiday",
        "kw_consumed"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # 5. Normalize HVAC states
    df["hvac_state"] = (
        df["hvac_state"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    # Remove invalid or incomplete records
    df = df.dropna(
        subset=REQUIRED_COLUMNS
    ).copy()

    if len(df) < 50:
        raise ValueError(
            "Not enough valid records for anomaly detection."
        )

    # 6. Convert HVAC state into numeric values
    df["hvac_on"] = df["hvac_state"].map({
        "ON": 1,
        "OFF": 0
    })

    if df["hvac_on"].isna().any():
        raise ValueError(
            "Dataset contains an unknown HVAC state."
        )

    # 7. Extract time-based features
    df["hour"] = df["timestamp"].dt.hour

    df["day_of_week"] = (
        df["timestamp"].dt.dayofweek
    )

    df["month"] = df["timestamp"].dt.month

    df["is_weekend"] = (
        df["day_of_week"] >= 5
    ).astype(int)

    # 8. Prepare model features
    feature_columns = [
        "temperature",
        "is_holiday",
        "hvac_on",
        "kw_consumed",
        "hour",
        "day_of_week",
        "month",
        "is_weekend"
    ]

    X = df[feature_columns].astype(float)

    # 9. Create Isolation Forest model
    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42
    )

    # 10. Detect unusual energy records
    df["anomaly_label"] = model.fit_predict(X)

    # 11. Calculate anomaly scores
    df["anomaly_score"] = (
        -model.decision_function(X)
    )

    # -1 = unusual record
    #  1 = normal record
    anomalies = df[
        df["anomaly_label"] == -1
    ].copy()

    # 12. Sort by highest anomaly score
    anomalies = anomalies.sort_values(
        by="anomaly_score",
        ascending=False
    )

    # 13. Prepare dashboard records
    anomaly_records = []

    for row in anomalies.itertuples():

        anomaly_records.append({
            "timestamp": row.timestamp.strftime(
                "%Y-%m-%d %H:%M"
            ),
            "temperature": round(
                float(row.temperature), 2
            ),
            "hvac_state": str(row.hvac_state),
            "energy": round(
                float(row.kw_consumed), 2
            ),
            "anomaly_score": round(
                float(row.anomaly_score), 4
            )
        })

    # 14. Calculate anomaly statistics
    total_records = len(df)
    total_anomalies = len(anomalies)

    return {
        "total_records": total_records,
        "total_anomalies": total_anomalies,
        "anomaly_percentage": round(
            (total_anomalies / total_records) * 100,
            2
        ),
        "anomalies": anomaly_records
    }


def detect_energy_anomalies(limit=10):
    """
    Return cached anomaly analysis for the dashboard.
    """

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise ValueError(
            "Anomaly record limit must be an integer."
        )

    if limit < 0:
        raise ValueError(
            "Anomaly record limit cannot be negative."
        )

    # Reuse cached analysis
    result = analyze_energy_anomalies()

    # Return a separate result dictionary
    return {
        "total_records": result["total_records"],
        "total_anomalies": result["total_anomalies"],
        "anomaly_percentage": result["anomaly_percentage"],
        "anomalies": result["anomalies"][:limit]
    }
