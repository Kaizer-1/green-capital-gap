"""Inject findings into the web page at build time.

The web edition originally resolved every statistic in the browser. That was the
wrong way round, for three reasons:

* the page's core content was JavaScript-dependent, so with scripts off the
  prose lost the numbers that carry its argument;
* numbers appeared a frame or more after first paint, which is a layout shift
  and a visible flicker on a slow connection;
* the report and the page reached their numbers by two different paths, and two
  paths are how two artefacts come to disagree.

So injection happens here, by the same mechanism ``gcg.report.render`` uses on
``report.md``: read ``findings.json``, substitute, and fail the build on anything
unresolved. The ``data-key`` attribute stays on every injected element, but its
job changes — it is no longer an instruction to the browser, it is an assertion
about what the element should contain. ``main.js`` checks it on load and
``checks.mjs`` checks it in CI, so a stale injection is caught rather than
shipped.

Injection is idempotent: it replaces an element's content whatever that content
currently is, so running it twice is the same as running it once.
"""

from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

from gcg.config import Config, get_logger, load_config
from gcg.report.render import (
    _CONFIDENCE_LEVEL,
    _findings_literals,
    apply_typography,
    check_typography,
    unmatched_numbers,
)

LOG = get_logger("web.inject")


class UnresolvedKeyError(RuntimeError):
    """The page asks for a finding that findings.json does not hold."""


class TypographyError(RuntimeError):
    """The page carries punctuation the report would have rejected."""


class StaleNumberError(RuntimeError):
    """The page states a number that no finding supports."""


def check_page_numbers(
    html: str, findings: dict[str, str], series: dict | None = None
) -> list[str]:
    """Every number on the page must be a value findings.json holds.

    The same gate the report runs over its prose and over the text baked into
    its figures, through the same scanner, so the three cannot drift on what
    counts as a number. An injected value passes by construction; what this
    catches is a number somebody typed into the markup.

    This is the "prove no hand-typed numbers" check from WEB.md §11 step 3, and
    it is here rather than in checks.mjs because reimplementing the exemptions
    in JavaScript would be a second copy of the rule.

    ``series.json`` counts alongside ``findings.json``. A figure's data table
    reproduces the series it plots, and those per-year values are pipeline
    output that simply has no prose counterpart. The rule being enforced is that
    no number was typed by a human, not that every number also appears in a
    sentence.
    """
    body = visible_text(html)
    # USNs are identifiers, not statistics, and the author list is injected.
    body = re.sub(r"\b\d[A-Z]{2}\d{2}[A-Z]{2}\d{3}\b", " ", body)
    # A confidence level is a property of the method, not a finding. Same
    # exemption the report's figure gate applies, from the same pattern.
    body = _CONFIDENCE_LEVEL.sub(" ", body)
    known = _findings_literals(findings)
    if series is not None:
        for token, keys in _findings_literals(_flatten_series(series)).items():
            known.setdefault(token, []).extend(keys)
    return [
        f"{raw!r} appears on the page but is not a value the pipeline exported; "
        "inject it from a key, or check it against the pipeline"
        for raw in unmatched_numbers(body, known)
    ]


def _flatten_series(node: object, prefix: str = "") -> dict[str, str]:
    """Every scalar in series.json, flattened to {path: value}.

    Feeds the same literal index findings.json feeds, so a number drawn from a
    plotted series is recognised as computed.
    """
    out: dict[str, str] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(_flatten_series(value, f"{prefix}.{key}"))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            out.update(_flatten_series(value, f"{prefix}[{i}]"))
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        out[prefix] = str(node)
    return out


# An element carrying data-key, with optional data-prefix / data-suffix. The
# content group is non-greedy and the pattern does not nest, which is fine
# because an injected element holds text and nothing else.
_SLOT = re.compile(
    r"(<(?P<tag>span|dd|dt|p|li|td|th|b|strong|em)\b(?P<attrs>[^>]*\bdata-key=\"(?P<key>[^\"]+)\"[^>]*)>)"
    r"(?P<body>.*?)"
    r"(</(?P=tag)>)",
    re.S,
)

