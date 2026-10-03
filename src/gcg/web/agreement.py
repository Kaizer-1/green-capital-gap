"""Assert that series.json and findings.json state the same quantity the same way.

The web page draws from two pipeline exports. ``findings.json`` holds the
statistics the prose quotes, already rounded for display; ``series.json`` holds
plot-ready arrays, rounded for geometry. Where a quantity appears in both, the
two must agree at the precision the report displays — otherwise a figure prints
88.24% beside a sentence reading 88.2%, which is exactly what happened.

The bare-number gate cannot catch this on its own. It accepts any value either
export produced, which is right in principle — a data table reproducing a
plotted series has no prose counterpart — but it means a precision mismatch
between the two exports passes. This module closes that specific hole by
naming the pairs and checking them.

The registry is deliberately explicit. A pair that is not declared is not
checked, so adding a figure means adding its pairs, and the check below fails
if a figure contributes none at all.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from gcg.config import get_logger
from gcg.rounding import half_up

LOG = get_logger("web.agreement")


class AgreementError(RuntimeError):
    """A quantity is stated two different ways by the two exports."""


def _decimals(text: str) -> int:
    """How many decimal places a findings value is displayed to."""
    match = re.search(r"\.(\d+)", text)
    return len(match.group(1)) if match else 0


def _numbers(text: str) -> list[float]:
    """Every number in a findings value, normalised out of its display form."""
    cleaned = text.replace(",", "").replace("−", "-").replace("×", "")
    return [float(t) for t in re.findall(r"-?\d+(?:\.\d+)?", cleaned)]


def _agrees(series_value: Any, findings_text: str) -> tuple[bool, str]:
    """Whether a series value rounds to what findings.json displays."""
    wanted = _numbers(findings_text)
    if not wanted:
        return True, ""  # a verdict or other prose value; nothing to compare

    got = series_value if isinstance(series_value, list) else [series_value]
    got = [g for g in got if isinstance(g, (int, float))]
    if len(got) != len(wanted):
        return False, f"series has {len(got)} number(s), findings has {len(wanted)}"

    # half_up, not Python's round(): the project rounds half away from zero
    # everywhere else, and a check that rounds differently from the thing it
    # checks will pass values the reader sees disagree.
    places = _decimals(findings_text)
    for g, w in zip(got, wanted, strict=True):
        if half_up(float(g), places) != half_up(w, places):
            return False, f"series {g} rounds to {half_up(float(g), places)}, findings {w}"
    return True, ""


# --------------------------------------------------------------------------
# The registry. Each entry yields (label, series value, findings key).


def _pairs(payload: dict) -> Iterator[tuple[str, str, Any, str]]:
    """Every declared (figure, label, series value, findings key)."""
    bloc_key = {
        "AE": "ae",
        "EM": "em",
        "CHINA": "china",
        "LDC": "ldc",
        "UNASSIGNED": "unassigned",
    }

    fig = payload["fig02_double_gap"]
    for mark in fig["marks"]:
        b = bloc_key[mark["bloc"]]
        yield ("fig02", f"{b} rate", mark["rate"], f"h1.{b}_rate_pct")
        yield ("fig02", f"{b} deals", mark["n"], f"pop.{b}_deals")
        yield ("fig02", f"{b} green", mark["green"], f"pop.{b}_green")
        if mark["draw_interval"]:
            yield ("fig02", f"{b} interval", mark["ci"], f"h1.{b}_ci")
    yield ("fig02", "risk ratio", fig["test"]["risk_ratio"], "h1.rr")
    yield ("fig02", "risk ratio CI", fig["test"]["risk_ratio_ci"], "h1.rr_ci")
    yield ("fig02", "upper bound", fig["upper_bound"]["rate"], "h1.ub_em_rate_pct")

    fig = payload["fig03_rate_by_year"]
    yield ("fig03", "minimum cell", fig["min_cell"], "power.min_cell")

    fig = payload["fig04_ladder"]
    yield ("fig04", "elasticity", fig["fit"]["slope"], "h1b.elasticity")
    yield ("fig04", "R squared", fig["fit"]["r_squared"], "h1b.r2")
    yield ("fig04", "sectors", fig["fit"]["n_sectors"], "h1b.n_sectors")
    yield (
        "fig04",
        "cleantech residual",
        fig["focus"]["residual_ratio"],
        "h1b.cleantech_residual",
    )
    yield (
        "fig04",
        "cleantech residual CI",
        fig["focus"]["residual_ci"],
        "h1b.cleantech_residual_ci",
    )

    fig = payload["fig06_subdomain"]
    for mark in fig["marks"]:
        b = bloc_key[mark["bloc"]]
        yield (
            "fig06",
            f"{b} unresolved",
            mark["unspecified_pct"],
            f"measure.{b}_unspecified_pct",
        )
        yield ("fig06", f"{b} resolved", mark["specific_pct"], f"measure.{b}_specific_pct")
        yield ("fig06", f"{b} green deals", mark["n"], f"pop.{b}_green")

    fig = payload["fig08_crisis"]
    for series, pct in fig["drawdown"].items():
        key = f"h2.crisis_{series.lower().replace('-', '_')}_pct"
        yield ("fig08", f"{series} drawdown", pct, key)
    # `omitted_series.reason_key` names a key rather than holding a value; the
    # browser resolves it. There is nothing numeric here to compare.

    fig = payload["fig09_instruments"]
    for mark in fig["marks"]:
        b = bloc_key[mark["bloc"]]
        suffix = "green" if mark["green"] else "nongreen"
        yield ("fig09", f"{b} {suffix} share", mark["pct"], f"h3.{b}_{suffix}_nondilutive_pct")
        yield ("fig09", f"{b} {suffix} deals", mark["n"], f"pop.{b}_{suffix}_deals")
    yield ("fig09", "minimum cell", fig["min_cell"], "power.min_cell")

    fig = payload["fig10_depth_need"]
    yield ("fig10", "rho", fig["depth"]["rho"], "h5.depth_rho")
    yield ("fig10", "rho CI", fig["depth"]["ci"], "h5.depth_ci")
    yield ("fig10", "countries", fig["depth"]["n"], "h5.depth_n")
    yield ("fig10", "gini", fig["concentration"]["gini"], "h5.gini")
    yield ("fig10", "top five share", fig["concentration"]["top5_pct"], "h5.top5_pct")
    yield (
        "fig10",
        "countries with variance",
        fig["need"]["non_trivial_values"],
        "h5.need_nonzero_countries",
    )

    fig = payload["fig11_power_wall"]
    yield ("fig11", "threshold", fig["threshold"]["value"], "power.min_cell")
    by_label = {m["label"]: m["value"] for m in fig["marks"]}
    yield (
        "fig11",
        "EM non-dilutive",
        by_label["EM green non-dilutive deals"],
        "h3.em_nondilutive_n",
    )
    yield (
        "fig11",
        "EM seed entrants",
        by_label["EM green seed entrants"],
        "h4.em_green_entrants",
    )
    yield ("fig11", "AE A-to-B pool", by_label["AE green Series A to B pool"], "h4.ae_ab_pool")
    yield (
        "fig11",
        "largest EM cell",
        by_label["Largest EM green year-cell"],
        "h2.em_largest_cell",
    )

    fig = payload["fig12_continuity"]
    # The India panel covers 2015-2019; india.deals counts the whole dated
    # scrape including the partial 2020 the figure excludes, so the two are not
    # the same quantity and are not compared. The Crunchbase panel is.
    crunchbase = next(p for p in fig["panels"] if p["id"] == "crunchbase")
    yield (
        "fig12",
        "emerging-market green deals",
        sum(m["green"] for m in crunchbase["marks"]),
        "h3.em_green_deals",
    )

    fig = payload["fig07_cycle"]
    peak = max(fig["marks"], key=lambda m: m["deals"])
    yield ("fig07", "peak deal count", peak["deals"], "cycle.peak_deals")
    yield ("fig07", "peak year", peak["year"], "cycle.peak_deals_year")
    yield (
        "fig07",
        "green deals",
        sum(m["deals"] for m in fig["marks"]),
        "classifier.green_deals",
    )


# The figures whose quantities have no prose counterpart at all, declared so the
# coverage check below can tell "nothing to compare" from "nobody wrote it down".
NO_PAIRS = frozenset({"fig01_coverage", "fig05_share_crossover", "figM1_censoring"})


def check(payload: dict, findings: dict[str, str]) -> list[str]:
    """Every disagreement between the two exports, by name."""
    problems = []
    seen = set()
    for figure, label, value, key in _pairs(payload):
        seen.add(figure)
        if key not in findings:
            problems.append(f"{figure}: {label} has no findings key {key!r}")
            continue
        ok, why = _agrees(value, findings[key])
        if not ok:
            problems.append(f"{figure}: {label} ({key}) — {why}")

    # A figure that contributes no pairs is a figure nobody checked. Adding one
    # without adding its pairs should fail here rather than pass silently.
    declared = {k for k in payload if k.startswith("fig")}
    missing = sorted(
        f for f in declared if f not in NO_PAIRS and f.split("_", 1)[0] not in seen
    )
    problems += [
        f"{f}: declared no series/findings pairs; add them to agreement.py" for f in missing
    ]
    return problems
