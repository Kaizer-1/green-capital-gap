"""Reshape the analysis frames into plot-ready arrays for the web edition.

This module computes nothing. Every value it writes is either read from a table
the analysis stage already produced, or returned by the same analysis function
the corresponding matplotlib figure calls. The web page and ``report.pdf``
therefore cannot disagree about a number: there is one pipeline and this is a
projection of it.

Two rules from ``WEB.md`` §3 shape the output and are worth stating here because
they are easy to erode:

``colour_role``
    A semantic name — ``em``, ``ae``, ``china``, ``ldc``, ``green``,
    ``nongreen``, ``cleantech``, ``muted``, ``alert`` — never a hex value. The
    palette lives in one place (``web/js/charts/theme.js``, which mirrors
    ``src/gcg/viz/theme.py``). Writing hexes here would create a second one.

``text_key``
    Any annotation whose text is a statistic carries a key into
    ``findings.json`` rather than a rendered string, so the browser resolves it
    through the same path the report's placeholders take.

Rounding goes through ``gcg.rounding`` so the web and the PDF round identically.
That is not pedantry: rounding twice by different rules is what produced 5.42
against 5.43 earlier in this project.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from gcg.analysis import h1b_capital_intensity as h1b
from gcg.analysis import h2_cycle, h3_instrument, h5_allocation
from gcg.analysis.h1_selection import (
    green_rate_by_bloc,
    green_rate_by_year,
    two_proportion_test,
)
from gcg.config import Config, get_logger, load_config, seed_everything
from gcg.io import read_parquet
from gcg.report.render import apply_typography
from gcg.rounding import fmt_ci as _rfmt_ci
from gcg.rounding import fmt_multiple as _rfmt_multiple
from gcg.rounding import half_up


def _fmt_multiple(value: float) -> str:
    """A ratio as the report writes it, e.g. 1.92x before typesetting."""
    return _rfmt_multiple(value, 2)


def _fmt_ci_multiple(pair: list[float]) -> str:
    """An interval of ratios as the report writes it."""
    return _rfmt_ci(pair, 2, suffix="x")


LOG = get_logger("web.export")

# Bumped when the shape of this file changes in a way the loader must notice.
# web/js/data.js refuses to render on a mismatch rather than guessing.
SCHEMA_VERSION = 1

# Bloc code to the palette role and the display name used in labels and
# tooltips. One mapping, so a bloc cannot be teal in one figure and grey in
# another.
BLOC_ROLE = {
    "AE": ("ae", "Advanced economies"),
    "EM": ("em", "Emerging markets"),
    "CHINA": ("china", "China"),
    "LDC": ("ldc", "Least developed"),
    "UNASSIGNED": ("muted", "No country recorded"),
}


def _r(value: Any, places: int = 2) -> float | None:
    """Round through the project's single rounding rule, or pass None through."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return half_up(number, places)


def _ints(values: Any) -> int | None:
    return None if values is None or pd.isna(values) else int(values)


def _commit(cfg: Config) -> str:
    """The commit the export was generated from, for the page's colophon."""
    try:
        out = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
            cwd=cfg.root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except OSError:
        return "unknown"
    return out.stdout.strip() or "unknown"


# ---------------------------------------------------------------------------
# One builder per figure. Each returns the object that becomes one top-level key.


def fig01_coverage(cfg: Config) -> dict[str, Any]:
    """Emerging-market share of world GDP against its share of recorded deals."""
    tab = pd.read_csv(cfg.path("tables") / "diag_coverage_bias_by_bloc_year.csv")
    em = tab.loc[tab["bloc"].eq("EM")].sort_values("year")
    marks = [
        {
            "year": int(r["year"]),
            "gdp_share": _r(r["gdp_share_pct"], 2),
            "deal_share": _r(r["deal_share_pct"], 2),
            "gap_pp": _r(r["gap_pp"], 2),
            "representation_ratio": _r(r["representation_ratio"], 3),
            "green_deals": _ints(r["green_deals"]),
        }
        for _, r in em.iterrows()
    ]
    widest = max(marks, key=lambda m: m["gap_pp"] or 0)
    return {
        "marks": marks,
        "series": [
            {"id": "gdp_share", "label": "Share of world GDP", "colour_role": "muted"},
            {
                "id": "deal_share",
                "label": "Share of recorded venture deals",
                "colour_role": "em",
            },
        ],
        "annotations": [
            {
                "id": "widest",
                "year": widest["year"],
                "text_key": "measure.under_rep_range",
                "prefix": "Under-representation of ",
            }
        ],
        "axis": {
            "x": {"domain": [min(m["year"] for m in marks), max(m["year"] for m in marks)]},
            "y": {"domain": [0, 25], "unit": "%", "label": "Share of the world total"},
        },
    }


