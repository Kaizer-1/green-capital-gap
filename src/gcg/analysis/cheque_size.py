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
# `venture_unspecified` is Crunchbase's catch-all: its volume explodes over the
# period and its median collapses in BOTH groups, which is the signature of
# coverage expansion rather than of anything in the market. The formal test
# therefore runs on clean stage codes only.
_CLEAN_STAGES = ("seed", "series_a", "series_b", "series_c_plus")


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


def _composite(
    frame: pd.DataFrame, amount: str, stages: tuple[str, ...], base_mix: pd.Series
) -> dict[int, float]:
    """Base-mix-weighted average of within-stage medians, by year."""
    out = {}
    for year in (_BASE_YEAR, _END_YEAR):
        yr = frame.loc[frame["year"].eq(year)]
        w, v = [], []
        for st in stages:
            vals = yr.loc[yr["instrument"].eq(st), amount].dropna()
            if len(vals) and base_mix.get(st, 0) > 0:
                w.append(base_mix[st])
                v.append(float(np.median(vals)))
        out[year] = float(np.average(v, weights=w)) if w else float("nan")
    return out


def bootstrap_within_stage_difference(
    deals: pd.DataFrame, cfg: Config, rng: np.random.Generator
) -> dict[str, Any]:
    """Bootstrap the green-minus-non-green within-stage change, clean stages only.

    The pooled comparison is composition-confounded for BOTH groups, so it
    cannot settle the question either way. The within-stage comparison is the
    real control, and it is tested here rather than eyeballed.

    Deals are resampled with replacement inside each group x stage x year cell,
    the base-mix-weighted composite is recomputed, and the difference in
    percentage change between the two groups is taken. ``venture_unspecified``
    is excluded: it is a catch-all whose median collapses in both groups as its
    volume explodes, which is coverage expansion rather than repricing.
    """
    amount = cfg.pipeline["deflate"]["real_column"]
    draws = int(cfg.pipeline["bootstrap_resamples"])
    sub = deals.loc[
        deals["instrument"].isin(_CLEAN_STAGES)
        & deals["year"].isin([_BASE_YEAR, _END_YEAR])
        & deals[amount].notna()
    ][["year", "instrument", "green", amount]].copy()

    groups = {"green": sub.loc[sub["green"]], "non_green": sub.loc[~sub["green"]]}
    base_mixes, point = {}, {}
    cells = {}
    for name, g in groups.items():
        base = g.loc[g["year"].eq(_BASE_YEAR), "instrument"].value_counts(normalize=True)
        base_mixes[name] = base
        comp = _composite(g, amount, _CLEAN_STAGES, base)
        point[name] = _pct_change(comp[_BASE_YEAR], comp[_END_YEAR])
        cells[name] = {
            f"{st}_{yr}": int(((g["instrument"] == st) & (g["year"] == yr)).sum())
            for st in _CLEAN_STAGES
            for yr in (_BASE_YEAR, _END_YEAR)
        }
    observed_diff = point["green"] - point["non_green"]

    # Pre-index each cell once; resampling is then an integer draw per cell.
    idx = {
        (name, st, yr): g.loc[g["instrument"].eq(st) & g["year"].eq(yr), amount].to_numpy()
        for name, g in groups.items()
        for st in _CLEAN_STAGES
        for yr in (_BASE_YEAR, _END_YEAR)
    }

    diffs = []
    for _ in range(draws):
        chg = {}
        for name in groups:
            base = base_mixes[name]
            comp = {}
            for yr in (_BASE_YEAR, _END_YEAR):
                w, v = [], []
                for st in _CLEAN_STAGES:
                    arr = idx[(name, st, yr)]
                    if len(arr) and base.get(st, 0) > 0:
                        draw = rng.integers(0, len(arr), len(arr))
                        w.append(base[st])
                        v.append(float(np.median(arr[draw])))
                comp[yr] = float(np.average(v, weights=w)) if w else float("nan")
            chg[name] = _pct_change(comp[_BASE_YEAR], comp[_END_YEAR])
        if np.isfinite(chg["green"]) and np.isfinite(chg["non_green"]):
            diffs.append(chg["green"] - chg["non_green"])

    arr = np.array(diffs)
    lo, hi = float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))
    excludes_zero = bool(lo * hi > 0)
    width = hi - lo

    if excludes_zero:
        verdict = "Supported in narrow form"
        reading = (
            "The within-stage decline is significantly steeper for green than for "
            "non-green on clean stage codes. The finding stands, narrowed: it is a "
            "statement about within-stage deal sizes in named rounds, not about the "
            "pooled median, which is composition-confounded for both groups."
        )
    else:
        verdict = "Underpowered \u2014 cannot determine"
        reading = (
            "The interval spans zero, so the data cannot determine whether the "
            "within-stage decline differs between green and non-green. This is NOT a "
            "retraction and NOT a confirmation: the point estimate is large but the "
            "green cells hold tens of deals per stage-year and the interval is "
            "correspondingly wide."
        )

    LOG.info(
        "BOOTSTRAP within-stage change (clean stages, %d draws): green %+.1f%% vs "
        "non-green %+.1f%%; difference %+.1f pp [%.1f, %.1f] -> excludes zero = %s",
        len(arr),
        point["green"],
        point["non_green"],
        observed_diff,
        lo,
        hi,
        excludes_zero,
    )
    LOG.info("  verdict: %s", verdict)
    LOG.info("  green cell sizes: %s", cells["green"])

    return {
        "stages_used": list(_CLEAN_STAGES),
        "excluded_stage": "venture_unspecified",
        "exclusion_reason": (
            "Crunchbase's catch-all. Its median collapses in both groups as its volume "
            "explodes, which is coverage expansion rather than repricing, so including "
            "it would import the very confound the test is meant to remove."
        ),
        "green_pct_change": round(point["green"], 2),
        "non_green_pct_change": round(point["non_green"], 2),
        "difference_pp": round(observed_diff, 2),
        "ci_pp": [round(lo, 2), round(hi, 2)],
        "ci_width_pp": round(width, 2),
        "ci_excludes_zero": excludes_zero,
        "draws": int(len(arr)),
        "cell_sizes": cells,
        "verdict": verdict,
        "reading": reading,
    }