_ATTR = re.compile(r'\bdata-(prefix|suffix)="([^"]*)"')


def inject(html: str, findings: dict[str, str]) -> tuple[str, list[str]]:
    """Substitute every ``data-key`` element's content. Returns html and misses."""
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        key = match.group("key")
        if key not in findings:
            missing.append(key)
            return match.group(0)
        affix = dict(_ATTR.findall(match.group("attrs")))
        value = f"{affix.get('prefix', '')}{findings[key]}{affix.get('suffix', '')}"
        # The same normalisation the report applies, from the same function: the
        # page read "1.92x" where the PDF read "1.92×" because findings.json
        # stores the raw form and only render.py was transforming it.
        return (
            f"{match.group(1)}{escape(apply_typography(value), quote=False)}{match.group(6)}"
        )

    return _SLOT.sub(replace, html), sorted(set(missing))


def inject_meta(html: str, meta: dict) -> str:
    """Fill the masthead from report/metadata.yaml.

    The author list was rendered by JavaScript from series.json, which meant the
    page lost its byline entirely with scripts off. It is content, not data
    visualisation, so it belongs in the HTML — injected, not typed, because
    metadata.yaml stays the one place those four names live.
    """
    authors = "\n".join(
        f"          <dt>{escape(a['name'])}</dt>\n          <dd>{escape(a['usn'])}</dd>"
        for a in meta["authors"]
    )
    html = re.sub(
        r'(<dl class="byline__authors"[^>]*>)(.*?)(</dl>)',
        lambda m: f"{m.group(1)}\n{authors}\n        {m.group(3)}",
        html,
        count=1,
        flags=re.S,
    )
    lines = {
        "guide": f"Under the guidance of {meta['guide']}",
        "institution": meta["institution"],
        "course-date": f"{meta['course']} · {meta['date']}",
    }
    for slot, text in lines.items():
        html = re.sub(
            rf'(<p class="byline__line" data-meta="{slot}">)(.*?)(</p>)',
            lambda m, t=text: f"{m.group(1)}{escape(t)}{m.group(3)}",
            html,
            count=1,
            flags=re.S,
        )
    return html


# One row-builder per figure, so the table says what that figure says. Keyed by
# the series.json key, which is what the markup's data-table attribute names.
# Every builder takes the same two arguments; the ones that need no findings
# lookup name the parameter with a leading underscore rather than varying the
# signature, so the dispatch below stays uniform.
def _table_fig02(
    spec: dict, findings: dict[str, str]
) -> tuple[str, list[str], list[list[str]]]:
    # Rates and intervals come from findings.json, not from the series numbers:
    # a table formatting its own 5.2 beside a report saying 5.20 is the same
    # class of disagreement the whole injection path exists to prevent.
    def key(mark: dict, suffix: str) -> str:
        return findings[f"h1.{mark['bloc'].lower()}_{suffix}"]

    return (
        "Green share of recorded venture deals by bloc, 2000 to 2012.",
        ["Bloc", "Green share of deals", "95% CI", "Deals", "Green deals"],
        [
            [
                m["label"],
                f"{key(m, 'rate_pct')}%",
                "not reported" if not m["draw_interval"] else key(m, "ci"),
                f"{m['n']:,}",
                f"{m['green']:,}",
            ]
            for m in spec["marks"]
        ],
    )


def _table_fig01(
    spec: dict,
    _findings: dict[str, str],
) -> tuple[str, list[str], list[list[str]]]:
    return (
        "Emerging-market share of world GDP against its share of recorded venture "
        "deals, by year.",
        ["Year", "Share of world GDP", "Share of recorded deals", "Gap"],
        [
            [str(m["year"]), f"{m['gdp_share']}%", f"{m['deal_share']}%", f"{m['gap_pp']} pp"]
            for m in spec["marks"]
        ],
    )


