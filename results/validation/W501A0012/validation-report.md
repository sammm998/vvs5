# Validation - W-50-1-A-0012 against its reference takeoff

Reference: a partial Bluebeam markup of this sheet - two systems measured as four polylines, with the
vertical pipes given as counts in the Antal_VS column. The engine ran on the same PDF with its annotations
stripped; production code never reads this directory.

- Scale: VERIFIED, 1:50 (scale_text_and_scale_bar_agree)
- Reconciliation: VALID; 100 % of the accepted pipe geometry (20.7 m) is owned by a designation
- Designations read: 30; verified attachments: 7

| Beteckning | ref H m | ours H m | diff | ref vertikala | ur etikett | ur symbol |
|---|---|---|---|---|---|---|
| KV1-X31-16 | 10.90 | 10.73 | -0.17 | 2 | 2 | 1 |
| S3-R8-75 | 6.70 | 6.50 | -0.20 | 2 | 2 | 0 |
| SUMMA | 17.60 | 17.23 | -0.37 | 4 | 4 | 1 |

Horizontal: 17.23 m against 17.60 m, -2.1 %.
Sampling the reference polylines every 1 pt: 17.46 m of their 17.72 m is owned under the right designation,
0.19 m lies inside hatching (measured, reported separately, excluded by default) and 0.07 m falls to the
neighbouring identity at a junction. Nothing is missing: no sample lies further than 3 pt from a primitive
the engine owns.

Vertical: the reference counts 2 + 2. Reading them from the labels whose dimension stands on the row below
gives exactly 2 + 2; reading them from drawn riser symbols gives 1 + 0. On this drawing the label rule is
right and the symbol rule is wrong, which is why labels are now the default source and symbols the option.

Outside the reference's scope: the sheet carries 11 further designations with a dimension whose leader the
engine does not resolve to a pipe (KV2-X31, VV1-X31 and S3-R8-110 among them). The reference does not
measure those systems at all, so this drawing cannot settle whether they belong in the takeoff.
