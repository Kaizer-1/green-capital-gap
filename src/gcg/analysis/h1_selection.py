"""H1-revised: selection and visibility — the double gap.

The original H1 (emerging-market deal share rose faster than dollar share) is
not testable: the emerging-market green sample is 35 deals across thirteen
years, and no widening of the green definition changes that. H1 is therefore
replaced by the claim the data *can* carry, which is a stronger claim about the
field:

    Emerging-market green ventures face a **double gap**. First, emerging
    markets are under-represented in the venture record relative to their
    economic weight. Second, and separately, *conditional on already being in
    the record*, an emerging-market company is markedly less likely to be green
    than an advanced-economy one.

The second gap is the headline. It is measured within the dataset, so it does
not depend on the coverage of the dataset: both numerator and denominator are
drawn from companies Crunchbase chose to index. The GDP coverage comparison is
demoted to a denominator check whose only job is to show that the second gap is
not the first restated.

The green rate is a proportion of deals, tested with a two-proportion z-test,
Wilson score intervals on each rate, and Fisher's exact test as a small-sample
check. Effect size is reported as a risk ratio with a confidence interval, since
with 35 events a bare p-value says almost nothing worth knowing.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from gcg.config import Config, get_logger

LOG = get_logger("analysis.h1")

_Z = 1.959963984540054  # two-sided 95%
_MIN_CELL = 30


def wilson_interval(successes: int, total: int, z: float = _Z) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Preferred over the normal approximation here because the emerging-market
    green rate is a small proportion on a modest denominator, where the Wald
    interval misbehaves and can run below zero.
    """
    if total == 0:
        return (float("nan"), float("nan"))
    p = successes / total
    denom = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denom
    half = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def two_proportion_test(s1: int, n1: int, s2: int, n2: int) -> dict[str, Any]:
    """Compare two proportions: z-test, risk ratio, odds ratio, Fisher's exact.

    Parameters
    ----------
    s1, n1
        Successes and total for group 1 (emerging markets).
    s2, n2
        Successes and total for group 2 (advanced economies).

    Returns
    -------
    dict
        Rates with Wilson intervals, the z statistic and p-value, the risk ratio
        and odds ratio with log-method confidence intervals, Cohen's h, and
        Fisher's exact p-value.
    """
    if min(n1, n2) == 0:
        return {"error": "empty group"}

    p1, p2 = s1 / n1, s2 / n2
    pooled = (s1 + s2) / (n1 + n2)
    se_pooled = np.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se_pooled if se_pooled > 0 else float("nan")
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    # CI on the difference uses unpooled SEs.
    se_diff = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    diff_lo, diff_hi = (p1 - p2) - _Z * se_diff, (p1 - p2) + _Z * se_diff

    out: dict[str, Any] = {
        "n_group1": n1,
        "successes_group1": s1,
        "rate_group1": round(p1, 6),
        "rate_group1_ci": [round(v, 6) for v in wilson_interval(s1, n1)],
        "n_group2": n2,
        "successes_group2": s2,
        "rate_group2": round(p2, 6),
        "rate_group2_ci": [round(v, 6) for v in wilson_interval(s2, n2)],
        "difference_pp": round(100 * (p1 - p2), 4),
        "difference_ci_pp": [round(100 * diff_lo, 4), round(100 * diff_hi, 4)],
        "z": round(float(z), 4),
        "p_value": float(p_value),
    }

    # Risk ratio with a log-scale interval.
    if s1 > 0 and s2 > 0:
        rr = p1 / p2
        se_log_rr = np.sqrt(1 / s1 - 1 / n1 + 1 / s2 - 1 / n2)
        out["risk_ratio"] = round(float(rr), 4)
        out["risk_ratio_ci"] = [
            round(float(np.exp(np.log(rr) - _Z * se_log_rr)), 4),
            round(float(np.exp(np.log(rr) + _Z * se_log_rr)), 4),
        ]
        out["inverse_risk_ratio"] = round(float(1 / rr), 4)

        f1, f2 = n1 - s1, n2 - s2
        odds = (s1 / f1) / (s2 / f2)
        se_log_or = np.sqrt(1 / s1 + 1 / f1 + 1 / s2 + 1 / f2)
        out["odds_ratio"] = round(float(odds), 4)
        out["odds_ratio_ci"] = [
            round(float(np.exp(np.log(odds) - _Z * se_log_or)), 4),
            round(float(np.exp(np.log(odds) + _Z * se_log_or)), 4),
        ]

    # Cohen's h: effect size for a difference of proportions.
    out["cohens_h"] = round(float(2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))), 4)

    table = [[s1, n1 - s1], [s2, n2 - s2]]
    out["fisher_p_value"] = float(stats.fisher_exact(table)[1])
    return out


