"""Time-varying country-to-bloc assignment.

CLAUDE.md §5. A deal takes the bloc its country held **in the year the deal
closed**: a deal in Poland in 2004 is not a deal in an advanced economy, a deal
in Poland in 2013 is. Almost nobody does this, and doing it is a genuine
methodological contribution that the report states explicitly.

Blocs:

- ``AE``    advanced economies, World Bank high-income
- ``EM``    upper-middle, lower-middle and low income, excluding China and LDCs
- ``CHINA`` always separate; it dominates EM aggregates and hides everything else
- ``LDC``   UN least developed countries, also evaluated per year
- ``UNASSIGNED`` anything that cannot be mapped, never silently dropped

Two alternative schemes are built for the robustness appendix: a static
present-day classification, and the MSCI Emerging Markets constituent list.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from gcg.config import Config, get_logger

LOG = get_logger("classify.blocs")

UNASSIGNED = "UNASSIGNED"


def normalise_country_code(series: pd.Series, cfg: Config) -> tuple[pd.Series, dict[str, Any]]:
    """Apply the ISO-3166-3 override map to raw Crunchbase country codes.

    The snapshot is nominally ISO-3166-1 alpha-3 but carries withdrawn codes
    (``ROM`` for Romania, ``TMP`` for Timor-Leste) and blanks. Every override is
    counted so the report can state what was remapped and why.
    """
    overrides = {k.upper(): v["to"] for k, v in cfg.blocs["code_overrides"].items()}
    non_country = {str(c).strip().upper() for c in cfg.blocs["non_country_codes"]}

    raw = series.astype("string").str.strip().str.upper()
    blank = raw.isna() | raw.isin(non_country) | raw.eq("")
    out = raw.mask(blank).replace(overrides)

    applied = {
        code: int((raw == code).sum()) for code in overrides if int((raw == code).sum()) > 0
    }
    stats = {
        "rows": int(len(series)),
        "blank_or_non_country": int(blank.sum()),
        "overrides_applied": applied,
    }
    if applied:
        LOG.info("country-code overrides applied: %s", applied)
    LOG.info(
        "country code blank or non-country: %d of %d",
        stats["blank_or_non_country"],
        len(series),
    )
    return out, stats


def _ldc_membership(cfg: Config) -> dict[str, tuple[int, int]]:
    """Return ``{code: (from_year, until_year)}`` for LDC status.

    ``until_year`` is the graduation year; a country is LDC strictly before it.
    """
    spec = cfg.blocs["ldc"]
    out: dict[str, tuple[int, int]] = {}
    for entry in spec["current"]:
        out[entry["code"]] = (int(entry.get("from", 1971)), 9999)
    for entry in spec["graduated"]:
        out[entry["code"]] = (int(entry.get("from", 1971)), int(entry["graduated"]))
    return out


def build_bloc_panel(cfg: Config, income_groups: pd.DataFrame) -> pd.DataFrame:
    """Build the (country, year) -> bloc panel from the historical income series.

    Parameters
    ----------
    cfg
        Project configuration.
    income_groups
        The OWID/World Bank time-varying income classification, with columns
        ``country_code``, ``year`` and ``income_group``.

    Returns
    -------
    pandas.DataFrame
        Columns ``country_code``, ``year``, ``income_group``, ``bloc``, covering
        every country-year in the series plus the configured overrides.
    """
    window = cfg.window
    y0 = int(window["start"][:4])
    y1 = int(window["plausible_max"][:4])

    df = (
        income_groups[["country_code", "year", "income_group"]]
        .dropna(subset=["country_code"])
        .copy()
    )
    df["year"] = df["year"].astype(int)

    # Reindex each country over the full year range and carry the last known
    # classification forward. The World Bank publishes a classification per
    # country-year, but coverage starts later for some countries; carrying the
    # first known value backwards would invent history, so back-fill is NOT
    # applied and early years stay unclassified.
    years = pd.RangeIndex(min(y0, int(df["year"].min())), y1 + 1, name="year")
    frames = []
    for code, grp in df.groupby("country_code", sort=False):
        s = grp.set_index("year")["income_group"].sort_index().reindex(years).ffill()
        frames.append(
            pd.DataFrame({"country_code": code, "year": years, "income_group": s.to_numpy()})
        )
    panel = pd.concat(frames, ignore_index=True)

    # Explicit income overrides for economies the series does not classify.
    for code, spec in cfg.blocs.get("income_overrides", {}).items():
        mask = panel["country_code"].eq(code) & panel["year"].ge(int(spec.get("from", y0)))
        if mask.any():
            panel.loc[mask, "income_group"] = spec["income_group"]
        else:
            add = pd.DataFrame(
                {
                    "country_code": code,
                    "year": [y for y in years if y >= int(spec.get("from", y0))],
                    "income_group": spec["income_group"],
                }
            )
            panel = pd.concat([panel, add], ignore_index=True)
        LOG.info("income override: %s -> %s (%s)", code, spec["income_group"], spec["bloc"])

    panel["bloc"] = _derive_bloc(panel, cfg)
    panel = panel.drop_duplicates(subset=["country_code", "year"], keep="last").reset_index(
        drop=True
    )

    LOG.info(
        "bloc panel: %d country-years, %d countries, %d-%d",
        len(panel),
        panel["country_code"].nunique(),
        panel["year"].min(),
        panel["year"].max(),
    )
    in_window = panel.loc[panel["year"].between(y0, int(window["end"][:4]))]
    LOG.info(
        "in-window bloc mix (country-years): %s", in_window["bloc"].value_counts().to_dict()
    )
    return panel


def _derive_bloc(panel: pd.DataFrame, cfg: Config) -> pd.Series:
    """Map income group plus the separated groups to a bloc label."""
    mapping = cfg.blocs["income_group_to_bloc"]
    china = {c.upper() for c in cfg.blocs["china"]["codes"]}
    ldc = _ldc_membership(cfg)

    bloc = panel["income_group"].map(mapping).fillna(UNASSIGNED)

    # LDC overrides the income-derived bloc, evaluated per year.
    codes = panel["country_code"].to_numpy()
    years = panel["year"].to_numpy()
    is_ldc = np.zeros(len(panel), dtype=bool)
    for code, (start, end) in ldc.items():
        is_ldc |= (codes == code) & (years >= start) & (years < end)
    bloc = bloc.mask(pd.Series(is_ldc, index=panel.index), "LDC")

    # China is always reported separately and overrides everything.
    return bloc.mask(panel["country_code"].str.upper().isin(china), "CHINA")


def assign(
    df: pd.DataFrame,
    panel: pd.DataFrame,
    cfg: Config,  # noqa: ARG001 - kept so every bloc scheme shares one call contract
    *,
    country_col: str = "country_code",
    year_col: str = "year",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Attach the time-varying bloc to each row, logging everything unmapped.

    Returns
    -------
    tuple[pandas.DataFrame, dict]
        The frame with ``bloc`` and ``income_group`` columns added, and a
        diagnostics dict naming every country code that failed to map.
    """
    lookup = panel.set_index(["country_code", "year"])[["income_group", "bloc"]]
    idx = pd.MultiIndex.from_arrays([df[country_col], df[year_col]])
    joined = lookup.reindex(idx)

    out = df.copy()
    out["income_group"] = joined["income_group"].to_numpy()
    out["bloc"] = pd.Series(joined["bloc"].to_numpy(), index=df.index).fillna(UNASSIGNED)

    unmapped = out.loc[out["bloc"].eq(UNASSIGNED)]
    by_code = unmapped[country_col].value_counts(dropna=False)
    known_codes = set(panel["country_code"])
    absent = sorted(
        {str(c) for c in by_code.index if str(c) not in known_codes and pd.notna(c)}
    )

    stats = {
        "rows": int(len(out)),
        "assigned": int((~out["bloc"].eq(UNASSIGNED)).sum()),
        "unassigned": int(len(unmapped)),
        "unassigned_share": round(float(out["bloc"].eq(UNASSIGNED).mean()), 4),
        "unassigned_by_code": {str(k): int(v) for k, v in by_code.head(30).items()},
        "codes_absent_from_panel": absent,
        "bloc_counts": out["bloc"].value_counts().to_dict(),
    }
    LOG.info(
        "bloc assignment: %d/%d assigned (%.2f%% unassigned)",
        stats["assigned"],
        stats["rows"],
        100 * stats["unassigned_share"],
    )
    if absent:
        LOG.warning(
            "country codes with no entry in the income panel (add to blocs.yaml "
            "code_overrides or income_overrides): %s",
            absent,
        )
    if stats["unassigned"]:
        LOG.info(
            "top unassigned country codes: %s", list(stats["unassigned_by_code"].items())[:12]
        )
    return out, stats


