# Every drawing in the style library, every page

The library is 35 PDFs in six drawing styles, 215 pages in total. None of them has a reference takeoff, so what
is recorded here is what the engine makes of each page and where it stops - not an accuracy.

Every page is run through the whole pipeline and the run records: how it classified the input, what scale it
found and on what evidence, how many entries it read from the sheet's own designation list, how many labels
open with one of that list's system codes, how many of those reached a pipe, which stroke families it accepted
as pipe geometry, and how much of that geometry any label ended up owning.

The runner is `corpus.py`; the per-page records are JSONL so a change can be diffed against the previous run
rather than argued about. Where a page's reading mattered, it was also checked by overlay: the confirmed
geometry drawn back onto the sheet in red, and looked at.

## The pair that settled the hardest question

`z/2/V-50-1-A0122.pdf` and page 5 of `z/2/Hus A.pdf` are **the same sheet**: one exported with its layers, one
flattened to bare pen widths. That shape - a print with the layers dropped - is most of this library, and it
used to read nothing at all. Having both meant the layerless case could be settled against an answer instead of
guessed at: whatever rule was tried on the flat sheet had to land near what the layered one already reads, had
to leave the four reference takeoffs untouched, and had to survive being drawn back onto the paper and looked at.

## What the passes found, in the order they cost

1. **Sheets exported without layers read nothing.** A leader that strayed onto the pipes was enough to condemn
   their pen, because any family carrying a traced leader was excluded whole. Fixed: a drawing draws its leaders
   alike, so only the families carrying most of them are excluded; a family carrying a handful while another
   carries most is not where the drawing draws leaders. Where layer names exist they still decide on their own.
2. **Opening those sheets started measuring buildings.** Three sheets of one style read their outline - 664 m
   under a single waste designation on one of them. Two things hold the reading to the drawing now: with no
   layer name, the leaders must end on one family more than on all the others together, and that family must be
   at least the sheet's own middle pen by drawn length. A drawing's pipes are what it is for; they are never its
   faintest stroke, which is what rules its construction lines, hatching and grids. Every reading confirmed by
   overlay is on a pen at or above that middle; every reading of walls was below it.
3. **A note in the title block measured the paper.** The sheet border shares the pipes' pen on a flattened
   export, and a leader pointing at it carried 133 m named after the drawing number. A border ruled around
   nearly the whole sheet in a few square-on segments is now never pipe.
4. **A label written on a line was not read.** In one common Swedish style the code sits on a line that carries
   on to the pipe. Its free end is at the text, inside the label, where no boundary point looked - so the label's
   own leader was missed and a neighbour's passing leader was claimed instead. Fixed, and because the line
   belongs to one row it also tells a stacked block's labels apart.
5. **Dashed runs fell into more pieces than they had breaks.** Each free end names the nearest collinear end
   ahead of it; the two ends of one break name each other, and a third end further back that also named one of
   them used to stop the pair from being joined. Fixed: mutual naming joins, a one-sided claim only where
   nothing else claims either end.
6. **A stacked label of two pipes in one system could not be split.** Both rows matched the shared layer while
   one of them also had a layer naming it exactly. Fixed: a row takes the group whose layer names it most
   exactly and leaves the shared layer to the rows with nothing more exact.
7. **A scale conflict stopped four sheets before they began** (fixed earlier: the scale bar is read as geometry,
   and a ratio printed for another sheet format is rescaled and then confirmed by the bar).

## Where the library stands

Same 215 pages, same runner, before and after.

| | before | after |
|---|---|---|
| pipe geometry found | 19 523 m | 16 196 m |
| of it owned by a label | 3 443 m (18 %) | **3 932 m (24 %)** |
| pipe labels that reached a pipe | 568 of 8 534 (7 %) | **757 of 8 515 (9 %)** |
| pages that found no pipe family | 169 of 212 | **159 of 211** |
| scale verified | 185 | 184 |

Less geometry and more of it owned: the drop is the sheet borders and the leader lines that used to be counted
as pipe. Per file:

