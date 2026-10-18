# the four bidding zones, their entso-e codes, time zones and a few weather sites (lat, lon)

AREAS = {
    "DK1": {"price": "DK_1", "gen": "DK_1", "tz": "Europe/Copenhagen",
            "wind": [(56.10, 8.30), (57.05, 9.30)],
            "solar": [(55.20, 9.20), (56.20, 9.50), (55.30, 10.30)]},
    "SE3": {"price": "SE_3", "gen": "SE_3", "tz": "Europe/Stockholm",
            "wind": [(58.40, 13.00), (60.60, 16.50)],
            "solar": [(57.70, 12.00), (59.30, 17.00)]},
    "FI": {"price": "FI", "gen": "FI", "tz": "Europe/Helsinki",
           "wind": [(64.20, 23.90), (62.60, 21.60)],
           "solar": [(60.50, 24.50), (61.50, 23.80)]},
    "DE": {"price": "DE_LU", "gen": "DE", "tz": "Europe/Berlin",
           "wind": [(54.40, 9.40), (52.90, 7.90), (52.60, 13.60)],
           "solar": [(48.60, 11.60), (52.30, 13.60), (48.70, 9.20)]},
}
TECH = {"solar": "Solar", "onshore": "Wind Onshore"}