def run(cfg: Config | None = None) -> dict[str, Any]:
    """Run the control and the decomposition, and state what may be claimed."""
    cfg = cfg or load_config()
    cfg.ensure_dirs()
    seed_everything(cfg)
    deals = read_parquet(cfg.path("data_processed") / "deals.parquet")

    rng = seed_everything(cfg)
    control, table = control_green_vs_non_green(deals, cfg)
    green_dec = decompose_within_stage(deals, cfg, green=True)
    non_green_dec = decompose_within_stage(deals, cfg, green=False)
    formal = bootstrap_within_stage_difference(deals, cfg, rng)

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
        "formal_test": formal,
        "claim_permitted": (
            "The POOLED median real cheque fell by roughly 72% for green deals and 73% "
            "for non-green between "
            f"{_BASE_YEAR} and {_END_YEAR}. That comparison settles nothing, because the "
            "pooled median is composition-confounded for both groups: holding the "
            f"{_BASE_YEAR} stage mix fixed leaves non-green at only -11%. The question is "
            "therefore decided on the WITHIN-STAGE comparison, tested by bootstrap on "
            "clean stage codes. See formal_test for the interval and the verdict it "
            "licenses."
        ),
        "claim_not_permitted": (
            "Asserting the Gaddy et al. rotation out of hardware as a mechanism this "
            "dataset demonstrates. Whatever the within-stage test returns, it establishes "
            "a size pattern, not an investor motive; the rotation remains external "
            "evidence."
        ),
    }
    path = cfg.path("data_interim") / "cheque_size_findings.json"
    path.write_text(json.dumps(findings, indent=2, default=str) + "\n", encoding="utf-8")
    return findings


if __name__ == "__main__":
    run()
