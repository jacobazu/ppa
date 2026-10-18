# what solar and onshore wind earned per mwh in each area and year, and how much the fleet produced per mw
# capture rate = output-weighted price / average price. "_stop" = the park stops when the price is negative

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from areas import AREAS, TECH

prices = pd.read_csv("data/prices.csv", index_col="time", parse_dates=True)
prod = pd.read_csv("data/production.csv", index_col="time", parse_dates=True)
cap = pd.read_csv("data/capacity.csv", index_col="year")

rows = []
for area, a in AREAS.items():
    d = prod[prod["area"] == area].join(prices[area].rename("price"), how="inner").dropna(subset=["price"])
    d.index = d.index.tz_convert(a["tz"])
    c = cap[cap["area"] == area]
    for y, g in d.groupby(d.index.year):
        row = {"area": area, "year": y, "hours": len(g), "baseload": g["price"].mean(),
               "negative_hours": (g["price"] < 0).mean()}
        for t in TECH:
            q = g[t].dropna()
            p = g.loc[q.index, "price"]
            if q.sum() <= 0:
                continue
            on = p >= 0
            row[f"{t}_rate"] = (p * q).sum() / q.sum() / g["price"].mean()
            row[f"{t}_rate_stop"] = (p * q)[on].sum() / q[on].sum() / g["price"].mean()
            row[f"{t}_lost"] = q[~on].sum() / q.sum()
            mw = c.loc[c.index.isin([y, y + 1]), f"{t}_mw"].mean()  # capacity at the start and end of the year
            row[f"{t}_cf"] = q.sum() / (mw * len(q)) if mw > 0 else None
        rows.append(row)
yearly = pd.DataFrame(rows)

Path("results").mkdir(exist_ok=True)
yearly.round(4).to_csv("results/capture_yearly.csv", index=False)

full = yearly[yearly["hours"] > 8700]
fig, axes = plt.subplots(1, len(TECH), figsize=(11, 4), sharey=True)
for ax, t in zip(axes, TECH):
    for i, area in enumerate(AREAS):
        b = full[full["area"] == area]
        if f"{t}_rate" in b and b[f"{t}_rate"].notna().any():
            ax.plot(b["year"], 100 * b[f"{t}_rate"], marker="o", color=f"C{i}", label=area)
    ax.axhline(100, color="#888888", lw=0.8)
    ax.set_title(t)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("% of the average price")
axes[-1].legend(frameon=False, loc="upper left", bbox_to_anchor=(1, 1))
fig.suptitle("Capture rate: what the fleet earned per MWh, full years")
fig.tight_layout()
Path("charts").mkdir(exist_ok=True)
fig.savefig("charts/capture.png", dpi=150)

print(full.set_index(["area", "year"]).round(3).to_string())
