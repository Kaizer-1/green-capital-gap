"""Convert nominal USD to constant 2015 USD using the US GDP deflator.

CLAUDE.md §7: comparing $2004 with $2012 unadjusted is a basic error. Crunchbase
amounts are USD-denominated, so the US deflator is the correct series rather than
a country-specific one — the quantity being deflated is a dollar, wherever the
company sits.

The World Bank series ``NY.GDP.DEFL.ZS`` is an index whose base year is not 2015
(the 2015 value is 92.35, not 100), so it is rescaled rather than used directly:

    amount_real2015 = amount_nominal * deflator[2015] / deflator[year]

Both columns are kept and unambiguously named, per CLAUDE.md §7.
"""

from __future__ import annotations

import pandas as pd

from gcg.config import Config, get_logger

LOG = get_logger("transform.deflate")


class DeflatorError(RuntimeError):
    """The deflator series cannot support the requested conversion."""


def build_deflator(cfg: Config, indicators: pd.DataFrame) -> pd.Series:
    """Return a year-indexed deflator rescaled so the base year equals 1.0.

    Parameters
    ----------
    cfg
        Project configuration; supplies the series code, country and base year.
    indicators
        Long World Bank indicator table.

    Returns
    -------
    pandas.Series
        Index ``year``, values the multiplier that converts a nominal amount in
        that year into base-year dollars.

    Raises
    ------
    DeflatorError
        If the base year is missing or any in-window year has no value.
    """
    spec = cfg.pipeline["deflate"]
    base_year = int(spec["base_year"])

    series = indicators.loc[
        indicators["indicator_code"].eq(spec["series_code"])
        & indicators["country_code"].eq(spec["deflator_country"])
        & indicators["value"].notna(),
        ["year", "value"],
    ]
    if series.empty:
        msg = (
            f"no {spec['series_code']} values for {spec['deflator_country']}. "
            "The constant-dollar conversion cannot proceed."
        )
        raise DeflatorError(msg)

    deflator = series.set_index("year")["value"].astype("float64").sort_index()
    if base_year not in deflator.index:
        msg = (
            f"deflator has no value for base year {base_year}; "
            f"have {deflator.index.min()}-{deflator.index.max()}"
        )
        raise DeflatorError(msg)

    base_value = float(deflator.loc[base_year])
    if base_value <= 0:
        msg = f"deflator for base year {base_year} is {base_value}, which is not usable"
        raise DeflatorError(msg)

    multiplier = base_value / deflator
    multiplier.name = "deflator_multiplier"

    y0 = int(cfg.window["start"][:4])
    y1 = int(cfg.window["uncensored_end"][:4])
    missing = [y for y in range(y0, y1 + 1) if y not in multiplier.index]
    if missing:
        msg = (
            f"deflator is missing years {missing}; amounts in those years cannot be converted"
        )
        raise DeflatorError(msg)

    LOG.info(
        "deflator built from %s/%s, base %d: %d-%d, multiplier %.4f (%d) to %.4f (%d)",
        spec["series_code"],
        spec["deflator_country"],
        base_year,
        int(multiplier.index.min()),
        int(multiplier.index.max()),
        float(multiplier.loc[y0]),
        y0,
        float(multiplier.loc[y1]),
        y1,
    )
    return multiplier


def apply_deflator(
    df: pd.DataFrame,
    multiplier: pd.Series,
    cfg: Config,
    *,
    year_col: str = "year",
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Add the constant-dollar column, leaving the nominal column untouched.

    A row with no disclosed nominal amount keeps a null real amount. Nulls are
    never imputed: CLAUDE.md §7 requires counts and dollars to be reported as
    independent series precisely because the dollar series is a subsample.
    """
    spec = cfg.pipeline["deflate"]
    nominal_col, real_col = spec["nominal_column"], spec["real_column"]

    out = df.copy()
    factors = out[year_col].map(multiplier)
    out[real_col] = out[nominal_col] * factors

    stats = {
        "rows": int(len(out)),
        "nominal_disclosed": int(out[nominal_col].notna().sum()),
        "real_converted": int(out[real_col].notna().sum()),
        "missing_deflator_year": int((out[nominal_col].notna() & factors.isna()).sum()),
    }
    if stats["missing_deflator_year"]:
        msg = (
            f"{stats['missing_deflator_year']} rows have a disclosed amount but no "
            "deflator for their year. Fix the window or the deflator, do not drop them."
        )
        raise DeflatorError(msg)

    LOG.info(
        "deflated %d of %d rows to constant %d USD (%d rows have no disclosed amount)",
        stats["real_converted"],
        stats["rows"],
        int(spec["base_year"]),
        stats["rows"] - stats["nominal_disclosed"],
    )
    return out, stats
