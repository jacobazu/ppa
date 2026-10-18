# how much the yearly average price moves, and how long a high or low year lasts
# ar(1) on the log of dk1's yearly average price, 2000-2025: x(t) = c + phi * x(t-1) + e, e ~ N(0, sigma^2)

from pathlib import Path

import numpy as np
import pandas as pd

y = np.log(pd.read_csv("data/dk1_yearly.csv", index_col="year")["price"])
x, x1 = y.iloc[1:].to_numpy(), y.iloc[:-1].to_numpy()
X = np.column_stack([np.ones_like(x1), x1])
(c, phi), *_ = np.linalg.lstsq(X, x, rcond=None)
e = x - X @ np.array([c, phi])
sigma = np.sqrt(e @ e / (len(x) - 2))

out = pd.Series({"phi": phi, "sigma": sigma, "first_year": y.index.min(), "last_year": y.index.max(),
                 "years": len(y)}, name="value")
Path("results").mkdir(exist_ok=True)
out.to_csv("results/price_level.csv", index_label="name")
print(out.round(3))
