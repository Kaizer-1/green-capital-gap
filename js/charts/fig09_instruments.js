/* fig09_instruments.js — non-dilutive share of deals, green against non-green.
 *
 * Supported for the advanced-economy benchmark case. The emerging-market arm
 * rests on three non-dilutive deals and is a pre-registered null, not an
 * estimate; the bar is dimmed and labelled rather than omitted, because the
 * cell size IS the finding.
 */

import { renderBars } from "./bars.js";

export function render(container, spec, findings, options) {
  renderBars(
    container,
    {
      axis: spec.axis,
      label:
        "Green ventures lean harder on grants and debt than non-green ones do. " +
        spec.marks.map((m) => `${m.label}: ${m.pct}% of ${m.n} deals`).join("; "),
      marks: spec.marks.map((m) => ({
        label: m.label,
        sublabel: `n = ${m.n.toLocaleString()}${
          m.below_min_cell ? ` · ${m.non_dilutive} non-dilutive, below the minimum` : ""
        }`,
        value: m.pct,
        display: `${m.pct}%`,
        colour_role: m.colour_role,
        dim: m.below_min_cell,
        raw: m,
      })),
      tooltip: (m) => [
        ["Non-dilutive share", `${m.raw.pct}%`, m.colour_role],
        ["Grant rounds", m.raw.grant.toLocaleString(), null],
        ["Debt rounds", m.raw.debt.toLocaleString(), null],
        ["Deals in the cell", m.raw.n.toLocaleString(), null],
      ],
    },
    options
  );
}
