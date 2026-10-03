"""The house style. CLAUDE.md §8.

Default matplotlib output reads as unfinished work. Everything here exists to
make the figures look considered: a restricted palette with semantic colour
assignment, serif titles over sans labels, horizontal gridlines only, no top or
right spine, direct series labelling instead of legends, and a source footer
carrying the n.

``apply_theme()`` is called once per process. Fonts degrade silently through a
preference list, so a missing font never crashes a build or emits tofu boxes.
"""

from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager

from gcg.config import Config, get_logger

LOG = get_logger("viz.theme")


@dataclass(frozen=True)
class Palette:
    """The project palette. Considered, not rainbow."""

    ink: str = "#141413"
    ink_muted: str = "#6E6E68"
    rule: str = "#E3E1DA"
    canvas: str = "#FFFFFF"
    em: str = "#0E7C7B"
    ae: str = "#B5651D"
    china: str = "#4A4A52"
    ldc: str = "#9C7B9B"
    accent_green: str = "#3F7D3F"
    accent_grey: str = "#A8A69E"
    alert: str = "#B03A2E"
    # Marks the series under discussion. Deliberately outside the bloc colours
    # so highlighting cleantech cannot be read as a bloc assignment.
    focus: str = "#5B4B8A"

    def bloc(self, name: str) -> str:
        """Colour for a bloc label."""
        return {
            "AE": self.ae,
            "EM": self.em,
            "CHINA": self.china,
            "LDC": self.ldc,
            "UNASSIGNED": self.accent_grey,
        }.get(str(name).upper(), self.accent_grey)


PALETTE = Palette()

_TITLE_FONTS = ["Source Serif 4", "Charter", "Georgia", "DejaVu Serif"]
_BODY_FONTS = ["Inter", "Source Sans 3", "Helvetica Neue", "DejaVu Sans"]

_resolved: dict[str, str] = {}

# Which variant is being built. Screen variants are standalone exhibits and keep
# their chrome; print variants carry axes, data and annotations only, because
# the title, subtitle and source note become caption text set by the document.
_MODE = "screen"

# Annotations longer than this are moved to the caption in print variants. Short
# pointer labels ("n = 34", "2008") stay in-plot; a sentence does not, because at
# print size it has nowhere to sit that is not over data.
PRINT_ANNOTATION_MAX_CHARS = 40

# Slack measured on each print variant, written out for the render gate.
_SLACK: dict[str, dict[str, float]] = {}
_INK: dict[str, dict[str, float]] = {}

# Every authored string rendered into a figure, keyed by figure slug. Harvested
# in save() while the figure still exists, because figure text never reaches the
# report's prose gate: it is baked into a PDF before the renderer ever sees it.
# That is how a hand-typed 2 reached a published figure past five gates.
_TEXTS: dict[str, list[str]] = {}


def set_mode(mode: str) -> None:
    """Select the variant being built: ``screen`` or ``print``."""
    global _MODE  # noqa: PLW0603
    if mode not in {"screen", "print"}:
        msg = f"unknown figure mode {mode!r}"
        raise ValueError(msg)
    _MODE = mode


def is_print() -> bool:
    """Whether the print variant is being built."""
    return _MODE == "print"


def _resolve_font(candidates: list[str], fallback: str) -> str:
    """Return the first installed font from ``candidates``.

    Checks the font manager rather than trusting matplotlib's fallback chain,
    which silently substitutes and can emit tofu boxes for missing glyphs.
    """
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            return name
    return fallback


def title_font() -> str:
    """The resolved serif face for titles."""
    if "title" not in _resolved:
        _resolved["title"] = _resolve_font(_TITLE_FONTS, "DejaVu Serif")
    return _resolved["title"]


def body_font() -> str:
    """The resolved sans face for labels."""
    if "body" not in _resolved:
        _resolved["body"] = _resolve_font(_BODY_FONTS, "DejaVu Sans")
    return _resolved["body"]


