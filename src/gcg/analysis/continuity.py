"""The continuity probe: Indian startup funding, 2015-2020.

Report §8. Asks whether the structural signatures found in 2000-2012 still
appear in a later window in one large emerging market.

This dataset is **never pooled** with the Crunchbase data. The taxonomies and
amount conventions are not compatible, and the two are kept visually and
analytically separate throughout (CLAUDE.md §4, RESEARCH_BRIEF §6).

The probe produces its own finding rather than rescuing the main one: run
through the same lexicon, a 3,044-row scrape of Indian funding across six years
yields a green count in the low tens. The measurement problem does not end with
the 2013 snapshot.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from gcg.analysis.h1_selection import two_proportion_test, wilson_interval
from gcg.classify.green import classify
from gcg.config import Config, get_logger, load_config, seed_everything
from gcg.io import read_parquet, write_parquet

LOG = get_logger("analysis.continuity")


def prepare(cfg: Config) -> pd.DataFrame:
    """Shape the Indian scrape so the project's own classifier can read it.

    The classifier expects the Crunchbase field names. Mapping the Indian
    columns onto them means the same lexicon, the same vetoes and the same
    sub-domain priority apply to both datasets, which is the only way the
    comparison means anything — even though the resulting labels are not
    pooled.
    """
    df = read_parquet(cfg.path("data_interim") / "india_funding.parquet").copy()

    df["category_list"] = df["industry"].astype("string").fillna("")
    df["tag_list"] = df["subvertical"].astype("string").fillna("")
    df["short_description"] = df["tag_list"]
    df["market"] = df["category_list"]
    df["category_code"] = ""  # no equivalent field; Tier A cannot fire here
    df["name"] = df["startup"]
    df["permalink_norm"] = df["startup"].astype("string").str.lower().str.strip()
    df["country_code"] = "IND"
    df["id"] = range(len(df))
    return df


def like_for_like(cfg: Config, india_green: int, india_n: int) -> dict[str, Any]:
    """Compare the Indian green rate with Crunchbase on a Tier-B-only basis.

    The Indian scrape has no ``category_code``, so Tier A cannot fire there and
    every Indian label is Tier B. Comparing that against a Crunchbase rate that
    includes Tier-A hits compares a one-tier classifier with a two-tier one and
    would overstate the Crunchbase rate for a reason that has nothing to do with
    either economy.

    Both pairs are reported: the headline rates, and the Tier-B-only rates that
    are actually comparable.
    """
    deals = read_parquet(cfg.path("data_processed") / "deals.parquet")
    # green = TierA OR (TierB AND NOT TierC), so Tier-B-surviving-and-unvetoed
    # is exactly the rows whose tier label is "B" or "A+B".
    tier_b_only = deals["green_tier"].isin(["B", "A+B"])

    rows = []
    for bloc in ("AE", "EM"):
        sub = deals.loc[deals["bloc"].eq(bloc)]
        sub_b = tier_b_only.loc[sub.index]
        for basis, flags in (("headline (A or B)", sub["green"]), ("Tier B only", sub_b)):
            k, n = int(flags.sum()), len(sub)
            lo, hi = wilson_interval(k, n)
            rows.append(
                {
                    "source": f"Crunchbase {bloc}",
                    "basis": basis,
                    "green": k,
                    "deals": n,
                    "rate_pct": round(100 * k / n, 3),
                    "ci_lo_pct": round(100 * lo, 3),
                    "ci_hi_pct": round(100 * hi, 3),
                }
            )
    lo, hi = wilson_interval(india_green, india_n)
    rows.append(
        {
            "source": "India scrape",
            "basis": "Tier B only (forced: no category_code)",
            "green": india_green,
            "deals": india_n,
            "rate_pct": round(100 * india_green / india_n, 3),
            "ci_lo_pct": round(100 * lo, 3),
            "ci_hi_pct": round(100 * hi, 3),
        }
    )
    table = pd.DataFrame(rows)
    table.to_csv(cfg.path("tables") / "appendix_india_like_for_like.csv", index=False)
    LOG.info("wrote appendix_india_like_for_like.csv")

    em_b = table.loc[
        table["source"].eq("Crunchbase EM") & table["basis"].eq("Tier B only")
    ].iloc[0]
    test = two_proportion_test(india_green, india_n, int(em_b["green"]), int(em_b["deals"]))

    findings = {
        "comparable_basis": "Tier B only",
        "india_rate_pct": round(100 * india_green / india_n, 3),
        "crunchbase_em_tier_b_rate_pct": float(em_b["rate_pct"]),
        "india_vs_em_tier_b": {
            "risk_ratio": test.get("risk_ratio"),
            "risk_ratio_ci": test.get("risk_ratio_ci"),
            "p_value": test["p_value"],
            "fisher_p_value": test["fisher_p_value"],
        },
        "rows": table.to_dict("records"),
        "why": (
            "The Indian data carries no category_code, so Tier A cannot fire and every "
            "Indian green label is Tier B. Comparing it against the Crunchbase headline "
            "rate, which admits Tier-A hits, would compare a one-tier classifier with a "
            "two-tier one. Both pairs are reported; the Tier-B-only pair is the "
            "like-for-like one."
        ),
    }
    LOG.info("LIKE-FOR-LIKE comparison (Tier B only):")
    for r in rows:
        LOG.info(
            "    %-16s %-38s %5d / %6d = %6.3f%%  [%.3f-%.3f]",
            r["source"],
            r["basis"],
            r["green"],
            r["deals"],
            r["rate_pct"],
            r["ci_lo_pct"],
            r["ci_hi_pct"],
        )
    LOG.info(
        "    India vs Crunchbase-EM on Tier B: RR %.3f %s, p=%.4g",
        test.get("risk_ratio", float("nan")),
        test.get("risk_ratio_ci"),
        test["p_value"],
    )
    return findings


def run(cfg: Config | None = None) -> dict[str, Any]:
    """Classify the Indian window and summarise it, with its caveats attached."""
    cfg = cfg or load_config()
    cfg.ensure_dirs()
    seed_everything(cfg)

    df = prepare(cfg)
    labels = classify(df, cfg)
    df["green"] = labels["green"].to_numpy()
    df["green_subdomain"] = labels["green_subdomain"].to_numpy()
    df["year"] = df["funded_at"].dt.year

    dated = df.loc[df["funded_at"].notna()].copy()
    by_year = (
        dated.groupby("year")
        .agg(
            deals=("id", "size"),
            green_deals=("green", "sum"),
            green_usd_nominal=("amount_usd_nominal", lambda s: float(s.sum())),
        )
        .assign(green_rate_pct=lambda x: (100 * x["green_deals"] / x["deals"]).round(3))
        .reset_index()
    )
    green_by_year = (
        dated.loc[dated["green"]]
        .groupby("year")["amount_usd_nominal"]
        .agg(green_deals="size", green_usd=lambda s: float(s.sum()))
        .reset_index()
    )
    by_year = by_year.merge(green_by_year[["year", "green_usd"]], on="year", how="left")

    path = cfg.path("tables") / "fig12_india_continuity.csv"
    by_year.to_csv(path, index=False)
    write_parquet(dated, cfg.path("data_interim") / "india_classified.parquet")
    LOG.info("wrote %s", path.name)

    # Tier A cannot fire without a category_code, so every Indian green label is
    # Tier B. Stated rather than left for a reader to infer from a zero.
    findings: dict[str, Any] = {
        "rows": int(len(df)),
        "dated_rows": int(len(dated)),
        "green_deals": int(dated["green"].sum()),
        "green_rate_pct": round(100 * float(dated["green"].mean()), 3),
        "green_usd_nominal_m": round(
            float(dated.loc[dated["green"], "amount_usd_nominal"].sum()) / 1e6, 1
        ),
        "green_with_amount": int((dated["green"] & dated["amount_usd_nominal"].notna()).sum()),
        "year_min": int(dated["year"].min()),
        "year_max": int(dated["year"].max()),
        "by_year": by_year.to_dict("records"),
        "subdomains": dated.loc[dated["green"], "green_subdomain"].value_counts().to_dict(),
        "tier_a_applicable": False,
        "like_for_like": like_for_like(cfg, int(dated["green"].sum()), int(len(dated))),
        "caveats": [
            "Never pooled with the Crunchbase data: taxonomies and amount "
            "conventions are not compatible.",
            "No category_code field exists, so Tier A cannot fire and every label "
            "here is Tier B.",
            "A scrape of press reports, not a database export; coverage rules are "
            "unknown and almost certainly differ from Crunchbase's.",
            "The window ends in January 2020, so 2020 is a partial year and is "
            "excluded from any trend read.",
        ],
    }
    LOG.info(
        "India continuity probe: %d dated deals, %d green (%.2f%%), $%.1fm nominal, %d-%d",
        findings["dated_rows"],
        findings["green_deals"],
        findings["green_rate_pct"],
        findings["green_usd_nominal_m"],
        findings["year_min"],
        findings["year_max"],
    )
    LOG.info(
        "  green by year: %s", dict(zip(by_year["year"], by_year["green_deals"], strict=False))
    )

    out = cfg.path("data_interim") / "continuity_findings.json"
    out.write_text(json.dumps(findings, indent=2, default=str) + "\n", encoding="utf-8")
    return findings


if __name__ == "__main__":
    run()
