"""Tests for the three-tier green classifier.

These run against the PRODUCTION lexicon in ``config/green_lexicon.yaml``, not a
toy one. A test that passes against a stand-in lexicon proves nothing about the
lexicon that actually labels 31,707 companies.

The fixture in ``tests/fixtures/green_cases.csv`` is hand-built with known
answers and covers every nasty edge case named in CLAUDE.md §6: cleaning
services, Greenhouse the ATS, Green as a surname, greeting cards, solarium and
Solaris, window/windows, wasteland, organic search, carbon copy and Carbonite,
sector trade media, plus the fossil-fuel and nuclear vetoes added at step 1.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from gcg.classify.green import (
    build_match_text,
    classify,
    cohens_kappa,
    count_taxonomy_tags,
)

FIXTURE = Path(__file__).parent / "fixtures" / "green_cases.csv"


@pytest.fixture(scope="module")
def cases() -> pd.DataFrame:
    """The hand-labelled fixture, shaped like the joined company table."""
    df = pd.read_csv(FIXTURE, keep_default_na=False, na_values=[])
    df["expected_green"] = df["expected_green"].astype(str).str.strip().str.lower() == "true"
    return df


@pytest.fixture(scope="module")
def classified(cases: pd.DataFrame, cfg) -> pd.DataFrame:
    """Classifier output for the fixture, under the headline specification."""
    return classify(cases, cfg)


# ---------------------------------------------------------------------------
# Headline labels
# ---------------------------------------------------------------------------
def test_every_case_matches_its_expected_label(cases, classified):
    """No row may be misclassified. Each failure prints the case and the reason."""
    got = classified["green"].to_numpy()
    want = cases["expected_green"].to_numpy()
    wrong = [
        f"{cases.loc[i, 'permalink_norm']}: expected green={want[i]} got {got[i]} "
        f"(tier={classified.loc[i, 'green_tier']}, "
        f"subdomain={classified.loc[i, 'green_subdomain']!r}, "
        f"veto={classified.loc[i, 'veto_reason'][:60]!r}) "
        f"-- {cases.loc[i, 'why']}"
        for i in range(len(cases))
        if got[i] != want[i]
    ]
    assert not wrong, "misclassified cases:\n  " + "\n  ".join(wrong)


def test_primary_subdomain_matches_expectation(cases, classified):
    """Sub-domain assignment must follow the configured priority order."""
    wrong = []
    for i in range(len(cases)):
        if not cases.loc[i, "expected_green"]:
            continue
        want = str(cases.loc[i, "expected_subdomain"]).strip()
        got = str(classified.loc[i, "green_subdomain"]).strip()
        if want and want != got:
            wrong.append(
                f"{cases.loc[i, 'permalink_norm']}: expected {want!r} got {got!r} "
                f"(all hits: {classified.loc[i, 'green_subdomains_all']!r})"
            )
    assert not wrong, "wrong sub-domain:\n  " + "\n  ".join(wrong)


# ---------------------------------------------------------------------------
# Tier separability
# ---------------------------------------------------------------------------
def test_tier_a_is_exactly_the_cleantech_flag(cases, classified, cfg):
    """Tier A must be the snapshot's own flag and nothing else."""
    values = {v.lower() for v in cfg.lexicon["tier_a"]["values"]}
    expected = cases["category_code"].astype(str).str.strip().str.lower().isin(values)
    pd.testing.assert_series_equal(
        classified["tier_a"].rename(None).reset_index(drop=True),
        expected.rename(None).reset_index(drop=True),
        check_names=False,
    )


def test_tier_c_never_vetoes_tier_a(cases, classified):
    """``green = TierA OR (TierB AND NOT TierC)``: Tier C vetoes Tier B only.

    A company the snapshot itself flags as cleantech is not removed by a lexicon
    exclusion, or the strict definition would stop being a superset-free
    reference point.
    """
    tier_a_rows = classified.loc[classified["tier_a"]]
    assert tier_a_rows["green"].all(), (
        "a Tier-A company was vetoed: "
        f"{tier_a_rows.loc[~tier_a_rows['green'], 'permalink_norm'].tolist()}"
    )


