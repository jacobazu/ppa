# the case study as one static page: docs/index.html, built from the files in results/ and inputs/

import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from areas import AREAS

INK, GREY, LINE, GRID = "#1f2328", "#6b7280", "#e5ddd3", "#f1ebe4"
SOLAR, WIND = "#f59e0b", "#0ea5e9"
AREA_COLOR = {"DK1": "#c2410c", "SE3": "#0ea5e9", "FI": "#16a34a", "DE": "#6b7280"}
NAME = {"DK1": "DK1", "SE3": "SE3", "FI": "Finland", "DE": "Germany", "DK1 (SOEB25)": "DK1, Energistyrelsen's outlook"}
TECH = {"solar": "Solar", "onshore": "Onshore wind"}
FONT = "IBM Plex Sans, Segoe UI, Helvetica Neue, Arial, sans-serif"
PLOTLY_JS = "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@4.1.1/plotly.min.js"

prices = pd.read_csv("results/ppa_prices.csv")
inputs = pd.read_csv("results/ppa_inputs.csv")
risk = pd.read_csv("results/ppa_risk.csv")
hedge = pd.read_csv("results/ppa_hedge.csv")
sens = pd.read_csv("results/ppa_sensitivity.csv")
sample = pd.read_csv("results/ppa_dk1_sample.csv")
yearly = pd.read_csv("results/capture_yearly.csv")
windows = pd.read_csv("results/capture_windows.csv")
volume = pd.read_csv("results/volume_summary.csv", index_col="case")
pl = pd.read_csv("results/price_level.csv", index_col="name")["value"]
fwd = pd.read_csv("inputs/forwards.csv")
data_to, fwd_date = windows["end"].max(), fwd["trade_date"].iloc[0]
cases = list(prices["case"].unique())


def chart(fig, height=340):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), font=dict(family=FONT, color=GREY, size=12),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", hovermode="x unified",
                      legend=dict(orientation="h", x=0, y=-0.18, font=dict(color=INK)))
    fig.update_xaxes(showgrid=False, linecolor=LINE)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=LINE)
    return fig.to_html(full_html=False, include_plotlyjs=False, config=dict(displayModeBar=False, responsive=True))


def table(head, rows, left=1):
    h = "".join(f"<th{' class=n' if i >= left else ''}>{x}</th>" for i, x in enumerate(head))
    b = "".join("<tr>" + "".join(f"<td{' class=n' if i >= left else ''}>{x}</td>" for i, x in enumerate(r)) + "</tr>"
                for r in rows)
    return f"<div class='scroll'><table><tr>{h}</tr>{b}</table></div>"


def fp(area, year):
    return fwd[(fwd["area"] == area) & (fwd["year"] == year)]["price"].iloc[0]


def p(case, tech, col="pap_price"):
    r = prices[(prices["case"] == case) & (prices["tech"] == tech)]
    return r[col].iloc[0] if len(r) else float("nan")


def v(case, tech, contract, side, col="var"):
    r = risk[(risk["case"] == case) & (risk["tech"] == tech) & (risk["contract"] == contract) & (risk["side"] == side)]
    return r[col].iloc[0]


def win(area, k, col):
    return windows[(windows["area"] == area) & (windows["window"] == k)][col].iloc[0]


def cap(area, year, col):
    r = yearly[(yearly["area"] == area) & (yearly["year"] == year)]
    return r[col].iloc[0] if len(r) else float("nan")


def h(case, tech, col):
    return hedge[(hedge["case"] == case) & (hedge["tech"] == tech)][col].iloc[0]


# charts
fig = go.Figure()
for t, color in [("solar", SOLAR), ("onshore", WIND)]:
    fig.add_trace(go.Bar(x=[NAME[c] for c in cases], y=[p(c, t) for c in cases], name=f"{TECH[t]}, pay-as-produced",
                         marker=dict(color=color, cornerradius=4)))
