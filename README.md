# PPA pricing in four areas

What is a fair fixed price for a 10-year PPA with a solar park or an onshore wind farm, and how much risk does each side carry? A case study of DK1, SE3, Finland and Germany, in Python.

Case study: [jacobazu.github.io/ppa](https://jacobazu.github.io/ppa/)

Methods: [one page (PDF)](notes/method.pdf)

- **Pay-as-produced:** the buyer takes whatever the park produces.
- **Baseload:** the park delivers the same amount every hour and buys any shortfall at the day-ahead price.

## Assumptions

Set before running. Prices are in euros of each year (nominal).

### From data and literature

| | Assumption | Source |
|---|---|---|
| Price level | exchange settlement prices of baseload year futures, 16 Oct 2026, in `inputs/forwards.csv`. DK1, SE3 and Finland: the Nordic system price plus the area's EPAD. DK1 is also run with Energistyrelsen's outlook | [Euronext](https://live.euronext.com/en/products/commodities/power-derivatives/contracts-list), [EEX](https://www.eex.com/en/market-data/market-data-hub); Energistyrelsen, SØB25, table 7 |
| Price changes | the yearly average price follows an AR(1) in logs, estimated on DK1's yearly prices 2000 to 2025 | [Energi Data Service](https://www.energidataservice.dk), ENTSO-E |
| Hourly patterns | prices and production in the last three 12-month periods | ENTSO-E |
| Weather | 35 weather years, 1991 to 2025. Wind through a Vestas V126-3.45 MW power curve | [Open-Meteo](https://open-meteo.com) (ERA5); [Open Energy Database](https://openenergyplatform.org) via windpowerlib |
| Fair price | the production-weighted expected price, split into the forward price, the profile of the park, and the covariance of price and volume | [Qorbanian et al.](https://arxiv.org/abs/2403.08846); [Chatziandreou and Karbach (2026)](https://ideas.repec.org/p/arx/papers/2607.27814.html) |
| Discount rate | 5.6% a year: 3.5% real plus 2% inflation | Finansministeriet, nøgletal, February 2026; ECB's inflation target |

### My choices

- **Contract:** 10 years, 2027 to 2036. The baseload volume is the park's average output.
- **Size:** a park that produces 100 GWh in an average weather year, the same in every area.
- **After the last futures:** where the EPADs stop, SE3 and Finland keep their last EPAD. DK1 follows the German curve with its 2029 spread, since DK1 and German prices move together (correlation 0.93-0.96 in 2024-2026). The forward prices are updated by hand.
- **Energistyrelsen's outlook** is in 2025 prices, so 2% inflation a year is added.
- **Price changes:** the DK1 estimate is used in all four areas.
- **Each year** draws one of the three 12-month patterns and one of the 35 weather years, separately.
- **Negative prices:** the park stops when the price is below zero, and the buyer doesn't pay for those hours.
- **No risk premium:** both sides get the same expected value.
- **Risk:** the 1 in 20 worst outcome over the 10 years, and the average below it.

## Checks against other sources

- Energistyrelsen expects a DK1 price of about 67 €/MWh on average over 2027 to 2036 (SØB25). The model is also run with that path.
- With Energistyrelsen's full-load hours for new parks in Denmark, 3,500 for onshore wind and about 1,450 for ground-mounted solar (KF25, tables 4.6 and 4.7), 100 GWh a year is about 29 MW of wind or 69 MW of solar.
- Pexapark reported 10-year pay-as-produced PPA prices in DK1 of 31 to 55 €/MWh for solar and 33 to 65 €/MWh for onshore wind ([April 2025](https://pexapark.com/blog/prmc-denmark-shows-widening-gap-between-bid-prices/)). Those include the buyer's risk premium, mine don't.

## Not included

- Grid tariffs, subsidies and the buyer going bankrupt.
- A link between windy years and low prices. Price level and weather are drawn separately, so the covariance part only comes from the hourly patterns.
- A risk premium, balancing costs and the value of guarantees of origin, which real prices include.
- Further cannibalisation. If more solar is built, solar will earn less than in 2023 to 2025.
- Price changes estimated on DK1 alone. Swedish and Finnish prices follow hydro and may move differently.
- Finnish solar production in ENTSO-E starts in 2023 and looks smoother than the other areas, so its high capture rate should be read with care.
- Recent years have been sunnier than the 35-year average, so part of the solar weather spread is a trend, not chance.

## License

Code: [MIT](LICENSE). Not trading advice.

Data from ENTSO-E, [Energi Data Service](https://www.energidataservice.dk) (Energinet) and [Open-Meteo.com](https://open-meteo.com) ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).
