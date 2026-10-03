"""Resolve placeholders, enforce the writing standards, and render the PDF.

Six gates, all failures rather than warnings:

1. **Unresolved placeholders** (CLAUDE.md §2.2). Every statistic is a
   ``{{key}}`` resolved from ``outputs/findings.json``. A report that renders
   with a literal ``{{h1.rr}}`` is worse than one that does not render, because
   the first can be submitted.
2. **Banned phrases** (CLAUDE.md §10).
3. **Typography.** Primes used as apostrophes, ASCII ``x`` used as a
   multiplication sign, and hyphen-minus used as a minus sign are all defects a
   reader sees before they read a sentence.
4. **Print chrome.** A print variant that still carries its own finding
   sentence shows the reader that sentence twice.
5. **Figure alignment.** A print variant whose ink does not reach its canvas
   edges sits at a different indent from the caption beneath it and from every
   other figure in the document.
6. **PDF smoke test** on the extracted text of the rendered document.

The PDF is produced by handing a generated Typst file to the compiler directly
rather than through pandoc's template system. Pandoc's default template put the
page number inside the text block, so extracted text read ``15. The double gap``
for page 1 followed by heading 5; ``report/template.typ`` puts it in the page
margin. A smoke test on the extracted text fails the build if that class of
defect returns.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from gcg.config import Config, get_logger, load_config

LOG = get_logger("report.render")

_PLACEHOLDER = re.compile(r"\{\{([a-zA-Z0-9_.]+)\}\}")

_BANNED = [
    "delve",
    "underscore",
    "it is worth noting",
    "it's important to note",
    "in today's rapidly evolving",
    "navigate the complexities",
    "a testament to",
    "tapestry",
    "realm",
    "pivotal",
    "paradigm shift",
    "game-changer",
    "unlock the potential",
    "at the intersection of",
    "shed light on",
    "paving the way",
    "holistic",
]
_BANNED_OPENERS = ("Moreover,", "Furthermore,", "Additionally,")

# Two-letter tails that legitimately follow a digit, so the smoke test does not
# flag "49pp" or "2nd" as page-number bleed.
_UNIT_SUFFIXES = frozenset(
    {"st", "nd", "rd", "th", "pp", "bn", "mn", "kg", "km", "yr", "ms", "pc"}
)

# Compounds that must never break across a line. A non-breaking hyphen keeps
# "emerging-market" from rendering as "emergingmarket" at a line end.
_NB_HYPHEN = "‑"
_KEEP_TOGETHER = (
    "emerging-market",
    "advanced-economy",
    "income-controlled",
    "capital-intensity",
    "green-specific",
    "non-dilutive",
    "difference-in-differences",
    "leave-one-out",
    "missing-middle",
    "venture-stage",
    "sub-domain",
    "half-up",
    "pre-registered",
    "post-IPO",
    "cross-sector",
    "year-cell",
    "start-end",
)


class UnresolvedPlaceholderError(RuntimeError):
    """The report contains a placeholder with no value in findings.json."""


class BannedPhraseError(RuntimeError):
    """The rendered prose contains a phrase banned by the writing standards."""


class TypographyError(RuntimeError):
    """The rendered prose violates the typographic conventions."""


class PdfSmokeTestError(RuntimeError):
    """The rendered PDF shows a defect visible in its extracted text."""


class ChromeLeakError(RuntimeError):
    """A print-variant figure still carries the chrome it should have shed."""


class TypstCompileError(RuntimeError):
    """The Typst compiler rejected the generated document."""


class FigureAlignmentError(RuntimeError):
    """A print variant's ink does not reach its canvas edges."""


