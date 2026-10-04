/* checks.mjs — automated assertions against the rendered page.
 *
 * WEB.md §10.1. Every check here fails the build.
 *
 * The division of labour is deliberate. Anything that can be decided from the
 * SOURCE is checked in Python, by `gcg.web.inject`, reusing the report's own
 * gates: unresolved keys, typography, and the bare-number rule. Re-implementing
 * those here would be a second copy of each rule, which is the divergence the
 * single injection path exists to prevent.
 *
 * What is left for this file is everything that only exists once a browser has
 * run: the rendered DOM, the console, layout, and the no-JS and reduced-motion
 * states.
 *
 * Six sections, in the order a defect is cheapest to find: data integrity,
 * rendering, behaviour, accessibility, performance, and the degraded states.
 */

import { chromium } from "playwright";
import { createRequire } from "node:module";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { scrollThrough, serve, VIEWPORTS } from "./capture.mjs";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
// Resolved rather than path-joined: node_modules sits beside this directory in
// a checkout and above it in CI, and a hard-coded path works in one of them.
const AXE_PATH = createRequire(import.meta.url).resolve("axe-core/axe.min.js");

/** Every chart module, with the series.json key it requires. */
const FIGURE_KEYS = {
  fig01: "fig01_coverage",
  fig02: "fig02_double_gap",
  fig03: "fig03_rate_by_year",
  fig05: "fig05_share_crossover",
  fig04: "fig04_ladder",
  fig06: "fig06_subdomain",
  fig07: "fig07_cycle",
  fig08: "fig08_crisis",
  fig09: "fig09_instruments",
  fig10: "fig10_depth_need",
  fig11: "fig11_power_wall",
  fig12: "fig12_continuity",
  figM1: "figM1_censoring",
};

const SCHEMA_VERSION = 1;

const failures = [];
const passes = [];

function check(name, ok, detail = "") {
  if (ok) {
    passes.push(name);
  } else {
    failures.push(detail ? `${name}\n      ${detail}` : name);
  }
}

// ---------------------------------------------------------------------------
// Data integrity

async function dataIntegrity(page, findings, series) {
  check(
    "series.json schema_version matches the page",
    series.schema_version === SCHEMA_VERSION,
    `series.json says ${series.schema_version}, checks.mjs expects ${SCHEMA_VERSION}`,
  );

  // Every data-key resolves, and every injected value still equals the finding.
  // The injector asserts this at build time; this asserts it against what the
  // browser actually rendered, which is the thing a reader sees.
  const slots = await page.evaluate(() =>
    [...document.querySelectorAll("[data-key]")].map((n) => ({
      key: n.dataset.key,
      prefix: n.dataset.prefix ?? "",
      suffix: n.dataset.suffix ?? "",
      text: n.textContent,
    })),
  );
  check("the page carries at least one injected statistic", slots.length > 0);

  const flatten = (t) =>
    t
      .replace(/×/g, "x")
      .replace(/−/g, "-")
      .replace(/[’′]/g, "'")
      .replace(/‑/g, "-")
      .replace(/\s+/g, " ")
      .trim();

  const unresolved = slots
    .filter((s) => !(s.key in findings))
    .map((s) => s.key);
  check(
    "every data-key resolves against findings.json",
    unresolved.length === 0,
    unresolved.join(", "),
  );

  const stale = slots
    .filter((s) => s.key in findings)
    .filter(
      (s) =>
        flatten(s.text) !== flatten(`${s.prefix}${findings[s.key]}${s.suffix}`),
    )
    .map(
      (s) =>
        `${s.key}: page "${s.text.trim()}" vs findings "${findings[s.key]}"`,
    );
  check(
    "every injected statistic equals its finding",
    stale.length === 0,
    stale.join("\n      "),
  );

  // Every chart module's series key exists.
  const missingSeries = Object.entries(FIGURE_KEYS)
    .filter(([, key]) => series[key] === undefined)
    .map(([id, key]) => `${id} needs series.json key "${key}"`);
  check(
    "every chart module's series key exists",
    missingSeries.length === 0,
    missingSeries.join(", "),
  );

  // Every figure container in the DOM is one this file knows about, so a figure
  // cannot be added to the page without being added to the checks.
  const inDom = await page.evaluate(() =>
    [...document.querySelectorAll("[data-figure]")].map(
      (n) => n.dataset.figure,
    ),
  );
  const unchecked = inDom.filter((id) => !(id in FIGURE_KEYS));
  check(
    "every figure in the DOM is covered by this file",
    unchecked.length === 0,
    unchecked.join(", "),
  );

  // Each figure's data table is present in the HTML, not built by script: it is
  // the screen-reader path and the no-JS fallback, and it cannot be both if a
  // script has to run first.
  const tables = await page.evaluate(() =>
    [...document.querySelectorAll(".figure__table")].map((n) => ({
      key: n.dataset.table,
      rows: n.querySelectorAll("tbody tr").length,
      cols: n.querySelectorAll("thead th").length,
    })),
  );
  check(
    "every figure has a data table with rows and columns",
    tables.length === inDom.length &&
      tables.every((t) => t.rows > 0 && t.cols > 0),
    JSON.stringify(tables),
  );

  // The table's rows must agree with the series it describes. A spec carries
  // either `marks` (one row per mark) or `series[].points` (one row per year).
  for (const t of tables) {
    const spec = series[t.key];
    if (!spec) continue;
    // A spec carries one of three shapes: `marks` (one row per mark),
    // `series[].points` keyed by year or by month (one row per distinct x), or
    // `panels[].marks` (one row per mark across all panels).
    const expected = spec.marks
      ? spec.marks.length
      : spec.panels
        ? spec.panels.reduce((n, p) => n + p.marks.length, 0)
        : new Set(
            (spec.series ?? []).flatMap((s) =>
              s.points.map((p) => p.year ?? p.month),
            ),
          ).size;
    check(
      `${t.key} data table has one row per observation`,
      t.rows === expected,
      `table has ${t.rows} rows, series has ${expected} marks`,
    );
  }
}

// ---------------------------------------------------------------------------
// Rendering — the subset that data integrity depends on. The rest at step 9.

