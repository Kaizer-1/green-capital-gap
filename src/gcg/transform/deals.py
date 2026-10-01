"""Build the canonical deal-level fact table: build step 5.

One row per funding round, carrying its green label, its time-varying bloc, its
instrument, its venture-stage flag, and both nominal and constant-2015-USD
amounts. Every row removed on the way is recorded in the attrition ledger, which
becomes Appendix E.

Two green specifications are carried side by side on every row:

- ``green`` — the raw classifier output. **This is the headline.** The
  classifier is symmetric by construction; it applies the same lexicon to every
  company regardless of bloc.
- ``green_curated`` — the raw output minus the ratified manual exclusions. This
  is a robustness run, reported alongside, because manual curation is *not*
  symmetric: the emerging-market green set was audited exhaustively while
  advanced-economy companies were audited only at the top of the funding
  distribution, and that asymmetry biases toward finding a gap.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from gcg.classify import blocs as blocs_mod
from gcg.classify import venture_stage as vs_mod
from gcg.config import Config, get_logger, load_config, seed_everything
from gcg.io import read_parquet, write_parquet
from gcg.ledger import Ledger
from gcg.transform.deflate import apply_deflator, build_deflator

LOG = get_logger("transform.deals")


def _apply_country_corrections(
    labels: pd.DataFrame, cfg: Config
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply ratified company-level country corrections.

    These are factual corrections to a wrong ``country_code``, not judgements
    about a company's business, and they move bloc assignment only.
    """
    corrections = cfg.blocs.get("company_country_corrections", {}) or {}
    out = labels.copy()
    applied: dict[str, Any] = {}
    for slug, spec in corrections.items():
        mask = out["permalink_norm"].astype("string").str.lower().eq(slug.lower())
        if mask.any():
            before = out.loc[mask, "country_code"].iloc[0]
            out.loc[mask, "country_code"] = spec["to"]
            applied[slug] = {
                "from": str(before),
                "to": spec["to"],
                "companies": int(mask.sum()),
            }
            LOG.info("country correction: %s %s -> %s", slug, before, spec["to"])
        else:
            LOG.warning("country correction for %r matched no company", slug)
    return out, applied


