"""Ingest World Bank and Our World in Data enrichment layers.

All open, no authentication. Supplies the time-varying income groups that drive
bloc assignment (CLAUDE.md §5), the US GDP deflator for the constant-dollar
conversion (§7), and the H5 need indicators.
"""

from __future__ import annotations

import pandas as pd

from gcg.config import Config, get_logger
from gcg.io import (
    SourceRecord,
    download_http,
    fetch_json,
    read_csv_strict,
    sha256_file,
    write_parquet,
)

LOG = get_logger("ingest.worldbank")

# World Bank aggregates carry a region of "Aggregates" and are not countries.
_AGGREGATE_REGION = "Aggregates"


def ingest(cfg: Config) -> tuple[dict[str, pd.DataFrame], list[SourceRecord], dict[str, dict]]:
    """Download the enrichment layers and write normalised interim tables."""
    interim = cfg.path("data_interim")
    records: list[SourceRecord] = []
    stats: dict[str, dict] = {}
    tables: dict[str, pd.DataFrame] = {}

    tables["wb_income_groups"], rec, stats["income_groups"] = _income_groups(cfg)
    records += rec
    tables["wb_country_meta"], rec, stats["country_meta"] = _country_meta(cfg)
    records += rec
    tables["wb_indicators"], rec, stats["indicators"] = _indicators(cfg)
    records += rec
    tables["owid_co2"], rec, stats["co2"] = _co2(cfg)
    records += rec

    for name, df in tables.items():
        write_parquet(df, interim / f"{name}.parquet")
    return tables, records, stats


def _income_groups(cfg: Config) -> tuple[pd.DataFrame, list[SourceRecord], dict]:
    """Load the time-varying World Bank income classification from OWID.

    This is the series that makes time-varying bloc assignment possible: a deal
    takes the classification its country held in the deal year.
    """
    src = cfg.source("wb_income_groups")
    path = download_http(cfg, src["url"], src["filename"])
    df = read_csv_strict(path)
    LOG.info("income groups raw columns: %s", list(df.columns))

    # OWID column naming varies by vintage; resolve defensively rather than
    # positionally, and fail loudly if the shape changed upstream.
    code_col = _first_present(df, ["Code", "code", "iso_code"])
    year_col = _first_present(df, ["Year", "year"])
    entity_col = _first_present(df, ["Entity", "entity", "country"])
    group_candidates = [c for c in df.columns if c not in {code_col, year_col, entity_col}]
    if len(group_candidates) != 1:
        msg = (
            f"expected exactly one income-group value column in {src['filename']}, "
            f"found {group_candidates}. The upstream schema changed; update the ingest."
        )
        raise RuntimeError(msg)
    group_col = group_candidates[0]

    out = df.rename(
        columns={
            code_col: "country_code",
            year_col: "year",
            entity_col: "entity",
            group_col: "income_group_raw",
        }
    )[["country_code", "entity", "year", "income_group_raw"]].copy()

    # Rows without an ISO-3 code are OWID aggregates, not countries.
    no_code = out["country_code"].isna().sum()
    out = out.loc[out["country_code"].notna()].copy()
    out["year"] = out["year"].astype("int64")

    normalise = cfg.blocs["income_label_normalise"]
    out["income_group"] = out["income_group_raw"].map(normalise)
    unmapped = sorted(
        out.loc[out["income_group"].isna(), "income_group_raw"].dropna().unique()
    )
    if unmapped:
        # Not fatal here: logged now, and blocs.py (step 4) treats an unmapped
        # label as an explicit UNASSIGNED rather than a silent drop.
        LOG.warning("unmapped income-group labels (add to blocs.yaml): %s", unmapped)

    stats = {
        "rows": int(len(out)),
        "countries": int(out["country_code"].nunique()),
        "year_min": int(out["year"].min()),
        "year_max": int(out["year"].max()),
        "aggregate_rows_dropped": int(no_code),
        "unmapped_labels": unmapped,
        "label_counts": out["income_group_raw"].value_counts().to_dict(),
    }
    LOG.info(
        "income groups: %d rows, %d countries, %d-%d",
        stats["rows"],
        stats["countries"],
        stats["year_min"],
        stats["year_max"],
    )

    rec = [
        SourceRecord(
            source="wb_income_groups",
            filename=src["filename"],
            origin=src["url"],
            licence=src["licence"],
            sha256=sha256_file(path),
            size_bytes=path.stat().st_size,
            fetched_at=_mtime(path),
            rows=len(out),
            note=src.get("notes", ""),
        )
    ]
    return out, rec, stats