def apply_theme() -> None:
    """Install the house style, then the print overrides when in print mode."""
    p = PALETTE
    mpl.rcParams.update(
        {
            "figure.facecolor": p.canvas,
            "axes.facecolor": p.canvas,
            "savefig.facecolor": p.canvas,
            "font.family": "sans-serif",
            "font.sans-serif": [body_font(), "DejaVu Sans"],
            "font.size": 9,
            "text.color": p.ink,
            "axes.labelcolor": p.ink,
            "axes.edgecolor": p.ink,
            "axes.linewidth": 0.8,
            "axes.labelsize": 9,
            "axes.titlesize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": p.rule,
            "grid.linewidth": 0.6,
            "grid.linestyle": "-",
            "xtick.color": p.ink_muted,
            "ytick.color": p.ink_muted,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "legend.frameon": False,
            "lines.linewidth": 1.6,
            "lines.solid_capstyle": "round",
            "figure.dpi": 110,
            # NOT "tight": a tight bbox silently rescales the figure when an
            # artist strays outside the canvas, which turns a 7.2x8.0 portrait
            # figure into a letterbox. Layout is set explicitly instead.
            "savefig.bbox": None,
            "savefig.pad_inches": 0.03,
        }
    )
    if is_print():
        from gcg.viz import print_mode

        print_mode.apply_print_rc()
    LOG.info("theme applied (%s): titles %r, body %r", _MODE, title_font(), body_font())


def style_axes(ax: plt.Axes, *, xgrid: bool = False) -> None:
    """Horizontal gridlines only, behind the data, no top or right spine."""
    ax.grid(axis="y", visible=True)
    ax.grid(axis="x", visible=xgrid)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def finding_title(
    fig: plt.Figure,
    finding: str,
    subtitle: str,
    *,
    x: float = 0.0,
    y: float = 1.0,
) -> None:
    """Set a title that states the finding, with a unit-and-window subtitle.

    CLAUDE.md §8: the title is a sentence that states the finding, never a label.

    Suppressed in print mode: the finding sentence is the first tier of the
    Typst caption there, and a figure titled twice is worse than one titled
    once.
    """
    if is_print():
        return
    fig.text(
        x,
        y,
        finding,
        ha="left",
        va="bottom",
        fontsize=12.5,
        fontfamily=title_font(),
        color=PALETTE.ink,
        linespacing=1.25,
    )
    fig.text(
        x,
        y - 0.045,
        subtitle,
        ha="left",
        va="bottom",
        fontsize=8.8,
        color=PALETTE.ink_muted,
    )


def source_footer(
    fig: plt.Figure, cfg: Config, note: str, *, y: float = -0.02, width: int = 118
) -> None:
    """The 7pt source line carrying the n, the window and the dollar basis.

    Wrapped to a fixed character width because the footer is the one artist
    long enough to run off the canvas, and a clipped source line is worse than
    no source line.

    Suppressed in print mode, where the source note is the third tier of the
    Typst caption and is set in the document's own type rather than rasterised
    at 7pt inside a PDF.
    """
    if is_print():
        return
    base = cfg.pipeline["figures"]["source_line"]
    text = textwrap.fill(f"{base} {note}", width=width)
    fig.text(
        0.012,
        y,
        text,
        ha="left",
        va="top",
        fontsize=7,
        color=PALETTE.ink_muted,
        linespacing=1.3,
    )


def annotate(
    ax: plt.Axes,
    text: str,
    xy: tuple[float, float],
    xytext: tuple[float, float],
    *,
    color: str | None = None,
    fontsize: float = 8.0,
    ha: str = "left",
    keep_in_print: bool = False,
) -> None:
    """Inline callout with a thin leader line.

    CLAUDE.md §8 requires an annotation layer: a chart that makes the reader find
    the story is a chart that failed.

    In print variants an annotation longer than
    ``PRINT_ANNOTATION_MAX_CHARS`` is dropped and belongs in the caption
    instead. At 6.22in a sentence has nowhere to sit that is not over data, and
    the caption is set in the document's own type where it reads better anyway.
    Pass ``keep_in_print`` for a long label that genuinely has clear space.
    """
    if is_print() and not keep_in_print and len(text) > PRINT_ANNOTATION_MAX_CHARS:
        return
    ax.annotate(
        text,
        xy=xy,
        xytext=xytext,
        fontsize=fontsize,
        color=color or PALETTE.ink,
        ha=ha,
        va="center",
        linespacing=1.3,
        arrowprops={
            "arrowstyle": "-",
            "linewidth": 0.7,
            "color": color or PALETTE.ink_muted,
            "shrinkA": 2,
            "shrinkB": 3,
        },
    )