async function rendering(browser, base) {
  for (const vp of VIEWPORTS) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
    });
    const page = await context.newPage();
    const noise = [];
    page.on("console", (m) => {
      if (m.type() === "error" || m.type() === "warning")
        noise.push(`${m.type()}: ${m.text()}`);
    });
    page.on("pageerror", (e) => noise.push(`pageerror: ${e.message}`));

    await page.goto(base, { waitUntil: "networkidle" });
    const ready = await page.getAttribute("html", "data-ready");

    // Figures build on reveal, so the page has to be scrolled before any of
    // them can be asserted to exist. One helper, shared with the capture, so
    // the two cannot disagree about what "scrolled through" means.
    const reached = await scrollThrough(page);
    check(
      `${vp.name}: the scroll reached the bottom of the page`,
      reached >= 0.99,
      `covered ${(reached * 100).toFixed(0)}% of the document`,
    );

    check(
      `${vp.name}: page reaches data-ready`,
      ready === "true",
      `data-ready="${ready}"`,
    );
    check(
      `${vp.name}: no console errors or warnings`,
      noise.length === 0,
      noise.join("\n      "),
    );

    const layout = await page.evaluate(() => {
      const d = document.documentElement;
      const stacked = document.querySelector('.scrolly[data-layout="stacked"]');
      const empty = [...document.querySelectorAll("[data-figure]")]
        .filter((n) => !(stacked && n.dataset.figure === "fig04"))
        .filter((n) => {
          const svg = n.querySelector("svg");
          if (!svg) return true;
          const r = svg.getBoundingClientRect();
          return r.width * r.height === 0;
        })
        .map((n) => n.dataset.figure);
      return { scrollWidth: d.scrollWidth, clientWidth: d.clientWidth, empty };
    });
    check(
      `${vp.name}: no horizontal overflow`,
      layout.scrollWidth <= layout.clientWidth,
      `scrollWidth ${layout.scrollWidth} > clientWidth ${layout.clientWidth}`,
    );
    check(
      `${vp.name}: every figure has a non-zero bounding box`,
      layout.empty.length === 0,
      layout.empty.join(", "),
    );

    await context.close();
  }
}

// ---------------------------------------------------------------------------
// Behaviour. Two of these encode decisions that are easy to undo by accident.

