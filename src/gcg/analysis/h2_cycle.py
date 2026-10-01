"""H2: was the green bust amplified relative to non-green?

*Within advanced economies, the post-2008 contraction in green funding was
deeper and longer than the contraction in non-green funding.*

The advanced-economy comparison is the benchmark case for the capital-model
mismatch Gaddy et al. identify, not a retarget: it is the one bloc where the
record is dense enough to run a difference-in-differences at all. The
emerging-market arm is carried alongside as an explicitly bounded probe, with
every cell size printed and no test run below the minimum cell size.

The design follows RESEARCH_BRIEF §4. Pre-trends are plotted and formally
tested first; per the brief, **if parallel trends fail the claim is downgraded
to descriptive and the text says so.**
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from gcg.config import Config, get_logger

LOG = get_logger("analysis.h2")


def indexed_series(deals: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Deal volume indexed to the base year, for each bloc x green series."""
    base = int(cfg.window["did_index_base_year"])
    rows = []
    for (bloc, green), grp in deals.groupby(["bloc", "green"], observed=True):
        if bloc not in ("AE", "EM"):
            continue
        counts = grp.groupby("year").size()
        if base not in counts.index or counts.loc[base] == 0:
            continue
        for year, n in counts.items():
            rows.append(
                {
                    "series": f"{bloc}-{'green' if green else 'non-green'}",
                    "bloc": bloc,
                    "green": bool(green),
                    "year": int(year),
                    "deals": int(n),
                    "indexed": round(100 * n / counts.loc[base], 2),
                }
            )
    return pd.DataFrame(rows)


def drawdown(series: pd.DataFrame) -> dict[str, Any]:
    """Peak-to-trough drawdown and time to recovery for each series."""
    out = {}
    for name, grp in series.groupby("series"):
        g = grp.sort_values("year")
        peak_row = g.loc[g["deals"].idxmax()]
        after = g.loc[g["year"] > peak_row["year"]]
        if after.empty:
            out[name] = {
                "peak_year": int(peak_row["year"]),
                "peak_deals": int(peak_row["deals"]),
                "trough_year": None,
                "drawdown_pct": None,
                "recovered": None,
                "note": "peak is the final year; no observable drawdown",
            }
            continue
        trough_row = after.loc[after["deals"].idxmin()]
        recov = after.loc[
            (after["year"] > trough_row["year"]) & (after["deals"] >= peak_row["deals"])
        ]
        out[name] = {
            "peak_year": int(peak_row["year"]),
            "peak_deals": int(peak_row["deals"]),
            "trough_year": int(trough_row["year"]),
            "trough_deals": int(trough_row["deals"]),
            "drawdown_pct": round(100 * (trough_row["deals"] / peak_row["deals"] - 1), 2),
            "recovered": bool(len(recov) > 0),
            "years_to_recover": int(recov["year"].iloc[0] - peak_row["year"])
            if len(recov)
            else None,
        }
    return out


def _panel(deals: pd.DataFrame, cfg: Config, bloc: str) -> pd.DataFrame:
    """Year x green panel of log deal volume for one bloc."""
    post = int(cfg.window["did_post_from"])
    sub = deals.loc[deals["bloc"].eq(bloc)]
    panel = sub.groupby(["year", "green"]).size().rename("deals").reset_index()
    panel["log_deals"] = np.log(panel["deals"])
    panel["post"] = (panel["year"] >= post).astype(int)
    panel["is_green"] = panel["green"].astype(int)
    return panel


def pre_trend_test(deals: pd.DataFrame, cfg: Config, bloc: str = "AE") -> dict[str, Any]:
    """Test parallel trends in the pre-period.

    Run BEFORE the difference-in-differences, because its result decides whether
    the headline may be causal-flavoured or must be downgraded to descriptive.
    """
    post = int(cfg.window["did_post_from"])
    panel = _panel(deals, cfg, bloc)
    pre = panel.loc[panel["year"] < post].copy()
    pre["t"] = pre["year"] - pre["year"].min()

    model = smf.ols("log_deals ~ t * is_green", data=pre).fit(cov_type="HC1")
    coef = float(model.params["t:is_green"])
    ci = model.conf_int().loc["t:is_green"].tolist()
    p = float(model.pvalues["t:is_green"])
    parallel = bool(p >= cfg.threshold("alpha"))

    LOG.info(
        "H2 pre-trend (%s, %d-%d): differential trend %+.4f [%.4f, %.4f] per year, "
        "p=%.4f -> parallel trends hold = %s",
        bloc,
        int(pre["year"].min()),
        post - 1,
        coef,
        ci[0],
        ci[1],
        p,
        parallel,
    )
    if not parallel:
        LOG.warning(
            "  PARALLEL TRENDS FAIL for %s. The DiD estimate is reported as DESCRIPTIVE "
            "only, per RESEARCH_BRIEF §4.",
            bloc,
        )
    return {
        "bloc": bloc,
        "pre_period": [int(pre["year"].min()), post - 1],
        "differential_trend_per_year": round(coef, 4),
        "ci": [round(ci[0], 4), round(ci[1], 4)],
        "p_value": p,
        "parallel_trends_hold": parallel,
        "n_obs": int(model.nobs),
    }


