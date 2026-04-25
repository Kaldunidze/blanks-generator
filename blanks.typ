
// ─── Configuration ────────────────────────────────────────────────────────────
// Edit these values, or generate via the GUI (app.py).

#let start_team  = 1
#let finish_team = 60
#let cols        = 4            // blanks per row
#let rows        = 9            // rows per page  (4×9 = 36 blanks)
#let landscape   = false        // true = A4 landscape, false = A4 portrait
#let location    = ""           // event / location label
#let team_prefix = "Team №"
#let font_name   = ""           // leave empty for typst default
// #let logo     = image("/assets/logo.svg")
#let logo        = none         // set to image(...) or leave as none

// ─── Optional font ─────────────────────────────────────────────────────────────
#if font_name != "" {
  set text(font: font_name)
}

// ─── Layout helpers ────────────────────────────────────────────────────────────

#let blank_cell(team_label, event, question_num, pic) = [
  #box(width: 90%, height: 80%, [
    #place(left  + top,    text(size: 10pt, team_label))
    #if pic != none [
      #place(right + top,  move(dx: 10%, dy: -15%, box(height: 70%, pic)))
    ]
    #place(center + horizon, text(
      size: 50pt,
      fill: color.black.transparentize(80%),
      [#question_num],
    ))
    #place(right + bottom, event)
  ])
]

#let blank_page(team_label, event, pic, c, r, q0) = {
  set page(margin: 0cm, flipped: landscape)
  let cells = range(q0, c * r + q0).map(n =>
    align(center + horizon, blank_cell(team_label, event, n, pic))
  )
  grid(
    columns: (100% / c,) * c,
    rows:    (100% / r,) * r,
    gutter:  0cm,
    stroke:  1pt + black,
    ..cells,
  )
}

// ─── Output ────────────────────────────────────────────────────────────────────

#for i in range(start_team, finish_team + 1) {
  let label = team_prefix + str(i)
  blank_page(label, location, logo, cols, rows, 1)
}


