# Validation report: DRAWING_A (W-50-1-A-0011)

Reference: Bluebeam measurement annotations in the marked PDF (78 PolyLine measurements, subjects = designations) and the Excel export (horizontal lengths, vertical heights).
The blind artifacts (commit 87c37c1) were frozen before the facit was opened and are unchanged; the final run (420a617, post-gate generic fixes) gives identical results on A.

## Summary (final = blind for A)

- Designations: correct 8 / missed 1 (VV1-X31-16) / false positive 0
- DN: correct for all 8 matched designations (DN is part of the matched key); missed 1; wrong 0
- Pipe attachments (verified anchors vs reference geometry at the contact point): correct 84, wrong 18, not in facit 1
- Physical pipe match per reference measurement (78): full 39, partial 6, miss 33
- Quantity: confirmed horizontal 156.661 m vs reference 213.7 m; confirmed vertical 0.5 m vs reference 150.8 m (reference assumes 2.8 m per riser; the drawing carries no riser heights, so the engine reports UNKNOWN by design)
- Length audit: correctly owned 92.31 m, incorrectly owned 32.99 m, owned but unmarked in facit 8.21 m, missed reference 105.05 m, ambiguous near reference 2.95 m, unowned near reference 54.18 m

## Per designation

| Beteckning | ref H m | confirmed H m | ambiguous m | ref V m | confirmed V m | pipes | ref segments |
|---|---|---|---|---|---|---|---|
| KV1-X31-16 | 17.4 | 10.36 | 0.0 | 0.0 | 0.0 | 1 | 2 |
| KV2-X31-16 | 33.4 | 6.3 | 0.0 | 14.0 | 0.0 | 1 | 5 |
| S1-P2 | 0.0 | 2.72 | 0.0 | 0.0 | 0.0 | 1 | 0 |
| S1-P2-110 | 9.8 | 8.71 | 0.0 | 2.8 | 0.04 | 1 | 4 |
| S1-P2-75 | 4.7 | 10.45 | 0.0 | 8.0 | 0.0 | 5 | 4 |
| S3-P2-160 | 16.9 | 16.99 | 0.0 | 0.0 | 0.0 | 1 | 1 |
| S3-R8-110 | 59.8 | 50.73 | 1.15 | 14.0 | 0.25 | 6 | 28 |
| S3-R8-160 | 16.3 | 11.14 | 0.53 | 0.0 | 0.09 | 1 | 2 |
| S3-R8-75 | 21.3 | 39.27 | 1.28 | 98.0 | 0.12 | 20 | 27 |
| VV1-X31-16 | 34.1 | 0.0 | 0.0 | 14.0 | 0.0 | 0 | 5 |

## Wrong-ownership pairs (ours -> reference)

- S3-R8-75 owned geometry the facit marks as S3-R8-110: 19.47 m
- S3-R8-110 owned geometry the facit marks as VV1-X31-16: 5.15 m
- S3-R8-110 owned geometry the facit marks as S3-R8-160: 3.71 m
- S1-P2 owned geometry the facit marks as S1-P2-110: 1.98 m
- S3-R8-110 owned geometry the facit marks as S3-R8-75: 1.34 m
- S1-P2-75 owned geometry the facit marks as S1-P2-110: 0.98 m
- S1-P2 owned geometry the facit marks as S1-P2-75: 0.28 m
- KV2-X31-16 owned geometry the facit marks as VV1-X31-16: 0.05 m
- KV2-X31-16 owned geometry the facit marks as S3-R8-110: 0.03 m

## Verdict

PARTIALLY CORRECT. Designations and DN are right (8 of 9, no false positives, no wrong DN). Pipe ownership is right for 92.3 m of the 213.7 m the facit marks, wrong for 33.0 m and missing for 105.1 m. Horizontal total 156.7 m vs 213.7 m (73%). Vertical is not comparable: the facit adds 2.8 m per riser by convention, the drawing carries no riser heights, and the engine reports vertical as UNKNOWN rather than assuming a floor height.

