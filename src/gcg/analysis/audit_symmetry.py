"""Measure the differential-audit asymmetry and its direction.

The emerging-market green set (28 companies) was audited exhaustively. The
advanced-economy green set (1,114 companies) was audited only at the top of the
funding distribution. Removing false positives more thoroughly from one bloc
than the other biases the double gap, and the direction is knowable: if the
emerging-market false-positive rate is higher, curation lowers the
emerging-market green rate further and **widens** the gap, which means the raw
headline is the conservative choice.

This module tests whether the two rates actually differ, using a random
advanced-economy sample audited to the same standard. The calls themselves live
in ``config/audit_calls.yaml`` so they are version-controlled and reviewable
rather than embedded here.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from gcg.analysis.h1_selection import two_proportion_test, wilson_interval
from gcg.config import Config, get_logger

LOG = get_logger("analysis.audit")


def run(cfg: Config) -> dict[str, Any]:
    """Compare emerging-market and advanced-economy false-positive rates."""
    spec = cfg.audit_calls["ae_random_audit"]
    census = cfg.audit_calls["em_census"]

    ae_n = int(spec["sample_size"])
    ae_fp = len(spec["false_positive"])
    em_n = int(census["companies"])
    em_fp = int(census["excluded"])

    ae_lo, ae_hi = wilson_interval(ae_fp, ae_n)
    em_lo, em_hi = wilson_interval(em_fp, em_n)
    test = two_proportion_test(em_fp, em_n, ae_fp, ae_n)

    em_rate, ae_rate = em_fp / em_n, ae_fp / ae_n
    differs = test["p_value"] < cfg.threshold("alpha")

    findings: dict[str, Any] = {
        "em": {
            "companies": em_n,
            "false_positives": em_fp,
            "rate_pct": round(100 * em_rate, 2),
            "ci_pct": [round(100 * em_lo, 2), round(100 * em_hi, 2)],
            "audit_coverage": "census (all 28 companies)",
        },
        "ae": {
            "companies_sampled": ae_n,
            "companies_total": int(spec["drawn_from"]),
            "false_positives": ae_fp,
            "rate_pct": round(100 * ae_rate, 2),
            "ci_pct": [round(100 * ae_lo, 2), round(100 * ae_hi, 2)],
            "unverified_kept": len(spec["unverified_kept"]),
            "audit_coverage": (
                f"random sample of {ae_n}, seed {spec['seed']}, not funding-ranked"
            ),
        },
        "test": test,
        "rates_differ_at_alpha": bool(differs),
        "em_rate_higher": bool(em_rate > ae_rate),
        "bias_direction": (
            "Curation removes proportionally more emerging-market companies, so the "
            "curated specification WIDENS the gap and the raw headline is conservative."
            if em_rate > ae_rate
            else "Curation removes proportionally more advanced-economy companies, so the "
            "curated specification NARROWS the gap and the raw headline is anti-conservative."
        ),
        "interpretation": (
            "The two false-positive rates are not distinguishable at this sample size, "
            "so the differential-audit concern is real in principle but not detectably "
            "biasing the result."
            if not differs
            else "The two false-positive rates differ, so the curated specification must "
            "be read as the primary robustness check on the headline."
        ),
    }

    table = pd.DataFrame(
        [
            {
                "bloc": "EM",
                "audited": em_n,
                "false_positives": em_fp,
                "fp_rate_pct": round(100 * em_rate, 2),
                "ci_lo_pct": round(100 * em_lo, 2),
                "ci_hi_pct": round(100 * em_hi, 2),
                "coverage": findings["em"]["audit_coverage"],
            },
            {
                "bloc": "AE",
                "audited": ae_n,
                "false_positives": ae_fp,
                "fp_rate_pct": round(100 * ae_rate, 2),
                "ci_lo_pct": round(100 * ae_lo, 2),
                "ci_hi_pct": round(100 * ae_hi, 2),
                "coverage": findings["ae"]["audit_coverage"],
            },
        ]
    )
    path = cfg.path("tables") / "appendix_audit_symmetry.csv"
    table.to_csv(path, index=False)
    LOG.info("wrote %s", path.name)

    LOG.info(
        "audit symmetry: EM false-positive rate %.1f%% [%.1f-%.1f] (census of %d) vs "
        "AE %.1f%% [%.1f-%.1f] (random %d of %d)",
        100 * em_rate,
        100 * em_lo,
        100 * em_hi,
        em_n,
        100 * ae_rate,
        100 * ae_lo,
        100 * ae_hi,
        ae_n,
        spec["drawn_from"],
    )
    LOG.info(
        "  two-proportion test p=%.3f -> rates differ = %s; EM higher = %s",
        test["p_value"],
        differs,
        findings["em_rate_higher"],
    )
    LOG.info("  %s", findings["bias_direction"])
    return findings
