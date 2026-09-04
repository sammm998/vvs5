# Drawing styles read without a reference takeoff

Five sheets from other projects, in three drawing styles, none of which has a reference takeoff. Nothing here is
a measured accuracy. It is what the engine makes of each sheet, checked two ways that need no facit.

**How they are checked.** First, the designations: the sheet's own designation list names its systems, so every
word out on the drawing that opens with one of those system codes is a pipe label, and each one either became a
designation and reached a pipe, or did not. Second, the pipes: the engine's result is drawn back onto the
drawing - every primitive of the accepted pipe families coloured by which identity owns it, unowned in magenta,
each leader endpoint circled by its state - and the picture is compared with what is drawn. Both checks were
first run on the four sheets that do have a reference takeoff, where they agree with it: 100 % of the marked
geometry owned on three of them, 99 % on the fourth.

| sheet | pipe geometry | owned | pipe labels | reached a pipe |
|---|---|---|---|---|
| W-50-1-A-0011 (has a facit) | 190.2 m | 190.2 m | 100 % | 125 | 114 |
| W-50-1-A-0012 (has a facit) | 20.7 m | 20.7 m | 100 % | 22 | 9 |
| W-50-1-A-0013 (has a facit) | 99.6 m | 98.3 m | 99 % | 80 | 67 |
| W-50-1-A-0014 (has a facit) | 75.8 m | 75.8 m | 100 % | 70 | 62 |
| V53.1-1944, Plan 10 Del 44 | 43.9 m | 42.7 m | **97 %** | 13 | 8 |
| V53.1-1842, Plan 09 Del 42 | 26.3 m | 12.6 m | **48 %** | 31 | 12 |
| W--50-1-0501112 | 282.9 m | 11.7 m | **4 %** | 10 | 4 |

## V53.1-1944 - Plan 10, Del 44

Roof drainage, one system, `DBA1-110` labels with end ticks. The overlay shows the whole drawn network covered,
end to end: 42.7 m of 43.9 m owned, one roof drain left unowned. All 13 labels read; 8 reach a pipe. This sheet
reads as well as the reference set.

## V53.1-1842 - Plan 09, Del 42

A toilet block, dash-dot pipes, the two-row label form. Every drawn pipe is found - the overlay colours all of
it - but only half carries an identity. What the picture shows is that the runs the engine did not claim are the
ones no leader reached: the network is drawn in 237 separate pieces because of its dash-dot pattern and its
bends, so an identity reaches only as far as the piece its own label touches.

The remaining work here is connectivity, not reading.

## W--50-1-0501112

Heating, tap water and waste in one plan; leaders end in small circles on the pipe. Three systems are now
measured (14.2 m) where two were before. The family the leaders vote for is `w0.96` black, which on this sheet
is the title block's rules and headings with one dashed pipe run inside it, so 271 m is carried as unowned. The
sheet's designation list is also only half read - nine of its system and material codes are still unreadable
where two legend rows stand close enough to be read as one column.

This is the sheet still to solve, and it says so rather than inventing a number.
