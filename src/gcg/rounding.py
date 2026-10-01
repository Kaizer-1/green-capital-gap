"""One rounding convention, applied once, at the display edge.

Figure 1 reported an advanced-economy green rate of 5.42% while the text
reported 5.43% from the same underlying 5.4254%. The cause was not a
tie-breaking disagreement but **double rounding**: the analysis frame rounded to
three decimals (5.425), the figure then formatted that to two (5.42, because
5.425 is 5.42499... in binary), while the report formatted the raw value
directly (5.43).

The rule, applied everywhere:

1. **Analysis frames keep full precision.** Rounding is a presentation concern
   and does not belong in a table that something else will round again.
2. **Rounding happens once, at the point of display**, through this module.
3. **Half-up**, not Python's default banker's rounding, because a reader
   checking 5.425 by hand expects 5.43.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_DASH = "—"
_MINUS = "−"
_TIMES = "×"


def half_up(value: float, places: int = 2) -> float:
    """Round half away from zero, rather than to the nearest even digit.

    ``round(5.425, 2)`` and ``f"{5.425:.2f}"`` both depend on the binary
    representation of the input and can disagree with a reader doing the
    arithmetic by hand. This does not.
    """
    try:
        quant = Decimal(1).scaleb(-places)
        return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        return float("nan")


def fmt(
    value: float | None,
    places: int = 2,
    *,
    suffix: str = "",
    thousands: bool = True,
    minus: bool = True,
) -> str:
    """Format a number for display: half-up, typographic minus, optional suffix.

    ``minus`` replaces the ASCII hyphen with U+2212, which is the character a
    negative number should use in running text and in a figure label alike.
    """
    if value is None or (isinstance(value, float) and value != value):
        return _DASH
    rounded = half_up(value, places)
    spec = f",.{places}f" if thousands else f".{places}f"
    text = format(rounded, spec)
    if minus and text.startswith("-"):
        text = _MINUS + text[1:]
    return f"{text}{suffix}"


def fmt_pct(value: float | None, places: int = 2) -> str:
    """Format a percentage already expressed on a 0-100 scale."""
    return fmt(value, places, suffix="%")


def fmt_multiple(value: float | None, places: int = 2) -> str:
    """Format a multiplier as ``1.92x`` with a true multiplication sign."""
    return fmt(value, places, suffix=_TIMES)


def fmt_ci(
    pair: list[float] | tuple[float, float] | None,
    places: int = 2,
    *,
    suffix: str = "",
) -> str:
    """Render a confidence interval, both bounds rounded by the same rule."""
    if not pair or any(v is None for v in pair):
        return _DASH
    lo = fmt(pair[0], places, suffix=suffix, thousands=False)
    hi = fmt(pair[1], places, suffix=suffix, thousands=False)
    return f"[{lo}, {hi}]"


def fmt_p(value: float | None) -> str:
    """Format a p-value the way a reader expects to see one."""
    if value is None or (isinstance(value, float) and value != value):
        return _DASH
    if value < 1e-4:
        mantissa, exponent = f"{value:.1e}".split("e")
        return f"{mantissa}{_TIMES}10{_superscript(int(exponent))}"
    if value < 0.001:
        return "< 0.001"
    return fmt(value, 3, thousands=False)


def _superscript(n: int) -> str:
    """Render an exponent in superscript digits."""
    table = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
    return str(n).translate(table)
