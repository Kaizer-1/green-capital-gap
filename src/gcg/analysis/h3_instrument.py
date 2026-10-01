"""H3: is green capital less dilutive than non-green?

*Green ventures draw a higher share of funding from grants, debt and other
non-venture instruments than non-green ventures do.*

**Caveat stated before the numbers**, per docs/METHODOLOGY.md §11. The record
codes infrastructure project equity as ordinary venture rounds: KSK Power
Venture's coal-and-hydro financing appears as ``series_a``, Greenko's and
Akenerji's as ``venture_unspecified``. Project finance that is debt or
concessional in substance but equity-coded understates the non-dilutive share on
both sides, and more so for emerging markets, where independent power producers
are seven of 28 green companies. A null or reversed emerging-market result is
therefore biased toward the answer it gives and cannot be read as evidence
against the hypothesis.

The grant arm is descriptive only where cells fall below the minimum size, a
decision recorded in docs/METHODOLOGY.md §1.1 before the split was computed.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from gcg.analysis.h1_selection import two_proportion_test
from gcg.config import Config, get_logger

LOG = get_logger("analysis.h3")


def _families(cfg: Config) -> dict[str, str]:
    fam = cfg.pipeline["round_types"]["instrument_family"]
    return {v: k for k, members in fam.items() for v in members}


def mix_table(deals: pd.DataFrame, cfg: Config, bloc: str) -> pd.DataFrame:
    """Instrument-family mix by green status, in counts and dollars."""
    amount = cfg.pipeline["deflate"]["real_column"]
    rev = _families(cfg)
    sub = deals.loc[deals["bloc"].eq(bloc)].copy()
    sub["family"] = sub["instrument"].map(rev).fillna("other")

    rows = []
    for green, grp in sub.groupby("green"):
        total, total_usd = len(grp), float(grp[amount].sum())
        for fam, fg in grp.groupby("family"):
            rows.append(
                {
                    "bloc": bloc,
                    "green": bool(green),
                    "family": fam,
                    "deals": len(fg),
                    "deal_share_pct": round(100 * len(fg) / total, 3),
                    "usd_real2015": float(fg[amount].sum()),
                    "dollar_share_pct": round(100 * float(fg[amount].sum()) / total_usd, 3)
                    if total_usd
                    else 0.0,
                }
            )
    return pd.DataFrame(rows)


def chi2_test(deals: pd.DataFrame, cfg: Config, bloc: str) -> dict[str, Any]:
    """Chi-squared test of independence with Cramer's V as the effect size."""
    rev = _families(cfg)
    sub = deals.loc[deals["bloc"].eq(bloc)].copy()
    sub["family"] = sub["instrument"].map(rev).fillna("other")
    table = pd.crosstab(sub["green"], sub["family"])

    # Families with tiny expected counts break the chi-squared approximation.
    keep = [c for c in table.columns if table[c].sum() >= cfg.threshold("min_cell_n")]
    dropped = [c for c in table.columns if c not in keep]
    table = table[keep]

    chi2, p, dof, expected = stats.chi2_contingency(table)
    n = table.to_numpy().sum()
    cramers_v = float(np.sqrt(chi2 / (n * (min(table.shape) - 1))))

    LOG.info(
        "H3 chi-squared (%s): chi2=%.2f, dof=%d, p=%.4g, Cramer's V=%.4f, n=%d; "
        "families tested %s%s",
        bloc,
        chi2,
        dof,
        p,
        cramers_v,
        n,
        keep,
        f"; dropped as too small: {dropped}" if dropped else "",
    )
    return {
        "bloc": bloc,
        "chi2": round(float(chi2), 3),
        "dof": int(dof),
        "p_value": float(p),
        "cramers_v": round(cramers_v, 4),
        "n": int(n),
        "families_tested": keep,
        "families_dropped_small": dropped,
        "min_expected_count": round(float(expected.min()), 2),
    }


