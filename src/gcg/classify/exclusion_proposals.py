"""Build the manual-exclusion worksheets for human ratification.

CLAUDE.md §6 requires the highest-funded Tier-B-only hits to be eyeballed and
the decisions recorded in ``config/green_lexicon.yaml`` with a one-line reason
each. This module produces the worksheets; a human makes the calls. Nothing here
writes to the lexicon.

Two worksheets, because they need different levels of scrutiny:

- ``proposal_exclusions_top150.csv`` — the 150 highest-funded Tier-B-only
  companies, for bulk ratification.
- ``proposal_exclusions_em_green.csv`` — every company behind an emerging-market
  green deal, reviewed individually. With 35 EM green deals a single call moves
  a headline number by up to 20%, so these cannot be ratified in bulk.

``recommendation`` is one of ``keep``, ``exclude`` or ``review``. Where the
company could not be identified beyond its taxonomy tags, the recommendation
rests on pattern evidence alone and ``basis`` says so, rather than implying a
judgement that was not made.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from gcg.config import Config, get_logger

LOG = get_logger("classify.proposals")

# Named judgements. Each is a company identified from its name and taxonomy, with
# the reason the call is being made. Kept here rather than in the lexicon because
# these are PROPOSALS; only ratified decisions go into config.
NAMED_CALLS: dict[str, tuple[str, str]] = {
    # --- emerging-market green companies, reviewed individually ---
    "quippo-infrastructure": (
        "exclude",
        "Telecom tower infrastructure. Matched on a bare 'Clean Technology' tag with "
        "'mobile' as its only other token. Ratified for exclusion by the supervisor.",
    ),
    "sedemac-mechatronics": (
        "exclude",
        "Engine control units for small internal-combustion engines and gensets. "
        "Automotive electronics tagged 'Clean Technology'; the product burns fuel.",
    ),
    "wifinity-technology": (
        "exclude",
        "'Intelligent enterprise management' software. Only green evidence is a bare "
        "'Clean Technology' tag; nothing in the record describes a green product.",
    ),
    "gate-technology": (
        "exclude",
        "Diversified electronics and engineering firm; 'Clean Energy' is one of nine "
        "unrelated tags including Telecommunications, Medical and Automotive. Tag soup.",
    ),
    "aventones": (
        "exclude",
        "Carpooling marketplace matched only on a generic 'Sustainability' tag. "
        "Ride-sharing software with no energy or emissions technology.",
    ),
    "ksk-power-venture": (
        "review",
        "Indian independent power producer whose capacity in this period was "
        "predominantly coal-fired thermal, with some hydro. Tagged 'Clean Technology'. "
        "Excluding it is defensible; it is the 6th largest EM green deal at $97.4m.",
    ),
    "akenerji-elektrik-uretim": (
        "review",
        "Turkish power generator with a mixed portfolio including substantial "
        "natural-gas capacity alongside hydro and wind. Partially green at best.",
    ),
    "algenol-biofuel": (
        "review",
        "Genuine algae biofuel, so green is correct, but the country_code of RUS looks "
        "wrong: Algenol operated from Florida and the Russian link was its investor. "
        "A country error, not a green error. Affects bloc assignment, not the label.",
    ),
    "scion-global": (
        "review",
        "Unidentifiable from the record: a bare 'Clean Technology' tag and nothing "
        "else. Cannot be verified either way; $0.2m so immaterial to any total.",
    ),
    "villgro-innovation-marketing": (
        "review",
        "Rural distribution arm of a social-enterprise incubator. Distributes green "
        "products among others. In scope only on a broad reading of the sector.",
    ),
    "isagen": (
        "review",
        "Colombian hydroelectric generation utility. Genuinely renewable, but an "
        "infrastructure-scale utility rather than a venture; keeping it is correct for "
        "a green label and distorting for any claim about startup finance.",
    ),
    "farmhopping": (
        "keep",
        "Organic-food and farmers-market marketplace tagged Organic Food, Farming and "
        "Environmental Innovation. Sustainable agriculture is one of the eleven "
        "sub-domains, so this is in scope.",
    ),
    "playground-energy": (
        "keep",
        "Playground equipment that harvests energy from children's movement to "
        "generate electricity. Marginal in scale, genuine in kind.",
    ),
    # --- advanced-economy companies in the top 150 ---
    "agendia": (
        "exclude",
        "Molecular cancer diagnostics. Matched on generic 'sustainab'/'environmental' "
        "tokens with no green product. $122m, so material to AE green dollars.",
    ),
    "growlife": (
        "exclude",
        "Cannabis cultivation equipment retailer, matched on 'hydroponic'. Indoor "
        "cannabis growing is energy-intensive and is not sustainable agriculture in the "
        "sense this report uses.",
    ),
    "gainspan": (
        "exclude",
        "Low-power Wi-Fi chipsets. Matched on 'battery', which appears as battery LIFE "
        "in the product description, not as energy storage.",
    ),
    "virident-systems": (
        "exclude",
        "Flash memory and server storage. Matched on a generic cleantech token with no "
        "green product in the record.",
    ),
    "luca-technologies": (
        "review",
        "Stimulates biogenic methane production from existing coal seams. Marketed as "
        "clean energy, but the product is coal-bed methane, a fossil fuel. Arguably "
        "the fossil veto should cover it.",
    ),
}


def _evidence_strength(pattern_ids: str) -> str:
    """Classify how specific the green evidence is for a company."""
    if not isinstance(pattern_ids, str) or not pattern_ids.strip():
        return "none"
    ids = [p for p in pattern_ids.split("|") if p]
    specific = [p for p in ids if not p.startswith("general_unspecified")]
    if specific:
        return "specific_subdomain"
    if len(ids) == 1:
        return "single_generic_pattern"
    return "generic_only"


def _default_call(strength: str, tier: str) -> tuple[str, str]:
    """Fallback recommendation where the company was not individually identified."""
    if tier in {"A", "A+B"}:
        return (
            "keep",
            "Flagged cleantech by the snapshot's own category_code, which is "
            "independent of our lexicon. Pattern evidence corroborates.",
        )
    if strength == "specific_subdomain":
        return (
            "keep",
            "Matched a specific sub-domain pattern, not a generic green token. "
            "Basis: pattern evidence only; company not individually identified.",
        )
    if strength == "single_generic_pattern":
        return (
            "review",
            "Green label rests on a single generic token with no sub-domain detail "
            "and no corroborating category_code. Weakest admissible evidence.",
        )
    return (
        "review",
        "Generic green tokens only, no sub-domain detail. Basis: pattern evidence "
        "only; company not individually identified.",
    )


def _annotate(df: pd.DataFrame) -> pd.DataFrame:
    """Attach recommendation, reason and basis to a worksheet."""
    out = df.copy()
    out["evidence_strength"] = out["green_matched_pattern_ids"].map(_evidence_strength)

    recs, reasons, bases = [], [], []
    for _, row in out.iterrows():
        slug = str(row["permalink_norm"]).strip().lower()
        if slug in NAMED_CALLS:
            rec, reason = NAMED_CALLS[slug]
            basis = "company identified by name and taxonomy"
        else:
            rec, reason = _default_call(
                row["evidence_strength"], str(row.get("green_tier", ""))
            )
            basis = "pattern evidence only"
        recs.append(rec)
        reasons.append(reason)
        bases.append(basis)

    out["recommendation"] = recs
    out["reason"] = reasons
    out["basis"] = bases
    out["ratified"] = ""  # the supervisor fills this column
    return out


def build(
    cfg: Config, labels: pd.DataFrame, deals: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build both worksheets and return them with a summary."""
    funding = (
        deals.loc[deals["green"]]
        .groupby("object_id")
        .agg(
            in_window_deals=("raised_amount_usd", "size"),
            in_window_usd=("raised_amount_usd", "sum"),
            first_year=("year", "min"),
            bloc=("bloc", "first"),
        )
    )
    enriched = labels.merge(funding, left_on="object_id", right_index=True, how="inner")

    cols = [
        "permalink_norm",
        "name",
        "country_code",
        "bloc",
        "green_tier",
        "category_code",
        "green_subdomain",
        "in_window_deals",
        "in_window_usd",
        "first_year",
        "green_matched_pattern_ids",
        "match_text",
    ]

    # Worksheet 1: top 150 Tier-B-only by funding, for bulk ratification.
    top150 = (
        enriched.loc[enriched["green"] & enriched["tier_b_surviving"] & ~enriched["tier_a"]]
        .sort_values("in_window_usd", ascending=False)
        .head(150)[cols]
        .reset_index(drop=True)
    )
    top150 = _annotate(top150)

    # Worksheet 2: every EM green company, reviewed individually.
    em = (
        enriched.loc[enriched["green"] & enriched["bloc"].eq("EM")]
        .sort_values("in_window_usd", ascending=False)[cols]
        .reset_index(drop=True)
    )
    em = _annotate(em)
    em["share_of_em_green_usd_pct"] = (
        100 * em["in_window_usd"] / em["in_window_usd"].sum()
    ).round(2)

    for frame, name in (
        (top150, "proposal_exclusions_top150"),
        (em, "proposal_exclusions_em_green"),
    ):
        path = cfg.path("tables") / f"{name}.csv"
        frame.to_csv(path, index=False)
        LOG.info("wrote %-46s %d rows", path.name, len(frame))

    summary = {
        "top150": {
            "rows": int(len(top150)),
            "recommendations": top150["recommendation"].value_counts().to_dict(),
            "named_calls": int(
                (top150["basis"] == "company identified by name and taxonomy").sum()
            ),
            "proposed_exclusion_usd": float(
                top150.loc[top150["recommendation"].eq("exclude"), "in_window_usd"].sum()
            ),
        },
        "em_green": {
            "rows": int(len(em)),
            "recommendations": em["recommendation"].value_counts().to_dict(),
            "proposed_exclusion_usd": float(
                em.loc[em["recommendation"].eq("exclude"), "in_window_usd"].sum()
            ),
            "proposed_exclusion_usd_share_pct": round(
                float(
                    100
                    * em.loc[em["recommendation"].eq("exclude"), "in_window_usd"].sum()
                    / em["in_window_usd"].sum()
                ),
                2,
            ),
            "evidence_strength": em["evidence_strength"].value_counts().to_dict(),
        },
    }
    LOG.info("top-150 worksheet: %s", summary["top150"]["recommendations"])
    LOG.info(
        "EM green worksheet: %s; proposed exclusions are %.1f%% of EM green dollars",
        summary["em_green"]["recommendations"],
        summary["em_green"]["proposed_exclusion_usd_share_pct"],
    )
    return top150, em, summary
