"""Configuration loading, path resolution and determinism.

Every threshold, window, seed and path in this project lives in ``config/*.yaml``
(CLAUDE.md §12: no magic numbers in code). This module is the only place that
reads those files.
"""

from __future__ import annotations

import logging
import os
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

_CONFIG_FILES = {
    "pipeline": "config/pipeline.yaml",
    "lexicon": "config/green_lexicon.yaml",
    "blocs": "config/blocs.yaml",
    "audit_calls": "config/audit_calls.yaml",
}


class ConfigError(RuntimeError):
    """Raised when configuration is missing, malformed or internally inconsistent."""


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from ``start`` until a directory containing ``config/pipeline.yaml`` is found.

    Parameters
    ----------
    start
        Directory to begin the search from. Defaults to this file's location.

    Returns
    -------
    Path
        The repository root.
    """
    here = (start or Path(__file__).resolve().parent).resolve()
    for candidate in (here, *here.parents):
        if (candidate / _CONFIG_FILES["pipeline"]).is_file():
            return candidate
    msg = f"could not locate config/pipeline.yaml above {here}"
    raise ConfigError(msg)


@dataclass(frozen=True)
class Config:
    """Resolved project configuration.

    Attributes
    ----------
    root
        Repository root. All relative paths resolve against it.
    pipeline, lexicon, blocs
        Parsed contents of the three YAML config files.
    """

    root: Path
    pipeline: dict[str, Any] = field(repr=False)
    lexicon: dict[str, Any] = field(repr=False)
    blocs: dict[str, Any] = field(repr=False)
    audit_calls: dict[str, Any] = field(repr=False)

    # -- paths -------------------------------------------------------------
    def path(self, key: str) -> Path:
        """Resolve a key from ``pipeline.paths`` to an absolute path."""
        try:
            rel = self.pipeline["paths"][key]
        except KeyError as exc:
            msg = f"unknown path key {key!r}; known: {sorted(self.pipeline['paths'])}"
            raise ConfigError(msg) from exc
        return self.root / rel

    def ensure_dirs(self) -> None:
        """Create every directory the pipeline writes to."""
        for key in (
            "data_raw",
            "data_interim",
            "data_processed",
            "figures",
            "tables",
            "stamps",
        ):
            self.path(key).mkdir(parents=True, exist_ok=True)
        self.path("logs").parent.mkdir(parents=True, exist_ok=True)

    # -- scalars -----------------------------------------------------------
    @property
    def seed(self) -> int:
        """The single seed from which every stochastic step is derived."""
        return int(self.pipeline["seed"])

    def flag(self, name: str) -> bool:
        """Return a specification flag from ``pipeline.flags``.

        Flags are judgement calls that change a headline number. Each is run both
        ways in ``robustness.py``; this returns the headline setting.
        """
        try:
            return bool(self.pipeline["flags"][name])
        except KeyError as exc:
            msg = f"unknown flag {name!r}; known: {sorted(self.pipeline['flags'])}"
            raise ConfigError(msg) from exc

    def threshold(self, name: str) -> Any:
        """Return a value from ``pipeline.thresholds``."""
        try:
            return self.pipeline["thresholds"][name]
        except KeyError as exc:
            msg = f"unknown threshold {name!r}; known: {sorted(self.pipeline['thresholds'])}"
            raise ConfigError(msg) from exc

    def tripwire(self, name: str) -> Any:
        """Return a value from ``pipeline.tripwires``."""
        try:
            return self.pipeline["tripwires"][name]
        except KeyError as exc:
            msg = f"unknown tripwire {name!r}; known: {sorted(self.pipeline['tripwires'])}"
            raise ConfigError(msg) from exc

    def source(self, name: str) -> dict[str, Any]:
        """Return a source definition from ``pipeline.sources``."""
        try:
            return self.pipeline["sources"][name]
        except KeyError as exc:
            msg = f"unknown source {name!r}; known: {sorted(self.pipeline['sources'])}"
            raise ConfigError(msg) from exc

    @property
    def window(self) -> dict[str, Any]:
        """The analysis window block."""
        return self.pipeline["window"]


def load_config(root: Path | None = None) -> Config:
    """Load and validate the three config files.

    Raises
    ------
    ConfigError
        If a file is missing, unparseable, or fails a consistency check.
    """
    root = root or find_repo_root()
    parsed: dict[str, Any] = {}
    for key, rel in _CONFIG_FILES.items():
        target = root / rel
        if not target.is_file():
            msg = f"missing config file: {target}"
            raise ConfigError(msg)
        try:
            parsed[key] = yaml.safe_load(target.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            msg = f"{rel} is not valid YAML: {exc}"
            raise ConfigError(msg) from exc

    cfg = Config(root=root, **parsed)
    _validate(cfg)
    return cfg


def _validate(cfg: Config) -> None:
    """Check cross-file consistency that a typo would otherwise hide until step 7."""
    lex = cfg.lexicon
    declared = set(lex["subdomains"])
    priority = list(lex["subdomain_priority"])

    if len(priority) != len(set(priority)):
        msg = "subdomain_priority contains duplicates"
        raise ConfigError(msg)

    unknown = set(priority) - declared - {"general_unspecified"}
    if unknown:
        msg = f"subdomain_priority names undeclared sub-domains: {sorted(unknown)}"
        raise ConfigError(msg)

    unranked = declared - set(priority)
    if unranked:
        msg = f"sub-domains missing from subdomain_priority: {sorted(unranked)}"
        raise ConfigError(msg)

    # A veto_subdomain exclusion must name a sub-domain that exists.
    valid_targets = declared | {"general_unspecified"}
    for exc_def in lex["exclusions"]:
        if exc_def["scope"] == "veto_subdomain":
            target = exc_def.get("subdomain")
            if target not in valid_targets:
                msg = f"exclusion vetoes unknown sub-domain {target!r}: {exc_def['pattern']}"
                raise ConfigError(msg)
        elif exc_def["scope"] != "veto_all":
            msg = f"unknown exclusion scope {exc_def['scope']!r}"
            raise ConfigError(msg)
        if not str(exc_def.get("reason", "")).strip():
            msg = f"exclusion has no reason: {exc_def['pattern']}"
            raise ConfigError(msg)

    # Every gated pattern must name a flag that exists.
    for name, block in lex.get("gated_patterns", {}).items():
        flag_name = block.get("flag")
        if flag_name not in cfg.pipeline.get("flags", {}):
            msg = f"gated pattern {name!r} names unknown flag {flag_name!r}"
            raise ConfigError(msg)

    # Instrument normalisation must land only in declared families. Both the
    # primary map (funding_round_code) and the fallback (funding_round_type)
    # are checked, so a typo in either is caught here and not at step 7.
    rt = cfg.pipeline["round_types"]
    families = rt["instrument_family"]
    canonical = set(rt["normalise"].values()) | set(rt["normalise_fallback"].values())
    classified = {v for members in families.values() for v in members}
    orphans = canonical - classified
    if orphans:
        msg = f"canonical round types in no instrument family: {sorted(orphans)}"
        raise ConfigError(msg)

    # The H4 stage ladder must be canonical round types.
    ladder = set(rt["stage_ladder"])
    if not ladder <= canonical:
        msg = (
            f"stage_ladder entries are not canonical round types: {sorted(ladder - canonical)}"
        )
        raise ConfigError(msg)

    for spec in ("seed_entry_types_strict", "seed_entry_types_angel_inclusive"):
        entry = set(rt[spec])
        if not entry <= canonical:
            msg = f"{spec} entries are not canonical round types: {sorted(entry - canonical)}"
            raise ConfigError(msg)


def seed_everything(cfg: Config) -> np.random.Generator:
    """Seed every source of randomness and return the project's generator.

    CLAUDE.md §2.4: same input must give byte-identical output. Analysis code
    takes its randomness from the returned generator rather than from the
    global ``numpy.random`` state.
    """
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)  # noqa: NPY002 - legacy API seeded for third-party callers
    os.environ["PYTHONHASHSEED"] = str(cfg.seed)
    return np.random.default_rng(cfg.seed)


_LOGGING_READY = False


def get_logger(name: str, cfg: Config | None = None) -> logging.Logger:
    """Return a logger writing to both stderr and ``logs/build.log``.

    Configured once per process; later calls only fetch the named child logger.
    """
    global _LOGGING_READY  # noqa: PLW0603
    if not _LOGGING_READY:
        cfg = cfg or load_config()
        log_path = cfg.path("logs")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)-22s %(message)s", "%H:%M:%S"
        )

        root_logger = logging.getLogger("gcg")
        root_logger.setLevel(logging.INFO)
        root_logger.handlers.clear()

        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(fmt)
        root_logger.addHandler(stream)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(fmt)
        root_logger.addHandler(file_handler)

        root_logger.propagate = False
        _LOGGING_READY = True

    return logging.getLogger(f"gcg.{name}")
