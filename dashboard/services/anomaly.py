
import pandas as pd
from sklearn.ensemble import IsolationForest

from dashboard.services.prediction import DATA_PATH


def detect_energy_anomalies(limit=10):
    """
    Detect unusual energy-consumption patterns
    in historical building energy data.
    """

    # 1. Load historical dataset
    df = pd.read_csv(DATA_PATH)

    # 2. Convert timestamp into datetime
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    # 3. Remove invalid records
    df = df.dropna(
        subset=[
            "timestamp",
            "temperature",
            "is_holiday",
            "hvac_state",
            "kw_consumed"
        ]
    ).copy()

    if len(df) < 50:
        raise ValueError(
            "Not enough valid records for anomaly detection."
        )

    # 4. Extract time-based features
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["month"] = df["timestamp"].dt.month
    df["is_weekend"] = (
        df["day_of_week"] >= 5
    ).astype(int)

    # 5. Convert HVAC state into numeric values
    df["hvac_on"] = (
        df["hvac_state"]
        .astype(str)
        .str.upper()
        .map({"ON": 1, "OFF": 0})
    )

    if df["hvac_on"].isna().any():
        raise ValueError(
            "Dataset contains an unknown HVAC state."
        )

    # 6. Select model features
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

    # 7. Create Isolation Forest model
    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42
    )

    # 8. Train and detect anomalies
    df["anomaly_label"] = model.fit_predict(X)

    # 9. Calculate anomaly scores
    df["anomaly_score"] = -model.decision_function(X)

    # -1 means unusual record
    #  1 means normal record
    anomalies = df[df["anomaly_label"] == -1].copy()

    # 10. Sort by highest anomaly score
    anomalies = anomalies.sort_values(
        by="anomaly_score",
        ascending=False
    )

    # 11. Prepare dashboard records
    anomaly_records = []

    for _, row in anomalies.head(limit).iterrows():
        anomaly_records.append({
            "timestamp": row["timestamp"].strftime(
                "%Y-%m-%d %H:%M"
            ),
            "temperature": round(
                float(row["temperature"]), 2
            ),
            "hvac_state": str(row["hvac_state"]),
            "energy": round(
                float(row["kw_consumed"]), 2
            ),
            "anomaly_score": round(
                float(row["anomaly_score"]), 4
            )
        })

    # 12. Return results
    total_records = len(df)
    total_anomalies = len(anomalies)

    return {
        "total_records": total_records,
        "total_anomalies": total_anomalies,
        "anomaly_percentage": round(
            (total_anomalies / total_records) * 100, 2
        ),
        "anomalies": anomaly_records
    }