def _country_meta(cfg: Config) -> tuple[pd.DataFrame, list[SourceRecord], dict]:
    """Load World Bank country metadata: ISO-3, region and present-day income level.

    The present-day income level drives robustness alternative (a), the static
    classification against which time-varying assignment is compared.
    """
    src = cfg.source("wb_country_meta")
    payload = fetch_json(cfg, src["url"], src["filename"])
    rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []

    df = pd.DataFrame(
        [
            {
                "country_code": r["id"],
                "iso2": r.get("iso2Code"),
                "name": r.get("name"),
                "region": (r.get("region") or {}).get("value"),
                "region_id": (r.get("region") or {}).get("id"),
                "income_level_current": (r.get("incomeLevel") or {}).get("value"),
                "lending_type": (r.get("lendingType") or {}).get("value"),
                "capital": r.get("capitalCity"),
            }
            for r in rows
        ]
    )
    df["is_aggregate"] = df["region"].eq(_AGGREGATE_REGION) | df["region"].isna()

    path = cfg.path("data_raw") / src["filename"]
    stats = {
        "rows": int(len(df)),
        "countries": int((~df["is_aggregate"]).sum()),
        "aggregates": int(df["is_aggregate"].sum()),
    }
    LOG.info("country meta: %d entries (%d countries, %d aggregates)", *stats.values())

    rec = [
        SourceRecord(
            source="wb_country_meta",
            filename=src["filename"],
            origin=src["url"],
            licence=src["licence"],
            sha256=sha256_file(path),
            size_bytes=path.stat().st_size,
            fetched_at=_mtime(path),
            rows=len(df),
            note=src.get("notes", ""),
        )
    ]
    return df, rec, stats


