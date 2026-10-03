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

import pandas as pd

from gcg.config import Config, get_logger, load_config
from gcg.rounding import fmt as _r_fmt
from gcg.rounding import fmt_ci as _r_ci
from gcg.rounding import fmt_p as _r_p

LOG = get_logger("report.findings")


def _fmt(value: float | None, places: int = 2, suffix: str = "") -> str:
    """Format a number for prose through the project's single rounding rule."""
    return _r_fmt(value, places, suffix=suffix)


def _ci(pair: list[float] | None, places: int = 2, suffix: str = "") -> str:
    """Render a confidence interval through the same rule."""
    return _r_ci(pair, places, suffix=suffix)


def _p(value: float | None) -> str:
    """Format a p-value."""
    return _r_p(value)


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

    seas = pre["censoring_seasonality"]
    disc = pre["censoring_disclosure"]
    f["censor.dec_2013_pct"] = _fmt(seas["december_2013_pct"], 1)
    f["censor.dec_baseline_pct"] = _fmt(seas["december_baseline_2011_2012_pct"], 1)
    f["censor.disclosed_by_year"] = " / ".join(
        _fmt(v, 2) for _, v in sorted(disc["disclosed_pct_by_year"].items())
    )
    f["censor.nov_counts"] = " / ".join(
        f"{v:,}" for _, v in sorted(seas["november_counts"].items())
    )

    # The instrument-field disagreements that justify normalising from
    # funding_round_code. Keyed by the pair, so Appendix G quotes them rather
    # than restating them.
    inst = pre["instrument_contingency"]
    by_pair = {
        (r["code_canonical"], r["type_canonical"]): r["deals"] for r in inst["top_conflicts"]
    }
    f["instrument.conflict_deals"] = f"{inst['conflict_rows']:,}"
    f["instrument.conflict_pct"] = _fmt(100 * inst["conflict_share"], 1)
    f["instrument.seed_as_angel"] = f"{by_pair[('seed', 'angel')]:,}"
    f["instrument.debt_as_other"] = f"{by_pair[('debt_financing', 'other')]:,}"
    f["instrument.grant_as_other"] = f"{by_pair[('grant', 'other')]:,}"

    # -- classifier -------------------------------------------------------
    f["classifier.kappa"] = _fmt(classif["tier_agreement"]["funded_with_taxonomy"]["kappa"], 3)
    f["classifier.green_companies"] = f"{classif['counts']['green_headline']:,}"
    f["classifier.green_deals"] = f"{deal_diag['green_counts']['raw_deals']:,}"
    f["classifier.vetoed"] = f"{classif['counts']['tier_c_vetoed']:,}"
    lex = cfg.lexicon
    n_patterns = sum(len(b["patterns"]) for b in lex["subdomains"].values())
    n_patterns += len(lex["general_unspecified"]["patterns"])
    n_patterns += sum(len(b["patterns"]) for b in lex.get("gated_patterns", {}).values())
    f["classifier.patterns"] = str(n_patterns)
    f["classifier.exclusions"] = str(len(lex["exclusions"]))
    f["classifier.subdomains"] = str(len(lex["subdomains"]))
    f["classifier.green_with_amount"] = f"{desc['population']['green_with_amount']:,}"
    # Country recovery is carried at BOTH scopes, with the scope in the key name.
    # The company-level figures were previously exposed as `blank_country_deals`
    # and `country_recovered`, and the report read them as deal counts — which is
    # impossible, since the source holds fewer rounds than the blank count.
    crc = classif["country_recovery"]
    f["data.companies_total"] = f"{crc['companies']:,}"
    f["data.blank_country_companies"] = f"{crc['blank_before']:,}"
    f["data.country_recovered_companies"] = f"{crc['recovered_total']:,}"
    f["data.country_recovery_rate_pct"] = _fmt(100 * crc["recovery_rate"], 1)
    crd = deal_diag["country_recovery_deals"]
    f["data.country_recovered_deals"] = f"{crd['recovered']:,}"
    f["data.unassigned_no_country"] = f"{crd['unassigned_no_country']:,}"
    f["data.unassigned_unmappable"] = str(crd["unassigned_unmappable_code"])
    # The vanity-TLD refusals. The counts matter to the argument: a naive ccTLD
    # mapping would have manufactured ventures in exactly the countries this
    # paper reports as absent, so the figures are counted, not described.
    rec = cfg.blocs["country_recovery"]
    f["data.tld_accepted"] = str(len(rec["cctld_to_iso3"]))
    f["data.tld_refused"] = str(len(rec["cctld_refused"]))
    avoided = classif["country_recovery"]["fabrication_avoided"]
    f["data.fabrication_avoided"] = f"{sum(avoided.values()):,}"
    f["data.tld_tv"] = f"{avoided.get('tv', 0):,}"
    f["data.tld_st"] = f"{avoided.get('st', 0):,}"

    # -- population by bloc ----------------------------------------------
    for bloc, n in desc["population"]["by_bloc"].items():
        f[f"pop.{bloc.lower()}_deals"] = f"{n:,}"
    # Green count per bloc, including the unassigned row. Figure 1 and its data
    # table print all five; only four had keys, so the unassigned bloc's 64 was
    # a number on the page that nothing could check.
    for row in analysis["h1"]["gap_2_conditional_green_rate"]["by_bloc"]:
        bloc = str(row["bloc"]).lower()
        f[f"pop.{bloc}_green"] = f"{int(row['green_deals']):,}"
        # The rate every bloc row prints. Only AE and EM had keys; the figure
        # drew five.
        f[f"h1.{bloc}_rate_pct"] = _fmt(row["green_rate_pct"], 2)
        f[f"h1.{bloc}_ci"] = _ci([row["ci_lo_pct"], row["ci_hi_pct"]], 2)

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

    cn = h1["china_vs_ae"]
    f["china.rate_pct"] = _fmt(100 * cn["rate_group1"], 2)
    f["china.rr"] = _fmt(cn["risk_ratio"], 2)
    f["china.rr_ci"] = _ci(cn["risk_ratio_ci"], 2)
    f["china.p"] = _p(cn["p_value"])

    # The third specification: both blocs corrected by their own measured
    # false-positive rate, so neither is penalised for having been audited harder.
    bc = h1["bias_corrected"]
    f["h1.bias_em_rate_pct"] = _fmt(bc["em_rate_pct"], 2)
    f["h1.bias_ae_rate_pct"] = _fmt(bc["ae_rate_pct"], 2)
    f["h1.bias_rr"] = _fmt(bc["risk_ratio"], 2)
    f["h1.bias_rr_ci"] = _ci(bc["risk_ratio_ci"], 2)

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
    f["h1b.intercept"] = _fmt(fit["intercept"], 2)
    # How much further below proportionate representation biotech sits than
    # cleantech. The ladder states it; nothing held it.
    ladder = pd.read_csv(cfg.path("tables") / "h1b_sector_capital_intensity.csv", index_col=0)
    f["h1b.biotech_vs_cleantech"] = _fmt(
        float(ladder.loc["cleantech", "representation_ratio"])
        / float(ladder.loc["biotech", "representation_ratio"]),
        1,
        "x",
    )
    sec = h1b["secondary_fit"]
    f["h1b.elasticity2"] = _fmt(sec["slope"], 2)
    f["h1b.r2_secondary"] = _fmt(sec["r_squared"], 2)

    # -- H2 ---------------------------------------------------------------
    h2 = analysis["h2"]
    f["h2.verdict"] = h2["verdict"]
    # The 2008 convergence Figure 3 annotates, and the peak shares Figure 6
    # annotates. Both were drawn from the data and stated on a figure with no
    # key behind them.
    by_year = pd.read_csv(cfg.path("tables") / "h1_green_rate_by_bloc_year.csv")
    for bloc in ("AE", "EM"):
        row = by_year.loc[by_year["bloc"].eq(bloc) & by_year["year"].eq(2008)]
        if not row.empty:
            f[f"h2.parity_{bloc.lower()}_rate_pct"] = _fmt(
                float(row["green_rate_pct"].iloc[0]), 2
            )

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
    f["h3.em_nondilutive_n"] = str(h3["em_arm"]["em_green_non_dilutive_n"])
    # Cell sizes the instrument figure prints beside each bar.
    for row in h3["non_dilutive_by_bloc"]:
        if row["bloc"] in ("AE", "EM"):
            suffix = "green" if row["green"] else "nongreen"
            f[f"pop.{row['bloc'].lower()}_{suffix}_deals"] = f"{row['deals']:,}"
            f[f"h3.{row['bloc'].lower()}_{suffix}_nondilutive_pct"] = _fmt(
                row["non_dilutive_pct"], 2
            )
    # Whole-window non-dilutive share, the baseline the 2025 secondary evidence
    # about rising non-dilutive capital is read against in §8.
    rows = h3["non_dilutive_by_bloc"]
    f["h3.all_nondilutive_pct"] = _fmt(
        100 * sum(r["non_dilutive"] for r in rows) / sum(r["deals"] for r in rows), 1
    )

    # Taxonomy richness: the negative result. Emerging-market companies carry
    # MORE tags, so the gap is in which companies are indexed, not in how well
    # the indexed ones are described.
    tax = desc["taxonomy_richness"]
    f["tax.ae_mean_tags"] = _fmt(tax["mean_tags_ae"], 2)
    f["tax.em_mean_tags"] = _fmt(tax["mean_tags_em"], 2)
    f["tax.p"] = _p(tax["ae_vs_em_test"]["p_value"])
    f["tax.em_companies"] = f"{tax['ae_vs_em_test']['n_em']:,}"

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
    # The falsifier ran on a regressor where all but two countries sit at zero.
    # The caption has to say so, so the count is carried rather than described.
    deficit = h5["falsifier_stress_tests"]["electricity_deficit_pct"]
    f["h5.need_nonzero_countries"] = str(int(deficit["non_trivial_values"]))
    f["h5.depth_zero_countries"] = str(
        int(h5["power"]["countries_in_panel"]) - int(deficit["non_trivial_values"])
    )

    # -- power, shared by several captions --------------------------------
    f["power.min_cell"] = str(analysis["h1"]["gap_2_conditional_green_rate"]["min_cell_size"])

    # The condition each hypothesis was pre-registered to fail on. §8 of the web
    # edition states them beside the verdicts, so the reader can check that the
    # falsifier was written before the result and not after it.
    for name in ("h1", "h2", "h3", "h4", "h5"):
        condition = analysis[name].get("falsification_condition")
        if condition:
            f[f"{name}.falsifier"] = str(condition)

    # -- measurement thesis ----------------------------------------------
    f["measure.em_unspecified_pct"] = _fmt(
        100 * desc["subdomain_mix"]["em_unspecified_share"], 1
    )
    # Every bloc Figure 4 draws, not only the two the prose names.
    for bloc, share in desc["subdomain_mix"]["unspecified_share_by_bloc"].items():
        # The complement is derived from the ROUNDED value, not rounded
        # separately from the raw one. Rounding both halves independently gave
        # 67.9 and 32.2 for advanced economies — a pair that sums to 100.1 and
        # disagrees with the figure drawing the same two segments.
        unspecified = _fmt(100 * share, 1)
        f[f"measure.{str(bloc).lower()}_unspecified_pct"] = unspecified
        f[f"measure.{str(bloc).lower()}_specific_pct"] = _fmt(100 - float(unspecified), 1)
    f["measure.ae_unspecified_pct"] = _fmt(
        100 * desc["subdomain_mix"]["unspecified_share_by_bloc"]["AE"], 1
    )
    em_co = desc["subdomain_mix"]["companies_by_bloc"]["EM"]
    f["measure.em_green_companies"] = str(em_co["green_companies"])
    f["measure.em_unspecified_companies"] = str(em_co["unspecified"])
    thin = desc["thin_cells"]
    f["measure.thin_cells_pre2005"] = ", ".join(
        f"{year} n={n}" for year, n in sorted(thin["pre_2005_green_counts"].items())
    )
    f["h2.em_base_deals"] = str(thin["em_green_2007_base_deals"])
    f["h2.em_index_2008"] = f"{thin['em_green_2008_index_2007_base']:,.0f}"
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
    # The peak the cycle figure labels. It was drawn from the data and stated on
    # the figure with no key behind it, so nothing could check it.
    cyc = desc["green_cycle"]
    f["cycle.peak_deals"] = f"{cyc['peak_deals']:,}"
    f["cycle.peak_deals_year"] = str(cyc["peak_deals_year"])
    f["cycle.peak_usd_year"] = str(cyc["peak_usd_year"])
    # Green's peak share of venture dollars and of deals, which Figure 6
    # annotates.
    f["cycle.peak_dollar_share_pct"] = _fmt(cyc["peak_dollar_share_pct"], 1)
    f["cycle.peak_dollar_share_year"] = str(cyc["peak_dollar_share_year"])
    f["cycle.count_share_at_peak_pct"] = _fmt(cyc["count_share_at_peak_pct"], 1)

    f["cheque.pairs_negative_pct"] = _fmt(100 * ep["share_negative"], 0)
    f["cheque.pairs_evaluated"] = str(ep["pairs_evaluated"])
    f["cheque.range_to_close"] = (
        f"{ep['range_ending_at_close_pp'][0]:.1f} to {ep['range_ending_at_close_pp'][1]:.1f}"
    )

    # -- audit and robustness --------------------------------------------
    aud = analysis["audit"]
    f["audit.em_fp_pct"] = _fmt(aud["em"]["rate_pct"], 1)
    f["audit.ae_fp_pct"] = _fmt(aud["ae"]["rate_pct"], 1)
    f["audit.p"] = _p(aud["test"]["p_value"])
    f["audit.em_census_n"] = str(aud["em"]["companies"])
    f["audit.ae_sample_n"] = str(aud["ae"]["companies_sampled"])
    f["audit.ae_green_total"] = f"{aud['ae']['companies_total']:,}"
    f["audit.utility_scale"] = str(aud["utility_scale_companies"])
    perm = robust["permutation_double_gap"]
    f["robust.perm_observed_rr"] = _fmt(perm["observed_risk_ratio"], 3)
    f["robust.perm_null_ci"] = _ci(perm["null_ci"], 3)
    f["robust.perm_p"] = _fmt(perm["p_permutation"], 3)
    f["robust.perm_draws"] = f"{perm['draws']:,}"
    f["robust.green_def_rr_range"] = (
        f"{min(r['risk_ratio'] for r in robust['green_definitions']):.3f}–"
        f"{max(r['risk_ratio'] for r in robust['green_definitions']):.3f}"
    )
    by_spec = {r["specification"]: r for r in robust["green_definitions"]}
    f["robust.curated_rr"] = _fmt(by_spec["curated (ratified exclusions)"]["risk_ratio"], 2)
    f["robust.strict_rr"] = _fmt(by_spec["strict (Tier A only)"]["risk_ratio"], 2)
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
    # The author block is read from report/metadata.yaml, which is its single
    # source of truth; the README and the reproducibility statement render from
    # these keys rather than restating four names in three places.
    meta_path = cfg.root / "report" / "metadata.yaml"
    if meta_path.is_file():
        import re as _re

        import yaml as _yaml

        meta = _yaml.safe_load(_re.sub(r"^---\s*$", "", meta_path.read_text(), flags=_re.M))
        f["meta.authors"] = "; ".join(f"{a['name']} ({a['usn']})" for a in meta["authors"])
        f["meta.author_count"] = str(len(meta["authors"]))
        f["meta.guide"] = meta["guide"]
        f["meta.institution"] = meta["institution"]

    # Counted from the checksum ledger, not from memory: the prose said thirteen
    # source files when the ledger held twelve.
    checks = cfg.path("data_raw") / "_checksums.json"
    if checks.is_file():
        f["repro.source_files"] = str(len(json.loads(checks.read_text(encoding="utf-8"))))
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
