"""Download, checksum, cache and tabular I/O.

CLAUDE.md §4: every download is cached to ``data/raw`` with its SHA256 recorded,
never re-downloaded on a re-run, and a checksum mismatch fails loudly.
CLAUDE.md §2.1: if a dataset cannot be fetched the build STOPS. Nothing is ever
substituted, simulated or generated.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from gcg.config import Config, get_logger

LOG = get_logger("io")

_CHECKSUM_FILE = "_checksums.json"
_HTTP_TIMEOUT = 120
_CHUNK = 1 << 20


class DataUnavailableError(RuntimeError):
    """A required dataset could not be fetched.

    Raising this stops the build. CLAUDE.md §15: a dataset that will not download
    is a question for the user, never an invitation to substitute something else.
    """


class ChecksumMismatchError(RuntimeError):
    """A cached file's SHA256 no longer matches the recorded value."""


@dataclass
class SourceRecord:
    """Provenance for one fetched file, written to ``data/MANIFEST.md``."""

    source: str
    filename: str
    origin: str
    licence: str
    sha256: str
    size_bytes: int
    fetched_at: str
    rows: int | None = None
    note: str = ""


def sha256_file(path: Path) -> str:
    """Return the hex SHA256 of a file, streamed so large files stay out of memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _checksum_store(cfg: Config) -> Path:
    return cfg.path("data_raw") / _CHECKSUM_FILE


def load_checksums(cfg: Config) -> dict[str, str]:
    """Read the recorded checksum ledger, or an empty dict on first run."""
    store = _checksum_store(cfg)
    if not store.is_file():
        return {}
    return json.loads(store.read_text(encoding="utf-8"))


def record_checksum(cfg: Config, filename: str, digest: str) -> None:
    """Add or update one entry in the checksum ledger."""
    store = _checksum_store(cfg)
    current = load_checksums(cfg)
    current[filename] = digest
    store.write_text(
        json.dumps(dict(sorted(current.items())), indent=2) + "\n", encoding="utf-8"
    )


def verify_or_record(cfg: Config, path: Path) -> str:
    """Verify a cached file against the ledger, recording it if new.

    Returns
    -------
    str
        The file's SHA256.

    Raises
    ------
    ChecksumMismatchError
        If the file's digest differs from the recorded one. Silent corruption or
        an upstream file swapped under a stable URL both land here, and both
        must stop the build rather than quietly change the results.
    """
    digest = sha256_file(path)
    recorded = load_checksums(cfg).get(path.name)
    if recorded is None:
        record_checksum(cfg, path.name, digest)
        LOG.info("checksum recorded  %-44s %s", path.name, digest[:16])
    elif recorded != digest:
        msg = (
            f"{path.name}: SHA256 mismatch.\n"
            f"  recorded: {recorded}\n"
            f"  on disk:  {digest}\n"
            "The cached file changed. Delete it to re-download, or investigate."
        )
        raise ChecksumMismatchError(msg)
    return digest


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def download_http(cfg: Config, url: str, filename: str, *, force: bool = False) -> Path:
    """Download ``url`` to ``data/raw/filename``, skipping the fetch if cached.

    Raises
    ------
    DataUnavailableError
        On any network or HTTP failure. The build stops here.
    """
    dest = cfg.path("data_raw") / filename
    if dest.is_file() and not force:
        LOG.info("cached             %-44s %s", filename, _human(dest.stat().st_size))
        verify_or_record(cfg, dest)
        return dest

    LOG.info("downloading        %-44s %s", filename, url[:70])
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with requests.get(url, stream=True, timeout=_HTTP_TIMEOUT) as response:
            response.raise_for_status()
            with tmp.open("wb") as handle:
                for chunk in response.iter_content(_CHUNK):
                    handle.write(chunk)
    except requests.RequestException as exc:
        tmp.unlink(missing_ok=True)
        msg = (
            f"could not download {filename} from {url}\n"
            f"  {type(exc).__name__}: {exc}\n"
            "Build stopped. No substitute data will be generated."
        )
        raise DataUnavailableError(msg) from exc

    tmp.replace(dest)
    verify_or_record(cfg, dest)
    LOG.info("downloaded         %-44s %s", filename, _human(dest.stat().st_size))
    return dest


def fetch_json(cfg: Config, url: str, filename: str) -> Any:
    """Download a JSON endpoint to the raw cache and return the parsed payload."""
    path = download_http(cfg, url, filename)
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Kaggle
# ---------------------------------------------------------------------------
def kaggle_available() -> tuple[bool, str]:
    """Report whether the Kaggle CLI is installed and credentialed.

    Returns
    -------
    tuple[bool, str]
        ``(ok, detail)``. ``detail`` explains the failure when ``ok`` is False.
    """
    # Look beside the running interpreter first: in a virtualenv the CLI lives in
    # the venv's bin/ and PATH is not necessarily set up for it.
    local = Path(sys.executable).parent / "kaggle"
    binary = str(local) if local.is_file() else shutil.which("kaggle")
    if binary is None:
        return False, "the `kaggle` CLI is not on PATH (pip install 'kaggle>=1.6')"

    home = Path.home() / ".kaggle"
    has_token = (home / "access_token").is_file() or (home / "kaggle.json").is_file()
    if not has_token:
        return False, f"no credentials found in {home} (expected access_token or kaggle.json)"
    return True, binary


def download_kaggle(
    cfg: Config, handle: str, expect_files: list[str] | None = None
) -> list[Path]:
    """Download and unzip a Kaggle dataset into ``data/raw``.

    Skips the fetch when every expected file is already cached.

    Raises
    ------
    DataUnavailableError
        If the CLI is missing, credentials are absent, the download fails, or an
        expected file is not present afterwards.
    """
    raw = cfg.path("data_raw")
    if expect_files and all((raw / name).is_file() for name in expect_files):
        LOG.info("cached             %-44s (kaggle: %s)", ", ".join(expect_files)[:44], handle)
        for name in expect_files:
            verify_or_record(cfg, raw / name)
        return [raw / name for name in expect_files]

    ok, detail = kaggle_available()
    if not ok:
        msg = (
            f"cannot fetch Kaggle dataset {handle}: {detail}\n"
            "Build stopped. No substitute data will be generated."
        )
        raise DataUnavailableError(msg)

    LOG.info("downloading        %-44s (kaggle)", handle)
    cmd = [detail, "datasets", "download", "-d", handle, "-p", str(raw), "--unzip", "--force"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, check=False)  # noqa: S603
    if result.returncode != 0:
        msg = (
            f"kaggle download failed for {handle} (exit {result.returncode})\n"
            f"  stdout: {result.stdout.strip()[:500]}\n"
            f"  stderr: {result.stderr.strip()[:500]}\n"
            "Build stopped. No substitute data will be generated."
        )
        raise DataUnavailableError(msg)

    # --unzip is unreliable across CLI versions; unpack any zip left behind.
    for archive in raw.glob("*.zip"):
        LOG.info("unzipping          %-44s", archive.name)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(raw)
        archive.unlink()

    if expect_files:
        missing = [name for name in expect_files if not (raw / name).is_file()]
        if missing:
            present = sorted(p.name for p in raw.iterdir() if p.is_file())
            msg = (
                f"kaggle dataset {handle} downloaded but expected files are "
                f"missing: {missing}\n"
                f"  present in data/raw: {present}\n"
                "Build stopped."
            )
            raise DataUnavailableError(msg)

    out = [raw / name for name in (expect_files or [])]
    for path in out:
        verify_or_record(cfg, path)
    return out


# ---------------------------------------------------------------------------
# Tabular
# ---------------------------------------------------------------------------
def read_csv_strict(path: Path, *, encoding: str = "utf-8", **kwargs: Any) -> pd.DataFrame:
    """Read a CSV, always stripping whitespace from column names.

    CLAUDE.md §7: ``investments_VC.csv`` ships with column names such as
    ``" market"`` and ``" funding_total_usd "``. Stripping on load, always, as the
    first step, removes a whole class of silent key errors downstream.
    """
    df = pd.read_csv(path, encoding=encoding, low_memory=False, **kwargs)
    renamed = {col: str(col).strip() for col in df.columns}
    changed = {k: v for k, v in renamed.items() if k != v}
    if changed:
        LOG.info("stripped %d whitespace-padded column names in %s", len(changed), path.name)
    return df.rename(columns=renamed)


def write_parquet(df: pd.DataFrame, path: Path, *, label: str = "") -> Path:
    """Write a dataframe to parquet, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False, compression="snappy")
    LOG.info(
        "wrote              %-44s %7d rows x %2d cols  %s",
        path.name,
        len(df),
        df.shape[1],
        _human(path.stat().st_size),
    )
    if label:
        LOG.info("                   %s", label)
    return path


