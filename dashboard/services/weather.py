
import json
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from datetime import datetime
from zoneinfo import ZoneInfo

from django.core.cache import cache


LATITUDE = 22.5726
LONGITUDE = 88.3639
TIMEZONE = "Asia/Kolkata"

WEATHER_CACHE_KEY = "smart_building_weather_v1"
WEATHER_STALE_CACHE_KEY = "smart_building_weather_stale_v1"

# Fresh data: 10 minutes
WEATHER_CACHE_SECONDS = 600

# Backup data: 24 hours
WEATHER_STALE_CACHE_SECONDS = 86400


def get_hourly_weather():

    # 1. First check fresh weather data.
    cached_weather = cache.get(WEATHER_CACHE_KEY)

    if cached_weather is not None:
        return cached_weather

    # 2. Keep previously successful data as backup.
    stale_weather = cache.get(WEATHER_STALE_CACHE_KEY)

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

            if forecast_time >= now and temperature is not None:

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

        # 3. Save successful data in both caches.
        cache.set(
            WEATHER_CACHE_KEY,
            weather_data,
            WEATHER_CACHE_SECONDS
        )

        cache.set(
            WEATHER_STALE_CACHE_KEY,
            weather_data,
            WEATHER_STALE_CACHE_SECONDS
        )

        return weather_data

    except Exception as error:

        # 4. If the API fails, use previously saved data.
        if stale_weather is not None:
            print(
                f"Weather API temporarily unavailable: {error}. "
                "Using previously cached weather data."
            )
            return stale_weather

        # 5. No backup data is available.
        raise RuntimeError(
            f"Weather API error: {error}. "
            "No cached weather data is available."
        ) from error
