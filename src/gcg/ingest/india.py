"""Ingest Indian startup funding 2015-2020 for the continuity probe.

Used for ONE thing: report §7's test of whether the structural pattern found in
2000-2012 still appears in a later window in one large emerging market. It is
never pooled with the Crunchbase data; the taxonomies and amount conventions are
not compatible (CLAUDE.md §4, RESEARCH_BRIEF §6).
"""

from __future__ import annotations

import pandas as pd

from gcg.config import Config, get_logger
from gcg.io import SourceRecord, download_kaggle, read_csv_strict, sha256_file, write_parquet

LOG = get_logger("ingest.india")


def ingest(cfg: Config) -> tuple[dict[str, pd.DataFrame], list[SourceRecord], dict[str, dict]]:
    """Download and lightly normalise the Indian funding dataset."""
    src = cfg.source("india")
    raw = cfg.path("data_raw")

    paths = download_kaggle(cfg, src["handle"])
    if not paths:
        # The handle ships a single CSV whose name has changed across versions,
        # so resolve it by pattern rather than hard-coding a filename.
        candidates = sorted(raw.glob("*ndian*tartup*.csv")) or sorted(
            raw.glob("startup_funding*.csv")
        )
        if not candidates:
            present = sorted(p.name for p in raw.iterdir() if p.suffix == ".csv")
            msg = (
                f"Indian funding CSV not found after downloading {src['handle']}.\n"
                f"  CSVs in data/raw: {present}\n"
                "Build stopped."
            )
            raise RuntimeError(msg)
        paths = candidates[:1]

    path = paths[0]
    LOG.info("reading %s", path.name)
    df = read_csv_strict(path, encoding="utf-8")
    LOG.info("india raw columns: %s", list(df.columns))

    df = df.dropna(how="all").copy()
    rename = {
        "Sr No": "sr_no",
        "Date dd/mm/yyyy": "date_raw",
        "Date": "date_raw",
        "Startup Name": "startup",
        "Industry Vertical": "industry",
        "SubVertical": "subvertical",
        "City  Location": "city",
        "City Location": "city",
        "Investors Name": "investors",
        "InvestmentnType": "investment_type_raw",
        "InvestmentType": "investment_type_raw",
        "Amount in USD": "amount_usd_raw",
        "Remarks": "remarks",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    # Dates in this scrape are dd/mm/yyyy with a scattering of typos
    # ('05/072018', '01/07/015'). Parsed non-strictly; failures are counted and
    # reported, never guessed at.
    if "date_raw" in df.columns:
        df["funded_at"] = pd.to_datetime(
            df["date_raw"].astype("string").str.strip(), dayfirst=True, errors="coerce"
        )
    else:
        msg = f"no date column found in {path.name}; columns: {list(df.columns)}"
        raise RuntimeError(msg)

    from gcg.ingest.crunchbase import coerce_usd

    df["amount_usd_nominal"], amount_stats = coerce_usd(
        df["amount_usd_raw"], label="india.amount_usd"
    )

    stats = {
        "rows": int(len(df)),
        "unparseable_dates": int(df["funded_at"].isna().sum()),
        "date_min": str(df["funded_at"].min()),
        "date_max": str(df["funded_at"].max()),
        "amount": amount_stats,
        "distinct_startups": int(df["startup"].nunique()) if "startup" in df else None,
        "investment_types": (
            df["investment_type_raw"]
            .astype("string")
            .str.strip()
            .str.lower()
            .value_counts()
            .head(10)
            .to_dict()
            if "investment_type_raw" in df
            else {}
        ),
    }
    LOG.info(
        "india: %d rows, %d unparseable dates, %s to %s",
        stats["rows"],
        stats["unparseable_dates"],
        stats["date_min"][:10],
        stats["date_max"][:10],
    )

    write_parquet(df, cfg.path("data_interim") / "india_funding.parquet")

    rec = [
        SourceRecord(
            source="india",
            filename=path.name,
            origin=f"Kaggle dataset `{src['handle']}`",
            licence=src["licence"],
            sha256=sha256_file(path),
            size_bytes=path.stat().st_size,
            fetched_at=_mtime(path),
            rows=len(df),
            # The note is config's to state; prefixing it here duplicated the
            # sentence in the manifest.
            note=src.get("notes", ""),
        )
    ]
    return {"india_funding": df}, rec, stats


def _mtime(path) -> str:
    """ISO-8601 UTC modification time of a cached file."""
    from datetime import UTC, datetime

    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
