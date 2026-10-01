"""Analysis stage entry point: runs H1-H5 and assembles the test family.

CLAUDE.md §9 requires a Benjamini-Hochberg correction across the full family of
tests, with raw and adjusted p-values reported side by side. Collecting the
family here, rather than inside each hypothesis module, is what makes that
possible: no module can see the others' tests.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
from statsmodels.stats.multitest import multipletests

from gcg.analysis import (
    audit_symmetry,
    cheque_size,
    continuity,
    descriptives,
    h1_selection,
    h1b_capital_intensity,
    h2_cycle,
    h3_instrument,
    h4_graduation,
    h5_allocation,
    robustness,
)
from gcg.config import Config, get_logger, load_config, seed_everything
from gcg.io import read_parquet

LOG = get_logger("analysis.run")


def _collect_tests(findings: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull every reported p-value into one family for correction."""
    fam: list[dict[str, Any]] = []

    def add(hypothesis: str, test: str, p: float | None, effect: str = "") -> None:
        if p is not None and pd.notna(p):
            fam.append(
                {"hypothesis": hypothesis, "test": test, "p_raw": float(p), "effect": effect}
            )

    h1 = findings["h1"]["gap_2_conditional_green_rate"]
    add(
        "H1",
        "EM vs AE green rate, two-proportion z",
        h1["headline"]["p_value"],
        f"RR {h1['headline'].get('risk_ratio')}",
    )
    add(
        "H1",
        "EM vs AE green rate, Fisher exact",
        h1["headline"]["fisher_p_value"],
        f"RR {h1['headline'].get('risk_ratio')}",
    )
    add(
        "H1",
        "upper bound, unassigned as EM",
        h1["upper_bound_unassigned_as_em"]["p_value"],
        f"RR {h1['upper_bound_unassigned_as_em'].get('risk_ratio')}",
    )

    h1b = findings["h1b"]
    add(
        "H1b",
        "capital-intensity elasticity",
        h1b["primary_fit"]["slope_p"],
        f"slope {h1b['primary_fit']['slope']}",
    )

    h2 = findings["h2"]
    add(
        "H2",
        "pre-trend differential",
        h2["pre_trend"]["p_value"],
        f"trend {h2['pre_trend']['differential_trend_per_year']}/yr",
    )
    add(
        "H2", "DiD green x post", h2["did"]["p_value"], f"coef {h2['did']['interaction_coef']}"
    )

    h3 = findings["h3"]
    add(
        "H3",
        "instrument mix chi-squared (AE)",
        h3["chi2_ae"]["p_value"],
        f"Cramer's V {h3['chi2_ae']['cramers_v']}",
    )
    add(
        "H3",
        "non-dilutive share, green vs non-green (AE)",
        h3["focused_non_dilutive_test_ae"]["p_value"],
        f"RR {h3['focused_non_dilutive_test_ae'].get('risk_ratio')}",
    )

    for key, label in (("logit_seed_to_a", "seed to A"), ("logit_a_to_b", "A to B")):
        m = findings["h4"]["headline"][key]
        if m.get("testable"):
            add("H4", f"graduation logit, {label}", m["p_value"], f"OR {m['odds_ratio']}")

    h5 = findings["h5"]
    for outcome, block in h5["correlations"].items():
        for var, r in block.items():
            if r.get("p_value") is not None:
                add("H5", f"Spearman {outcome} vs {var}", r["p_value"], f"rho {r['rho']}")
    for var, m in h5["ols_need_after_income"].items():
        add("H5", f"OLS need after income: {var}", m["p_value"], f"coef {m['coef']}")

    add(
        "Audit",
        "EM vs AE false-positive rate",
        findings["audit"]["test"]["p_value"],
        f"RR {findings['audit']['test'].get('risk_ratio')}",
    )
    return fam


def benjamini_hochberg(family: list[dict[str, Any]], cfg: Config) -> pd.DataFrame:
    """Apply BH across the family and return the appendix table."""
    df = pd.DataFrame(family)
    reject, adj, _, _ = multipletests(
        df["p_raw"].to_numpy(),
        alpha=cfg.threshold("alpha"),
        method=cfg.threshold("fdr_method"),
    )
    df["p_adjusted"] = adj
    df["significant_after_bh"] = reject
    df = df.sort_values("p_raw").reset_index(drop=True)
    LOG.info(
        "test family: %d tests, %d significant at alpha=%.2f after %s correction",
        len(df),
        int(df["significant_after_bh"].sum()),
        cfg.threshold("alpha"),
        cfg.threshold("fdr_method"),
    )
    flipped = df.loc[(df["p_raw"] < cfg.threshold("alpha")) & (~df["significant_after_bh"])]
    if len(flipped):
        LOG.warning(
            "  %d tests lose significance under correction: %s",
            len(flipped),
            flipped["test"].tolist(),
        )
    return df


def main() -> int:
    """Run every analysis module and write the combined findings."""
    cfg = load_config()
    cfg.ensure_dirs()
    rng = seed_everything(cfg)
    deals = read_parquet(cfg.path("data_processed") / "deals.parquet")
    LOG.info("analysis stage: %d deals, %d green", len(deals), int(deals["green"].sum()))

    findings: dict[str, Any] = {}
    for name, fn in (
        ("descriptives", lambda: descriptives.run(cfg)),
        ("cheque_size", lambda: cheque_size.run(cfg)),
        ("audit", lambda: audit_symmetry.run(cfg)),
        ("continuity", lambda: continuity.run(cfg)),
        ("h1", lambda: h1_selection.run(deals, cfg)),
        ("h1b", lambda: h1b_capital_intensity.run(deals, cfg)),
        ("h2", lambda: h2_cycle.run(deals, cfg)),
        ("h3", lambda: h3_instrument.run(deals, cfg)),
        ("h4", lambda: h4_graduation.run(deals, cfg)),
        ("h5", lambda: h5_allocation.run(deals, cfg, rng)),
        ("robustness", lambda: robustness.run(cfg)),
    ):
        LOG.info("=" * 78)
        LOG.info("running %s", name)
        result = fn()
        for key, frame in (result.pop("_tables", {}) or {}).items():
            frame.to_csv(cfg.path("tables") / f"{key}.csv")
        findings[name] = result

    family = benjamini_hochberg(_collect_tests(findings), cfg)
    family.to_csv(cfg.path("tables") / "appendix_d_test_family.csv", index=False)
    findings["test_family"] = family.to_dict("records")

    path = cfg.path("data_interim") / "analysis_findings.json"
    path.write_text(json.dumps(findings, indent=2, default=str) + "\n", encoding="utf-8")
    LOG.info("wrote %s", path.name)

    LOG.info("=" * 78)
    LOG.info("VERDICTS")
    for key in ("h1", "h2", "h3", "h4", "h5"):
        LOG.info(
            "  %-4s %-20s %s",
            key.upper(),
            findings[key]["verdict"],
            findings[key].get("verdict_note", "")[:110],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