def _table_fig03(
    spec: dict,
    _findings: dict[str, str],
) -> tuple[str, list[str], list[list[str]]]:
    years = [p["year"] for p in spec["series"][0]["points"]]
    byid = {s["id"]: {p["year"]: p for p in s["points"]} for s in spec["series"]}
    columns = ["Year"]
    for s in spec["series"]:
        columns += [f"{s['label']} rate", f"{s['label']} green deals"]
    rows = []
    for year in years:
        row = [str(year)]
        for s in spec["series"]:
            p = byid[s["id"]].get(year)
            row += ["", ""] if p is None else [f"{p['rate']}%", f"{p['green']:,}"]
        rows.append(row)
    return (
        "Green share of recorded deals by bloc and year. No emerging-market "
        f"year-cell reaches the minimum cell size of {spec['min_cell']} green deals.",
        columns,
        rows,
    )


def _table_fig05(
    spec: dict,
    _findings: dict[str, str],
) -> tuple[str, list[str], list[list[str]]]:
    thin = {t["year"]: t["green"] for t in spec["thin_cells"]}
    return (
        "Green as a share of all recorded deals and of all disclosed dollars, by year.",
        ["Year", "Share of green deals", "Share of green dollars", "Green deals"],
        [
            [
                str(m["year"]),
                f"{m['count_share']}%",
                f"{m['dollar_share']}%",
                f"{thin.get(m['year'], m['green']):,}",
            ]
            for m in spec["marks"]
        ],
    )


def _table_fig06(
    spec: dict,
    _findings: dict[str, str],
) -> tuple[str, list[str], list[list[str]]]:
    return (
        "Share of green deals resolved to a specific sub-domain, by bloc.",
        ["Bloc", *(s["label"] for s in spec["segments"]), "Green deals"],
        [
            [m["label"], *(f"{m[s['id']]}%" for s in spec["segments"]), f"{m['n']:,}"]
            for m in spec["marks"]
        ],
    )


def _table_fig04(
    spec: dict,
    _findings: dict[str, str],
) -> tuple[str, list[str], list[list[str]]]:
    return (
        "Emerging-market representation relative to advanced economies, by sector, "
        "against each sector's capital intensity and the position the fit predicts.",
        [
            "Sector",
            "Observed representation",
            "Predicted",
            "Capital intensity (USD)",
            "EM deals",
            "AE deals",
        ],
        [
            [
                m["sector"],
                f"{m['observed']}\u00d7",
                f"{m['predicted']}\u00d7",
                f"{m['capital_intensity_usd']:,.0f}",
                f"{m['em_deals']:,}",
                f"{m['ae_deals']:,}",
            ]
            for m in sorted(spec["marks"], key=lambda m: m["observed"])
        ],
    )


def _table_fig07(
    spec: dict,
    _findings: dict[str, str],
) -> tuple[str, list[str], list[list[str]]]:
    return (
        "Green deals and disclosed green funding by year, in constant 2015 USD.",
        ["Year", "Green deals", "Disclosed funding (USD bn)", "Deals with an amount"],
        [
            [str(m["year"]), f"{m['deals']:,}", f"{m['usd_bn']}", f"{m['disclosed']:,}"]
            for m in spec["marks"]
        ],
    )


def _table_fig08(
    spec: dict,
    _findings: dict[str, str],
) -> tuple[str, list[str], list[list[str]]]:
    # The union of years, not one series': the two series do not cover the same
    # span, and taking the first left a year out of the table that the chart
    # draws.
    years = sorted({p["year"] for s in spec["series"] for p in s["points"]})
    byid = {s["id"]: {p["year"]: p for p in s["points"]} for s in spec["series"]}
    columns = ["Year"]
    for s in spec["series"]:
        columns += [f"{s['label']} index", f"{s['label']} deals"]
    rows = []
    for year in years:
        row = [str(year)]
        for s in spec["series"]:
            p = byid[s["id"]].get(year)
            row += ["", ""] if p is None else [str(p["indexed"]), f"{p['deals']:,}"]
        rows.append(row)
    return (
        f"Deal volume indexed to {spec['base_year']} = 100, by bloc and green status. "
        "The emerging-market green series is not drawn.",
        columns,
        rows,
    )