def layout(
    fig: plt.Figure,
    *,
    left: float,
    right: float,
    top: float,
    bottom: float,
    print_top: float = 0.965,
    print_bottom: float | None = None,
    print_left: float | None = None,
    print_right: float | None = None,
    **kwargs: Any,
) -> None:
    """Apply subplot margins appropriate to the variant being built.

    Top and bottom differ because of the chrome: with no title and no source
    block the print variant reclaims both. Side margins differ too, which is
    less obvious: the print canvas is 6.22in against the screen's 7.2in while
    its type is LARGER, so a tick label needs a bigger fraction of a smaller
    canvas. Figures with long y-axis labels pass explicit print values.
    """
    if is_print():
        fig.subplots_adjust(
            left=print_left if print_left is not None else left,
            right=print_right if print_right is not None else right,
            top=print_top,
            bottom=print_bottom if print_bottom is not None else 0.135,
            **kwargs,
        )
    else:
        fig.subplots_adjust(left=left, right=right, top=top, bottom=bottom, **kwargs)


def series_label(
    ax: plt.Axes,
    y_value: float,
    text: str,
    colour: str,
    *,
    fontsize: float = 8.0,
    dx: float = 0.015,
) -> None:
    """Label a series in the gutter to the right of the axes, not inside it.

    Direct labelling beats a legend, but placing the label inside the axes
    forces the x-limit past the data to make room: four figures ran to a 2014
    tick with nothing under it because the labels sat at 2013. Placing the label
    in axes coordinates just outside the right spine, with clipping off, lets
    the x-limit stop at the last year that has data. ``flush_fit`` then sizes
    the gutter to exactly what the labels need, since they count as ink.
    """
    ax.text(
        1.0 + dx,
        y_value,
        text,
        transform=ax.get_yaxis_transform(),
        va="center",
        ha="left",
        fontsize=fontsize,
        color=colour,
        clip_on=False,
        linespacing=1.3,
    )


# Measurement dpi for the raster pass. High enough that one pixel is well under
# the tolerance we care about (1/600in = 0.0017in), low enough to be cheap.
_RASTER_DPI = 600


def _ink_box(fig: plt.Figure, dpi: int = _RASTER_DPI) -> dict[str, float] | None:
    """True ink edges, in inches from each canvas edge, measured off a raster.

    ``get_tightbbox`` is what ``flush_fit`` uses, and for most artists it is
    exact. For *rotated* text it is not: a vertical y-axis label reports a box
    wider than the glyphs inside it, so a figure whose leftmost artist is the
    y-label ends up sitting a couple of points further right than one whose
    leftmost artist is a horizontal tick label, even though both report flush.
    Measured on a contact sheet that was the whole residual: the line and
    scatter figures clustered 4px left of the bar figures at 150dpi.

    Rendering the figure and finding the first non-white row and column removes
    the discrepancy, because it measures what the reader actually sees.
    """
    import numpy as np

    prev = fig.get_dpi()
    try:
        fig.set_dpi(dpi)
        fig.canvas.draw()
        buf = np.asarray(fig.canvas.buffer_rgba())
    except Exception:  # noqa: BLE001 - a measurement failure must not fail a build
        LOG.warning("raster ink measurement failed; keeping the tightbbox fit")
        return None
    finally:
        fig.set_dpi(prev)

    # Composite onto white, then treat anything off-white as ink.
    alpha = buf[..., 3:4].astype("float32") / 255.0
    grey = (buf[..., :3].astype("float32") * alpha + 255.0 * (1.0 - alpha)).mean(axis=2)
    ink = grey < 250.0
    if not ink.any():
        return None
    rows = np.where(ink.any(axis=1))[0]
    cols = np.where(ink.any(axis=0))[0]
    height, width = ink.shape
    return {
        "left": float(cols[0]) / dpi,
        "right": float(width - 1 - cols[-1]) / dpi,
        # Raster rows run top-down; subplot fractions run bottom-up.
        "top": float(rows[0]) / dpi,
        "bottom": float(height - 1 - rows[-1]) / dpi,
    }


