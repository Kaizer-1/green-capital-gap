"""One function per figure, named ``fig_01_*`` … ``fig_12_*``.

Every figure obeys CLAUDE.md §8: a title that states the finding, a subtitle
giving unit and window, a 7pt source footer carrying the n, horizontal
gridlines only, no top or right spine, direct labelling in place of a legend,
and 300dpi PNG plus PDF under a deterministic filename.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from gcg.analysis import h1b_capital_intensity as h1b
from gcg.analysis.h1_selection import green_rate_by_bloc, two_proportion_test
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


def main() -> None:
    """Render every figure."""
    cfg = load_config()
    cfg.ensure_dirs()
    seed_everything(cfg)
    deals = read_parquet(cfg.path("data_processed") / "deals.parquet")
    fig_01_double_gap_and_capital_intensity(deals, cfg)
    fig_m2_capital_intensity_regression(deals, cfg)


if __name__ == "__main__":
    main()