async function behaviour(browser, base) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();
  await page.goto(base, { waitUntil: "networkidle" });
  await scrollThrough(page);

  // --- Figure 7: the toggle must MORPH, not rebuild ----------------------
  // Dollars peaking a year before deals is visible in the transition and
  // invisible in two static panels. A fade-out/fade-in destroys the
  // correspondence between a bar and itself, so the same elements have to
  // persist across a toggle and animate their geometry.
  const barsOf = () =>
    page.evaluate(() =>
      [...document.querySelectorAll('[data-figure="fig07"] svg rect')]
        .filter((r) => r.getAttribute("fill") !== "transparent")
        .map((r) => ({ x: r.getAttribute("x"), h: r.getAttribute("height") })),
    );

  await page.locator('[data-figure="fig07"]').scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  const before = await barsOf();
  // Scoped to fig07s own toggle: the pinned sequence has one too.
  await page.locator('[data-figure="fig07"] .toggle button').nth(1).click();
  await page.waitForTimeout(60);
  const transitions = await page.evaluate(() =>
    [...document.querySelectorAll('[data-figure="fig07"] svg rect')]
      .filter((r) => r.getAttribute("fill") !== "transparent")
      .map((r) => r.style.transition)
      .filter(Boolean),
  );
  await page.waitForTimeout(700);
  const after = await barsOf();

  check(
    "fig07 toggle changes the rendered output",
    before.length > 0 && JSON.stringify(before) !== JSON.stringify(after),
  );
  check(
    "fig07 toggle morphs in place rather than rebuilding",
    before.length === after.length &&
      JSON.stringify(before.map((b) => b.x)) ===
        JSON.stringify(after.map((b) => b.x)),
    `${before.length} bars before, ${after.length} after`,
  );
  check(
    "fig07 bars animate their geometry during the morph",
    transitions.some((t) => /height/.test(t) && /\d+ms/.test(t)),
    transitions.slice(0, 1).join(""),
  );

  // --- Figure 10 panel (b): deliberately inert ---------------------------
  // The point of that panel is that there is nothing to explore. A hover
  // readout added "for consistency" with panel (a) would quietly contradict
  // its own caption, so the absence of one is asserted rather than assumed.
  const surfaces = await page.evaluate(() => {
    const svg = document.querySelector('[data-figure="fig10"] svg');
    const width = svg.viewBox.baseVal.width;
    const hit = [...svg.querySelectorAll('[fill="transparent"]')];
    return {
      panelA: hit.filter((n) => Number(n.getAttribute("cx")) < width * 0.62)
        .length,
      panelB: hit.filter((n) => Number(n.getAttribute("cx")) >= width * 0.62)
        .length,
    };
  });
  check(
    "fig10 panel (a) is interrogable",
    surfaces.panelA > 0,
    JSON.stringify(surfaces),
  );
  check(
    "fig10 panel (b) is inert, as its caption says",
    surfaces.panelB === 0,
    `${surfaces.panelB} interactive surface(s) in a panel that claims to have nothing to explore`,
  );

  // --- section scaffolding ----------------------------------------------
  // Numbering comes from a CSS counter on document order, so a section added
  // without its number span silently skips a number for every section after it.
  const sections = await page.evaluate(() =>
    [...document.querySelectorAll(".section")].map((el) => ({
      id: el.id,
      number: !!el.querySelector(".section__number"),
      labelled: el.getAttribute("aria-labelledby"),
      heading: el.querySelector(".section__title")?.id ?? null,
    })),
  );
  check(
    "every section carries a number span",
    sections.every((s) => s.number),
    sections
      .filter((s) => !s.number)
      .map((s) => s.id)
      .join(", "),
  );
  check(
    "every section is labelled by its own heading",
    sections.every((s) => s.labelled && s.labelled === s.heading),
    sections
      .filter((s) => s.labelled !== s.heading)
      .map((s) => s.id)
      .join(", "),
  );

  // --- the pinned sequence ----------------------------------------------
  const seqSteps = await page.locator(".scrolly__step").all();
  check(
    "the sequence has four steps",
    seqSteps.length === 4,
    `${seqSteps.length} steps`,
  );

  await seqSteps[seqSteps.length - 1].scrollIntoViewIfNeeded();
  await page.waitForTimeout(2600);
  const emphasis = await page.evaluate(() => {
    const svg = document.querySelector("[data-figure='fig04'] svg");
    if (!svg) return null;
    const dots = [...svg.querySelectorAll("circle")].filter(
      (c) =>
        c.getAttribute("fill") &&
        !["transparent", "none"].includes(c.getAttribute("fill")),
    );
    const opacities = dots.map((d) => Number(getComputedStyle(d).opacity));
    const labels = [...svg.querySelectorAll("text")]
      .filter((t) => Number(getComputedStyle(t.parentElement).opacity) > 0.5)
      .map((t) => t.textContent);
    return {
      faded: opacities.filter((o) => o < 0.45).length,
      full: opacities.filter((o) => o > 0.95).length,
      labels: labels.join(" | "),
    };
  });
  // Step 4 is the payload: everything else at 30%, cleantech alone at full
  // strength, its label and interval present.
  check(
    "step 4 fades everything but the focus",
    emphasis && emphasis.faded > 10,
    JSON.stringify(emphasis),
  );
  check(
    "step 4 keeps the focus at full strength",
    emphasis && emphasis.full >= 1,
    JSON.stringify(emphasis),
  );
  check(
    "step 4 shows the focus label and its interval",
    emphasis &&
      /cleantech/.test(emphasis.labels) &&
      /above its prediction/.test(emphasis.labels),
    emphasis?.labels,
  );

  await context.close();

  // The sequence must NOT pin at phone widths: a sticky graphic there fails by
  // sticking or jumping, which is worse than never pinning.
  const narrow = await browser.newContext({
    viewport: { width: 390, height: 844 },
  });
  const narrowPage = await narrow.newPage();
  await narrowPage.goto(base, { waitUntil: "networkidle" });
  await scrollThrough(narrowPage);
  const mobile = await narrowPage.evaluate(() => {
    const section = document.querySelector(".scrolly");
    const graphic = section?.querySelector(".scrolly__graphic");
    return {
      layout: section?.dataset.layout,
      sticky: graphic ? getComputedStyle(graphic).position : null,
      graphicVisible: graphic
        ? graphic.getBoundingClientRect().height > 0
        : false,
      stackedStates: document.querySelectorAll(".scrolly__step-graphic svg")
        .length,
      captions: document.querySelectorAll(".scrolly__step p").length,
      // data-active carries a different meaning per layout, so the invariant
      // that matters is the RENDERED one: stacked, no step may be singled out.
      // Checking the attribute instead would pass for the defect that prompted
      // this, because all four stacked steps are legitimately "true".
      distinctStepStyles: new Set(
        [...document.querySelectorAll(".scrolly__step")].map((el) => {
          const c = getComputedStyle(el);
          return [c.color, c.borderLeftColor, c.opacity].join("|");
        })
      ).size,
    };
  });
  check(
    "the sequence does not pin at 390",
    mobile.layout === "stacked",
    JSON.stringify(mobile),
  );
  check("the pinned graphic is not rendered at 390", !mobile.graphicVisible);
  check(
    "stacked: no step is singled out as active",
    mobile.distinctStepStyles === 1,
    `${mobile.distinctStepStyles} distinct step styles; stacked steps are all current`,
  );
  check(
    "390 gets four static states",
    mobile.stackedStates === 4,
    `${mobile.stackedStates} states`,
  );
  check(
    "390 keeps all four captions",
    mobile.captions === 4,
    `${mobile.captions} captions`,
  );
  await narrow.close();

  // Reduced motion gets the same stack, so the whole argument survives without
  // a single transition.
  const rmCtx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    reducedMotion: "reduce",
  });
  const rmPage2 = await rmCtx.newPage();
  await rmPage2.goto(base, { waitUntil: "networkidle" });
  await scrollThrough(rmPage2);
  const rmSeq = await rmPage2.evaluate(() => {
    const states = [...document.querySelectorAll(".scrolly__step-graphic svg")];
    const last = states[states.length - 1];
    const dots = last
      ? [...last.querySelectorAll("circle")].filter(
          (c) =>
            c.getAttribute("fill") &&
            !["transparent", "none"].includes(c.getAttribute("fill")),
        )
      : [];
    const op = dots.map((d) => Number(d.getAttribute("opacity")));
    return {
      layout: document.querySelector(".scrolly")?.dataset.layout,
      states: states.length,
      captions: document.querySelectorAll(".scrolly__step p").length,
      lastFaded: op.filter((o) => o < 0.45).length,
      lastFull: op.filter((o) => o > 0.95).length,
    };
  });
  check(
    "reduced motion gets the stacked sequence",
    rmSeq.layout === "stacked",
    JSON.stringify(rmSeq),
  );
  check(
    "reduced motion renders all four states",
    rmSeq.states === 4,
    `${rmSeq.states}`,
  );
  check(
    "reduced motion keeps all four captions",
    rmSeq.captions === 4,
    `${rmSeq.captions}`,
  );
  check(
    "reduced motion's final state is already emphasised",
    rmSeq.lastFaded > 10 && rmSeq.lastFull >= 1,
    JSON.stringify(rmSeq),
  );
  await rmCtx.close();
}

// ---------------------------------------------------------------------------
// Accessibility
//
// WEB.md §10.1 sets two contrast bars rather than one: >=7:1 for body copy
// (AAA) and >=4.5:1 for secondary text (AA). The split is deliberate — the
// apparatus is allowed to recede — but it only means anything if "body" and
// "secondary" are declared rather than inferred from how something looks. So
// BODY lists the selectors whose text a reader reads sentence by sentence;
// everything else with a text node is secondary. Two defects were found this
// way: the scrollytelling step captions were dimmed by opacity to 1.49:1, and
// the colophon's running prose had drifted into the muted tone.

/** Selectors whose text is body copy, held to 7:1. */
const BODY = [
  ".masthead__title",
  ".masthead__standfirst",
  ".section h2",
  ".section h3",
  ".section > p",
  ".scrolly__step p",
  ".colophon p",
  ".stat__value",
  ".verdicts__claim",
  ".defect__body",
];

/* The list above is a hand-made judgement, and a hand-made list is how body
 * copy drifts into the apparatus tone unnoticed: the colophon's 283-character
 * paragraphs were styled as metadata and nobody had put them on any list. So
 * length decides as well. A <p> or <li> carrying PROSE_CHARS or more of text is
 * read sentence by sentence whatever its class says, and is held to the body
 * bar. Roles that are legitimately long AND legitimately secondary are named
 * here, so each exemption is a visible decision rather than an omission. */
const PROSE_CHARS = 120;
const PROSE_EXEMPT = [
  ".figure__caption", // the finding sentence inside is <b> at --ink; the rest supports it
  ".figure__source", // provenance, deliberately recessive
  ".verdicts__falsifier", // the "what would falsify this" line, subordinate to the claim
  "figcaption",
  "caption",
];