def _table_fig09(
    spec: dict,
    _findings: dict[str, str],
) -> tuple[str, list[str], list[list[str]]]:
    return (
        "Non-dilutive share of deals by bloc and green status.",
        ["Group", "Non-dilutive share", "Grant rounds", "Debt rounds", "Deals"],
        [
            [
                m["label"],
                f"{m['pct']}%",
                f"{m['grant']:,}",
                f"{m['debt']:,}",
                f"{m['n']:,}",
            ]
            for m in spec["marks"]
        ],
    )


def _table_fig10(
    spec: dict,
    _findings: dict[str, str],
) -> tuple[str, list[str], list[list[str]]]:
    return (
        "Green funding intensity and market depth, by country. The "
        "electricity-access deficit column is the regressor that could not be tested.",
        [
            "Country",
            "GDP per capita (USD)",
            "Green funding per capita (USD)",
            "Green deals",
            "Electricity deficit",
        ],
        [
            [
                m["country"],
                f"{m['gdp_per_capita']:,.0f}",
                f"{m['green_usd_per_capita']}",
                f"{m['green_deals']:,}",
                f"{m['electricity_deficit_pct']}%",
            ]
            for m in spec["marks"]
        ],
    )


def _table_fig11(
    spec: dict,
    _findings: dict[str, str],
) -> tuple[str, list[str], list[list[str]]]:
    return (
        "Observations available in each emerging-market test cell, against the "
        f"pre-registered minimum of {spec['threshold']['value']}.",
        ["Hypothesis", "Cell", "Observations", "Test it blocks", "Clears the minimum"],
        [
            [
                m["hypothesis"],
                m["label"],
                str(m["value"]),
                m["blocks"],
                "yes" if m["clears_threshold"] else "no",
            ]
            for m in spec["marks"]
        ],
    )


def _table_fig12(
    spec: dict,
    _findings: dict[str, str],
) -> tuple[str, list[str], list[list[str]]]:
    rows = []
    for panel in spec["panels"]:
        for m in panel["marks"]:
            rows.append([panel["label"], str(m["year"]), str(m["green"]), f"{m['deals']:,}"])
    return (
        "Green deals per year in two instruments measuring two populations. The "
        "panels share no axis and the data is never pooled.",
        ["Source", "Year", "Green deals", "All deals"],
        rows,
    )


def _table_figM1(  # noqa: N802 - matches the figure id
    spec: dict,
    _findings: dict[str, str],
) -> tuple[str, list[str], list[list[str]]]:
    months = [p["month"] for p in spec["series"][0]["points"]]
    byid = {s["id"]: {p["month"]: p for p in s["points"]} for s in spec["series"]}
    columns = ["Month"] + [f"{s['label']} share of its year" for s in spec["series"]]
    rows = []
    for month in months:
        row = [str(month)]
        for s in spec["series"]:
            p = byid[s["id"]].get(month)
            row.append("" if p is None else f"{p['share']}%")
        rows.append(row)
    return (
        "Monthly deals as a share of their own year, 2011 to 2013.",
        columns,
        rows,
    )


_TABLES = {
    "fig01_coverage": _table_fig01,
    "fig02_double_gap": _table_fig02,
    "fig03_rate_by_year": _table_fig03,
    "fig05_share_crossover": _table_fig05,
    "fig04_ladder": _table_fig04,
    "fig06_subdomain": _table_fig06,
    "fig07_cycle": _table_fig07,
    "fig08_crisis": _table_fig08,
    "fig09_instruments": _table_fig09,
    "fig10_depth_need": _table_fig10,
    "fig11_power_wall": _table_fig11,
    "fig12_continuity": _table_fig12,
    "figM1_censoring": _table_figM1,
}


