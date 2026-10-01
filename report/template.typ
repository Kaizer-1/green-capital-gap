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
#let exhibit(file, caption) = figure(
  image("/outputs/figures/" + file + ".pdf", width: 100%),
  caption: caption,
  supplement: [Figure],
  // Float rather than leaving a page-tall hole wherever the block will not fit.
  placement: auto,
)

#let method-exhibit(file, caption) = figure(
  image("/outputs/figures/" + file + ".pdf", width: 100%),
  caption: caption,
  supplement: [Figure],
  kind: "methodology",
  placement: auto,
)

#let conf(
  title: none,
  subtitle: none,
  author: none,
  usn: none,
  course: none,
  date: none,
  wordcount: none,
  doc,
) = {
  set document(title: title, author: author)

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
        align(left)[The Green Capital Gap],
        align(center)[#counter(page).display("1")],
        align(right)[#usn],
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
    v(0.5em, weak: true)
  }
  show heading.where(level: 2): it => {
    v(1.15em, weak: true)
    text(size: 11.5pt, weight: "semibold", it.body)
    v(0.3em, weak: true)
  }
  show heading.where(level: 3): it => {
    v(0.9em, weak: true)
    text(size: 10.5pt, weight: "semibold", style: "italic", it.body)
    v(0.2em, weak: true)
  }

  show link: set text(fill: accent)
  set table(stroke: (x, y) => (
    top: if y <= 1 { 0.6pt + ink } else { 0.3pt + rule-colour },
    bottom: 0.6pt + ink,
  ))
  show table.cell.where(y: 0): set text(weight: "semibold")

  // Figures: caption below, small, muted, one line. The figures carry their
  // own finding-sentence titles and source footers, so the caption only needs
  // to name the exhibit.
  set figure(gap: 0.9em)
  show figure.caption: it => {
    set text(size: 8.5pt, fill: ink-muted)
    set par(justify: false, leading: 0.62em)
    align(left)[
      #text(weight: "semibold", fill: ink)[#it.supplement #context it.counter.display(it.numbering).]
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
  v(5.5cm)
  align(left)[
    #text(size: 26pt, weight: "semibold")[#title]
    #v(0.5em)
    #text(size: 13pt, fill: ink-muted, style: "italic")[#subtitle]
    #v(2.8cm)
    #line(length: 38%, stroke: 0.8pt + ink)
    #v(0.7em)
    #text(size: 11pt)[#author]
    #v(0.25em)
    #text(size: 10pt, fill: ink-muted)[USN #usn]
    #v(0.25em)
    #text(size: 10pt, fill: ink-muted)[#course]
    #v(0.25em)
    #text(size: 10pt, fill: ink-muted)[#date]
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