def non_dilutive_shares(deals: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Non-dilutive share by bloc and green status, with cell sizes."""
    rev = _families(cfg)
    sub = deals.copy()
    sub["family"] = sub["instrument"].map(rev).fillna("other")
    rows = []
    for (bloc, green), grp in sub.groupby(["bloc", "green"], observed=True):
        if bloc not in ("AE", "EM", "CHINA"):
            continue
        nd = int((grp["family"] == "non_dilutive").sum())
        rows.append(
            {
                "bloc": bloc,
                "green": bool(green),
                "deals": len(grp),
                "non_dilutive": nd,
                "non_dilutive_pct": round(100 * nd / len(grp), 3),
                "grant": int((grp["instrument"] == "grant").sum()),
                "debt": int((grp["instrument"] == "debt_financing").sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(["bloc", "green"])


def run(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Test H3 and return a JSON-serialisable findings dict."""
    min_n = int(cfg.threshold("min_cell_n"))
    mix_ae = mix_table(deals, cfg, "AE")
    test_ae = chi2_test(deals, cfg, "AE")
    shares = non_dilutive_shares(deals, cfg)
    mix_ae.to_csv(cfg.path("tables") / "h3_instrument_mix_ae.csv", index=False)
    shares.to_csv(cfg.path("tables") / "h3_non_dilutive_by_bloc.csv", index=False)

    ae_g = shares.loc[shares["bloc"].eq("AE") & shares["green"]].iloc[0]
    ae_n = shares.loc[shares["bloc"].eq("AE") & ~shares["green"]].iloc[0]
    em_g = shares.loc[shares["bloc"].eq("EM") & shares["green"]].iloc[0]
    em_n = shares.loc[shares["bloc"].eq("EM") & ~shares["green"]].iloc[0]

    # Grant arm: pre-registered as descriptive only below the minimum cell size.
    grant_cells = {
        f"{r['bloc']}-{'green' if r['green'] else 'non-green'}": int(r["grant"])
        for _, r in shares.iterrows()
    }
    grant_testable = all(v >= min_n for k, v in grant_cells.items() if k.startswith("AE"))
    LOG.info(
        "H3 grant cells %s -> AE grant arm testable = %s (pre-registered rule, n>=%d)",
        grant_cells,
        grant_testable,
        min_n,
    )

    LOG.info(
        "H3 non-dilutive share: AE green %.2f%% (n=%d) vs AE non-green %.2f%% (n=%d); "
        "EM green %.2f%% (n=%d) vs EM non-green %.2f%% (n=%d)",
        ae_g["non_dilutive_pct"],
        ae_g["deals"],
        ae_n["non_dilutive_pct"],
        ae_n["deals"],
        em_g["non_dilutive_pct"],
        em_g["deals"],
        em_n["non_dilutive_pct"],
        em_n["deals"],
    )

    # The chi-squared tests the whole mix; H3 is a claim about the non-dilutive
    # share specifically, so that is tested directly too. Cramer's V on the full
    # table is diluted by the dominant dilutive_venture column and understates
    # the quantity the hypothesis is actually about.
    focused = two_proportion_test(
        int(ae_g["non_dilutive"]),
        int(ae_g["deals"]),
        int(ae_n["non_dilutive"]),
        int(ae_n["deals"]),
    )
    LOG.info(
        "H3 focused test (AE, non-dilutive share): %.2f%% vs %.2f%%, risk ratio %.3f %s, "
        "p=%.3g",
        100 * focused["rate_group1"],
        100 * focused["rate_group2"],
        focused.get("risk_ratio", float("nan")),
        focused.get("risk_ratio_ci"),
        focused["p_value"],
    )
    LOG.info(
        "  NOTE Cramer's V on the full mix is %.4f, below the conventional 0.1 'small' "
        "threshold: with n=%d the chi-squared is significant on a negligible association. "
        "The focused risk ratio is the effect size that matters here.",
        test_ae["cramers_v"],
        test_ae["n"],
    )

    supported = (
        focused["p_value"] < cfg.threshold("alpha")
        and ae_g["non_dilutive_pct"] > ae_n["non_dilutive_pct"]
    )
    # The claim that was tested is the advanced-economy benchmark one. The
    # emerging-market claim was not supported and is not what the verdict covers,
    # so the qualification belongs in the verdict itself.
    verdict = (
        "Supported for the advanced-economy benchmark case" if supported else "Not supported"
    )

    em_arm = {
        "testable": bool(em_g["deals"] >= min_n and em_g["non_dilutive"] >= min_n),
        "em_green_non_dilutive_pct": float(em_g["non_dilutive_pct"]),
        "em_green_deals": int(em_g["deals"]),
        "em_green_non_dilutive_n": int(em_g["non_dilutive"]),
        "ae_green_non_dilutive_pct": float(ae_g["non_dilutive_pct"]),
        "pre_registered_expectation": (
            "This arm was expected to return a null: the green/non-green gap looked "
            "larger than the EM/AE gap before the split was computed."
        ),
        "result": (
            "The emerging-market green non-dilutive share is close to the "
            "advanced-economy green share, so the original H3 claim that emerging-market "
            "green capital is MORE non-dilutive than advanced-economy green capital is "
            "not supported."
        ),
        "bias_caveat": (
            "Stated before the numbers in docs/METHODOLOGY.md §11: equity-coded project "
            "finance understates the non-dilutive share on both sides and more so for "
            "emerging markets, so this null is biased toward the answer it gives and is "
            "not evidence against the underlying hypothesis."
        ),
    }

    findings = {
        "hypothesis": "H3: green capital is less dilutive than non-green",
        "benchmark_bloc": "AE",
        "chi2_ae": test_ae,
        "focused_non_dilutive_test_ae": focused,
        "cramers_v_note": (
            "Cramer's V is reported alongside the risk ratio in the appendix but is not "
            "quoted in the text. On a contingency table with heavily unbalanced marginals "
            "\u2014 here 94.6% of deals sit in one instrument family and 5.4% of companies "
            "are green \u2014 V is bounded well below 1 by the marginals themselves, so it "
            "understates association strength by construction. The risk ratio on the "
            "quantity the hypothesis is about is the interpretable effect size."
        ),
        "effect_size_warning": (
            f"Cramer's V on the full instrument mix is {test_ae['cramers_v']}, below the "
            "conventional 0.1 threshold for a small effect. With n = "
            f"{test_ae['n']:,} the chi-squared detects a negligible association. The "
            "focused comparison of non-dilutive share is the effect size the hypothesis "
            "is about, and it is reported alongside."
        ),
        "non_dilutive_by_bloc": shares.to_dict("records"),
        "grant_arm": {
            "testable": grant_testable,
            "cells": grant_cells,
            "min_cell_n": min_n,
            "decision": (
                "Grants are reported descriptively with exact cell sizes. No significance "
                f"test is run on any grant cell below n = {min_n}. Debt carries the "
                "inferential test. Recorded in docs/METHODOLOGY.md §1.1 before the split "
                "was computed."
            ),
        },
        "em_arm": em_arm,
        "verdict": verdict,
        "verdict_note": (
            f"Within advanced economies green deals are "
            f"{ae_g['non_dilutive_pct']:.2f}% non-dilutive against "
            f"{ae_n['non_dilutive_pct']:.2f}% for non-green, a risk ratio of "
            f"{focused.get('risk_ratio')} {focused.get('risk_ratio_ci')} "
            f"(p = {focused['p_value']:.3g}). The chi-squared on the full mix is also "
            f"significant but its Cramer's V of {test_ae['cramers_v']} is negligible, so "
            "the relative difference in non-dilutive share is the figure to quote."
        ),
        "falsification_condition": (
            "Falsified if green and non-green instrument mixes are statistically "
            "indistinguishable within advanced economies."
        ),
    }
    LOG.info("H3 verdict: %s — %s", verdict, findings["verdict_note"])
    findings["_tables"] = {"h3_instrument_mix_ae": mix_ae, "h3_non_dilutive_by_bloc": shares}
    return findings
