/* fig11_power_wall.js — every emerging-market test cell against the minimum.
 *
 * The one figure that earns a special touch. The threshold line is drawn before
 * the bars start, and the bars grow toward it and visibly stop short. The whole
 * argument is "nothing reaches the line", and watching five bars fail to reach
 * it says that better than the caption does.
 */

import { renderBars } from "./bars.js";

export function render(container, spec, findings, options) {
  renderBars(
    container,
    {
      axis: spec.axis,
      threshold: spec.threshold,
      rowHeight: 62,
      label:
        "Every emerging-market test fails on the same wall, for different reasons. " +
        spec.marks
          .map((m) => `${m.label}: ${m.value}, blocking the ${m.blocks}`)
          .join("; ") +
        `. The minimum cell size is ${spec.threshold.value}.`,
      marks: spec.marks.map((m) => ({
        label: m.label,
        sublabel: `blocks the ${m.blocks}`,
        value: m.value,
        display: String(m.value),
        colour_role: m.colour_role,
        raw: m,
      })),
      tooltip: (m) => [
        ["Observations available", String(m.raw.value), null],
        ["Minimum required", String(spec.threshold.value), "alert"],
        ["Test it blocks", m.raw.blocks, null],
        ["Hypothesis", m.raw.hypothesis, null],
      ],
    },
    options
  );
}
