# PPA pricing in four areas

What is a fair fixed price for a 10-year PPA with a 50 MW solar park or a 50 MW onshore wind farm, and how much risk does each side carry? I compare DK1, SE3, Finland and Germany. Python.

- **Pay-as-produced:** the buyer takes whatever the park produces.
- **Baseload:** the park delivers the same amount every hour and buys any shortfall at the day-ahead price.

## Assumptions

Set before running. Everything is in 2025 euros.

| | Assumption | Source |
|---|---|---|
| Contract | 10 years, 2027 to 2036. The baseload volume is the park's average output | my choice |
| Price level | each area's average day-ahead price over the last 12 months, the same every year. DK1 is also run with Energistyrelsen's outlook | [ENTSO-E](https://transparency.entsoe.eu); Energistyrelsen, SØB25, table 7 |
| Price changes | the yearly average price follows an AR(1) in logs, estimated on DK1's yearly prices 2000 to 2025 and used in all four areas | [Energi Data Service](https://www.energidataservice.dk), ENTSO-E |
| Hourly patterns | prices and production from 2023, 2024 or 2025, one drawn for each year | ENTSO-E |
| Negative prices | the park stops when the price is below zero, and the buyer doesn't pay for those hours | my choice |
| Capacity factor | the area's fleet production divided by installed capacity, 2023 to 2025, scaled to an average weather year | ENTSO-E |
| Weather | one of 35 weather years (1991 to 2025) for each year. Wind through a Vestas V126-3.45 MW power curve | [Open-Meteo](https://open-meteo.com) (ERA5); [Open Energy Database](https://openenergyplatform.org) via windpowerlib |
| Fair price | the same expected value for both sides, with no risk premium | my choice |
| Discount rate | 3.5% a year | Finansministeriet, nøgletal, February 2026 |
| Risk | the 1 in 20 worst outcome over the 10 years, and the average below it | my choice |

## Checks against other sources

- Energistyrelsen expects a DK1 price of about 67 €/MWh on average over 2027 to 2036 (SØB25). The model is run with both that and the last 12 months.
- Energistyrelsen assumes 3,500 full-load hours for new onshore wind and about 1,450 for new ground-mounted solar (KF25, tables 4.6 and 4.7). The fleet averages used here are lower, since they include old parks.
- Pexapark reported 10-year pay-as-produced PPA prices in DK1 of 31 to 55 €/MWh for solar and 33 to 65 €/MWh for onshore wind ([April 2025](https://pexapark.com/blog/prmc-denmark-shows-widening-gap-between-bid-prices/)). Those include the buyer's risk premium, mine don't.

## Not included

- Balancing costs, which the buyer usually charges for.
- Grid tariffs, subsidies and the buyer going bankrupt.
- A link between windy years and low prices. Price level and weather are drawn separately.
- Further cannibalisation. If more solar is built, solar will earn less than in 2023 to 2025.
- Price changes estimated on DK1 alone. Swedish and Finnish prices follow hydro and may move differently.

## License

Code: [MIT](LICENSE). Not trading advice.

Data from ENTSO-E, [Energi Data Service](https://www.energidataservice.dk) (Energinet) and [Open-Meteo.com](https://open-meteo.com) ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)).