## Failure taxonomy (generated after the blind freeze; frozen artifacts untouched)

### Class W1: DN-row leader ends on a junction between DN-different pipes (13 of 18 wrong attachments, 19.5 m wrong)

Labels `S3-R8` with DN row `75` sit on short branch stubs off the `S3-R8-110` main line. Their leader end tick lands within 0-0.4 pt of the T-junction where the 75 stub meets the 110 main line. The contact resolves to the 110 main line, so the 75 identity is seeded on the main line. The ownership propagation then carries `S3-R8-75` along the main line until it meets a 110 seed, and the DN boundary lands in the wrong place (AMBIGUOUS_DN_BOUNDARY in a few chains, wrong ownership in most).
Generic fix candidate: a contact within the micro-gap radius of a junction node between pipes of the same family must be attached to the junction, not to one incident pipe, and resolved by the DN row (a DN seed matching an incident pipe's existing DN-different seeds is contradictory, so the identity goes to the other incident branch or the state becomes AMBIGUOUS_ATTACHMENT). No drawing-specific values involved.

### Class W2: leader ends on a bundle marker of another system (1 wrong attachment, 5.2 m wrong)

One `S3-R8-110` leader terminates on the circle marker of the `5xVV1-X31-16` tappvatten bundle. The marker bridge (dot within 2.5 pt of a pipe end) accepted the marker as a bridge into the bundle pipe. System conflict (S3 vs VV1) was not raised because the bundle pipe carried no identity at that point.
Generic fix candidate: marker bridges must require the marker to be on the leader's own path chain or the bridged pipe to be the unique pipe end near the marker; when the bridged pipe family differs from the family the label's other rows attach to, mark AMBIGUOUS.

### Class W3: DN-less anchors on DN-carrying pipes (3 wrong attachments, 2.3 m wrong)

`S1-P2` (no DN row found, block split across two units) and one `S1-P2-75` anchor own geometry the facit marks as `S1-P2-110`. The DN row was in the neighbouring unit of the same block. Result is UNNAMED-DN pipes reported as `S1-P2` (2.72 m) and a 110/75 boundary 1 m off.
Generic fix candidate: unit splitting must not separate a designation row from the DN row directly beneath it when no second designation row intervenes.

### Class M1: parallel bundles not attached (10 reference segments missed, 69.9 m missed)

`5xVV1-X31-16` and `2xKV2-X31-16` label the tappvatten bundles. The count prefix is parsed (grammar `#`), but the parallel-count bijection in resolve_block requires N parallel pipe contacts on the leader; the bundle is drawn as a single polyline with a circle marker. The 5 VV1 segments (34.1 m) and 4 of 5 KV2 segments (27.1 m) are therefore unowned, and KV1 misses one 8.7 m segment for the same reason. `VV1-X31-16` is the one missed designation: the reading `5xVV1-X31-16` was produced but never verified by attachment, so it never entered the confirmed designation set.
Generic fix candidate: a count prefix N on a single-pipe contact means N physical pipes on one drawn line (quantity multiplier), which the model already supports for parallel groups; the bijection should accept 1 contact and set count = N.

### Class M2: short main-line stubs and partial coverage (15 S3-R8-110 misses, 5 partials, 23 m missed)

Short `S3-R8-110` segments between T-junctions (0.5-2 m) are owned by the wrong DN (class W1 mirror image) or remain unowned when both neighbouring chains carry a 75 seed. The 5 partial covers are chains whose DN boundary sits at the wrong junction.
Fix follows from W1.

### Class V1: vertical lengths (150.8 m reference, 0.5 m reported)

The facit assigns 2.8 m per riser symbol. The drawing has no riser elevations, so the engine reports vertical as UNKNOWN with reason NO_ELEVATION_EVIDENCE. This is by design and stays; the report exposes riser count so a user-set floor height can be applied in the application.

## Post-validation generic fixes (results/A regenerated; blind artifacts untouched)

The failure classes above were addressed with drawing-independent rules (tick marks as drawn DN boundaries, symbol-
attached labels as weak riser labels, junction DN flowing into dead-end stubs, leader start conflicts resolved by
outward direction, end-marker clusters for bundles, abbreviated layer tokens, single-system layers, hatched wall
areas reported separately, riser counting). Validation of the regenerated artifacts
(validation-post_validation_fixes.json):

- Designations: 9 / 9 correct (VV1-X31-16 found), no false positives, DN correct for all
- Pipe attachments at the contact point: correct 96, wrong 17 (riser-label stubs where the takeoff assigns the
  main DN, see below), not in facit 1
- Physical pipe match per reference measurement (78): full 64, partial 2, miss 12 (was 39 / 6 / 33)
- Length audit: correctly owned 171.6 m (was 92.3), wrongly owned 7.4 m (was 33.0), missed 11.3 m (was 105.1),
  ambiguous near reference 3.0 m, unowned near reference 0.5 m (was 54.2)
- Horizontal total 212.0 m vs 213.4 m of reference markup (-0.63 %), nothing ambiguous, nothing unowned. A
  further 12.2 m of drawn pipe runs inside hatched areas and is reported separately; measuring the reference's own
  polylines shows only 0.25 m of it lies inside hatching, so excluding it is what the takeoff does
- Coverage of the reference markup, sampled every 1 pt: 213.10 m of its 213.38 m is owned and counted, 0.23 m is
  inside hatching and 0.05 m has no primitive within 3 pt. The remaining 1.3 m is run ends, where the reference
  clicks to a leader contact or a fitting centre a point or two beyond where the drawn line stops
- Of the 19 DN boundaries the reference marks, 16 sit exactly (within 0.1 pt) on a leader end mark of the drawing
- Per designation the largest deviation is 1.1 m; about 5 m sits on the other side of a DN boundary on branches
  carrying several size labels, which shifts the split between DN110 and DN75 but not the total
- Risers: 55 counted vs 55 in the reference (150.8 m / 2.8 m per floor); vertical metres need a floor height that
  the drawing does not carry - the application computes them from a user-entered floor height
- Scale: the drawn scale bar is 283.56 pt for 5 m, i.e. exactly 1:50; the label glyph centres implied 1:50.5

| Beteckning | ref H m | ours H m | diff m | in hatch m |
|---|---|---|---|---|
| KV1-X31-16 | 17.4 | 17.10 | -0.25 | 3.49 |
| KV2-X31-16 | 33.3 | 33.11 | -0.22 | 0.00 |
| S1-P2-110 | 9.8 | 10.19 | +0.38 | 2.63 |
| S1-P2-75 | 4.8 | 4.16 | -0.62 | 4.62 |
| S3-P2-160 | 16.9 | 16.83 | -0.04 | 0.00 |
| S3-R8-110 | 59.9 | 59.94 | +0.02 | 1.42 |
| S3-R8-160 | 16.3 | 16.99 | +0.73 | 0.00 |
| S3-R8-75 | 20.9 | 19.81 | -1.12 | 0.00 |
| VV1-X31-16 | 34.1 | 33.92 | -0.22 | 0.00 |
| SUMMA | 213.4 | 212.04 | -1.34 | 12.16 |

Remaining differences: 5.2 m of stubs owned as S3-R8-75 from the first tick after the junction where the takeoff
keeps 110 up to the last tick before the riser (label reading vs takeoff convention); 1.7 m of ambiguous DN
boundary on the S3-R8-160/110 run where two ticks compete; riser counts per system differ where labelled end marks
of the tappvatten bundles are counted as risers (KV2/VV1 7 vs 5) and where seven S3-R8-75 riser marks sit on short
stubs the engine leaves unowned.

## Files

- validation-blind_frozen_87c37c1.json: blind frozen artifacts vs facit
- validation-final_420a617.json: final artifacts vs facit (identical numbers on A)
- Validation inputs (marked PDF, facit xlsx) are kept outside the repository in data/validation_A/ (git-ignored) and are never read by production code (contamination scan PASS).