/** Text that is decorative or duplicated, and is exempt by construction. */
const CONTRAST_EXEMPT = [
  ".section__number", // a CSS counter, aria-hidden, repeated in the heading
  ".was", // the pre-injection value, hidden from view and from AT
  ".tick-label", // measured separately below, against the plot background
];

async function accessibility(browser, base) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();
  await page.goto(base, { waitUntil: "networkidle" });
  await scrollThrough(page);

  // --- contrast, every rendered text node -------------------------------
  // Hoisted so the sweep can run at every viewport. A defect that was fixed
  // and then silently came back — a leaked replay reinstated opacity 0.35 on
  // the step captions after step 9 had removed it — needs a check, not a
  // memory, and it has to read COMPUTED style on rendered output rather than
  // the stylesheet, because the stylesheet looked correct the whole time.
  const contrastAt = (pg) =>
    pg.evaluate(
    ({ body, exempt, proseChars, proseExempt }) => {
      const lum = (css) => {
        const m = (css.match(/[\d.]+/g) || []).map(Number);
        if (m.length < 3) return null;
        const [r, g, b] = m.slice(0, 3).map((v) => {
          v /= 255;
          return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      };
      // Cumulative opacity: an ancestor at 0.35 dims its text just as surely
      // as a lighter colour does, and reading the element's own opacity misses
      // it. This is the check that caught the 1.49:1 step captions.
      const effectiveAlpha = (el) => {
        let a = 1;
        for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
          a *= parseFloat(getComputedStyle(e).opacity) || 0;
        }
        return a;
      };
      // The painted background: the nearest ancestor that declares one.
      const backdrop = (el) => {
        for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
          const bg = getComputedStyle(e).backgroundColor;
          const m = (bg.match(/[\d.]+/g) || []).map(Number);
          if (m.length >= 3 && (m.length < 4 || m[3] > 0.95)) return lum(bg);
        }
        return 1; // the page background is --canvas, white
      };
      const ratio = (fg, bgL, alpha) => {
        const L = fg * alpha + bgL * (1 - alpha);
        const [hi, lo] = L > bgL ? [L, bgL] : [bgL, L];
        return (hi + 0.05) / (lo + 0.05);
      };

      const isExempt = (el) => exempt.some((sel) => el.closest(sel));
      const hasOwnText = (el) =>
        [...el.childNodes].some(
          (n) => n.nodeType === 3 && n.textContent.trim().length > 1,
        );

      const bodyNodes = new Set();
      for (const sel of body) {
        for (const el of document.querySelectorAll(sel)) bodyNodes.add(el);
      }
      for (const el of document.querySelectorAll("p, li")) {
        if (el.textContent.trim().length < proseChars) continue;
        if (proseExempt.some((sel) => el.closest(sel))) continue;
        bodyNodes.add(el);
      }

      const rows = [];
      for (const el of document.querySelectorAll("body *")) {
        if (!hasOwnText(el) || isExempt(el)) continue;
        const style = getComputedStyle(el);
        if (style.visibility === "hidden" || style.display === "none") continue;
        const box = el.getBoundingClientRect();
        if (box.width < 1 || box.height < 1) continue;
        const fg = lum(style.color);
        if (fg === null) continue;
        const alpha = effectiveAlpha(el);
        if (alpha < 0.05) continue; // not painted at all
        // Body copy is identified by its own selector, or by having a body
        // ancestor and no role of its own: a <b> inside a paragraph is body.
        const isBody =
          bodyNodes.has(el) ||
          [...bodyNodes].some((b) => b !== el && b.contains(el));
        rows.push({
          selector:
            el.tagName.toLowerCase() +
            (typeof el.className === "string" && el.className
              ? "." + el.className.trim().split(/\s+/).join(".")
              : ""),
          tier: isBody ? "body" : "secondary",
          required: isBody ? 7 : 4.5,
          ratio: +ratio(fg, backdrop(el), alpha).toFixed(2),
          chars: el.textContent.trim().length,
        });
      }
      return rows;
    },
    {
      body: BODY,
      exempt: CONTRAST_EXEMPT,
      proseChars: PROSE_CHARS,
      proseExempt: PROSE_EXEMPT,
    },
    );

  const contrast = await contrastAt(page);

  const short = contrast.filter((r) => r.ratio < r.required);
  check(
    "every text node meets its tier's contrast bar",
    short.length === 0,
    short
      .slice(0, 8)
      .map(
        (r) => `${r.selector} — ${r.ratio}:1, ${r.tier} needs ${r.required}:1`,
      )
      .join("\n      "),
  );
  check(
    "both contrast tiers are actually populated",
    contrast.some((r) => r.tier === "body") &&
      contrast.some((r) => r.tier === "secondary"),
    `body ${contrast.filter((r) => r.tier === "body").length}, ` +
      `secondary ${contrast.filter((r) => r.tier === "secondary").length}`,
  );

  // The same sweep at every viewport. The stylesheet changes with width — the
  // compact layouts raise type sizes and the sequence switches layout entirely —
  // so a floor met at 1440 is not a floor met at 390.
  for (const vp of VIEWPORTS) {
    if (vp.width === 1440) continue; // already swept above
    const ctx = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
    });
    const pg = await ctx.newPage();
    await pg.goto(base, { waitUntil: "networkidle" });
    await scrollThrough(pg);
    const rows = await contrastAt(pg);
    const bad = rows.filter((r) => r.ratio < r.required);
    check(
      `${vp.name}: every text node meets its tier's contrast bar`,
      rows.length > 0 && bad.length === 0,
      bad
        .slice(0, 6)
        .map((r) => `${r.selector} — ${r.ratio}:1, ${r.tier} needs ${r.required}:1`)
        .join("\n      "),
    );
    await ctx.close();
  }

  // Text drawn inside the figures. CLAUDE.md §8 requires direct labelling at
  // the series terminus rather than a legend, which makes the palette's hues
  // text — and three of them fail 4.5:1 as text. theme.js resolves label text
  // through a darkened variant for exactly this reason; this asserts it.
  // Measured one figure at a time, each scrolled into view first:
  // elementsFromPoint only sees what is inside the viewport, and measuring a
  // figure below the fold reported every in-bar label as 1:1 against a
  // backdrop that was never found.
  const svgText = [];
  for (const key of Object.keys(FIGURE_KEYS)) {
    const host = page.locator(`[data-figure="${key}"]`).first();
    if (!(await host.count())) continue;
    await host.scrollIntoViewIfNeeded();
    await page.waitForTimeout(120);
    svgText.push(
      ...(await page.evaluate((key) => {
        const lum = (css) => {
          const m = (css.match(/[\d.]+/g) || []).map(Number);
          if (m.length < 3) return null;
          const [r, g, b] = m.slice(0, 3).map((v) => {
            v /= 255;
            return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
          });
          return 0.2126 * r + 0.7152 * g + 0.0722 * b;
        };
        // A label inside a stacked bar sits on the bar, not on the page. Assuming
        // white reported white-on-teal as 1:1 — a failure that was not one — and
        // would equally have reported white-on-pale-grey as 1:1 when that IS one.
        // So the backdrop is hit-tested: whatever shape is painted under the
        // label's own centre.
        const SHAPES = new Set([
          "rect",
          "circle",
          "ellipse",
          "path",
          "polygon",
        ]);
        const backdropUnder = (t) => {
          const box = t.getBoundingClientRect();
          if (!box.width || !box.height) return null;
          const prior = t.style.pointerEvents;
          t.style.pointerEvents = "none";
          const stack = document.elementsFromPoint(
            box.left + box.width / 2,
            box.top + box.height / 2,
          );
          t.style.pointerEvents = prior;
          for (const el of stack) {
            if (el === t) continue;
            // Painted SHAPES only. The <svg> root is in this stack too, and
            // its computed fill is the inherited default black, which measured
            // every tick label against a background that is not there —
            // #6e6e68 on black is 4.09:1, which is exactly what it reported.
            if (!SHAPES.has(el.tagName.toLowerCase())) continue;
            if (!el.hasAttribute("fill") && !el.style.fill) continue;
            // And a gridline crossing the glyphs is not a background either: a
            // backdrop has to be large enough to sit behind the text.
            const area = el.getBoundingClientRect();
            if (area.height < box.height * 0.9 || area.width < box.width * 0.9)
              continue;
            const cs = getComputedStyle(el);
            const fill = cs.fill;
            if (!fill || fill === "none" || fill === "rgba(0, 0, 0, 0)")
              continue;
            const a =
              (parseFloat(cs.fillOpacity) || 0) * (parseFloat(cs.opacity) || 1);
            const L = lum(fill);
            if (L === null || !(a > 0)) continue;
            return L * a + 1 * (1 - a); // composited over the white canvas
          }
          return 1;
        };
        const rows = [];
        for (const t of document.querySelectorAll(
          `[data-figure="${key}"] svg text`,
        )) {
          if (!t.textContent.trim()) continue;
          const style = getComputedStyle(t);
          const alpha = parseFloat(style.opacity) || 1;
          if (alpha < 0.05) continue;
          const fg = lum(style.fill);
          if (fg === null) continue;
          const bg = backdropUnder(t);
          if (bg === null) continue;
          const L = fg * alpha + bg * (1 - alpha);
          const [hi, lo] = L > bg ? [L, bg] : [bg, L];
          rows.push({
            figure: key,
            cls: t.getAttribute("class") || "(none)",
            text: t.textContent.trim().slice(0, 30),
            ratio: +((hi + 0.05) / (lo + 0.05)).toFixed(2),
          });
        }
        return rows;
      }, key)),
    );
  }
  const faint = svgText.filter((r) => r.ratio < 4.5);
  check(
    `every one of ${svgText.length} labels drawn inside a figure clears 4.5:1`,
    svgText.length > 0 && faint.length === 0,
    `${faint.length} below the bar:\n      ` +
      faint
        .slice(0, 12)
        .map((r) => `${r.figure} ${r.cls} "${r.text}" — ${r.ratio}:1`)
        .join("\n      "),
  );

  // Thin data marks, held to WCAG 1.4.11's 3:1 for non-text. Scoped to marks
  // the reader has to TRACE — a 1.8px line, a 3px dot, an interval whisker —
  // because a low-contrast hairline is genuinely hard to follow. Large filled
  // areas are exempt: a bar is read by its extent against a labelled axis, not
  // by its edge against the page, and darkening every bar would pull the whole
  // palette away from report.pdf for no gain. The exemption is a stated
  // position, not an omission.
  const THIN_PX = 6;
  const SERIES_TOKENS = [
    "--em",
    "--ae",
    "--china",
    "--ldc",
    "--green",
    "--nongreen",
    "--cleantech",
    "--alert",
    "--nongreen-stroke",
  ];
  const marks = await page.evaluate(
    ({ thin, tokens }) => {
      const rgb = (css) =>
        (css.match(/[\d.]+/g) || []).slice(0, 3).map(Number).join(",");
      const lum = (css) => {
        const m = (css.match(/[\d.]+/g) || []).map(Number);
        if (m.length < 3) return null;
        const [r, g, b] = m.slice(0, 3).map((v) => {
          v /= 255;
          return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      };
      // Which paints count as DATA. Furniture — gridlines, leader lines, the
      // bracket, the reference datum — is drawn in --rule and --ink-muted and
      // is meant to be faint; WCAG exempts it, and sweeping it in reported 33
      // failures that were all deliberate. A mark painted in a series colour
      // is carrying a value, and that is what this gate is for.
      const root = getComputedStyle(document.documentElement);
      const probe = document.createElement("span");
      document.body.appendChild(probe);
      const series = new Set();
      for (const t of tokens) {
        probe.style.color = root.getPropertyValue(t).trim();
        series.add(rgb(getComputedStyle(probe).color));
      }
      probe.remove();

      const rows = [];
      for (const fig of document.querySelectorAll("[data-figure]")) {
        for (const el of fig.querySelectorAll(
          "svg path, svg line, svg circle, svg rect",
        )) {
          const cs = getComputedStyle(el);
          const box = el.getBoundingClientRect();
          const tag = el.tagName.toLowerCase();
          const stroked = cs.stroke && cs.stroke !== "none";
          const isHairline = stroked && (box.width < thin || box.height < thin);
          const isMarker = tag === "circle" && box.width <= 12;
          if (!isHairline && !isMarker) continue;
          // A hollow marker is read by its ring, so the stroke is the paint
          // that matters even though the fill is opaque white.
          const fillIsPaint =
            isMarker && cs.fill !== "none" && series.has(rgb(cs.fill));
          const paint = fillIsPaint ? cs.fill : cs.stroke;
          if (!paint || paint === "none" || !series.has(rgb(paint))) continue;
          const a =
            (parseFloat(fillIsPaint ? cs.fillOpacity : cs.strokeOpacity) || 1) *
            (parseFloat(cs.opacity) || 1);
          // Not painted at all — a mark a step has not reached yet. It has no
          // contrast to fail.
          if (a < 0.05) continue;
          // Faint by declaration, not by inference. A chart that needs alpha to
          // show density, or a step that recedes to make one mark stand out,
          // says so with a class; anything else is held to the bar. Tuning an
          // opacity threshold here instead would have been the same mistake as
          // the exemption rule in §8.
          if (el.classList.contains("mark-soft")) continue;
          const L = lum(paint);
          if (L === null) continue;
          const C = L * a + 1 * (1 - a);
          rows.push({
            figure: fig.dataset.figure,
            tag,
            paint,
            alpha: +a.toFixed(2),
            cls: el.getAttribute("class") || "-",
            ratio: +(1.05 / (C + 0.05)).toFixed(2),
          });
        }
      }
      return rows;
    },
    { thin: THIN_PX, tokens: SERIES_TOKENS },
  );
  const dim = marks.filter((m) => m.ratio < 3);
  check(
    `every one of ${marks.length} thin data marks clears 3:1`,
    marks.length > 0 && dim.length === 0,
    `${dim.length} below the bar: ` +
      [
        ...new Set(
          dim.map(
            (m) =>
              `${m.figure} ${m.tag}.${m.cls} ${m.paint} @${m.alpha} ${m.ratio}:1`,
          ),
        ),
      ]
        .slice(0, 10)
        .join(", "),
  );

  // --- axe-core ---------------------------------------------------------
  await page.addScriptTag({ path: AXE_PATH });
  const axe = await page.evaluate(async () =>
    window.axe.run(document, {
      resultTypes: ["violations"],
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
      },
    }),
  );
  const serious = axe.violations.filter((v) =>
    ["serious", "critical"].includes(v.impact),
  );
  check(
    "axe-core reports no serious or critical violations",
    serious.length === 0,
    serious
      .map(
        (v) =>
          `${v.id} (${v.impact}) ×${v.nodes.length}: ${v.nodes[0]?.target?.join(" ")}`,
      )
      .join("\n      "),
  );
  const minor = axe.violations.filter(
    (v) => !["serious", "critical"].includes(v.impact),
  );
  if (minor.length) {
    console.log(
      `  note: axe also reports ${minor.length} moderate/minor — ` +
        minor.map((v) => `${v.id} (${v.impact})`).join(", "),
    );
  }

  // --- tab order and the focus ring -------------------------------------
  // Every control must be reachable by Tab, in document order, and must show
  // a focus indicator that differs measurably from its resting state.
  const controls = await page.evaluate(
    () =>
      [
        ...document.querySelectorAll(
          'body button, body a[href], body [tabindex]:not([tabindex="-1"])',
        ),
      ].map((el, i) => {
        el.dataset.tabProbe = String(i);
        return i;
      }).length,
  );

  const reached = new Set();
  const ringless = [];
  for (let i = 0; i < controls + 6; i += 1) {
    await page.keyboard.press("Tab");
    const at = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      const s = getComputedStyle(el);
      return {
        probe: el.dataset.tabProbe ?? null,
        label: el.tagName.toLowerCase() + "." + (el.className || ""),
        // A ring is an outline, or a box-shadow, or a border change. Any of
        // the three counts; none of the three is a keyboard trap you cannot
        // see your way out of.
        ring:
          (s.outlineStyle !== "none" && parseFloat(s.outlineWidth) > 0) ||
          (s.boxShadow !== "none" && s.boxShadow !== "") ||
          s.backgroundColor !== "rgba(0, 0, 0, 0)",
      };
    });
    if (!at) continue;
    if (at.probe !== null) reached.add(at.probe);
    if (!at.ring) ringless.push(at.label);
  }
  check(
    "Tab reaches every interactive control",
    controls > 0 && reached.size === controls,
    `${reached.size} of ${controls} reached`,
  );
  check(
    "every focused control shows a visible focus indicator",
    ringless.length === 0,
    [...new Set(ringless)].join(", "),
  );

  // --- tooltips: hover, tap, Escape -------------------------------------
  const tipTarget = '[data-figure="fig07"] svg rect[fill="transparent"]';
  await page.locator(tipTarget).first().scrollIntoViewIfNeeded();
  const tipState = async () =>
    page.evaluate(() => {
      const t = document.querySelector(".tooltip");
      return t
        ? {
            shown: !t.hidden,
            text: t.textContent.trim().length,
          }
        : null;
    });

  await page.locator(tipTarget).first().hover();
  const onHover = await tipState();
  check(
    "a tooltip appears on hover and carries text",
    !!onHover?.shown && onHover.text > 0,
    JSON.stringify(onHover),
  );

  await page.keyboard.press("Escape");
  check("Escape dismisses the tooltip", (await tipState())?.shown === false);

  await context.close();

  // Touch is a separate context: a tooltip that only opens on pointermove
  // never opens on a phone, and hover emulation would hide that.
  const touch = await browser.newContext({
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    isMobile: true,
  });
  const touchPage = await touch.newPage();
  await touchPage.goto(base, { waitUntil: "networkidle" });
  await scrollThrough(touchPage);
  const tapTarget = touchPage
    .locator('[data-figure="fig07"] svg rect[fill="transparent"]')
    .first();
  await tapTarget.scrollIntoViewIfNeeded();
  await tapTarget.dispatchEvent("pointerdown", { clientX: 100, clientY: 300 });
  const onTap = await touchPage.evaluate(() => {
    const t = document.querySelector(".tooltip");
    return t ? { shown: !t.hidden, text: t.textContent.trim().length } : null;
  });
  check(
    "a tooltip appears on tap",
    !!onTap?.shown && onTap.text > 0,
    JSON.stringify(onTap),
  );
  await touch.close();
}

