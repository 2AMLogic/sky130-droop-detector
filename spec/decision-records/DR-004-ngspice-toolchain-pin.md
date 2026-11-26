# DR-004: ngspice toolchain pin re-anchored to 47

- **Status**: **proposed** — becomes ratified when the operator merges the PR carrying it
  (the ratify-by-merge path of DR-001).
- **Date**: 2026-11-15
- **Author**: Builder agent, implementing issue #87.
- **Amends**: [DR-001](DR-001-target-spec-ratification.md), in its toolchain
  provenance parenthetical. DR-001 and DR-002 continue to define the bounds,
  thresholds and pass criteria.

## Context

At `dde826a`, [the toolchain pin](../../sim/toolchain.json) still said 46.
Of the twelve **local ngspice** benches investigated in #87, nine already
had ngspice-47 records from `1dadde4`. The other three were `smoke`,
`tb_ref_droop` and `tb_threshold_select`. The batch rail-model and Monte
Carlo benches are outside that count. In particular, the row 5 Monte Carlo
record identifies its simulation engine as 46. [Monte Carlo record](../../sim/tb_threshold_mc/records/2026-11-06/record.txt)

### What moved

Issue #87 compares the November 5 ngspice-46 records with ngspice-47p1
reruns of the pre-resize design. Its rerun figures are reported in the issue.
The November 14 ngspice-47 records come from `1dadde4`, which also resized
the comparator and flag logic. The four pairs below have different
`design/detector_top.spice` hashes (`0fca89f6…` and `c6307eb1…`).
Only the issue comparison addresses simulator drift on the earlier design.
[Original run report](https://github.com/2AMLogic/sky130-droop-detector/issues/87)

SIMULATED at tt / 27 °C, with 3.3 V detector supply except for the indicated
2.97 V headroom case. Each pair of record links names the testbench and its
stimulus.

| Testbench and quantity | Nov 5 record, ngspice-46 | #87 rerun, ngspice-47p1 (issue report) | Nov 14 record, ngspice-47 (resized design) | Committed records |
|---|---:|---:|---:|---|
| `tb_false_flag`, W1 settled rail, graded case (V) | 1.7955..1.7995 | 1.8004..1.8006 | 1.8004..1.8006 | [Nov 5](../../sim/tb_false_flag/records/2026-11-05-tb_false_flag-tt.txt) / [Nov 14](../../sim/tb_false_flag/records/2026-11-14-tb_false_flag-tt.txt) |
| `tb_false_flag`, reported load-step excursion (V) | 1.6061..1.9262 | 1.6074..1.9273 | 1.6074..1.9273 | [Nov 5](../../sim/tb_false_flag/records/2026-11-05-tb_false_flag-tt.txt) / [Nov 14](../../sim/tb_false_flag/records/2026-11-14-tb_false_flag-tt.txt) |
| `tb_latency`, row 6 level 2 high start / worst envelope latency (ns) | 4.811 / 4.9594 | 4.810 / 4.9593 | 3.102 / 3.1906 | [Nov 5](../../sim/tb_latency/records/2026-11-05-tb_latency-tt.txt) / [Nov 14](../../sim/tb_latency/records/2026-11-14-tb_latency-tt.txt) |
| `tb_supply_headroom`, level 1 live maximum at 2.97 V, zero sag (V) | 1.6158 | 1.6159 | 1.6447 | [Nov 5](../../sim/tb_supply_headroom/records/2026-11-05-tb_supply_headroom-tt.txt) / [Nov 14](../../sim/tb_supply_headroom/records/2026-11-14-tb_supply_headroom-tt.txt) |
| `tb_filter`, level 0 post-droop maximum (V) | 7.1589E-10 | 7.15889E-10 | −4.12708E-08 | [Nov 5](../../sim/tb_filter/records/2026-11-05-tb_filter-tt.txt) / [Nov 14](../../sim/tb_filter/records/2026-11-14-tb_filter-tt.txt) |

The filter rerun agrees with the earlier value at the earlier record's
printed precision. Its post-resize result has a different sign. Both
committed filter records flag 10 ns and 50 ns droops at every level. The
reported 2 ns stretch case at level 0 changed after the resize.

## Decision

1. **Pin ngspice 47.** The `ngspice` field in `sim/toolchain.json` records the
   simulator version reported for these local runs.
2. **Use the version in the banner.** The 47p1 build prints `ngspice-47`.
   The `pdk_record_header` function extracts `ngspice-[0-9.]*` from
   `ngspice --version`, so the version component of the record stamp is
   `47`. Patch-level build identity and solver configuration cannot be
   recovered from that stamp. [Record header implementation](../../sim/lib/pdk_pin.sh)
3. **Complete the three missing local records.** This PR appends the November
   15 records for [tb_ref_droop](../../sim/tb_ref_droop/records/2026-11-15-tb_ref_droop-tt.txt)
   and [tb_threshold_select](../../sim/tb_threshold_select/records/2026-11-15-tb_threshold_select-tt.txt).
   The [smoke record](../../sim/smoke/records/2026-11-15-smoke-tt.txt) came
   from `402f298` on main. All three stamp `ngspice-47`, and their
   `results:` sections match their respective ngspice-46 predecessors.
4. **Update the prose pins.** DR-001 and the PVT corner box in the target
   spec refer to this decision for ngspice. The target spec also records
   klayout-tools 0.8.0, the existing released signoff pin. Simulation records
   name the klt build used for each run. [Signoff version](../../.github/klt-version)

## Not relaxed

Issue #87 reports that all twelve local benches exited zero and that the
simulator comparison flipped no graded verdict. Both committed W1 rail
ranges lie inside the 1.764..1.836 V normal window, and both records report
zero flags in the graded cases. Both worst envelope latencies meet the
row 6 target of < 5 ns at this corner. The two appended reference records
use an ideal comparator and explicitly withhold a row 5 verdict. DR-001's
limits and DR-002's statistical grading criteria still apply.

## Rejected alternatives

- **Pin `47p1`.** The banner and the local record headers identify version 47.
- **Widen the banner capture.** The banner itself omits the patch suffix.
- **Select ngspice-46 in the bench drivers.** That would reproduce an older
  environment while the nine existing records already identify version 47.
- **Re-run all twelve local benches.** Nine already have records at 47 and
  the other three now have dated records at that version.
- **Treat 47 as a minimum supported version.** A floor answers which future
  simulators a runner may accept. This field identifies the version associated
  with the cited measurements. The sibling project adopted a floor for its
  runner's admission check. [gf180-ldo DR-0043](https://github.com/2AMLogic/gf180-ldo/blob/dd46a607efb88d9f268833da4de2e9d2b78cc0f8/spec/decision-records/DR-0043-ngspice-pin-is-a-major-version-floor-not-an-exact-version.md)
