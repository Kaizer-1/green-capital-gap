"""Classification stage report: build step 3.

Runs the green classifier and the bloc assignment over the real data, then
computes the diagnostics that decide what the report is allowed to claim:
inter-tier agreement, the gated-pattern dependence, the veto counts, the
sub-domain mix tripwire, and the taxonomy tag-count comparison that tests
whether emerging-market companies are systematically less richly described.

Amounts here are NOMINAL USD. Deflation to constant 2015 USD happens at step 5.
The canonical deal table with its full attrition ledger is also step 5; the deal
join performed here exists only to compute bloc-split diagnostics.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from gcg.classify import blocs as blocs_mod
from gcg.classify.country_recovery import recover
from gcg.classify.green import classify, cohens_kappa, count_taxonomy_tags
from gcg.config import Config, get_logger, load_config, seed_everything
from gcg.io import read_parquet, write_parquet

LOG = get_logger("classify.run")

_AUDIT_TOP_N = 150
_SHOW_TOP_N = 30


def build_company_table(cfg: Config) -> pd.DataFrame:
    """Join the relational company table to the flat mirror's rich taxonomy.

    The flat mirror supplies ``category_list`` and ``market`` only. Its funding
    columns are deliberately not carried through: it is a later export vintage
    and is never used as a funding source (see docs/METHODOLOGY.md §5).
    """
    interim = cfg.path("data_interim")
    companies = read_parquet(interim / "cb_companies.parquet")
    flat = read_parquet(interim / "cb_flat.parquet")

    taxonomy = flat.loc[
        flat["permalink_norm"].notna(), ["permalink_norm", "category_list", "market"]
    ].drop_duplicates(subset=["permalink_norm"], keep="first")
    joined = companies.merge(taxonomy, on="permalink_norm", how="left")
    assert len(joined) == len(companies), "the taxonomy join must not duplicate companies"

    # Recover blank country codes before any bloc assignment. The blank bucket is
    # larger than the entire emerging-market bloc, so resolving what can be
    # resolved comes first (see country_recovery for why ccTLDs are allow-listed).
    joined, recovery_stats = recover(joined, flat, cfg)
    joined.attrs["recovery_stats"] = recovery_stats

    matched = joined["category_list"].notna().sum()
    LOG.info(
        "company table: %d companies, %d (%.1f%%) carry a rich category_list",
        len(joined),
        matched,
        100 * matched / len(joined),
    )
    return joined


def build_bloc_panel(cfg: Config) -> pd.DataFrame:
    """Build and persist the time-varying bloc panel."""
    income = read_parquet(cfg.path("data_interim") / "wb_income_groups.parquet")
    panel = blocs_mod.build_bloc_panel(cfg, income)
    write_parquet(panel, cfg.path("data_interim") / "bloc_panel.parquet")
    return panel


def attach_deal_level(cfg: Config, labels: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """Join green labels and time-varying blocs onto in-window deal rows.

    Diagnostics only. Step 5 builds the canonical table with the attrition ledger.
    """
    rounds = read_parquet(cfg.path("data_interim") / "cb_rounds.parquet")
    w = cfg.window
    deals = rounds.loc[rounds["funded_at"].between(w["start"], w["end"])].copy()
    deals["year"] = deals["funded_at"].dt.year

    cols = [
        "object_id",
        "country_code",
        "country_recovery_route",
        "green",
        "green_strict_tier_a",
        "green_tier",
        "green_subdomain",
        "depends_on_gated_pattern",
        "tier_c_vetoed",
        "veto_reason",
        "taxonomy_tag_count",
    ]
    deals = deals.merge(labels[cols], on="object_id", how="left")
    deals["country_code"], _ = blocs_mod.normalise_country_code(deals["country_code"], cfg)
    deals, bloc_stats = blocs_mod.assign(deals, panel, cfg)
    deals["green"] = deals["green"].fillna(False).astype(bool)

    LOG.info("deal-level diagnostic table: %d in-window deals", len(deals))
    deals.attrs["bloc_stats"] = bloc_stats
    return deals


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------
def tier_agreement(cfg: Config, labels: pd.DataFrame) -> dict[str, Any]:  # noqa: ARG001
    """Cohen's kappa between Tier A and Tier B, on the analysis population.

    Computed on companies that carry a rich ``category_list``: Tier B cannot be
    evaluated fairly where the taxonomy field is absent, so including those
    companies would understate agreement for a reason that has nothing to do
    with the lexicon.
    """
    joined = labels.loc[labels["has_taxonomy"]]
    overall = cohens_kappa(labels["tier_a"], labels["tier_b_surviving"])
    on_joined = cohens_kappa(joined["tier_a"], joined["tier_b_surviving"])
    funded = labels.loc[labels["is_funded"] & labels["has_taxonomy"]]
    on_funded = cohens_kappa(funded["tier_a"], funded["tier_b_surviving"])

    LOG.info(
        "Cohen's kappa  all=%.4f  with-taxonomy=%.4f  funded-with-taxonomy=%.4f",
        overall["kappa"],
        on_joined["kappa"],
        on_funded["kappa"],
    )
    return {
        "all_companies": overall,
        "with_taxonomy": on_joined,
        "funded_with_taxonomy": on_funded,
    }


def gated_pattern_dependence(cfg: Config, deals: pd.DataFrame) -> dict[str, Any]:
    """Quantify how much of the green sample rests on the bare-``Energy`` pattern.

    Reported as deals and nominal dollars, split by bloc. The tripwire in
    ``pipeline.yaml`` decides whether this gets one line or a section.
    """
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
                "green_usd_nominal": float(grp["raised_amount_usd"].sum()),
                "gated_usd_nominal": float(d["raised_amount_usd"].sum()),
                "gated_usd_share": round(
                    float(d["raised_amount_usd"].sum() / grp["raised_amount_usd"].sum()), 4
                )
                if grp["raised_amount_usd"].sum()
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


def veto_audit(cfg: Config, labels: pd.DataFrame) -> dict[str, Any]:
    """Count every Tier-C veto by reason, with examples.

    CLAUDE.md requires the exclusion list to be an audit trail. A veto nobody
    counted is indistinguishable from a veto that never fired.
    """
    vetoed = labels.loc[labels["tier_c_vetoed"]]
    by_reason = (
        vetoed.groupby("veto_pattern")
        .agg(
            companies=("object_id", "size"),
            funded_companies=("is_funded", "sum"),
            reason=("veto_reason", "first"),
        )
        .sort_values("companies", ascending=False)
        .reset_index()
    )
    _save(cfg, by_reason, "appendix_veto_counts", index=False)

    # Diversified firms: a green tag AND a fossil tag. veto_all removes them.
    fossil_rule = next(r for r in cfg.lexicon["exclusions"] if "petroleum" in r["pattern"])
    fossil_hit = labels["match_text"].str.contains(
        fossil_rule["pattern"], case=False, na=False
    )
    diversified = labels.loc[fossil_hit & labels["tier_b_raw"]]
    div_examples = diversified.loc[
        diversified["match_text"].str.contains(
            r"solar|wind|renewab|biofuel|photovolt", case=False, na=False
        )
    ]
    exhibit = div_examples[
        ["permalink_norm", "name", "country_code", "category_code", "match_text"]
    ].head(40)
    _save(cfg, exhibit, "appendix_fossil_veto_diversified_firms", index=False)

    findings = {
        "companies_vetoed": int(len(vetoed)),
        "funded_companies_vetoed": int(vetoed["is_funded"].sum()),
        "by_pattern": by_reason.head(20).to_dict("records"),
        "fossil_veto_total": int((fossil_hit & labels["tier_b_raw"]).sum()),
        "fossil_veto_with_green_tag": int(len(div_examples)),
        "fossil_veto_diversified_examples": div_examples[
            ["permalink_norm", "name", "country_code"]
        ]
        .head(10)
        .to_dict("records"),
    }
    LOG.info(
        "Tier-C vetoes: %d companies (%d funded). Fossil veto hit %d Tier-B companies, "
        "of which %d also carry an explicit green tag (diversified firms).",
        findings["companies_vetoed"],
        findings["funded_companies_vetoed"],
        findings["fossil_veto_total"],
        findings["fossil_veto_with_green_tag"],
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
        "in_window_usd_nominal_bn": round(
            float(in_window["raised_amount_usd"].sum()) / 1e9, 3
        ),
        "threshold": threshold,
        "is_trivial": bool(len(in_window) <= threshold),
        "examples": funded[["permalink_norm", "name", "country_code"]]
        .head(10)
        .to_dict("records"),
    }
    LOG.info(
        "nuclear: %d companies match, %d funded, %d in-window deals ($%.2fbn) -> trivial = %s",
        findings["companies_matching_nuclear"],
        findings["funded_companies"],
        findings["in_window_deals"],
        findings["in_window_usd_nominal_bn"],
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
    funding = (
        deals.loc[deals["green"]]
        .groupby("object_id")
        .agg(
            in_window_deals=("raised_amount_usd", "size"),
            in_window_usd=("raised_amount_usd", "sum"),
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


def _save(cfg: Config, df: pd.DataFrame, name: str, *, index: bool = True) -> None:
    path = cfg.path("tables") / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index)
    LOG.info("wrote %-48s %d rows", path.name, len(df))


# ---------------------------------------------------------------------------
def run(cfg: Config | None = None) -> dict[str, Any]:
    """Run the classification stage and persist labels, panel and diagnostics."""
    cfg = cfg or load_config()
    cfg.ensure_dirs()
    seed_everything(cfg)

    companies = build_company_table(cfg)
    panel = build_bloc_panel(cfg)

    labels = classify(companies, cfg)
    # classify() reads the ORIGINAL country_code; overwrite with the recovered
    # one so every downstream bloc assignment uses it, and keep the route.
    labels["country_code"] = companies["country_code_recovered"].to_numpy()
    labels["country_recovery_route"] = companies["country_recovery_route"].to_numpy()
    labels["has_taxonomy"] = companies["category_list"].notna().to_numpy()
    if "taxonomy_tag_count" not in labels.columns:
        labels["taxonomy_tag_count"] = count_taxonomy_tags(
            companies["category_list"]
        ).to_numpy()

    rounds = read_parquet(cfg.path("data_interim") / "cb_rounds.parquet")
    funded_ids = set(rounds["object_id"].dropna())
    labels["is_funded"] = labels["object_id"].isin(funded_ids)

    write_parquet(labels, cfg.path("data_interim") / "green_labels.parquet")

    deals = attach_deal_level(cfg, labels, panel)

    findings: dict[str, Any] = {
        "country_recovery": companies.attrs["recovery_stats"],
        "population": {
            "companies": int(len(labels)),
            "funded_companies": int(labels["is_funded"].sum()),
            "with_taxonomy": int(labels["has_taxonomy"].sum()),
            "funded_with_taxonomy": int((labels["is_funded"] & labels["has_taxonomy"]).sum()),
            "in_window_deals": int(len(deals)),
        },
        "counts": {
            "green_headline": int(labels["green"].sum()),
            "green_funded": int((labels["green"] & labels["is_funded"]).sum()),
            "tier_a": int(labels["tier_a"].sum()),
            "tier_b_raw": int(labels["tier_b_raw"].sum()),
            "tier_b_surviving": int(labels["tier_b_surviving"].sum()),
            "tier_c_vetoed": int(labels["tier_c_vetoed"].sum()),
            "by_tier": labels["green_tier"].value_counts().to_dict(),
            "green_deals_in_window": int(deals["green"].sum()),
            "green_deals_strict": int(deals["green_strict_tier_a"].fillna(False).sum()),
        },
        "bloc_assignment": deals.attrs["bloc_stats"],
        "tier_agreement": tier_agreement(cfg, labels),
        "gated_dependence": gated_pattern_dependence(cfg, deals),
        "vetoes": veto_audit(cfg, labels),
        "nuclear": nuclear_check(cfg, labels, deals),
        "subdomain_mix": subdomain_mix(cfg, deals),
        "taxonomy_richness": taxonomy_richness(cfg, deals, labels),
        "coverage_bias": coverage_bias(cfg, deals),
    }
    tier_b_only_audit(cfg, labels, deals)

    path = cfg.path("data_interim") / "classification_diagnostics.json"
    path.write_text(json.dumps(findings, indent=2, default=str) + "\n", encoding="utf-8")
    LOG.info("wrote %s", path.name)
    return findings


if __name__ == "__main__":
    run()
