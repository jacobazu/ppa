# fair fixed price and risk of a 10-year ppa, 2027-2036, for a solar park and an onshore wind farm in each area,
# each producing 100 gwh in an average weather year. prices are nominal
# pay-as-produced: the buyer takes all output. baseload: the park delivers its average output every hour
# the park stops when the day-ahead price is negative, and the buyer doesn't pay for those hours

from pathlib import Path

import numpy as np
import pandas as pd

from areas import AREAS, TECH

VOLUME = 100_000                # mwh in an average weather year
YEARS = np.arange(2027, 2037)
INFLATION = 0.02                # the ecb's target
RATE = 1.035 * (1 + INFLATION) - 1  # finansministeriet's 3.5% real (noegletal, feb 2026) plus inflation
ALPHA = 0.05
N = 20_000
SEED = 1
# energistyrelsen, soeb25 (final, 26 march 2026), table 7: kr/mwh in 2025 prices, 7.46 kr/eur
SOEB25 = np.array([580, 650, 570, 480, 460, 460, 440, 440, 440, 500]) / 7.46 * (1 + INFLATION) ** (YEARS - 2025)

forwards = pd.read_csv("inputs/forwards.csv")
windows = pd.read_csv("results/capture_windows.csv")
volume = pd.read_csv("results/volume_years.csv", index_col="year")
pl = pd.read_csv("results/price_level.csv", index_col="name")["value"]

# the same random draws everywhere, so areas and cases can be compared
rng = np.random.default_rng(SEED)
T = len(YEARS)
pick = rng.integers(3, size=(N, T))            # which 12-month period gives the hourly pattern
weather = rng.integers(10 ** 6, size=(N, T))   # which weather year
u = np.zeros((N, T))                            # log price level around the forward, ar(1)
for k in range(T):
    u[:, k] = (pl["phi"] * u[:, k - 1] if k else 0) + pl["sigma"] * rng.standard_normal(N)
shock = np.exp(u - pl["sigma"] ** 2 * np.cumsum(pl["phi"] ** (2 * np.arange(T))) / 2)  # mean 1 every year
disc = (1 + RATE) ** -np.arange(1, T + 1)


def pv(x):
    return (x * disc).sum(axis=1)


def risk(x, **row):
    p5 = np.quantile(x, ALPHA)
    return {**row, "mean": x.mean(), "p5": p5, "var": x.mean() - p5, "es": x.mean() - x[x <= p5].mean()}


def simulate(level, pat, area, t, stop=True, trend=False, latest=False):
    # one 10-year price, output and income path per row
    w = volume[f"{area}_{t}"].dropna().to_numpy()
    rate = pat[f"{t}_rate_stop" if stop else f"{t}_rate"].to_numpy()
    kept = 1 - pat[f"{t}_lost"].to_numpy() if stop else np.ones(3)
    k = np.zeros_like(pick) if latest else pick
    r = np.broadcast_to(rate[k], (N, T)).copy()
    if trend:  # more cannibalisation: the capture rate falls 1 percentage point every year, my assumption
        r = r - 0.01 * np.arange(1, T + 1)
    h = pat["hours"].to_numpy()[k]
    price = level * shock
    mwh = VOLUME * h / 8760 * w[weather % len(w)] * kept[k]
    return price, h, mwh, price * r * mwh, VOLUME / 8760 * kept.mean()


cases = {a: forwards[forwards["area"] == a].set_index("year")["price"].reindex(YEARS).ffill().to_numpy()
         for a in AREAS}
cases["DK1 (SOEB25)"] = SOEB25
variants = {"keeps producing at negative prices": dict(stop=False),
            "capture rate 1 point lower each year": dict(trend=True),
            "only the last 12 months' pattern": dict(latest=True)}

inputs, prices, risks, hedges, sens, sample = [], [], [], [], [], {}
for case, level in cases.items():
    area = case.split()[0]
    pat = windows[windows["area"] == area].sort_values("window")
    for t in TECH:
        if f"{t}_rate_stop" not in pat or pat[f"{t}_rate_stop"].isna().any():
            print(f"{case} {t}: no production data, skipped")
            continue
        price, h, mwh, merchant, flat = simulate(level, pat, area, t)
        pap = pv(merchant).mean() / pv(mwh).mean()
        base = pv(price * flat * h).mean() / pv(flat * h).mean()
        # split as in chatziandreou and karbach (2026): forward + profile + price-volume covariance
        q = mwh.mean(axis=0)
        forward_part = (disc * level * q).sum() / (disc * q).sum()
        profile_part = (disc * level * (merchant / price).mean(axis=0)).sum() / (disc * q).sum() - forward_part
        inputs.append({"case": case, "tech": t, "price_level": level.mean(),
                       "capture_rate": pat[f"{t}_rate_stop"].mean(), "output_lost_negative": pat[f"{t}_lost"].mean()})
        prices.append({"case": case, "tech": t, "baseload_price": base, "pap_price": pap, "pap_share": pap / base,
                       "forward_part": forward_part, "profile_part": profile_part,
                       "covariance_part": pap - forward_part - profile_part})

        m = 1e6
        park = {"merchant": pv(merchant), "pay-as-produced": pv(pap * mwh),
                "baseload": pv(base * flat * h + merchant - price * flat * h)}
        buyer = {"pay-as-produced": pv(merchant - pap * mwh), "baseload": pv((price - base) * flat * h)}
        risks += [risk(v / m, case=case, tech=t, contract=c, side="park") for c, v in park.items()]
        risks += [risk(v / m, case=case, tech=t, contract=c, side="buyer") for c, v in buyer.items()]
        if case == "DK1":
            sample.update({f"{t}_{c}": v[:4000] / m for c, v in park.items()})

        # sell some mw forward as baseload, at the forward price, to steady the 10-year income
        fwd = pv((level - price) * h)
        hedge_mw = -np.cov(park["merchant"], fwd)[0, 1] / fwd.var(ddof=1)
        hedged = park["merchant"] + hedge_mw * fwd
        hedges.append({"case": case, "tech": t, "average_output_mw": flat, "hedge_mw": hedge_mw,
                       "std_unhedged": park["merchant"].std() / m, "std_hedged": hedged.std() / m,
                       "reduction": 1 - hedged.std() / park["merchant"].std()})

        sens.append({"case": case, "tech": t, "variant": "main case", "pap_price": pap})
        for name, kw in variants.items():
            _, _, mwh_v, merchant_v, _ = simulate(level, pat, area, t, **kw)
            sens.append({"case": case, "tech": t, "variant": name, "pap_price": pv(merchant_v).mean() / pv(mwh_v).mean()})

Path("results").mkdir(exist_ok=True)
for name, rows in [("inputs", inputs), ("prices", prices), ("risk", risks), ("hedge", hedges), ("sensitivity", sens)]:
    pd.DataFrame(rows).round(4).to_csv(f"results/ppa_{name}.csv", index=False)
pd.DataFrame(sample).round(3).to_csv("results/ppa_dk1_sample.csv", index=False)
print(pd.DataFrame(prices).round(2).to_string(index=False))
print(pd.DataFrame(sens).pivot_table(index=["case", "tech"], columns="variant", values="pap_price").round(1))