def check_column_width(cfg: Config) -> list[str]:
    """Fail if the figure canvas and the template's text column have drifted apart.

    Typst embeds every print variant at ``width: 100%`` of the text column, so a
    canvas wider than that column is scaled down and a narrower one is scaled up.
    Either way the type size chosen in ``print_mode.apply_print_rc`` is not the
    size the reader gets. This went unnoticed once: the canvas was built for a
    2.6cm margin while the template set 2.9cm, and every figure rendered at 96%.
    """
    import re as _re

    from gcg.viz.print_mode import SIDE_MARGIN_CM

    template = (cfg.root / "report" / "template.typ").read_text(encoding="utf-8")
    found = _re.search(r"left:\s*([\d.]+)cm,\s*right:\s*([\d.]+)cm", template)
    if not found:
        return ["could not read the side margins from report/template.typ"]
    left, right = float(found.group(1)), float(found.group(2))
    hits = []
    if left != right:
        hits.append(f"template.typ side margins differ: left {left}cm, right {right}cm")
    if abs(left - SIDE_MARGIN_CM) > 1e-9:
        hits.append(
            f"template.typ sets a {left}cm side margin but print_mode.SIDE_MARGIN_CM is "
            f"{SIDE_MARGIN_CM}cm, so every figure would be scaled by "
            f"{(21.0 - 2 * left) / (21.0 - 2 * SIDE_MARGIN_CM):.3f} when embedded"
        )
    return hits


def check_figure_alignment(cfg: Config, tolerance_in: float = 0.03) -> list[str]:
    """Fail if any print variant has slack between its ink and its canvas edge.

    Every print variant is embedded at ``width: 100%`` of the text column, so
    whatever blank space a figure carries inside its own canvas becomes an
    indent in the document. Because the subplot fractions were originally chosen
    per figure by hand, no two figures shared an edge: measured against the text
    block, one figure's ink started 122px in and another's 27px in, and several
    left 60-135px dead on the right. ``flush_fit`` removes that slack; this gate
    is what stops it from coming back silently when a figure gains a long tick
    label or an artist outside the axes.

    The tolerance is 0.03in — about 2pt, below what the eye picks up as a ragged
    edge down a page, and comfortably above ``flush_fit``'s own 0.01in pad.
    """
    from gcg.viz.print_mode import SPECS

    report = cfg.path("figures") / "print" / "_slack.json"
    if not report.is_file():
        return [
            f"no slack report at {report}. Run `make figures`, which writes it "
            "after building the print variants."
        ]

    slack = json.loads(report.read_text(encoding="utf-8"))
    hits = []
    for slug in SPECS:
        if slug not in slack:
            hits.append(f"{slug}: no slack measurement - the print variant was not built")
            continue
        # The four edge values are raster-measured ink; "tightbbox" sits beside
        # them and is not an edge, so it is named rather than iterated.
        over = {
            edge: slack[slug][edge]
            for edge in ("left", "right", "bottom", "top")
            if abs(slack[slug].get(edge, 9.9)) > tolerance_in
        }
        if over:
            detail = ", ".join(
                f"{edge} {value:+.3f}in" for edge, value in sorted(over.items())
            )
            hits.append(f"{slug}: {detail}")
    return hits