# ---------------------------------------------------------------------------
# Robustness alternatives
# ---------------------------------------------------------------------------
def static_bloc_map(cfg: Config, country_meta: pd.DataFrame) -> dict[str, str]:
    """Robustness (a): each country's present-day income level, applied to all years."""
    normalise = {
        "High income": "high_income",
        "Upper middle income": "upper_middle_income",
        "Lower middle income": "lower_middle_income",
        "Low income": "low_income",
    }
    mapping = cfg.blocs["income_group_to_bloc"]
    china = {c.upper() for c in cfg.blocs["china"]["codes"]}
    ldc = _ldc_membership(cfg)

    out: dict[str, str] = {}
    meta = country_meta.loc[~country_meta["is_aggregate"]]
    for _, row in meta.iterrows():
        code = str(row["country_code"]).upper()
        group = normalise.get(str(row["income_level_current"]).strip())
        bloc = mapping.get(group, UNASSIGNED)
        if code in ldc:
            start, end = ldc[code]
            # Static scheme uses present-day LDC status.
            bloc = "LDC" if end == 9999 else bloc
        if code in china:
            bloc = "CHINA"
        out[code] = bloc

    for code, spec in cfg.blocs.get("income_overrides", {}).items():
        out.setdefault(code, spec["bloc"])
    LOG.info(
        "static bloc map: %d countries, mix %s",
        len(out),
        pd.Series(out).value_counts().to_dict(),
    )
    return out


def msci_bloc_map(cfg: Config) -> dict[str, str]:
    """Robustness (b): the MSCI Emerging Markets constituent list.

    MSCI treats Korea and Taiwan as emerging while the World Bank treats both as
    high-income, and it includes China. That disagreement is the point of running
    the comparison.
    """
    spec = cfg.blocs["robustness_msci_em"]
    out = {str(c["code"]).upper(): "EM" for c in spec["codes"]}
    if not spec.get("include_china", True):
        out.pop("CHN", None)
    LOG.info(
        "MSCI EM map: %d markets, china included = %s", len(out), spec.get("include_china")
    )
    return out
