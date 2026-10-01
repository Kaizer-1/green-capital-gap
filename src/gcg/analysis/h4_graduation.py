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
    testable = [m for m in (seed_a, a_b) if m.get("testable")]
    if not testable:
        verdict = "Not supported"
        note = "Neither transition is testable at the configured minimum cell size."
    else:
        sig_neg = [
            m
            for m in testable
            if m["p_value"] < cfg.threshold("alpha") and m["odds_ratio"] < 1
        ]
        if not sig_neg:
            verdict = "Not supported"
            note = (
                "Green ventures are not significantly less likely to graduate than "
                "non-green ones at either transition under the headline specification."
            )
        elif (
            a_b.get("testable")
            and a_b in sig_neg
            and (not seed_a.get("testable") or a_b["odds_ratio"] < seed_a["odds_ratio"])
        ):
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
        "verdict": verdict,
        "verdict_note": note,
        "falsification_condition": (
            "Falsified if the green coefficient is null, or if the gap is no larger at "
            "A to B than at seed to A."
        ),
    }
    LOG.info("H4 verdict: %s — %s", verdict, note)
    findings["_tables"] = {"h4_graduation_rates": rates}
    return findings
