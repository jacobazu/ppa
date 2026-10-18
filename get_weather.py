# 35 years of weather at the sites in areas.py, from the open-meteo archive (era5)
# hourly wind speed at 100 m for wind, daily solar radiation for solar

import time
from pathlib import Path

import pandas as pd
import requests

from areas import AREAS

API = "https://archive-api.open-meteo.com/v1/archive"
FIRST, LAST = 1991, 2025
RAW = Path("data/raw/weather")
RAW.mkdir(parents=True, exist_ok=True)


def get(lat, lon, start, end, what):
    params = {"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
              "wind_speed_unit": "ms", "timezone": "GMT", **what}
    for _ in range(80):
        try:
            r = requests.get(API, params=params, timeout=300)
        except requests.ConnectionError:
            print("connection dropped, trying again in a minute")
            time.sleep(60)
            continue
        if r.status_code == 429:  # free use is limited per minute, hour and day
            print("open-meteo limit reached, waiting a minute")
            time.sleep(60)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("open-meteo: still not answering, run again later")


wind, solar = [], []
for area, a in AREAS.items():
    for kind, var, freq in [("wind", "wind_speed_100m", "hourly"), ("solar", "shortwave_radiation_sum", "daily")]:
        for i, (lat, lon) in enumerate(a[kind]):
            path = RAW / f"{kind}_{area}_{i}.csv"
            if not path.exists():
                parts = []
                for y in range(FIRST, LAST + 1, 5):
                    j = get(lat, lon, f"{y}-01-01", f"{min(y + 4, LAST)}-12-31", {freq: var})[freq]
                    parts.append(pd.DataFrame({"time": j["time"], "value": j[var]}))
                pd.concat(parts).to_csv(path, index=False)
                print(f"{area} {kind} site {i + 1} done")
            d = pd.read_csv(path).assign(area=area, site=i)
            (wind if kind == "wind" else solar).append(d)

Path("data").mkdir(exist_ok=True)
pd.concat(wind).rename(columns={"value": "wind"}).to_csv("data/weather_wind.csv.gz", index=False)
pd.concat(solar).rename(columns={"time": "date", "value": "radiation"}).to_csv("data/weather_solar.csv", index=False)
