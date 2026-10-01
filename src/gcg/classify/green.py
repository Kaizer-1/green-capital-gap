"""Three-tier green classifier with a full per-company audit trail.

CLAUDE.md §6. The tiers are kept separable so every headline result can be
re-run under the strict definition:

- **Tier A, strict** — ``category_code == 'cleantech'``, the snapshot's own flag.
- **Tier B, lexicon** — case-insensitive regex over the concatenation of
  ``category_list``, ``category_code``, ``tag_list``, ``short_description`` and
  ``market``, driven entirely by ``config/green_lexicon.yaml``. No pattern is
  hard-coded here.
- **Tier C, exclusions** — vetoes that kill false positives before they reach
  the sample.

Headline definition: ``green = TierA OR (TierB AND NOT TierC)``. Note that
Tier C vetoes Tier B only. A company the snapshot itself flags as cleantech is
not removed by a lexicon exclusion.

The classifier emits an auditable table rather than a boolean: for every company
it records which tier fired, the actual regexes that matched, the assigned
sub-domain, and the reason for any veto. Appendix A and the top-150 manual audit
both read from that table.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from gcg.config import Config, get_logger

LOG = get_logger("classify.green")

_SEP = " | "
_PATTERN_JOIN = " ;; "
_GENERAL = "general_unspecified"


@dataclass(frozen=True)
class _Pattern:
    """One compiled lexicon pattern and where it came from."""

    subdomain: str
    index: int
    regex: str
    gated_by: str | None = None

    @property
    def label(self) -> str:
        """Short identifier used in the audit table."""
        suffix = f"@{self.gated_by}" if self.gated_by else ""
        return f"{self.subdomain}#{self.index}{suffix}"


def _compile_patterns(cfg: Config, *, admit_gated: dict[str, bool]) -> list[_Pattern]:
    """Collect every active Tier-B pattern, honouring the gating flags."""
    lex = cfg.lexicon
    out: list[_Pattern] = []

    for name, block in lex["subdomains"].items():
        for i, rx in enumerate(block["patterns"]):
            out.append(_Pattern(subdomain=name, index=i, regex=rx))

    for i, rx in enumerate(lex[_GENERAL]["patterns"]):
        out.append(_Pattern(subdomain=_GENERAL, index=i, regex=rx))

    for name, block in lex.get("gated_patterns", {}).items():
        flag = block["flag"]
        if not admit_gated.get(flag, False):
            LOG.info("gated pattern group %r disabled (flag %s = false)", name, flag)
            continue
        for i, rx in enumerate(block["patterns"]):
            out.append(
                _Pattern(subdomain=block["subdomain"], index=i, regex=rx, gated_by=name)
            )
    return out


def build_match_text(df: pd.DataFrame, cfg: Config) -> tuple[pd.Series, list[str]]:
    """Concatenate the configured match fields into one searchable string per company.

    Fields absent from the joined table are skipped with a logged warning rather
    than silently ignored. The separator is a pipe because several lexicon
    patterns use a lookahead for a taxonomy-token boundary.

    Returns
    -------
    tuple[pandas.Series, list[str]]
        The concatenated text, and the field names actually used.
    """
    wanted = cfg.lexicon["match_fields"]
    present = [f for f in wanted if f in df.columns]
    missing = [f for f in wanted if f not in df.columns]
    if missing:
        LOG.warning("match fields absent from the joined table, skipped: %s", missing)
    if not present:
        msg = f"none of the configured match_fields {wanted} are present"
        raise ValueError(msg)

    parts = [df[f].astype("string").fillna("") for f in present]
    text = parts[0]
    for part in parts[1:]:
        text = text.str.cat(part, sep=_SEP)
    LOG.info("match text built from %d fields: %s", len(present), present)
    return text.fillna(""), present


def count_taxonomy_tags(series: pd.Series) -> pd.Series:
    """Count non-empty pipe-delimited tags in a ``category_list`` value.

    Used to test whether emerging-market companies carry systematically fewer
    tags, which would be a coverage-bias finding rather than a config note.
    """
    raw = series.astype("string").fillna("")
    return (
        raw.str.strip("|")
        .str.split("|")
        .apply(
            lambda parts: (
                sum(1 for p in parts if str(p).strip()) if isinstance(parts, list) else 0
            )
        )
    )


def cohens_kappa(a: pd.Series, b: pd.Series) -> dict[str, float]:
    """Cohen's kappa for two binary labellings, with the confusion cells.

    Reported between Tier A and Tier B per CLAUDE.md §6. Implemented directly
    rather than pulled from a dependency, so the agreement figure in the report
    is traceable to arithmetic in this file.
    """
    x = a.astype(bool).to_numpy()
    y = b.astype(bool).to_numpy()
    n = len(x)
    if n == 0:
        return {"kappa": float("nan"), "n": 0}

    both = int((x & y).sum())
    a_only = int((x & ~y).sum())
    b_only = int((~x & y).sum())
    neither = int((~x & ~y).sum())

    po = (both + neither) / n
    pa_yes, pb_yes = x.mean(), y.mean()
    pe = pa_yes * pb_yes + (1 - pa_yes) * (1 - pb_yes)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")

    return {
        "kappa": round(float(kappa), 4),
        "observed_agreement": round(float(po), 4),
        "expected_agreement": round(float(pe), 4),
        "n": n,
        "both": both,
        "tier_a_only": a_only,
        "tier_b_only": b_only,
        "neither": neither,
    }


def classify(
    df: pd.DataFrame,
    cfg: Config,
    *,
    admit_bare_energy: bool | None = None,
) -> pd.DataFrame:
    """Classify companies and return the full audit table.

    Parameters
    ----------
    df
        Company-level frame carrying the match fields and ``permalink_norm``.
    cfg
        Project configuration.
    admit_bare_energy
        Override for the ``admit_bare_energy`` flag. ``None`` uses the headline
        setting from ``pipeline.yaml``.

    Returns
    -------
    pandas.DataFrame
        One row per input company with the tier flags, the regexes that fired,
        the sub-domain assignment, any veto reason, and the headline label.
    """
    lex = cfg.lexicon
    flags = {
        "admit_bare_energy": cfg.flag("admit_bare_energy")
        if admit_bare_energy is None
        else admit_bare_energy
    }
    patterns = _compile_patterns(cfg, admit_gated=flags)
    text, _ = build_match_text(df, cfg)

    # ---- Tier A: the snapshot's own flag -------------------------------
    tier_a_cfg = lex["tier_a"]
    field = tier_a_cfg["field"]
    values = {str(v).strip().lower() for v in tier_a_cfg["values"]}
    tier_a = (
        df[field].astype("string").str.strip().str.lower().isin(values)
        if field in df.columns
        else pd.Series(False, index=df.index)
    )

    # ---- Tier B: one vectorised pass per pattern -----------------------
    hits = np.zeros((len(df), len(patterns)), dtype=bool)
    for j, pat in enumerate(patterns):
        hits[:, j] = text.str.contains(pat.regex, case=False, regex=True, na=False).to_numpy()
    LOG.info("Tier B: %d patterns evaluated over %d companies", len(patterns), len(df))

    tier_b = hits.any(axis=1)

    # ---- Tier C: exclusions --------------------------------------------
    veto_all = np.zeros(len(df), dtype=bool)
    veto_reason = np.array([""] * len(df), dtype=object)
    veto_pattern = np.array([""] * len(df), dtype=object)
    subdomain_veto: dict[str, np.ndarray] = {}

    for rule in lex["exclusions"]:
        matched = text.str.contains(
            rule["pattern"], case=False, regex=True, na=False
        ).to_numpy()
        if rule["scope"] == "veto_all":
            first = matched & ~veto_all
            veto_reason[first] = rule["reason"].strip()
            veto_pattern[first] = rule["pattern"]
            veto_all |= matched
        else:
            target = rule["subdomain"]
            subdomain_veto.setdefault(target, np.zeros(len(df), dtype=bool))
            subdomain_veto[target] |= matched

    # ---- sub-domain assignment -----------------------------------------
    by_subdomain: dict[str, np.ndarray] = {}
    for j, pat in enumerate(patterns):
        acc = by_subdomain.setdefault(pat.subdomain, np.zeros(len(df), dtype=bool))
        acc |= hits[:, j]
    for name, vetoed in subdomain_veto.items():
        if name in by_subdomain:
            by_subdomain[name] &= ~vetoed

    priority = [s for s in lex["subdomain_priority"] if s in by_subdomain]
    primary = np.array([""] * len(df), dtype=object)
    for name in reversed(priority):
        primary[by_subdomain[name]] = name

    all_labels = np.array([""] * len(df), dtype=object)
    stacked = (
        np.vstack([by_subdomain[n] for n in priority]) if priority else np.zeros((0, len(df)))
    )
    for i in range(len(df)):
        active = [priority[k] for k in range(len(priority)) if stacked[k, i]]
        all_labels[i] = "|".join(active)

    # Tier B survives only if at least one sub-domain survived its vetoes.
    tier_b_surviving = stacked.any(axis=0) if priority else np.zeros(len(df), dtype=bool)

    # ---- matched-pattern audit trail -----------------------------------
    labels_fired = np.array([""] * len(df), dtype=object)
    regexes_fired = np.array([""] * len(df), dtype=object)
    rows_with_hits = np.flatnonzero(tier_b)
    for i in rows_with_hits:
        idx = np.flatnonzero(hits[i])
        labels_fired[i] = "|".join(patterns[j].label for j in idx)
        regexes_fired[i] = _PATTERN_JOIN.join(patterns[j].regex for j in idx)

    # ---- gated-pattern dependence --------------------------------------
    gated_cols = [j for j, p in enumerate(patterns) if p.gated_by is not None]
    ungated_cols = [j for j, p in enumerate(patterns) if p.gated_by is None]
    if gated_cols:
        hit_gated = hits[:, gated_cols].any(axis=1)
        hit_ungated = (
            hits[:, ungated_cols].any(axis=1) if ungated_cols else np.zeros(len(df), bool)
        )
        depends_on_gated = hit_gated & ~hit_ungated
    else:
        depends_on_gated = np.zeros(len(df), dtype=bool)

    # ---- manual audit decisions ----------------------------------------
    manual_excl = {
        str(e["permalink"]).strip().lower(): e["reason"]
        for e in (lex.get("manual_exclusions") or [])
    }
    manual_incl = {
        str(e["permalink"]).strip().lower(): e["reason"]
        for e in (lex.get("manual_inclusions") or [])
    }
    slug = df["permalink_norm"].astype("string").fillna("")
    is_manual_excl = slug.isin(manual_excl).to_numpy()
    is_manual_incl = slug.isin(manual_incl).to_numpy()
    manual_reason = np.array([""] * len(df), dtype=object)
    for i in np.flatnonzero(is_manual_excl):
        manual_reason[i] = f"manual exclusion: {manual_excl[slug.iloc[i]]}"
    for i in np.flatnonzero(is_manual_incl):
        manual_reason[i] = f"manual inclusion: {manual_incl[slug.iloc[i]]}"

    # ---- headline definition -------------------------------------------
    # `green` is the RAW classifier output: patterns only. Manual audit
    # decisions are deliberately NOT folded in here, because the classifier is
    # symmetric by construction (the same lexicon is applied to every company
    # regardless of bloc) while manual curation is not: the emerging-market
    # green set was audited exhaustively and advanced-economy companies only at
    # the top of the funding distribution. Mixing the two would make the
    # headline depend on an asymmetric process. See docs/METHODOLOGY.md §6.
    #
    # Tier C vetoes Tier B only. Tier A is the snapshot's own flag and is not
    # overridden by a lexicon exclusion.
    green = tier_a | (tier_b_surviving & ~veto_all)

    # `green_curated` applies the ratified manual decisions as a robustness
    # specification, reported alongside the raw headline. A manual exclusion
    # DOES override Tier A here: the point of excluding a coal-predominant IPP
    # is precisely that the snapshot flagged it as cleantech.
    green_curated = (green & ~is_manual_excl) | is_manual_incl

    tier = np.array(["none"] * len(df), dtype=object)
    tier[tier_b_surviving & ~veto_all] = "B"
    tier[tier_a] = "A"
    tier[tier_a & tier_b_surviving & ~veto_all] = "A+B"
    tier[veto_all & ~tier_a] = "C_vetoed"

    out = pd.DataFrame(
        {
            "object_id": df["id"].to_numpy() if "id" in df.columns else df.index.to_numpy(),
            "permalink_norm": slug.to_numpy(),
            "name": df["name"].to_numpy() if "name" in df.columns else "",
            "country_code": df["country_code"].to_numpy()
            if "country_code" in df.columns
            else "",
            "category_code": df[field].to_numpy() if field in df.columns else "",
            "green": green,
            "green_curated": green_curated,
            "manual_excluded": is_manual_excl,
            "manual_included": is_manual_incl,
            "manual_decision_reason": manual_reason,
            "green_strict_tier_a": tier_a.to_numpy(),
            "green_tier": tier,
            "tier_a": tier_a.to_numpy(),
            "tier_b_raw": tier_b,
            "tier_b_surviving": tier_b_surviving,
            "tier_c_vetoed": veto_all,
            "veto_reason": veto_reason,
            "veto_pattern": veto_pattern,
            "green_subdomain": np.where(green, primary, ""),
            "green_subdomains_all": np.where(green, all_labels, ""),
            "green_matched_pattern_ids": labels_fired,
            "green_matched_patterns": regexes_fired,
            "depends_on_gated_pattern": depends_on_gated,
            "n_patterns_fired": hits.sum(axis=1),
        }
    )
    if "category_list" in df.columns:
        out["taxonomy_tag_count"] = count_taxonomy_tags(df["category_list"]).to_numpy()
    out["match_text"] = text.str.slice(0, 300).to_numpy()
    return out
