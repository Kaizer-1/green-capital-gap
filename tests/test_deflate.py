"""Tests for the constant-dollar conversion.

The failure this guards against is silent and total: an inverted deflator makes
every real-dollar figure in the report wrong in a way that still looks plausible,
because the series is monotone either way.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from gcg.transform.deflate import DeflatorError, apply_deflator, build_deflator


def _indicators(
    values: dict[int, float], *, code="NY.GDP.DEFL.ZS", country="USA"
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "country_code": country,
            "year": list(values),
            "indicator_code": code,
            "indicator": "gdp_deflator",
            "value": list(values.values()),
        }
    )


@pytest.fixture
def deflator_values() -> dict[int, float]:
    """The real US GDP deflator, so the test checks actual arithmetic.

    Every in-window year is present because ``build_deflator`` requires
    completeness: a gap must stop the build rather than null out amounts.
    """
    return {
        2000: 69.011230,
        2001: 70.565149,
        2002: 71.661727,
        2003: 73.076555,
        2004: 75.041648,
        2005: 77.394545,
        2006: 79.781266,
        2007: 81.942747,
        2008: 83.521546,
        2009: 84.036690,
        2010: 85.057977,
        2011: 86.812816,
        2012: 88.429414,
        2013: 89.934377,
        2014: 91.500690,
        2015: 92.349856,
    }


def test_base_year_multiplier_is_exactly_one(cfg, deflator_values):
    """A base-year dollar must convert to itself."""
    m = build_deflator(cfg, _indicators(deflator_values))
    assert m.loc[2015] == pytest.approx(1.0)


def test_earlier_dollars_are_worth_more_in_base_year_terms(cfg, deflator_values):
    """The direction check. An inverted deflator would deflate instead of inflate."""
    m = build_deflator(cfg, _indicators(deflator_values))
    assert m.loc[2000] > m.loc[2004] > m.loc[2008] > m.loc[2012] > m.loc[2015]
    assert m.loc[2000] > 1.0, "a 2000 dollar is worth MORE than one 2015 dollar"


def test_multiplier_matches_hand_computed_value(cfg, deflator_values):
    """92.349856 / 75.041648 = 1.230648..., computed independently of the code."""
    m = build_deflator(cfg, _indicators(deflator_values))
    assert m.loc[2004] == pytest.approx(92.349856 / 75.041648, rel=1e-12)
    assert m.loc[2004] == pytest.approx(1.230648, abs=1e-6)


def test_apply_preserves_the_nominal_column(cfg, deflator_values):
    """Both columns must survive, unambiguously named (CLAUDE.md §7)."""
    m = build_deflator(cfg, _indicators(deflator_values))
    df = pd.DataFrame({"year": [2004, 2012], "amount_usd_nominal": [1_000_000.0, 1_000_000.0]})
    out, stats = apply_deflator(df, m, cfg)

    assert out["amount_usd_nominal"].tolist() == [1_000_000.0, 1_000_000.0]
    assert out.loc[0, "amount_usd_real2015"] == pytest.approx(1_230_648.0, abs=1.0)
    assert out.loc[1, "amount_usd_real2015"] > 1_000_000.0
    assert stats["real_converted"] == 2


def test_undisclosed_amounts_stay_null_and_are_never_imputed(cfg, deflator_values):
    """A null nominal amount must give a null real amount, not a zero."""
    m = build_deflator(cfg, _indicators(deflator_values))
    df = pd.DataFrame({"year": [2004, 2008], "amount_usd_nominal": [np.nan, 500_000.0]})
    out, stats = apply_deflator(df, m, cfg)

    assert pd.isna(out.loc[0, "amount_usd_real2015"])
    assert stats["nominal_disclosed"] == 1
    assert stats["real_converted"] == 1


def test_missing_base_year_fails_loudly(cfg, deflator_values):
    """Silently picking a different base year would corrupt every real figure."""
    without_base = {y: v for y, v in deflator_values.items() if y != 2015}
    with pytest.raises(DeflatorError, match="base year"):
        build_deflator(cfg, _indicators(without_base))


def test_missing_in_window_year_fails_loudly(cfg):
    """An incomplete deflator must stop the build, not null out amounts."""
    with pytest.raises(DeflatorError, match="missing years"):
        build_deflator(cfg, _indicators({2015: 92.35}))


def test_wrong_country_series_is_rejected(cfg, deflator_values):
    """Deflating USD by a non-US deflator is a real and easy mistake."""
    with pytest.raises(DeflatorError, match="no NY.GDP.DEFL.ZS values"):
        build_deflator(cfg, _indicators(deflator_values, country="IND"))


def test_real_amounts_are_comparable_across_years(cfg, deflator_values):
    """The point of the exercise: equal real value must give equal real amounts."""
    m = build_deflator(cfg, _indicators(deflator_values))
    # $1m in 2004 and $1.230648m in 2015 are the same real quantity.
    df = pd.DataFrame({"year": [2004, 2015], "amount_usd_nominal": [1_000_000.0, 1_230_648.0]})
    out, _ = apply_deflator(df, m, cfg)
    a, b = out["amount_usd_real2015"]
    assert a == pytest.approx(b, rel=1e-5)
