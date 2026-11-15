
import logging

from django.shortcuts import render

from .services.prediction import (
    generate_predictions,
    generate_fallback_weather
)

from .services.weather import get_hourly_weather
from .services.anomaly import detect_energy_anomalies


logger = logging.getLogger(__name__)


def home(request):

    context = {
        "predictions": [],
        "weather_data": [],
        "total_energy": 0,
        "average_energy": 0,
        "current_temperature": None,
        "weather_error": None,
        "prediction_error": None,
        "weather_is_estimated": False,

        "anomaly_data": {
            "total_records": 0,
            "total_anomalies": 0,
            "anomaly_percentage": 0,
            "anomalies": [],
        },

        "anomaly_error": None,
    }

    # Get live weather
    weather_data = None

    try:
        weather_data = get_hourly_weather()

    except Exception as error:

        logger.exception("Live weather retrieval failed.")

        context["weather_error"] = str(error)

        # Use historical temperature estimates
        try:
            weather_data = generate_fallback_weather()

            context["weather_is_estimated"] = True

            logger.warning(
                "Using historical temperature estimates."
            )

        except Exception as fallback_error:

            logger.exception(
                "Historical weather fallback failed."
            )

            context["prediction_error"] = str(
                fallback_error
            )

    # Generate energy predictions
    if weather_data is not None:

        try:
            predictions = generate_predictions(
                weather_data,
                is_holiday=0
            )

            total_energy = round(
                sum(
                    item["predicted_energy"]
                    for item in predictions
                ),
                2
            )

            average_energy = round(
                total_energy / len(predictions),
                2
            ) if predictions else 0

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

            context["prediction_error"] = str(error)

    # Run anomaly detection independently
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

    return render(
        request,
        "dashboard/home.html",
        context
    )
