
import json
from urllib.parse import urlencode
from urllib.request import urlopen
from datetime import datetime
from zoneinfo import ZoneInfo


# Building location: Kolkata, West Bengal, India
LATITUDE = 22.5726
LONGITUDE = 88.3639
TIMEZONE = "Asia/Kolkata"


def get_hourly_weather():

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "temperature_2m",
        "forecast_days": 2,
        "timezone": TIMEZONE
    }

    url = (
        "https://api.open-meteo.com/v1/forecast?"
        + urlencode(params)
    )

    try:
        # Get weather data from Open-Meteo
        with urlopen(url, timeout=20) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        hourly = data["hourly"]

        times = hourly["time"]
        temperatures = hourly["temperature_2m"]

        # Current Kolkata time (timezone-naive for comparison)
        now = datetime.now(
            ZoneInfo(TIMEZONE)
        ).replace(
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=None
        )

        weather_data = []

        # Collect the next 24 hourly temperatures
        for timestamp, temperature in zip(times, temperatures):

            forecast_time = datetime.fromisoformat(timestamp)

            if forecast_time >= now:

                weather_data.append({
                    "timestamp": timestamp,
                    "temperature": float(temperature)
                })

            if len(weather_data) == 24:
                break

        # Ensure exactly 24 records are available
        if len(weather_data) != 24:
            raise ValueError(
                "Could not retrieve 24 hourly temperatures."
            )

        return weather_data

    except Exception as error:

        raise RuntimeError(
            f"Weather API error: {error}"
        ) from error
