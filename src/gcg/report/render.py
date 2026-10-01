"""Resolve placeholders, enforce the writing standards, and render the PDF.

Three gates, all failures rather than warnings:

1. **Unresolved placeholders** (CLAUDE.md §2.2). Every statistic is a
   ``{{key}}`` resolved from ``outputs/findings.json``. A report that renders
   with a literal ``{{h1.rr}}`` is worse than one that does not render, because
   the first can be submitted.
2. **Banned phrases** (CLAUDE.md §10).
3. **Typography.** Primes used as apostrophes, ASCII ``x`` used as a
   multiplication sign, and hyphen-minus used as a minus sign are all defects a
   reader sees before they read a sentence.

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


def resolve(text: str, findings: dict[str, str]) -> tuple[str, list[str]]:
    """Substitute every placeholder, returning the text and any unresolved keys."""
    missing: list[str] = []

    def sub(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in findings:
            missing.append(key)
            return match.group(0)
        return str(findings[key])

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

    meta = cfg.pipeline["report"]
    words = count_words(body_md.read_text(encoding="utf-8"))
    main = cfg.root / "report" / ".report.typ"
    main.write_text(
        "\n".join(
            [
                '#import "template.typ": conf, exhibit, method-exhibit',
                "#show: conf.with(",
                f'  title: "{meta["title"]}",',
                f'  subtitle: "{meta["subtitle"]}",',
                f'  author: "{meta["author"]}",',
                f'  usn: "{meta["usn"]}",',
                f'  course: "{meta["course"]}",',
                f'  date: "{meta["date"]}",',
                f'  wordcount: "{words:,}",',
                ")",
                "",
                body_typ.read_text(encoding="utf-8"),
            ]
        ),
        encoding="utf-8",
    )
    return main


def count_words(markdown: str) -> int:
    """Count prose words, excluding figure blocks, tables and headings."""
    text = re.sub(r"```\{=typst\}.*?```", " ", markdown, flags=re.S)
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
        LOG.error(
            "typst failed (exit %d): %s", result.returncode, result.stderr.strip()[:1500]
        )
        return None
    LOG.info("wrote %s", pdf.name)
    return pdf


def smoke_test_pdf(pdf: Path) -> list[str]:
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
        if re.match(r"^\d+\d+\.\s+[A-Z]", line):
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
    """Render the report, failing on any of the four gates."""
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

    main_typ = build_typst(cfg, out)
    pdf = to_pdf(cfg, main_typ)
    if pdf is None:
        return 0

    defects = smoke_test_pdf(pdf)
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
