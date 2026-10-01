"""Deal-level descriptive diagnostics, computed on the CANONICAL deal table.

Every function here reads ``data/processed/deals.parquet``, the table produced by
``transform/deals.py`` after the attrition ledger has been applied.

That is the point of this module existing. These diagnostics previously ran
inside the classification stage against its own ad-hoc in-window join, which
bypassed the ledger: it never dropped the 298 orphan ``object_id`` rows, the 104
duplicates or the 19 implausible dates. The two populations differed by 350
rows, so the same quantity had two values depending on which stage reported it
(advanced-economy deals were 37,965 in one place and 37,896 in another). Running
every deal-level number off one post-ledger table removes that whole class of
discrepancy rather than correcting instances of it.

Amounts are constant 2015 USD unless a function says otherwise.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from gcg.config import Config, get_logger, load_config, seed_everything
from gcg.io import read_parquet

LOG = get_logger("analysis.descriptives")

_AUDIT_TOP_N = 150
_SHOW_TOP_N = 30


def _save(cfg: Config, df: pd.DataFrame, name: str, *, index: bool = True) -> None:
    """Write a diagnostic table to outputs/tables as CSV."""
    path = cfg.path("tables") / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index)
    LOG.info("wrote %-48s %d rows", path.name, len(df))


def gated_pattern_dependence(cfg: Config, deals: pd.DataFrame) -> dict[str, Any]:
    """Quantify how much of the green sample rests on the bare-``Energy`` pattern.

    Reported as deals and nominal dollars, split by bloc. The tripwire in
    ``pipeline.yaml`` decides whether this gets one line or a section.
    """
    amount = cfg.pipeline["deflate"]["real_column"]
    green = deals.loc[deals["green"]]
    dep = green.loc[green["depends_on_gated_pattern"].fillna(False)]

    rows = []
    for bloc, grp in green.groupby("bloc", observed=True):
        d = grp.loc[grp["depends_on_gated_pattern"].fillna(False)]
        rows.append(
            {
                "bloc": bloc,
                "green_deals": len(grp),
                "gated_deals": len(d),
                "gated_deal_share": round(len(d) / len(grp), 4) if len(grp) else 0.0,
                "green_usd_real2015": float(grp[amount].sum()),
                "gated_usd_real2015": float(d[amount].sum()),
                "gated_usd_share": round(float(d[amount].sum() / grp[amount].sum()), 4)
                if grp[amount].sum()
                else 0.0,
            }
        )
    table = pd.DataFrame(rows).sort_values("green_deals", ascending=False)
    _save(cfg, table, "diag_bare_energy_dependence_by_bloc", index=False)

    em = table.loc[table["bloc"].eq("EM")]
    em_share = float(em["gated_deal_share"].iloc[0]) if len(em) else 0.0
    threshold = float(cfg.tripwire("bare_energy_em_share_trivial"))

    findings = {
        "green_deals_total": len(green),
        "gated_dependent_deals": len(dep),
        "gated_dependent_share_all": round(len(dep) / len(green), 4) if len(green) else 0.0,
        "em_gated_deal_share": round(em_share, 4),
        "em_threshold": threshold,
        "em_below_threshold": bool(em_share < threshold),
        "by_bloc": table.to_dict("records"),
    }
    LOG.info(
        "bare-energy dependence: %d/%d green deals overall (%.2f%%); EM share %.2f%% "
        "vs %.1f%% threshold -> trivial = %s",
        len(dep),
        len(green),
        100 * findings["gated_dependent_share_all"],
        100 * em_share,
        100 * threshold,
        findings["em_below_threshold"],
    )
    return findings


def nuclear_check(cfg: Config, labels: pd.DataFrame, deals: pd.DataFrame) -> dict[str, Any]:
    """Verify empirically that nuclear venture activity is negligible in 2000-2012.

    If n is trivial the nuclear veto gets a footnote and no robustness budget,
    per the ruling recorded before this was computed.
    """
    rule = next(r for r in cfg.lexicon["exclusions"] if "nuclear" in r["pattern"])
    hit = labels["match_text"].str.contains(rule["pattern"], case=False, na=False)
    companies = labels.loc[hit]
    funded = companies.loc[companies["is_funded"]]
    in_window = deals.loc[deals["object_id"].isin(set(funded["object_id"]))]

    threshold = int(cfg.tripwire("nuclear_trivial_n"))
    findings = {
        "companies_matching_nuclear": int(len(companies)),
        "funded_companies": int(len(funded)),
        "in_window_deals": int(len(in_window)),
        "in_window_usd_real2015_bn": round(
            float(in_window[cfg.pipeline["deflate"]["real_column"]].sum()) / 1e9, 3
        ),
        "threshold": threshold,
        "is_trivial": bool(len(in_window) <= threshold),
        "examples": funded[["permalink_norm", "name", "country_code"]]
        .head(10)
        .to_dict("records"),
    }
    LOG.info(
        "nuclear: %d companies match, %d funded, %d in-window deals "
        "($%.2fbn, 2015 USD) -> trivial = %s",
        findings["companies_matching_nuclear"],
        findings["funded_companies"],
        findings["in_window_deals"],
        findings["in_window_usd_real2015_bn"],
        findings["is_trivial"],
    )
    return findings


def subdomain_mix(cfg: Config, deals: pd.DataFrame) -> dict[str, Any]:
    """Sub-domain mix by bloc, and the ``general_unspecified`` tripwire.

    If unspecified exceeds the configured share for EM, Figure 5 is reframed:
    mix conditional on having a specific sub-domain, with the unspecified rate
    plotted as its own bar alongside.
    """
    green = deals.loc[deals["green"] & deals["green_subdomain"].notna()]
    table = (
        pd.crosstab(green["green_subdomain"], green["bloc"])
        .reindex(cfg.lexicon["subdomain_priority"])
        .fillna(0)
        .astype(int)
    )
    shares = (table / table.sum(axis=0) * 100).round(2)
    _save(
        cfg,
        pd.concat([table.add_prefix("n_"), shares.add_prefix("pct_")], axis=1),
        "diag_subdomain_mix_by_bloc",
    )

    unspec = {}
    for bloc in table.columns:
        total = int(table[bloc].sum())
        n = (
            int(table.loc["general_unspecified", bloc])
            if "general_unspecified" in table.index
            else 0
        )
        unspec[str(bloc)] = round(n / total, 4) if total else 0.0

    threshold = float(cfg.tripwire("general_unspecified_em_share_max"))
    em_share = unspec.get("EM", 0.0)
    findings = {
        "unspecified_share_by_bloc": unspec,
        "em_unspecified_share": em_share,
        "em_threshold": threshold,
        "tripwire_crossed": bool(em_share > threshold),
        "figure5_needs_reframing": bool(em_share > threshold),
        "counts_by_bloc": table.to_dict(),
    }
    LOG.info(
        "sub-domain mix: general_unspecified share by bloc %s; EM %.1f%% vs %.0f%% "
        "threshold -> Figure 5 reframe needed = %s",
        {k: f"{v:.1%}" for k, v in unspec.items()},
        100 * em_share,
        100 * threshold,
        findings["tripwire_crossed"],
    )
    return findings


def taxonomy_richness(
    cfg: Config, deals: pd.DataFrame, labels: pd.DataFrame
) -> dict[str, Any]:
    """Mean taxonomy tag-count per company by bloc.

    Tests whether emerging-market companies are systematically less richly
    described. If they are, that is a coverage-bias finding for the report's
    data section, not a footnote about the classifier: a company with fewer tags
    has fewer chances to trip a green pattern, so green prevalence would be
    understated in EM for a purely descriptive reason.
    """
    # Company level, deduplicated. Restricted to companies that actually HAVE a
    # taxonomy: count_taxonomy_tags returns 0 for a missing category_list, so
    # including unmatched companies would conflate "not joined to the flat file"
    # with "described by few tags" and make the comparison meaningless. The
    # join rate itself is reported separately, by bloc, as its own coverage
    # measure.
    has_tax = labels.loc[labels["has_taxonomy"], "object_id"]
    firms = (
        deals.loc[
            deals["object_id"].isin(set(has_tax)),
            ["object_id", "bloc", "taxonomy_tag_count", "green"],
        ]
        .dropna(subset=["taxonomy_tag_count"])
        .drop_duplicates(subset=["object_id"])
    )
    join_rate = (
        deals.assign(has_tax=deals["object_id"].isin(set(has_tax)))
        .drop_duplicates(subset=["object_id"])
        .groupby("bloc", observed=True)["has_tax"]
        .agg(companies="size", joined="sum")
        .assign(join_rate=lambda x: (x["joined"] / x["companies"]).round(4))
    )
    _save(cfg, join_rate, "diag_taxonomy_join_rate_by_bloc")
    by_bloc = (
        firms.groupby("bloc", observed=True)["taxonomy_tag_count"]
        .agg(companies="size", mean_tags="mean", median_tags="median", std="std")
        .round(3)
        .sort_values("companies", ascending=False)
    )
    _save(cfg, by_bloc, "diag_taxonomy_tag_count_by_bloc")

    # Green prevalence alongside, so the two can be read together.
    prevalence = (
        firms.groupby("bloc", observed=True)["green"]
        .agg(companies="size", green="sum")
        .assign(green_pct=lambda d: (100 * d["green"] / d["companies"]).round(2))
    )
    _save(cfg, prevalence, "diag_green_prevalence_by_bloc")

    ae = float(by_bloc.loc["AE", "mean_tags"]) if "AE" in by_bloc.index else float("nan")
    em = float(by_bloc.loc["EM", "mean_tags"]) if "EM" in by_bloc.index else float("nan")

    # Mann-Whitney U: tag counts are counts, not normal.
    from scipy.stats import mannwhitneyu

    test = {}
    if {"AE", "EM"} <= set(firms["bloc"].unique()):
        a = firms.loc[firms["bloc"].eq("AE"), "taxonomy_tag_count"]
        b = firms.loc[firms["bloc"].eq("EM"), "taxonomy_tag_count"]
        stat, p = mannwhitneyu(a, b, alternative="two-sided")
        # Rank-biserial correlation as the effect size.
        rbc = 1 - (2 * stat) / (len(a) * len(b))
        test = {
            "mannwhitney_u": float(stat),
            "p_value": float(p),
            "rank_biserial_r": round(float(rbc), 4),
            "n_ae": int(len(a)),
            "n_em": int(len(b)),
        }

    findings = {
        "by_bloc": by_bloc.reset_index().to_dict("records"),
        "mean_tags_ae": round(ae, 3),
        "mean_tags_em": round(em, 3),
        "em_minus_ae": round(em - ae, 3),
        "em_fewer_tags": bool(em < ae),
        "ae_vs_em_test": test,
        "green_prevalence_by_bloc": prevalence.reset_index().to_dict("records"),
        "taxonomy_join_rate_by_bloc": join_rate.reset_index().to_dict("records"),
    }
    LOG.info(
        "taxonomy richness: mean tags AE=%.3f EM=%.3f (EM-AE = %+.3f); EM fewer = %s",
        ae,
        em,
        findings["em_minus_ae"],
        findings["em_fewer_tags"],
    )
    if test:
        LOG.info(
            "  Mann-Whitney U=%.0f p=%.3g rank-biserial r=%.4f (n_AE=%d n_EM=%d)",
            test["mannwhitney_u"],
            test["p_value"],
            test["rank_biserial_r"],
            test["n_ae"],
            test["n_em"],
        )
    return findings


def coverage_bias(cfg: Config, deals: pd.DataFrame) -> dict[str, Any]:
    """Benchmark each bloc's share of recorded deals against its share of world GDP.

    The single most important diagnostic in the project. CLAUDE.md §7 names
    Crunchbase's under-coverage of non-US, non-English-language ecosystems as the
    biggest threat to validity and asks for it to be quantified rather than
    disclaimed. This is that quantification, and it also establishes how far the
    emerging-market sample can be pushed before it stops meaning anything.

    GDP shares are computed over the same country set that the bloc panel covers,
    so the two series are comparable by construction rather than by assumption.
    """
    indicators = read_parquet(cfg.path("data_interim") / "wb_indicators.parquet")
    panel = read_parquet(cfg.path("data_interim") / "bloc_panel.parquet")

    gdp = indicators.loc[
        indicators["indicator"].eq("gdp_current_usd"), ["country_code", "year", "value"]
    ].dropna(subset=["value"])
    gdp = gdp.merge(
        panel[["country_code", "year", "bloc"]], on=["country_code", "year"], how="inner"
    )
    gdp_by = (
        gdp.groupby(["year", "bloc"], observed=True)["value"].sum().unstack(fill_value=0.0)
    )

    deal_by = deals.groupby(["year", "bloc"], observed=True).size().unstack(fill_value=0)
    green_by = (
        deals.loc[deals["green"]]
        .groupby(["year", "bloc"], observed=True)
        .size()
        .unstack(fill_value=0)
    )

    y0, y1 = int(cfg.window["start"][:4]), int(cfg.window["end"][:4])
    rows = []
    for year in range(y0, y1 + 1):
        if year not in gdp_by.index or year not in deal_by.index:
            continue
        gdp_total = float(gdp_by.loc[year].sum())
        deal_total = int(deal_by.loc[year].sum())
        green_total = int(green_by.loc[year].sum()) if year in green_by.index else 0
        for bloc in ("AE", "EM", "CHINA", "LDC"):
            gdp_share = (
                100 * float(gdp_by.loc[year].get(bloc, 0.0)) / gdp_total if gdp_total else 0.0
            )
            deal_share = (
                100 * int(deal_by.loc[year].get(bloc, 0)) / deal_total if deal_total else 0.0
            )
            green_n = int(green_by.loc[year].get(bloc, 0)) if year in green_by.index else 0
            green_share = 100 * green_n / green_total if green_total else 0.0
            rows.append(
                {
                    "year": year,
                    "bloc": bloc,
                    "gdp_share_pct": round(gdp_share, 3),
                    "deal_share_pct": round(deal_share, 3),
                    "green_deal_share_pct": round(green_share, 3),
                    "green_deals": green_n,
                    "representation_ratio": round(deal_share / gdp_share, 4)
                    if gdp_share
                    else None,
                    "gap_pp": round(gdp_share - deal_share, 3),
                }
            )
    table = pd.DataFrame(rows)
    _save(cfg, table, "diag_coverage_bias_by_bloc_year", index=False)

    em = table.loc[table["bloc"].eq("EM")].set_index("year")
    ratios = em["representation_ratio"].dropna()
    findings = {
        "em_gdp_share_pct_range": [
            round(float(em["gdp_share_pct"].min()), 2),
            round(float(em["gdp_share_pct"].max()), 2),
        ],
        "em_deal_share_pct_range": [
            round(float(em["deal_share_pct"].min()), 2),
            round(float(em["deal_share_pct"].max()), 2),
        ],
        "em_representation_ratio_range": [
            round(float(ratios.min()), 4),
            round(float(ratios.max()), 4),
        ],
        "em_under_representation_factor_range": [
            round(1 / float(ratios.max()), 2),
            round(1 / float(ratios.min()), 2),
        ],
        "em_gap_pp_first_year": round(float(em["gap_pp"].iloc[0]), 2),
        "em_gap_pp_last_year": round(float(em["gap_pp"].iloc[-1]), 2),
        "em_gap_pp_max": round(float(em["gap_pp"].max()), 2),
        "em_green_deals_total": int(em["green_deals"].sum()),
        "by_year": table.to_dict("records"),
    }
    LOG.info(
        "COVERAGE BIAS: EM is %.1f-%.1f%% of world GDP but only %.1f-%.1f%% of recorded "
        "deals -> under-represented by %.1fx to %.1fx; gap %.1fpp to %.1fpp",
        *findings["em_gdp_share_pct_range"],
        *findings["em_deal_share_pct_range"],
        *findings["em_under_representation_factor_range"],
        findings["em_gap_pp_first_year"],
        findings["em_gap_pp_last_year"],
    )
    return findings


def tier_b_only_audit(cfg: Config, labels: pd.DataFrame, deals: pd.DataFrame) -> pd.DataFrame:
    """The top-150 Tier-B-only companies by in-window funding, for manual review.

    CLAUDE.md §6: eyeball these and record the exclusion decisions in
    ``green_lexicon.yaml`` with a one-line reason each. This produces the
    worksheet; the decisions are made by a human reading it.
    """
    amount = cfg.pipeline["deflate"]["real_column"]
    funding = (
        deals.loc[deals["green"]]
        .groupby("object_id")
        .agg(
            in_window_deals=(amount, "size"),
            in_window_usd=(amount, "sum"),
            first_year=("year", "min"),
            bloc=("bloc", "first"),
        )
    )
    b_only = labels.loc[labels["green"] & labels["tier_b_surviving"] & ~labels["tier_a"]]
    audit = (
        b_only.merge(funding, left_on="object_id", right_index=True, how="inner")
        .sort_values("in_window_usd", ascending=False)
        .head(_AUDIT_TOP_N)
    )
    cols = [
        "permalink_norm",
        "name",
        "country_code",
        "bloc",
        "category_code",
        "green_subdomain",
        "in_window_deals",
        "in_window_usd",
        "first_year",
        "green_matched_pattern_ids",
        "green_matched_patterns",
        "match_text",
    ]
    out = audit[cols].reset_index(drop=True)
    _save(cfg, out, "audit_tier_b_only_top150", index=False)
    LOG.info("wrote the top-%d Tier-B-only audit worksheet", len(out))
    return out


def run(cfg: Config | None = None) -> dict[str, Any]:
    """Run every deal-level descriptive against the canonical deal table."""
    cfg = cfg or load_config()
    cfg.ensure_dirs()
    seed_everything(cfg)

    deals = read_parquet(cfg.path("data_processed") / "deals.parquet")
    labels = read_parquet(cfg.path("data_interim") / "green_labels.parquet")

    LOG.info("descriptives on the canonical table: %d deals", len(deals))
    by_bloc = deals.groupby("bloc", observed=True).size()
    LOG.info("bloc composition: %s (total %d)", by_bloc.to_dict(), int(by_bloc.sum()))

    findings: dict[str, Any] = {
        "population": {
            "deals": int(len(deals)),
            "by_bloc": {str(k): int(v) for k, v in by_bloc.items()},
            "green_raw": int(deals["green"].sum()),
            "green_curated": int(deals["green_curated"].sum()),
            "green_strict": int(deals["green_strict_tier_a"].fillna(False).sum()),
            "source": "data/processed/deals.parquet (post-attrition-ledger)",
        },
        "gated_dependence": gated_pattern_dependence(cfg, deals),
        "nuclear": nuclear_check(cfg, labels, deals),
        "subdomain_mix": subdomain_mix(cfg, deals),
        "taxonomy_richness": taxonomy_richness(cfg, deals, labels),
        "coverage_bias": coverage_bias(cfg, deals),
    }
    tier_b_only_audit(cfg, labels, deals)

    path = cfg.path("data_interim") / "descriptive_diagnostics.json"
    path.write_text(json.dumps(findings, indent=2, default=str) + "\n", encoding="utf-8")
    LOG.info("wrote %s", path.name)
    return findings


if __name__ == "__main__":
    run()