// ---------------------------------------------------------------------------
// Stylesheet integrity
//
// A leaked replay once appended a second copy of the pinned-sequence block to
// layout.css. The later copy won, silently reinstating a value an earlier fix
// had removed, and nothing failed. Same selector twice is legitimate — this
// stylesheet deliberately sets .wrap's grid in one place and its counters in
// another — so what is checked is narrower and exact: the same PROPERTY set
// twice for the same selector in two different blocks, where one quietly
// overrides the other.

async function stylesheets() {
  const files = ["css/tokens.css", "css/layout.css"];
  const clashes = [];
  const repeats = [];
  for (const f of files) {
    const css = await readFile(join(ROOT, f), "utf8");
    const flat = css.replace(/\/\*[\s\S]*?\*\//g, "");

    // Drop at-rule bodies before looking for clashes. Re-declaring a property
    // inside @media is the entire point of a media query, so only declarations
    // at the top level can quietly override one another.
    let top = "";
    for (let i = 0; i < flat.length; i += 1) {
      if (flat.startsWith("@", i)) {
        const open = flat.indexOf("{", i);
        if (open === -1) break;
        let depth = 0;
        let j = open;
        for (; j < flat.length; j += 1) {
          if (flat[j] === "{") depth += 1;
          else if (flat[j] === "}" && --depth === 0) break;
        }
        i = j;
        continue;
      }
      top += flat[i];
    }

    const seen = new Map();
    let block = 0;
    for (const m of top.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      const sel = m[1].trim().replace(/\s+/g, " ");
      if (!sel) continue;
      block += 1;
      const props = seen.get(sel) ?? new Map();
      for (const decl of m[2].split(";")) {
        const name = decl.split(":")[0]?.trim();
        if (!name || name.startsWith("--")) continue;
        props.set(name, (props.get(name) ?? 0) + 1);
      }
      seen.set(sel, props);
    }
    for (const [sel, props] of seen) {
      for (const [name, n] of props) {
        if (n > 1) clashes.push(`${f}: ${sel} sets ${name} ${n} times`);
      }
    }

    // And an exact repeat of a whole rule anywhere, at-rules included. This is
    // what the leak produced: a verbatim second copy of a block, several
    // hundred lines later, that silently won.
    const bodies = new Map();
    for (const m of flat.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      const sel = m[1].trim().replace(/\s+/g, " ");
      const body = m[2].replace(/\s+/g, " ").trim();
      if (!sel || !body) continue;
      const k = `${sel}{${body}}`;
      bodies.set(k, (bodies.get(k) ?? 0) + 1);
    }
    for (const [k, n] of bodies) {
      if (n > 1) repeats.push(`${f}: ${k.slice(0, 70)}… appears ${n} times`);
    }
  }
  check(
    "no stylesheet property is set twice for one selector outside a media query",
    clashes.length === 0,
    clashes.slice(0, 8).join("\n      "),
  );
  check(
    "no stylesheet rule is a verbatim repeat of another",
    repeats.length === 0,
    repeats.slice(0, 8).join("\n      "),
  );
}

// ---------------------------------------------------------------------------
// Performance
//
// WEB.md §10.1: under 1.5MB, LCP under 2.5s on a throttled connection, CLS
// under 0.05.
//
// The byte count is taken from the network, not from `du` on the directory.
// Charter and Inter load from Google Fonts, so those bytes land on the reader
// and a directory listing cannot see them — the local tree is 284KB and the
// stylesheet plus four woff2 faces are not in it. Every request the browser
// makes is counted, first-party and third-party, headers included, which is
// what the reader actually waits for.

/** Chrome DevTools' "Fast 3G", in the units CDP wants. */
const FAST_3G = {
  offline: false,
  latency: 562.5,
  downloadThroughput: (1.6 * 1024 * 1024) / 8,
  uploadThroughput: (750 * 1024) / 8,
};

const BUDGET_BYTES = 1.5 * 1024 * 1024;
const BUDGET_LCP_MS = 2500;
const BUDGET_CLS = 0.05;

async function performance_(browser, base) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();

  // Every byte, by origin, so the third-party share is visible rather than
  // assumed. `sizes()` reports what crossed the wire, including headers.
  const requests = [];
  page.on("requestfinished", async (request) => {
    try {
      const s = await request.sizes();
      requests.push({
        url: request.url(),
        type: request.resourceType(),
        bytes: (s.responseBodySize ?? 0) + (s.responseHeadersSize ?? 0),
        thirdParty: !request.url().includes("127.0.0.1"),
      });
    } catch {
      /* a request that never finished contributes nothing */
    }
  });
  page.on("requestfailed", (request) => {
    requests.push({
      url: request.url(),
      type: request.resourceType(),
      bytes: 0,
      failed: true,
      thirdParty: !request.url().includes("127.0.0.1"),
    });
  });

  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.emulateNetworkConditions", FAST_3G);

  // Register the observers before navigation so no entry is missed; the
  // buffered flag covers anything emitted before the script runs.
  await page.addInitScript(() => {
    window.__lcp = 0;
    window.__cls = 0;
    window.__lcpEl = null;
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        if (e.startTime < window.__lcp) continue;
        window.__lcp = e.startTime;
        // Captured in the callback, not read back afterwards: the entry's
        // `element` reference is not retained once the callback returns,
        // and querying it later reported the LCP element as null.
        window.__lcpEl = e.element
          ? e.element.tagName.toLowerCase() +
            (e.element.className ? "." + e.element.className : "")
          : e.url || "(no element)";
      }
    }).observe({ type: "largest-contentful-paint", buffered: true });
    new PerformanceObserver((list) => {
      for (const e of list.getEntries())
        if (!e.hadRecentInput) window.__cls += e.value;
    }).observe({ type: "layout-shift", buffered: true });
  });

  await page.goto(base, { waitUntil: "load" });
  // Let the fonts arrive and any late shift land. On Fast 3G the font swap is
  // the most likely source of a shift, and measuring before it would report a
  // CLS the reader does not get.
  await page
    .waitForFunction(() => document.fonts.status === "loaded", null, {
      timeout: 60000,
    })
    .catch(() => {});
  await page.waitForTimeout(3000);

  const vitals = await page.evaluate(() => ({
    lcp: Math.round(window.__lcp),
    cls: +window.__cls.toFixed(4),
    element: window.__lcpEl,
    fonts: [...document.fonts].map(
      (f) => `${f.family} ${f.weight} ${f.status}`,
    ),
  }));

  await cdp.send("Network.emulateNetworkConditions", {
    offline: false,
    latency: 0,
    downloadThroughput: -1,
    uploadThroughput: -1,
  });

  const total = requests.reduce((a, r) => a + r.bytes, 0);
  const third = requests
    .filter((r) => r.thirdParty)
    .reduce((a, r) => a + r.bytes, 0);
  const fontBytes = requests
    .filter((r) => r.type === "font" || r.url.includes("fonts.g"))
    .reduce((a, r) => a + r.bytes, 0);
  const kb = (b) => `${(b / 1024).toFixed(0)}KB`;

  // The font request must actually have happened. If it were blocked the page
  // would still render in the fallback and the budget would pass while
  // measuring something the reader never receives.
  const fontRequests = requests.filter((r) => r.url.includes("fonts.g"));
  check(
    "the webfont requests were made and counted",
    fontRequests.length > 0 && fontRequests.every((r) => !r.failed),
    `${fontRequests.length} request(s): ${fontRequests.map((r) => `${r.type} ${kb(r.bytes)}${r.failed ? " FAILED" : ""}`).join(", ")}`,
  );
  check(
    `total transferred under ${kb(BUDGET_BYTES)}`,
    total < BUDGET_BYTES,
    `${kb(total)} over ${requests.length} requests — ${kb(total - third)} first-party, ` +
      `${kb(third)} third-party, of which ${kb(fontBytes)} fonts`,
  );
  check(
    `LCP under ${BUDGET_LCP_MS}ms on Fast 3G with the fonts included`,
    vitals.lcp > 0 && vitals.lcp < BUDGET_LCP_MS,
    `${vitals.lcp}ms on ${vitals.element}`,
  );
  check(`CLS under ${BUDGET_CLS}`, vitals.cls < BUDGET_CLS, String(vitals.cls));

  console.log(
    `  weight ${kb(total)} (${kb(fontBytes)} fonts) · LCP ${vitals.lcp}ms on Fast 3G · ` +
      `CLS ${vitals.cls} · LCP element ${vitals.element}`,
  );

  await context.close();
}

