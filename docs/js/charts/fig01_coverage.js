/* fig01_coverage.js — emerging-market share of world GDP against its share of
 * the recorded venture record.
 *
 * The denominator check: it establishes that the conditional green-rate gap in
 * Figure 2 is not this coverage gap restated.
 */

import { renderLines } from "./lines.js";

export function render(container, spec, findings, options) {
  const series = spec.series.map((s) => ({
    ...s,
    points: spec.marks.map((m) => ({ year: m.year, value: m[s.id], mark: m })),
  }));

  const byYear = new Map(spec.marks.map((m) => [m.year, m]));

  renderLines(
    container,
    {
      series,
      axis: spec.axis,
      label:
        "Emerging markets hold a fifth of world GDP and a fiftieth of the venture " +
        "record. " +
        spec.marks
          .map((m) => `${m.year}: ${m.gdp_share}% of GDP, ${m.deal_share}% of deals`)
          .join("; "),
      tooltip: (year) => {
        const m = byYear.get(year);
        return [
          ["Share of world GDP", `${m.gdp_share}%`, "muted"],
          ["Share of recorded deals", `${m.deal_share}%`, "em"],
          ["Gap", `${m.gap_pp} pp`, null],
        ];
      },
    },
    options
  );
}