fig.add_trace(go.Scatter(x=[NAME[c] for c in cases], y=[p(c, "onshore", "baseload_price") for c in cases],
                         name="Baseload", mode="markers",
                         marker=dict(color=INK, symbol="line-ew-open", size=40, line=dict(width=3))))
fig.update_yaxes(ticksuffix=" €")
price_chart = chart(fig, 360)

fig = go.Figure()
for a in AREAS:
    f = fwd[fwd["area"] == a]
    fig.add_trace(go.Scatter(x=f["year"], y=f["price"], name=NAME[a], mode="lines+markers",
                             line=dict(color=AREA_COLOR[a], width=2.5)))
fig.update_yaxes(ticksuffix=" €")
forward_chart = chart(fig)

cap_charts = {}
for t in TECH:
    fig = go.Figure()
    for a in AREAS:
        c = yearly[(yearly["area"] == a) & (yearly["hours"] > 8700)].dropna(subset=[f"{t}_rate"])
        c = c.iloc[1:] if len(c) and c["year"].iloc[0] > yearly["year"].min() else c  # a fleet's first year is tiny
        fig.add_trace(go.Scatter(x=c["year"], y=100 * c[f"{t}_rate"], name=NAME[a], mode="lines+markers",
                                 line=dict(color=AREA_COLOR[a], width=2.5)))
    fig.add_hline(y=100, line=dict(color=LINE))
    fig.update_yaxes(ticksuffix="%")
    cap_charts[t] = chart(fig, 300)

fig = go.Figure()
for a in AREAS:
    c = yearly[(yearly["area"] == a) & (yearly["hours"] > 8700)]
    fig.add_trace(go.Bar(x=c["year"], y=100 * c["negative_hours"], name=NAME[a], marker=dict(color=AREA_COLOR[a])))
fig.update_yaxes(ticksuffix="%")
negative_chart = chart(fig, 300)

fig = go.Figure()
for c, color, name in [("merchant", "#9ca3af", "No PPA"), ("pay-as-produced", WIND, "Pay-as-produced"),
                       ("baseload", "#c2410c", "Baseload")]:
    fig.add_trace(go.Histogram(x=sample[f"onshore_{c}"], name=name, marker=dict(color=color), opacity=0.6,
                               nbinsx=80, histnorm="probability"))
fig.update_layout(barmode="overlay", hovermode=False)
fig.update_xaxes(title_text="What the wind farm earns over 10 years, million €, present value")
fig.update_yaxes(showticklabels=False)
risk_hist = chart(fig, 340)

# tables
price_table = table(["", "Price level", "Baseload", "Solar", "Onshore wind"], [
    [NAME[c], f"{inputs[inputs['case'] == c]['price_level'].iloc[0]:.1f}", f"{p(c, 'onshore', 'baseload_price'):.1f}",
     f"{p(c, 'solar'):.1f} ({p(c, 'solar', 'pap_share'):.0%})",
     f"{p(c, 'onshore'):.1f} ({p(c, 'onshore', 'pap_share'):.0%})"] for c in cases])
window_table = table(["", "Negative hours", "Solar", "Onshore wind", "Solar output at negative prices",
                      "Wind output at negative prices"], [
    [NAME[a], f"{win(a, 1, 'negative_hours'):.1%}", f"{win(a, 1, 'solar_rate_stop'):.0%}",
     f"{win(a, 1, 'onshore_rate_stop'):.0%}", f"{win(a, 1, 'solar_lost'):.0%}", f"{win(a, 1, 'onshore_lost'):.0%}"]
    for a in AREAS])
split_table = table(["", "Technology", "Forward", "Profile", "Covariance", "Fair price"], [
    [NAME[r.case], TECH[r.tech], f"{r.forward_part:.1f}", f"{r.profile_part:.1f}", f"{r.covariance_part:.1f}",
     f"{r.pap_price:.1f}"] for r in prices.itertuples() if r.case in AREAS], left=2)
