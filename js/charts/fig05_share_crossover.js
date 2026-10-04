/* fig05_share_crossover.js — green's share of deals against its share of dollars.
 *
 * A dollar share above the count share means the average green cheque exceeded
 * the average cheque overall, which is CONSISTENT WITH green being
 * capital-intensive. It does not test the cross-sector elasticity; that is a
 * different claim and Figure 4 makes it.
 */

import { renderLines } from "./lines.js";

export function render(container, spec, findings, options) {
  const series = spec.series.map((s) => ({
    ...s,
    points: spec.marks.map((m) => ({ year: m.year, value: m[s.id], mark: m })),
  }));
  const byYear = new Map(spec.marks.map((m) => [m.year, m]));
  const thin = new Map(spec.thin_cells.map((t) => [t.year, t.green]));

  renderLines(
    container,
    {
      series,
      axis: spec.axis,
      label:
        "From 2005, green took a bigger share of venture dollars than of deals. " +
        spec.marks
          .map((m) => `${m.year}: ${m.count_share}% of deals, ${m.dollar_share}% of dollars`)
          .join("; "),
      annotations: spec.annotations,
      tooltip: (year) => {
        const m = byYear.get(year);
        const rows = [
          ["Share of green deals", `${m.count_share}%`, "muted"],
          ["Share of green dollars", `${m.dollar_share}%`, "green"],
        ];
        if (thin.has(year)) {
          rows.push(["Green deals that year", String(thin.get(year)), null]);
        }
        return rows;
      },
    },
    options
  );
}
