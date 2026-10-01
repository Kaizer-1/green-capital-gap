"""Tests for time-varying bloc assignment.

The headline claim being protected: a deal takes the bloc its country held in
the deal year. Poland in 2004 is not Poland in 2013, and a test that passes with
a static map would not catch the difference.
"""

from __future__ import annotations

import pandas as pd
import pytest

from gcg.classify.blocs import (
    UNASSIGNED,
    assign,
    build_bloc_panel,
    msci_bloc_map,
    normalise_country_code,
)


@pytest.fixture
def income_groups() -> pd.DataFrame:
    """A tiny income series with a real reclassification in it.

    Poland moves from upper-middle to high income between 2004 and 2013, which is
    the exact case time-varying assignment exists to handle.
    """
    rows = [
        ("POL", 2000, "upper_middle_income"),
        ("POL", 2004, "upper_middle_income"),
        ("POL", 2009, "high_income"),
        ("USA", 2000, "high_income"),
        ("CHN", 2000, "lower_middle_income"),
        ("CHN", 2010, "upper_middle_income"),
        ("IND", 2000, "low_income"),
        ("IND", 2008, "lower_middle_income"),
        ("ETH", 2000, "low_income"),
        ("ROU", 2000, "lower_middle_income"),
        ("ROU", 2006, "upper_middle_income"),
        ("MDV", 2000, "lower_middle_income"),
        ("MDV", 2005, "upper_middle_income"),
        ("BRA", 2000, "upper_middle_income"),
    ]
    return pd.DataFrame(rows, columns=["country_code", "year", "income_group"])


@pytest.fixture
def panel(cfg, income_groups):
    """The derived (country, year) -> bloc panel."""
    return build_bloc_panel(cfg, income_groups)


def _bloc(panel, code, year):
    row = panel.loc[panel["country_code"].eq(code) & panel["year"].eq(year), "bloc"]
    assert len(row) == 1, f"{code} {year}: expected one row, got {len(row)}"
    return row.iloc[0]


# ---------------------------------------------------------------------------
# The headline behaviour
# ---------------------------------------------------------------------------
def test_poland_changes_bloc_across_the_window(panel):
    """The case the whole design exists for."""
    assert _bloc(panel, "POL", 2004) == "EM"
    assert _bloc(panel, "POL", 2012) == "AE"


def test_classification_carries_forward_but_never_backward(panel):
    """A known classification holds until superseded; earlier years stay unknown.

    Back-filling would invent a classification for years the World Bank never
    published one for.
    """
    assert _bloc(panel, "POL", 2008) == "EM"   # last known before 2009 is upper-middle
    assert _bloc(panel, "POL", 2009) == "AE"
    assert _bloc(panel, "IND", 2007) == "EM"


def test_china_is_always_separate(panel):
    """China overrides its income group in every year."""
    assert _bloc(panel, "CHN", 2000) == "CHINA"
    assert _bloc(panel, "CHN", 2012) == "CHINA"


def test_ldc_overrides_income_group(panel):
    """Ethiopia is low-income and an LDC; LDC wins."""
    assert _bloc(panel, "ETH", 2005) == "LDC"


def test_ldc_graduation_is_time_varying(panel):
    """The Maldives graduated from the LDC list in 2011."""
    assert _bloc(panel, "MDV", 2010) == "LDC"
    assert _bloc(panel, "MDV", 2011) == "EM"


def test_high_income_is_advanced(panel):
    assert _bloc(panel, "USA", 2000) == "AE"
    assert _bloc(panel, "USA", 2012) == "AE"


def test_taiwan_override_is_applied(panel, cfg):
    """Taiwan has no World Bank classification and needs an explicit assignment.

    Dropping it would bias the AE/EM split, which is the project's biggest threat
    to validity.
    """
    assert "TWN" in cfg.blocs["income_overrides"]
    assert _bloc(panel, "TWN", 2005) == "AE"


# ---------------------------------------------------------------------------
# Country-code normalisation
# ---------------------------------------------------------------------------
def test_legacy_codes_are_remapped(cfg):
    """ROM and TMP are withdrawn ISO-3166-3 codes present in the snapshot."""
    s = pd.Series(["ROM", "TMP", "ZAR", "USA", "IND"])
    out, stats = normalise_country_code(s, cfg)
    assert out.tolist() == ["ROU", "TLS", "COD", "USA", "IND"]
    assert stats["overrides_applied"]["ROM"] == 1


def test_blanks_become_missing_not_a_country(cfg):
    """Blank country codes must not silently become a real country."""
    s = pd.Series(["", "  ", None, "UNKNOWN", "USA"])
    out, stats = normalise_country_code(s, cfg)
    assert out.isna().sum() == 4
    assert stats["blank_or_non_country"] == 4


def test_codes_are_uppercased(cfg):
    out, _ = normalise_country_code(pd.Series(["usa", "ind"]), cfg)
    assert out.tolist() == ["USA", "IND"]


# ---------------------------------------------------------------------------
# Assignment and the unmapped log
# ---------------------------------------------------------------------------
def test_unmapped_codes_are_flagged_not_dropped(panel, cfg):
    """CLAUDE.md §5: log every code that fails to map, never drop it silently."""
    deals = pd.DataFrame(
        {"country_code": ["POL", "ZZZ", "USA", None], "year": [2004, 2004, 2004, 2004]}
    )
    out, stats = assign(deals, panel, cfg)
    assert len(out) == len(deals), "no row may be dropped"
    assert out["bloc"].tolist() == ["EM", UNASSIGNED, "AE", UNASSIGNED]
    assert stats["unassigned"] == 2
    assert "ZZZ" in stats["codes_absent_from_panel"]


def test_assignment_is_year_sensitive(panel, cfg):
    """The same country in two years must get two different blocs."""
    deals = pd.DataFrame({"country_code": ["POL", "POL"], "year": [2004, 2012]})
    out, _ = assign(deals, panel, cfg)
    assert out["bloc"].tolist() == ["EM", "AE"]


def test_no_duplicate_country_years(panel):
    """A duplicated country-year would silently multiply deals on the join."""
    assert not panel.duplicated(subset=["country_code", "year"]).any()


# ---------------------------------------------------------------------------
# Robustness schemes
# ---------------------------------------------------------------------------
def test_msci_scheme_disagrees_with_the_world_bank(cfg):
    """Korea and Taiwan are MSCI-emerging but World Bank high-income.

    The disagreement is the reason the comparison is worth running.
    """
    msci = msci_bloc_map(cfg)
    assert msci["KOR"] == "EM"
    assert msci["TWN"] == "EM"
    assert msci["CHN"] == "EM"
    assert "USA" not in msci


def test_msci_list_is_the_documented_size(cfg):
    assert len(msci_bloc_map(cfg)) == len(cfg.blocs["robustness_msci_em"]["codes"])
