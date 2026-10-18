# fair fixed price and risk of a 10-year ppa for a solar park and an onshore wind farm in each area,
# each producing 100 gwh in an average weather year
# pay-as-produced: the buyer takes all the power. baseload: the park delivers a flat volume and buys any shortfall
# the park stops when the day-ahead price is negative, and the buyer doesn't pay for those hours

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from areas import AREAS, TECH

VOLUME = 100_000                 # mwh a year in an average weather year
YEARS = np.arange(2027, 2037)
RATE = 0.035                     # finansministeriet's discount rate, years 0-35 (noegletal, feb 2026)
PATTERN_YEARS = [2023, 2024, 2025]
ALPHA = 0.05
N = 20000
SEED = 1
# energistyrelsen, soeb25 (final, 26 march 2026), table 7, kr/mwh in 2025 prices, 2027-2036, at 7.46 kr/eur
SOEB25 = np.array([580, 650, 570, 480, 460, 460, 440, 440, 440, 500]) / 7.46

prices = pd.read_csv("data/prices.csv", index_col="time", parse_dates=True)
yearly = pd.read_csv("results/capture_yearly.csv")
volume = pd.read_csv("results/volume_years.csv", index_col="year")
pl = pd.read_csv("results/price_level.csv", index_col="name")["value"]
phi, sigma = pl["phi"], pl["sigma"]

# the same random draws in every area, so the areas can be compared
rng = np.random.default_rng(SEED)
T = len(YEARS)
pick = rng.integers(len(PATTERN_YEARS), size=(N, T))
u = np.zeros((N, T))
for k in range(T):
    u[:, k] = (phi * u[:, k - 1] if k else 0) + sigma * rng.standard_normal(N)
var_u = sigma ** 2 * np.cumsum(phi ** (2 * np.arange(T)))
shock = np.exp(u - var_u / 2)  # mean 1 in every year
weather_draw = rng.integers(10 ** 6, size=(N, T))
disc = (1 + RATE) ** -np.arange(1, T + 1)


def pv(x):
    return (x * disc).sum(axis=1)


def risk(x, case, t, contract, side):
    p5 = np.quantile(x, ALPHA)
    return {"case": case, "tech": t, "contract": contract, "side": side, "mean": x.mean(), "p5": p5,
            "var": x.mean() - p5, "es": x.mean() - x[x <= p5].mean()}


cases = {a: np.full(T, prices[a].dropna().iloc[-8760:].mean()) for a in AREAS}
cases["DK1 (SOEB25)"] = SOEB25

inputs, out_prices, out_risk, out_hedge = [], [], [], []
for case, level in cases.items():
    area = case.split()[0]
    pat = yearly[(yearly["area"] == area) & yearly["year"].isin(PATTERN_YEARS)].set_index("year").loc[PATTERN_YEARS]
    h = pat["hours"].to_numpy()[pick]
    price = level * shock
    for t in TECH:
        w = volume[f"{area}_{t}"].dropna().to_numpy()
        if f"{t}_rate_stop" not in pat or pat[f"{t}_rate_stop"].isna().any() or len(w) == 0:
            print(f"{case} {t}: missing data, skipped")
            continue
        rate, kept = pat[f"{t}_rate_stop"].to_numpy(), 1 - pat[f"{t}_lost"].to_numpy()
        mwh = VOLUME * h / 8760 * w[weather_draw % len(w)] * kept[pick]
        merchant = price * rate[pick] * mwh
        flat = VOLUME / 8760 * kept.mean()

        pap = pv(merchant).mean() / pv(mwh).mean()
        base = pv(price * flat * h).mean() / pv(flat * h).mean()
        inputs.append({"case": case, "tech": t, "price_level": level.mean(),
                       "capture_rate": rate.mean(), "output_lost_negative": 1 - kept.mean()})
        out_prices.append({"case": case, "tech": t, "baseload_price": base, "pap_price": pap,
                           "pap_share": pap / base, "profile_discount": base - pap})

        m = 1e6
        park = {"merchant": pv(merchant) / m, "pay-as-produced": pv(pap * mwh) / m,
                "baseload": pv(base * flat * h + merchant - price * flat * h) / m}
        buyer = {"pay-as-produced": pv(merchant - pap * mwh) / m, "baseload": pv((price - base) * flat * h) / m}
        out_risk += [risk(v, case, t, c, "park") for c, v in park.items()]
        out_risk += [risk(v, case, t, c, "buyer") for c, v in buyer.items()]

        # hedge: sell some mw forward as baseload, at the expected price, to steady the 10-year income
        income, fwd = pv(merchant), pv((level - price) * h)
        hedge_mw = -np.cov(income, fwd)[0, 1] / fwd.var(ddof=1)
        hedged = income + hedge_mw * fwd
        out_hedge.append({"case": case, "tech": t, "average_output_mw": flat, "hedge_mw": hedge_mw,
                          "std_unhedged": income.std() / m, "std_hedged": hedged.std() / m,
                          "reduction": 1 - hedged.std() / income.std()})

Path("results").mkdir(exist_ok=True)
for name, rows in [("inputs", inputs), ("prices", out_prices), ("risk", out_risk), ("hedge", out_hedge)]:
    pd.DataFrame(rows).round(4).to_csv(f"results/ppa_{name}.csv", index=False)

p = pd.DataFrame(out_prices).pivot(index="case", columns="tech", values="pap_price").reindex(list(cases))
b = pd.DataFrame(out_prices).groupby("case")["baseload_price"].first().reindex(list(cases))
fig, ax = plt.subplots(figsize=(9, 4.6))
x = np.arange(len(cases))
ax.bar(x - 0.27, b, width=0.27, color="#888888", label="baseload")
for i, (t, color) in enumerate([("solar", "#e8a317"), ("onshore", "#2b7bba")]):
    if t in p:
        ax.bar(x + 0.27 * i, p[t], width=0.27, color=color, label=f"{t}, pay-as-produced")
ax.set_xticks(x, list(cases))
ax.set_ylabel("EUR/MWh, 2025 prices")
ax.set_title("Fair fixed price of a 10-year PPA, 2027-2036")
ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
Path("charts").mkdir(exist_ok=True)
fig.savefig("charts/ppa_prices.png", dpi=150)

print(pd.DataFrame(inputs).round(3).to_string(index=False))
print(pd.DataFrame(out_prices).round(2).to_string(index=False))
print(pd.DataFrame(out_risk).round(2).to_string(index=False))
print(pd.DataFrame(out_hedge).round(3).to_string(index=False))
