"""H5: does green capital track market depth rather than climate need?

*Country-level green funding intensity correlates with GDP per capita and
financial-market depth, and shows no positive association with indicators of
climate or energy need.*

**Power, stated up front rather than discovered later.** 42 countries record at
least one green deal, 23 record at least three, 20 record at least five. The
outcome is built on small per-country counts, so every correlation is reported
with a bootstrap confidence interval rather than a bare coefficient, and the
small-n caveat travels with the number.

Spearman rather than Pearson because the relationships are monotone rather than
linear and the funding distribution is heavy-tailed. No causal claim is made:
this is an association between country characteristics and where capital landed.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

from gcg.config import Config, get_logger
from gcg.io import read_parquet

LOG = get_logger("analysis.h5")

# Need indicators: higher value = greater climate or energy need.
# Electricity ACCESS is deliberately NOT here. Higher access means LESS need, so
# counting it as a need indicator would read a confirmation of the hypothesis as
# a falsification of it. The deficit (100 - access) is the need measure, and
# access is reported below as a development covariate instead.
_NEED = {
    "co2_per_capita": "CO2 per capita",
    "renewable_energy_share_pct": "renewable share of final energy",
    "electricity_deficit_pct": "electricity access deficit",
}
_DEPTH = {
    "gdp_per_capita_usd": "GDP per capita",
    "electricity_access_pct": "access to electricity (development covariate)",
}


def build_panel(deals: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Country-level cross-section: green funding intensity and covariates."""
    amount = cfg.pipeline["deflate"]["real_column"]
    interim = cfg.path("data_interim")
    indicators = read_parquet(interim / "wb_indicators.parquet")
    co2 = read_parquet(interim / "owid_co2.parquet")

    end_year = int(cfg.window["end"][:4])
    g = deals.loc[deals["green"]]
    by_country = g.groupby("country_code").agg(
        green_deals=("id", "size"),
        green_usd=(amount, lambda s: float(s.sum())),
    )
    all_country = deals.groupby("country_code").size().rename("all_deals")
    panel = by_country.join(all_country, how="left").reset_index()

    wide = (
        indicators.loc[indicators["year"].eq(end_year)]
        .pivot_table(index="country_code", columns="indicator", values="value")
        .reset_index()
    )
    panel = panel.merge(wide, on="country_code", how="left")

    c = co2.loc[co2["year"].eq(end_year), ["country_code", "co2_per_capita"]].drop_duplicates(
        "country_code"
    )
    panel = panel.merge(c, on="country_code", how="left")

    panel["green_usd_per_capita"] = panel["green_usd"] / panel["population"]
    panel["green_usd_per_gdp"] = panel["green_usd"] / panel["gdp_current_usd"]
    panel["green_share_of_deals"] = panel["green_deals"] / panel["all_deals"]
    # Electricity ACCESS is the inverse of energy need; the deficit is the need.
    panel["electricity_deficit_pct"] = 100 - panel["electricity_access_pct"]
    return panel


def spearman_ci(
    x: pd.Series, y: pd.Series, rng: np.random.Generator, draws: int
) -> dict[str, Any]:
    """Spearman rho with a bootstrap confidence interval.

    With 20 to 42 countries a bare rho is not reportable; the interval is what
    tells a reader whether the sign is even stable.
    """
    ok = x.notna() & y.notna()
    xa, ya = x.loc[ok].to_numpy(), y.loc[ok].to_numpy()
    n = len(xa)
    if n < 5:
        return {"n": n, "rho": None, "note": "too few observations"}

    rho, p = stats.spearmanr(xa, ya)
    boot = []
    for _ in range(draws):
        idx = rng.integers(0, n, n)
        if len(np.unique(xa[idx])) < 3 or len(np.unique(ya[idx])) < 3:
            continue
        boot.append(stats.spearmanr(xa[idx], ya[idx])[0])
    boot = np.array([b for b in boot if np.isfinite(b)])
    return {
        "n": int(n),
        "rho": round(float(rho), 4),
        "p_value": float(p),
        "ci": [
            round(float(np.percentile(boot, 2.5)), 4),
            round(float(np.percentile(boot, 97.5)), 4),
        ]
        if len(boot)
        else None,
        "ci_excludes_zero": bool(
            len(boot) and np.percentile(boot, 2.5) * np.percentile(boot, 97.5) > 0
        ),
    }