// ---------------------------------------------------------------------------

async function main() {
  const findings = JSON.parse(
    await readFile(join(ROOT, "data", "findings.json"), "utf8"),
  );
  const series = JSON.parse(
    await readFile(join(ROOT, "data", "series.json"), "utf8"),
  );

  const { server, port } = await serve();
  const browser = await chromium.launch();
  const base = `http://127.0.0.1:${port}/index.html`;

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const page = await context.newPage();
  await page.goto(base, { waitUntil: "networkidle" });
  await scrollThrough(page);
  await dataIntegrity(page, findings, series);
  await context.close();

  await rendering(browser, base);
  await behaviour(browser, base);
  await accessibility(browser, base);
  await stylesheets();
  await performance_(browser, base);

  // Motion. A chart that re-animates every time it re-enters the viewport is
  // the single most irritating pattern on the web, so scrolling past a figure
  // and back must not retrigger it.
  const motion = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });
  const motionPage = await motion.newPage();
  await motionPage.goto(base, { waitUntil: "networkidle" });
  await scrollThrough(motionPage);
  const firstPass = await motionPage.evaluate(() =>
    [...document.querySelectorAll("[data-figure] path[stroke]")].map(
      (p) => p.style.strokeDashoffset,
    ),
  );
  await scrollThrough(motionPage);
  const secondPass = await motionPage.evaluate(() =>
    [...document.querySelectorAll("[data-figure] path[stroke]")].map(
      (p) => p.style.strokeDashoffset,
    ),
  );
  check(
    "entrance animations do not replay on scroll-back",
    firstPass.length > 0 &&
      JSON.stringify(firstPass) === JSON.stringify(secondPass),
    `before ${JSON.stringify(firstPass)} after ${JSON.stringify(secondPass)}`,
  );
  await motion.close();

  // Reduced motion: zero duration, final state, immediately.
  const reduced = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    reducedMotion: "reduce",
  });
  const reducedPage = await reduced.newPage();
  await reducedPage.goto(base, { waitUntil: "networkidle" });
  await scrollThrough(reducedPage);
  const animated = await reducedPage.evaluate(() =>
    [...document.querySelectorAll("*")]
      .filter((el) => {
        const s = getComputedStyle(el);
        return [s.transitionDuration, s.animationDuration]
          .join(" ")
          .split(/[,\s]+/)
          .some((d) => d && d !== "0s" && d !== "0ms");
      })
      .map((el) => `${el.tagName}.${el.className}`)
      .slice(0, 6),
  );
  // Under reduced motion the sequence uses its stacked layout, where fig04's
  // pinned host is empty by design and four per-step graphics stand in for it.
  const drawn = await reducedPage.evaluate(() => {
    const stacked = document.querySelector('.scrolly[data-layout="stacked"]');
    const pinned = document.querySelectorAll("[data-figure] svg").length;
    const perStep = document.querySelectorAll(
      ".scrolly__step-graphic svg",
    ).length;
    return stacked ? pinned + (perStep > 0 ? 1 : 0) : pinned;
  });
  check(
    "reduced motion: nothing animates",
    animated.length === 0,
    animated.join(", "),
  );
  check(
    "reduced motion: every figure still renders",
    drawn === Object.keys(FIGURE_KEYS).length,
    `${drawn} of ${Object.keys(FIGURE_KEYS).length} rendered`,
  );
  await reduced.close();

  // With scripts off the page must still carry its statistics, its byline and
  // its tables, and must not leave an empty box where a chart would be.
  const nojs = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    javaScriptEnabled: false,
  });
  const nojsPage = await nojs.newPage();
  await nojsPage.goto(base, { waitUntil: "load" });
  const degraded = await nojsPage.evaluate(() => ({
    stats: [...document.querySelectorAll("[data-key]")].filter((n) =>
      n.textContent.trim(),
    ).length,
    byline: document.querySelectorAll(".byline__authors dt").length,
    tableRows: document.querySelectorAll(".figure__table tbody tr").length,
    frameHeight:
      document.querySelector(".figure__frame")?.getBoundingClientRect()
        .height ?? -1,
    noscript: !!document.querySelector("noscript"),
  }));
  check(
    "no-JS: statistics are present",
    degraded.stats > 0,
    JSON.stringify(degraded),
  );
  check("no-JS: the byline is present", degraded.byline > 0);
  check("no-JS: data tables are visible", degraded.tableRows > 0);
  check(
    "no-JS: the empty chart box is collapsed",
    degraded.frameHeight === 0,
    `height ${degraded.frameHeight}`,
  );
  check("no-JS: a noscript block explains what is missing", degraded.noscript);
  await nojs.close();

  await browser.close();
  server.close();

  console.log(`\n${passes.length} check(s) passed`);
  if (failures.length) {
    console.error(`\n${failures.length} check(s) FAILED:`);
    for (const f of failures) console.error(`  - ${f}`);
    process.exitCode = 1;
  }
}

await main();
