
import logging

from django.shortcuts import render

from .services.prediction import generate_predictions
from .services.weather import get_hourly_weather
from .services.anomaly import detect_energy_anomalies


# Application logger
logger = logging.getLogger(__name__)


def home(request):

    # 1. Initialize dashboard values
    context = {
        "predictions": [],
        "weather_data": [],
        "total_energy": 0,
        "average_energy": 0,
        "current_temperature": None,
        "weather_error": None,
        "anomaly_data": {
            "total_records": 0,
            "total_anomalies": 0,
            "anomaly_percentage": 0,
            "anomalies": [],
        },
        "anomaly_error": None,
    }

    # 2. Get weather and generate energy predictions
    try:

        weather_data = get_hourly_weather()

        predictions = generate_predictions(
            weather_data,
            is_holiday=0
        )

        # Calculate total predicted energy
        total_energy = round(
            sum(
                item["predicted_energy"]
                for item in predictions
            ),
            2
        )

        # Calculate average hourly energy
        average_energy = round(
            total_energy / len(predictions),
            2
        ) if predictions else 0

        # Update dashboard context
        context.update({
            "predictions": predictions,
            "weather_data": weather_data,
            "total_energy": total_energy,
            "average_energy": average_energy,
            "current_temperature": (
                weather_data[0]["temperature"]
                if weather_data else None
            ),
        })

    except Exception as error:

        logger.exception(
            "Energy forecasting failed."
        )

        context["weather_error"] = str(error)

    # 3. Detect historical energy anomalies
    try:

        anomaly_data = detect_energy_anomalies(
            limit=10
        )

        context["anomaly_data"] = anomaly_data

    except Exception as error:

        logger.exception(
            "HVAC anomaly detection failed."
        )

        context["anomaly_error"] = str(error)

    # 4. Render the dashboard
    return render(
        request,
        "dashboard/home.html",
        context
    )
