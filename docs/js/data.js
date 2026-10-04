/* data.js — load, validate, and resolve.
 *
 * Two files, both written by the Python pipeline:
 *   findings.json  every statistic the report states, by dotted key
 *   series.json    plot-ready arrays, one object per figure
 *
 * Nothing here computes a number. Resolution is a lookup and a failure if the
 * lookup misses: a page that silently renders an empty span where a statistic
 * should be is worse than one that refuses to render, because the first can be
 * published.
 */

const SCHEMA_VERSION = 1;

export class DataError extends Error {}

/** Fetch JSON, failing with the path rather than a bare "Unexpected token". */
async function getJSON(path) {
  let response;
  try {
    response = await fetch(path, { cache: "no-cache" });
  } catch (cause) {
    throw new DataError(`could not fetch ${path}: ${cause.message}`);
  }
  if (!response.ok) {
    throw new DataError(`${path} returned ${response.status} ${response.statusText}`);
  }
  try {
    return await response.json();
  } catch (cause) {
    throw new DataError(`${path} is not valid JSON: ${cause.message}`);
  }
}

export async function load() {
  const [findings, series] = await Promise.all([
    getJSON("data/findings.json"),
    getJSON("data/series.json"),
  ]);

  if (series.schema_version !== SCHEMA_VERSION) {
    throw new DataError(
      `series.json is schema_version ${series.schema_version}; this page expects ` +
        `${SCHEMA_VERSION}. Re-run \`make web-data\`.`
    );
  }
  return { findings, series };
}

/**
 * Verify every [data-key] in the DOM against findings.json.
 *
 * The numbers are injected at build time by gcg.web.inject, so this does not
 * write them — it checks them. The attribute is an assertion: this element
 * should contain the value findings.json holds for this key. A mismatch means
 * the page was published against a stale injection, which is exactly the class
 * of defect the report's placeholder gate exists to catch, so it is caught here
 * too rather than being left to a reader to notice.
 *
 * Returns a list of problems, each naming the key and both values.
 */
/**
 * Strip the cosmetic difference between a findings value and its typeset form.
 *
 * The injector applies the report's typography pass, so the page carries 1.92×
 * where findings.json stores 1.92x. The assertion is about the VALUE, not the
 * glyphs, so both sides are flattened before comparison. Re-implementing the
 * transform here would be a second copy of it, which is the divergence the
 * single injection path exists to prevent.
 */
function flatten(text) {
  return text
    .replace(/[×]/g, "x")
    .replace(/[−]/g, "-")
    .replace(/[’′]/g, "'")
    .replace(/\u2011/g, "-")
    .replace(/\s+/g, " ")
    .trim();
}

export function verifyKeys(root, findings) {
  const problems = [];
  for (const node of root.querySelectorAll("[data-key]")) {
    const key = node.dataset.key;
    if (!(key in findings)) {
      problems.push(`${key}: not in findings.json`);
      continue;
    }
    const prefix = node.dataset.prefix ?? "";
    const suffix = node.dataset.suffix ?? "";
    const expected = `${prefix}${findings[key]}${suffix}`;
    const actual = node.textContent;
    if (flatten(actual) !== flatten(expected)) {
      problems.push(`${key}: page shows "${actual}", findings.json says "${expected}"`);
    }
  }
  return problems;
}

/** One figure's series object, or a thrown error naming the key. */
export function figure(series, key) {
  const value = series[key];
  if (value === undefined) {
    throw new DataError(`series.json has no key "${key}". Re-run \`make web-data\`.`);
  }
  return value;
}
