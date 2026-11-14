# Roadmap

A fast supply-droop detector on SkyWater sky130, the companion to `sky130-ldo`;
this file says where it stands against its ratified spec and what comes next.

Status as of 2026-11-13, `main` @ `4365851`. Every figure below is
**simulated**, quoted from the committed record named beside it. The verdict of
record is `manifests/sky130-droop-detector.signoff.json`, not this file; the
T1 tracker is #3. `WORK_PLAN.md` is a generated, older label snapshot.

## Where it stands

**T1 checklist (`klt signoff`, klt 0.8.0): 2 of 11 met, `tier: null`.**

| Item | State | Evidence or what is missing |
|---|---|---|
| 1 Design sources | met | `evidence/item1.json`; `design/{threshold_ref,comparator,glitch_filter,flag_logic,detector_top}` (PRs #19, #42, #50) |
| 2 Layout | unmet | `layout/` holds only a README; #30 awaits a decision |
| 3 DRC, 4 LVS, 11 Power delivery | unmet | no GDS; #31, #32, #33 wait on #30 |
| 5 Corners, 6 Monte Carlo | unmet | single-corner records only (#34); the Monte Carlo ran and **fails** (#35) |
| 7 Post-layout, 8 Characterization | unmet | #36, #37, behind layout and items 5 and 6 |
| 9 Testbenches shipped | unmet | all benches are on `main`; the inventory and attestation are not (#29) |
| 10 Repo hygiene | met | `evidence/item10.json`, re-checked in CI (PR #41) |

**Spec.** `spec/target-spec.md` and DR-001 were ratified on 2026-10-20 (PR #8).
DR-002 fixes the statistical form of row 5 (3σ, N ≥ 300 per corner, untrimmed,
negative control); it is on `main` and row 5 cites it, but its header still
reads "proposed".

**Benches.** Every spec row 1 to 11 has a committed bench and record (README,
"Reproduce"). All detector-top records are one corner: tt, 27 °C, 3.3 V.

**What the records say about the design** (single corner unless stated):

- Row 5, threshold accuracy: **not met.** `sim/tb_threshold_mc/records/2026-11-06/`
  (seed 20261105, N = 300, `klt yield` status `fail` in all 24 sections). At the
  4% level the corner means run from 1.660 V (`sf_mm`) to 1.833 V (`fs_mm`)
  against 1.728 V ± 27 mV, tt carries a systematic offset of about +19.6 mV,
  and mismatch sigma is about 12.3 mV, so 3σ of mismatch alone is about 37 mV.
  The process spread also exceeds the ±54 mV fallback band, and the reference
  tracks the detector supply: the trip point moves about −4.0% at 2.97 V
  (`sim/tb_ref_droop/records/2026-10-23-tb_ref_droop-tt.txt`).
- Row 6, latency: worst 4.96 ns at 3.3 V, inside the < 5 ns target with almost
  no margin (`sim/tb_latency`). At a 2.97 V supply the same droop takes 7.4 to
  7.8 ns (`sim/tb_supply_headroom`): fallback band only.
- Row 2, supply headroom: 4 of 32 cases do not behave as required; with the
  2.97 V supply sagging a further 0.3 V the flag does not assert. The sag
  depths are the bench's assumption; the spec fixes none.
- Row 11, quiescent current: 51.6 µA at code 00 (fallback band), 37.7 to
  39.4 µA at the other codes (`sim/tb_iq`).
- Rows 7 to 10: the 10 ns width asserts, no false flag, and the filter and
  flag sequence checks pass at this corner; the 2 ns stretch width does not
  assert (`sim/tb_min_width`, `tb_false_flag`, `tb_filter`, `tb_flag_logic`).

## Now

No open issue is ready to draw today: every T1 item issue is blocked or awaits
a decision. These can start today without layout or a batch campaign.

1. **Row 5 error budget.** Split the trip-point error into supply, process,
   mismatch and temperature contributions, per sub-block where the records
   allow, and state how much each must shrink to fit ±27 mV at 3σ.
   Done when a committed note under `design/` gives each contribution with the
   record it comes from, and lists the contributions no record measures yet.
   Issue: none. Blocks: nothing.
2. **Low-supply speed of the comparator path.** Bring latency at a 2.97 V
   supply inside the row 6 target without pushing row 11 further out.
   Done when new dated records for `tb_supply_headroom`, `tb_latency` and
   `tb_iq` are committed from a revised `design/comparator.sch` (netlists and
   item 1 evidence regenerated), or a committed note records the sizings tried
   and the figures they gave. Issue: none. Blocks: nothing.
3. **Bring the README and `design/README.md` up to the tree.** The README
   status paragraph and maturity line still say the comparator, filter and
   flags are not started. Done when both files match the signoff record and
   the signoff CI job passes on regenerated item 10 evidence.
   Issue: none. Blocks: nothing.

## Next

- **Threshold reference, second revision.** A reference that does not track
  the 3.3 V supply and whose process and mismatch spread fits the budget from
  Now 1, still in-tree and untrimmed (row 3, DR-002). Done when
  `tb_ref_droop` and `tb_threshold_accuracy` records at tt show the supply
  step and offset inside that budget. Unblocked by Now 1.
- **Item 6 re-run (#35).** Re-run `sim/tb_threshold_mc` on the revised design;
  the committed record also predates PR #72, so its `ss_mm`, `sf_mm` and
  `fs_mm` negative controls read `not_detected`. Done when `klt yield` passes with every control
  detected. Needs the revised reference and a multi-hour batch run.
- **Item 9 attestation (#29).** The inventory and cold-start wrapper sit on
  branch `feature/issue-29`. Done when `klt signoff --attest 9` writes an
  envelope and item 9 reads `met`. Blocked: `sim/tb_rail_model_check`'s batch
  grid does not collect (see below).
- **Item 5 corner campaign (#34).** One `klt sim` request per row over the
  corner box, binding corner recorded. Parked on #29; its benches are on `main`.
- **Layout per block (#30).** If the split is chosen: `glitch_filter` first,
  each block with its own DRC and LVS report, then top assembly; #31, #32, #33
  and #36 follow.

## Later

- **Adopt `sky130-comparator` or record why not** (`reuse.lock.json`,
  `status: evaluate`). Question first: is it simulation-validated, and does a
  1.8 V core-device stage fit the 3.3 V domain (DR-001 (c))?
- **Row 12, area.** Deferred by DR-001 until a floorplan exists.
- **Tool pin.** CI grades with klt 0.8.0; recent records used 0.9.x development
  clients. Question first: which release carries what the benches rely on?
- **Item 8 report (#37)** after items 5 to 7; stretch rows after the targets.

## Blocked and waiting

- **#30 layout: decision needed.** Six probes of `klt layout-plan` left the
  smallest block unrouted (tool gaps filed as klayout-tools#5093, #5108, #5110,
  #5135, all closed). The options on the issue: split into per-block issues,
  wait for routed mixed-device layout, or rescope to a floorplan-only area.
- **#35 Monte Carlo.** The design does not meet row 5 and the spec is not
  relaxed, so this waits on the reference revision above.
- **#29 attestation.** Waits on a passing batch collect for the rail-model
  grid, or a ruling on how item 9 treats that bench. klayout-tools#4891 may be
  related; the link is unconfirmed.
- **#37: issue body needs restoring.** Its text was replaced by a write-up for
  a different block; the title and its blockers (#34, #35, #36) are right.
- **PR #48** (generated `WORK_PLAN.md`) is far behind `main`; while it is open
  `WORK_LOG.md` is not regenerated. The DR-002 header still reads "proposed".

## Not planned

- A regulator (`sky130-ldo`) or a power-on reset (`sky130-temp-por`).
- A trimmed threshold, a different detector supply, or an external reference
  pin: each needs a superseding decision record first. No ratified row is
  relaxed to make a result pass.
