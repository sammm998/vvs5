# Known limitations (state at the open-world gate)

* **Vertical quantities**: the drawing carries no floor height, so the engine never invents vertical metres. It
  counts risers per designation (closed riser marks a label points at, marks of the same riser-mark family at the
  end of or on a pipe, count prefixes such as `5x` for marker stacks) and reports `riser_count`; the application
  turns risers into vertical metres only with a floor height the user enters (Excel/CSV export accept
  `floor_height`). Elevation pairs (VG/CL) on one pipe still give measured vertical metres. Riser counts follow the
  drawn marks: tiny end circles without a label (fixture connection points) are not risers; a label pointing at a
  connection mark still counts it. On drawing A this gives 55 risers against 54 in the reference takeoff, with
  per-system differences (KV2/VV1 7 vs 5 counted from the labelled end marks, S3-R8-75 28 vs 35 where seven riser
  marks sit on short unowned stubs).
* **Hatched areas** (regularly spaced parallel strokes: wall sections, existing parts) are discovered per drawing;
  pipe length inside them is measured but excluded from the horizontal quantity and reported as
  `in_hatched_area_m` ("varav i skrafferat område"), since takeoffs normally do not count pipe in walls.
* **DN transitions** are placed only at drawn evidence: the tick mark at a leader end on the pipe. Between two labels
  of different DN the geometry belongs to the label whose tick is not the boundary; when both (or neither) carry a
  tick and no dead end decides, the run is AMBIGUOUS_DN_BOUNDARY. A tick in the middle of a branch that continues
  past it (DN change or plain pointer, undecidable) makes the part between junction and tick AMBIGUOUS.
  Reducer symbols are not recognised as proof of a transition point.
* **Label-vs-takeoff convention on dead-end stubs**: a stub labelled DN75 with its tick right after the junction is
  owned as DN75 from that tick (label evidence). A human takeoff may count the stub as the main DN up to the last
  tick before the riser; the engine does not guess and reports the label's reading.
* **Unlabeled branches** at junctions stay AMBIGUOUS_BRANCH with candidate identities; only collinear straight-through
  runs, agreeing anchors, and the junction's own DN up to a drawn tick continue ownership through junctions.
* **Bundle labels** (one leader crossing N pipes with N stacked rows) are resolved through drawing-local layer-name
  tokens (exact, wildcard, or abbreviated tail such as KV2 -> V2), a unique parallel-line count bijection, or the row
  whose own underline the leader starts from; a bundle with two rows of the same system and different DN on the same
  layer stays ambiguous. Runs interrupted by symbol groups (stacked valve/coupling circles) are not bridged through
  the symbols: the geometry beyond the symbol group stays UNNAMED unless it carries its own label.
* **Count prefixes** ("5xKV2-X31") are read and recorded as the label's multiplier; quantities count the pipes actually
  drawn and attached (parallel lines), never the multiplier times one line.
* **Stroke-font recognition** relies on generic reference alphabets (Hershey simplex/duplex, Helvetica, Courier,
  Times skeletons). Very small text (< 2.5 pt on the page) and exotic CAD fonts produce unknown glyphs ('?');
  unknown characters are never repaired from expected words. The one exception is a character whose ink is cut
  by a clipping edge of the drawing (a sheet-part boundary that halves a label): the truncated character is
  completed from what this drawing itself writes, and only when one reading dominates the alternatives.
* **Hatched areas** are detected as regularly spaced parallel strokes and pipe inside them is measured but held
  out of the total. The engine cannot tell a wall section from a large area hatch marking an adjacent sheet part,
  so on a sheet that hatches most of its plan (drawing W-50-1-A-0014: 39 m hatched against 48 m outside) the
  operator decides with the "Räkna med skrafferade ytor" checkbox.
* **Open-world drawing D** (ground-heating site plan, 1:400): labels are zone descriptions without DN, placed on
  unlabeled loop pipes; no VVS designation grammar exists, so no pipes are owned. The engine reports UNSUPPORTED
  structure and zero false ownership. Post-freeze, per-glyph O/0 twin substitution lets the vector scale bar
  (0 5 10 20 30 METER) be read (BAR_ONLY, 1:400).
* **Unreadable characters are only partly recoverable.** The OCR-assisted pass fills a '?' only where OCR reads
  the same word and agrees with it character for character. On dense drawings much of the small text is beyond
  OCR too, so unreadable characters remain; the unresolved list now says how many sit inside a designation (which
  costs a takeoff row) and how many sit in legend or note text (which costs nothing).
* **The review agents are deterministic checks, not a language model.** They compare the result against the
  drawing's own evidence and report where to look; they do not reason about intent, and they never edit a
  measurement. The OCR cross-check reads the rendered page only to ask whether a designation exists where the
  vector reading has none - it never contributes a metre.
* **Scanned drawings are not analysed.** Only vector PDFs are read. A scanned or image-only page is classified,
  skipped and reported; a PDF with no vector page is rejected. Measuring a scan means inferring geometry from
  pixels, and on these drawings that produced errors large enough to be misleading, so the engine says no instead.
