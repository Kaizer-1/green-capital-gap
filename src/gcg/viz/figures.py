"""One function per figure, named ``fig_01_*`` … ``fig_12_*``.

Every figure obeys CLAUDE.md §8: a title that states the finding, a subtitle
giving unit and window, a 7pt source footer carrying the n, horizontal
gridlines only, no top or right spine, direct labelling in place of a legend,
and 300dpi PNG plus PDF under a deterministic filename.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from gcg.analysis import h1b_capital_intensity as h1b
from gcg.analysis import h2_cycle, h3_instrument, h5_allocation
from gcg.analysis.h1_selection import (
    green_rate_by_bloc,
    green_rate_by_year,
    two_proportion_test,
)
from gcg.config import Config, get_logger, load_config, seed_everything
from gcg.io import read_parquet
from gcg.viz import theme
from gcg.viz.theme import PALETTE as P

LOG = get_logger("viz.figures")


def fig_01_double_gap_and_capital_intensity(deals: pd.DataFrame, cfg: Config) -> None:
    """Figure 1: the gap is real, and it is not green-specific.

    Two panels, because the headline needs both. Panel (a) is the finding:
    conditional on being in the record, an emerging-market company is half as
    likely to be green. Panel (b) is the qualifier, and it cuts against the
    simplest reading of panel (a): capital intensity predicts the cross-sector
    pattern, and it over-predicts cleantech's gap. Putting the finding on page
    one and its qualifier in an appendix would be the same error as suppressing
    the finding.
    """
    theme.apply_theme()
    by_bloc = green_rate_by_bloc(deals, cfg).set_index("bloc")

    em, ae = deals.loc[deals["bloc"].eq("EM")], deals.loc[deals["bloc"].eq("AE")]
    cn = deals.loc[deals["bloc"].eq("CHINA")]
    test = two_proportion_test(
        int(em["green"].sum()), len(em), int(ae["green"].sum()), len(ae)
    )
    china_test = two_proportion_test(
        int(cn["green"].sum()), len(cn), int(ae["green"].sum()), len(ae)
    )
    ub = deals.copy()
    ub["b"] = ub["bloc"].replace({"UNASSIGNED": "EM"})
    em_ub = ub.loc[ub["b"].eq("EM")]
    ub_rate = 100 * em_ub["green"].mean()

    panel_b = h1b.run(deals, cfg)
    sectors = panel_b["_tables"]["h1b_sector_capital_intensity"]
    fitobj = panel_b["primary_fit"]
    res = panel_b["cleantech_residual_primary"]

    fig, (ax_a, ax_b) = plt.subplots(
        2, 1, figsize=theme.figsize(cfg, "stacked"), height_ratios=[1.0, 1.95]
    )

    # ---------------- panel (a): the double gap -------------------------
    # Every bloc is shown, including UNASSIGNED, so the rows sum to the n in the
    # footer. Leaving it out made the panel irreconcilable with its own source
    # line, and its rate is substantively useful: it sits between EM and AE,
    # which is what a blank-country bucket skewed away from the US should do.
    order = ["AE", "CHINA", "UNASSIGNED", "EM", "LDC"]
    short = {
        "AE": "Advanced economies",
        "CHINA": "China",
        "UNASSIGNED": "No country recorded",
        "EM": "Emerging markets",
        "LDC": "Least developed",
    }
    rows = by_bloc.reindex(order)
    y = np.arange(len(order))[::-1]
    xmax = 9.0

    tick_labels = []
    for yi, bloc in zip(y, order, strict=False):
        r = rows.loc[bloc]
        colour = P.accent_grey if bloc == "UNASSIGNED" else P.bloc(bloc)
        if bloc != "LDC":
            # The LDC interval runs to 22.8% on 13 deals. Drawing it implies a
            # precision that does not exist; the annotation says so instead.
            ax_a.plot(
                [r["ci_lo_pct"], min(r["ci_hi_pct"], xmax)],
                [yi, yi],
                color=colour,
                linewidth=1.6,
                solid_capstyle="butt",
                alpha=0.5,
                zorder=2,
            )
        ax_a.plot(r["green_rate_pct"], yi, "o", color=colour, markersize=7, zorder=4)
        ax_a.text(
            r["green_rate_pct"] + 0.18,
            yi + 0.3,
            f"{r['green_rate_pct']:.2f}%",
            va="center",
            ha="left",
            fontsize=8.5,
            color=colour,
            fontweight="bold",
        )
        tick_labels.append(f"{short[bloc]}  (n = {int(r['deals']):,})")

    em_y = y[order.index("EM")]
    ax_a.plot(
        ub_rate,
        em_y,
        "o",
        markerfacecolor="none",
        markeredgecolor=P.em,
        markersize=7,
        markeredgewidth=1.3,
        zorder=4,
    )
    theme.annotate(
        ax_a,
        "Upper bound: every unattributable deal\n"
        f"counted as emerging market ({ub_rate:.2f}%). Gap holds.",
        xy=(ub_rate, em_y),
        xytext=(ub_rate + 0.75, em_y - 0.55),
        color=P.ink_muted,
        fontsize=7.4,
    )

    # The risk ratio is a comparison, so it is anchored between the two rows it
    # compares rather than on one of them.
    ae_y, cn_y = y[order.index("AE")], y[order.index("CHINA")]
    mid_y = (ae_y + em_y) / 2
    bracket_x = 0.26
    ax_a.plot([bracket_x] * 2, [em_y, ae_y], color=P.ink_muted, linewidth=0.8, zorder=2)
    for yy in (em_y, ae_y):
        ax_a.plot(
            [bracket_x, bracket_x + 0.13], [yy, yy], color=P.ink_muted, linewidth=0.8, zorder=2
        )
    ax_a.text(
        bracket_x + 0.22,
        mid_y,
        f"EM vs AE\nrisk ratio {test['risk_ratio']:.2f}\n"
        f"[{test['risk_ratio_ci'][0]:.2f}, {test['risk_ratio_ci'][1]:.2f}]",
        va="center",
        ha="left",
        fontsize=7.8,
        color=P.ink,
        linespacing=1.35,
    )
    theme.annotate(
        ax_a,
        "China indistinguishable from AE\n"
        f"(risk ratio {china_test['risk_ratio']:.2f}, p = {china_test['p_value']:.2f})",
        xy=(rows.loc["CHINA", "green_rate_pct"], cn_y),
        xytext=(8.9, cn_y + 0.5),
        ha="right",
        color=P.china,
        fontsize=7.4,
    )
    ldc_y = y[order.index("LDC")]
    ax_a.text(
        0.22,
        ldc_y - 0.34,
        "0 of 13 deals: no usable interval",
        va="center",
        ha="left",
        fontsize=7.0,
        color=P.ldc,
        style="italic",
    )

    ax_a.set_xlim(0, xmax)
    ax_a.set_ylim(-0.75, len(order) - 0.35)
    ax_a.set_yticks(y)
    ax_a.set_yticklabels(tick_labels, fontsize=8.4)
    ax_a.tick_params(axis="y", length=0, pad=6)
    for lbl in ax_a.get_yticklabels():
        lbl.set_color(P.ink)
    ax_a.set_xlabel("Green share of the bloc's recorded deals")
    ax_a.xaxis.set_major_formatter(theme.fmt_pct)
    ax_a.spines["left"].set_visible(False)
    theme.style_axes(ax_a, xgrid=True)
    ax_a.grid(axis="y", visible=False)
    ax_a.set_title(
        "(a)  In the record, an emerging-market company is half as likely to be green",
        fontsize=9.3,
        fontfamily=theme.title_font(),
        color=P.ink,
        loc="left",
        pad=8,
    )

    # ---------------- panel (b): the capital-intensity ladder -----------
    s = sectors.sort_values("representation_ratio").rename(index={"<none>": "No sector tag"})
    yb = np.arange(len(s))
    obs = s["representation_ratio"].to_numpy()
    fit = np.exp(s["fitted_log_ratio"].to_numpy())
    ct = int(s.index.get_loc("cleantech"))
    bio = int(s.index.get_loc("biotech"))

    # Segment colour carries the panel's claim: green where a sector does better
    # than capital intensity predicts, ochre where it does worse.
    for yi, o, f in zip(yb, obs, fit, strict=False):
        ax_b.plot(
            [f, o],
            [yi, yi],
            color=P.accent_green if o > f else P.ae,
            linewidth=1.6,
            alpha=0.55,
            zorder=1,
        )

    ax_b.plot(
        fit,
        yb,
        "o",
        markerfacecolor="none",
        markeredgecolor=P.accent_grey,
        markersize=4.2,
        markeredgewidth=1.0,
        zorder=2,
    )
    ax_b.plot(obs, yb, "o", color=P.ink, markersize=4.2, zorder=3)

    ax_b.plot([fit[ct], obs[ct]], [ct, ct], color=P.focus, linewidth=2.4, zorder=3)
    ax_b.plot(
        fit[ct],
        ct,
        "o",
        markerfacecolor="none",
        markeredgecolor=P.focus,
        markersize=7.5,
        markeredgewidth=1.6,
        zorder=5,
    )
    ax_b.plot(obs[ct], ct, "o", color=P.focus, markersize=7.5, zorder=5)

    ax_b.axvline(1.0, color=P.ink_muted, linewidth=0.8, linestyle=(0, (4, 3)), zorder=0)

    ax_b.set_yticks(yb)
    ax_b.set_yticklabels([str(n).replace("_", " ") for n in s.index], fontsize=7.5)
    for lbl, name in zip(ax_b.get_yticklabels(), s.index, strict=False):
        if name == "cleantech":
            lbl.set_color(P.focus)
            lbl.set_fontweight("bold")
            lbl.set_fontsize(8.2)
        else:
            lbl.set_color(P.ink_muted)
    ax_b.tick_params(axis="y", length=0, pad=4)

    theme.annotate(
        ax_b,
        f"Cleantech sits {res['residual_ratio_scale']:.2f}x above its\n"
        f"predicted position [{res['residual_ratio_ci'][0]:.2f}x, "
        f"{res['residual_ratio_ci'][1]:.2f}x].\n"
        "Capital intensity OVER-predicts the gap.\n"
        "The interval includes 1x, so\noutperformance is not confirmed.",
        xy=(obs[ct], ct),
        xytext=(0.093, ct + 16.2),
        ha="left",
        color=P.focus,
        fontsize=7.3,
    )
    theme.annotate(
        ax_b,
        "Biotech: 4.6x more under-represented\n"
        "than cleantech, and below its own\nprediction too",
        xy=(obs[bio], bio),
        xytext=(0.093, bio + 12.6),
        ha="left",
        color=P.ae,
        fontsize=7.3,
    )

    ax_b.set_xscale("log")
    ax_b.set_xlim(0.085, 6.2)
    ax_b.set_ylim(-0.9, len(s) - 0.1)
    ax_b.set_xticks([0.1, 0.25, 0.5, 1, 2, 4])
    ax_b.set_xticklabels(["0.1x", "0.25x", "0.5x", "1x", "2x", "4x"])
    ax_b.set_xlabel(
        "Emerging-market representation relative to advanced economies "
        "(1x = proportionate), log scale"
    )
    ax_b.spines["left"].set_visible(False)
    theme.style_axes(ax_b, xgrid=True)
    ax_b.grid(axis="y", visible=False)
    ax_b.set_title(
        "(b)  Capital intensity drives the pattern \u2014 and green beats its prediction",
        fontsize=9.3,
        fontfamily=theme.title_font(),
        color=P.ink,
        loc="left",
        pad=8,
    )
    ax_b.text(
        0.985,
        0.275,
        f"elasticity {fitobj['slope']:.2f} [{fitobj['slope_ci'][0]:.2f}, "
        f"{fitobj['slope_ci'][1]:.2f}]\n"
        f"R\u00b2 = {fitobj['r_squared']:.2f}   \u00b7   {fitobj['n_sectors']} sectors",
        transform=ax_b.transAxes,
        fontsize=7.5,
        color=P.ink_muted,
        ha="right",
    )

    handles = [
        Line2D(
            [], [], marker="o", linestyle="none", color=P.ink, markersize=4.2, label="observed"
        ),
        Line2D(
            [],
            [],
            marker="o",
            linestyle="none",
            markerfacecolor="none",
            markeredgecolor=P.accent_grey,
            markersize=4.2,
            label="predicted by capital intensity",
        ),
        Line2D([], [], color=P.accent_green, linewidth=1.8, label="better than predicted"),
        Line2D([], [], color=P.ae, linewidth=1.8, label="worse than predicted"),
    ]
    leg = ax_b.legend(
        handles=handles,
        loc="lower right",
        fontsize=7.3,
        handletextpad=0.5,
        borderpad=0.3,
        bbox_to_anchor=(0.995, 0.015),
    )
    for txt in leg.get_texts():
        txt.set_color(P.ink_muted)

    theme.finding_title(
        fig,
        "The emerging-market green gap is real. It is not green-specific.",
        "Green share of recorded venture deals by bloc, and sector representation "
        "against capital intensity. 2000\u20132012.",
        y=0.965,
    )
    theme.source_footer(
        fig,
        cfg,
        f"Panel (a) n = {len(deals):,} deals, {int(deals['green'].sum()):,} green; "
        "bloc rows sum to the total. Panel (b) "
        f"{fitobj['n_sectors']} sectors with \u2265"
        f"{cfg.pipeline['capital_intensity']['min_em_deals']} emerging-market and \u2265"
        f"{cfg.pipeline['capital_intensity']['min_ae_deals']} advanced-economy deals; capital "
        "intensity is median advanced-economy deal size in constant 2015 USD, so the proxy "
        "cannot be contaminated by the emerging-market composition it explains. Intervals are "
        "Wilson score (a) and residual 95% CI (b). Headline is raw classifier output; "
        "bias-corrected risk ratio 0.44, curated 0.40 (Appendix C).",
        y=0.125,
    )
    fig.subplots_adjust(left=0.265, right=0.985, top=0.885, bottom=0.185, hspace=0.26)
    theme.save(fig, cfg, "fig_01_double_gap_capital_intensity")


def fig_m2_capital_intensity_regression(deals: pd.DataFrame, cfg: Config) -> None:
    """Methodology figure: the capital-intensity regression behind Figure 1b.

    The ladder in Figure 1b shows residuals, which is what the argument needs,
    but it asserts the fit rather than showing it. This shows the fit.

    The line is drawn from the model's own fitted values rather than
    re-evaluated from the coefficients, so the figure cannot disagree with the
    table it illustrates.
    """
    theme.apply_theme()
    panel = h1b.run(deals, cfg)
    s = panel["_tables"]["h1b_sector_capital_intensity"].rename(
        index={"<none>": "No sector tag"}
    )
    fitobj = panel["primary_fit"]
    res = panel["cleantech_residual_primary"]

    fig, ax = plt.subplots(figsize=theme.figsize(cfg, "single"))

    s = s.sort_values("median_deal_usd_real")
    x = s["median_deal_usd_real"].to_numpy() / 1e6
    yv = s["representation_ratio"].to_numpy()
    fitted = np.exp(s["fitted_log_ratio"].to_numpy())
    is_ct = np.array([n == "cleantech" for n in s.index])

    ax.plot(x, fitted, color=P.alert, linewidth=1.4, zorder=2)
    ax.scatter(x[~is_ct], yv[~is_ct], s=26, color=P.ink, zorder=3, linewidths=0)
    ax.scatter(x[is_ct], yv[is_ct], s=90, color=P.focus, zorder=4, linewidths=0)
    ax.plot(
        [x[is_ct][0], x[is_ct][0]],
        [fitted[is_ct][0], yv[is_ct][0]],
        color=P.focus,
        linewidth=1.8,
        zorder=3,
    )
    ax.axhline(1.0, color=P.ink_muted, linewidth=0.8, linestyle=(0, (4, 3)), zorder=0)

    for name, xi, yi in zip(s.index, x, yv, strict=False):
        if name in {"biotech", "ecommerce", "travel", "hardware", "software", "social"}:
            ax.annotate(
                str(name),
                (xi, yi),
                textcoords="offset points",
                xytext=(7, -2),
                fontsize=7.4,
                color=P.ink_muted,
            )
    ct_x, ct_y = float(x[is_ct][0]), float(yv[is_ct][0])
    ax.annotate(
        "cleantech",
        (ct_x, ct_y),
        textcoords="offset points",
        xytext=(-9, 9),
        fontsize=8.0,
        color=P.focus,
        fontweight="bold",
        ha="right",
    )

    theme.annotate(
        ax,
        f"Cleantech sits {res['residual_ratio_scale']:.2f}x above the fit\n"
        f"[{res['residual_ratio_ci'][0]:.2f}x, {res['residual_ratio_ci'][1]:.2f}x]: "
        "capital intensity\nover-predicts the emerging-market green gap.",
        xy=(ct_x, (ct_y * float(fitted[is_ct][0])) ** 0.5),
        xytext=(10.2, 1.95),
        ha="right",
        color=P.focus,
        fontsize=7.4,
    )

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.65, 10.5)
    ax.set_ylim(0.085, 6.0)
    ax.set_xlabel(
        "Sector capital intensity: median advanced-economy deal size, "
        "constant 2015 USD, log scale"
    )
    ax.set_ylabel("EM representation\nrelative to AE (log)")
    ax.set_yticks([0.1, 0.25, 0.5, 1, 2, 4])
    ax.set_yticklabels(["0.1x", "0.25x", "0.5x", "1x", "2x", "4x"])
    ax.set_xticks([0.8, 1, 2, 3, 5, 8])
    ax.set_xticklabels(["$0.8m", "$1m", "$2m", "$3m", "$5m", "$8m"])
    # Log axes emit minor-tick labels such as "6 x 10^0" by default.
    ax.minorticks_off()
    theme.style_axes(ax, xgrid=True)
    ax.text(
        0.015,
        0.028,
        f"log(ratio) = {fitobj['intercept']:.2f} {fitobj['slope']:+.2f} "
        "\u00b7 log(deal size)"
        f"   \u00b7   R\u00b2 = {fitobj['r_squared']:.2f}"
        f"   \u00b7   p = {fitobj['slope_p']:.1e}",
        transform=ax.transAxes,
        fontsize=7.5,
        color=P.alert,
    )

    theme.finding_title(
        fig,
        "Emerging-market representation falls roughly in proportion to capital intensity",
        f"{fitobj['n_sectors']} sectors, 2000\u20132012. Elasticity "
        f"{fitobj['slope']:.2f} [{fitobj['slope_ci'][0]:.2f}, {fitobj['slope_ci'][1]:.2f}].",
        y=0.935,
    )
    theme.source_footer(
        fig,
        cfg,
        f"{fitobj['n_sectors']} sectors with \u2265"
        f"{cfg.pipeline['capital_intensity']['min_em_deals']} emerging-market and \u2265"
        f"{cfg.pipeline['capital_intensity']['min_ae_deals']} advanced-economy deals, from "
        f"n = {len(deals):,} deals. The capital-intensity proxy uses advanced-economy deals "
        "only, so it cannot be contaminated by the emerging-market composition it explains. "
        "Ordinary least squares on logs; the line is the model's fitted values. The secondary "
        "proxy, median cumulative funding per company, gives an elasticity of -0.96 with "
        "R-squared 0.69.",
        y=0.205,
        width=112,
    )
    fig.subplots_adjust(left=0.135, right=0.98, top=0.845, bottom=0.355)
    theme.save(fig, cfg, "fig_m2_capital_intensity_regression")


def fig_02_coverage_vs_gdp(deals: pd.DataFrame, cfg: Config) -> None:
    """Figure 2: gap one, the denominator check.

    Its only job is to show that the conditional green-rate gap in Figure 1a is
    not the coverage gap restated. Emerging markets hold a fifth of world GDP
    and a fiftieth of the venture record; that is a fact about the dataset, and
    it is why the headline result is measured *within* the dataset instead.
    """
    theme.apply_theme()
    tab = pd.read_csv(cfg.path("tables") / "diag_coverage_bias_by_bloc_year.csv")
    em = tab.loc[tab["bloc"].eq("EM")].sort_values("year")

    fig, ax = plt.subplots(figsize=theme.figsize(cfg, "single"))
    ax.fill_between(
        em["year"], em["deal_share_pct"], em["gdp_share_pct"], color=P.em, alpha=0.10, zorder=1
    )
    ax.plot(em["year"], em["gdp_share_pct"], color=P.ink, linewidth=1.8, zorder=3)
    ax.plot(em["year"], em["deal_share_pct"], color=P.em, linewidth=1.8, zorder=3)

    last = em.iloc[-1]
    ax.text(
        last["year"] + 0.12,
        last["gdp_share_pct"],
        "share of\nworld GDP",
        va="center",
        ha="left",
        fontsize=8,
        color=P.ink,
        linespacing=1.3,
    )
    ax.text(
        last["year"] + 0.12,
        last["deal_share_pct"],
        "share of recorded\nventure deals",
        va="center",
        ha="left",
        fontsize=8,
        color=P.em,
        linespacing=1.3,
    )

    worst = em.loc[em["representation_ratio"].idxmin()]
    theme.annotate(
        ax,
        f"Widest in {int(worst['year'])}: {worst['gdp_share_pct']:.1f}% of world GDP,\n"
        f"{worst['deal_share_pct']:.1f}% of recorded deals "
        f"\u2014 {1 / worst['representation_ratio']:.0f}x under-represented",
        xy=(worst["year"], (worst["gdp_share_pct"] + worst["deal_share_pct"]) / 2),
        xytext=(2004.6, 13.0),
        color=P.ink_muted,
        fontsize=7.6,
    )

    ax.set_xlim(em["year"].min() - 0.3, em["year"].max() + 2.4)
    ax.set_ylim(0, 25)
    ax.yaxis.set_major_formatter(theme.fmt_pct)
    ax.set_xlabel("Year the deal closed")
    ax.set_ylabel("Emerging-market share")
    theme.style_axes(ax)
    theme.finding_title(
        fig,
        "Emerging markets hold a fifth of world GDP and a fiftieth of the venture record",
        "Emerging-market share of world GDP against its share of recorded venture deals, "
        "2000\u20132012.",
        y=0.945,
    )
    theme.source_footer(
        fig,
        cfg,
        f"n = {len(deals):,} deals. GDP shares are computed over the same country set the "
        "bloc panel covers, so the two series are comparable by construction. This is the "
        "denominator check for Figure 1: it establishes that the conditional green-rate gap "
        "is not this coverage gap restated.",
        y=0.195,
        width=108,
    )
    fig.subplots_adjust(left=0.105, right=0.985, top=0.84, bottom=0.30)
    theme.save(fig, cfg, "fig_02_coverage_vs_gdp")


def fig_03_green_rate_by_year(deals: pd.DataFrame, cfg: Config) -> None:
    """Figure 3: the gap over time, with every emerging-market cell flagged.

    The substantive point is the 2008 convergence. At the peak of Cleantech 1.0
    the two rates were within a sixth of a percentage point of each other; the
    gap opens only after the crash. No emerging-market year-cell reaches the
    minimum cell size, so nothing here is tested and the figure says so.
    """
    theme.apply_theme()
    by_year = green_rate_by_year(deals)
    ae = by_year.loc[by_year["bloc"].eq("AE")].sort_values("year")
    em = by_year.loc[by_year["bloc"].eq("EM")].sort_values("year")

    fig, ax = plt.subplots(figsize=theme.figsize(cfg, "single"))
    ax.plot(ae["year"], ae["green_rate_pct"], color=P.ae, linewidth=1.8, zorder=3)
    ax.plot(
        em["year"],
        em["green_rate_pct"],
        color=P.em,
        linewidth=1.8,
        zorder=3,
        linestyle=(0, (5, 2)),
    )
    ax.scatter(em["year"], em["green_rate_pct"], s=18, color=P.em, zorder=4)

    # Only non-zero counts are printed. Seven "0" labels along the axis would be
    # noise; the footer states that 2000-2006 contain no emerging-market green
    # deals at all, which is the more useful way to say it.
    for _, r in em.iterrows():
        if int(r["green_deals"]) == 0:
            continue
        ax.annotate(
            f"{int(r['green_deals'])}",
            (r["year"], r["green_rate_pct"]),
            textcoords="offset points",
            xytext=(0, -12),
            ha="center",
            fontsize=6.8,
            color=P.em,
        )

    ax.text(
        ae["year"].iloc[-1] + 0.12,
        ae["green_rate_pct"].iloc[-1],
        "Advanced economies",
        va="center",
        ha="left",
        fontsize=8,
        color=P.ae,
    )
    ax.text(
        em["year"].iloc[-1] + 0.12,
        em["green_rate_pct"].iloc[-1],
        "Emerging markets",
        va="center",
        ha="left",
        fontsize=8,
        color=P.em,
    )

    y08_ae = float(ae.loc[ae["year"].eq(2008), "green_rate_pct"].iloc[0])
    y08_em = float(em.loc[em["year"].eq(2008), "green_rate_pct"].iloc[0])
    theme.annotate(
        ax,
        f"2008: the rates converge\n({y08_em:.2f}% vs {y08_ae:.2f}%).\n"
        "The gap opens only after the crash.",
        xy=(2008, (y08_ae + y08_em) / 2),
        xytext=(2002.4, 8.6),
        color=P.ink,
        fontsize=7.6,
    )

    ax.set_xlim(1999.7, 2014.6)
    ax.set_ylim(0, 11.5)
    ax.yaxis.set_major_formatter(theme.fmt_pct)
    ax.set_xlabel(
        "Year the deal closed  \u00b7  numbers beside the emerging-market line "
        "are green deal counts"
    )
    ax.set_ylabel("Green share of the\nbloc's recorded deals", labelpad=8)
    theme.style_axes(ax)
    theme.finding_title(
        fig,
        "The two rates met in 2008, at the peak of Cleantech 1.0, then diverged",
        "Green share of recorded deals by bloc and year, 2000\u20132012.",
        y=0.945,
    )
    theme.source_footer(
        fig,
        cfg,
        f"n = {len(deals):,} deals. NO emerging-market year-cell reaches the minimum cell "
        f"size of {int(cfg.threshold('min_cell_n'))} green deals \u2014 the largest is 12, in "
        "2008 \u2014 so no per-year test is reported and this figure is descriptive only. "
        "Counts are printed under each emerging-market point so the reader can see the "
        "precision available. Raw classifier output.",
        y=0.205,
        width=108,
    )
    fig.subplots_adjust(left=0.125, right=0.985, top=0.84, bottom=0.31)
    theme.save(fig, cfg, "fig_03_green_rate_by_year")


def fig_04_subdomain_resolution(deals: pd.DataFrame, cfg: Config) -> None:
    """Figure 4: the taxonomy cannot resolve green sub-domains in emerging markets.

    This replaces the sub-domain mix comparison that was cut. It reports the
    measurement failure itself, which is a finding: the record cannot say what
    *kind* of green an emerging-market company is.
    """
    theme.apply_theme()
    green = deals.loc[deals["green"] & deals["green_subdomain"].notna()]
    tab = pd.crosstab(green["bloc"], green["green_subdomain"])
    order = [b for b in ("AE", "CHINA", "EM") if b in tab.index]
    tab = tab.reindex(order)
    shares = tab.div(tab.sum(axis=1), axis=0) * 100

    unspec = shares.get("general_unspecified", pd.Series(0.0, index=shares.index))
    specific = 100 - unspec

    fig, ax = plt.subplots(figsize=theme.figsize(cfg, "single"))
    y = np.arange(len(order))[::-1]
    ax.barh(y, unspec, color=P.accent_grey, height=0.44, zorder=3)
    ax.barh(y, specific, left=unspec, color=P.accent_green, height=0.44, zorder=3)

    # Direct labelling on the first bar, in place of a legend (CLAUDE.md §8).
    top = y[0]
    ax.text(
        unspec.iloc[0] / 2,
        top + 0.42,
        'tagged only "Clean Technology"',
        ha="center",
        va="bottom",
        fontsize=7.6,
        color=P.accent_grey,
    )
    ax.text(
        unspec.iloc[0] + specific.iloc[0] / 2,
        top + 0.42,
        "resolved to a\nspecific sub-domain",
        ha="center",
        va="bottom",
        fontsize=7.6,
        color=P.accent_green,
        linespacing=1.3,
    )

    labels = cfg.blocs["display"]["labels"]
    for yi, bloc in zip(y, order, strict=False):
        ax.text(
            unspec[bloc] / 2,
            yi,
            f"{unspec[bloc]:.1f}%",
            va="center",
            ha="center",
            fontsize=8.2,
            color="white",
            fontweight="bold",
            zorder=4,
        )
        n = int(tab.loc[bloc].sum())
        ax.text(
            -1.2,
            yi,
            f"{labels.get(bloc, bloc).split(' (')[0]}\n(n = {n:,} green deals)",
            va="center",
            ha="right",
            fontsize=8.2,
            color=P.ink,
            linespacing=1.4,
        )

    theme.annotate(
        ax,
        "26 of the 28 emerging-market green companies carry\n"
        'no tag more specific than "Clean Technology"',
        xy=(unspec["EM"] * 0.72, y[order.index("EM")]),
        xytext=(21, y[order.index("EM")] - 0.62),
        color=P.ink,
        fontsize=7.6,
    )

    ax.set_xlim(0, 100)
    ax.set_ylim(-1.15, len(order) + 0.25)
    ax.set_yticks([])
    ax.xaxis.set_major_formatter(theme.fmt_pct)
    ax.set_xlabel("Share of the bloc's green deals")
    ax.spines["left"].set_visible(False)
    theme.style_axes(ax, xgrid=True)
    ax.grid(axis="y", visible=False)
    theme.finding_title(
        fig,
        "The taxonomy cannot say what kind of green an emerging-market company is",
        "Share of green deals resolved to a specific sub-domain, by bloc, 2000\u20132012.",
        y=0.945,
    )
    theme.source_footer(
        fig,
        cfg,
        f"n = {int(green.shape[0]):,} green deals carrying a sub-domain label. The eleven "
        "specific sub-domains are solar, wind/hydro/geothermal, biofuels, storage, "
        "efficiency and smart grid, electric mobility, water, waste and circular, "
        "sustainable agriculture, green building, and environmental monitoring. This "
        "figure replaces the planned emerging-market sub-domain mix comparison, which the "
        "measurement failure shown here makes impossible.",
        y=0.205,
        width=108,
    )
    fig.subplots_adjust(left=0.235, right=0.985, top=0.805, bottom=0.30)
    theme.save(fig, cfg, "fig_04_subdomain_resolution")


def fig_05_cycle(deals: pd.DataFrame, cfg: Config) -> None:
    """Figure 5: the Cleantech 1.0 cycle, in deals and in constant dollars."""
    theme.apply_theme()
    amount = cfg.pipeline["deflate"]["real_column"]
    g = deals.loc[deals["green"]]
    by_year = (
        g.groupby("year")
        .agg(
            deals=("id", "size"),
            usd=(amount, lambda s: float(s.sum())),
            disclosed=(amount, "count"),
            median=(amount, "median"),
        )
        .reset_index()
    )

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=theme.figsize(cfg, "stacked"), sharex=True)

    ax1.bar(by_year["year"], by_year["deals"], color=P.accent_green, width=0.62, zorder=3)
    ax1.set_ylabel("Green deals")
    theme.style_axes(ax1)
    ax1.set_title(
        "(a)  Deal count",
        fontsize=9.3,
        fontfamily=theme.title_font(),
        color=P.ink,
        loc="left",
        pad=6,
    )

    ax2.bar(by_year["year"], by_year["usd"] / 1e9, color=P.accent_green, width=0.62, zorder=3)
    ax2.set_ylabel("Green funding\n($bn, constant 2015)")
    ax2.set_xlabel("Year the deal closed")
    theme.style_axes(ax2)
    ax2.set_title(
        "(b)  Disclosed dollars, constant 2015 USD",
        fontsize=9.3,
        fontfamily=theme.title_font(),
        color=P.ink,
        loc="left",
        pad=6,
    )

    peak = by_year.loc[by_year["deals"].idxmax()]
    dollar_peak = by_year.loc[by_year["usd"].idxmax()]
    for ax in (ax1, ax2):
        # Above the bars, not behind them: at zorder 0 these were hidden.
        ax.axvline(2008, color=P.ink_muted, linewidth=0.8, alpha=0.30, zorder=5)
    theme.annotate(
        ax1,
        "Global financial crisis",
        xy=(2008, by_year.loc[by_year["year"].eq(2008), "deals"].iloc[0] * 0.55),
        xytext=(2002.6, by_year["deals"].max() * 0.80),
        color=P.ink_muted,
        fontsize=7.4,
    )
    theme.annotate(
        ax1,
        f"Deal count peaks at {int(peak['deals'])} in {int(peak['year'])}",
        xy=(peak["year"], peak["deals"]),
        xytext=(2002.6, by_year["deals"].max() * 0.97),
        color=P.ink,
        fontsize=7.4,
    )
    theme.annotate(
        ax2,
        f"Dollars peak in {int(dollar_peak['year'])}, a year BEFORE deals do.\n"
        "Within named stages, green deal sizes fall 49pp more\n"
        "than non-green over 2007-12 [CI -69 to -22]. The POOLED\n"
        "median falls alike in both: that comparison is confounded.",
        xy=(dollar_peak["year"], dollar_peak["usd"] / 1e9),
        xytext=(2000.2, by_year["usd"].max() / 1e9 * 0.70),
        color=P.ink,
        fontsize=7.4,
    )

    theme.finding_title(
        fig,
        "Green deal sizes fell far faster than non-green within the same stages",
        "Green deals and disclosed green funding, all blocs, 2000\u20132012. "
        "Constant 2015 USD.",
        y=0.955,
    )
    theme.source_footer(
        fig,
        cfg,
        f"n = {int(g.shape[0]):,} green deals, of which {int(by_year['disclosed'].sum()):,} "
        "carry a disclosed amount. Counts and dollars are reported as separate series "
        "because undisclosed-amount rates differ systematically by instrument and bloc; "
        "panel (b) covers only the disclosed subsample. Constant 2015 USD via the US GDP "
        "deflator. The cheque-size claim is the WITHIN-STAGE comparison: the pooled median "
        "falls about 72% for green and 73% for non-green, but that is composition-"
        "confounded for both, since holding the 2007 stage mix fixed leaves non-green at "
        "-11%. Bootstrapped over 10,000 draws on clean stage codes, excluding the "
        "venture_unspecified catch-all: green -50.4% against non-green -1.1%, difference "
        "-49.3pp [-69.3, -22.4]. All five start-end pairs running to the window close are "
        "negative (-69.9 to -21.5pp) and -49.3 is their median, so the direction is robust "
        "to the start year; pairs stopping before the decline completes can turn positive, "
        "so it is sensitive to the end year. This is a size pattern, not an investor "
        "motive. Raw classifier output.",
        y=0.072,
        width=118,
    )
    fig.subplots_adjust(left=0.135, right=0.985, top=0.885, bottom=0.20, hspace=0.22)
    theme.save(fig, cfg, "fig_05_cycle")


def fig_06_green_share_of_all(deals: pd.DataFrame, cfg: Config) -> None:
    """Figure 6: green's share of deals against its share of dollars.

    An earlier draft of this figure plotted the green rate by bloc and year,
    which is what Figure 3 already does; it was replaced because a figure with
    no job of its own should be cut.

    This version asks a question Figure 3 cannot: was a green deal bigger or
    smaller than an average deal? Green's dollar share running above its count
    share means green deals were larger, which is CONSISTENT WITH green being
    capital-intensive. It does not corroborate the cross-sector elasticity in
    Figure 1b: that is a different claim, about how representation varies with
    capital intensity across sectors. This figure speaks only to green's own
    average deal size over time.
    """
    theme.apply_theme()
    amount = cfg.pipeline["deflate"]["real_column"]
    by_year = (
        deals.groupby("year")
        .apply(
            lambda d: pd.Series(
                {
                    "count_share": 100 * d["green"].mean(),
                    "dollar_share": 100
                    * d.loc[d["green"], amount].sum()
                    / max(d[amount].sum(), 1e-9),
                    "deals": len(d),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )

    # The pre-2005 reversal rests on very few green deals; the footer carries
    # the counts so a reader can weigh it.
    early = deals.loc[deals["year"].lt(2005) & deals["green"]]
    early_counts = early.groupby("year").size()
    pre2005 = ", ".join(f"{int(y)} n={int(n)}" for y, n in early_counts.items()) or "none"

    fig, ax = plt.subplots(figsize=theme.figsize(cfg, "single"))
    ax.fill_between(
        by_year["year"],
        by_year["count_share"],
        by_year["dollar_share"],
        where=by_year["dollar_share"] >= by_year["count_share"],
        color=P.accent_green,
        alpha=0.12,
        zorder=1,
    )
    ax.plot(
        by_year["year"], by_year["dollar_share"], color=P.accent_green, linewidth=2.0, zorder=3
    )
    ax.plot(
        by_year["year"],
        by_year["count_share"],
        color=P.ink,
        linewidth=1.6,
        zorder=3,
        linestyle=(0, (5, 2)),
    )

    last = by_year.iloc[-1]
    ax.text(
        last["year"] + 0.12,
        last["dollar_share"],
        "share of green\ndollars",
        va="center",
        ha="left",
        fontsize=8,
        color=P.accent_green,
        linespacing=1.3,
    )
    ax.text(
        last["year"] + 0.12,
        last["count_share"] - 0.4,
        "share of green\ndeals",
        va="center",
        ha="left",
        fontsize=8,
        color=P.ink,
        linespacing=1.3,
    )

    peak = by_year.loc[by_year["dollar_share"].idxmax()]
    theme.annotate(
        ax,
        "The two series CROSS in 2005. Before then a green\n"
        "deal was smaller than average; from 2005 on it was\n"
        "larger, peaking at roughly twice the count share.",
        xy=(2005, float(by_year.loc[by_year["year"].eq(2005), "dollar_share"].iloc[0])),
        xytext=(2000.2, 13.2),
        color=P.ink,
        fontsize=7.6,
    )
    theme.annotate(
        ax,
        f"Peak: {peak['dollar_share']:.1f}% of all venture\n"
        f"dollars in {int(peak['year'])}, against a "
        f"{float(by_year.loc[by_year['year'].eq(peak['year']), 'count_share'].iloc[0]):.1f}%\n"
        "share of deals",
        xy=(peak["year"], peak["dollar_share"]),
        xytext=(peak["year"] + 0.6, peak["dollar_share"] + 1.9),
        color=P.accent_green,
        fontsize=7.6,
    )

    ax.set_xlim(1999.7, 2014.8)
    ax.set_ylim(0, 25)
    ax.yaxis.set_major_formatter(theme.fmt_pct)
    ax.set_xlabel("Year the deal closed")
    ax.set_ylabel("Green share of all\nrecorded venture activity")
    theme.style_axes(ax)
    theme.finding_title(
        fig,
        "From 2005, green took a bigger share of venture dollars than of deals",
        "Green as a share of all recorded deals and of all disclosed dollars, "
        "2000\u20132012. Constant 2015 USD.",
        y=0.945,
    )
    theme.source_footer(
        fig,
        cfg,
        f"n = {len(deals):,} deals, {int(deals['green'].sum()):,} green. The dollar series "
        "covers the disclosed subsample only, and both series are computed on that same "
        "subsample's denominator where dollars are concerned, so the comparison is "
        "internally consistent. A dollar share above the count share means the average "
        "green cheque exceeded the average cheque overall, which is consistent with green "
        "being capital-intensive; it does not test the cross-sector elasticity of Figure "
        "1b. The ordering reverses before 2005, when green deals were SMALLER than "
        f"average, on thin cells: {pre2005}. Raw classifier output.",
        y=0.195,
        width=108,
    )
    fig.subplots_adjust(left=0.125, right=0.845, top=0.84, bottom=0.30)
    theme.save(fig, cfg, "fig_06_green_share_of_all")


def fig_12_continuity_india(deals: pd.DataFrame, cfg: Config) -> None:
    """Figure 12: the continuity probe, deliberately kept apart from the main series.

    The two panels never share an axis. Pooling them would be the error the
    brief warns about most explicitly, and the visual separation is the
    argument: the later window is a different instrument measuring a different
    population, and it reproduces the same measurement problem.
    """
    theme.apply_theme()
    india = pd.read_csv(cfg.path("tables") / "fig12_india_continuity.csv")
    india = india.loc[india["year"].between(2015, 2019)]
    em = deals.loc[deals["bloc"].eq("EM")]
    em_year = em.groupby("year")["green"].agg(deals="size", green="sum").reset_index()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.9), width_ratios=[1.25, 1.0])

    ax1.bar(em_year["year"], em_year["green"], color=P.em, width=0.62, zorder=3)
    ax1.set_title(
        "Crunchbase, emerging markets\n2000\u20132012",
        fontsize=8.8,
        fontfamily=theme.title_font(),
        color=P.em,
        loc="left",
        pad=6,
    )
    ax1.set_ylabel("Green deals recorded")
    ax1.set_ylim(0, 20)
    theme.style_axes(ax1)

    ax2.bar(india["year"], india["green_deals"], color=P.ldc, width=0.62, zorder=3)
    ax2.set_title(
        "Indian funding scrape\n2015\u20132019",
        fontsize=8.8,
        fontfamily=theme.title_font(),
        color=P.ldc,
        loc="left",
        pad=6,
    )
    ax2.set_ylim(0, 20)
    theme.style_axes(ax2)
    ax2.tick_params(labelleft=False)

    for ax in (ax1, ax2):
        ax.set_xlabel("Year")

    # The divider is positioned from the realised axes geometry. Hard-coding a
    # figure fraction put it inside the left panel, drawing a red line through
    # the data.
    fig.subplots_adjust(left=0.105, right=0.985, top=0.78, bottom=0.33, wspace=0.10)
    gap = (ax1.get_position().x1 + ax2.get_position().x0) / 2
    fig.text(
        gap,
        0.555,
        "NOT COMPARABLE",
        rotation=90,
        ha="center",
        va="center",
        fontsize=7.2,
        color=P.alert,
        fontweight="bold",
    )
    for y0, y1 in ((0.345, 0.47), (0.645, 0.775)):
        fig.lines.append(
            plt.Line2D(
                [gap, gap], [y0, y1], transform=fig.transFigure, color=P.alert, linewidth=0.9
            )
        )

    theme.finding_title(
        fig,
        "A later window in one large emerging market reproduces the same scarcity",
        "Green deals per year. Two different instruments measuring two different "
        "populations; the panels share no axis.",
        y=0.93,
    )
    theme.source_footer(
        fig,
        cfg,
        "Left: Crunchbase 2013 Snapshot, emerging markets excluding China and LDCs, "
        f"{int(em['green'].sum())} green deals. Right: the Indian startup funding scrape, "
        "3,036 dated deals of which 54 are green under the SAME lexicon, $502m nominal. "
        "The two are never pooled: taxonomies and amount conventions are not compatible, no "
        "category_code exists in the Indian data so Tier A cannot fire, and the scrape's "
        "coverage rules are unknown. 2020 is a partial year and is excluded.",
        y=0.235,
        width=108,
    )
    theme.save(fig, cfg, "fig_12_continuity_india")


def fig_m1_censoring_artefact(cfg: Config) -> None:
    """Methodology figure: the censoring boundary, established rather than assumed.

    CLAUDE.md asked for the uncensored tail plotted as an artefact. Measuring it
    turned out to matter: the spec expected 2013 to look like a crash, and it
    does not. Only December is incomplete, and the seasonal comparison is what
    establishes that.
    """
    theme.apply_theme()
    tab = pd.read_csv(cfg.path("tables") / "diag_censoring_monthly_counts.csv", index_col=0)

    fig, ax = plt.subplots(figsize=theme.figsize(cfg, "single"))
    months = tab.index.to_numpy()
    styles = {"2011": (P.accent_grey, "-"), "2012": (P.ink_muted, "-"), "2013": (P.alert, "-")}
    for year, (colour, ls) in styles.items():
        col = f"share_pct_{year}"
        if col not in tab.columns:
            continue
        ax.plot(
            months,
            tab[col],
            color=colour,
            linewidth=1.9 if year == "2013" else 1.4,
            linestyle=ls,
            zorder=4 if year == "2013" else 3,
        )
        ax.text(
            12.18,
            tab[col].iloc[-1],
            year,
            va="center",
            ha="left",
            fontsize=8,
            color=colour,
            fontweight="bold" if year == "2013" else "normal",
        )

    theme.annotate(
        ax,
        "December 2013 holds 3.8% of its year\nagainst a 7.5% baseline. The snapshot\n"
        "was taken mid-December; only this month\nis incomplete, not the year.",
        xy=(12, tab["share_pct_2013"].iloc[-1]),
        xytext=(4.6, 4.3),
        color=P.alert,
        fontsize=7.6,
    )
    theme.annotate(
        ax,
        "November 2013 is ABOVE both earlier\nyears, so coverage was not decaying",
        xy=(11, tab["share_pct_2013"].iloc[-2]),
        xytext=(5.0, 10.6),
        color=P.ink_muted,
        fontsize=7.6,
    )

    ax.set_xlim(0.6, 13.1)
    ax.set_ylim(0, 13)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
    ax.yaxis.set_major_formatter(theme.fmt_pct)
    ax.set_xlabel("Month the deal closed")
    ax.set_ylabel("Share of that year's deals")
    theme.style_axes(ax)
    theme.finding_title(
        fig,
        "Only December 2013 is censored, which is why the window closes at 2012",
        "Monthly deals as a share of their own year, 2011\u20132013.",
        y=0.945,
    )
    theme.source_footer(
        fig,
        cfg,
        "Deal counts before the analysis window is applied. Expressing each month as a share "
        "of its own year removes the level difference between years so the shapes are "
        "comparable. The disclosed-amount rate is flat across these years (88.99 / 88.61 / "
        "88.44%), and November and December 2013 are among the highest monthly rates in the "
        "series, so dollars are not differentially censored either. The window still closes "
        "at 2012-12-31, on the coverage-growth argument rather than this one.",
        y=0.22,
        width=108,
    )
    fig.subplots_adjust(left=0.105, right=0.975, top=0.84, bottom=0.325)
    theme.save(fig, cfg, "fig_m1_censoring_artefact")


def fig_07_crisis_contraction(deals: pd.DataFrame, cfg: Config) -> None:
    """Figure 7: the crisis hit green and spared non-green, descriptively.

    No difference-in-differences coefficient plot accompanies this figure,
    because the design did not identify one: pre-trends fail. Plotting a
    coefficient whose identifying assumption failed would present a number the
    analysis is not entitled to. The indexed series carries the descriptive
    claim and the annotation states the limit on it.
    """
    theme.apply_theme()
    res = h2_cycle.run(deals, cfg)
    series = res["_tables"]["h2_indexed_series"]
    base = int(cfg.window["did_index_base_year"])

    fig, ax = plt.subplots(figsize=theme.figsize(cfg, "single"))
    styles = {
        "AE-green": (P.accent_green, "-", 2.0),
        "AE-non-green": (P.accent_grey, "-", 1.6),
        "EM-green": (P.em, (0, (5, 2)), 1.4),
    }
    for name, (colour, ls, lw) in styles.items():
        sub = series.loc[series["series"].eq(name)].sort_values("year")
        if sub.empty:
            continue
        ax.plot(
            sub["year"], sub["indexed"], color=colour, linestyle=ls, linewidth=lw, zorder=3
        )
        last = sub.iloc[-1]
        ax.text(
            last["year"] + 0.15,
            last["indexed"],
            name.replace("-", " "),
            va="center",
            ha="left",
            fontsize=8,
            color=colour,
        )

    ax.axhline(100, color=P.ink_muted, linewidth=0.8, linestyle=(0, (4, 3)), zorder=0)
    ax.axvline(2008, color=P.rule, linewidth=1.0, zorder=0)

    cd = res["crisis_drawdown"]
    theme.annotate(
        ax,
        f"Across 2008-09 advanced-economy green contracted\n"
        f"{cd['AE-green']['contraction_pct']:.1f}% while non-green GREW "
        f"{cd['AE-non-green']['contraction_pct']:+.1f}%.",
        xy=(
            2009,
            float(
                series.loc[
                    series["series"].eq("AE-green") & series["year"].eq(2009), "indexed"
                ].iloc[0]
            ),
        ),
        xytext=(2000.3, 330),
        color=P.ink,
        fontsize=7.6,
    )
    theme.annotate(
        ax,
        "Pre-trends diverge, so no difference-in-differences\n"
        "estimate is reported. These series are descriptive.",
        xy=(2004, 120),
        xytext=(2000.3, 232),
        color=P.alert,
        fontsize=7.6,
    )

    ax.set_xlim(1999.7, 2014.4)
    ax.set_ylim(0, 420)
    ax.set_xlabel("Year the deal closed")
    ax.set_ylabel(f"Deal volume, {base} = 100")
    theme.style_axes(ax)
    theme.finding_title(
        fig,
        "The crisis hit green venture funding and left non-green growing",
        f"Deal volume indexed to {base}, by bloc and green status, 2000\u20132012.",
        y=0.945,
    )
    theme.source_footer(
        fig,
        cfg,
        f"n = {len(deals):,} deals. The emerging-market green series rests on 0\u2013"
        f"{res['em_arm']['largest_cell']} deals per year and is plotted for shape only. No "
        "difference-in-differences coefficient is shown: green volume was already growing "
        f"{res['pre_trend']['differential_trend_per_year']:+.3f} log-points per year faster "
        f"than non-green before the event window (p = {res['pre_trend']['p_value']:.4f}), so "
        "parallel trends fail and the design does not identify a causal effect. Raw "
        "classifier output.",
        y=0.195,
        width=108,
    )
    fig.subplots_adjust(left=0.105, right=0.845, top=0.84, bottom=0.30)
    theme.save(fig, cfg, "fig_07_crisis_contraction")


def fig_08_instrument_mix(deals: pd.DataFrame, cfg: Config) -> None:
    """Figure 8: non-dilutive dependence, green against non-green."""
    theme.apply_theme()
    res = h3_instrument.run(deals, cfg)
    shares = res["_tables"]["h3_non_dilutive_by_bloc"]
    shares = shares.loc[shares["bloc"].isin(["AE", "EM"])]

    fig, ax = plt.subplots(figsize=theme.figsize(cfg, "single"))
    labels, values, colours, notes = [], [], [], []
    for bloc in ("AE", "EM"):
        for green in (True, False):
            r = shares.loc[shares["bloc"].eq(bloc) & shares["green"].eq(green)]
            if r.empty:
                continue
            r = r.iloc[0]
            labels.append(f"{bloc}\n{'green' if green else 'non-green'}")
            values.append(r["non_dilutive_pct"])
            colours.append(P.accent_green if green else P.accent_grey)
            notes.append(f"n = {int(r['deals']):,}")

    y = np.arange(len(labels))[::-1]
    ax.barh(y, values, color=colours, height=0.56, zorder=3)
    for yi, v, note in zip(y, values, notes, strict=False):
        ax.text(
            v + 0.22,
            yi,
            f"{v:.2f}%",
            va="center",
            ha="left",
            fontsize=8.4,
            color=P.ink,
            fontweight="bold",
        )
        ax.text(v + 2.35, yi, note, va="center", ha="left", fontsize=7.4, color=P.ink_muted)

    foc = res["focused_non_dilutive_test_ae"]
    theme.annotate(
        ax,
        f"Within advanced economies, green is {foc['risk_ratio']:.2f}x\n"
        f"more likely to use non-dilutive capital "
        f"{foc['risk_ratio_ci']}",
        xy=(values[0], y[0]),
        xytext=(4.0, y[0] - 0.62),
        color=P.accent_green,
        fontsize=7.6,
    )
    theme.annotate(
        ax,
        f"The emerging-market arm rests on {res['em_arm']['em_green_deals']} deals\n"
        "and is reported as untestable, not as a null",
        xy=(values[2], y[2]),
        xytext=(4.0, y[2] - 0.6),
        color=P.em,
        fontsize=7.6,
    )

    ax.set_xlim(0, 15)
    ax.set_ylim(-0.95, len(labels) - 0.4)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.2, linespacing=1.4)
    ax.tick_params(axis="y", length=0, pad=6)
    ax.xaxis.set_major_formatter(theme.fmt_pct)
    ax.set_xlabel("Share of the group's deals using non-dilutive instruments")
    ax.spines["left"].set_visible(False)
    theme.style_axes(ax, xgrid=True)
    ax.grid(axis="y", visible=False)
    theme.finding_title(
        fig,
        "Green ventures lean harder on grants and debt than non-green ones do",
        "Non-dilutive share of deals by bloc and green status, 2000\u20132012.",
        y=0.945,
    )
    theme.source_footer(
        fig,
        cfg,
        "Non-dilutive instruments are grants, debt financing and post-IPO debt. "
        f"Advanced-economy comparison: risk ratio {foc['risk_ratio']:.3f} "
        f"{foc['risk_ratio_ci']}, p = {foc['p_value']:.2e}. Project finance that is debt or "
        "concessional in substance but coded as an equity round understates the "
        "non-dilutive share on both sides, and more so for emerging markets where "
        "independent power producers are seven of 28 green companies; that bias direction "
        "was stated before these numbers were computed. Raw classifier output.",
        y=0.195,
        width=108,
    )
    fig.subplots_adjust(left=0.165, right=0.985, top=0.84, bottom=0.30)
    theme.save(fig, cfg, "fig_08_instrument_mix")


def fig_09_cell_sizes(
    deals: pd.DataFrame,  # noqa: ARG001 - every figure takes the deal table
    cfg: Config,
) -> None:
    """Figure 9: every emerging-market test cell against the minimum, on one scale.

    This replaces three planned figures that would have rendered results the
    analysis does not have: a difference-in-differences coefficient plot whose
    identifying assumption failed, a graduation odds-ratio plot whose interval
    spans 1 at n = 40, and a need-indicator panel whose regressor is degenerate.
    Each would have shown a quantity dressed as a finding.

    What is left when those are removed is the argument itself: the cells are
    too small, everywhere, for the same reason.
    """
    theme.apply_theme()
    min_n = int(cfg.threshold("min_cell_n"))
    analysis = json.loads(
        (cfg.path("data_interim") / "analysis_findings.json").read_text(encoding="utf-8")
    )

    em_green_nd = next(
        r["non_dilutive"]
        for r in analysis["h3"]["non_dilutive_by_bloc"]
        if r["bloc"] == "EM" and r["green"]
    )
    # The cell a test depends on is not always the headline count. H3's
    # emerging-market green sample is 34 deals, which clears the minimum; the
    # instrument-mix comparison depends on the NON-DILUTIVE cell within it,
    # which is 3. Plotting 34 here would have put a bar past the threshold line
    # on a figure whose whole claim is that none of them clear it.
    rows = [
        (
            "H2  largest EM green year-cell",
            analysis["h2"]["em_arm"]["largest_cell"],
            "difference-in-differences",
        ),
        ("H3  EM green non-dilutive deals", em_green_nd, "instrument-mix test"),
        (
            "H4  EM green seed entrants",
            analysis["h4"]["em_arm"]["cells"]["em_green_entrants"],
            "graduation model",
        ),
        (
            "H4  AE green Series A to B pool",
            analysis["h4"]["power"]["ae_green_a_to_b_pool"],
            "missing-middle transition",
        ),
        ("H5  countries with any energy deficit", 2, "need-indicator regression"),
    ]
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    tests = [r[2] for r in rows]

    fig, ax = plt.subplots(figsize=theme.figsize(cfg, "single"))
    y = np.arange(len(rows))[::-1]
    ax.barh(y, values, color=P.em, height=0.5, zorder=3)
    ax.axvline(min_n, color=P.alert, linewidth=1.3, zorder=4)

    for yi, v, test in zip(y, values, tests, strict=False):
        ax.text(
            v + 0.7,
            yi,
            str(v),
            va="center",
            ha="left",
            fontsize=9,
            color=P.em,
            fontweight="bold",
        )
        ax.text(
            v + 3.0,
            yi,
            f"{test} not reported",
            va="center",
            ha="left",
            fontsize=7.4,
            color=P.ink_muted,
            style="italic",
        )

    ax.text(
        min_n - 0.6,
        y[0] + 0.62,
        f"minimum cell size, n = {min_n}",
        ha="right",
        va="bottom",
        fontsize=7.8,
        color=P.alert,
        fontweight="bold",
    )

    ax.set_xlim(0, 36)
    ax.set_ylim(-0.75, len(rows) - 0.1)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.2)
    ax.tick_params(axis="y", length=0, pad=6)
    for lbl in ax.get_yticklabels():
        lbl.set_color(P.ink)
    ax.set_xlabel("Observations available in the cell the test depends on")
    ax.spines["left"].set_visible(False)
    theme.style_axes(ax, xgrid=True)
    ax.grid(axis="y", visible=False)
    theme.finding_title(
        fig,
        "Every emerging-market test fails on the same wall, for different reasons",
        "Observations available against the pre-registered minimum cell size, "
        "across H2\u2013H5.",
        y=0.945,
    )
    theme.source_footer(
        fig,
        cfg,
        f"The minimum cell size of {min_n} was fixed in config before any hypothesis was "
        "tested, and no bar clears it. These are five distinct failures rather than one "
        "repeated: a difference-in-differences with no usable time series; an "
        "instrument-mix comparison resting on 3 non-dilutive deals, drawn from an "
        "emerging-market green sample of 34 which does itself clear the threshold; a "
        "graduation model with no entrants at all; a missing-middle transition holding 13 "
        "companies even in the best-covered bloc; and a need regressor on which 20 of 22 "
        "countries record exactly zero. Three figures that would have plotted these "
        "quantities as estimates were cut rather than drawn.",
        y=0.195,
        width=108,
    )
    fig.subplots_adjust(left=0.305, right=0.985, top=0.84, bottom=0.30)
    theme.save(fig, cfg, "fig_09_cell_sizes")


def fig_11_depth_vs_need(deals: pd.DataFrame, cfg: Config, rng) -> None:
    """Figure 11: green funding intensity against market depth.

    The planned small-multiple of need indicators is not drawn. Twenty of the
    22 panel countries record an electricity-access deficit of exactly zero, so
    a scatter against it would be a column of points on the axis with one
    outlier, which reads as a relationship and is not one. The degenerate
    distribution is shown instead, beside the depth relationship that can be
    measured.
    """
    theme.apply_theme()
    res = h5_allocation.run(deals, cfg, rng)
    panel = res["_tables"]["h5_country_panel"]
    depth = res["correlations"]["green_usd_per_capita"]["gdp_per_capita_usd"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 4.0), width_ratios=[1.45, 1.0])

    x = panel["gdp_per_capita_usd"] / 1e3
    yv = panel["green_usd_per_capita"].clip(lower=1e-3)
    ax1.scatter(x, yv, s=26, color=P.ink, zorder=3, linewidths=0)
    for code in ("USA", "IND", "CHN", "NOR", "ISR"):
        row = panel.loc[panel["country_code"].eq(code)]
        if row.empty:
            continue
        ax1.annotate(
            code,
            (
                float(row["gdp_per_capita_usd"].iloc[0]) / 1e3,
                max(float(row["green_usd_per_capita"].iloc[0]), 1e-3),
            ),
            textcoords="offset points",
            xytext=(6, -2),
            fontsize=7.2,
            color=P.ink_muted,
        )
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("GDP per capita, 2012 USD thousands (log)")
    ax1.set_ylabel("Green funding per capita,\nconstant 2015 USD (log)")
    ax1.set_title(
        f"(a)  Depth: rho {depth['rho']:+.3f} {depth['ci']}",
        fontsize=9.0,
        fontfamily=theme.title_font(),
        color=P.ink,
        loc="left",
        pad=6,
    )
    theme.style_axes(ax1, xgrid=True)

    deficit = panel["electricity_deficit_pct"].fillna(0)
    ax2.hist(deficit, bins=np.arange(0, 24, 1.5), color=P.accent_grey, zorder=3)
    ax2.set_xlabel("Electricity access deficit (%)")
    ax2.set_ylabel("Countries in panel")
    ax2.set_title(
        "(b)  Need: no usable variation",
        fontsize=9.0,
        fontfamily=theme.title_font(),
        color=P.ink,
        loc="left",
        pad=6,
    )
    theme.style_axes(ax2)
    n_zero = int((deficit < 0.05).sum())
    theme.annotate(
        ax2,
        f"{n_zero} of {len(deficit)} countries\nsit at exactly 0.0%",
        xy=(0.8, n_zero * 0.75),
        xytext=(5.5, n_zero * 0.72),
        color=P.alert,
        fontsize=7.6,
    )

    theme.finding_title(
        fig,
        "Capital tracks market depth; whether it tracks need cannot be measured here",
        f"Green funding intensity across {len(panel)} countries with at least three "
        "green deals, 2000\u20132012.",
        y=0.935,
    )
    theme.source_footer(
        fig,
        cfg,
        f"Spearman rank correlation with a bootstrap interval over "
        f"{cfg.pipeline['bootstrap_resamples']:,} draws; n = {depth['n']} countries. The "
        "planned small-multiple of need indicators is not drawn: panel (b) shows why. A "
        "scatter against a regressor on which 20 of 22 countries record exactly zero "
        "would read as a relationship and is not one. Green funding is highly "
        f"concentrated, with a Gini of {res['concentration']['gini']:.3f} and the top five "
        f"countries holding {res['concentration']['top5_share_pct']:.1f}% of green dollars.",
        y=0.175,
        width=108,
    )
    fig.subplots_adjust(left=0.125, right=0.985, top=0.80, bottom=0.275, wspace=0.34)
    theme.save(fig, cfg, "fig_11_depth_vs_need")


def main() -> None:
    """Render every figure."""
    cfg = load_config()
    cfg.ensure_dirs()
    rng = seed_everything(cfg)
    deals = read_parquet(cfg.path("data_processed") / "deals.parquet")
    fig_01_double_gap_and_capital_intensity(deals, cfg)
    fig_02_coverage_vs_gdp(deals, cfg)
    fig_03_green_rate_by_year(deals, cfg)
    fig_04_subdomain_resolution(deals, cfg)
    fig_05_cycle(deals, cfg)
    fig_06_green_share_of_all(deals, cfg)
    fig_07_crisis_contraction(deals, cfg)
    fig_08_instrument_mix(deals, cfg)
    fig_09_cell_sizes(deals, cfg)
    fig_11_depth_vs_need(deals, cfg, rng)
    fig_12_continuity_india(deals, cfg)
    fig_m1_censoring_artefact(cfg)
    fig_m2_capital_intensity_regression(deals, cfg)


if __name__ == "__main__":
    main()
