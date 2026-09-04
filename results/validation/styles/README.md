# Drawing styles read without a reference takeoff

Three sheets from other projects were run to find defects that only show up outside one office's conventions.
No reference takeoff exists for them, so nothing here is a measured accuracy: it is what the engine makes of
each sheet, and where it still stops short.

All three are vector pages with real text (not stroke-exploded labels) and, unlike the reference set, **carry no
optional-content layers at all**. Everything the engine knows about which line is which has to come from stroke
width, colour and structure.

## V53.1-1944 - Plan 10, Del 44, Spillvattenanläggning

Roof drainage, one system, labels `DBA1-110` over two note rows, leaders with end ticks.

- Scale VERIFIED 1:50 (printed ratio and scale bar agree).
- 51 designations read; 13 of 17 leaders attached to pipe geometry.
- One pipe family, `w1.98` black: 52.68 m confirmed, 1.23 m unowned, nothing ambiguous.
- Reconciliation VALID.

Reads essentially cleanly. Before this session it found 5 attachments and read all system codes as elevations.

## V53.1-1842 - Plan 09, Del 42, Spillvattenanläggning

A toilet block drawn at 1:50 with dash-dot pipes and the two-row label form (`S12` over `75`).

- Scale VERIFIED 1:50.
- 44 designations read, including the row-below dimensions; four sizes measured (S12-160, S12-110, S12-75,
  DBA1-110), 8.42 m in total.
- One pipe family, `w1.92` black: 11.13 m confirmed, 15.14 m unowned.
- 21 of 30 anchors reach no pipe - most of them component tags in the room schedule boxes, which have no pipe to
  reach and are correctly left unattached.

The remaining gap is ownership, not reading: the pipes are found and the labels are read, but a little over half
the network is not claimed by any label. That is reported as unowned rather than guessed.

## W--50-1-0501112 - Plan 05, Del 2

Heating, tap water and waste in one plan, leaders ending in small circles on the pipe.

- Scale TEXT_ONLY 1:50 - the printed ratio is there, the scale bar is not vector geometry on this sheet.
- 49 designations read, including `RAD2-S13/W` over `35` and `S1-G3` over `75 (L)`.
- Two systems measured (9.73 m); the family the leaders vote for is `w0.96` black, which on this sheet is mostly
  title-block line work with one dashed pipe run in it, so 275 m is carried as unowned.

This sheet is the one still to solve: the pipes are drawn in `w1.44` and `w2.04` black, and the leaders reach
them through circle symbols rather than by touching the line, so the family vote never sees them. It is an
honest failure - the engine reports two systems and 275 m of unowned line work rather than inventing a number -
but it is a failure.
