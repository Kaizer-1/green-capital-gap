"""Classification stage: build steps 3 and 4.

Produces the two company-level artefacts the rest of the pipeline joins against:

- ``green_labels.parquet`` — the per-company green audit table, with the tier
  that fired, the regexes that matched, the sub-domain, any veto reason, and the
  recovered country code.
- ``bloc_panel.parquet`` — the time-varying country-year to bloc panel.

Only COMPANY-level diagnostics live here (inter-tier agreement and the veto
audit). Every deal-level number is computed in ``analysis/descriptives.py``
against the canonical post-ledger deal table, so that a quantity has one value
rather than one per stage.
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


def _save(cfg: Config, df: pd.DataFrame, name: str, *, index: bool = True) -> None:
    path = cfg.path("tables") / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index)
    LOG.info("wrote %-48s %d rows", path.name, len(df))


# ---------------------------------------------------------------------------
def run(cfg: Config | None = None) -> dict[str, Any]:
    """Build the green labels and the bloc panel, with company-level diagnostics."""
    cfg = cfg or load_config()
    cfg.ensure_dirs()
    seed_everything(cfg)

    companies = build_company_table(cfg)
    build_bloc_panel(cfg)

    labels = classify(companies, cfg)
    # classify() reads the ORIGINAL country_code; overwrite with the recovered
    # one so every downstream bloc assignment uses it, and keep the route.
    labels["country_code"] = companies["country_code_recovered"].to_numpy()
    labels["country_recovery_route"] = companies["country_recovery_route"].to_numpy()
    labels["has_taxonomy"] = companies["category_list"].notna().to_numpy()
    # Source attributes H4 needs for founding cohorts, carried on the labels
    # table so it is the single company-level join target downstream.
    labels["founded_at"] = pd.to_datetime(companies["founded_at"], errors="coerce").to_numpy()
    labels["status"] = companies["status"].to_numpy()
    if "taxonomy_tag_count" not in labels.columns:
        labels["taxonomy_tag_count"] = count_taxonomy_tags(
            companies["category_list"]
        ).to_numpy()

    rounds = read_parquet(cfg.path("data_interim") / "cb_rounds.parquet")
    labels["is_funded"] = labels["object_id"].isin(set(rounds["object_id"].dropna()))

    write_parquet(labels, cfg.path("data_interim") / "green_labels.parquet")

    findings: dict[str, Any] = {
        "country_recovery": companies.attrs["recovery_stats"],
        "population": {
            "companies": int(len(labels)),
            "funded_companies": int(labels["is_funded"].sum()),
            "with_taxonomy": int(labels["has_taxonomy"].sum()),
            "funded_with_taxonomy": int((labels["is_funded"] & labels["has_taxonomy"]).sum()),
        },
        "counts": {
            "green_headline": int(labels["green"].sum()),
            "green_curated": int(labels["green_curated"].sum()),
            "green_funded": int((labels["green"] & labels["is_funded"]).sum()),
            "tier_a": int(labels["tier_a"].sum()),
            "tier_b_raw": int(labels["tier_b_raw"].sum()),
            "tier_b_surviving": int(labels["tier_b_surviving"].sum()),
            "tier_c_vetoed": int(labels["tier_c_vetoed"].sum()),
            "by_tier": labels["green_tier"].value_counts().to_dict(),
        },
        "tier_agreement": tier_agreement(cfg, labels),
        "vetoes": veto_audit(cfg, labels),
        "note": (
            "Company-level only. Every deal-level number is produced by "
            "analysis/descriptives.py against the canonical post-ledger deal table."
        ),
    }
    path = cfg.path("data_interim") / "classification_diagnostics.json"
    path.write_text(json.dumps(findings, indent=2, default=str) + "\n", encoding="utf-8")
    LOG.info("wrote %s", path.name)
    return findings


if __name__ == "__main__":
    run()
