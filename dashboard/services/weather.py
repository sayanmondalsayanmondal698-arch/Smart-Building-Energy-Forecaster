import json
from urllib.parse import urlencode
from urllib.request import urlopen
from datetime import datetime
from zoneinfo import ZoneInfo

from django.core.cache import cache


LATITUDE = 22.5726
LONGITUDE = 88.3639
TIMEZONE = "Asia/Kolkata"

WEATHER_CACHE_KEY = "smart_building_weather_v1"
WEATHER_CACHE_SECONDS = 600


def get_hourly_weather():

    # Reuse recently retrieved weather data.
    cached_weather = cache.get(WEATHER_CACHE_KEY)

    if cached_weather is not None:
        return cached_weather

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
        with urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        hourly = data["hourly"]

        times = hourly["time"]
        temperatures = hourly["temperature_2m"]

        now = datetime.now(
            ZoneInfo(TIMEZONE)
        ).replace(
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=None
        )

        weather_data = []

        for timestamp, temperature in zip(times, temperatures):

            forecast_time = datetime.fromisoformat(timestamp)

            if forecast_time >= now:

                if temperature is None:
                    continue

                weather_data.append({
                    "timestamp": timestamp,
                    "temperature": float(temperature)
                })

            if len(weather_data) == 24:
                break

        if len(weather_data) != 24:
            raise ValueError(
                "Could not retrieve 24 hourly temperatures."
            )

        cache.set(
            WEATHER_CACHE_KEY,
            weather_data,
            WEATHER_CACHE_SECONDS
        )

        return weather_data

    except Exception as error:
        raise RuntimeError(
            f"Weather API error: {error}"
        ) from error