def build(cfg: Config | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build and persist the canonical deal table."""
    cfg = cfg or load_config()
    cfg.ensure_dirs()
    seed_everything(cfg)
    interim = cfg.path("data_interim")
    ledger = Ledger()

    rounds = read_parquet(interim / "cb_rounds.parquet")
    labels = read_parquet(interim / "green_labels.parquet")
    panel = read_parquet(interim / "bloc_panel.parquet")
    indicators = read_parquet(interim / "wb_indicators.parquet")

    labels, corrections = _apply_country_corrections(labels, cfg)

    df = rounds.copy()
    ledger.record(
        "ingest", "funding_rounds.csv as ingested", "starting population", len(df), len(df)
    )

    # ---- date validity -------------------------------------------------
    w = cfg.window
    df = ledger.apply(
        df,
        df["funded_at"].notna(),
        stage="dates",
        action="drop unparseable funded_at",
        reason="no usable deal date, so the row cannot be placed in the window or deflated",
    )
    df = ledger.apply(
        df,
        df["funded_at"].between(w["plausible_min"], w["plausible_max"]),
        stage="dates",
        action="drop implausible funded_at",
        reason=(
            f"date outside {w['plausible_min'][:4]}-{w['plausible_max'][:4]}, "
            "impossible for a 2013 snapshot"
        ),
    )

    # ---- company linkage ----------------------------------------------
    df = ledger.apply(
        df,
        df["object_id"].isin(set(labels["object_id"])),
        stage="linkage",
        action="drop orphan object_id",
        reason=(
            "no matching company in objects.csv, so no country, date of founding "
            "or green label"
        ),
    )

    # ---- deduplicate ---------------------------------------------------
    key = cfg.pipeline["dedupe_key"]
    key = [k if k != "funding_round_type" else "instrument" for k in key]
    before = len(df)
    df = df.drop_duplicates(subset=key, keep="first")
    ledger.record(
        "dedupe",
        "drop duplicates on " + "+".join(key),
        "identical company, date, instrument and amount",
        before,
        len(df),
    )

    # ---- attach company attributes -------------------------------------
    cols = [
        "object_id",
        "permalink_norm",
        "name",
        "country_code",
        "category_code",
        "founded_at",
        "status",
        "green",
        "green_curated",
        "manual_excluded",
        "manual_included",
        "green_strict_tier_a",
        "green_tier",
        "green_subdomain",
        "green_subdomains_all",
        "depends_on_gated_pattern",
        "tier_c_vetoed",
        "country_recovery_route",
        "taxonomy_tag_count",
        "has_taxonomy",
    ]
    before = len(df)
    df = df.merge(labels[cols], on="object_id", how="left")
    ledger.record(
        "join",
        "attach company attributes",
        "left join, must not change row count",
        before,
        len(df),
    )
    if len(df) != before:
        msg = f"the company join changed the row count from {before} to {len(df)}"
        raise RuntimeError(msg)

    # ---- window --------------------------------------------------------
    df["year"] = df["funded_at"].dt.year
    df["uncensored"] = df["funded_at"] > pd.Timestamp(w["end"])
    uncensored = df.loc[df["funded_at"].between(w["start"], w["uncensored_end"])].copy()

    df = ledger.apply(
        df,
        df["funded_at"].between(w["start"], w["end"]),
        stage="window",
        action=f"truncate to {w['start'][:4]}-{w['end'][:4]}",
        reason=(
            "coverage growth contaminates the final year, and the snapshot cut "
            "censors December 2013"
        ),
    )

    # ---- blocs ---------------------------------------------------------
    df["country_code"], code_stats = blocs_mod.normalise_country_code(df["country_code"], cfg)
    df, bloc_stats = blocs_mod.assign(df, panel, cfg)
    LOG.info(
        "blocs assigned; %d rows UNASSIGNED retained, never dropped", bloc_stats["unassigned"]
    )

    # ---- deflate -------------------------------------------------------
    spec = cfg.pipeline["deflate"]
    df = df.rename(columns={"raised_amount_usd": spec["nominal_column"]})
    multiplier = build_deflator(cfg, indicators)
    df, deflate_stats = apply_deflator(df, multiplier, cfg)

    # ---- venture stage -------------------------------------------------
    per_company = vs_mod.classify_companies(df, cfg)
    df = df.merge(
        per_company[["object_id", "venture_stage", "venture_stage_class"]],
        on="object_id",
        how="left",
    )

    # ---- persist -------------------------------------------------------
    out_path = cfg.path("data_processed") / "deals.parquet"
    write_parquet(df, out_path)
    write_parquet(uncensored, interim / "deals_uncensored.parquet")

    ledger_frame = ledger.to_frame()
    ledger_frame.to_csv(cfg.path("tables") / "appendix_e_attrition_ledger.csv", index=False)
    LOG.info("wrote appendix_e_attrition_ledger.csv (%d steps)", len(ledger_frame))

    vs_split = vs_mod.split_by_bloc(df)
    vs_split.to_csv(cfg.path("tables") / "diag_venture_stage_by_bloc.csv", index=False)
    vs_size = vs_mod.size_crosscheck(df, cfg)
    vs_size.to_csv(cfg.path("tables") / "diag_venture_stage_size_crosscheck.csv", index=False)

    findings: dict[str, Any] = {
        "attrition": ledger_frame.to_dict("records"),
        "attrition_summary": ledger.summary(),
        "country_corrections": corrections,
        "country_code_stats": code_stats,
        "bloc_stats": bloc_stats,
        "deflate": deflate_stats,
        "venture_stage_by_bloc": vs_split.to_dict("records"),
        "venture_stage_size_crosscheck": vs_size.to_dict("records"),
        "green_counts": {
            "raw_deals": int(df["green"].sum()),
            "curated_deals": int(df["green_curated"].sum()),
            "strict_tier_a_deals": int(df["green_strict_tier_a"].fillna(False).sum()),
        },
        "rows": int(len(df)),
    }
    path = interim / "deal_table_diagnostics.json"
    path.write_text(json.dumps(findings, indent=2, default=str) + "\n", encoding="utf-8")

    LOG.info(
        "canonical deal table: %d rows, %d green (raw), %d green (curated), %d green (strict)",
        len(df),
        findings["green_counts"]["raw_deals"],
        findings["green_counts"]["curated_deals"],
        findings["green_counts"]["strict_tier_a_deals"],
    )
    return df, findings


if __name__ == "__main__":
    build()
