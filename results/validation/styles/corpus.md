# Every drawing in the style library, every page

The library is 32 PDFs in six drawing styles, 212 pages in total. None of them has a reference takeoff, so what
is recorded here is what the engine makes of each page and where it stops - not an accuracy.

Every page is run through the whole pipeline and the run records: how it classified the input, what scale it
found and on what evidence, how many entries it read from the sheet's own designation list, how many labels
open with one of that list's system codes, how many of those reached a pipe, which stroke families it accepted
as pipe geometry, and how much of that geometry any label ended up owning.

The runner is `corpus.py` in the working notes; the per-page records are JSONL so a change can be diffed
against the previous run rather than argued about.

## What the first full pass found

Ordered by how much they cost:

1. **20 of 26 single-page sheets found no pipe family at all** and measured nothing. Two causes, both since
   traced: a scale conflict that stopped four sheets before they began, and - on the sheets that carry no
   layers - the leaders being drawn with the same pen as the pipes, so the family that carries them is excluded
   as annotation and the pipes go with it.
2. **Four sheets of one style could not settle their scale.** Their title block says "1:50 i A1-format (1:100 i
   A3-format)" and the sheet is A3; the second ratio was misread and the two candidates could not be told
   apart.
3. **Where a pipe family is found, ownership is the limit, not reading.** On the sheets that do measure, the
   labels are read and most of them attach, but between a third and a half of the pipe geometry ends up
   unowned, because a dashed run falls into many separate pieces and an identity reaches only as far as the
   piece its own label touches.

## Fixed since

- A scale bar is now read as geometry - a baseline with ticks at one spacing - and its drawn length must come
  out a whole number of metres. That confirms a printed ratio, or tells two apart, without reading the numbers
  under the bar. A ratio printed for another sheet format is rescaled to this sheet by the step between the
  formats and then has to be confirmed by the bar. All four sheets of that style now read a verified 1:100, and
  one of them measures 370 m of pipe where it measured none.
- The leader lines and label frames are never measured as pipe, even where they share the pipes' pen.

## Not fixed, and why

The layer-less sheets where the leaders share the pipes' pen still measure nothing. Two ways of relaxing the
rule were tried and both reverted: admitting those families to the vote displaced the real pipe families on the
reference set, and admitting them only as a last resort claimed 1327 m of floor plan as pipe on the very sheets
it was meant to rescue. Reporting nothing is the honest answer until leaders and pipes can be separated on
evidence rather than on the pen they were drawn with.