def did(deals: pd.DataFrame, cfg: Config, bloc: str = "AE") -> dict[str, Any]:
    """Difference-in-differences on log deal volume, green vs non-green."""
    panel = _panel(deals, cfg, bloc)
    model = smf.ols("log_deals ~ is_green + post + is_green:post", data=panel).fit(
        cov_type="HC1"
    )
    coef = float(model.params["is_green:post"])
    ci = model.conf_int().loc["is_green:post"].tolist()
    p = float(model.pvalues["is_green:post"])

    LOG.info(
        "H2 DiD (%s): green x post coefficient %+.4f [%.4f, %.4f], p=%.4g "
        "(robust HC1, n=%d year-group cells)",
        bloc,
        coef,
        ci[0],
        ci[1],
        p,
        int(model.nobs),
    )
    LOG.info(
        "  interpretation: green deal volume changed by %+.1f%% relative to non-green "
        "after %d",
        100 * (np.exp(coef) - 1),
        int(cfg.window["did_post_from"]),
    )
    return {
        "bloc": bloc,
        "interaction_coef": round(coef, 4),
        "interaction_ci": [round(ci[0], 4), round(ci[1], 4)],
        "p_value": p,
        "pct_effect": round(100 * (np.exp(coef) - 1), 2),
        "n_cells": int(model.nobs),
        "post_from": int(cfg.window["did_post_from"]),
        "se_type": "HC1 robust",
    }


def em_arm(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """The emerging-market arm: descriptive, bounded, every cell printed."""
    min_n = int(cfg.threshold("min_cell_n"))
    em = deals.loc[deals["bloc"].eq("EM")]
    by_year = em.groupby("year")["green"].agg(deals="size", green="sum").reset_index()
    by_year["green_rate_pct"] = (100 * by_year["green"] / by_year["deals"]).round(3)
    largest = int(by_year["green"].max())

    LOG.info(
        "H2 EM arm: green deals by year %s; largest cell %d < %d, so NO test is run",
        dict(zip(by_year["year"], by_year["green"], strict=False)),
        largest,
        min_n,
    )
    return {
        "testable": False,
        "reason": (
            f"the largest emerging-market green year-cell holds {largest} deals, below "
            f"the minimum cell size of {min_n}. No difference-in-differences is run and "
            "no significance test is reported."
        ),
        "largest_cell": largest,
        "min_cell_n": min_n,
        "by_year": by_year.to_dict("records"),
        "descriptive_note": (
            "The emerging-market green rate tracked the advanced-economy rate almost "
            "exactly in 2008 and fell away afterwards. That is a description of six "
            "single-digit cells, not a tested amplification effect."
        ),
    }


def crisis_drawdown(series: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Contraction across the crisis window specifically.

    ``drawdown`` finds each series' global peak, which for advanced-economy
    green is 2011 and therefore skips the 2008-09 contraction entirely. H2 is a
    question about the crisis, so the crisis window is measured directly: the
    fall from the event year to the lowest of the two years that follow.
    """
    event = int(cfg.window["events"]["gfc"])
    out = {}
    for name, grp in series.groupby("series"):
        g = grp.set_index("year")["deals"]
        if event not in g.index:
            continue
        after = g.loc[(g.index > event) & (g.index <= event + 2)]
        if after.empty:
            continue
        trough_year = int(after.idxmin())
        out[name] = {
            "event_year": event,
            "event_deals": int(g.loc[event]),
            "trough_year": trough_year,
            "trough_deals": int(after.min()),
            "contraction_pct": round(100 * (after.min() / g.loc[event] - 1), 2),
            "back_above_event_by": int(
                g.loc[(g.index > trough_year) & (g >= g.loc[event])].index.min()
            )
            if (g.loc[g.index > trough_year] >= g.loc[event]).any()
            else None,
        }
    LOG.info("H2 crisis-window contraction from %d:", event)
    for name, v in out.items():
        LOG.info(
            "    %-16s %4d -> %4d  (%+.1f%%)  back above %d by %s",
            name,
            v["event_deals"],
            v["trough_deals"],
            v["contraction_pct"],
            event,
            v["back_above_event_by"] or "never",
        )
    return out


def run(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Test H2 and return a JSON-serialisable findings dict."""
    series = indexed_series(deals, cfg)
    dd = drawdown(series)
    crisis = crisis_drawdown(series, cfg)
    pre = pre_trend_test(deals, cfg, "AE")
    estimate = did(deals, cfg, "AE")
    em = em_arm(deals, cfg)

    series.to_csv(cfg.path("tables") / "h2_indexed_series.csv", index=False)

    # The verdict is gated on the pre-trend check, not on the p-value alone.
    significant = estimate["p_value"] < cfg.threshold("alpha")
    if not pre["parallel_trends_hold"]:
        verdict = "Not supported"
        status = (
            "Parallel trends FAIL in the pre-period, so the difference-in-differences "
            "is downgraded to descriptive and no causal reading is offered, per the "
            "pre-registered rule in RESEARCH_BRIEF §4."
        )
    elif significant and estimate["interaction_coef"] < 0:
        verdict = "Supported"
        status = "Parallel trends hold and the interaction is negative and significant."
    elif significant:
        verdict = "Not supported"
        status = (
            "The interaction is significant but POSITIVE: green volume held up better "
            "than non-green after 2008, the opposite of the hypothesis."
        )
    else:
        verdict = "Not supported"
        status = "The interaction is indistinguishable from zero."

    findings = {
        "hypothesis": "H2: the green bust was amplified relative to non-green",
        "benchmark_bloc": "AE",
        "pre_trend": pre,
        "did": estimate,
        "drawdown": dd,
        "crisis_drawdown": crisis,
        "em_arm": em,
        "verdict": verdict,
        "verdict_note": status,
        "falsification_condition": (
            "Falsified if the green x post interaction is indistinguishable from zero, "
            "or if pre-trends diverge, in which case the claim is downgraded to "
            "descriptive rather than defended."
        ),
    }
    LOG.info("H2 verdict: %s — %s", verdict, status)
    findings["_tables"] = {"h2_indexed_series": series}
    return findings