def _indicators(cfg: Config) -> tuple[pd.DataFrame, list[SourceRecord], dict]:
    """Load the six World Bank indicator series into one long table."""
    src = cfg.source("wb_indicators")
    frames: list[pd.DataFrame] = []
    records: list[SourceRecord] = []
    per_series: dict[str, int] = {}

    for code, short_name in src["indicators"].items():
        url = src["url_template"].format(
            code=code, start=src["date_start"], end=src["date_end"]
        )
        filename = f"wb_indicator_{code}.json"
        payload = fetch_json(cfg, url, filename)

        if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
            msg = (
                f"World Bank indicator {code} returned no data rows. "
                f"Response head: {str(payload)[:300]}"
            )
            raise RuntimeError(msg)

        header, rows = payload[0], payload[1]
        if header.get("pages", 1) > 1:
            msg = (
                f"indicator {code} is paginated ({header['pages']} pages) but the ingest "
                "reads only page 1. Raise per_page in pipeline.yaml."
            )
            raise RuntimeError(msg)

        frame = pd.DataFrame(
            [
                {
                    "country_code": r["countryiso3code"] or (r.get("country") or {}).get("id"),
                    "country_name": (r.get("country") or {}).get("value"),
                    "year": int(r["date"]),
                    "indicator_code": code,
                    "indicator": short_name,
                    "value": r["value"],
                }
                for r in rows
            ]
        )
        frame = frame.loc[frame["country_code"].notna() & frame["country_code"].ne("")]
        frames.append(frame)
        per_series[short_name] = int(frame["value"].notna().sum())
        LOG.info(
            "indicator %-18s %-22s %6d rows, %6d non-null",
            code,
            short_name,
            len(frame),
            per_series[short_name],
        )

        path = cfg.path("data_raw") / filename
        records.append(
            SourceRecord(
                source="wb_indicators",
                filename=filename,
                origin=url,
                licence=src["licence"],
                sha256=sha256_file(path),
                size_bytes=path.stat().st_size,
                fetched_at=_mtime(path),
                rows=len(frame),
                note=f"{code} -> {short_name}",
            )
        )

    out = pd.concat(frames, ignore_index=True)

    # The US GDP deflator must be present and complete over the analysis window
    # or the constant-dollar conversion silently nulls amounts.
    defl = cfg.pipeline["deflate"]
    us_defl = out.loc[
        out["indicator_code"].eq(defl["series_code"])
        & out["country_code"].eq(defl["deflator_country"])
        & out["value"].notna()
    ]
    need_years = set(
        range(int(cfg.window["start"][:4]), int(cfg.window["uncensored_end"][:4]) + 1)
    ) | {defl["base_year"]}
    have_years = set(us_defl["year"].astype(int))
    missing = sorted(need_years - have_years)
    if missing:
        msg = (
            f"US GDP deflator ({defl['series_code']}/{defl['deflator_country']}) is missing "
            f"years {missing}. Constant-{defl['base_year']}-USD conversion is impossible."
        )
        raise RuntimeError(msg)
    LOG.info(
        "US GDP deflator complete for %d-%d (base %d present)",
        min(need_years),
        max(need_years),
        defl["base_year"],
    )

    stats = {
        "rows": int(len(out)),
        "series": len(src["indicators"]),
        "non_null_by_series": per_series,
        "deflator_years_available": len(have_years),
    }
    return out, records, stats


def _co2(cfg: Config) -> tuple[pd.DataFrame, list[SourceRecord], dict]:
    """Load the OWID CO2 dataset, keeping only the H5 need-indicator columns."""
    src = cfg.source("owid_co2")
    path = download_http(cfg, src["url"], src["filename"])
    wanted = [
        "iso_code",
        "country",
        "year",
        "co2",
        "co2_per_capita",
        "co2_per_gdp",
        "population",
        "gdp",
        "energy_per_capita",
        "primary_energy_consumption",
    ]
    df = read_csv_strict(path, usecols=lambda c: c.strip() in wanted)
    before = len(df)
    # Rows without an ISO code are OWID regional aggregates.
    df = df.loc[df["iso_code"].notna() & df["iso_code"].str.len().eq(3)].copy()
    df = df.rename(columns={"iso_code": "country_code"})

    stats = {
        "rows": int(len(df)),
        "aggregate_rows_dropped": int(before - len(df)),
        "countries": int(df["country_code"].nunique()),
        "year_max": int(df["year"].max()),
    }
    LOG.info(
        "owid co2: %d rows, %d countries, to %d",
        stats["rows"],
        stats["countries"],
        stats["year_max"],
    )

    rec = [
        SourceRecord(
            source="owid_co2",
            filename=src["filename"],
            origin=src["url"],
            licence=src["licence"],
            sha256=sha256_file(path),
            size_bytes=path.stat().st_size,
            fetched_at=_mtime(path),
            rows=len(df),
            note=src.get("notes", ""),
        )
    ]
    return df, rec, stats


def _first_present(df: pd.DataFrame, candidates: list[str]) -> str:
    """Return the first candidate column present, or raise naming what was found."""
    for name in candidates:
        if name in df.columns:
            return name
    msg = f"none of {candidates} in columns {list(df.columns)}"
    raise RuntimeError(msg)


def _mtime(path) -> str:
    """ISO-8601 UTC modification time of a cached file."""
    from datetime import UTC, datetime

    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
