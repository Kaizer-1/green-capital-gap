// report/template.typ
//
// Hand-written Typst template for the Green Capital Gap report.
//
// Replaces pandoc's default, which (a) placed the page number inside the text
// block so that extracted text read "15. The double gap" for page 1 followed by
// heading 5, and (b) looked like a default document wrapped around figures that
// did not. The palette, the serif display face and the rule colour below are
// the same ones src/gcg/viz/theme.py uses, so the document and its figures read
// as one artefact.
#let ink = rgb("#141413")
#let ink-muted = rgb("#6E6E68")
#let rule-colour = rgb("#E3E1DA")
#let accent = rgb("#0E7C7B")

// An exhibit: a vector figure with a one-line caption and a label for
// cross-referencing. Captions stay short because every figure already carries a
// finding-sentence title and a source footer of its own.
// An exhibit embeds the PRINT variant: no baked-in title, subtitle or source
// block, rendered at exactly the text-column width so nothing is scaled here.
// Captions are injected by render.py from src/gcg/viz/print_mode.py, which is
// their single source of truth. Writing one into the markdown lets it drift
// from the spec the figure was built against, which is exactly what happened
// once: a caption still described a series the figure no longer drew.
#let CAPTIONS = state("captions", (:))

#let exhibit(file) = figure(
  image("/outputs/figures/print/" + file + "_print.pdf", width: 100%),
  caption: context CAPTIONS.get().at(file, default: [MISSING CAPTION: #file]),
  supplement: [Figure],
  // Float rather than leaving a page-tall hole wherever the block will not fit.
  placement: auto,
)

#let method-exhibit(file) = figure(
  image("/outputs/figures/print/" + file + "_print.pdf", width: 100%),
  caption: context CAPTIONS.get().at(file, default: [MISSING CAPTION: #file]),
  supplement: [Figure],
  kind: "methodology",
  placement: auto,
)

#let conf(
  title: none,
  subtitle: none,
  shorttitle: none,
  footerright: none,
  authors: (),
  guide: none,
  institution: none,
  course: none,
  date: none,
  wordcount: none,
  doc,
) = {
  set document(title: title, author: authors.map(a => a.name))

  set page(
    paper: "a4",
    margin: (top: 2.6cm, bottom: 2.6cm, left: 2.9cm, right: 2.9cm),
    // The number lives in the page margin, not at the end of the text block.
    // That is the fix for the "15." defect: nothing can concatenate it with
    // the first line of the following page.
    footer: context {
      // The title page carries no running footer.
      if counter(page).get().first() <= 1 and here().page() <= 1 { return }
      set text(size: 8.5pt, fill: ink-muted)
      line(length: 100%, stroke: 0.4pt + rule-colour)
      v(0.35em)
      grid(
        columns: (1fr, auto, 1fr),
        align(left)[#shorttitle],
        align(center)[#counter(page).display("1")],
        align(right)[#footerright],
      )
    },
    footer-descent: 1.1em,
  )

  set text(font: ("Charter", "Georgia", "New Computer Modern"),
           size: 10.5pt, fill: ink, lang: "en")
  // Generous leading: the figures are airy and the prose should match.
  set par(justify: true, leading: 0.78em, spacing: 1.25em, first-line-indent: 0pt)

  show heading: set text(fill: ink)
  show heading.where(level: 1): it => {
    v(1.5em, weak: true)
    text(size: 15pt, weight: "semibold", it.body)
    v(0.45em, weak: true)
    line(length: 100%, stroke: 0.6pt + rule-colour)
    v(0.72em)
  }
  show heading.where(level: 2): it => {
    v(1.2em, weak: true)
    text(size: 11.5pt, weight: "semibold", it.body)
    // NOT weak: a weak space collapses against the paragraph that follows,
    // which is why level-2 headings ran flush into their first line.
    v(0.52em)
  }
  show heading.where(level: 3): it => {
    v(1.0em, weak: true)
    text(size: 10.5pt, weight: "semibold", style: "italic", it.body)
    v(0.42em)
  }

  show link: set text(fill: accent)
  set table(stroke: (x, y) => (
    top: if y <= 1 { 0.6pt + ink } else { 0.3pt + rule-colour },
    bottom: 0.6pt + ink,
  ))
  show table.cell.where(y: 0): set text(weight: "semibold")

  // Figures: the caption now carries what the image used to. Print variants
  // have no baked-in title, subtitle or source block, so those three tiers are
  // set here in the document's own type rather than rasterised inside a PDF at
  // a size nobody chose.
  set figure(gap: 0.85em)
  show figure.caption: it => {
    set text(size: 8.3pt, fill: ink-muted)
    set par(justify: false, leading: 0.66em)
    align(left)[
      #text(weight: "semibold", fill: ink)[
        #it.supplement #context it.counter.display(it.numbering).
      ]
      #it.body
    ]
  }
  show figure: set block(breakable: false, above: 1.6em, below: 1.6em)

  // Methodology exhibits carry their own sequence so that M1 and M2 do not
  // consume numbers in the results flow. They answer questions about method,
  // not about the argument.
  show figure.where(kind: "methodology"): set figure(numbering: n => "M" + str(n))

  show quote: set text(style: "italic", fill: ink-muted)

  // ---- title page ----
  v(4.2cm)
  align(left)[
    #text(size: 26pt, weight: "semibold")[#title]
    #v(0.5em)
    #text(size: 12.5pt, fill: ink-muted, style: "italic")[#subtitle]
    #v(2.4cm)
    #line(length: 38%, stroke: 0.8pt + ink)
    #v(0.8em)
    // The author list is read from report/metadata.yaml, which is the single
    // source of truth for it; nothing here is typed twice.
    #grid(
      columns: (auto, auto),
      column-gutter: 1.1em,
      row-gutter: 0.42em,
      ..authors.map(a => (
        text(size: 10.5pt)[#a.name],
        text(size: 10pt, fill: ink-muted)[#a.usn],
      )).flatten()
    )
    #v(1.0em)
    #text(size: 10pt, fill: ink-muted)[Under the guidance of #guide]
    #v(0.9em)
    #text(size: 10pt, fill: ink-muted)[#institution]
    #v(0.25em)
    #text(size: 10pt, fill: ink-muted)[#course #sym.dot.c #date]
    #v(0.25em)
    #text(size: 10pt, fill: ink-muted)[#wordcount words, excluding figures, tables, references and appendices]
  ]
  pagebreak()

  // ---- contents, no dot leaders ----
  {
    set text(size: 10pt)
    show outline.entry: it => {
      let is-top = it.level == 1
      block(
        above: if is-top { 1.0em } else { 0.4em },
        below: 0em,
        grid(
          columns: (1fr, auto),
          gutter: 0.6em,
          text(
            weight: if is-top { "semibold" } else { "regular" },
            fill: if is-top { ink } else { ink-muted },
            it.element.body,
          ),
          // `entry.page` was removed in Typst 0.13; resolve the page
          // counter at the target location instead.
          text(fill: ink-muted)[#context counter(page).at(it.element.location()).first()],
        ),
      )
    }
    text(size: 13pt, weight: "semibold")[Contents]
    v(0.6em)
    outline(title: none, depth: 2, indent: 1.2em)
  }
  pagebreak()

  counter(page).update(1)
  doc
}