variants = ["main case", "only the last 12 months' pattern", "keeps producing at negative prices",
            "capture rate 1 point lower each year"]
s = sens.pivot_table(index=["case", "tech"], columns="variant", values="pap_price")
sens_table = table(["", "Technology", "Main case", "Last 12 months only", "No stop at negative prices",
                    "1 point lower a year"], [
    [NAME[c], TECH[t]] + [f"{s.loc[(c, t), x]:.1f}" for x in variants]
    for c in cases for t in TECH if (c, t) in s.index], left=2)
risk_table = table(["", "Technology", "Park, no PPA", "Park, pay-as-produced", "Park, baseload",
                    "Buyer, pay-as-produced", "Buyer, baseload"], [
    [NAME[a], TECH[t], f"{v(a, t, 'merchant', 'park'):.1f}", f"{v(a, t, 'pay-as-produced', 'park'):.1f}",
     f"{v(a, t, 'baseload', 'park'):.1f}", f"{v(a, t, 'pay-as-produced', 'buyer'):.1f}",
     f"{v(a, t, 'baseload', 'buyer'):.1f}"]
    for a in AREAS for t in TECH if ((risk["case"] == a) & (risk["tech"] == t)).any()], left=2)
hedge_table = table(["", "Technology", "Average output", "Sell forward", "Spread of income cut by"], [
    [NAME[r.case], TECH[r.tech], f"{r.average_output_mw:.1f} MW", f"{r.hedge_mw:.1f} MW", f"{r.reduction:.0%}"]
    for r in hedge.itertuples() if r.case in AREAS], left=2)
volume_table = table(["", "Technology", "Year-to-year spread", "P90 year", "Worst of 35"], [
    [NAME[a], TECH[t], f"{volume.loc[f'{a}_{t}', 'std']:.1%}", f"{volume.loc[f'{a}_{t}', 'p90']:.0%}",
     f"{volume.loc[f'{a}_{t}', 'worst']:.0%}"] for t in ["onshore", "solar"] for a in AREAS], left=2)