def read_parquet(path: Path) -> pd.DataFrame:
    """Read a parquet file, with a clear error if the stage that writes it has not run."""
    if not path.is_file():
        msg = f"missing {path}. Run the pipeline stage that produces it first."
        raise FileNotFoundError(msg)
    return pd.read_parquet(path)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
def write_manifest(cfg: Config, records: list[SourceRecord]) -> Path:
    """Write ``data/MANIFEST.md``: every source with URL, licence, SHA256, date, rows."""
    path = cfg.path("manifest")
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Data manifest",
        "",
        "Generated by `make data` (`src/gcg/ingest/run.py`). Do not edit by hand.",
        "",
        "Every file below was downloaded by the pipeline and is cached in `data/raw/`",
        "(gitignored). Checksums are recorded in `data/raw/_checksums.json` and verified",
        "on every re-run; a mismatch fails the build.",
        "",
        f"Fetched: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "| Source | File | Rows | Size | Licence | SHA256 (first 16) |",
        "|---|---|---:|---:|---|---|",
    ]
    for rec in sorted(records, key=lambda r: (r.source, r.filename)):
        rows = f"{rec.rows:,}" if rec.rows is not None else "—"
        lines.append(
            f"| `{rec.source}` | `{rec.filename}` | {rows} | {_human(rec.size_bytes)} "
            f"| {rec.licence} | `{rec.sha256[:16]}` |"
        )

    lines += ["", "## Origins", ""]
    seen: set[str] = set()
    for rec in sorted(records, key=lambda r: r.source):
        if rec.source in seen:
            continue
        seen.add(rec.source)
        lines.append(f"- **`{rec.source}`** — {rec.origin}")
        if rec.note:
            lines.append(f"  - {rec.note.strip()}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    LOG.info("wrote              %-44s %d source files", path.name, len(records))

    json_path = path.with_suffix(".json")
    json_path.write_text(
        json.dumps([asdict(r) for r in records], indent=2) + "\n", encoding="utf-8"
    )
    return path


def _human(size: int) -> str:
    """Format a byte count for log output."""
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:,.0f}{unit}" if unit == "B" else f"{value:,.1f}{unit}"
        value /= 1024
    return f"{value:,.1f}GB"