def test_strict_definition_is_a_subset_of_the_headline(classified):
    """Every Tier-A company must also be green under the headline definition."""
    assert not (classified["green_strict_tier_a"] & ~classified["green"]).any()


# ---------------------------------------------------------------------------
# Specific traps named in CLAUDE.md §6
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("slug", "reason"),
    [
        ("windowpane", "window must not match wind"),
        ("microsoft-win", "windowing must not match wind"),
        ("greenhouse-io", "Greenhouse the ATS"),
        ("sparkle-dry", "dry cleaning"),
        ("cleanly-x", "cleaning services"),
        ("greentech-media", "trade media"),
        ("cleantech-group", "analyst firm"),
        ("solaris-sys", "Solaris the OS"),
        ("tan-solarium", "solarium"),
        ("hallmark-greet", "greeting cards"),
        ("mr-green-ltd", "Green as a surname"),
        ("wasteland-games", "wasteland"),
        ("seo-organic", "organic search"),
        ("carboncopy-sw", "carbon copy"),
        ("carbonite-inc", "Carbonite"),
        ("carbonblack-sec", "Carbon Black"),
        ("hydroflask-co", "Hydro Flask"),
        ("batterypark-cap", "Battery Park"),
        ("exxon-upstream", "fossil veto: oil and gas"),
        ("coal-india-x", "fossil veto: coal power"),
        ("frack-tech", "fossil veto: fracking"),
        ("nuclear-power-x", "nuclear vetoed from the generic tier"),
    ],
)
def test_known_false_positives_are_rejected(classified, slug, reason):
    """Each named trap must come out not-green."""
    row = classified.loc[classified["permalink_norm"] == slug]
    assert len(row) == 1, f"fixture missing {slug}"
    assert not bool(row["green"].iloc[0]), f"{slug} should be rejected ({reason})"


@pytest.mark.parametrize(
    ("slug", "reason"),
    [
        ("ghg-analytics", "greenhouse GAS is a green signal"),
        ("green-building-co", "green-compounds do trigger"),
        ("earthfarm-x", "organic farming is agriculture"),
        ("southpole-carbon", "carbon credits is a green compound"),
        ("andritz-hydro", "hydropower is genuine"),
        ("biorefinery-co", "biorefinery survives the fossil veto"),
    ],
)
def test_near_miss_true_positives_are_kept(classified, slug, reason):
    """Cases that sit next to a veto pattern must survive it."""
    row = classified.loc[classified["permalink_norm"] == slug]
    assert len(row) == 1, f"fixture missing {slug}"
    assert bool(row["green"].iloc[0]), f"{slug} should be kept ({reason})"


# ---------------------------------------------------------------------------
# Gated pattern behaviour
# ---------------------------------------------------------------------------
def test_bare_energy_is_gated_by_its_flag(cases, cfg):
    """A company tagged only ``Energy`` flips with the ``admit_bare_energy`` flag."""
    on = classify(cases, cfg, admit_bare_energy=True)
    off = classify(cases, cfg, admit_bare_energy=False)
    idx = cases.index[cases["permalink_norm"] == "plain-energy-co"][0]
    assert bool(on.loc[idx, "green"]), "bare Energy should be green with the flag on"
    assert not bool(off.loc[idx, "green"]), "bare Energy should not be green with the flag off"
    assert bool(on.loc[idx, "depends_on_gated_pattern"]), "dependence must be recorded"


