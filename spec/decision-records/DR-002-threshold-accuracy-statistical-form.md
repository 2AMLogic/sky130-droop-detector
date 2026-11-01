# DR-002: statistical form and trim status of row 5 (threshold accuracy)

- **Status**: **proposed** — becomes ratified when the operator merges the PR carrying it
  (the ratify-by-merge path of DR-001).
- **Date**: 2026-11-01
- **Author**: Doctor agent, addressing the operator's send-back on PR #46 (EE-key review, head `23511f7`).
- **Amends**: [DR-001](DR-001-target-spec-ratification.md) / `spec/target-spec.md` rows 3 and 5. **No number is changed.**

## Context

Row 5 ratified ±1.5 % (target), ±3 % (fallback) and ±0.75 % (stretch), but left
the statistical form of the bound — sigma level, number of draws, negative
control — and whether a trim is allowed to "the row's testbench record". A bar
set later by its own bench is not a ratified bound. `sky130-comparator` and
`sky130-bandgap` both state the form at ratification (e.g. bandgap: untrimmed,
3σ, mismatch MC N ≥ 300 plus process corners).

## Decision

1. **Form.** Row 5 is graded as the **3σ** bound of the trip-point error
   (relative to nominal, per threshold level) from a Monte Carlo combining the
   process corners of the PVT box with device mismatch (`tt_mm`, `ss_mm`,
   `ff_mm`, `sf_mm`, `fs_mm`, and the `mc` process section), **N ≥ 300 draws
   per corner**, with a fixed seed recorded in the result. The same bound
   applies to fallback (3σ ≤ ±3 %) and stretch (3σ ≤ ±0.75 %).
2. **Negative control.** The testbench record commits a control (a deliberately
   offset or mismatched variant) that must *fail* the same grade, so a pass
   cannot come from an inert harness.
3. **Trim.** **Untrimmed** at fallback and target. A trimmed design (fuse, DAC,
   or similar) is a different architecture and needs a superseding DR; it is
   not a quiet route to meet the row. The stretch may be revisited then.
4. **Row 3 wording.** "Derived from the detector supply" is reworded to
   "generated in-tree from the detector supply rail (not ratioed to it)":
   the reference is not supposed to track the supply, and whatever supply
   sensitivity remains is part of this row's error budget, not an exemption.
5. Mismatch MC runs as a `klt sim` / `klt yield` request, not as local loops.

## Not relaxed

No fallback, target or stretch value moves; the form chosen is the
sibling-repo convention, stricter than leaving it open. The grade is fixed
now, before any MC has run, so it cannot be tuned to a result.

## Noted, not part of this change

The committed `threshold_ref` currently tracks the supply (≈0.31 V/V; trip
−4.0 % at 2.97 V in the simulated tt/27 °C `tb_ref_droop` record). That is a
disclosed design-direction fact against row 5, not a failure of the spec, and
is not addressed here.