def _flush_raster(
    fig: plt.Figure,
    *,
    pad_in: float = 0.01,
    edges: dict[str, bool] | None = None,
    passes: int = 2,
) -> None:
    """Correct the subplot margins against raster-measured ink.

    Runs after ``flush_fit``, which gets within a few thousandths of an inch on
    everything and within about two points on figures with a rotated y-label.
    This closes the remainder so that every figure in the document shares one
    left edge rather than two clusters of one.
    """
    on = {"left": True, "right": True, "bottom": True, "top": True} | (edges or {})
    width_in, height_in = fig.get_size_inches()
    for _ in range(passes):
        box = _ink_box(fig)
        if box is None:
            return
        sp = fig.subplotpars
        new = {"left": sp.left, "right": sp.right, "bottom": sp.bottom, "top": sp.top}
        if on["left"]:
            new["left"] = sp.left - (box["left"] - pad_in) / width_in
        if on["right"]:
            new["right"] = sp.right + (box["right"] - pad_in) / width_in
        if on["bottom"]:
            new["bottom"] = sp.bottom - (box["bottom"] - pad_in) / height_in
        if on["top"]:
            new["top"] = sp.top + (box["top"] - pad_in) / height_in
        if new["left"] >= new["right"] or new["bottom"] >= new["top"]:
            LOG.warning("raster flush would invert the axes; leaving the tightbbox fit")
            return
        fig.subplots_adjust(**new)


def harvest_text(fig: plt.Figure) -> list[str]:
    """Every authored string drawn on a figure, tick labels excluded.

    Walks the artist tree rather than intercepting the drawing calls, so it sees
    text whatever produced it — ``ax.text``, ``ax.annotate``, ``fig.text``, a
    title, an axis label, or one of this module's own helpers.

    Tick labels are excluded deliberately. They are generated by a formatter
    from the axis domain, so their numbers are properties of the data's range
    rather than claims an author made, and including them would bury the
    authored strings in axis scales.
    """
    import matplotlib.text as mtext

    # Draw first: before a draw, an axis may not have materialised the Text
    # objects it will actually render, so identities collected now would not
    # match the ones findobj returns and every tick label would leak through as
    # an authored string.
    fig.canvas.draw()

    # Each tick owns TWO Text objects, label1 and label2 (bottom/top, left/right),
    # and get_ticklabels returns only one of them. Collecting just that one left
    # the other in the harvest, so every axis scale leaked through as authored
    # text. Walk the ticks and take both.
    ticks: set[int] = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for tick in (*axis.get_major_ticks(), *axis.get_minor_ticks()):
                ticks.add(id(tick.label1))
                ticks.add(id(tick.label2))
            ticks.add(id(axis.get_offset_text()))

    out = []
    for artist in fig.findobj(mtext.Text):
        if id(artist) in ticks:
            continue
        text = artist.get_text()
        if text and text.strip():
            out.append(text)
    return out


