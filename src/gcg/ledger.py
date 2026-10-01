"""The attrition ledger: every row dropped, and why.

CLAUDE.md §11: each stage logs rows in, rows out, rows dropped and why, and the
drop ledger becomes a table in the methodology appendix. A transparent attrition
table is one of the clearest quality signals a marker can see, and it is also the
only way a reader can tell whether a headline number rests on the data or on a
sequence of quiet deletions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from gcg.config import get_logger

LOG = get_logger("ledger")


@dataclass
class Step:
    """One recorded transition in the pipeline."""

    stage: str
    action: str
    reason: str
    rows_in: int
    rows_out: int

    @property
    def dropped(self) -> int:
        """Rows removed by this step. Negative if the step added rows."""
        return self.rows_in - self.rows_out


@dataclass
class Ledger:
    """An ordered record of row counts through the pipeline."""

    steps: list[Step] = field(default_factory=list)

    def record(
        self, stage: str, action: str, reason: str, rows_in: int, rows_out: int
    ) -> None:
        """Append a step and log it."""
        step = Step(stage, action, reason, int(rows_in), int(rows_out))
        self.steps.append(step)
        LOG.info(
            "ledger  %-14s %-34s %7d -> %7d  (%+d)",
            stage,
            action,
            step.rows_in,
            step.rows_out,
            -step.dropped,
        )

    def apply(
        self,
        df: pd.DataFrame,
        mask: pd.Series,
        *,
        stage: str,
        action: str,
        reason: str,
    ) -> pd.DataFrame:
        """Keep rows where ``mask`` is True, recording the drop.

        Using this instead of a bare boolean filter is what makes the ledger
        complete by construction: a filter applied without it will not appear in
        the appendix table and is therefore a bug.
        """
        before = len(df)
        out = df.loc[mask.fillna(False)].copy()
        self.record(stage, action, reason, before, len(out))
        return out

    def to_frame(self) -> pd.DataFrame:
        """Render the ledger as the appendix table."""
        rows = [
            {
                "step": i + 1,
                "stage": s.stage,
                "action": s.action,
                "reason": s.reason,
                "rows_in": s.rows_in,
                "rows_out": s.rows_out,
                "rows_dropped": s.dropped,
                "pct_of_step_input": round(100 * s.dropped / s.rows_in, 3)
                if s.rows_in
                else 0.0,
            }
            for i, s in enumerate(self.steps)
        ]
        frame = pd.DataFrame(rows)
        if not frame.empty:
            origin = frame["rows_in"].iloc[0]
            frame["pct_of_original"] = (100 * frame["rows_dropped"] / origin).round(3)
        return frame

    def summary(self) -> dict[str, int | float]:
        """Totals for the report's data section."""
        if not self.steps:
            return {}
        start, end = self.steps[0].rows_in, self.steps[-1].rows_out
        return {
            "rows_at_start": start,
            "rows_at_end": end,
            "net_dropped": start - end,
            "retention_pct": round(100 * end / start, 3) if start else 0.0,
            "steps": len(self.steps),
        }
