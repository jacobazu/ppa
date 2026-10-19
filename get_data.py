# day-ahead prices and solar and onshore wind production from entso-e, 2019 to now,
# and dk1's yearly average price since 2000 from energi data service

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


def saved(name, fetch, fresh=False):
    # each piece is saved, and only the newest pieces are downloaded again
    path = RAW / f"{name}.csv"
    if fresh or not path.exists():
        try:
            fetch().to_csv(path)
        except NoMatchingDataError:
            return None
    d = pd.read_csv(path, index_col=0)
    d.index = pd.to_datetime(d.index, utc=True)
    return d


def prices_year(code, y):
    s, e = max(START, pd.Timestamp(f"{y}-01-01", tz="UTC")), min(END, pd.Timestamp(f"{y + 1}-01-01", tz="UTC"))
    return client.query_day_ahead_prices(code, start=s, end=e).rename("price")


def generation_month(code, m):
    g = actual(client.query_generation(code, start=m, end=min(m + pd.offsets.MonthBegin(), END)))
    return g.reindex(columns=list(TECH.values()))


prices, prod = {}, []
months = pd.date_range(START, END, freq="MS")
for area, a in AREAS.items():
    print(area)
    p = [saved(f"prices_{area}_{y}", lambda: prices_year(a["price"], y), fresh=y == END.year)
         for y in range(START.year, END.year + 1)]
    p = pd.concat([x for x in p if x is not None])["price"]
    prices[area] = p[~p.index.duplicated(keep="last")].resample("h").mean()

    g = [saved(f"generation_{area}_{m:%Y-%m}", lambda: generation_month(a["gen"], m), fresh=m >= months[-2])
         for m in months]
    g = pd.concat([x for x in g if x is not None])
    g = g[~g.index.duplicated(keep="last")].resample("h").mean()
    prod.append(g.rename(columns={v: k for k, v in TECH.items()}).assign(area=area))

prices = pd.DataFrame(prices)
prices.index.name = "time"
prices.to_csv("data/prices.csv")
prod = pd.concat(prod)
prod.index.name = "time"
prod.to_csv("data/production.csv")

path = RAW / "dk1_2000_2018.csv"
if not path.exists():
    for _ in range(10):
        r = requests.get("https://api.energidataservice.dk/dataset/Elspotprices", timeout=300, params={
            "start": "2000-01-01", "end": "2019-01-01", "limit": 0, "columns": "HourUTC,SpotPriceEUR",
            "filter": '{"PriceArea":["DK1"]}'})
        if r.status_code != 429:
            break
        time.sleep(int(r.headers.get("Retry-After", 60)))
    r.raise_for_status()
    pd.DataFrame(r.json()["records"]).to_csv(path, index=False)
old = pd.read_csv(path)
old.index = pd.DatetimeIndex(pd.to_datetime(old["HourUTC"], utc=True)).tz_convert("Europe/Copenhagen")
new = prices["DK1"].tz_convert("Europe/Copenhagen")
dk1 = pd.concat([old["SpotPriceEUR"].groupby(old.index.year).mean(), new.groupby(new.index.year).mean()])
dk1 = dk1.loc[2000:END.year - 1].rename("price")
dk1.index.name = "year"
dk1.to_csv("data/dk1_yearly.csv")

print(prices.describe().round(1))
print(prod.groupby("area")[list(TECH)].count())