* **Docker images** could not be built inside the development container (no Docker daemon); the Dockerfiles and
  compose file are provided as written and the backend/frontend were verified with pytest and `npm run build`.
* Multi-page PDFs are analysed page by page; overlays and artifacts are written for page 0 (the first analysed page)
  in the CLI and web application.

## Added after the generality pass over four unseen drawing styles

* **One scale per page, not per drawing region.** A detail box drawn at another scale is measured at the plan's
  scale. Where the page states two ratios and no bar confirms either, the reading refuses rather than picks; where
  a bar disagrees with the text, the bar is used, the state is CONFLICT, and every run measured that way now
  carries the conflict in its reasons rather than reading as confidently measured.
* **Curved dashed runs are not bridged around a bend.** Curves (Bezier, arc, polyline) are read and measured, but
  a break in a dashed *curve* is only closed where the pieces are collinear or meet at a corner.
* **A bundle label listing more codes than the sheet draws lines** is left ambiguous. Elimination settles it only
  when every other run of the bundle is named elsewhere AND the remaining code's own leader touches the remaining
  run; without that positive contact the case stays open rather than being split by a convention.
* **Identity can still be decided by node ordering in one case.** The junction pass stops looking at a run once it
  is confirmed, so an unnamed length between two junctions takes the identity of whichever end was reached first.
  A pass demoting such runs where the far end disagrees was written, measured, and reverted: on the reference set
  it cost correct metres and removed no wrong ones. The defect is real and unfixed.
* **Material written after the dimension would merge two identities.** `identity_from_text` drops short alphabetic
  tokens after the DN token, which is right for an insulation marker (`FJV1-S6-50/W`) and wrong for an office that
  writes the material there (`VS1-20-CU` vs `VS1-20-PEX`). No sheet in the corpus writes it that way, so the change
  cannot be tested and has not been made.
* **Very large pages can exceed the analysis timeout.** Five of 212 pages in the style corpus did not finish inside
  240 s. A page that times out is reported as TIMEOUT; it never produces a partial quantity.

## Ink that never becomes pipe

Most of the ink on a plan sheet is not pipe, and the reading has four different relationships to a drawn family:
it measures it, it weighs it and sets it aside, no label's leader ever comes near it, or it sits on a layer the
drawing uses for its own labels and frames. Only the first produces metres. The others used to leave the reading
without a word, which made a declined wall and a missed run look identical on the sheet - both simply grey - so
`declined-geometry.json` now carries all of them with the reason and a bounded sample of the strokes, and the
viewer draws them as *Bortvald geometri*. On the seven drawings in the corpus every stroke that is not a letter or
a leader line lands in one of the four, and a test holds that invariant.

Two limits are worth stating plainly:

* **A family no leader points at can never be measured, however much it looks like pipe.** Identity comes from a
  designation and its real leader; a run with neither has no identity, and inventing one would be exactly the wrong
  certainty. Such a family is reported - and marked when its layer is named the way this drawing names its pipe
  layers, which is the case a reader most wants to look at - but it is never claimed. On the reference drawing that
  is 36.9 m of ink on VVS-named layers, none of it in the hand takeoff.
* **The strokes carried are bounded** (8 000 for weighed-and-declined families, 4 000 for unweighed ones, and no
  single family may take more than 3 000 / 1 500). A building outline can hold tens of thousands of strokes; past
  the budget a family reports its full length and segment count with `segments_truncated` set, so the number is
  complete even when the picture is a sample. The budget is spent on pipe-named layers first, so a vector logo
  cannot crowd out the ink a reader actually wants to look at.
* **Filled shapes are counted, not drawn.** A pipe is a stroked line; a filled room outline or piece of furniture
  is not one however much of the sheet it covers. Their number and length are reported (2 199.75 m on the
  reference drawing) so the sheet adds up, and they are never offered as pipe candidates.

## What a language model is and is not allowed to do here

The measurement path is vector geometry and nothing else. Two model-assisted passes exist, both fenced in code:

* **A second reader** (`vvs_engine/semantics/astra.py`) may choose among candidates the drawing itself offers, for a
  case the engine already declared AMBIGUOUS. `verify()` refuses any answer that is not one of those candidates, an
  answer naming two of them stays ambiguous, and a chosen family is checked again at the point of use against the
  geometry that leader actually touched. Without a transport nothing is asked, which is the default: the engine is
  deterministic and needs no network.
* **A look at the rendered page** (`vvs_engine/review/vision.py`) may report what the vector reading seems to have
  missed. It cannot do anything else: there is no `apply()`, a finding carries no number, and nothing connects a
  finding to a quantity. On its first run against the reference drawing it correctly spotted unread component tags
  and also reported two systems as being in the designation list that are not in it. A model that can see is still
  a model that can be wrong, which is why it cannot cost a metre.