dk = {t: p("DK1", t) for t in TECH}
soeb = {t: p("DK1 (SOEB25)", t) for t in TECH}
neg_share = {a: win(a, 1, "negative_hours") for a in AREAS}
html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PPA pricing in four areas</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<script src="{PLOTLY_JS}"></script>
<style>
  body {{ margin: 0; background: #faf6f1; color: {INK}; font: 16px/1.65 {FONT}; }}
  header {{ background: #fff; border-bottom: 1px solid #efe6dc; padding: 10px 20px; display: flex; flex-wrap: wrap;
           gap: 8px 20px; font-size: 14px; }}
  header a {{ color: {GREY}; }}
  main {{ max-width: 860px; margin: 0 auto; padding: 24px 16px 48px; }}
  h1 {{ font-size: 28px; line-height: 1.25; margin: 8px 0 4px; }}
  h2 {{ font-size: 20px; margin: 40px 0 6px; }}
  .by {{ color: {GREY}; font-size: 14px; margin-bottom: 20px; }}
  .card {{ background: #fff; border: 1px solid #efe6dc; border-radius: 14px; padding: 12px 14px; margin: 12px 0; }}
  .scroll {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
  th, td {{ text-align: left; padding: 6px 10px 6px 0; border-bottom: 1px solid {GRID}; white-space: nowrap; }}
  th {{ color: {GREY}; font-weight: 500; font-size: 13px; }}
  .n {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .note {{ color: {GREY}; font-size: 14px; margin: 6px 0 2px; }}
  a {{ color: #c2410c; }}
  ul {{ padding-left: 20px; }}
  li {{ margin-bottom: 4px; }}
</style>
</head>
<body>
<header><a href="https://jacobazu.github.io/">jacobazu.github.io</a><a href="https://github.com/jacobazu/ppa">Code</a>
<a href="method.pdf">Methods (PDF)</a></header>
<main>
<h1>What is a fair price for a 10-year solar or wind PPA?</h1>
<div class="by">DK1, SE3, Finland and Germany. Jacob Qazizada, {date.today():%B %Y}. Prices and production up to
{data_to}, forward prices from {fwd_date}.</div>

<p>Most new wind and solar in the Nordics is built on a power purchase agreement, a PPA. The park sells its power to a
buyer at a fixed price for ten years or more, so it has a known income to borrow against. The buyer, often a large
company or a utility, gets power at a known price.</p>
<p>I wanted to know what a fair fixed price is, and what each side is really taking on. The setup:</p>
<ul>
<li>A solar park and an onshore wind farm, each producing 100 GWh in an average year. That is roughly 29 MW of wind or
69 MW of solar in Denmark.</li>
<li>A 10-year contract, 2027 to 2036, priced in four bidding zones: DK1 (western Denmark), SE3 (Stockholm), Finland and
Germany.</li>
<li>Two contract types. Pay-as-produced: the buyer takes whatever the park produces. Baseload: the park delivers the
same amount every hour and buys at the day-ahead price whenever it produces less.</li>
<li>Fair means both sides expect to come out even. Real contracts add a risk premium, balancing costs and the value of
guarantees of origin. I leave those out, so real prices should be somewhat lower than mine.</li>
</ul>

<h2>The answer</h2>
<div class="card">{price_table}<p class="note">€/MWh, nominal, averaged over 2027-2036. In brackets: the share of the
baseload price. Price level: the forward price for each year, averaged.</p></div>
<div class="card">{price_chart}</div>
<p>In DK1 a fair pay-as-produced price is {dk['onshore']:.0f} €/MWh for wind and {dk['solar']:.0f} €/MWh for solar.
A baseload contract would be {p('DK1', 'onshore', 'baseload_price'):.0f}. The gap is what the park's timing costs:
it produces when everyone like it produces, and those hours are cheap. Solar loses more than wind everywhere except
Finland, where years of fast wind building have made wind the cheap kind of power.</p>
<p>The level depends heavily on which price path you believe. With Energistyrelsen's official outlook instead of the
forward prices, the DK1 prices drop to {soeb['onshore']:.0f} for wind and {soeb['solar']:.0f} for solar.</p>

<h2>The price level: forward prices</h2>
<div class="card">{forward_chart}<p class="note">Settlement prices of baseload year futures on {fwd_date}. DK1, SE3 and
Finland: Euronext's Nordic system price plus the area's EPAD (the price difference to the system price). Germany: EEX.
</p></div>
<p>A PPA should be priced off what the market will pay for power in those years today, not off last year's prices.
Forward prices are the closest thing to that. DK1 trades at {fp('DK1', 2027):.0f} €/MWh for 2027 and falls to
{fp('DK1', 2036):.0f} by 2036. Germany follows almost the same path. SE3 and Finland sit around 50-65 €/MWh, held down
by hydro and nuclear.</p>
<p>Two practical problems. The futures beyond about 2030 hardly trade, so those prices are thin. And the EPADs, which
turn the Nordic system price into an area price, only go to 2029 for DK1 and 2030 for SE3 and Finland. After that I keep
the last EPAD for SE3 and Finland. For DK1 I follow the German curve instead, with the 2029 gap between the two, because
DK1 and German prices moved with a correlation of 0.93-0.96 in 2024-2026. Keeping DK1's last EPAD would have put DK1
above Germany for the whole 2030s, which I don't believe.</p>
<p>Energistyrelsen's own outlook for DK1 (SØB25) averages {inputs[inputs['case'] == 'DK1 (SOEB25)']['price_level'].iloc[0]:.0f}
€/MWh in nominal terms, well below the forwards, so I run DK1 with both.</p>

<h2>Why a park gets less than the average price</h2>
<div class="card"><b>Solar</b>{cap_charts['solar']}</div>
<div class="card"><b>Onshore wind</b>{cap_charts['onshore']}</div>
<p>The capture rate is the price a park actually got, weighted by when it produced, as a share of the average price. It
falls as more of the same technology is built, because all of it produces in the same hours. DK1 solar went from
{cap('DK1', 2019, 'solar_rate'):.0%} in 2019 to {cap('DK1', 2025, 'solar_rate'):.0%} in 2025, and German solar to
{cap('DE', 2025, 'solar_rate'):.0%}. Finnish wind fell to {cap('FI', 2025, 'onshore_rate'):.0%} as Finland's wind fleet
grew several times over. 2022 stands out for solar: gas set the price most of the time, so sunny hours were not much cheaper than the rest.</p>
<div class="card"><b>Share of hours with negative prices</b>{negative_chart}</div>
<p>Negative prices are part of the same story. In the last 12 months prices were below zero in
{neg_share['DE']:.1%} of hours in Germany and {neg_share['DK1']:.1%} in DK1. A park without subsidies loses money
producing then, so in the model it stops, and the buyer doesn't pay for those hours.</p>
<div class="card">{window_table}<p class="note">The last 12 months, {win('DK1', 1, 'start')} to {data_to}. Capture rates
when the park stops at negative prices.</p></div>
<p>The model draws each year's hourly pattern from one of the last three 12-month periods. That keeps the real link
between when a park produces and what power is worth in those hours, including the bad hours.</p>

<h2>From forward price to fair price</h2>
<div class="card">{split_table}<p class="note">€/MWh. Split as in Chatziandreou and Karbach (2026): the forward price,
then what the production profile costs, then the covariance of price and volume across years.</p></div>
<p>The profile is the whole story here. The covariance part is close to zero because I draw the yearly price level and
the weather separately, so a windy year doesn't come with lower prices in the model. Inside each year that link is
there, through the hourly patterns. Across years it isn't, and that is one of the weaker points of the model.</p>

<h2>What moves the price</h2>
<div class="card">{sens_table}<p class="note">Fair pay-as-produced price, €/MWh, when one thing is changed.</p></div>
<ul>
<li><b>Only the last 12 months' pattern.</b> Uses the newest year instead of three. It moves DK1 wind up to
{s.loc[('DK1', 'onshore'), variants[1]]:.0f}, because the last year was a better one for wind.</li>
<li><b>No stop at negative prices.</b> If the park keeps producing and the buyer pays for those hours too, the fair price
falls, most of all for German solar ({s.loc[('DE', 'solar'), variants[2]]:.0f} instead of
{s.loc[('DE', 'solar'), variants[0]]:.0f}). Stopping is worth a lot where negative hours are common.</li>
<li><b>More cannibalisation.</b> If capture rates fall one percentage point a year from here, DK1 solar ends at
{s.loc[('DK1', 'solar'), variants[3]]:.0f} and DK1 wind at {s.loc[('DK1', 'onshore'), variants[3]]:.0f}. That rate is my
assumption, not an estimate.</li>
</ul>

<h2>Who carries the risk</h2>
<div class="card">{risk_hist}<p class="note">DK1 wind farm, 20,000 simulated 10-year paths.</p></div>
<p>Without a PPA the park's income spreads widely. Prices can stay high or low for years: the yearly DK1 price moves by
about {pl['sigma']:.0%} a year and a high or low year tends to be followed by another (AR(1) on 26 years of prices,
phi {pl['phi']:.2f}). A pay-as-produced PPA moves almost all of that to the buyer. The park is left with the weather.
A baseload PPA sits in between: the park has promised a fixed amount every hour, so when it produces less it has to buy
the rest, and that tends to happen when prices are high.</p>
<div class="card">{risk_table}<p class="note">How far the 1 in 20 worst outcome over the 10 years is below the average,
million €, present value at 5.6%.</p></div>
<p>For DK1 wind the 1 in 20 bad case is {v('DK1', 'onshore', 'merchant', 'park'):.0f} million € below average without a
PPA and {v('DK1', 'onshore', 'pay-as-produced', 'park'):.0f} million € with one. The buyer of the pay-as-produced PPA
takes on {v('DK1', 'onshore', 'pay-as-produced', 'buyer'):.0f} million €. The buyer of a baseload PPA takes on even
more, because it gets power at a fixed price in every hour, including the cheap ones.</p>

<h2>Hedging a park without a PPA</h2>
<div class="card">{hedge_table}<p class="note">Baseload sold forward at today's forward prices: the amount that makes the
10-year income steadiest.</p></div>
<p>A park that stays merchant can still sell part of its output forward as baseload. Selling a bit less than the average
output, for DK1 wind {h('DK1', 'onshore', 'hedge_mw'):.1f} MW of {h('DK1', 'onshore', 'average_output_mw'):.1f} MW, cuts
the spread of its 10-year income by {h('DK1', 'onshore', 'reduction'):.0%}. What's left is weather and timing, which a
baseload hedge can't touch. In practice the forwards beyond a few years are thin, so this is easier on paper.</p>

<h2>How much the weather matters</h2>
<div class="card">{volume_table}<p class="note">Production in each of 35 weather years, 1991-2025, as a share of an
average year. P90: a year so poor that 9 in 10 years are better.</p></div>
<p>Wind output moves by 7-10% from one year to the next, solar by about 4%. Wind is computed from hourly ERA5 wind at
100 m through a Vestas V126 power curve at a few sites per area, solar from yearly radiation. The last years have been
sunnier than the 35-year average, so part of the solar spread is a trend rather than chance.</p>

<h2>Compared with the market</h2>
<p>Pexapark reported 10-year pay-as-produced prices in DK1 of 31-55 €/MWh for solar and 33-65 €/MWh for wind in April
2025. My prices are higher, for three reasons. Forward prices have gone up a lot since then. Real buyers take a risk
premium and charge for balancing, which I don't. And my profiles are for the whole fleet; a new park with bigger
turbines produces more evenly and would do a little better. With Energistyrelsen's outlook, which is closer to the
price level of early 2025, DK1 wind lands at {soeb['onshore']:.0f}, near the top of its range, and solar at
{soeb['solar']:.0f}, just above it.</p>

<h2>What I would add</h2>
<ul>
<li>Balancing costs, from the area's imbalance prices and forecast errors.</li>
<li>A link between windy years and low prices across years, not only within them.</li>
<li>A risk premium, for example a price that compensates the buyer for its 1 in 20 loss at a cost of capital.</li>
<li>Production profiles for a single new park instead of the fleet, and a separate price model for SE3 and Finland,
where hydro drives prices.</li>
</ul>

<h2>Method and sources</h2>
<p>20,000 simulated 10-year paths with the same random draws in every area. Each year draws an hourly pattern, a
weather year and a price level around the forward curve. Fair prices are present values at 5.6% nominal (Finansministeriet's
3.5% real plus 2% inflation). The full list of assumptions and their sources is in the
<a href="https://github.com/jacobazu/ppa#assumptions">README</a>, the method on <a href="method.pdf">one page</a>.</p>
<p class="note">Data: ENTSO-E (prices and production), Energi Data Service (DK1 prices 2000-2018), Open-Meteo / ERA5
(weather, CC BY 4.0), Euronext and EEX (forward prices), Energistyrelsen (SØB25, KF25), Finansministeriet (discount rate).
Not trading advice.</p>
</main>
</body>
</html>
"""

Path("docs").mkdir(exist_ok=True)
Path("docs/index.html").write_text(html, encoding="utf-8")
shutil.copy("notes/method.pdf", "docs/method.pdf")
print("docs/index.html")
