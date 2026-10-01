"""Ingest the Crunchbase 2013 Snapshot from its two Kaggle mirrors.

The relational mirror (``justinas/startup-investments``) carries deal-level rows
but only a coarse single-bucket ``category_code``. The flat mirror
(``arindam235/startup-investments-crunchbase``) carries the rich pipe-delimited
``category_list`` but no deal dates. Joining them on a normalised permalink is
what makes a deal-level green analysis possible at all (CLAUDE.md §4).

This module does ingestion and *light* normalisation only: encoding, column-name
stripping, permalink normalisation and numeric coercion. Date clipping,
deduplication and the attrition ledger belong to ``transform/deals.py`` (step 5).
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from gcg.config import Config, get_logger
from gcg.io import SourceRecord, download_kaggle, read_csv_strict, sha256_file, write_parquet

LOG = get_logger("ingest.crunchbase")

# Columns we need from objects.csv. It is a 285MB file; reading all of it costs
# minutes and gigabytes for no benefit.
_OBJECT_COLS = [
    "id",
    "entity_type",
    "permalink",
    "name",
    "category_code",
    "status",
    "founded_at",
    "closed_at",
    "country_code",
    "state_code",
    "region",
    "city",
    "homepage_url",
    "domain",
    "funding_total_usd",
    "funding_rounds",
    "first_funding_at",
    "last_funding_at",
    "tag_list",
    "short_description",
    "description",
    "overview",
]

_ROUND_COLS = [
    "id",
    "funding_round_id",
    "object_id",
    "funded_at",
    "funding_round_type",
    "funding_round_code",
    "raised_amount_usd",
    "raised_amount",
    "raised_currency_code",
    "pre_money_valuation_usd",
    "post_money_valuation_usd",
    "participants",
    "is_first_round",
    "is_last_round",
]

_PERMALINK_PREFIX = re.compile(r"^/?(?:organization|company|org)/")


def normalise_permalink(series: pd.Series) -> pd.Series:
    """Normalise Crunchbase permalinks so the two mirrors can be joined.

    Lowercases, strips whitespace, removes the ``/organization/`` or ``/company/``
    prefix and any surrounding slashes. CLAUDE.md §4 requires this before any
    comparison; the two mirrors use different prefix conventions.

    Parameters
    ----------
    series
        Raw permalink strings.

    Returns
    -------
    pandas.Series
        Normalised slugs, with empty strings as ``pd.NA``.
    """
    out = (
        series.astype("string")
        .str.strip()
        .str.lower()
        .str.replace(_PERMALINK_PREFIX, "", regex=True)
        .str.strip("/")
        .str.strip()
    )
    return out.replace({"": pd.NA, "nan": pd.NA})


def coerce_usd(
    series: pd.Series,
    *,
    label: str,
    zero_is_null: bool = False,
    local_amount: pd.Series | None = None,
) -> tuple[pd.Series, dict[str, Any]]:
    """Coerce a money column to float, handling separators, ``-`` nulls and zero-as-null.

    Two distinct traps are handled here.

    First, CLAUDE.md §7: ``funding_total_usd`` in the flat mirror is a *string*
    with comma thousands separators and a bare ``-`` for null. A plain
    ``pd.to_numeric`` silently nulls every one of those rows.

    Second, established at build step 2: in the relational mirror an undisclosed
    amount is encoded as a literal ``0.0``, not as NaN. 6,000 of 52,928 deal rows
    are zeros. Treating those as disclosed $0 rounds would drag every median,
    IQR and dollar total toward zero. With ``zero_is_null`` the zeros become NaN
    and are counted, never imputed.

    Parameters
    ----------
    series
        The raw column.
    label
        Name used in the log line.
    zero_is_null
        Treat ``0`` as undisclosed rather than as a disclosed zero amount.
    local_amount
        Optional local-currency amount column. Where the USD value is zero but a
        positive local amount exists, the row is a currency-conversion failure
        rather than an undisclosed deal, and is counted separately. Such rows are
        NOT back-converted; that would require an unvetted historical FX source.

    Returns
    -------
    tuple[pandas.Series, dict]
        The coerced float series, and a count dict for the attrition ledger.
    """
    raw = series.astype("string").str.strip()
    blank = raw.isna() | raw.isin({"", "-", "—", "–", "n/a", "N/A", "nan", "NaN"})

    cleaned = (
        raw.str.replace(",", "", regex=False).str.replace("$", "", regex=False).str.strip()
    )
    cleaned = cleaned.mask(blank)
    numeric = pd.to_numeric(cleaned, errors="coerce")

    failed = (~blank) & numeric.isna()
    stats: dict[str, Any] = {
        "total": int(len(series)),
        "blank_or_dash": int(blank.sum()),
        "uncoercible": int(failed.sum()),
    }

    if zero_is_null:
        zeros = numeric.eq(0)
        stats["zero_encoded_null"] = int(zeros.sum())
        if local_amount is not None:
            local = pd.to_numeric(local_amount, errors="coerce")
            fx_fail = zeros & local.gt(0)
            stats["fx_conversion_failures"] = int(fx_fail.sum())
            stats["genuinely_undisclosed"] = int((zeros & ~fx_fail).sum())
        numeric = numeric.mask(zeros)

    stats["coerced_ok"] = int(numeric.notna().sum())
    stats["disclosed_share"] = round(stats["coerced_ok"] / max(stats["total"], 1), 4)

    LOG.info(
        "coerce %-26s total=%-7d disclosed=%-7d blank/dash=%-6d "
        "zero-as-null=%-6s uncoercible=%d",
        label,
        stats["total"],
        stats["coerced_ok"],
        stats["blank_or_dash"],
        stats.get("zero_encoded_null", "-"),
        stats["uncoercible"],
    )
    if stats.get("fx_conversion_failures"):
        LOG.warning(
            "  %s: %d rows have a positive local-currency amount but no USD conversion "
            "(counted separately, not back-converted)",
            label,
            stats["fx_conversion_failures"],
        )
    if stats["uncoercible"]:
        examples = raw[failed].dropna().unique()[:5].tolist()
        LOG.warning("  uncoercible %s examples: %s", label, examples)
    return numeric.astype("float64"), stats


def ingest(cfg: Config) -> tuple[dict[str, pd.DataFrame], list[SourceRecord], dict[str, dict]]:
    """Download both mirrors and write normalised interim tables.

    Returns
    -------
    tuple
        ``(tables, records, stats)`` where ``tables`` maps a short name to the
        interim dataframe, ``records`` is manifest provenance, and ``stats``
        holds per-table diagnostics for the step-2 report.
    """
    raw = cfg.path("data_raw")
    interim = cfg.path("data_interim")
    records: list[SourceRecord] = []
    stats: dict[str, dict] = {}

    # -- relational mirror -------------------------------------------------
    rel = cfg.source("cb_relational")
    download_kaggle(cfg, rel["handle"], rel["expect_files"])

    LOG.info("reading funding_rounds.csv")
    rounds = read_csv_strict(
        raw / "funding_rounds.csv", usecols=lambda c: c.strip() in _ROUND_COLS
    )
    LOG.info("reading objects.csv (285MB, selected columns only)")
    objects = read_csv_strict(raw / "objects.csv", usecols=lambda c: c.strip() in _OBJECT_COLS)

    for name in rel["expect_files"]:
        path = raw / name
        n = len(rounds) if name == "funding_rounds.csv" else len(objects)
        records.append(
            SourceRecord(
                source="cb_relational",
                filename=name,
                origin=f"Kaggle dataset `{rel['handle']}` (Crunchbase 2013 Snapshot)",
                licence=rel["licence"],
                sha256=sha256_file(path),
                size_bytes=path.stat().st_size,
                fetched_at=_mtime(path),
                rows=n,
                note=rel.get("notes", ""),
            )
        )

    # Companies only. objects.csv also holds people, financial orgs and products.
    companies = objects.loc[
        objects["entity_type"].astype("string").str.lower() == "company"
    ].copy()
    LOG.info(
        "objects.csv entity_type split: %s",
        objects["entity_type"].value_counts().to_dict(),
    )
    companies["permalink_norm"] = normalise_permalink(companies["permalink"])
    amt_cfg = cfg.pipeline["amounts"]
    companies["funding_total_usd_rel"], stats["objects_funding_total"] = coerce_usd(
        companies["funding_total_usd"],
        label="objects.funding_total_usd",
        zero_is_null=amt_cfg["zero_means_undisclosed"],
    )

    rounds["raised_amount_usd"], stats["rounds_raised_amount"] = coerce_usd(
        rounds["raised_amount_usd"],
        label="rounds.raised_amount_usd",
        zero_is_null=amt_cfg["zero_means_undisclosed"],
        local_amount=rounds[amt_cfg["local_amount_field"]]
        if amt_cfg["track_fx_conversion_failures"]
        else None,
    )

    rounds["instrument"], stats["instruments"] = normalise_instrument(rounds, cfg)
    # funded_at is parsed but NOT clipped here; clipping is a step-5 ledger event.
    rounds["funded_at"] = pd.to_datetime(rounds["funded_at"], errors="coerce")
    stats["rounds_dates"] = {
        "total": int(len(rounds)),
        "unparseable_funded_at": int(rounds["funded_at"].isna().sum()),
        "min": str(rounds["funded_at"].min()),
        "max": str(rounds["funded_at"].max()),
    }

    # -- flat mirror -------------------------------------------------------
    flat_cfg = cfg.source("cb_flat")
    download_kaggle(cfg, flat_cfg["handle"], flat_cfg["expect_files"])
    LOG.info("reading investments_VC.csv (encoding=%s)", flat_cfg["encoding"])
    flat = read_csv_strict(raw / "investments_VC.csv", encoding=flat_cfg["encoding"])

    # The flat file ships with fully-blank trailing rows and unnamed columns.
    before = len(flat)
    flat = flat.dropna(how="all").copy()
    flat = flat.loc[:, ~flat.columns.str.match(r"^Unnamed")]
    LOG.info(
        "flat mirror: dropped %d all-blank rows, %d cols retained",
        before - len(flat),
        flat.shape[1],
    )

    flat["permalink_norm"] = normalise_permalink(flat["permalink"])
    flat["funding_total_usd_flat"], stats["flat_funding_total"] = coerce_usd(
        flat["funding_total_usd"],
        label="flat.funding_total_usd",
        zero_is_null=amt_cfg["zero_means_undisclosed"],
    )

    path = raw / "investments_VC.csv"
    records.append(
        SourceRecord(
            source="cb_flat",
            filename="investments_VC.csv",
            origin=f"Kaggle dataset `{flat_cfg['handle']}` "
            "(Crunchbase 2013 Snapshot, flat mirror)",
            licence=flat_cfg["licence"],
            sha256=sha256_file(path),
            size_bytes=path.stat().st_size,
            fetched_at=_mtime(path),
            rows=len(flat),
            note=f"Read as {flat_cfg['encoding']}; column names stripped on load. "
            + flat_cfg.get("notes", ""),
        )
    )

    # Deal rows whose object_id matches no company in objects.csv. Referential
    # orphans: they cannot be given a country, a date-of-founding or a green
    # label, so they are an attrition-ledger line, not a silent drop.
    all_object_ids = set(objects["id"])
    orphan = ~rounds["object_id"].isin(all_object_ids)
    non_company = rounds["object_id"].isin(set(objects["id"])) & ~rounds["object_id"].isin(
        set(companies["id"])
    )
    stats["rounds_linkage"] = {
        "deals_total": int(len(rounds)),
        "orphan_object_id": int(orphan.sum()),
        "object_id_not_a_company": int(non_company.sum()),
        "linkable_to_company": int((~orphan & ~non_company).sum()),
    }
    LOG.info(
        "linkage: %d deals, %d orphan object_id, %d point at non-company entities",
        len(rounds),
        int(orphan.sum()),
        int(non_company.sum()),
    )

    # -- join diagnostic ---------------------------------------------------
    stats["join"] = _join_diagnostic(cfg, companies, flat, rounds)

    # -- persist -----------------------------------------------------------
    tables = {
        "cb_rounds": rounds,
        "cb_companies": companies,
        "cb_flat": flat,
    }
    for name, df in tables.items():
        write_parquet(df, interim / f"{name}.parquet")

    return tables, records, stats


def _join_diagnostic(
    cfg: Config, companies: pd.DataFrame, flat: pd.DataFrame, rounds: pd.DataFrame
) -> dict:
    """Measure the permalink join rate and fail if it is below the configured floor.

    CLAUDE.md §4: report the join rate, investigate and document the non-matches
    rather than silently dropping them.

    The denominator is companies that have at least one deal row, NOT every
    company in ``objects.csv``. Of the 196,553 companies in the relational
    mirror only 31,707 ever raised a recorded round, while the flat mirror
    contains funded companies only. Measuring against all companies understates
    the join rate by a factor of five and says nothing about the data that
    actually enters the analysis.
    """
    funded_ids = set(rounds["object_id"].dropna())
    funded = companies.loc[companies["id"].isin(funded_ids)]

    left = set(funded["permalink_norm"].dropna())
    right = set(flat["permalink_norm"].dropna())
    matched = left & right

    # Deal-weighted rate matters too: a company with eight rounds counts eight
    # times in the analysis.
    matched_ids = set(funded.loc[funded["permalink_norm"].isin(matched), "id"])
    deals_matched = int(rounds["object_id"].isin(matched_ids).sum())

    rate_companies = len(matched) / len(left) if left else 0.0
    rate_deals = deals_matched / len(rounds) if len(rounds) else 0.0

    diag = {
        "companies_relational_all": int(len(companies)),
        "companies_relational_funded": len(left),
        "companies_flat": len(right),
        "companies_matched": len(matched),
        "join_rate_companies": round(rate_companies, 4),
        "deals_total": int(len(rounds)),
        "deals_on_matched_companies": deals_matched,
        "join_rate_deals": round(rate_deals, 4),
        "funded_relational_only": len(left - right),
        "flat_only": len(right - left),
    }
    LOG.info(
        "JOIN  funded companies %d/%d = %.1f%%   |   deals %d/%d = %.1f%%",
        len(matched),
        len(left),
        100 * rate_companies,
        deals_matched,
        len(rounds),
        100 * rate_deals,
    )
    LOG.info(
        "      non-matches: %d funded-relational-only (no rich category_list), "
        "%d flat-only (no deal rows)",
        len(left - right),
        len(right - left),
    )

    floor = float(cfg.threshold("join_rate_floor"))
    if rate_companies < floor:
        msg = (
            f"permalink join rate {rate_companies:.1%} is below the configured floor "
            f"{floor:.0%}. The join is the methodological core of this project; "
            "proceeding on a bad join would corrupt every green label. "
            "Investigate the permalink normalisation before continuing."
        )
        raise RuntimeError(msg)
    return diag


def normalise_instrument(
    rounds: pd.DataFrame, cfg: Config
) -> tuple[pd.Series, dict[str, Any]]:
    """Map raw round codes to canonical instrument labels.

    ``funding_round_code`` is the primary field; ``funding_round_type`` is a
    fallback for rows where the code is absent. Established at step 2: the type
    field is a coarse rollup that collapses ``seed`` into ``angel`` and buries
    ``grant`` and ``debt_round`` in an ``other`` bucket, so normalising from it
    would leave H3 untestable and H4 unmeasurable.

    Returns
    -------
    tuple[pandas.Series, dict]
        Canonical instrument labels, and diagnostics including the count of rows
        where the two source fields disagree.
    """
    rt = cfg.pipeline["round_types"]
    primary = rounds[rt["primary_field"]].astype("string").str.strip().str.lower()
    fallback = rounds[rt["fallback_field"]].astype("string").str.strip().str.lower()

    mapped = primary.map(rt["normalise"])
    from_fallback = fallback.map(rt["normalise_fallback"])
    instrument = mapped.fillna(from_fallback).fillna("unknown")

    unmapped_primary = sorted(primary[mapped.isna() & primary.notna()].unique())
    unmapped_fallback = sorted(
        fallback[mapped.isna() & from_fallback.isna() & fallback.notna()].unique()
    )

    # Where both fields carry a stage signal and they disagree, the code wins.
    # The count is a methodology line, not something to bury.
    both = mapped.notna() & from_fallback.notna()
    conflict = both & mapped.ne(from_fallback)

    stats: dict[str, Any] = {
        "rows": int(len(rounds)),
        "from_primary_code": int(mapped.notna().sum()),
        "from_fallback_type": int((mapped.isna() & from_fallback.notna()).sum()),
        "unknown": int(instrument.eq("unknown").sum()),
        "unmapped_primary_values": unmapped_primary,
        "unmapped_fallback_values": unmapped_fallback,
        "code_type_conflicts": int(conflict.sum()),
        "instrument_counts": instrument.value_counts().to_dict(),
    }
    LOG.info(
        "instrument: %d from code, %d from type fallback, %d unknown, %d code/type conflicts",
        stats["from_primary_code"],
        stats["from_fallback_type"],
        stats["unknown"],
        stats["code_type_conflicts"],
    )
    if unmapped_primary or unmapped_fallback:
        LOG.warning(
            "unmapped instrument values (add to pipeline.yaml round_types): code=%s type=%s",
            unmapped_primary,
            unmapped_fallback,
        )
    if conflict.any():
        examples = (
            pd.DataFrame({"code": primary[conflict], "type": fallback[conflict]})
            .value_counts()
            .head(5)
            .to_dict()
        )
        LOG.info("  top code/type conflicts: %s", examples)

    return instrument.astype("string"), stats


def _mtime(path) -> str:
    """ISO-8601 UTC modification time of a cached file."""
    from datetime import UTC, datetime

    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