def check_print_chrome(cfg: Config) -> list[str]:
    """Fail if a print variant still contains its own caption's finding sentence.

    The print variants exist so the finding sentence, subtitle and source note
    are set by the document rather than rasterised inside the image. If a figure
    is built without ``theme.set_mode("print")`` taking effect, the title stays
    baked in and the reader sees it twice: once in the image and once in the
    caption. Extracting the text of each print PDF and looking for its own
    finding sentence catches exactly that.
    """
    from gcg.viz.print_mode import SPECS

    if not shutil.which("pdftotext"):
        LOG.warning("pdftotext not found; skipping the print-chrome check")
        return []

    hits = []
    for slug, spec in SPECS.items():
        path = cfg.path("figures") / "print" / f"{slug}_print.pdf"
        if not path.is_file():
            hits.append(f"{slug}: print variant missing at {path}")
            continue
        out = subprocess.run(  # noqa: S603
            ["pdftotext", str(path), "-"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if out.returncode != 0:
            continue
        # Compare on a normalised form: the image would carry the sentence with
        # its own spacing and line breaks.
        text = re.sub(r"\s+", " ", out.stdout).lower()
        probe = re.sub(r"\s+", " ", spec.finding).lower().rstrip(".")
        # A seven-word run is enough to identify the sentence without tripping
        # on an axis label that happens to share two words with it.
        words = probe.split()
        if len(words) >= 7 and " ".join(words[:7]) in text:
            hits.append(
                f"{slug}: print variant still contains its finding sentence "
                f"({' '.join(words[:7])!r}) - chrome was not stripped"
            )
    return hits


def resolve(
    text: str,
    findings: dict[str, str],
    *,
    escape: Callable[[str], str] | None = None,
) -> tuple[str, list[str]]:
    """Substitute every placeholder, returning the text and any unresolved keys.

    ``escape`` is applied to each substituted value, for targets whose syntax a
    value could collide with. The markdown body needs none; Typst captions do.
    """
    missing: list[str] = []

    def sub(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in findings:
            missing.append(key)
            return match.group(0)
        value = str(findings[key])
        return escape(value) if escape else value

    return _PLACEHOLDER.sub(sub, text), sorted(set(missing))


def apply_typography(text: str) -> str:
    """Normalise punctuation that a reader notices before they read a word.

    Applied after substitution so values coming out of findings.json are
    normalised too, and before the checks below, which then verify the result.
    """
    out = text
    # A prime is not an apostrophe. "H2's", never "H2′s".
    out = out.replace("′", "’")
    out = re.sub(r"(?<=[A-Za-z0-9])'(?=[a-z])", "’", out)
    # A multiplication sign is not the letter x.
    out = re.sub(r"(?<=\d)\s?x(?=\b|\s|[,.\]])", "×", out)
    # One minus-sign convention in numeric contexts.
    out = re.sub(r"(?<![\w−-])-(?=\d)", "−", out)
    # Compounds that must not break.
    for compound in _KEEP_TOGETHER:
        out = out.replace(compound, compound.replace("-", _NB_HYPHEN))
    return out


def check_banned(text: str) -> list[str]:
    """Return every banned phrase found in the rendered prose."""
    hits = []
    lowered = text.lower()
    for phrase in _BANNED:
        if re.search(rf"\b{re.escape(phrase)}\b", lowered):
            hits.append(phrase)
    for para in text.split("\n\n"):
        stripped = para.strip()
        for opener in _BANNED_OPENERS:
            if stripped.startswith(opener):
                hits.append(f"paragraph opener: {opener}")
    return sorted(set(hits))


class StaleNumberError(RuntimeError):
    """A literal number in the prose contradicts the computed findings."""


# Numbers that legitimately appear as literals: years, section and appendix
# references, licence versions, and the small cardinals ordinary prose uses.
_PROSE_NUMBER_OK = re.compile(
    r"""^(?:
        (?:19|20)\d\d          # a year
      | [0-9]                  # a single digit: "one of 5", list counts
      | 1[0-9]|2[0-5]          # small cardinals up to 25
    )$""",
    re.X,
)

# Numbers that are references or names rather than measurements. Stripped by
# CONTEXT before the scan, not by shape.
#
# These were previously exempted by the shape `\d{1,2}\.\d{1,2}`, meant to pass
# section references like "6.1". It also passed 5.43, 1.92, 22.81 and every
# other one- or two-digit decimal — including a WRONG one. The gate could only
# ever catch integers. Matching on context closes that.
_NOT_A_MEASUREMENT = re.compile(
    r"""
      \u00a7\s*\d+(?:\.\d+)*        # a section reference: §6.1, §4
    | \bCC\s+BY\s+\d+(?:\.\d+)*    # a licence version
    | \bCleantech\s+\d+(?:\.\d+)*   # Cleantech 1.0, a period's name
    | \bPython\s+\d+(?:\.\d+)*      # a language version
    | \bISO-?\d+(?:-\d+)*           # a standard's number
    """,
    re.X | re.I,
)


def _findings_literals(findings: dict[str, str]) -> dict[str, list[str]]:
    """Map each bare numeric token in findings.json to the keys that produce it."""
    index: dict[str, list[str]] = {}
    for key, value in findings.items():
        for token in re.findall(r"\d[\d,]*(?:\.\d+)?", str(value)):
            bare = token.replace(",", "")
            index.setdefault(bare, []).append(key)
            # A JSON number arrives as "68301.0" while the page displays
            # "68,301". Index the integer form too, so a whole number written
            # without its empty decimal still resolves.
            if bare.endswith(".0"):
                index.setdefault(bare[:-2], []).append(key)
    return index


# A number may carry a unit directly: "49.3pp", "1.92x", "5.43%". The unit is
# part of the token, so that "49.3pp" matches the finding 49.3 rather than
# degenerating to a bare "49" that matches nothing.
_NUMBER_TOKEN = re.compile(
    r"(?<![\w.$])(\d[\d,]*(?:\.\d+)?)(?:%|pp|x|\u00d7|bn|mn|m|k)?(?![\w])"
)


def unmatched_numbers(text: str, known: dict[str, list[str]]) -> list[str]:
    """Numbers in ``text`` that no finding holds, after the shared exemptions.

    One scanner for the prose and for the text baked into figures, so the two
    gates cannot drift apart on what counts as a number or what is exempt.
    """
    body = _NOT_A_MEASUREMENT.sub(" ", text)
    body = re.sub(r"\d{4}-\d{2}-\d{2}", " ", body)
    body = re.sub(r"(?:19|20)\d\d\s*[\u2013-]\s*\d{2,4}", " ", body)
    hits = []
    for match in _NUMBER_TOKEN.finditer(body):
        token = match.group(1).replace(",", "")
        if _PROSE_NUMBER_OK.match(token) or token in known:
            continue
        hits.append(match.group(0))
    return sorted(set(hits))


def check_stale_numbers(markdown: str, findings: dict[str, str]) -> list[str]:
    """Fail on a literal number in the prose that no finding agrees with.

    Called on the resolved text, after placeholder substitution.

    The placeholder gate only sees numbers that are placeholders. A number typed
    directly into a sentence is invisible to it, which is how "26 of the 28
    emerging-market green companies" survived in §5.4 while the figure caption
    beside it, resolved from findings.json, said 23 of 27.

    The rule: any number in the prose that looks like a statistic must either be
    a value some finding actually holds, or be exempt as a year, a section
    reference or a small cardinal. A number that is neither is either stale or
    was never computed, and both are defects.
    """
    body = re.split(r"^##\s+References\b", markdown, maxsplit=1, flags=re.M)[0]
    body = re.sub(r"```\{=typst\}.*?```", " ", body, flags=re.S)
    body = re.sub(r"`[^`]*`", " ", body)  # inline code: file names, column names
    body = re.sub(r"^\s*\|.*$", " ", body, flags=re.M)  # table rows
    body = re.sub(r"^#+ .*$", " ", body, flags=re.M)  # headings
    body = re.sub(r"\d{4}-\d{2}-\d{2}", " ", body)  # dates
    body = re.sub(r"(?:19|20)\d\d\s*[–-]\s*\d{2,4}", " ", body)  # year ranges

    # A sentence carrying a citation is quoting an external source, which
    # CLAUDE.md §2.5 permits as an alternative to computing a number. Those
    # sentences are skipped wholesale. The cost is a real hole: a stale computed
    # number sharing a sentence with a citation would not be caught. Keeping
    # computed and cited figures in separate sentences is what closes it.
    body = " ".join(part for part in re.split(r"(?<=[.!?])\s+", body) if "[@" not in part)

    return [
        f"{raw!r} appears in the prose but is not a value in findings.json; "
        "make it a placeholder, or check it against the pipeline"
        for raw in unmatched_numbers(body, _findings_literals(findings))
    ]


class FigureNumberError(RuntimeError):
    """A number baked into a figure contradicts the computed findings."""


# Strings a figure draws that are structural rather than claims: a scale legend,
# an axis unit, a confidence level. These are exempt by exact match so the
# exemption cannot quietly widen.
_FIGURE_TEXT_EXEMPT = frozenset(
    {
        # An index's base is a definition, not a measurement: the 100 is the
        # normalisation, and the base year beside it comes from config.
        "Deal volume, 2007 = 100",
    }
)

# A confidence level is a property of the method, not a finding. Stripped before
# the scan rather than exempting the number 95 everywhere.
_CONFIDENCE_LEVEL = re.compile(r"\b95\s*%?\s*(?:CI|confidence)", re.I)


def check_figure_numbers(cfg: Config, findings: dict[str, str]) -> list[str]:
    """Fail on a number drawn into a figure that no finding supports.

    Figure text is composed in Python and rasterised into a PDF before the
    renderer ever runs, so the prose gate has never been able to see it. That is
    how a hand-typed 2 reached a published figure past every other check, and how
    one figure came to print a bootstrap interval that disagreed with the
    sentence beside it.

    ``make figures`` writes the harvest; this applies the same membership rule
    the prose gate applies, through the same scanner.
    """
    report = cfg.path("figures") / "_text_audit.json"
    if not report.is_file():
        return [
            f"no figure-text audit at {report}. Run `make figures`, which writes it "
            "while each figure still exists."
        ]

    known = _findings_literals(findings)
    audit = json.loads(report.read_text(encoding="utf-8"))
    hits = []
    for slug, strings in sorted(audit.items()):
        for text in strings:
            if text.strip() in _FIGURE_TEXT_EXEMPT:
                continue
            for raw in unmatched_numbers(_CONFIDENCE_LEVEL.sub(" ", text), known):
                hits.append(f"{slug}: {raw!r} in {text.strip()[:70]!r}")
            # Figures are typeset by the same rules as the prose. This ran only
            # over the markdown, so a figure could draw "4.6x" on a page whose
            # sentences read "4.6×" and nothing noticed.
            for violation in check_typography(text):
                hits.append(f"{slug}: {violation} in {text.strip()[:70]!r}")
    return sorted(set(hits))


def check_typography(text: str) -> list[str]:
    """Return every typographic violation remaining after normalisation."""
    body = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith(("#", "`", "|"))
    )
    hits = []
    if "′" in body:
        hits.append("prime U+2032 used as an apostrophe")
    for match in re.finditer(r"\d\s?x\b", body):
        hits.append(f"ASCII 'x' as a multiplication sign: {match.group(0)!r}")
    for match in re.finditer(r"(?<![\w−])-\d", body):
        hits.append(f"hyphen-minus in a numeric context: {match.group(0)!r}")
    return sorted(set(hits))


def build_typst(cfg: Config, body_md: Path) -> Path:
    """Convert the resolved markdown to a Typst document using our template."""
    pandoc = shutil.which("pandoc")
    if not pandoc:
        msg = "pandoc not found. Install with: brew install pandoc typst"
        raise RuntimeError(msg)

    body_typ = cfg.root / "report" / ".body.typ"
    cmd = [pandoc, str(body_md), "-o", str(body_typ), "--to=typst", "--wrap=preserve"]
    bib = cfg.root / "report" / "references.bib"
    if bib.is_file():
        cmd += ["--citeproc", "--bibliography", str(bib)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)  # noqa: S603
    if result.returncode != 0:
        msg = f"pandoc failed (exit {result.returncode}): {result.stderr.strip()[:800]}"
        raise RuntimeError(msg)

    meta = load_metadata(cfg)
    words = count_words(body_md.read_text(encoding="utf-8"))
    captions, caption_gaps = caption_table(
        json.loads(cfg.path("findings").read_text(encoding="utf-8"))
    )
    if caption_gaps:
        msg = (
            f"{len(caption_gaps)} unresolved placeholder(s) in figure captions "
            f"(src/gcg/viz/print_mode.py):\n  " + "\n  ".join(caption_gaps)
        )
        raise UnresolvedPlaceholderError(msg)
    authors = ", ".join(f'(name: "{a["name"]}", usn: "{a["usn"]}")' for a in meta["authors"])
    main = cfg.root / "report" / ".report.typ"
    main.write_text(
        "\n".join(
            [
                '#import "template.typ": conf, exhibit, method-exhibit, csvtable, CAPTIONS',
                # Captions come from print_mode.SPECS, never from the markdown,
                # so a caption cannot describe a figure that has changed.
                captions,
                "#show: conf.with(",
                f'  title: "{meta["title"]}",',
                f'  subtitle: "{meta["subtitle"]}",',
                f'  shorttitle: "{meta["shorttitle"]}",',
                f'  footerright: "{meta["footerright"]}",',
                f"  authors: ({authors},),",
                f'  guide: "{meta["guide"]}",',
                f'  institution: "{meta["institution"]}",',
                f'  course: "{meta["course"]}",',
                f'  date: "{meta["date"]}",',
                # The word count is computed from the prose, never typed.
                f'  wordcount: "{words:,}",',
                ")",
                "",
                body_typ.read_text(encoding="utf-8"),
            ]
        ),
        encoding="utf-8",
    )
    return main


# Typst reads these as syntax inside a content block, so any value substituted
# into a caption has to be neutralised. Interval notation is the live hazard:
# an unescaped "[0.26, 0.65]" opens a content block and swallows the rest of
# the caption.
_TYPST_SPECIAL = str.maketrans({c: "\\" + c for c in "\\#$[]*_@<>`"})


def caption_table(findings: dict[str, str]) -> tuple[str, list[str]]:
    """Typst source binding every figure slug to its caption, and unresolved keys.

    The caption is assembled from the same ``PrintSpec`` the figure was rendered
    from, so the three tiers a reader sees are the three tiers the spec declares.

    Captions carry statistics, which means they are subject to the same rule as
    the prose: no number is typed into them. A caption writes ``{{h3.rr}}`` and
    this resolves it from ``findings.json``, so a caption cannot quote a stale
    number, and it cannot quote one whose generating code does not run. Both had
    happened: a caption reported a bias-corrected risk ratio of 0.44 from a
    function that was defined and never called, and another reported "26 of the
    28" emerging-market green companies when the counts were 23 of 27.
    """
    from gcg.viz.print_mode import SPECS, caption_for

    missing: list[str] = []
    rows = []
    for slug, spec in SPECS.items():
        text, gaps = resolve(caption_for(spec), findings, escape=_escape_typst)
        missing += [f"{slug}: {{{{{key}}}}}" for key in gaps]
        rows.append(f'  "{slug}": [{apply_typography(text)}]')
    return "#CAPTIONS.update((\n" + ",\n".join(rows) + ",\n))", missing


def _escape_typst(value: str) -> str:
    """Neutralise Typst syntax in a value substituted into a caption."""
    return value.translate(_TYPST_SPECIAL)


def load_metadata(cfg: Config) -> dict:
    """Read report/metadata.yaml, the single source of truth for front matter.

    The author list lives here and nowhere else: the title page, the README and
    the reproducibility statement all read from it rather than restating four
    names and four USNs in three places.
    """
    import yaml

    path = cfg.root / "report" / "metadata.yaml"
    if not path.is_file():
        msg = f"missing {path}"
        raise FileNotFoundError(msg)
    text = path.read_text(encoding="utf-8")
    # The file is fenced like YAML front matter; strip the delimiters.
    text = re.sub(r"^---\s*$", "", text, flags=re.M)
    return yaml.safe_load(text)


def count_words(markdown: str) -> int:
    """Count prose words, excluding figure blocks, tables, headings and appendices.

    The title page states the count "excluding figures, tables, references and
    appendices", so the counter has to honour that claim: everything from the
    first appendix heading onward is cut before counting.
    """
    body = re.split(r"^##\s+(?:Appendix|References)\b", markdown, maxsplit=1, flags=re.M)[0]
    text = re.sub(r"```\{=typst\}.*?```", " ", body, flags=re.S)
    text = re.sub(r"^\s*\|.*$", " ", text, flags=re.M)
    text = re.sub(r"^#+ .*$", " ", text, flags=re.M)
    text = re.sub(r"[*_`\[\]#>]", " ", text)
    return len([w for w in text.split() if any(c.isalpha() for c in w)])


def to_pdf(cfg: Config, main_typ: Path) -> Path | None:
    """Compile the Typst document, with the repository as the file root."""
    typst = shutil.which("typst")
    if not typst:
        LOG.warning("typst not found; skipping PDF. Install with: brew install typst")
        return None
    pdf = cfg.path("report_pdf")
    cmd = [typst, "compile", "--root", str(cfg.root), str(main_typ), str(pdf)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)  # noqa: S603
    if result.returncode != 0:
        # A failed compile used to log and return None, and main() returned 0, so
        # `make all` reported success while report.pdf did not exist. The PDF is
        # the graded artefact; a build that does not produce it has failed.
        msg = f"typst failed (exit {result.returncode}):\n{result.stderr.strip()[:1500]}"
        raise TypstCompileError(msg)
    LOG.info("wrote %s", pdf.name)
    return pdf


def heading_lines(markdown: str) -> set[str]:
    """Every numbered heading in the source, as extraction would render it.

    The fused-page-number check cannot tell ``15. The double gap`` (page 1 glued
    to heading 5) from ``10. Limitations`` (a real heading) by shape alone. It
    tells them apart by asking the source which headings exist.
    """
    found = set()
    for line in markdown.splitlines():
        match = re.match(r"^#+\s+(\d+(?:\.\d+)*\.?)\s+(.+?)\s*$", line)
        if match:
            number = match.group(1).rstrip(".")
            found.add(f"{number}. {match.group(2)}".lower())
    return found


def smoke_test_pdf(pdf: Path, headings: set[str] | None = None) -> list[str]:
    """Check the rendered PDF's extracted text for layout bleed.

    The specific defect this exists for: a page number rendered inside the text
    block concatenates with the following page's first line, so extraction reads
    ``15. The double gap``. Any digit sitting immediately against a heading
    number or a sentence-initial capital is the signature.
    """
    if not shutil.which("pdftotext"):
        LOG.warning("pdftotext not found; skipping the PDF smoke test")
        return []
    out = subprocess.run(  # noqa: S603
        ["pdftotext", str(pdf), "-"],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if out.returncode != 0:
        return [f"pdftotext failed: {out.stderr.strip()[:200]}"]

    hits = []
    for raw in out.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        # A digit immediately followed by a section number, e.g. "15. The..."
        if re.match(r"^\d+\d+\.\s+[A-Z]", line) and line.lower() not in (headings or set()):
            hits.append(f"page number fused with a heading number: {line[:60]!r}")
        # A digit immediately followed by a capitalised word starting a sentence.
        if re.match(r"^\d+[A-Z][a-z]{2,}", line):
            hits.append(f"page number fused with body text: {line[:60]!r}")
        # A digit glued to a lower-case word mid-body, e.g. "3on both sides".
        # Two letters is enough: the defect that shipped was exactly "3on". The
        # digit must start a token, so "1RV23IS058" and "2015" are not hits, and
        # ordinal suffixes are excluded explicitly.
        for m in re.finditer(r"(?<![\w.])(\d{1,3})(?=[a-z]{2,})", line):
            if line[m.end() : m.end() + 2] in _UNIT_SUFFIXES:
                continue
            hits.append(
                f"digit fused with a word: {line[max(0, m.start() - 8) : m.start() + 26]!r}"
            )
    return sorted(set(hits))


def main(cfg: Config | None = None) -> int:
    """Render the report, failing on any of the six gates."""
    cfg = cfg or load_config()
    findings_path = cfg.path("findings")
    if not findings_path.is_file():
        msg = f"missing {findings_path}. Run the analysis stage first."
        raise FileNotFoundError(msg)
    findings = json.loads(findings_path.read_text(encoding="utf-8"))

    src = cfg.path("report_md")
    text = src.read_text(encoding="utf-8")
    total = len(_PLACEHOLDER.findall(text))
    rendered, missing = resolve(text, findings)

    if missing:
        msg = (
            f"{len(missing)} unresolved placeholder(s) in {src.name}:\n  "
            + "\n  ".join(missing)
            + f"\n\n{len(findings)} keys are available in {findings_path.name}."
        )
        raise UnresolvedPlaceholderError(msg)

    rendered = apply_typography(rendered)

    banned = check_banned(rendered)
    if banned:
        msg = f"{len(banned)} banned phrase(s) (CLAUDE.md §10):\n  " + "\n  ".join(banned)
        raise BannedPhraseError(msg)

    typo = check_typography(rendered)
    if typo:
        msg = f"{len(typo)} typographic violation(s):\n  " + "\n  ".join(typo)
        raise TypographyError(msg)

    # Run on the RESOLVED text, which is what the reader sees: a resolved
    # placeholder's value is by definition in findings.json and passes, so what
    # is left over is exactly the set of numbers somebody typed.
    stale = check_stale_numbers(rendered, findings)
    if stale:
        msg = (
            f"{len(stale)} number(s) in the prose that no finding supports:\n  "
            + "\n  ".join(stale)
        )
        raise StaleNumberError(msg)

    out = src.with_suffix(".rendered.md")
    out.write_text(rendered, encoding="utf-8")
    words = count_words(rendered)
    LOG.info(
        "resolved %d placeholders (%d distinct keys of %d available); "
        "no banned phrases, no typographic violations; %d words of prose",
        total,
        len(set(_PLACEHOLDER.findall(text))),
        len(findings),
        words,
    )

    chrome = check_print_chrome(cfg)
    if chrome:
        msg = (
            f"{len(chrome)} print variant(s) kept their chrome:\n  "
            + "\n  ".join(chrome)
            + "\n\nRebuild with `make figures`; print variants must carry axes, data "
            "and annotations only."
        )
        raise ChromeLeakError(msg)
    LOG.info("print-chrome check passed: no figure carries its caption's finding sentence")

    figure_numbers = check_figure_numbers(cfg, findings)
    if figure_numbers:
        msg = (
            f"{len(figure_numbers)} number(s) drawn into a figure that no finding "
            f"supports:\n  "
            + "\n  ".join(figure_numbers)
            + "\n\nA figure displays the pipeline's number. Read it from findings.json "
            "through viz.figures.finding(), or add the quantity to the export."
        )
        raise FigureNumberError(msg)
    LOG.info("figure-number check passed: no figure states a number findings.json lacks")

    width_drift = check_column_width(cfg)
    if width_drift:
        msg = "figure canvas and text column disagree:\n  " + "\n  ".join(width_drift)
        raise FigureAlignmentError(msg)

    slack = check_figure_alignment(cfg)
    if slack:
        msg = (
            f"{len(slack)} print variant(s) are not flush with their canvas "
            f"(tolerance 0.03in):\n  "
            + "\n  ".join(slack)
            + "\n\nEvery figure function must call flush_fit(fig) after its last "
            "artist is added. A figure that deliberately reserves a gutter should "
            "place the artists in that gutter as ink rather than switching the "
            "edge off, so flush_fit sizes the gutter to them."
        )
        raise FigureAlignmentError(msg)
    LOG.info(
        "figure-alignment check passed: all %d print variants flush to 0.03in",
        len(json.loads((cfg.path("figures") / "print" / "_slack.json").read_text())),
    )

    main_typ = build_typst(cfg, out)
    pdf = to_pdf(cfg, main_typ)
    if pdf is None:
        return 0

    defects = smoke_test_pdf(pdf, heading_lines(rendered))
    if defects:
        msg = (
            f"{len(defects)} layout defect(s) in the rendered PDF's extracted text:\n  "
            + "\n  ".join(defects[:20])
        )
        raise PdfSmokeTestError(msg)
    LOG.info("PDF smoke test passed: no page-number bleed in the extracted text")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
