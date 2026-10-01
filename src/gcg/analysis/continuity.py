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