def save(
    fig: plt.Figure,
    cfg: Config,
    stem: str,
    *,
    flush: bool = True,
    flush_edges: dict[str, bool] | None = None,
) -> list[Path]:
    """Save at 300 dpi as both PNG and PDF with a deterministic filename."""
    # Expand the axes until the ink meets the canvas, so every figure in the
    # document shares one left edge instead of each having its own hand-chosen
    # margin. Canvas size is untouched, so a 6.22in figure stays 6.22in.
    if flush:
        from gcg.viz.flush_fit import flush_fit, measure_slack

        flush_fit(fig, **(flush_edges or {}))
        if is_print():
            # flush_fit leaves rotated y-labels a couple of points shy; the raster
            # pass closes that so the print variants share one edge exactly.
            _flush_raster(fig, edges=flush_edges)
            _SLACK[stem] = {k: round(v, 4) for k, v in measure_slack(fig).items()}
            ink = _ink_box(fig)
            if ink:
                _INK[stem] = {k: round(v, 4) for k, v in ink.items()}

    # Harvested before the figure is saved and closed. Print and screen variants
    # draw different text (print sheds its chrome), so both passes contribute and
    # the gate sees the union.
    _TEXTS.setdefault(stem, [])
    _TEXTS[stem].extend(harvest_text(fig))

    spec = cfg.pipeline["figures"]
    out: list[Path] = []
    if is_print():
        target = cfg.path("figures") / "print"
        target.mkdir(parents=True, exist_ok=True)
        path = target / f"{stem}_print.pdf"
        # bbox_inches=None: the canvas was sized to the text column exactly, and
        # a tight bbox would silently change that width.
        fig.savefig(path, format="pdf", bbox_inches=None, pad_inches=0.0)
        out.append(path)
        LOG.info("saved print/%s", path.name)
    else:
        target = cfg.path("figures")
        target.mkdir(parents=True, exist_ok=True)
        for ext in spec["formats"]:
            path = target / f"{stem}.{ext}"
            fig.savefig(path, dpi=spec["dpi"], bbox_inches=None)
            out.append(path)
        LOG.info("saved %s (%s)", stem, ", ".join(spec["formats"]))
    plt.close(fig)
    return out


def write_slack_report(cfg: Config) -> Path:
    """Persist the measured slack for every print variant.

    The render gate reads this rather than re-rendering, and a missing entry is
    itself a failure: it means a figure was added without being flushed.
    """
    path = cfg.path("figures") / "print" / "_slack.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    # The four edge values are the RASTER-measured ink, because that is what the
    # reader sees lined up against the caption. The tightbbox figures flush_fit
    # itself works to are kept beside them, so a disagreement between the two is
    # visible rather than hidden.
    report = {
        slug: {**(_INK.get(slug) or _SLACK[slug]), "tightbbox": _SLACK[slug]}
        for slug in sorted(_SLACK)
    }
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    LOG.info("wrote %s for %d print variants", path.name, len(_SLACK))
    return path


def write_text_report(cfg: Config) -> Path:
    """Write every authored string drawn into a figure, for the render gate.

    The report's bare-number gate reads the prose. Figure text is composed in
    Python and rasterised into a PDF long before the renderer runs, so no gate
    has ever seen it. This file is what lets one check both.
    """
    path = cfg.path("figures") / "_text_audit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        slug: sorted({" ".join(t.split()) for t in texts})
        for slug, texts in sorted(_TEXTS.items())
    }
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LOG.info(
        "wrote %s: %d strings across %d figures",
        path.name,
        sum(len(v) for v in report.values()),
        len(report),
    )
    return path


def figsize(cfg: Config, kind: str = "single", slug: str | None = None) -> tuple[float, float]:
    """Figure size for the variant being built.

    In print mode the size comes from ``print_mode.SPECS``, so the canvas is the
    exact width of the text column and nothing is scaled in the document.
    """
    if is_print() and slug:
        from gcg.viz import print_mode

        spec = print_mode.SPECS.get(slug)
        if spec is not None:
            return print_mode.size_for(spec)
    key = {
        "stacked": "figsize_stacked",
        "wide": "figsize_wide",
        "single": "figsize_single",
    }.get(kind, "figsize_single")
    w, h = cfg.pipeline["figures"][key]
    return float(w), float(h)


def fmt_pct(value: float, _pos: Any = None) -> str:
    """Tick formatter for percentages already expressed 0-100."""
    return f"{value:g}%"