def inject_tables(html: str, series: dict, findings: dict[str, str]) -> str:
    """Write each figure's data table into the page at build time.

    WEB.md §8 makes the table the screen-reader path and the no-JS fallback. It
    cannot be both while JavaScript builds it: with scripts off the page showed
    an empty reserved box and no table at all. Injecting it puts it in the HTML
    either way, and the stylesheet decides whether it is visible.
    """

    def cell(tag: str, text: str) -> str:
        attr = ' scope="col"' if tag == "th" else ""
        return f"<{tag}{attr}>{escape(apply_typography(text))}</{tag}>"

    def replace(match: re.Match[str]) -> str:
        key = match.group("key")
        if key not in _TABLES:
            return match.group(0)
        caption, columns, rows = _TABLES[key](series[key], findings)
        head = "".join(cell("th", c) for c in columns)
        body = "".join("<tr>" + "".join(cell("td", c) for c in r) + "</tr>" for r in rows)
        table = (
            f"<table><caption>{escape(caption)}</caption>"
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
        )
        # group(3) is the old content; group(4) is the closing tag. Returning
        # group(3) dropped the </div>, and the unclosed element swallowed the
        # figcaption into a 1px absolutely-positioned box.
        return f"{match.group(1)}{table}{match.group(4)}"

    return re.sub(
        r'(<div class="figure__table" data-table="(?P<key>[^"]+)">)(.*?)(</div>)',
        lambda m: replace(m),
        html,
        flags=re.S,
    )


def visible_text(html: str) -> str:
    """The page's prose, with tags, scripts, styles and chrome removed.

    Section numbers go with the chrome: "02" is a position in the document, not
    a measurement, and the figure numbers beside them come from a CSS counter
    and never appear in the source at all.
    """
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    body = re.sub(r'<span class="section__number">.*?</span>', " ", body, flags=re.S)
    # A value this project USED to produce, quoted to describe a defect. The
    # defect list cannot be written without naming what the wrong number was,
    # and those are by definition not current pipeline output. The exemption is
    # a visible class in the markup rather than a loosened rule, so every use of
    # it can be read and argued with.
    body = re.sub(r'<span class="was">.*?</span>', " ", body, flags=re.S)
    return re.sub(r"<[^>]+>", " ", body)


def main(cfg: Config | None = None) -> int:
    """Inject into web/index.html in place."""
    cfg = cfg or load_config()

    findings_path = cfg.path("findings")
    if not findings_path.is_file():
        msg = f"missing {findings_path}. Run `make analysis` first."
        raise FileNotFoundError(msg)
    findings = json.loads(findings_path.read_text(encoding="utf-8"))

    page = Path(cfg.root) / "web" / "index.html"
    html = page.read_text(encoding="utf-8")

    html, missing = inject(html, findings)
    if missing:
        msg = (
            f"{len(missing)} unresolved data-key(s) in {page.name}:\n  "
            + "\n  ".join(missing)
            + f"\n\n{len(findings)} keys are available in {findings_path.name}."
        )
        raise UnresolvedKeyError(msg)

    series = json.loads(
        (Path(cfg.root) / "web" / "data" / "series.json").read_text(encoding="utf-8")
    )
    html = inject_meta(html, series["meta"])
    html = inject_tables(html, series, findings)

    stale = check_page_numbers(html, findings, series)
    if stale:
        msg = (
            f"{len(stale)} number(s) on the page that no finding supports:\n  "
            + "\n  ".join(stale)
        )
        raise StaleNumberError(msg)

    typo = check_typography(visible_text(html))
    if typo:
        msg = (
            f"{len(typo)} typographic violation(s) on the page:\n  "
            + "\n  ".join(typo)
            + "\n\nThe report applies the same rule; the page must not diverge."
        )
        raise TypographyError(msg)

    page.write_text(html, encoding="utf-8")
    LOG.info(
        "injected %d statistic(s) and the masthead into %s",
        len(_SLOT.findall(html)),
        page.name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
