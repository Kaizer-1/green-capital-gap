"""Assemble ``outputs/findings.json``: every number the report is allowed to use.

CLAUDE.md §2.2: no number is ever typed by hand into the report. Every statistic
in ``report.md`` is written as a ``{{placeholder}}`` and resolved from this file,
and ``render.py`` fails loudly on any placeholder that does not resolve.

This module flattens the per-stage findings into a flat, dotted key space so a
placeholder reads as what it is: ``{{h1.rr}}`` rather than an index into nested
JSON. Values are pre-formatted for prose — percentages carry their sign
convention, intervals are rendered as ``[a, b]`` — because formatting a number
in the report template would be another way of typing it by hand.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from typing import Any

from gcg.config import Config, get_logger, load_config

LOG = get_logger("report.findings")


def _fmt(value: float | None, places: int = 2, suffix: str = "") -> str:
    """Format a number for prose, or an em dash when it is absent."""
    if value is None or (isinstance(value, float) and value != value):
        return "—"
    return f"{value:,.{places}f}{suffix}"


def _ci(pair: list[float] | None, places: int = 2, suffix: str = "") -> str:
    """Render a confidence interval as prose."""
    if not pair or any(v is None for v in pair):
        return "—"
    return f"[{pair[0]:,.{places}f}{suffix}, {pair[1]:,.{places}f}{suffix}]"


def _p(value: float | None) -> str:
    """Format a p-value the way a reader expects to see it."""
    if value is None:
        return "—"
    if value < 1e-4:
        return f"{value:.1e}"
    if value < 0.001:
        return "< 0.001"
    return f"{value:.3f}"


def _git_hash(cfg: Config) -> str:
    """Current commit hash, or a marker when the tree is not a repository."""
    try:
        out = subprocess.run(  # noqa: S603
            ["git", "-C", str(cfg.root), "rev-parse", "--short", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return out.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def _dirty(cfg: Config) -> bool:
    """Whether the working tree has uncommitted changes."""
    try:
        out = subprocess.run(  # noqa: S603
            ["git", "-C", str(cfg.root), "status", "--porcelain"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return bool(out.stdout.strip())
    except OSError:
        return False


def build(cfg: Config | None = None) -> dict[str, Any]:
    """Flatten every stage's findings into the dotted key space."""
    cfg = cfg or load_config()
    interim = cfg.path("data_interim")

    def load(name: str) -> dict[str, Any]:
        path = interim / name
        if not path.is_file():
            msg = f"missing {path}. Run the analysis stage first."
            raise FileNotFoundError(msg)
        return json.loads(path.read_text(encoding="utf-8"))

    analysis = load("analysis_findings.json")
    deal_diag = load("deal_table_diagnostics.json")
    pre = load("preanalysis_diagnostics.json")
    classif = load("classification_diagnostics.json")
    desc = analysis["descriptives"]
    robust = analysis["robustness"]

    f: dict[str, Any] = {}

    # -- data and attrition ----------------------------------------------
    att = deal_diag["attrition_summary"]
    f["data.rounds_total"] = f"{pre['amount_sentinels']['rows']:,}"
    f["data.deals_in_window"] = f"{deal_diag['rows']:,}"
    f["data.retention_pct"] = _fmt(att["retention_pct"], 1)
    f["data.rows_dropped"] = f"{att['net_dropped']:,}"
    f["data.window_start"] = cfg.window["start"][:4]
    f["data.window_end"] = cfg.window["end"][:4]
    ingest = load("ingest_diagnostics.json")
    join = ingest["crunchbase"]["join"]
    f["data.join_rate_pct"] = _fmt(100 * join["join_rate_companies"], 1)
    f["data.join_rate_deals_pct"] = _fmt(100 * join["join_rate_deals"], 1)
    f["data.undisclosed_zero_rows"] = f"{pre['amount_sentinels']['zero']:,}"
    f["data.fx_failures"] = f"{pre['fx_failures']['fx_failures']:,}"
    f["data.relational_vintage"] = pre["mirror_vintage"]["relational_max_funded_at"]
    f["data.flat_vintage"] = pre["mirror_vintage"]["flat_max_last_funding_at"]
    f["data.census_gap_companies"] = f"{pre['mirror_vintage']['census_gap_companies']:,}"
    f["data.under_recording_pct"] = _fmt(
        100 * pre["mirror_vintage"]["surplus_unexplained_share_of_deals"], 1
    )

    # -- classifier -------------------------------------------------------
    f["classifier.kappa"] = _fmt(classif["tier_agreement"]["funded_with_taxonomy"]["kappa"], 3)
    f["classifier.green_companies"] = f"{classif['counts']['green_headline']:,}"
    f["classifier.green_deals"] = f"{deal_diag['green_counts']['raw_deals']:,}"
    f["classifier.vetoed"] = f"{classif['counts']['tier_c_vetoed']:,}"

    # -- population by bloc ----------------------------------------------
    for bloc, n in desc["population"]["by_bloc"].items():
        f[f"pop.{bloc.lower()}_deals"] = f"{n:,}"

    # -- H1 ---------------------------------------------------------------
    h1 = analysis["h1"]["gap_2_conditional_green_rate"]
    head = h1["headline"]
    f["h1.em_rate_pct"] = _fmt(100 * head["rate_group1"], 2)
    f["h1.em_ci"] = _ci([100 * v for v in head["rate_group1_ci"]], 2)
    f["h1.ae_rate_pct"] = _fmt(100 * head["rate_group2"], 2)
    f["h1.ae_ci"] = _ci([100 * v for v in head["rate_group2_ci"]], 2)
    f["h1.rr"] = _fmt(head["risk_ratio"], 3)
    f["h1.rr_ci"] = _ci(head["risk_ratio_ci"], 3)
    f["h1.p"] = _p(head["p_value"])
    f["h1.fisher_p"] = _p(head["fisher_p_value"])
    f["h1.difference_pp"] = _fmt(head["difference_pp"], 2)
    f["h1.difference_ci"] = _ci(head["difference_ci_pp"], 2)
    ub = h1["upper_bound_unassigned_as_em"]
    f["h1.ub_em_rate_pct"] = _fmt(100 * ub["rate_group1"], 2)
    f["h1.ub_rr"] = _fmt(ub["risk_ratio"], 3)
    f["h1.ub_p"] = _p(ub["p_value"])
    f["h1.verdict"] = analysis["h1"]["verdict"]
    loo = analysis["h1"]["leave_one_out_em"]
    f["h1.loo_companies"] = str(loo["companies_tested"])
    f["h1.loo_usd_swing"] = (
        f"{loo['green_usd_swing_pct'][0]:.1f}% to {loo['green_usd_swing_pct'][1]:.1f}%"
    )

    # -- H1b --------------------------------------------------------------
    h1b = analysis["h1b"]
    fit, res = h1b["primary_fit"], h1b["cleantech_residual_primary"]
    f["h1b.elasticity"] = _fmt(fit["slope"], 2)
    f["h1b.elasticity_ci"] = _ci(fit["slope_ci"], 2)
    f["h1b.r2"] = _fmt(fit["r_squared"], 2)
    f["h1b.n_sectors"] = str(fit["n_sectors"])
    f["h1b.p"] = _p(fit["slope_p"])
    f["h1b.cleantech_residual"] = _fmt(res["residual_ratio_scale"], 2, "x")
    f["h1b.cleantech_residual_ci"] = _ci(res["residual_ratio_ci"], 2, "x")

    # -- H2 ---------------------------------------------------------------
    h2 = analysis["h2"]
    f["h2.verdict"] = h2["verdict"]
    f["h2.pretrend_coef"] = _fmt(h2["pre_trend"]["differential_trend_per_year"], 3)
    f["h2.pretrend_ci"] = _ci(h2["pre_trend"]["ci"], 3)
    f["h2.pretrend_p"] = _p(h2["pre_trend"]["p_value"])
    for series, v in h2["crisis_drawdown"].items():
        key = series.lower().replace("-", "_")
        f[f"h2.crisis_{key}_pct"] = _fmt(v["contraction_pct"], 1)
    f["h2.em_largest_cell"] = str(h2["em_arm"]["largest_cell"])

    # -- H3 ---------------------------------------------------------------
    h3 = analysis["h3"]
    foc = h3["focused_non_dilutive_test_ae"]
    f["h3.verdict"] = h3["verdict"]
    f["h3.ae_green_nondilutive_pct"] = _fmt(100 * foc["rate_group1"], 2)
    f["h3.ae_nongreen_nondilutive_pct"] = _fmt(100 * foc["rate_group2"], 2)
    f["h3.rr"] = _fmt(foc["risk_ratio"], 3)
    f["h3.rr_ci"] = _ci(foc["risk_ratio_ci"], 3)
    f["h3.p"] = _p(foc["p_value"])
    f["h3.cramers_v"] = _fmt(h3["chi2_ae"]["cramers_v"], 3)
    f["h3.em_green_deals"] = str(h3["em_arm"]["em_green_deals"])

    # -- H4 ---------------------------------------------------------------
    h4 = analysis["h4"]
    seed_a = h4["headline"]["logit_seed_to_a"]
    f["h4.verdict"] = h4["verdict"]
    f["h4.or"] = _fmt(seed_a.get("odds_ratio"), 2)
    f["h4.or_ci"] = _ci(seed_a.get("odds_ratio_ci"), 2)
    f["h4.p"] = _p(seed_a.get("p_value"))
    f["h4.ae_green_entrants"] = str(h4["power"]["ae_green_seed_entrants"])
    f["h4.ae_ab_pool"] = str(h4["power"]["ae_green_a_to_b_pool"])
    f["h4.em_green_entrants"] = str(h4["em_arm"]["cells"]["em_green_entrants"])

    # -- H5 ---------------------------------------------------------------
    h5 = analysis["h5"]
    depth = h5["correlations"]["green_usd_per_capita"]["gdp_per_capita_usd"]
    f["h5.verdict"] = h5["verdict"]
    f["h5.depth_rho"] = _fmt(depth["rho"], 3)
    f["h5.depth_ci"] = _ci(depth["ci"], 3)
    f["h5.depth_n"] = str(depth["n"])
    f["h5.countries_any"] = str(h5["power"]["countries_with_any_green_deal"])
    f["h5.countries_panel"] = str(h5["power"]["countries_in_panel"])
    f["h5.gini"] = _fmt(h5["concentration"]["gini"], 3)
    f["h5.top5_pct"] = _fmt(h5["concentration"]["top5_share_pct"], 1)

    # -- measurement thesis ----------------------------------------------
    f["measure.em_unspecified_pct"] = _fmt(
        100 * desc["subdomain_mix"]["em_unspecified_share"], 1
    )
    f["measure.ae_unspecified_pct"] = _fmt(
        100 * desc["subdomain_mix"]["unspecified_share_by_bloc"]["AE"], 1
    )
    cov = desc["coverage_bias"]
    f["measure.em_gdp_share_range"] = (
        f"{cov['em_gdp_share_pct_range'][0]:.1f}–{cov['em_gdp_share_pct_range'][1]:.1f}%"
    )
    f["measure.em_deal_share_range"] = (
        f"{cov['em_deal_share_pct_range'][0]:.1f}–{cov['em_deal_share_pct_range'][1]:.1f}%"
    )
    f["measure.under_rep_range"] = (
        f"{cov['em_under_representation_factor_range'][0]:.1f}–"
        f"{cov['em_under_representation_factor_range'][1]:.1f}×"
    )

    # -- cheque size ------------------------------------------------------
    ch = analysis["cheque_size"]["formal_test"]
    f["cheque.green_pct"] = _fmt(ch["green_pct_change"], 1)
    f["cheque.nongreen_pct"] = _fmt(ch["non_green_pct_change"], 1)
    f["cheque.difference_pp"] = _fmt(ch["difference_pp"], 1)
    f["cheque.ci"] = _ci(ch["ci_pp"], 1)
    ep = robust["cheque_endpoint_sensitivity"]
    f["cheque.pairs_to_close"] = str(ep["pairs_ending_at_window_close"])
    f["cheque.range_to_close"] = (
        f"{ep['range_ending_at_close_pp'][0]:.1f} to {ep['range_ending_at_close_pp'][1]:.1f}"
    )

    # -- audit and robustness --------------------------------------------
    aud = analysis["audit"]
    f["audit.em_fp_pct"] = _fmt(aud["em"]["rate_pct"], 1)
    f["audit.ae_fp_pct"] = _fmt(aud["ae"]["rate_pct"], 1)
    f["audit.p"] = _p(aud["test"]["p_value"])
    perm = robust["permutation_double_gap"]
    f["robust.perm_observed_rr"] = _fmt(perm["observed_risk_ratio"], 3)
    f["robust.perm_null_ci"] = _ci(perm["null_ci"], 3)
    f["robust.perm_p"] = _fmt(perm["p_permutation"], 3)
    f["robust.perm_draws"] = f"{perm['draws']:,}"
    f["robust.green_def_rr_range"] = (
        f"{min(r['risk_ratio'] for r in robust['green_definitions']):.3f}–"
        f"{max(r['risk_ratio'] for r in robust['green_definitions']):.3f}"
    )
    f["robust.bloc_rr_range"] = (
        f"{min(r['risk_ratio'] for r in robust['bloc_schemes']):.3f}–"
        f"{max(r['risk_ratio'] for r in robust['bloc_schemes']):.3f}"
    )
    fam = analysis["test_family"]
    f["robust.tests_total"] = str(len(fam))
    f["robust.tests_significant"] = str(sum(1 for t in fam if t["significant_after_bh"]))

    # -- continuity -------------------------------------------------------
    cont = analysis["continuity"]
    f["india.deals"] = f"{cont['dated_rows']:,}"
    f["india.green"] = str(cont["green_deals"])
    f["india.rate_pct"] = _fmt(cont["green_rate_pct"], 2)
    lfl = cont["like_for_like"]
    f["india.vs_em_rr"] = _fmt(lfl["india_vs_em_tier_b"]["risk_ratio"], 3)
    f["india.vs_em_p"] = _p(lfl["india_vs_em_tier_b"]["p_value"])

    # -- reproducibility --------------------------------------------------
    f["repro.commit"] = _git_hash(cfg)
    f["repro.dirty"] = "yes" if _dirty(cfg) else "no"
    f["repro.python"] = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    f["repro.generated"] = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    f["repro.seed"] = str(cfg.seed)
    f["repro.bootstrap_draws"] = f"{cfg.pipeline['bootstrap_resamples']:,}"

    out = cfg.path("findings")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(sorted(f.items())), indent=2) + "\n", encoding="utf-8")
    LOG.info("wrote %s with %d resolvable placeholders", out.name, len(f))
    return f


if __name__ == "__main__":
    build()