def test_gated_flag_does_not_disturb_specific_hits(cases, cfg):
    """Turning the gate off must not change a company with a specific green tag."""
    on = classify(cases, cfg, admit_bare_energy=True)
    off = classify(cases, cfg, admit_bare_energy=False)
    specific = cases["permalink_norm"].isin(["solarcity", "ather-energy", "andritz-hydro"])
    rows = cases.index[specific]
    assert on.loc[rows, "green"].equals(off.loc[rows, "green"])


def test_fossil_veto_beats_the_bare_energy_gate(cases, cfg):
    """An oil and gas company tagged ``Energy`` stays out with the gate open."""
    on = classify(cases, cfg, admit_bare_energy=True)
    for slug in ("exxon-upstream", "coal-india-x"):
        idx = cases.index[cases["permalink_norm"] == slug][0]
        assert not bool(on.loc[idx, "green"]), f"{slug} must be vetoed even with the gate open"


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------
def test_green_rows_record_the_patterns_that_fired(classified):
    """A Tier-B green row must name the regexes responsible, for Appendix A."""
    tier_b = classified.loc[classified["tier_b_surviving"] & classified["green"]]
    assert len(tier_b) > 0
    assert (tier_b["green_matched_patterns"].str.len() > 0).all()
    assert (tier_b["green_matched_pattern_ids"].str.len() > 0).all()
    assert (tier_b["n_patterns_fired"] > 0).all()


def test_recorded_patterns_actually_match_the_text(classified):
    """Every regex named in the audit trail must really match that row's text.

    Guards against the audit trail drifting out of step with the decision it is
    supposed to document.
    """
    for _, row in classified.loc[classified["n_patterns_fired"] > 0].iterrows():
        text = row["match_text"]
        for rx in str(row["green_matched_patterns"]).split(" ;; "):
            if rx:
                assert re.search(rx, text, re.I), f"{row['permalink_norm']}: {rx!r} does not match"


def test_vetoed_rows_record_a_reason(classified):
    """No silent veto. Every Tier-C rejection carries a human-readable reason."""
    vetoed = classified.loc[classified["tier_c_vetoed"]]
    assert len(vetoed) > 0
    assert (vetoed["veto_reason"].str.len() > 0).all()
    assert (vetoed["veto_pattern"].str.len() > 0).all()


def test_non_green_rows_carry_no_subdomain(classified):
    """A sub-domain label on a non-green row would corrupt the Figure 5 mix."""
    non_green = classified.loc[~classified["green"]]
    assert (non_green["green_subdomain"] == "").all()
    assert (non_green["green_subdomains_all"] == "").all()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def test_empty_record_does_not_classify_or_crash(cases, classified):
    """An all-blank company must come out not-green rather than raising."""
    idx = cases.index[cases["permalink_norm"] == "no-fields-at-all"][0]
    assert not bool(classified.loc[idx, "green"])
    assert classified.loc[idx, "green_tier"] == "none"


def test_match_text_uses_a_pipe_separator(cases, cfg):
    """Several patterns rely on a pipe token boundary, so the separator matters."""
    text, fields = build_match_text(cases, cfg)
    assert len(fields) >= 3
    assert "|" in text.iloc[0]


def test_taxonomy_tag_count():
    """Tag counting must ignore empty segments from leading/trailing pipes."""
    s = pd.Series(["|Solar|Clean Energy|", "|Software|", "", "|A|B|C|D|", None])
    assert count_taxonomy_tags(s).tolist() == [2, 1, 0, 4, 0]


def test_cohens_kappa_edge_cases():
    """Perfect agreement gives 1.0; the confusion cells must add to n."""
    perfect = cohens_kappa(pd.Series([True, False, True]), pd.Series([True, False, True]))
    assert perfect["kappa"] == pytest.approx(1.0)

    mixed = cohens_kappa(
        pd.Series([True, True, False, False]), pd.Series([True, False, True, False])
    )
    assert mixed["both"] + mixed["tier_a_only"] + mixed["tier_b_only"] + mixed["neither"] == 4
    assert -1.0 <= mixed["kappa"] <= 1.0
