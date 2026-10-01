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
    """Install the house style. Call once per process."""
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
    LOG.info("theme applied: titles %r, body %r", title_font(), body_font())


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
    """
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
    """
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
) -> None:
    """Inline callout with a thin leader line.

    CLAUDE.md §8 requires an annotation layer: a chart that makes the reader find
    the story is a chart that failed.
    """
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


def save(fig: plt.Figure, cfg: Config, stem: str) -> list[Path]:
    """Save at 300 dpi as both PNG and PDF with a deterministic filename."""
    spec = cfg.pipeline["figures"]
    out: list[Path] = []
    target = cfg.path("figures")
    target.mkdir(parents=True, exist_ok=True)
    for ext in spec["formats"]:
        path = target / f"{stem}.{ext}"
        fig.savefig(path, dpi=spec["dpi"], bbox_inches=None)
        out.append(path)
    LOG.info("saved %s (%s)", stem, ", ".join(spec["formats"]))
    plt.close(fig)
    return out


def figsize(cfg: Config, kind: str = "single") -> tuple[float, float]:
    """Figure size from config: ``single`` or ``stacked``."""
    key = "figsize_stacked" if kind == "stacked" else "figsize_single"
    w, h = cfg.pipeline["figures"][key]
    return float(w), float(h)


def fmt_pct(value: float, _pos: Any = None) -> str:
    """Tick formatter for percentages already expressed 0-100."""
    return f"{value:g}%"
