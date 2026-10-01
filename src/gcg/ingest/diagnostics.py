"""Pre-analysis data diagnostics that constrain what the report may claim.

These are not exploratory scratch work. Each function here answers a specific
threat to validity raised before the deal table was built, writes a table to
``outputs/tables/`` for the appendix, and returns a findings dict. Running them
before ``transform/deals.py`` is deliberate: several of their answers decide
which specifications are permitted downstream.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from gcg.config import Config, get_logger, load_config
from gcg.io import read_parquet

LOG = get_logger("ingest.diagnostics")

# A single private venture round above this in nominal USD is implausible for
# 2000-2012 and is inspected rather than trusted.
_IMPLAUSIBLE_ROUND_USD = 5_000_000_000


def _save(cfg: Config, df: pd.DataFrame, name: str, *, index: bool = True) -> None:
    """Write a diagnostic table to outputs/tables as CSV."""
    path = cfg.path("tables") / f"{name}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index)
    LOG.info("wrote %-46s %d rows", path.name, len(df))


# ---------------------------------------------------------------------------
# 1. Censoring: seasonality and dollar backfill
# ---------------------------------------------------------------------------
def censoring_seasonality(cfg: Config, rounds: pd.DataFrame) -> dict[str, Any]:
    """Compare monthly deal counts across 2011, 2012 and 2013.

    December 2013's low count cannot be attributed to the snapshot cut without
    ruling out seasonality: if December is always weak, the 2013 dip says
    nothing about censoring.
    """
    df = rounds.loc[rounds["funded_at"].notna()].copy()
    df["year"] = df["funded_at"].dt.year
    df["month"] = df["funded_at"].dt.month
    sub = df.loc[df["year"].between(2011, 2013)]

    counts = sub.pivot_table(index="month", columns="year", values="id", aggfunc="size")
    counts.index.name = "month"

    # Each month as a share of its own year, so levels do not swamp shape.
    shares = counts.div(counts.sum(axis=0), axis=1) * 100

    dec_share = {int(y): float(shares.loc[12, y]) for y in counts.columns if 12 in shares.index}
    baseline = np.mean([v for y, v in dec_share.items() if y != 2013])
    dec_2013 = dec_share.get(2013, float("nan"))

    out = pd.concat(
        [counts.add_prefix("deals_"), shares.round(2).add_prefix("share_pct_")], axis=1
    )
    _save(cfg, out, "diag_censoring_monthly_counts")

    findings = {
        "december_share_pct": {str(k): round(v, 2) for k, v in dec_share.items()},
        "december_baseline_2011_2012_pct": round(float(baseline), 2),
        "december_2013_pct": round(float(dec_2013), 2),
        "december_2013_vs_baseline_ratio": round(float(dec_2013 / baseline), 3),
        "november_counts": {
            str(int(y)): int(counts.loc[11, y]) for y in counts.columns if 11 in counts.index
        },
    }
    LOG.info(
        "censoring/seasonality: December share of year = %s (2011-12 baseline %.2f%%, "
        "2013 %.2f%%, ratio %.2f)",
        findings["december_share_pct"],
        baseline,
        dec_2013,
        findings["december_2013_vs_baseline_ratio"],
    )
    return findings


def censoring_disclosure_backfill(cfg: Config, rounds: pd.DataFrame) -> dict[str, Any]:
    """Track the disclosed-amount rate by month across 2011-2013.

    Amounts backfill after a round is first entered, so deal *counts* can look
    complete while *dollars* are still censored. If 2013's disclosure rate is
    depressed relative to 2011-2012, a 2013-inclusive window is unusable for any
    dollar-denominated result.
    """
    df = rounds.loc[rounds["funded_at"].notna()].copy()
    df["year"] = df["funded_at"].dt.year
    df["month"] = df["funded_at"].dt.month
    df["disclosed"] = df["raised_amount_usd"].notna()
    sub = df.loc[df["year"].between(2011, 2013)]

    by_month = (
        sub.groupby(["year", "month"])["disclosed"].agg(deals="size", disclosed="sum").reset_index()
    )
    by_month["disclosed_pct"] = (100 * by_month["disclosed"] / by_month["deals"]).round(2)
    wide = by_month.pivot(index="month", columns="year", values="disclosed_pct")
    _save(cfg, wide, "diag_censoring_disclosure_by_month")

    by_year = sub.groupby("year")["disclosed"].agg(deals="size", disclosed="sum")
    by_year["disclosed_pct"] = (100 * by_year["disclosed"] / by_year["deals"]).round(2)
    _save(cfg, by_year, "diag_censoring_disclosure_by_year")

    rates = {int(y): float(by_year.loc[y, "disclosed_pct"]) for y in by_year.index}
    baseline = np.mean([v for y, v in rates.items() if y != 2013])
    depressed = bool(rates.get(2013, 100.0) < baseline - 2.0)

    findings = {
        "disclosed_pct_by_year": {str(k): v for k, v in rates.items()},
        "baseline_2011_2012_pct": round(float(baseline), 2),
        "y2013_pct": rates.get(2013),
        "y2013_depressed": depressed,
        "h2_2013_last_quarter_pct": [
            float(wide.loc[m, 2013]) for m in (10, 11, 12) if m in wide.index
        ],
    }
    LOG.info(
        "censoring/disclosure: by year %s; 2013 depressed vs baseline = %s",
        findings["disclosed_pct_by_year"],
        depressed,
    )
    return findings


# ---------------------------------------------------------------------------
# 2. Sentinel sweep
# ---------------------------------------------------------------------------
def amount_sentinel_sweep(cfg: Config, rounds_raw: pd.DataFrame) -> dict[str, Any]:
    """Confirm 0.0 is a null sentinel and sweep for other sentinel values.

    Called on the RAW amount column, before nulling, so the evidence for the
    null-encoding decision is recorded rather than assumed.
    """
    amt = pd.to_numeric(rounds_raw["raised_amount_usd"], errors="coerce")
    local = pd.to_numeric(rounds_raw["raised_amount"], errors="coerce")
    ccy = rounds_raw["raised_currency_code"]

    zeros = amt.eq(0)
    findings: dict[str, Any] = {
        "rows": int(len(amt)),
        "zero": int(zeros.sum()),
        "negative": int(amt.lt(0).sum()),
        "exactly_one": int(amt.eq(1).sum()),
        "under_1000_positive": int((amt.gt(0) & amt.lt(1000)).sum()),
        "above_implausible_threshold": int(amt.gt(_IMPLAUSIBLE_ROUND_USD).sum()),
        "implausible_threshold_usd": _IMPLAUSIBLE_ROUND_USD,
    }

    # Does a zero ever coexist with evidence of a real, non-zero round?
    findings["zero_with_positive_local_amount"] = int((zeros & local.gt(0)).sum())
    findings["zero_with_currency_code"] = int((zeros & ccy.notna()).sum())
    findings["zero_with_no_other_evidence"] = int((zeros & ~local.gt(0) & ccy.isna()).sum())

    # Repeated exact values are the signature of a placeholder.
    top = amt.loc[amt.gt(0)].value_counts().head(12)
    findings["most_repeated_positive_values"] = {
        f"{float(k):.0f}": int(v) for k, v in top.items()
    }

    big = rounds_raw.loc[amt.gt(_IMPLAUSIBLE_ROUND_USD)]
    if len(big):
        cols = [c for c in ("object_id", "funded_at", "funding_round_code") if c in big.columns]
        exhibit = big[cols].assign(raised_amount_usd=amt.loc[big.index])
        _save(cfg, exhibit, "diag_implausible_round_amounts", index=False)
        findings["implausible_examples"] = exhibit.head(10).to_dict("records")

    dist = (
        amt.loc[amt.gt(0)]
        .describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99])
        .round(0)
        .to_dict()
    )
    findings["positive_amount_distribution"] = {k: float(v) for k, v in dist.items()}

    LOG.info(
        "sentinel sweep: zero=%d (local>0: %d, ccy set: %d, no evidence: %d) | "
        "negative=%d | ==1=%d | <1000=%d | >$%.0fbn=%d",
        findings["zero"],
        findings["zero_with_positive_local_amount"],
        findings["zero_with_currency_code"],
        findings["zero_with_no_other_evidence"],
        findings["negative"],
        findings["exactly_one"],
        findings["under_1000_positive"],
        _IMPLAUSIBLE_ROUND_USD / 1e9,
        findings["above_implausible_threshold"],
    )
    return findings


def fx_failure_profile(
    cfg: Config, rounds_raw: pd.DataFrame, companies: pd.DataFrame
) -> dict[str, Any]:
    """Profile the zero-USD rows that carry a positive local-currency amount.

    If these skew toward emerging-market countries they are another line in the
    bias ledger, not a neutral data-quality quirk. Bloc assignment is not yet
    built, so this reports by currency and by country, and the formal bloc split
    is produced at step 4.
    """
    amt = pd.to_numeric(rounds_raw["raised_amount_usd"], errors="coerce")
    local = pd.to_numeric(rounds_raw["raised_amount"], errors="coerce")
    fx_fail = amt.eq(0) & local.gt(0)

    sub = rounds_raw.loc[fx_fail, ["object_id", "raised_currency_code", "funded_at"]].copy()
    sub = sub.merge(
        companies[["id", "country_code"]].rename(columns={"id": "object_id"}),
        on="object_id",
        how="left",
    )

    by_ccy = sub["raised_currency_code"].value_counts(dropna=False)
    by_country = sub["country_code"].value_counts(dropna=False).head(15)

    # Benchmark: the country mix of all deals, so skew is measurable not asserted.
    allc = (
        rounds_raw[["object_id"]]
        .merge(
            companies[["id", "country_code"]].rename(columns={"id": "object_id"}),
            on="object_id",
            how="left",
        )["country_code"]
        .value_counts(dropna=False)
    )
    comparison = pd.DataFrame(
        {
            "fx_fail_deals": by_country,
            "fx_fail_pct": (100 * by_country / by_country.sum()).round(2),
            "all_deals_pct": (100 * allc.reindex(by_country.index) / allc.sum()).round(2),
        }
    )
    comparison["skew_ratio"] = (comparison["fx_fail_pct"] / comparison["all_deals_pct"]).round(2)
    _save(cfg, comparison, "diag_fx_failures_by_country")
    _save(cfg, by_ccy.to_frame("deals"), "diag_fx_failures_by_currency")

    usa_share_fx = float(comparison["fx_fail_pct"].get("USA", 0.0))
    usa_share_all = float(comparison["all_deals_pct"].get("USA", 0.0))

    findings = {
        "fx_failures": int(fx_fail.sum()),
        "by_currency": {str(k): int(v) for k, v in by_ccy.head(12).items()},
        "usa_share_of_fx_failures_pct": usa_share_fx,
        "usa_share_of_all_deals_pct": usa_share_all,
        "non_usa_concentration": round(
            (100 - usa_share_fx) / max(100 - usa_share_all, 1e-9), 3
        ),
        "top_countries": comparison.head(10).reset_index().to_dict("records"),
    }
    LOG.info(
        "fx failures: n=%d | USA %.1f%% of FX failures vs %.1f%% of all deals "
        "-> non-US over-represented by %.2fx",
        findings["fx_failures"],
        usa_share_fx,
        usa_share_all,
        findings["non_usa_concentration"],
    )
    return findings


# ---------------------------------------------------------------------------
# 3. Instrument field disagreement (appendix exhibit)
# ---------------------------------------------------------------------------
def instrument_contingency(cfg: Config, rounds_raw: pd.DataFrame) -> dict[str, Any]:
    """Cross-tabulate funding_round_type against funding_round_code.

    The appendix exhibit behind the decision to normalise from the code field.
    The type field collapses seed into angel and buries grant and debt_round in
    an ``other`` bucket; this table is the evidence.
    """
    ct = pd.crosstab(
        rounds_raw["funding_round_type"].fillna("<missing>"),
        rounds_raw["funding_round_code"].fillna("<missing>"),
    )
    _save(cfg, ct, "appendix_instrument_type_x_code")

    rt = cfg.pipeline["round_types"]
    primary = rounds_raw[rt["primary_field"]].astype("string").str.strip().str.lower()
    fallback = rounds_raw[rt["fallback_field"]].astype("string").str.strip().str.lower()
    mapped = primary.map(rt["normalise"])
    fb = fallback.map(rt["normalise_fallback"])
    conflict = mapped.notna() & fb.notna() & mapped.ne(fb)

    detail = (
        pd.DataFrame({"code_canonical": mapped[conflict], "type_canonical": fb[conflict]})
        .value_counts()
        .reset_index(name="deals")
        .sort_values("deals", ascending=False)
    )
    _save(cfg, detail, "appendix_instrument_conflicts", index=False)

    findings = {
        "conflict_rows": int(conflict.sum()),
        "conflict_share": round(float(conflict.mean()), 4),
        "top_conflicts": detail.head(8).to_dict("records"),
        "type_values": int(rounds_raw["funding_round_type"].nunique()),
        "code_values": int(rounds_raw["funding_round_code"].nunique()),
    }
    LOG.info(
        "instrument contingency: %d type values x %d code values, %d conflicting rows (%.1f%%)",
        findings["type_values"],
        findings["code_values"],
        findings["conflict_rows"],
        100 * findings["conflict_share"],
    )
    return findings


# ---------------------------------------------------------------------------
# 4. Mirror vintage and relational completeness
# ---------------------------------------------------------------------------
def mirror_vintage(
    cfg: Config, rounds: pd.DataFrame, companies: pd.DataFrame, flat: pd.DataFrame
) -> dict[str, Any]:
    """Establish whether the two Kaggle datasets are the same snapshot vintage.

    CLAUDE.md §4 describes them as "two Kaggle mirrors of the same underlying
    snapshot". They are not, and the difference bounds what the deal table can
    claim to be a complete census of.
    """
    rel_max = rounds["funded_at"].max()
    flat_last = pd.to_datetime(flat["last_funding_at"], errors="coerce")

    funded_ids = set(rounds["object_id"].dropna())
    funded = companies.loc[companies["id"].isin(funded_ids)]
    matched_slugs = set(funded["permalink_norm"].dropna()) & set(flat["permalink_norm"].dropna())
    all_slugs = set(companies["permalink_norm"].dropna())

    flat_only = flat.loc[
        flat["permalink_norm"].notna() & ~flat["permalink_norm"].isin(matched_slugs)
    ]
    fo_last = pd.to_datetime(flat_only["last_funding_at"], errors="coerce")
    in_objects = flat_only["permalink_norm"].isin(all_slugs)

    # Companies the relational dump lists but gives no rounds for, which the flat
    # file says were funded before the snapshot closed: genuine census gaps.
    gap = flat_only.loc[in_objects & (fo_last < rel_max)]
    gap_dollars = pd.to_numeric(gap["funding_total_usd_flat"], errors="coerce").sum()

    # Round-count comparison on matched companies.
    rel_counts = rounds.groupby("object_id").size().rename("rel_rounds")
    comp = (
        funded[["id", "permalink_norm"]]
        .merge(rel_counts, left_on="id", right_index=True)
        .merge(
            flat[["permalink_norm", "funding_rounds", "last_funding_at"]],
            on="permalink_norm",
            how="inner",
        )
    )
    comp["flat_rounds"] = pd.to_numeric(comp["funding_rounds"], errors="coerce")
    comp["surplus"] = comp["flat_rounds"] - comp["rel_rounds"]
    comp["last"] = pd.to_datetime(comp["last_funding_at"], errors="coerce")

    surplus = comp.loc[comp["surplus"] > 0]
    post_snapshot = surplus["last"] >= rel_max
    unexplained = surplus.loc[~post_snapshot, "surplus"].sum()

    exhibit = pd.DataFrame(
        {
            "metric": [
                "relational max funded_at",
                "flat max last_funding_at",
                "flat-only companies",
                "flat-only absent from objects.csv",
                "flat-only in objects.csv but no deal rows",
                "of those, last funded before snapshot close",
                "claimed funding of that gap (USD bn)",
                "matched companies",
                "matched: flat reports more rounds",
                "matched: equal round counts",
                "matched: flat reports fewer",
                "surplus rounds claimed by flat",
                "surplus explained by post-snapshot activity",
                "surplus NOT explained by timing",
            ],
            "value": [
                str(rel_max)[:10],
                str(flat_last.max())[:10],
                len(flat_only),
                int((~in_objects).sum()),
                int(in_objects.sum()),
                len(gap),
                round(gap_dollars / 1e9, 2),
                len(comp),
                int((comp["surplus"] > 0).sum()),
                int((comp["surplus"] == 0).sum()),
                int((comp["surplus"] < 0).sum()),
                int(surplus["surplus"].sum()),
                int(surplus.loc[post_snapshot, "surplus"].sum()),
                int(unexplained),
            ],
        }
    )
    _save(cfg, exhibit, "appendix_mirror_vintage", index=False)

    findings = {
        "relational_max_funded_at": str(rel_max)[:10],
        "flat_max_last_funding_at": str(flat_last.max())[:10],
        "same_vintage": bool(flat_last.max() <= rel_max),
        "flat_only_companies": len(flat_only),
        "flat_only_absent_from_objects": int((~in_objects).sum()),
        "census_gap_companies": len(gap),
        "census_gap_claimed_usd_bn": round(float(gap_dollars) / 1e9, 2),
        "matched_companies": len(comp),
        "surplus_rounds_total": int(surplus["surplus"].sum()),
        "surplus_explained_post_snapshot": int(surplus.loc[post_snapshot, "surplus"].sum()),
        "surplus_unexplained": int(unexplained),
        "surplus_unexplained_share_of_deals": round(float(unexplained) / len(rounds), 4),
    }
    LOG.info(
        "mirror vintage: relational to %s, flat to %s -> same vintage = %s",
        findings["relational_max_funded_at"],
        findings["flat_max_last_funding_at"],
        findings["same_vintage"],
    )
    LOG.info(
        "relational completeness: %d census-gap companies ($%.2fbn claimed), "
        "%d surplus rounds of which %d unexplained by timing (%.1f%% of deals)",
        findings["census_gap_companies"],
        findings["census_gap_claimed_usd_bn"],
        findings["surplus_rounds_total"],
        findings["surplus_unexplained"],
        100 * findings["surplus_unexplained_share_of_deals"],
    )
    return findings


# ---------------------------------------------------------------------------
def run(cfg: Config | None = None) -> dict[str, Any]:
    """Run every pre-analysis diagnostic and persist the findings."""
    cfg = cfg or load_config()
    cfg.ensure_dirs()
    interim = cfg.path("data_interim")

    rounds = read_parquet(interim / "cb_rounds.parquet")
    companies = read_parquet(interim / "cb_companies.parquet")
    flat = read_parquet(interim / "cb_flat.parquet")

    # The sentinel sweep and FX profile need the amounts BEFORE nulling, so
    # re-read the raw CSV rather than the already-cleaned interim table.
    raw_rounds = pd.read_csv(
        cfg.path("data_raw") / "funding_rounds.csv",
        usecols=[
            "object_id",
            "funded_at",
            "funding_round_type",
            "funding_round_code",
            "raised_amount_usd",
            "raised_amount",
            "raised_currency_code",
        ],
        low_memory=False,
    )

    findings = {
        "censoring_seasonality": censoring_seasonality(cfg, rounds),
        "censoring_disclosure": censoring_disclosure_backfill(cfg, rounds),
        "amount_sentinels": amount_sentinel_sweep(cfg, raw_rounds),
        "fx_failures": fx_failure_profile(cfg, raw_rounds, companies),
        "instrument_contingency": instrument_contingency(cfg, raw_rounds),
        "mirror_vintage": mirror_vintage(cfg, rounds, companies, flat),
    }

    path = interim / "preanalysis_diagnostics.json"
    path.write_text(json.dumps(findings, indent=2, default=str) + "\n", encoding="utf-8")
    LOG.info("wrote %s", path.name)
    return findings


if __name__ == "__main__":
    run()