def fig02_double_gap(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Green share of recorded deals by bloc, with Wilson intervals."""
    rows = green_rate_by_bloc(deals, cfg).set_index("bloc")
    em = deals.loc[deals["bloc"].eq("EM")]
    ae = deals.loc[deals["bloc"].eq("AE")]
    test = two_proportion_test(
        int(em["green"].sum()), len(em), int(ae["green"].sum()), len(ae)
    )

    upper = deals.copy()
    upper["b"] = upper["bloc"].replace({"UNASSIGNED": "EM"})
    ub_rate = 100 * float(upper.loc[upper["b"].eq("EM"), "green"].mean())

    order = ["AE", "CHINA", "UNASSIGNED", "EM", "LDC"]
    marks = []
    for bloc in order:
        if bloc not in rows.index:
            continue
        r = rows.loc[bloc]
        role, label = BLOC_ROLE[bloc]
        # Whether the interval is drawn at all is decided HERE, not in the
        # browser, and on the same rule the print figure applies: a bloc with no
        # green deals has a Wilson interval running to 22.8% on thirteen deals,
        # and drawing it implies a precision that does not exist. The web and
        # print variants of this figure must not diverge on it.
        green = _ints(r["green_deals"])
        marks.append(
            {
                "bloc": bloc,
                "label": label,
                "rate": _r(r["green_rate_pct"], 2),
                "ci": [_r(r["ci_lo_pct"], 2), _r(r["ci_hi_pct"], 2)],
                "n": _ints(r["deals"]),
                "green": green,
                "below_min_cell": bool(r["below_min_cell"]),
                "draw_interval": green > 0,
                "note": (
                    None
                    if green > 0
                    else f"0 of {_ints(r['deals']):,} deals: no usable interval"
                ),
                "colour_role": role,
            }
        )
    return {
        "marks": marks,
        "upper_bound": {
            "bloc": "EM",
            "rate": _r(ub_rate, 2),
            "label": "Every unattributable deal counted as emerging-market",
        },
        "bracket": {"from": "AE", "to": "EM", "label": "EM vs AE"},
        "annotations": [
            {"id": "risk_ratio", "text_key": "h1.rr", "prefix": "Risk ratio "},
            {"id": "china", "text_key": "china.rr", "prefix": "China risk ratio "},
        ],
        "test": {
            "risk_ratio": _r(test["risk_ratio"], 3),
            "risk_ratio_ci": [_r(v, 3) for v in test["risk_ratio_ci"]],
        },
        "axis": {
            "x": {
                "domain": [0, 9],
                "unit": "%",
                "label": "Green share of the bloc's recorded deals",
            }
        },
    }


def fig03_rate_by_year(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Green rate by bloc and year. Descriptive only; no cell clears the minimum."""
    by_year = green_rate_by_year(deals)
    min_cell = int(cfg.threshold("min_cell_n"))
    series = []
    for bloc in ("AE", "EM"):
        sub = by_year.loc[by_year["bloc"].eq(bloc)].sort_values("year")
        role, label = BLOC_ROLE[bloc]
        series.append(
            {
                "id": bloc,
                "label": label,
                "colour_role": role,
                "dash": None if bloc == "AE" else "4 3",
                "points": [
                    {
                        "year": int(r["year"]),
                        "rate": _r(r["green_rate_pct"], 2),
                        "deals": _ints(r["deals"]),
                        "green": _ints(r["green_deals"]),
                        "below_min_cell": bool(int(r["green_deals"]) < min_cell),
                    }
                    for _, r in sub.iterrows()
                ],
            }
        )
    em_points = next(s for s in series if s["id"] == "EM")["points"]
    largest = max(em_points, key=lambda p: p["green"] or 0)
    return {
        "series": series,
        "min_cell": min_cell,
        "annotations": [
            {
                "id": "parity_2008",
                "year": 2008,
                "text": "The rates converge at the peak of Cleantech 1.0",
            },
            {
                "id": "largest_cell",
                "year": largest["year"],
                "text": f"largest emerging-market cell: {largest['green']} green deals",
            },
        ],
        "axis": {
            "x": {"domain": [2000, 2012]},
            "y": {"unit": "%", "label": "Green share of recorded deals"},
        },
    }


def fig04_ladder(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Sector representation against capital intensity: ladder and scatter.

    One object serves both views and all four scrollytelling steps. The browser
    switches which fields it reads; it does not recompute positions.
    """
    panel = h1b.run(deals, cfg)
    # The sector table is indexed by category_code; the figure reads it the same
    # way. Resetting gives a plain column without touching the analysis frame.
    sectors = panel["_tables"]["h1b_sector_capital_intensity"].reset_index()
    fit = panel["primary_fit"]
    residual = panel["cleantech_residual_primary"]

    marks = []
    for _, r in sectors.sort_values("representation_ratio").iterrows():
        sector = str(r["category_code"])
        observed = float(r["representation_ratio"])
        predicted = float(np.exp(r["fitted_log_ratio"]))
        marks.append(
            {
                "sector": sector,
                "observed": _r(observed, 3),
                "predicted": _r(predicted, 3),
                "residual_log": _r(r["residual_log"], 3),
                "capital_intensity_usd": _r(r["median_deal_usd_real"], 0),
                "em_deals": _ints(r["em_deals"]),
                "ae_deals": _ints(r["ae_deals"]),
                "studentised": _r(r["studentised"], 2),
                "colour_role": "cleantech" if sector == "cleantech" else "muted",
                "is_focus": sector == "cleantech",
                # Sign drives the residual segment's colour in step 3.
                "residual_sign": "over" if float(r["residual_log"]) > 0 else "under",
            }
        )

    xs = [m["capital_intensity_usd"] for m in marks if m["capital_intensity_usd"]]
    return {
        "marks": marks,
        "fit": {
            # Rounded to the precision the report displays, not to full precision.
            # The page may print these, and a page showing -1.195 beside a PDF
            # showing -1.19 is the disagreement WEB.md §1.4 forbids. The line
            # endpoints below are computed from the unrounded fit, so the geometry
            # is unaffected.
            "slope": _r(fit["slope"], 2),
            "intercept": _r(fit["intercept"], 2),
            "r_squared": _r(fit["r_squared"], 2),
            "n_sectors": int(fit["n_sectors"]),
            # Two endpoints in data space; the browser draws a line through them
            # rather than evaluating the model itself.
            "line": [
                {
                    "x": _r(x, 0),
                    "y": _r(float(np.exp(fit["intercept"] + fit["slope"] * np.log(x))), 4),
                }
                for x in (min(xs), max(xs))
            ],
        },
        "focus": {
            # Display strings, typeset by the report's own pass. The browser
            # prints them as given: re-implementing the transform in JavaScript
            # would be a second copy of a rule that already exists in Python,
            # and the figure would eventually disagree with the prose about
            # whether a multiplication sign is the letter x.
            "residual_display": apply_typography(
                _fmt_multiple(residual["residual_ratio_scale"])
            ),
            "residual_ci_display": apply_typography(
                _fmt_ci_multiple(residual["residual_ratio_ci"])
            ),
            "sector": "cleantech",
            "residual_ratio": _r(residual["residual_ratio_scale"], 2),
            "residual_ci": [_r(v, 2) for v in residual["residual_ratio_ci"]],
            "ci_excludes_zero": bool(residual["ci_excludes_zero"]),
        },
        "steps": [
            {
                "id": "observed",
                "caption_key": None,
                "caption": (
                    "Twenty-three sectors, at their observed emerging-market representation."
                ),
            },
            {
                "id": "pattern",
                "caption_key": "h1b.elasticity",
                "caption_prefix": (
                    "Re-scaled against capital intensity. "
                    "The relationship is an elasticity of "
                ),
            },
            {
                "id": "prediction",
                "caption_key": None,
                "caption": ("Predicted positions, and the residual each sector carries."),
            },
            {
                "id": "exception",
                "caption_key": "h1b.cleantech_residual",
                "caption_prefix": "Cleantech sits above its prediction, at ",
            },
        ],
        "axis": {
            "x": {
                "log": True,
                "unit": "USD",
                "label": "Median advanced-economy deal size, constant 2015 USD",
            },
            "y": {"log": True, "label": "EM representation relative to AE", "reference": 1.0},
        },
    }


def fig05_share_crossover(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Green's share of deals against its share of dollars."""
    amount = cfg.pipeline["deflate"]["real_column"]
    by_year = (
        deals.groupby("year")
        .apply(
            lambda d: pd.Series(
                {
                    "count_share": 100 * d["green"].mean(),
                    "dollar_share": 100
                    * d.loc[d["green"], amount].sum()
                    / max(d[amount].sum(), 1e-9),
                    "deals": len(d),
                    "green": int(d["green"].sum()),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    marks = [
        {
            "year": int(r["year"]),
            "count_share": _r(r["count_share"], 2),
            "dollar_share": _r(r["dollar_share"], 2),
            "deals": _ints(r["deals"]),
            "green": _ints(r["green"]),
        }
        for _, r in by_year.iterrows()
    ]
    early = deals.loc[deals["year"].lt(2005) & deals["green"]].groupby("year").size()
    return {
        "marks": marks,
        "series": [
            {"id": "count_share", "label": "Share of green deals", "colour_role": "muted"},
            {"id": "dollar_share", "label": "Share of green dollars", "colour_role": "green"},
        ],
        "thin_cells": [{"year": int(y), "green": int(n)} for y, n in early.items()],
        "annotations": [
            {
                "id": "crossover",
                "year": 2005,
                "text": (
                    "The series cross: from here a green deal is larger than the average deal"
                ),
            }
        ],
        "axis": {
            "x": {"domain": [2000, 2012]},
            "y": {"unit": "%", "label": "Share of all recorded activity"},
        },
    }


def fig06_subdomain(deals: pd.DataFrame) -> dict[str, Any]:
    """Share of green deals resolved to a specific sub-domain, by bloc."""
    green = deals.loc[deals["green"] & deals["green_subdomain"].notna()]
    tab = pd.crosstab(green["bloc"], green["green_subdomain"])
    order = [b for b in ("AE", "CHINA", "EM") if b in tab.index]
    tab = tab.reindex(order)
    shares = tab.div(tab.sum(axis=1), axis=0) * 100
    unspec = shares.get("general_unspecified", pd.Series(0.0, index=shares.index))

    marks = []
    for bloc in order:
        role, label = BLOC_ROLE[bloc]
        marks.append(
            {
                "bloc": bloc,
                "label": label,
                # One decimal place, matching measure.*_unspecified_pct in
                # findings.json. At two the figure read 88.24% on a page whose
                # sentence beside it read 88.2%.
                "specific_pct": _r(100 - float(unspec[bloc]), 1),
                "unspecified_pct": _r(float(unspec[bloc]), 1),
                "n": _ints(tab.loc[bloc].sum()),
                "colour_role": role,
            }
        )
    return {
        "marks": marks,
        "segments": [
            {
                "id": "specific_pct",
                "label": "Resolved to a sub-domain",
                "colour_role": "green",
            },
            {
                "id": "unspecified_pct",
                "label": "“Clean Technology” and nothing more",
                "colour_role": "nongreen",
            },
        ],
        "annotations": [
            {
                "id": "em_companies",
                "text_key": "measure.em_unspecified_companies",
                "suffix_key": "measure.em_green_companies",
                "template": (
                    "{a} of {b} emerging-market green companies carry no more specific tag"
                ),
            }
        ],
        "axis": {
            "x": {"domain": [0, 100], "unit": "%", "label": "Share of the bloc's green deals"}
        },
    }


def fig07_cycle(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Green deals and disclosed green dollars by year. Toggles between the two."""
    amount = cfg.pipeline["deflate"]["real_column"]
    g = deals.loc[deals["green"]]
    by_year = (
        g.groupby("year")
        .agg(
            deals=("id", "size"),
            usd=(amount, lambda s: float(s.sum())),
            disclosed=(amount, "count"),
            median=(amount, "median"),
        )
        .reset_index()
    )
    marks = [
        {
            "year": int(r["year"]),
            "deals": _ints(r["deals"]),
            "usd_bn": _r(float(r["usd"]) / 1e9, 3),
            "disclosed": _ints(r["disclosed"]),
            "median_usd_m": _r(float(r["median"]) / 1e6, 2) if pd.notna(r["median"]) else None,
        }
        for _, r in by_year.iterrows()
    ]
    peak_deals = max(marks, key=lambda m: m["deals"] or 0)
    peak_usd = max(marks, key=lambda m: m["usd_bn"] or 0)
    return {
        "marks": marks,
        "views": [
            {
                "id": "deals",
                "label": "Deal count",
                "field": "deals",
                "unit": "deals",
                "colour_role": "green",
            },
            {
                "id": "dollars",
                "label": "Disclosed funding",
                "field": "usd_bn",
                "unit": "bn (constant 2015 USD)",
                "colour_role": "green",
            },
        ],
        "annotations": [
            {
                "id": "peak_deals",
                "year": peak_deals["year"],
                "text": f"Deal count peaks at {peak_deals['deals']}",
            },
            {
                "id": "peak_usd",
                "year": peak_usd["year"],
                "text": "Dollars peak a year before deals do",
            },
            {
                "id": "cheque",
                "text_key": "cheque.difference_pp",
                "prefix": "Within named stages, green cheque sizes fall ",
                "suffix": "pp further than non-green",
            },
        ],
        "axis": {"x": {"domain": [2000, 2012]}},
    }


def fig08_crisis(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Deal volume indexed to the pre-crisis base year, by bloc and green status."""
    res = h2_cycle.run(deals, cfg)
    series_tab = res["_tables"]["h2_indexed_series"]
    base = int(cfg.window["did_index_base_year"])

    roles = {
        "AE-green": ("green", "Advanced economies, green", None),
        "AE-non-green": ("nongreen", "Advanced economies, non-green", "4 3"),
    }
    series = []
    for name, (role, label, dash) in roles.items():
        sub = series_tab.loc[series_tab["series"].eq(name)].sort_values("year")
        if sub.empty:
            continue
        series.append(
            {
                "id": name,
                "label": label,
                "colour_role": role,
                "dash": dash,
                "points": [
                    {
                        "year": int(r["year"]),
                        "indexed": _r(r["indexed"], 1),
                        "deals": _ints(r["deals"]),
                    }
                    for _, r in sub.iterrows()
                ],
            }
        )
    drawdown = {k: _r(v["contraction_pct"], 1) for k, v in res["crisis_drawdown"].items()}
    return {
        "series": series,
        "base_year": base,
        "crisis_window": [2008, 2009],
        "drawdown": drawdown,
        "omitted_series": {
            "id": "EM-green",
            "reason_key": "h2.em_base_deals",
            "reason": (
                "not drawn: its base year holds a single deal, so the index leaves the canvas"
            ),
        },
        "annotations": [
            {
                "id": "pretrend",
                "text_key": "h2.pretrend_coef",
                "prefix": "Parallel trends fail: green was already growing ",
                "suffix": " log-points per year faster before the window",
            }
        ],
        "axis": {
            "x": {"domain": [2000, 2012]},
            "y": {"label": f"Deal volume, indexed to {base} = 100", "reference": 100},
        },
    }


def fig09_instruments(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Non-dilutive share of deals, green against non-green, by bloc."""
    res = h3_instrument.run(deals, cfg)
    shares = res["_tables"]["h3_non_dilutive_by_bloc"]
    shares = shares.loc[shares["bloc"].isin(["AE", "EM"])]
    min_cell = int(cfg.threshold("min_cell_n"))

    marks = []
    for bloc in ("AE", "EM"):
        for green in (True, False):
            r = shares.loc[shares["bloc"].eq(bloc) & shares["green"].eq(green)]
            if r.empty:
                continue
            r = r.iloc[0]
            marks.append(
                {
                    "bloc": bloc,
                    "green": bool(green),
                    "label": f"{BLOC_ROLE[bloc][1]}, {'green' if green else 'non-green'}",
                    "pct": _r(r["non_dilutive_pct"], 2),
                    "n": _ints(r["deals"]),
                    "non_dilutive": _ints(r["non_dilutive"]),
                    "grant": _ints(r["grant"]),
                    "debt": _ints(r["debt"]),
                    "colour_role": "green" if green else "nongreen",
                    "below_min_cell": bool(int(r["non_dilutive"]) < min_cell),
                }
            )
    return {
        "marks": marks,
        "min_cell": min_cell,
        "annotations": [
            {
                "id": "ae_test",
                "text_key": "h3.rr",
                "prefix": "Within advanced economies, green is ",
                "suffix": " times more likely",
            },
            {
                "id": "em_arm",
                "text_key": "h3.em_nondilutive_n",
                "prefix": "The emerging-market arm rests on ",
                "suffix": " non-dilutive deals",
            },
        ],
        "axis": {
            "x": {
                "domain": [0, 15],
                "unit": "%",
                "label": "Share of the group's deals using non-dilutive instruments",
            }
        },
    }


def fig10_depth_need(deals: pd.DataFrame, cfg: Config, rng) -> dict[str, Any]:
    """Green funding intensity against market depth, and the degenerate need regressor."""
    res = h5_allocation.run(deals, cfg, rng)
    panel = res["_tables"]["h5_country_panel"]
    depth = res["correlations"]["green_usd_per_capita"]["gdp_per_capita_usd"]
    deficit_test = res["falsifier_stress_tests"]["electricity_deficit_pct"]

    marks = [
        {
            "country": str(r["country_code"]),
            "gdp_per_capita": _r(r["gdp_per_capita_usd"], 0),
            "green_usd_per_capita": _r(r["green_usd_per_capita"], 4),
            "green_deals": _ints(r["green_deals"]),
            "all_deals": _ints(r["all_deals"]),
            "electricity_deficit_pct": _r(r["electricity_deficit_pct"], 2),
            "colour_role": "em",
        }
        for _, r in panel.iterrows()
    ]
    return {
        "marks": marks,
        "depth": {
            "rho": _r(depth["rho"], 3),
            "ci": [_r(v, 3) for v in depth["ci"]],
            "n": int(depth["n"]),
        },
        "need": {
            "variable": "electricity_deficit_pct",
            "non_trivial_values": int(deficit_test["non_trivial_values"]),
            "variance_carriers": list(deficit_test["variance_carriers"]),
            "degenerate": True,
            "note": "Panel (b) is deliberately static: there is nothing to explore.",
        },
        "concentration": {
            "gini": _r(res["concentration"]["gini"], 3),
            "top5_pct": _r(res["concentration"]["top5_share_pct"], 1),
        },
        "axis": {
            "x": {"log": True, "unit": "USD", "label": "GDP per capita, current USD"},
            "y": {"log": True, "label": "Green funding per capita, constant 2015 USD"},
        },
    }


def fig11_power_wall(cfg: Config) -> dict[str, Any]:
    """Every emerging-market test cell against the pre-registered minimum."""
    analysis = json.loads(
        (cfg.path("data_interim") / "analysis_findings.json").read_text(encoding="utf-8")
    )
    min_cell = int(cfg.threshold("min_cell_n"))
    em_green_nd = next(
        r["non_dilutive"]
        for r in analysis["h3"]["non_dilutive_by_bloc"]
        if r["bloc"] == "EM" and r["green"]
    )
    rows = [
        (
            "H2",
            "Largest EM green year-cell",
            analysis["h2"]["em_arm"]["largest_cell"],
            "difference-in-differences",
        ),
        ("H3", "EM green non-dilutive deals", em_green_nd, "instrument-mix test"),
        (
            "H4",
            "EM green seed entrants",
            analysis["h4"]["em_arm"]["cells"]["em_green_entrants"],
            "graduation model",
        ),
        (
            "H4",
            "AE green Series A to B pool",
            analysis["h4"]["power"]["ae_green_a_to_b_pool"],
            "missing-middle transition",
        ),
        (
            "H5",
            "Countries with any energy deficit",
            analysis["h5"]["falsifier_stress_tests"]["electricity_deficit_pct"][
                "non_trivial_values"
            ],
            "need-indicator regression",
        ),
    ]
    return {
        "marks": [
            {
                "hypothesis": h,
                "label": label,
                "value": int(value),
                "blocks": blocks,
                "colour_role": "muted",
                "clears_threshold": bool(int(value) >= min_cell),
            }
            for h, label, value, blocks in rows
        ],
        "threshold": {
            "value": min_cell,
            "label": f"minimum cell size, n = {min_cell}",
            "colour_role": "alert",
        },
        "axis": {
            "x": {
                "domain": [0, max(min_cell + 10, 40)],
                "label": "Observations available in the cell the test depends on",
            }
        },
    }


def fig12_continuity(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Two instruments, two populations, never pooled."""
    india = pd.read_csv(cfg.path("tables") / "fig12_india_continuity.csv")
    india = india.loc[india["year"].between(2015, 2019)]
    em = deals.loc[deals["bloc"].eq("EM")]
    em_year = em.groupby("year")["green"].agg(deals="size", green="sum").reset_index()
    return {
        "panels": [
            {
                "id": "crunchbase",
                "label": "Crunchbase 2013 Snapshot",
                "sublabel": "Emerging markets excluding China and LDCs, 2000–2012",
                "colour_role": "em",
                "marks": [
                    {
                        "year": int(r["year"]),
                        "green": _ints(r["green"]),
                        "deals": _ints(r["deals"]),
                    }
                    for _, r in em_year.iterrows()
                ],
            },
            {
                "id": "india",
                "label": "Indian startup funding scrape",
                "sublabel": "2015–2019",
                "colour_role": "ldc",
                "marks": [
                    {
                        "year": int(r["year"]),
                        "green": _ints(r["green_deals"]),
                        "deals": _ints(r["deals"]),
                    }
                    for _, r in india.iterrows()
                ],
            },
        ],
        "never_pooled": (
            "The panels share no axis. The taxonomies and amount conventions are not "
            "compatible, and the Indian data has no category_code so Tier A cannot fire."
        ),
        "annotations": [
            {
                "id": "india_rate",
                "text_key": "india.rate_pct",
                "prefix": "Green rate in the later window: ",
                "suffix": "%",
            }
        ],
    }


def figM1_censoring(cfg: Config) -> dict[str, Any]:  # noqa: N802 - matches the figure id
    """Monthly deals as a share of their own year. Establishes the censoring boundary."""
    tab = pd.read_csv(cfg.path("tables") / "diag_censoring_monthly_counts.csv", index_col=0)
    years = [2011, 2012, 2013]
    series = [
        {
            "id": str(year),
            "label": str(year),
            "colour_role": "alert" if year == 2013 else "muted",
            "dash": None if year == 2013 else "4 3",
            "points": [
                {
                    "month": int(m),
                    "share": _r(tab.loc[m, f"share_pct_{year}"], 2),
                    "deals": _ints(tab.loc[m, f"deals_{year}"]),
                }
                for m in tab.index
            ],
        }
        for year in years
    ]
    return {
        "series": series,
        "annotations": [
            {
                "id": "december",
                "text_key": "censor.dec_2013_pct",
                "prefix": "December 2013 holds ",
                "suffix": "% of its year",
            },
            {
                "id": "baseline",
                "text_key": "censor.dec_baseline_pct",
                "prefix": "against a baseline of ",
                "suffix": "%",
            },
        ],
        "axis": {
            "x": {"domain": [1, 12], "label": "Month"},
            "y": {"unit": "%", "label": "Share of the year's deals"},
        },
    }


# ---------------------------------------------------------------------------


def masthead(cfg: Config) -> dict[str, Any]:
    """Front matter, read from report/metadata.yaml.

    The same file the PDF's title page reads. The author list reaches the page
    structured rather than as the semicolon-joined string findings.json carries,
    because the masthead sets names and USNs in separate columns and splitting a
    joined string in the browser would make metadata.yaml's format load-bearing
    in two places.
    """
    # Reuses the report's loader rather than re-parsing: the file is fenced like
    # YAML front matter, and handling that in two places is how the two would
    # come to disagree.
    from gcg.report.render import load_metadata

    meta = load_metadata(cfg)
    return {
        "title": meta["title"],
        "subtitle": meta["subtitle"],
        "authors": [{"name": a["name"], "usn": a["usn"]} for a in meta["authors"]],
        "guide": meta["guide"],
        "institution": meta["institution"],
        "course": meta["course"],
        "date": meta["date"],
        # The page links to its own source; the README links to the page. Both
        # read from metadata.yaml so neither restates a URL that then drifts.
        "repo": meta.get("repo", "UNSET"),
        "site": meta.get("site", "UNSET"),
    }


def build(cfg: Config | None = None) -> dict[str, Any]:
    """Assemble the whole export."""
    cfg = cfg or load_config()
    rng = seed_everything(cfg)
    deals = read_parquet(cfg.path("data_processed") / "deals.parquet")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_from_commit": _commit(cfg),
        "window": {"start": int(cfg.window["start"][:4]), "end": int(cfg.window["end"][:4])},
        "meta": masthead(cfg),
        "fig01_coverage": fig01_coverage(cfg),
        "fig02_double_gap": fig02_double_gap(deals, cfg),
        "fig03_rate_by_year": fig03_rate_by_year(deals, cfg),
        "fig04_ladder": fig04_ladder(deals, cfg),
        "fig05_share_crossover": fig05_share_crossover(deals, cfg),
        "fig06_subdomain": fig06_subdomain(deals),
        "fig07_cycle": fig07_cycle(deals, cfg),
        "fig08_crisis": fig08_crisis(deals, cfg),
        "fig09_instruments": fig09_instruments(deals, cfg),
        "fig10_depth_need": fig10_depth_need(deals, cfg, rng),
        "fig11_power_wall": fig11_power_wall(cfg),
        "fig12_continuity": fig12_continuity(deals, cfg),
        "figM1_censoring": figM1_censoring(cfg),
    }
    return payload


def main(cfg: Config | None = None) -> int:
    """Write web/data/series.json and copy findings.json beside it."""
    cfg = cfg or load_config()
    payload = build(cfg)

    out_dir = Path(cfg.root) / "web" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    # The two exports must state a shared quantity the same way. A precision
    # mismatch between them reaches the page as a figure disagreeing with the
    # sentence beside it, which the bare-number gate cannot see because both
    # values are legitimately computed.
    from gcg.web.agreement import AgreementError
    from gcg.web.agreement import check as check_agreement

    findings_now = json.loads(cfg.path("findings").read_text(encoding="utf-8"))
    disagreements = check_agreement(payload, findings_now)
    if disagreements:
        msg = (
            f"{len(disagreements)} quantity(ies) stated differently by series.json "
            f"and findings.json:\n  " + "\n  ".join(disagreements)
        )
        raise AgreementError(msg)

    series_path = out_dir / "series.json"
    series_path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")

    findings_src = cfg.path("findings")
    if not findings_src.is_file():
        msg = f"missing {findings_src}. Run `make analysis` first."
        raise FileNotFoundError(msg)
    (out_dir / "findings.json").write_text(
        findings_src.read_text(encoding="utf-8"), encoding="utf-8"
    )

    figures = [k for k in payload if k.startswith("fig")]
    LOG.info(
        "wrote %s (%d figure keys, %.0f KB) and copied findings.json",
        series_path.name,
        len(figures),
        series_path.stat().st_size / 1024,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
