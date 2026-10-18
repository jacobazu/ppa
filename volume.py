# how much a park produces in each of 35 weather years, as a share of an average year
# wind: hourly wind speed through the power curve of a vestas v126-3.45 mw. solar: yearly radiation

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from areas import AREAS

# kw at 3.0, 3.5, ..., 12.0 m/s, full power up to 22.5 m/s (open energy database turbine library, via windpowerlib)
SPEED = np.arange(3.0, 12.5, 0.5)
POWER = np.array([35, 101, 184, 283, 404, 550, 725, 932, 1172, 1446, 1760, 2104, 2482, 2865, 3187, 3366, 3433,
                  3448, 3450]) / 3450


def power_curve(v):
    p = np.interp(v, SPEED, POWER, left=0, right=1)
    return np.where(v > 22.5, 0, p)


wind = pd.read_csv("data/weather_wind.csv.gz", parse_dates=["time"])
wind["power"] = power_curve(wind["wind"].to_numpy())
wind = wind.groupby(["area", wind["time"].dt.year])["power"].mean().unstack("area")

solar = pd.read_csv("data/weather_solar.csv", parse_dates=["date"])
solar = solar.groupby(["area", "site", solar["date"].dt.year])["radiation"].sum().groupby(["area", "date"]).mean()
solar = solar.unstack("area")

years = pd.concat({"onshore": wind / wind.mean(), "solar": solar / solar.mean()}, axis=1)
years.index.name = "year"
years.columns = [f"{a}_{t}" for t, a in years.columns]

summary = pd.DataFrame({c: {"std": years[c].std(), "p90": years[c].quantile(0.10), "p50": years[c].median(),
                            "worst": years[c].min(), "best": years[c].max()} for c in years}).T

# check: does the weather index move with what the real fleet produced per mw?
fleet = pd.read_csv("results/capture_yearly.csv").query("hours > 8700")
check = {}
for c in years:
    area, t = c.split("_")
    f = fleet[fleet["area"] == area].set_index("year").get(f"{t}_cf")
    if f is not None and f.notna().sum() >= 4:
        both = pd.concat([years[c], f], axis=1, join="inner").dropna()
        check[c] = both.corr().iloc[0, 1]
summary["corr_with_fleet"] = pd.Series(check)

Path("results").mkdir(exist_ok=True)
years.round(4).to_csv("results/volume_years.csv")
summary.round(4).to_csv("results/volume_summary.csv")

fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
for ax, t in zip(axes, ["solar", "onshore"]):
    for i, area in enumerate(AREAS):
        ax.plot(years.index, 100 * (years[f"{area}_{t}"] - 1), lw=1.2, color=f"C{i}", label=area)
    ax.axhline(0, color="#888888", lw=0.8)
    ax.set_title(t)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("% more or less than an average year")
axes[-1].legend(frameon=False, loc="upper left", bbox_to_anchor=(1, 1))
fig.suptitle(f"Production in each weather year, {years.index.min()}-{years.index.max()}")
fig.tight_layout()
Path("charts").mkdir(exist_ok=True)
fig.savefig("charts/volume.png", dpi=150)

print(summary.round(3))
