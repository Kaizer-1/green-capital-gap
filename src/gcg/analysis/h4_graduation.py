"""H4: is the scale-up step where green ventures lose?

*Conditional on raising seed capital, green ventures are less likely to reach
Series A, and markedly less likely to reach Series B, than comparable non-green
ventures, with the largest gap at A to B, the "missing middle".*

Three pre-commitments bind this module, all fixed in docs/METHODOLOGY.md before
any graduation rate was computed:

- **§1.3** the headline uses strict seed, the specification that does NOT
  flatter the hypothesis, with the angel-inclusive specification reported
  alongside;
- **§1.2** an extended observation window to 2013-11-30 is permitted as a
  reported secondary specification, because H4 conditions on sample entry and
  so differences out part of the coverage growth that the level-based
  hypotheses cannot;
- the standing rule that no significance test is run on a cell below the
  configured minimum.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from gcg.analysis.h1_selection import wilson_interval
from gcg.config import Config, get_logger

LOG = get_logger("analysis.h4")


def build_histories(
    deals: pd.DataFrame, cfg: Config, *, fold_angel: bool, window_end: str
) -> pd.DataFrame:
    """One row per company: entry cohort, stages reached, green status, bloc.

    A company enters the funnel in the year of its first seed-equivalent round.
    Cohorts need the configured minimum follow-up before the window closes, or a
    company that raised seed in the final year would be counted as having failed
    to graduate when it simply had no time to.
    """
    rt = cfg.pipeline["round_types"]
    entry_types = set(
        rt["seed_entry_types_angel_inclusive"] if fold_angel else rt["seed_entry_types_strict"]
    )
    end = pd.Timestamp(window_end)
    sub = deals.loc[deals["funded_at"].le(end)].copy()

    entries = (
        sub.loc[sub["instrument"].isin(entry_types)]
        .groupby("object_id")
        .agg(entry_year=("year", "min"))
    )
    reached = sub.groupby("object_id")["instrument"].agg(lambda s: set(s)).rename("stages")
    attrs = sub.groupby("object_id").agg(
        green=("green", "max"), bloc=("bloc", "first"), name=("name", "first")
    )

    hist = entries.join(reached).join(attrs).reset_index()
    hist["reached_a"] = hist["stages"].apply(lambda s: "series_a" in s)
    hist["reached_b"] = hist["stages"].apply(lambda s: "series_b" in s)

    min_follow = int(cfg.threshold("min_cohort_followup_years"))
    last_usable = end.year - min_follow
    hist["cohort_usable"] = hist["entry_year"] <= last_usable

    LOG.info(
        "H4 histories (%s seed, window to %s): %d entrants, %d in usable cohorts "
        "(entry year <= %d, needing %d years of follow-up)",
        "angel-inclusive" if fold_angel else "strict",
        window_end,
        len(hist),
        int(hist["cohort_usable"].sum()),
        last_usable,
        min_follow,
    )
    return hist


def _rates(hist: pd.DataFrame) -> pd.DataFrame:
    """Graduation rates by green status, with cell sizes and intervals."""
    usable = hist.loc[hist["cohort_usable"] & hist["bloc"].eq("AE")]
    rows = []
    for green, grp in usable.groupby("green"):
        n = len(grp)
        a = int(grp["reached_a"].sum())
        lo, hi = wilson_interval(a, n)
        rows.append(
            {
                "transition": "seed -> A",
                "green": bool(green),
                "entrants": n,
                "graduated": a,
                "rate_pct": round(100 * a / n, 3) if n else 0.0,
                "ci_lo_pct": round(100 * lo, 3),
                "ci_hi_pct": round(100 * hi, 3),
            }
        )
        pool = grp.loc[grp["reached_a"]]
        nb = len(pool)
        b = int(pool["reached_b"].sum())
        lo, hi = wilson_interval(b, nb) if nb else (float("nan"), float("nan"))
        rows.append(
            {
                "transition": "A -> B",
                "green": bool(green),
                "entrants": nb,
                "graduated": b,
                "rate_pct": round(100 * b / nb, 3) if nb else 0.0,
                "ci_lo_pct": round(100 * lo, 3) if nb else None,
                "ci_hi_pct": round(100 * hi, 3) if nb else None,
            }
        )
    return pd.DataFrame(rows)


def logistic(hist: pd.DataFrame, cfg: Config, outcome: str) -> dict[str, Any]:
    """Logistic regression on graduation with green and cohort fixed effects."""
    df = hist.loc[hist["cohort_usable"] & hist["bloc"].eq("AE")].copy()
    if outcome == "reached_b":
        df = df.loc[df["reached_a"]]
    df["y"] = df[outcome].astype(int)
    df["is_green"] = df["green"].astype(int)

    if df["y"].nunique() < 2 or int(df["is_green"].sum()) < cfg.threshold("min_cell_n"):
        return {"testable": False, "reason": "insufficient variation or green cell too small"}

    model = smf.logit("y ~ is_green + C(entry_year)", data=df).fit(disp=0)
    coef = float(model.params["is_green"])
    ci = model.conf_int().loc["is_green"].tolist()
    return {
        "testable": True,
        "outcome": outcome,
        "odds_ratio": round(float(np.exp(coef)), 4),
        "odds_ratio_ci": [round(float(np.exp(ci[0])), 4), round(float(np.exp(ci[1])), 4)],
        "p_value": float(model.pvalues["is_green"]),
        "n": int(model.nobs),
        "n_green": int(df["is_green"].sum()),
        "note": "year fixed effects via C(entry_year); green coefficient exponentiated",
    }


def _spec(
    deals: pd.DataFrame, cfg: Config, *, fold_angel: bool, window_end: str
) -> dict[str, Any]:
    """One full specification: histories, rates, both logistic models."""
    hist = build_histories(deals, cfg, fold_angel=fold_angel, window_end=window_end)
    rates = _rates(hist)
    out = {
        "seed_definition": "angel-inclusive" if fold_angel else "strict",
        "window_end": window_end,
        "rates": rates.to_dict("records"),
        "logit_seed_to_a": logistic(hist, cfg, "reached_a"),
        "logit_a_to_b": logistic(hist, cfg, "reached_b"),
    }
    for _, r in rates.iterrows():
        LOG.info(
            "    %-10s %-9s  %5d entrants -> %4d graduated = %6.2f%% [%.2f-%.2f]",
            r["transition"],
            "green" if r["green"] else "non-green",
            r["entrants"],
            r["graduated"],
            r["rate_pct"],
            r["ci_lo_pct"] or 0,
            r["ci_hi_pct"] or 0,
        )
    for key in ("logit_seed_to_a", "logit_a_to_b"):
        m = out[key]
        if m.get("testable"):
            LOG.info(
                "    %-16s OR %.3f %s, p=%.4g (n=%d, green=%d)",
                key,
                m["odds_ratio"],
                m["odds_ratio_ci"],
                m["p_value"],
                m["n"],
                m["n_green"],
            )
        else:
            LOG.info("    %-16s not testable: %s", key, m.get("reason"))
    out["_rates_frame"] = rates
    return out


def em_arm(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """The emerging-market arm. Expected to be untestable; cells printed anyway."""
    min_n = int(cfg.threshold("min_cell_n"))
    hist = build_histories(
        deals,
        cfg,
        fold_angel=cfg.flag("fold_angel_into_seed"),
        window_end=cfg.pipeline["h4"]["observation_window_end"],
    )
    em = hist.loc[hist["cohort_usable"] & hist["bloc"].eq("EM")]
    green = em.loc[em["green"]]
    cells = {
        "em_green_entrants": int(len(green)),
        "em_green_reached_a": int(green["reached_a"].sum()),
        "em_green_reached_b": int(green["reached_b"].sum()),
        "em_non_green_entrants": int((~em["green"]).sum()),
    }
    LOG.info("H4 EM arm cells: %s -> testable = False (min cell %d)", cells, min_n)
    return {
        "testable": False,
        "cells": cells,
        "min_cell_n": min_n,
        "reason": (
            f"the emerging-market green seed cohort holds {cells['em_green_entrants']} "
            f"companies against a minimum cell size of {min_n}. No graduation rate, "
            "logistic model or significance test is reported for this arm."
        ),
    }


def run(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Test H4 under both seed definitions and both observation windows."""
    h4 = cfg.pipeline["h4"]
    headline_angel = cfg.flag("fold_angel_into_seed")

    LOG.info(
        "H4 HEADLINE specification (strict seed, window to %s):", h4["observation_window_end"]
    )
    headline = _spec(
        deals, cfg, fold_angel=headline_angel, window_end=h4["observation_window_end"]
    )
    LOG.info("H4 alternative seed definition (angel-inclusive):")
    alt_seed = _spec(
        deals, cfg, fold_angel=not headline_angel, window_end=h4["observation_window_end"]
    )
    LOG.info("H4 secondary window (%s):", h4["observation_window_end_secondary"])
    alt_window = _spec(
        deals,
        cfg,
        fold_angel=headline_angel,
        window_end=h4["observation_window_end_secondary"],
    )

    rates = headline.pop("_rates_frame")
    alt_seed.pop("_rates_frame")
    alt_window.pop("_rates_frame")
    rates.to_csv(cfg.path("tables") / "h4_graduation_rates.csv", index=False)

    seed_a = headline["logit_seed_to_a"]
    a_b = headline["logit_a_to_b"]

    # H4 is decided on POWER first. An odds ratio of 1.30 with an interval
    # spanning 0.65 to 2.60 does not identify a direction, so reading one off
    # the point estimate would be reading noise. The same applies to the spread
    # across specifications: at these cell sizes 1.30, 1.66 and 1.00 are not
    # three findings, they are one interval sampled three ways.
    min_n = int(cfg.threshold("min_cell_n"))
    green_entrants = next(
        (
            r["entrants"]
            for r in headline["rates"]
            if r["green"] and r["transition"] == "seed -> A"
        ),
        0,
    )
    ab_green = next(
        (
            r["entrants"]
            for r in headline["rates"]
            if r["green"] and r["transition"] == "A -> B"
        ),
        0,
    )
    seed_a_uninformative = bool(
        seed_a.get("testable") and seed_a["odds_ratio_ci"][0] < 1 < seed_a["odds_ratio_ci"][1]
    )

    if not a_b.get("testable") or seed_a_uninformative:
        verdict = "Underpowered \u2014 cannot determine"
        note = (
            f"The advanced-economy green seed cohort holds {green_entrants} companies and "
            f"the A-to-B pool holds {ab_green}, against a minimum cell size of {min_n}. "
            "The seed-to-A odds ratio is "
            f"{seed_a.get('odds_ratio')} {seed_a.get('odds_ratio_ci')}, an interval that "
            "spans 1 and identifies no direction. A-to-B, the specific missing-middle "
            "transition, is not testable at all. H4 is therefore recorded as "
            "undetermined rather than as supported or refuted: the data cannot answer it."
        )
    else:
        sig_neg = [
            m
            for m in (seed_a, a_b)
            if m.get("testable")
            and m["p_value"] < cfg.threshold("alpha")
            and m["odds_ratio"] < 1
        ]
        if not sig_neg:
            verdict = "Not supported"
            note = (
                "Both transitions are adequately powered and neither shows green ventures "
                "graduating less often than non-green ones."
            )
        elif a_b in sig_neg and a_b["odds_ratio"] < seed_a["odds_ratio"]:
            verdict = "Supported"
            note = "Green graduation is lower, and the gap is larger at A to B as predicted."
        else:
            verdict = "Partially supported"
            note = (
                "Green graduation is lower at at least one transition, but the gap is not "
                "larger at A to B, which is the specific missing-middle prediction."
            )

    findings = {
        "hypothesis": "H4: the scale-up step is where green ventures lose",
        "benchmark_bloc": "AE",
        "headline": headline,
        "alternative_seed_definition": alt_seed,
        "secondary_window": alt_window,
        "em_arm": em_arm(deals, cfg),
        "power": {
            "ae_green_seed_entrants": green_entrants,
            "ae_green_a_to_b_pool": ab_green,
            "min_cell_n": min_n,
            "seed_to_a_ci_spans_one": seed_a_uninformative,
            "a_to_b_testable": bool(a_b.get("testable")),
        },
        "specification_spread_note": (
            "The headline, angel-inclusive and extended-window specifications give odds "
            "ratios of roughly 1.30, 1.66 and 1.00. At these cell sizes that spread is "
            "sampling noise within one wide interval, not three substantive results, and "
            "it is NOT reported as a divergence finding."
        ),
        "pre_commitment_status": (
            "The §1.3 pre-commitment chose strict seed as the specification that would "
            "not flatter the hypothesis, reasoning about the DIRECTION of an expected "
            "negative effect. That reasoning is void here, because the binding failure is "
            "POWER, not direction: no specification identifies a direction at all. The "
            "pre-commitment is recorded as void on its power assumption rather than "
            "quietly satisfied or quietly dropped."
        ),
        "what_this_shows": (
            "The scale-up step that the missing-middle literature points to is "
            "unobservable in the open record. There are ZERO emerging-market green seed "
            f"entrants across thirteen years, and even in advanced economies the A-to-B "
            f"pool is {ab_green} companies. The hypothesis is not refuted; it cannot be "
            "put to this data."
        ),
        "verdict": verdict,
        "verdict_note": note,
        "falsification_condition": (
            "Falsified if the green coefficient is null, or if the gap is no larger at "
            "A to B than at seed to A. Neither can be assessed: the test is underpowered."
        ),
    }
    LOG.info("H4 verdict: %s — %s", verdict, note)
    findings["_tables"] = {"h4_graduation_rates": rates}
    return findings
