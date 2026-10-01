"""Tests for the single rounding convention.

The defect these guard against shipped once: Figure 1 said 5.42% and the text
said 5.43% from the same 5.4254%, because one path rounded twice.
"""

from __future__ import annotations

import pytest

from gcg.rounding import fmt, fmt_ci, fmt_multiple, fmt_p, fmt_pct, half_up


def test_half_up_breaks_ties_away_from_zero():
    """Python's round() gives 5.42 here; a reader checking by hand expects 5.43."""
    assert half_up(5.425, 2) == 5.43
    assert half_up(2.675, 2) == 2.68
    assert half_up(0.125, 2) == 0.13
    assert half_up(-5.425, 2) == -5.43


def test_the_exact_value_that_caused_the_defect():
    """5.4254 must give 5.43 by every route."""
    raw = 0.054254 * 100
    assert fmt(raw, 2) == "5.43"
    assert fmt_pct(raw, 2) == "5.43%"


def test_the_old_double_rounding_path_gave_a_different_answer():
    """Reproduce the defect, so the fix is anchored to the thing that broke.

    The analysis frame rounded 5.4254 to three decimals and the figure then
    formatted that with an f-string. Binary float makes 5.425 render as 5.42,
    while the report formatted the raw value and got 5.43.
    """
    raw = 5.4254
    assert f"{round(raw, 3):.2f}" == "5.42"   # what the figure printed
    assert f"{raw:.2f}" == "5.43"             # what the report printed
    assert fmt(raw, 2) == "5.43"              # what both print now


def test_helper_is_stable_under_an_accidental_second_rounding():
    """Even if a value is rounded twice through the helper, it agrees.

    Decimal does not inherit the binary representation problem, so routing both
    paths through this module removes the whole failure mode rather than
    relying on callers never pre-rounding.
    """
    raw = 5.4254
    assert fmt(half_up(raw, 3), 2) == fmt(raw, 2) == "5.43"


def test_negative_numbers_use_a_typographic_minus():
    assert fmt(-49.3, 1) == "−49.3"
    assert "-" not in fmt(-49.3, 1)


def test_minus_can_be_disabled_for_contexts_that_need_ascii():
    assert fmt(-49.3, 1, minus=False) == "-49.3"


def test_multiples_use_a_multiplication_sign():
    assert fmt_multiple(1.92) == "1.92×"
    assert "x" not in fmt_multiple(1.92)


def test_confidence_intervals_round_both_bounds_identically():
    assert fmt_ci([0.3425, 0.6695], 3) == "[0.343, 0.670]"
    assert fmt_ci([-1.6383, -0.7516], 2) == "[−1.64, −0.75]"


def test_missing_values_render_as_an_em_dash():
    assert fmt(None) == "—"
    assert fmt(float("nan")) == "—"
    assert fmt_ci(None) == "—"
    assert fmt_p(None) == "—"


def test_p_values_render_conventionally():
    assert fmt_p(0.458) == "0.458"
    assert fmt_p(0.0005) == "< 0.001"
    assert "10" in fmt_p(1.24e-07)


def test_thousands_separator_is_applied_by_default():
    assert fmt(41105, 0) == "41,105"
    assert fmt(41105, 0, thousands=False) == "41105"


@pytest.mark.parametrize("value", [0.0, 100.0, -0.0])
def test_edge_values_do_not_raise(value):
    assert isinstance(fmt(value), str)
