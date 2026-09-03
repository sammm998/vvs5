# Known limitations (state at the open-world gate)

* **Vertical quantities** are produced only when two elevation annotations with the same tag (VG, CL, ...) sit on
  the anchors of one physical pipe; riser symbols and section relationships are not interpreted. Most pipes therefore
  report `vertical_m = UNKNOWN` (honest, not fabricated).
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
  unknown characters are never repaired from expected words.
* **Open-world drawing D** (ground-heating site plan, 1:400): labels are zone descriptions without DN, placed on
  unlabeled loop pipes; no VVS designation grammar exists, so no pipes are owned. The engine reports UNSUPPORTED
  structure and zero false ownership. Post-freeze, per-glyph O/0 twin substitution lets the vector scale bar
  (0 5 10 20 30 METER) be read (BAR_ONLY, 1:400).
* **Docker images** could not be built inside the development container (no Docker daemon); the Dockerfiles and
  compose file are provided as written and the backend/frontend were verified with pytest and `npm run build`.
* Multi-page PDFs are analysed page by page; overlays and artifacts are written for page 0 (the first analysed page)
  in the CLI and web application.