| file | pages | geometry | owned | labels | reached a pipe | pages with no family |
|---|---|---|---|---|---|---|
| S1_plan10_del44 | 1 | 44 m | 43 m (97 %) | 13 | 10 | 0/1 |
| S2_plan09_del42 | 1 | 26 m | 14 m (54 %) | 31 | 14 | 0/1 |
| S3_25 | 1 | 149 m | 12 m (8 %) | 10 | 4 | 0/1 |
| z/2 Hus A | 47 | 5 665 m | 1 138 m (20 %) | 1 749 | 243 | 30/47 |
| z/2 Hus B | 39 | 4 345 m | 1 012 m (23 %) | 954 | 105 | 26/39 |
| z/2 V-50-1-A0122 | 1 | 515 m | 180 m (35 %) | 106 | 68 | 0/1 |
| z/2 V-50-1-A0123 | 1 | 419 m | 259 m (62 %) | 87 | 51 | 0/1 |
| z/2 V-50-1-A0412 | 1 | 486 m | 246 m (51 %) | 80 | 51 | 0/1 |
| z/3 Badskon 1 | 26 | 668 m | 248 m (37 %) | 1 558 | 103 | 24/26 |
| z/3 3 | 1 | 371 m | 138 m (37 %) | 231 | 60 | 0/1 |
| z/3 10, 5, 7 | 3 | 0 m | - | 316 | 0 | 3/3 |
| z/4 Badskon 2 | 36 | 2 770 m | 498 m (18 %) | 1 186 | 38 | 27/36 |
| z/4 22, 9, 25 | 3 | 645 m | 144 m (22 %) | 36 | 10 | 0/3 |
| z/4 24, 6 | 2 | 0 m | - | 83 | 0 | 2/2 |
| z/5 (12 sheets + Badmössan) | 49 | 93 m | 0 m | 1 665 | 0 | 42/43 |
| z/6 (5 sheets) | 5 | 0 m | - | 430 | 0 | 5/5 |

Hus A changed character rather than size: before, a handful of pages carried enormous families named after the
drawing number (one page 2 573 m, another 1 136 m, a third 1 041 m of "pipe"); now twelve pages read 235-591 m
each under real designations - VS21-S13-15-F50, SF01-P5-75, KV01-X7-40-W40, S01-P5-110 - and five times as many
labels reach a pipe.

Two small sheets went the other way: `z/4/24` read 10 m before and now reads nothing, because its leaders are
all drawn with the one pen that carries them and nothing else on the sheet gets enough of the leaders' attention
to be named. That is the cost of the gate, paid on a 10 m sheet to stop a 664 m mistake.

## What is still open

- **97 pages carry 20 or more pipe labels and still find no pipe family.** They are concentrated in the styles
  below; this is the number to watch.
- **Where a pipe family is found, ownership is the limit, not reading.** Between a half and four fifths of the
  pipe geometry ends up unowned: a dashed run falls into separate pieces and an identity reaches only as far as
  the piece its own label touches.
- **A bundle label of several rows pointing at several parallel pipes is not resolved** unless the layer names
  separate the rows. The order convention is real - on the layered sheet where the layers do resolve them, 8 of
  9 such labels have their rows in the same order as the pipes are crossed - but the direction is not constant
  (7 near-first, 1 far-first), and assigning on a convention that holds 7 times in 8 swaps identities between
  systems on the ninth. Left unresolved rather than guessed.
- **Two styles still read nothing at all** (`z/5`, 49 pages, and `z/6`, 5 pages). On `z/5` the pipes, the
  leaders, the dimension lines and the hatching all share one pen and the leaders end on all of them alike; the
  sheet has not said which geometry its labels describe.

  On `z/6` the cause is now known. The sheets embed no font and carry no text at all - every glyph is stroked
  vector geometry - so the only route is shape recognition, and this typeface puts several characters within a
  hair of each other. Reading `R1402`, fourteen distinct shape families all come back as `0`, and their own
  runner-up scores are near-ties: the family of 43 glyphs scores `0:0.053` against `D:0.060` and spells
  `0I? FLÖOE` where the drawing wrote `DIM FLÖDE`; the family of 30 scores `0:0.053` against `O:0.071` and
  appears in `VV OCH VVC`; the family of 5 spells `0ATU?`, `UN0EPGPUPP`, `6YGGNA0` for `DATUM`, `UNDERGRUPP`,
  `BYGGNAD`. The family of 252 that spells `S?-?00` and `CL 3300` is the real zero. No family reads as `D` at
  all, on a Swedish drawing.

  The shape of the fix is a constraint the drawing itself provides: one typeface has one glyph per character, so
  within a size class two distinct shape families are two distinct characters. Three rules were measured against
  that evidence and none is safe yet. Letting the lowest-scoring family keep the character hands `0` to a
  single-glyph family and moves the 252-glyph one. Letting the largest family keep it and moving the near-tied
  rest is right for the three families above but wrong for two small numeral families (`?50, 02, ?0` and
  `0?, ?0, 06, 05`) that are near-tied on `O` and really are zeros. A one-to-one assignment weighted by member
  count breaks those same two, because once `0`, `O` and `D` are taken they are pushed onto whatever is free.
  What separates the true cases from the false ones is that the drawing has no `D` family anywhere - and that is
  knowledge about Swedish, not about the drawing. Recorded rather than shipped: a confidently wrong character
  splits an identity in two, which is worse than an unnamed one.
- **Four pages exceed a 300 second budget** and are recorded as timeouts.
