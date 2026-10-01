"""Recover country codes for companies whose ``country_code`` is blank.

2,160 in-window deal rows, from 1,650 companies, carry no country code. That is
a larger block than the entire emerging-market bloc (1,264 deals), so leaving it
unresolved would discard the single biggest body of potentially emerging-market
evidence in the dataset.

``city``, ``state_code`` and ``region`` are also entirely blank for these
companies — ``region`` is the literal string ``"unknown"`` — so geographic
recovery from the relational dump alone is impossible. Two routes remain:

1. **The flat mirror's own ``country_code``.** Authoritative: same underlying
   database, later vintage, so a country there is a Crunchbase assertion rather
   than an inference of ours.
2. **Country-code top-level domains**, accepted only for an explicit allow-list.

Route 2 is the dangerous one and the allow-list is the safeguard. Several
ccTLDs belong to emerging or least-developed countries and are sold worldwide as
vanity domains: ``.tv`` (Tuvalu, an LDC), ``.ws`` (Samoa), ``.st`` (Sao Tome, an
LDC), ``.nr`` (Nauru), ``.ly`` (Libya), ``.io``, ``.me``, ``.am``. Accepting them
would fabricate emerging-market and LDC ventures out of domain marketing —
nine Tuvaluan ventures from ``.tv`` alone. Every refusal is enumerated in
``config/blocs.yaml`` with its reason.

Every recovered row is flagged with its route so any result can be re-run
without the inferred ones.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from gcg.config import Config, get_logger

LOG = get_logger("classify.recovery")

_HOST = re.compile(r"^(?:https?://)?(?:www\.)?([^/\s:?#]+)", re.I)

# ccTLDs belonging to emerging or least-developed countries that are sold
# worldwide as vanity domains. Accepting any of these as country evidence would
# fabricate exactly the emerging-market and LDC deals this project looks for, so
# the set is named and the avoided fabrications are reported.
FABRICATION_RISK_TLDS = frozenset(
    {"tv", "ws", "st", "nr", "ly", "me", "am", "fm", "ag", "gs", "to", "gl", "cc"}
)

RECOVERY_NONE = "none"
RECOVERY_FLAT = "flat_mirror"
RECOVERY_CCTLD = "cctld"
RECOVERY_MANUAL = "manual"


def extract_tld(series: pd.Series) -> pd.Series:
    """Extract the top-level domain from a URL or bare hostname."""

    def _one(value: object) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        match = _HOST.match(value.strip())
        if not match:
            return None
        parts = match.group(1).lower().split(".")
        return parts[-1] if len(parts) > 1 else None

    return series.map(_one).astype("string")


def recover(
    companies: pd.DataFrame,
    flat: pd.DataFrame,
    cfg: Config,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fill blank country codes, recording the route used for each.

    Parameters
    ----------
    companies
        The relational company table, with ``country_code`` and ``permalink_norm``.
    flat
        The flat mirror, used for its own ``country_code`` and ``homepage_url``.
    cfg
        Project configuration.

    Returns
    -------
    tuple[pandas.DataFrame, dict]
        The company frame with ``country_code_recovered`` and
        ``country_recovery_route`` columns added, plus diagnostics.
    """
    spec = cfg.blocs["country_recovery"]
    non_country = {str(c).strip().upper() for c in cfg.blocs["non_country_codes"]}

    out = companies.copy()
    raw = out["country_code"].astype("string").str.strip().str.upper()
    blank = raw.isna() | raw.eq("") | raw.isin(non_country)

    out["country_code_recovered"] = raw.mask(blank)
    out["country_recovery_route"] = pd.Series(RECOVERY_NONE, index=out.index, dtype="string")
    out.loc[~blank, "country_recovery_route"] = "original"

    n_blank = int(blank.sum())
    LOG.info("country recovery: %d companies have no usable country_code", n_blank)

    # ---- route 1: the flat mirror's own country_code --------------------
    n_flat = 0
    if spec.get("use_flat_mirror", True):
        mirror = (
            flat.loc[flat["permalink_norm"].notna(), ["permalink_norm", "country_code"]]
            .rename(columns={"country_code": "_flat_cc"})
            .drop_duplicates(subset=["permalink_norm"], keep="first")
        )
        out = out.merge(mirror, on="permalink_norm", how="left")
        flat_cc = out["_flat_cc"].astype("string").str.strip().str.upper()
        flat_cc = flat_cc.where(flat_cc.notna() & flat_cc.ne("") & ~flat_cc.isin(non_country))

        fill = out["country_code_recovered"].isna() & flat_cc.notna()
        out.loc[fill, "country_code_recovered"] = flat_cc[fill]
        out.loc[fill, "country_recovery_route"] = RECOVERY_FLAT
        n_flat = int(fill.sum())
        out = out.drop(columns=["_flat_cc"])
        LOG.info("  route 1 (flat mirror): recovered %d", n_flat)

    # ---- route 2: geographic ccTLD only --------------------------------
    n_cctld = 0
    refused_counts: dict[str, int] = {}
    if spec.get("use_cctld", True):
        accept = {k.lower(): v for k, v in spec["cctld_to_iso3"].items()}
        refused = {k.lower() for k in spec["cctld_refused"]}

        url = out["homepage_url"].astype("string")
        if "domain" in out.columns:
            url = url.fillna(out["domain"].astype("string"))
        tld = extract_tld(url)

        candidate = out["country_code_recovered"].isna() & tld.notna()
        mapped = tld.map(accept)

        fill = candidate & mapped.notna()
        out.loc[fill, "country_code_recovered"] = mapped[fill]
        out.loc[fill, "country_recovery_route"] = RECOVERY_CCTLD
        n_cctld = int(fill.sum())

        was_refused = candidate & tld.isin(refused)
        refused_counts = tld[was_refused].value_counts().to_dict()
        LOG.info("  route 2 (ccTLD): recovered %d", n_cctld)
        LOG.info(
            "  route 2 refused %d companies on vanity/generic TLDs: %s",
            int(was_refused.sum()),
            dict(sorted(refused_counts.items(), key=lambda kv: -kv[1])[:10]),
        )
        # The refusals that would have invented EM/LDC evidence.
        fabricated = {
            t: int(n) for t, n in refused_counts.items() if t in FABRICATION_RISK_TLDS
        }
        if fabricated:
            LOG.warning(
                "  had the vanity TLDs been accepted, these fake country attributions "
                "would have entered the sample: %s",
                fabricated,
            )

    still_blank = int(out["country_code_recovered"].isna().sum())
    recovered = n_flat + n_cctld
    stats = {
        "companies": int(len(out)),
        "blank_before": n_blank,
        "recovered_total": recovered,
        "recovered_flat_mirror": n_flat,
        "recovered_cctld": n_cctld,
        "recovery_rate": round(recovered / n_blank, 4) if n_blank else 0.0,
        "still_blank": still_blank,
        "refused_tld_counts": {str(k): int(v) for k, v in refused_counts.items()},
        "fabrication_avoided": {
            str(k): int(v)
            for k, v in refused_counts.items()
            if str(k) in FABRICATION_RISK_TLDS
        },
    }
    LOG.info(
        "country recovery: %d/%d blanks resolved (%.1f%%); %d still unknown",
        recovered,
        n_blank,
        100 * stats["recovery_rate"],
        still_blank,
    )
    return out, stats
