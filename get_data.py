# day-ahead prices and solar and onshore wind production from entso-e, 2019 to now,
# and dk1's yearly average price since 2000 from energi data service
# needs an entso-e token in the environment variable ENTSOE_TOKEN

import os
import time
from pathlib import Path

import pandas as pd
import requests
from entsoe import EntsoePandasClient
from entsoe.exceptions import NoMatchingDataError

from areas import AREAS, TECH

START = pd.Timestamp("2019-01-01", tz="UTC")
END = pd.Timestamp.now(tz="UTC").floor("D")
RAW = Path("data/raw")
RAW.mkdir(parents=True, exist_ok=True)
client = EntsoePandasClient(api_key=os.environ["ENTSOE_TOKEN"])


def actual(df):
    if isinstance(df.columns, pd.MultiIndex):
        df = df.xs("Actual Aggregated", axis=1, level=-1)
    return df


def saved(name, fetch):
    # each download is saved, so a run that stops can start again where it was
    path = RAW / f"{name}.csv"
    if not path.exists():
        fetch().to_csv(path)
    return pd.read_csv(path, index_col=0, parse_dates=True)


prices, prod = {}, []
for area, a in AREAS.items():
    print(area)
    p = saved(f"prices_{area}", lambda: client.query_day_ahead_prices(a["price"], start=START, end=END).rename("price"))
    p.index = pd.to_datetime(p.index, utc=True)
    prices[area] = p["price"].resample("h").mean()

    def generation():
        out = []
        for m in pd.date_range(START, END, freq="MS"):
            try:
                g = client.query_generation(a["gen"], start=m, end=min(m + pd.offsets.MonthBegin(), END))
            except NoMatchingDataError:
                continue
            g = actual(g).reindex(columns=list(TECH.values()))
            g.index = g.index.tz_convert("UTC")
            out.append(g.resample("h").mean())
        return pd.concat(out)

    g = saved(f"generation_{area}", generation)
    g.index = pd.to_datetime(g.index, utc=True)
    g = g[~g.index.duplicated()].rename(columns={v: k for k, v in TECH.items()})
    prod.append(g.assign(area=area))


prices = pd.DataFrame(prices)
prices.index.name = "time"
prices.to_csv("data/prices.csv")
prod = pd.concat(prod)
prod.index.name = "time"
prod.to_csv("data/production.csv")

for _ in range(10):
    r = requests.get("https://api.energidataservice.dk/dataset/Elspotprices", timeout=300, params={
        "start": "2000-01-01", "end": "2019-01-01", "limit": 0, "columns": "HourUTC,SpotPriceEUR",
        "filter": '{"PriceArea":["DK1"]}'})
    if r.status_code != 429:
        break
    time.sleep(int(r.headers.get("Retry-After", 60)))
r.raise_for_status()
old = pd.DataFrame(r.json()["records"])
old.index = pd.DatetimeIndex(pd.to_datetime(old["HourUTC"], utc=True)).tz_convert("Europe/Copenhagen")
new = prices["DK1"].tz_convert("Europe/Copenhagen")
dk1 = pd.concat([old["SpotPriceEUR"].groupby(old.index.year).mean(), new.groupby(new.index.year).mean()])
dk1 = dk1.loc[2000:2025].rename("price")
dk1.index.name = "year"
dk1.to_csv("data/dk1_yearly.csv")

print(prices.describe().round(1))
print(prod.groupby("area")[list(TECH)].count())