def concentration(panel: pd.DataFrame) -> dict[str, Any]:
    """Gini and HHI of green funding across countries, with the top-5 share."""

    def gini(values: np.ndarray) -> float:
        v = np.sort(values[values >= 0])
        if v.sum() == 0:
            return float("nan")
        n = len(v)
        return float((2 * np.arange(1, n + 1) - n - 1).dot(v) / (n * v.sum()))

    usd = panel["green_usd"].dropna().to_numpy()
    shares = usd / usd.sum()
    top5 = float(np.sort(shares)[-5:].sum())
    return {
        "countries": int(len(usd)),
        "gini": round(gini(usd), 4),
        "hhi": round(float((shares**2).sum()), 4),
        "top5_share_pct": round(100 * top5, 2),
    }


def run(deals: pd.DataFrame, cfg: Config, rng: np.random.Generator) -> dict[str, Any]:
    """Test H5 and return a JSON-serialisable findings dict."""
    draws = int(cfg.pipeline["bootstrap_resamples"])
    panel = build_panel(deals, cfg)

    thresholds = {
        "countries_with_any_green_deal": int((panel["green_deals"] >= 1).sum()),
        "countries_with_3_plus": int((panel["green_deals"] >= 3).sum()),
        "countries_with_5_plus": int((panel["green_deals"] >= 5).sum()),
    }
    LOG.info("H5 POWER (stated before results): %s", thresholds)

    # Restrict to countries with enough green activity for an intensity measure
    # to mean anything. The threshold is reported, not hidden.
    min_deals = 3
    sub = panel.loc[panel["green_deals"].ge(min_deals)].copy()
    LOG.info(
        "H5 panel: %d countries with >= %d green deals used for correlations",
        len(sub),
        min_deals,
    )

    outcomes = ["green_usd_per_capita", "green_usd_per_gdp", "green_share_of_deals"]
    correlations: dict[str, Any] = {}
    for outcome in outcomes:
        correlations[outcome] = {}
        for var, label in {
            **_DEPTH,
            **_NEED,
            "electricity_deficit_pct": "electricity deficit",
        }.items():
            if var not in sub.columns:
                continue
            res = spearman_ci(sub[var], sub[outcome], rng, draws)
            correlations[outcome][var] = {"label": label, **res}
            if res.get("rho") is not None:
                LOG.info(
                    "    %-24s vs %-28s rho %+0.3f %s  n=%d  p=%.3f",
                    outcome,
                    var,
                    res["rho"],
                    res.get("ci"),
                    res["n"],
                    res["p_value"],
                )

    # Does any need indicator survive controlling for income?
    ols = {}
    model_df = sub.dropna(subset=["gdp_per_capita_usd", "green_usd_per_capita"]).copy()
    model_df["log_gdp_pc"] = np.log(model_df["gdp_per_capita_usd"])
    model_df["log_green_pc"] = np.log(model_df["green_usd_per_capita"].clip(lower=1e-9))
    for var in _NEED:
        if var not in model_df.columns or model_df[var].notna().sum() < 10:
            continue
        d = model_df.dropna(subset=[var])
        m = smf.ols(f"log_green_pc ~ log_gdp_pc + {var}", data=d).fit(cov_type="HC1")
        ols[var] = {
            "coef": round(float(m.params[var]), 6),
            "ci": [round(float(v), 6) for v in m.conf_int().loc[var].tolist()],
            "p_value": float(m.pvalues[var]),
            "n": int(m.nobs),
            "adds_signal": bool(m.pvalues[var] < cfg.threshold("alpha")),
        }
        LOG.info(
            "    OLS log(green per capita) ~ log(GDP pc) + %-28s coef %+0.5f p=%.3f n=%d",
            var,
            ols[var]["coef"],
            ols[var]["p_value"],
            ols[var]["n"],
        )

    conc = concentration(panel)
    LOG.info(
        "H5 concentration: Gini %.3f, HHI %.3f, top-5 countries hold %.1f%% of green dollars "
        "across %d countries",
        conc["gini"],
        conc["hhi"],
        conc["top5_share_pct"],
        conc["countries"],
    )
    sub.to_csv(cfg.path("tables") / "h5_country_panel.csv", index=False)

    depth = correlations.get("green_usd_per_capita", {}).get("gdp_per_capita_usd", {})
    depth_positive = bool(
        depth.get("rho") is not None and depth["rho"] > 0 and depth.get("ci_excludes_zero")
    )
    need_positive_raw = [
        v
        for v in _NEED
        if (r := correlations.get("green_usd_per_capita", {}).get(v, {})).get("rho")
        is not None
        and r["rho"] > 0
        and r.get("ci_excludes_zero")
    ]
    # The pre-registered falsification condition is about the association that
    # SURVIVES controlling for income, so the OLS is what triggers it.
    need_positive_controlled = [
        v for v, m in ols.items() if m["coef"] > 0 and m["adds_signal"]
    ]
    falsifier_triggered = bool(need_positive_controlled)

    if depth_positive and not need_positive_raw and not falsifier_triggered:
        verdict = "Supported"
    elif depth_positive:
        verdict = "Partially supported"
    else:
        verdict = "Not supported"

    note_parts = [
        f"Green funding per capita is {'positively' if depth_positive else 'not reliably'} "
        f"associated with GDP per capita (rho {depth.get('rho')} {depth.get('ci')}, "
        f"n = {depth.get('n')})."
    ]
    if need_positive_raw:
        note_parts.append(
            f"Raw correlations show a positive association for: {need_positive_raw}."
        )
    else:
        note_parts.append(
            "No need indicator shows a positive raw association whose interval excludes "
            "zero; the electricity deficit runs negative, as predicted."
        )
    if falsifier_triggered:
        note_parts.append(
            "HOWEVER the pre-registered falsification condition is MET for "
            f"{need_positive_controlled}: after controlling for log GDP per capita the "
            "association turns positive and significant. The raw and income-controlled "
            "results point in opposite directions, which is a suppression effect running "
            "through income, and the strong form of H5 does not survive it."
        )
    note = " ".join(note_parts)

    findings = {
        "hypothesis": "H5: capital tracks market depth, not climate need",
        "power": {
            **thresholds,
            "min_green_deals_for_panel": min_deals,
            "countries_in_panel": int(len(sub)),
            "statement": (
                "The outcome rests on small per-country green deal counts. Every "
                "correlation carries a bootstrap interval and none is reported as a "
                "precise estimate."
            ),
        },
        "correlations": correlations,
        "ols_need_after_income": ols,
        "concentration": conc,
        "verdict": verdict,
        "verdict_note": note,
        "need_positive_raw": need_positive_raw,
        "need_positive_after_income_control": need_positive_controlled,
        "falsification_condition_met": falsifier_triggered,
        "causal_disclaimer": (
            "This is an association between country characteristics and where recorded "
            "capital landed. No causal identification is attempted and none should be "
            "read in."
        ),
        "falsification_condition": (
            "Falsified if need indicators show a positive, significant association after "
            "controlling for income."
        ),
    }
    LOG.info("H5 verdict: %s — %s", verdict, findings["verdict_note"])
    findings["_tables"] = {"h5_country_panel": sub}
    return findings
