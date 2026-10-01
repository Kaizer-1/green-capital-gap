"""Resolve ``{{placeholders}}`` and render the report.

CLAUDE.md §2.2 makes this the enforcement point: every statistic in the report
is a placeholder resolved from ``outputs/findings.json``, and an unresolved
placeholder **fails the build**. A report that renders with a literal
``{{h1.rr}}`` in it is worse than one that does not render at all, because the
first can be submitted.

A second check runs on the rendered prose: the §10 banned-phrase list. Both are
failures, not warnings.
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

# CLAUDE.md §10. Matched case-insensitively on word boundaries.
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
# Paragraph-opening connectives, banned only in that position.
_BANNED_OPENERS = ("Moreover,", "Furthermore,", "Additionally,")


class UnresolvedPlaceholderError(RuntimeError):
    """The report contains a placeholder with no value in findings.json."""


class BannedPhraseError(RuntimeError):
    """The rendered prose contains a phrase banned by the writing standards."""


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


def to_pdf(cfg: Config, md_path: Path) -> Path | None:
    """Render markdown to PDF via pandoc with the typst engine.

    Returns ``None`` rather than raising when the toolchain is absent: a missing
    PDF engine should not fail a build whose numbers are already correct.
    """
    pdf = cfg.path("report_pdf")
    pandoc = shutil.which("pandoc")
    if not pandoc:
        LOG.warning("pandoc not found; skipping PDF. Install with: brew install pandoc typst")
        return None

    engine = "typst" if shutil.which("typst") else None
    cmd = [pandoc, str(md_path), "-o", str(pdf), "--citeproc", "--toc"]
    if engine:
        cmd += [f"--pdf-engine={engine}"]
    bib = cfg.root / "report" / "references.bib"
    if bib.is_file():
        cmd += ["--bibliography", str(bib)]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)  # noqa: S603
    if result.returncode != 0:
        LOG.error(
            "pandoc failed (exit %d): %s", result.returncode, result.stderr.strip()[:800]
        )
        return None
    LOG.info("wrote %s", pdf.name)
    return pdf


def main(cfg: Config | None = None) -> int:
    """Render the report, failing on unresolved placeholders or banned phrases."""
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
            + f"\n\n{len(findings)} keys are available in {findings_path.name}. "
            "Every number in the report must resolve from it; nothing is typed by hand."
        )
        raise UnresolvedPlaceholderError(msg)

    banned = check_banned(rendered)
    if banned:
        msg = (
            f"{len(banned)} banned phrase(s) in the rendered report (CLAUDE.md §10):\n  "
            + "\n  ".join(banned)
        )
        raise BannedPhraseError(msg)

    out = src.with_suffix(".rendered.md")
    out.write_text(rendered, encoding="utf-8")
    LOG.info(
        "resolved %d placeholders (%d distinct keys used of %d available); no banned phrases",
        total,
        len(set(_PLACEHOLDER.findall(text))),
        len(findings),
    )
    LOG.info("wrote %s", out.name)
    to_pdf(cfg, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
