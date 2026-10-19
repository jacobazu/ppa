# what solar and onshore wind earned per mwh, per year and over the last three 12-month periods
# capture rate = output-weighted price / average price. the park stops when the price is negative

from pathlib import Path

import pandas as pd

from areas import AREAS, TECH


def capture(g, row):
    row.update(hours=len(g), baseload=g["price"].mean(), negative_hours=(g["price"] < 0).mean())
    for t in TECH:
        q = g[t].dropna()
        if q.sum() <= 0 or len(q) < 0.95 * len(g):  # missing production
            continue
        p = g.loc[q.index, "price"]
        on = p >= 0
        row[f"{t}_rate"] = (p * q).sum() / q.sum() / g["price"].mean()
        row[f"{t}_rate_stop"] = (p * q)[on].sum() / q[on].sum() / g["price"].mean()
        row[f"{t}_lost"] = q[~on].sum() / q.sum()
    return row


prices = pd.read_csv("data/prices.csv", index_col="time", parse_dates=True)
prod = pd.read_csv("data/production.csv", index_col="time", parse_dates=True)

years, windows = [], []
for area, a in AREAS.items():
    d = prod[prod["area"] == area].join(prices[area].rename("price"), how="inner").dropna(subset=["price"])
    d.index = d.index.tz_convert(a["tz"])
    for y, g in d.groupby(d.index.year):
        years.append(capture(g, {"area": area, "year": y}))
    end = d.dropna().index.max()
    for k in range(3):
        g = d[(d.index > end - pd.DateOffset(years=k + 1)) & (d.index <= end - pd.DateOffset(years=k))]
        windows.append(capture(g, {"area": area, "window": k + 1, "start": f"{g.index.min():%Y-%m-%d}",
                                   "end": f"{g.index.max():%Y-%m-%d}"}))

Path("results").mkdir(exist_ok=True)
pd.DataFrame(years).round(4).to_csv("results/capture_yearly.csv", index=False)
pd.DataFrame(windows).round(4).to_csv("results/capture_windows.csv", index=False)
print(pd.DataFrame(windows).set_index(["area", "window"]).round(3).to_string())
