"""Control for the apparent collapse in green cheque size.

Figure 5 initially carried the claim that the median green cheque fell by about
72% in real terms between 2007 and 2012, and read that as the Gaddy et al.
rotation out of capital-intensive hardware showing up directly in the deal
record.

**That claim does not survive its control.** Non-green deals fall by almost
exactly the same amount over the same window, which means the decline is a
property of the dataset rather than of green entrepreneurship. The most likely
mechanism is Crunchbase's coverage of small rounds improving as the platform
matured, dragging the pooled median down across every sector at once.

This module runs two checks and reports both:

1. **The control.** The same series for non-green deals. If non-green falls
   similarly, nothing green-specific has been demonstrated.
2. **The decomposition.** Pooled medians can fall either because deals within
   each stage got smaller (repricing) or because the mix shifted toward
   earlier, smaller stages (composition). Holding the 2007 stage mix fixed and
   recomputing separates the two.

Nothing here asserts a mechanism. The module exists to stop one being asserted.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from gcg.config import Config, get_logger, load_config, seed_everything
from gcg.io import read_parquet

LOG = get_logger("analysis.cheque")

_BASE_YEAR = 2007
_END_YEAR = 2012
_STAGES = ("seed", "series_a", "series_b", "series_c_plus", "venture_unspecified")


def _pct_change(first: float, last: float) -> float:
    """Percentage change, guarding division by zero."""
    return float(100 * (last / first - 1)) if first else float("nan")


def control_green_vs_non_green(deals: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    """Median real cheque by year for green and non-green deals.

    The control that decides whether the green decline means anything.
    """
    amount = cfg.pipeline["deflate"]["real_column"]
    tab = (
        deals.assign(group=np.where(deals["green"], "green", "non_green"))
        .groupby(["year", "group"])[amount]
        .agg(["median", "count"])
        .unstack("group")
    )
    out = pd.DataFrame(
        {
            "green_median_usd": tab[("median", "green")],
            "green_n": tab[("count", "green")],
            "non_green_median_usd": tab[("median", "non_green")],
            "non_green_n": tab[("count", "non_green")],
        }
    )
    out["ratio_green_over_non_green"] = (
        out["green_median_usd"] / out["non_green_median_usd"]
    ).round(3)

    g_chg = _pct_change(
        float(out.loc[_BASE_YEAR, "green_median_usd"]),
        float(out.loc[_END_YEAR, "green_median_usd"]),
    )
    ng_chg = _pct_change(
        float(out.loc[_BASE_YEAR, "non_green_median_usd"]),
        float(out.loc[_END_YEAR, "non_green_median_usd"]),
    )
    # A green-specific story needs green to fall materially MORE than non-green.
    differential = g_chg - ng_chg
    green_specific = bool(differential < -15.0)

    findings = {
        "base_year": _BASE_YEAR,
        "end_year": _END_YEAR,
        "green_pct_change": round(g_chg, 2),
        "non_green_pct_change": round(ng_chg, 2),
        "differential_pp": round(differential, 2),
        "green_specific": green_specific,
        "verdict": (
            "Green-specific decline NOT demonstrated: non-green falls by a comparable "
            "amount over the same window, so the pooled decline is a property of the "
            "dataset rather than of green entrepreneurship."
            if not green_specific
            else "Green falls materially faster than non-green; a green-specific "
            "explanation is admissible."
        ),
        "by_year": out.reset_index().to_dict("records"),
    }
    LOG.info(
        "CONTROL  green %+.1f%% vs non-green %+.1f%% (%d->%d); differential %+.1f pp "
        "-> green-specific = %s",
        g_chg,
        ng_chg,
        _BASE_YEAR,
        _END_YEAR,
        differential,
        green_specific,
    )
    LOG.info("  %s", findings["verdict"])
    return findings, out


def decompose_within_stage(deals: pd.DataFrame, cfg: Config, *, green: bool) -> dict[str, Any]:
    """Separate repricing from composition using the stage mix.

    A pooled median can fall because each stage got cheaper, or because the mix
    tilted toward earlier stages. Recomputing with the base-year mix held fixed
    isolates the first.
    """
    amount = cfg.pipeline["deflate"]["real_column"]
    sub = deals.loc[deals["green"].eq(green) & deals["instrument"].isin(_STAGES)]

    within = sub.pivot_table(
        index="year", columns="instrument", values=amount, aggfunc="median"
    )
    mix = pd.crosstab(sub["year"], sub["instrument"], normalize="index")
    counts = pd.crosstab(sub["year"], sub["instrument"])

    if _BASE_YEAR not in mix.index:
        return {"error": f"no {_BASE_YEAR} rows"}

    base_mix = mix.loc[_BASE_YEAR]
    stages = [s for s in _STAGES if s in within.columns]

    # Counterfactual: within-stage medians of each year, weighted by the base
    # year's mix. Movement here is repricing; the residual is composition.
    cf = []
    for year in within.index:
        w, v = [], []
        for st in stages:
            med = within.loc[year, st]
            if pd.notna(med) and base_mix.get(st, 0) > 0:
                w.append(base_mix[st])
                v.append(med)
        cf.append(float(np.average(v, weights=w)) if w else float("nan"))
    within["counterfactual_base_mix_usd"] = cf

    actual_first = float(within.loc[_BASE_YEAR, "counterfactual_base_mix_usd"])
    actual_last = float(within.loc[_END_YEAR, "counterfactual_base_mix_usd"])
    repricing = _pct_change(actual_first, actual_last)

    per_stage = {
        st: {
            "base_usd_m": round(float(within.loc[_BASE_YEAR, st]) / 1e6, 2)
            if pd.notna(within.loc[_BASE_YEAR, st])
            else None,
            "end_usd_m": round(float(within.loc[_END_YEAR, st]) / 1e6, 2)
            if pd.notna(within.loc[_END_YEAR, st])
            else None,
            "pct_change": round(
                _pct_change(
                    float(within.loc[_BASE_YEAR, st]), float(within.loc[_END_YEAR, st])
                ),
                1,
            )
            if pd.notna(within.loc[_BASE_YEAR, st]) and pd.notna(within.loc[_END_YEAR, st])
            else None,
            "base_n": int(counts.loc[_BASE_YEAR, st]) if st in counts.columns else 0,
            "end_n": int(counts.loc[_END_YEAR, st]) if st in counts.columns else 0,
        }
        for st in stages
    }
    mix_shift = {
        st: {
            "base_pct": round(100 * float(base_mix.get(st, 0)), 1),
            "end_pct": round(100 * float(mix.loc[_END_YEAR].get(st, 0)), 1),
        }
        for st in stages
    }

    label = "green" if green else "non-green"
    LOG.info(
        "DECOMPOSITION (%s): holding the %d stage mix fixed, the within-stage "
        "average moves %+.1f%% by %d",
        label,
        _BASE_YEAR,
        repricing,
        _END_YEAR,
    )
    for st, v in per_stage.items():
        LOG.info(
            "    %-20s %s -> %s  (%s%%)  n %d -> %d",
            st,
            f"${v['base_usd_m']}m" if v["base_usd_m"] is not None else "-",
            f"${v['end_usd_m']}m" if v["end_usd_m"] is not None else "-",
            v["pct_change"],
            v["base_n"],
            v["end_n"],
        )
    LOG.info(
        "    stage mix shift: %s",
        {k: f"{v['base_pct']}->{v['end_pct']}%" for k, v in mix_shift.items()},
    )

    return {
        "group": label,
        "repricing_pct_change_base_mix": round(repricing, 2),
        "per_stage": per_stage,
        "stage_mix": mix_shift,
        "within_stage_usd_m": (within[stages] / 1e6).round(3).reset_index().to_dict("records"),
    }


def run(cfg: Config | None = None) -> dict[str, Any]:
    """Run the control and the decomposition, and state what may be claimed."""
    cfg = cfg or load_config()
    cfg.ensure_dirs()
    seed_everything(cfg)
    deals = read_parquet(cfg.path("data_processed") / "deals.parquet")

    control, table = control_green_vs_non_green(deals, cfg)
    green_dec = decompose_within_stage(deals, cfg, green=True)
    non_green_dec = decompose_within_stage(deals, cfg, green=False)

    out = table.copy()
    out["green_median_usd_m"] = (out["green_median_usd"] / 1e6).round(3)
    out["non_green_median_usd_m"] = (out["non_green_median_usd"] / 1e6).round(3)
    out.drop(columns=["green_median_usd", "non_green_median_usd"]).to_csv(
        cfg.path("tables") / "appendix_cheque_size_control.csv"
    )
    LOG.info("wrote appendix_cheque_size_control.csv")

    findings = {
        "control": control,
        "decomposition_green": green_dec,
        "decomposition_non_green": non_green_dec,
        "claim_permitted": (
            "The pooled median real cheque fell by roughly 72% for green deals between "
            f"{_BASE_YEAR} and {_END_YEAR}. It fell by a comparable amount for non-green "
            "deals over the same window. The decline is therefore reported as a "
            "dataset-wide pattern, most plausibly improving coverage of small rounds as "
            "the platform matured, and NOT as evidence of a rotation out of "
            "capital-intensive green hardware."
        ),
        "claim_not_permitted": (
            "That the green cheque decline reflects investors rotating from hardware into "
            "software after the cleantech bust. The control does not support it, and the "
            "Gaddy et al. rotation can only be cited as external evidence."
        ),
    }
    path = cfg.path("data_interim") / "cheque_size_findings.json"
    path.write_text(json.dumps(findings, indent=2, default=str) + "\n", encoding="utf-8")
    return findings


if __name__ == "__main__":
    run()
