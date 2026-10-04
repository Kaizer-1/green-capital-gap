"""Static checks on the built ``docs/`` tree, before it is published.

Two classes of defect break on GitHub Pages and never locally, so neither the
browser checks nor a local server will find them:

**Case.** Pages serves from a case-sensitive filesystem; macOS does not. A
``src="js/Theme.js"`` against a file named ``theme.js`` resolves locally and
404s once deployed. ``Path.exists()`` cannot see this on macOS — it answers the
same for either spelling — so every reference is compared against the actual
directory entry, character for character.

**Root-relative paths.** A local server is rooted at the site, so ``/css/x.css``
works. Pages roots the site at ``/<repo>/``, where the same path resolves to
``user.github.io/css/x.css`` and is not there. Anything leaving the deploy root,
by a leading slash or by ``../``, is refused.

Run as ``python -m gcg.web.deploy_check docs``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# src= / href= on a tag, a bare ES-module specifier, and a fetch() argument.
_REF = re.compile(
    r"""(?:\b(?:src|href)=["']([^"'#?]+)["'])"""
    r"""|(?:\bfrom\s+["']([^"']+)["'])"""
    r"""|(?:\bfetch\(\s*["']([^"'#?]+)["'])"""
    r"""|(?:\burl\(\s*["']?([^"')]+)["']?\s*\))""",
    re.X,
)

_SCANNED = {".html", ".js", ".mjs", ".css"}


class DeployError(RuntimeError):
    """The built tree would not serve correctly from a project sub-path."""


def _entries(directory: Path) -> set[str]:
    """The names in a directory exactly as the filesystem spells them."""
    try:
        return {e.name for e in directory.iterdir()}
    except OSError:
        return set()


def _resolve_exactly(root: Path, base: Path, ref: str) -> str | None:
    """Why ``ref`` would fail when served case-sensitively, or None if it is fine."""
    target = (base / ref).resolve()
    try:
        rel = target.relative_to(root.resolve())
    except ValueError:
        return f"escapes the deploy root ({ref})"

    # Walk down, comparing each component against the real directory entry.
    here = root.resolve()
    for part in rel.parts:
        names = _entries(here)
        if part not in names:
            near = [n for n in names if n.lower() == part.lower()]
            if near:
                return f"case mismatch: references {part!r}, on disk as {near[0]!r}"
            return f"missing: {ref}"
        here = here / part
    return None


def check(root: Path) -> list[str]:
    """Every reason the tree would not serve from ``user.github.io/<repo>/``."""
    problems: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in _SCANNED or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _REF.finditer(text):
            ref = next((g for g in match.groups() if g), None)
            if not ref:
                continue
            ref = ref.strip()
            if not ref or ref.startswith(("http://", "https://", "//", "data:", "#", "mailto:")):
                continue
            where = path.relative_to(root)
            if ref.startswith("/"):
                problems.append(
                    f"{where}: root-relative path {ref!r}. Pages serves this site "
                    f"from /<repo>/, where a leading slash resolves outside it."
                )
                continue
            why = _resolve_exactly(root, path.parent, ref)
            if why:
                problems.append(f"{where}: {why}")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    root = Path(args[0] if args else "docs")
    if not root.is_dir():
        raise DeployError(f"{root} is not a directory; run `make web-deploy` first")

    problems = check(root)
    if problems:
        joined = "\n  - ".join(sorted(set(problems)))
        raise DeployError(
            f"{len(set(problems))} reference(s) would not serve from a project "
            f"sub-path:\n  - {joined}"
        )

    if not (root / ".nojekyll").exists():
        raise DeployError(f"{root}/.nojekyll is missing; Jekyll would drop _-prefixed paths")
    if not (root / "report.pdf").exists():
        raise DeployError(f"{root}/report.pdf is missing; the masthead links to it")

    files = sum(1 for p in root.rglob("*") if p.is_file())
    print(f"deploy_check: {files} files, every reference relative and correctly cased")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
