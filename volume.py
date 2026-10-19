# how much a park produces in each of 35 weather years, as a share of an average year
# wind: hourly wind speed through the power curve of a vestas v126-3.45 mw. solar: yearly radiation

from pathlib import Path

import numpy as np
import pandas as pd

# kw at 3.0, 3.5, ..., 12.0 m/s, full power up to 22.5 m/s (open energy database turbine library, via windpowerlib)
SPEED = np.arange(3.0, 12.5, 0.5)
POWER = np.array([35, 101, 184, 283, 404, 550, 725, 932, 1172, 1446, 1760, 2104, 2482, 2865, 3187, 3366, 3433,
                  3448, 3450]) / 3450


def power_curve(v):
    return np.where(v > 22.5, 0, np.interp(v, SPEED, POWER, left=0, right=1))


wind = pd.read_csv("data/weather_wind.csv.gz", parse_dates=["time"])
wind["power"] = power_curve(wind["wind"].to_numpy())
wind = wind.groupby(["area", wind["time"].dt.year])["power"].mean().unstack("area")

solar = pd.read_csv("data/weather_solar.csv", parse_dates=["date"])
solar = solar.groupby(["area", "site", solar["date"].dt.year])["radiation"].sum().groupby(["area", "date"]).mean()
solar = solar.unstack("area")

years = pd.concat({"onshore": wind / wind.mean(), "solar": solar / solar.mean()}, axis=1)
years.columns = [f"{a}_{t}" for t, a in years.columns]
years.index.name = "year"
summary = pd.DataFrame({c: {"std": years[c].std(), "p90": years[c].quantile(0.10), "p50": years[c].median(),
                            "worst": years[c].min(), "best": years[c].max()} for c in years}).T

Path("results").mkdir(exist_ok=True)
years.round(4).to_csv("results/volume_years.csv")
summary.round(4).to_csv("results/volume_summary.csv", index_label="case")
print(summary.round(3))
