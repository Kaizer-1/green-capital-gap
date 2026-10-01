"""Separate venture-stage companies from infrastructure and project finance.

Several of the largest emerging-market "green venture" deals in this snapshot are
utility-scale generation assets rather than startups — hydro and thermal
independent power producers financed through private equity. The same is true of
a smaller share of advanced-economy rows. Pooling them with seed and Series A
rounds makes "venture funding" mean two different things in the same series.

The criterion is declared in ``config/pipeline.yaml`` **before** being applied to
any data, is instrument-based, uses only fields already present, and is applied
symmetrically to every bloc. It cannot be tuned toward a preferred answer because
it never looks at deal size, company name, country or green status.

Deal size is reported afterwards as an independent cross-check on whether the
criterion actually separated the two populations. If it did not, that is reported
rather than quietly repaired.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from gcg.config import Config, get_logger

LOG = get_logger("classify.venture_stage")

VENTURE = "venture_stage"
NON_VENTURE = "non_venture_only"


def classify_companies(deals: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Assign each company a venture-stage flag from its in-window instrument mix.

    Parameters
    ----------
    deals
        In-window deal rows with ``object_id`` and ``instrument``.
    cfg
        Project configuration.

    Returns
    -------
    pandas.DataFrame
        One row per company: ``object_id``, ``venture_stage`` (bool),
        ``venture_stage_class``, and the counts behind the decision.
    """
    spec = cfg.pipeline["venture_stage"]
    venture_set = set(spec["venture_instruments"])

    grouped = deals.groupby("object_id", observed=True)["instrument"]
    per_company = grouped.agg(
        rounds="size",
        venture_rounds=lambda s: int(s.isin(venture_set).sum()),
    ).reset_index()
    per_company["venture_stage"] = per_company["venture_rounds"] > 0
    per_company["venture_stage_class"] = per_company["venture_stage"].map(
        {True: VENTURE, False: NON_VENTURE}
    )
    LOG.info(
        "venture-stage classification: %d companies, %d venture-stage, %d non-venture-only",
        len(per_company),
        int(per_company["venture_stage"].sum()),
        int((~per_company["venture_stage"]).sum()),
    )
    return per_company


def size_crosscheck(deals: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Independent check on whether the criterion separated the populations.

    Not part of the definition. If venture-stage and non-venture deals have
    indistinguishable size distributions, the criterion has not done its job and
    the report says so.
    """
    pcts = cfg.pipeline["venture_stage"]["size_crosscheck_percentiles"]
    amount = cfg.pipeline["deflate"]["real_column"]
    rows = []
    for label, grp in deals.groupby("venture_stage_class", observed=True):
        disclosed = grp[amount].dropna()
        row: dict[str, Any] = {
            "venture_stage_class": label,
            "deals": len(grp),
            "deals_with_amount": len(disclosed),
            "mean_usd": round(float(disclosed.mean()), 0) if len(disclosed) else None,
        }
        for p in pcts:
            row[f"p{int(p * 100)}_usd"] = (
                round(float(disclosed.quantile(p)), 0) if len(disclosed) else None
            )
        rows.append(row)
    return pd.DataFrame(rows)


def split_by_bloc(deals: pd.DataFrame) -> pd.DataFrame:
    """Venture-stage composition by bloc, reported as a finding in its own right.

    If emerging-market green funding runs disproportionately through
    project-finance structures rather than venture rounds, that is a statement
    about how green capital reaches emerging markets, not a nuisance to control
    away.
    """
    rows = []
    for (bloc, green), grp in deals.groupby(["bloc", "green"], observed=True):
        venture = int((grp["venture_stage_class"] == VENTURE).sum())
        rows.append(
            {
                "bloc": bloc,
                "green": bool(green),
                "deals": len(grp),
                "venture_stage_deals": venture,
                "non_venture_deals": len(grp) - venture,
                "venture_stage_pct": round(100 * venture / len(grp), 2) if len(grp) else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values(["green", "bloc"])