def green_rate_by_bloc(deals: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Green rate conditional on dataset membership, by bloc.

    This is the exhibit that replaces the cut sub-domain-mix figure.
    """
    rows = []
    for bloc, grp in deals.groupby("bloc", observed=True):
        green = int(grp["green"].sum())
        total = int(len(grp))
        lo, hi = wilson_interval(green, total)
        rows.append(
            {
                "bloc": bloc,
                "deals": total,
                "green_deals": green,
                # Full precision retained: rounding is a display concern and
                # a value rounded here would be rounded again downstream.
                "green_rate_pct": 100 * green / total if total else 0.0,
                "ci_lo_pct": 100 * lo,
                "ci_hi_pct": 100 * hi,
                "below_min_cell": bool(green < _MIN_CELL),
            }
        )
    order = {b: i for i, b in enumerate(cfg.blocs["display"]["order"])}
    return pd.DataFrame(rows).sort_values(
        "bloc", key=lambda s: s.map(lambda b: order.get(b, 99))
    )


def green_rate_by_year(deals: pd.DataFrame) -> pd.DataFrame:
    """Green rate by bloc and year, with cell sizes and a suppression flag.

    No significance test is attached to a cell below the minimum size. With the
    emerging-market green count in single digits in every year, that means no
    per-year test is reported at all, and the table says so rather than quietly
    omitting it.
    """
    rows = []
    for (year, bloc), grp in deals.groupby(["year", "bloc"], observed=True):
        green = int(grp["green"].sum())
        total = int(len(grp))
        lo, hi = wilson_interval(green, total)
        rows.append(
            {
                "year": int(year),
                "bloc": bloc,
                "deals": total,
                "green_deals": green,
                "green_rate_pct": 100 * green / total if total else 0.0,
                "ci_lo_pct": 100 * lo,
                "ci_hi_pct": 100 * hi,
                "test_permitted": bool(green >= _MIN_CELL),
            }
        )
    return pd.DataFrame(rows).sort_values(["bloc", "year"])


def leave_one_out(deals: pd.DataFrame, cfg: Config, bloc: str = "EM") -> pd.DataFrame:
    """Leave-one-out sensitivity on a bloc's headline green numbers.

    With 35 green deals a single curation call moves a reported figure by
    several percent. The honest response is to publish the whole swing rather
    than defend a point estimate, so this drops each green COMPANY in turn (not
    each deal, because an exclusion decision removes a company and all its
    rounds) and recomputes.
    """
    amount = cfg.pipeline["deflate"]["real_column"]
    sub = deals.loc[deals["bloc"].eq(bloc)]
    green = sub.loc[sub["green"]]
    companies = green["object_id"].dropna().unique()

    base_rate = 100 * len(green) / len(sub) if len(sub) else 0.0
    base_usd = float(green[amount].sum())

    rows = []
    for obj in companies:
        keep = sub.loc[sub["object_id"].ne(obj)]
        kept_green = keep.loc[keep["green"]]
        rate = 100 * len(kept_green) / len(keep) if len(keep) else 0.0
        usd = float(kept_green[amount].sum())
        dropped = green.loc[green["object_id"].eq(obj)]
        rows.append(
            {
                "excluded_object_id": obj,
                "excluded_name": dropped["name"].iloc[0] if "name" in dropped else "",
                "excluded_country": dropped["country_code"].iloc[0],
                "excluded_deals": len(dropped),
                "excluded_usd_real2015": float(dropped[amount].sum()),
                "green_rate_pct": round(rate, 4),
                "green_rate_change_pp": round(rate - base_rate, 4),
                "green_usd_real2015": usd,
                "green_usd_change_pct": round(100 * (usd - base_usd) / base_usd, 3)
                if base_usd
                else 0.0,
            }
        )
    out = pd.DataFrame(rows).sort_values("green_usd_change_pct")
    out.attrs["base_rate_pct"] = round(base_rate, 4)
    out.attrs["base_usd_nominal"] = base_usd
    return out


def bias_corrected_gap(
    deals: pd.DataFrame, cfg: Config, rng: np.random.Generator
) -> dict[str, Any]:
    """Third specification: correct both blocs by their measured false-positive rates.

    Raw applies no curation. Partial curation applies the manual exclusions,
    which were produced by an asymmetric audit (a census of 28 emerging-market
    companies against a sample of advanced-economy ones) and therefore removes
    proportionally more from the bloc that was looked at harder.

    This specification instead applies each bloc's *measured* false-positive
    rate to its *whole* green population, so both blocs are corrected on the
    same basis. Uncertainty from the audit is propagated: the false-positive
    rates are drawn from Jeffreys Beta posteriors reflecting how few companies
    were actually audited, and binomial sampling of the green counts is layered
    on top. Both sources of error therefore appear in the interval.

    The expected result is a risk ratio between the raw and partially-curated
    ones, which would confirm that partial curation inflates the gap.
    """
    spec = cfg.audit_calls["ae_random_audit"]
    census = cfg.audit_calls["em_census"]
    draws = int(cfg.pipeline["capital_intensity"]["bias_correction_draws"])

    em, ae = deals.loc[deals["bloc"].eq("EM")], deals.loc[deals["bloc"].eq("AE")]
    em_n, ae_n = len(em), len(ae)
    em_g, ae_g = int(em["green"].sum()), int(ae["green"].sum())

    # Jeffreys posteriors on the two false-positive rates.
    em_k, em_audited = int(census["excluded"]), int(census["companies"])
    ae_k, ae_audited = len(spec["false_positive"]), int(spec["sample_size"])
    fp_em = rng.beta(em_k + 0.5, em_audited - em_k + 0.5, size=draws)
    fp_ae = rng.beta(ae_k + 0.5, ae_audited - ae_k + 0.5, size=draws)

    p_em = np.clip(em_g * (1 - fp_em) / em_n, 1e-12, 1)
    p_ae = np.clip(ae_g * (1 - fp_ae) / ae_n, 1e-12, 1)
    s_em = rng.binomial(em_n, p_em)
    s_ae = rng.binomial(ae_n, p_ae)

    rate_em, rate_ae = s_em / em_n, s_ae / ae_n
    with np.errstate(divide="ignore", invalid="ignore"):
        rr = np.where(rate_ae > 0, rate_em / rate_ae, np.nan)
    rr = rr[np.isfinite(rr)]

    out = {
        "em_green_raw": em_g,
        "ae_green_raw": ae_g,
        "fp_rate_em_mean": round(float(fp_em.mean()), 4),
        "fp_rate_ae_mean": round(float(fp_ae.mean()), 4),
        "em_green_corrected_expected": round(float((em_g * (1 - fp_em)).mean()), 2),
        "ae_green_corrected_expected": round(float((ae_g * (1 - fp_ae)).mean()), 2),
        "em_rate_pct": round(100 * float(rate_em.mean()), 4),
        "em_rate_ci_pct": [
            round(100 * float(np.percentile(rate_em, 2.5)), 4),
            round(100 * float(np.percentile(rate_em, 97.5)), 4),
        ],
        "ae_rate_pct": round(100 * float(rate_ae.mean()), 4),
        "ae_rate_ci_pct": [
            round(100 * float(np.percentile(rate_ae, 2.5)), 4),
            round(100 * float(np.percentile(rate_ae, 97.5)), 4),
        ],
        "risk_ratio": round(float(np.median(rr)), 4),
        "risk_ratio_ci": [
            round(float(np.percentile(rr, 2.5)), 4),
            round(float(np.percentile(rr, 97.5)), 4),
        ],
        "prob_rr_below_1": round(float((rr < 1).mean()), 5),
        "draws": int(len(rr)),
        "note": (
            "Company-level false-positive rates applied to deal counts. This assumes "
            "false-positive companies carry an average number of deals; in the "
            "emerging-market census they carried exactly one each, so the assumption "
            "holds there and is an approximation for advanced economies."
        ),
    }
    LOG.info(
        "bias-corrected gap: EM %.3f%% [%.3f-%.3f] vs AE %.3f%% [%.3f-%.3f]; "
        "RR %.4f [%.4f, %.4f]; P(RR<1)=%.4f",
        out["em_rate_pct"],
        *out["em_rate_ci_pct"],
        out["ae_rate_pct"],
        *out["ae_rate_ci_pct"],
        out["risk_ratio"],
        *out["risk_ratio_ci"],
        out["prob_rr_below_1"],
    )
    return out


def run(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Test H1-revised and return a JSON-serialisable findings dict."""
    by_bloc = green_rate_by_bloc(deals, cfg)
    by_year = green_rate_by_year(deals)

    em = deals.loc[deals["bloc"].eq("EM")]
    ae = deals.loc[deals["bloc"].eq("AE")]
    headline = two_proportion_test(
        int(em["green"].sum()), len(em), int(ae["green"].sum()), len(ae)
    )

    # Upper bound: every still-unattributable deal counted as emerging-market.
    # Maximally generous to the null, so if the gap survives this it is not an
    # artefact of the unresolved country codes.
    ub = deals.copy()
    ub["bloc_ub"] = ub["bloc"].replace({"UNASSIGNED": "EM"})
    em_ub = ub.loc[ub["bloc_ub"].eq("EM")]
    upper_bound = two_proportion_test(
        int(em_ub["green"].sum()), len(em_ub), int(ae["green"].sum()), len(ae)
    )

    loo = leave_one_out(deals, cfg, "EM")

    findings: dict[str, Any] = {
        "hypothesis": "H1-revised: selection and visibility (the double gap)",
        "gap_2_conditional_green_rate": {
            "headline": headline,
            "upper_bound_unassigned_as_em": upper_bound,
            "by_bloc": by_bloc.to_dict("records"),
            "by_year_no_test_permitted": by_year.to_dict("records"),
            "per_year_tests_permitted": int(by_year["test_permitted"].sum()),
            "min_cell_size": _MIN_CELL,
        },
        "leave_one_out_em": {
            "base_green_rate_pct": loo.attrs["base_rate_pct"],
            "base_green_usd_real2015": loo.attrs["base_usd_nominal"],
            "companies_tested": int(len(loo)),
            "green_rate_swing_pp": [
                round(float(loo["green_rate_change_pp"].min()), 4),
                round(float(loo["green_rate_change_pp"].max()), 4),
            ],
            "green_usd_swing_pct": [
                round(float(loo["green_usd_change_pct"].min()), 3),
                round(float(loo["green_usd_change_pct"].max()), 3),
            ],
            "largest_single_influence": loo.iloc[0].to_dict() if len(loo) else {},
        },
    }

    verdict = (
        "Supported"
        if headline["p_value"] < cfg.threshold("alpha")
        and upper_bound["p_value"] < cfg.threshold("alpha")
        else "Not supported"
    )
    findings["verdict"] = verdict
    findings["falsification_condition"] = (
        "Falsified if the emerging-market green rate is indistinguishable from the "
        "advanced-economy rate, or if the gap disappears when every unattributable "
        "deal is counted as emerging-market."
    )

    LOG.info(
        "H1-revised gap 2: EM green rate %.2f%% [%.2f-%.2f] vs AE %.2f%% [%.2f-%.2f]; "
        "RR %.3f [%.3f-%.3f]; z=%.3f p=%.3g; Fisher p=%.3g",
        100 * headline["rate_group1"],
        100 * headline["rate_group1_ci"][0],
        100 * headline["rate_group1_ci"][1],
        100 * headline["rate_group2"],
        100 * headline["rate_group2_ci"][0],
        100 * headline["rate_group2_ci"][1],
        headline.get("risk_ratio", float("nan")),
        headline.get("risk_ratio_ci", [float("nan")] * 2)[0],
        headline.get("risk_ratio_ci", [float("nan")] * 2)[1],
        headline["z"],
        headline["p_value"],
        headline["fisher_p_value"],
    )
    LOG.info(
        "H1-revised upper bound (unassigned as EM): EM %.2f%% vs AE %.2f%%; "
        "RR %.3f; p=%.3g -> gap survives = %s",
        100 * upper_bound["rate_group1"],
        100 * upper_bound["rate_group2"],
        upper_bound.get("risk_ratio", float("nan")),
        upper_bound["p_value"],
        upper_bound["p_value"] < cfg.threshold("alpha"),
    )
    LOG.info(
        "H1-revised leave-one-out (EM, %d companies): green rate swings %+.3f to %+.3f pp; "
        "green dollars swing %+.1f%% to %+.1f%%",
        findings["leave_one_out_em"]["companies_tested"],
        *findings["leave_one_out_em"]["green_rate_swing_pp"],
        *findings["leave_one_out_em"]["green_usd_swing_pct"],
    )
    LOG.info("H1-revised verdict: %s", verdict)

    findings["_tables"] = {
        "h1_green_rate_by_bloc": by_bloc,
        "h1_green_rate_by_bloc_year": by_year,
        "appendix_h1_em_leave_one_out": loo,
    }
    return findings
