"""Ingest stage entry point: ``make data``.

Downloads every source, verifies checksums, writes ``data/MANIFEST.md`` and
prints row counts plus the head of each table (CLAUDE.md §13 step 2).
"""

from __future__ import annotations

import json
import sys
from typing import Any

import pandas as pd

from gcg.config import get_logger, load_config, seed_everything
from gcg.ingest import crunchbase, india, worldbank
from gcg.io import DataUnavailableError, SourceRecord, write_manifest

LOG = get_logger("ingest.run")

_HEAD_ROWS = 5
_HEAD_COLS = 7


def main() -> int:
    """Run every ingest, write the manifest, print the step-2 report."""
    cfg = load_config()
    cfg.ensure_dirs()
    seed_everything(cfg)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 40)

    tables: dict[str, pd.DataFrame] = {}
    records: list[SourceRecord] = []
    stats: dict[str, Any] = {}

    try:
        for name, module in (
            ("crunchbase", crunchbase),
            ("worldbank", worldbank),
            ("india", india),
        ):
            LOG.info("=" * 78)
            LOG.info("ingest: %s", name)
            LOG.info("=" * 78)
            tbl, rec, stat = module.ingest(cfg)
            tables.update(tbl)
            records += rec
            stats[name] = stat
    except DataUnavailableError as exc:
        LOG.error("INGEST STOPPED\n%s", exc)
        return 2

    write_manifest(cfg, records)

    diag_path = cfg.path("data_interim") / "ingest_diagnostics.json"
    diag_path.write_text(json.dumps(stats, indent=2, default=str) + "\n", encoding="utf-8")
    LOG.info("wrote %s", diag_path.name)

    _report(tables, stats)
    return 0


def _report(tables: dict[str, pd.DataFrame], stats: dict[str, Any]) -> None:
    """Print row counts and heads for human inspection at build step 2."""
    out = sys.stdout
    rule = "=" * 100

    print(f"\n{rule}\nSTEP 2 — INGEST REPORT\n{rule}", file=out)

    print("\nROW COUNTS\n" + "-" * 100, file=out)
    print(f"{'table':<26}{'rows':>12}{'cols':>7}   columns", file=out)
    for name, df in tables.items():
        cols = ", ".join(map(str, df.columns[:6]))
        suffix = ", ..." if df.shape[1] > 6 else ""
        print(f"{name:<26}{len(df):>12,}{df.shape[1]:>7}   {cols}{suffix}", file=out)

    join = stats["crunchbase"]["join"]
    print("\nPERMALINK JOIN — the methodological core\n" + "-" * 100, file=out)
    print(
        f"  relational companies (all)   {join['companies_relational_all']:>10,}\n"
        f"  relational WITH >=1 deal     {join['companies_relational_funded']:>10,}"
        "   <- the join denominator\n"
        f"  flat-mirror companies        {join['companies_flat']:>10,}\n"
        f"  matched on permalink         {join['companies_matched']:>10,}"
        f"   = {join['join_rate_companies']:.1%} of funded companies\n"
        f"  deals on matched companies   {join['deals_on_matched_companies']:>10,}"
        f"   = {join['join_rate_deals']:.1%} of all {join['deals_total']:,} deals\n"
        f"  funded-relational only       {join['funded_relational_only']:>10,}"
        "   (no rich category_list)\n"
        f"  flat only                    {join['flat_only']:>10,}"
        "   (no deal rows)",
        file=out,
    )

    link = stats["crunchbase"]["rounds_linkage"]
    print("\nDEAL-TO-COMPANY LINKAGE\n" + "-" * 100, file=out)
    print(
        f"  deal rows                    {link['deals_total']:>10,}\n"
        f"  linkable to a company        {link['linkable_to_company']:>10,}\n"
        f"  orphan object_id             {link['orphan_object_id']:>10,}"
        "   (no matching row in objects.csv)\n"
        f"  object_id not a company      {link['object_id_not_a_company']:>10,}",
        file=out,
    )

    rd = stats["crunchbase"]["rounds_raised_amount"]
    print(
        "\nDISCLOSURE — raised_amount_usd (NOT imputed; counts and dollars stay separate)\n"
        + "-" * 100,
        file=out,
    )
    total = rd["total"]
    print(
        f"  deal rows                    {total:>10,}\n"
        f"  amount disclosed             {rd['coerced_ok']:>10,}"
        f"   = {rd['coerced_ok'] / total:.1%}\n"
        f"  zero-encoded (undisclosed)   {rd.get('zero_encoded_null', 0):>10,}"
        f"   = {rd.get('zero_encoded_null', 0) / total:.1%}  <- encoded 0.0, NOT NaN\n"
        f"     of which genuinely undisclosed  {rd.get('genuinely_undisclosed', 0):>5,}\n"
        f"     of which FX conversion failures {rd.get('fx_conversion_failures', 0):>5,}"
        "   (positive local amount, no USD)\n"
        f"  NaN / blank                  {rd['blank_or_dash']:>10,}\n"
        f"  uncoercible                  {rd['uncoercible']:>10,}",
        file=out,
    )

    ins = stats["crunchbase"]["instruments"]
    print("\nINSTRUMENT MIX — normalised from funding_round_code\n" + "-" * 100, file=out)
    print(
        f"  from funding_round_code      {ins['from_primary_code']:>10,}\n"
        f"  from funding_round_type      {ins['from_fallback_type']:>10,}   (fallback)\n"
        f"  unknown                      {ins['unknown']:>10,}\n"
        f"  code/type conflicts          {ins['code_type_conflicts']:>10,}   (code wins)\n"
        f"  unmapped code values         {ins['unmapped_primary_values'] or 'none'}",
        file=out,
    )
    print(f"\n  {'instrument':<24}{'deals':>10}", file=out)
    for name, count in sorted(ins["instrument_counts"].items(), key=lambda kv: -kv[1]):
        print(f"  {name:<24}{count:>10,}", file=out)

    dates = stats["crunchbase"]["rounds_dates"]
    print("\nDATE RANGE — raw as ingested, pre-truncation\n" + "-" * 100, file=out)
    print(
        f"  funded_at min                {dates['min'][:10]:>10}\n"
        f"  funded_at max                {dates['max'][:10]:>10}\n"
        f"  unparseable                  {dates['unparseable_funded_at']:>10,}",
        file=out,
    )

    ig = stats["worldbank"]["income_groups"]
    ind = stats["worldbank"]["indicators"]
    ind_india = stats["india"]
    print("\nENRICHMENT\n" + "-" * 100, file=out)
    print(
        f"  income-group rows            {ig['rows']:>10,}"
        f"   {ig['countries']} countries, {ig['year_min']}-{ig['year_max']}\n"
        f"  unmapped income labels       {ig['unmapped_labels'] or 'none'}\n"
        f"  indicator rows               {ind['rows']:>10,}   {ind['series']} series\n"
        f"  co2 rows                     {stats['worldbank']['co2']['rows']:>10,}\n"
        f"  india rows                   {ind_india['rows']:>10,}"
        f"   {ind_india['date_min'][:10]} to {ind_india['date_max'][:10]}, "
        f"{ind_india['unparseable_dates']:,} unparseable dates",
        file=out,
    )

    print("\nHEADS\n" + "-" * 100, file=out)
    for name, df in tables.items():
        print(f"\n--- {name}  ({len(df):,} rows x {df.shape[1]} cols) ---", file=out)
        print(df.head(_HEAD_ROWS).iloc[:, :_HEAD_COLS].to_string(max_colwidth=28), file=out)

    print(f"\n{rule}", file=out)


if __name__ == "__main__":
    raise SystemExit(main())
