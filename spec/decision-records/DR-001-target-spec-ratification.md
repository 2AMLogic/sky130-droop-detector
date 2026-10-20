# DR-001: ratify the target specification

- **Status**: **proposed** — ratified by the operator's approval of the PR
  that lands it (the ratification-via-PR path `sky130-ldo` used for its
  DR-006). Nothing here is binding until that PR merges.
- **Date**: 2026-10-17
- **Author**: Builder agent (drafted per #2)
- **Ratifies against / input to**: #2; gates #3 items 5–8.
- **Supersedes**: none — first decision record in this repo.

## Context

The README carried a draft fallback/target/stretch table. Design work needs a
fixed target to verify against (this repo's CLAUDE.md: verification is the
product; agents do not relax a ratified spec). This record turns the draft
into [`spec/target-spec.md`](../target-spec.md), copies the `sky130-ldo`
interface rows at `aaaae71ee5b9edea017ccb1ccf6cfbd3f5f99f94`, and resolves or
defers the open questions of #2. No schematic, testbench or result exists;
every number is a target.

## Decision

Adopt `spec/target-spec.md` as the proposed spec, with the README's numbers
carried unchanged except the three listed under *Changes to README numbers*.
The three judgment calls below are **recommendations for the operator to
accept or overrule at PR review**.

### (a) Detector supply — recommend the 3.3 V LDO input rail

The decision the detector is built around: the comparator must not slow down
when its headroom shrinks. Powering from the 3.3 V input keeps the reference
and comparator headroom independent of the 1.8 V rail collapsing, and the
output flag stays valid while the rail is down. Cost: 3.3 V exceeds the
1.8 V-class device ratings, so the 3.3 V domain needs `g5v0d10v5`-class
devices (slower, larger) where it touches 3.3 V, and the flag needs a
level-limited driver to a 1.8 V consumer. Residual risk, carried as a
testbench case and not assumed away: a 3.3 V input that itself sags with the
event.

- Rejected: **monitored 1.8 V rail.** Reference and comparator headroom shrink
  with the very droop being detected; fails the central requirement.
- Rejected: **separate rail.** Adds a supply no consumer has declared and an
  integration burden; revisit if the 3.3 V input proves not independent enough.

### (b) Threshold reference — recommend generated in-tree

A reference generated from the 3.3 V supply, with thresholds at fixed
fractions of nominal. No sibling is consumed, so **no `consumes` edge is
added** and none is requested. The LDO's own `VREF` is an unbuilt external
port from `sky130-bandgap`; taking it would make that sibling a dependency.
That edge is an operator decision and is **flagged here, not assumed**.

- Rejected: **sibling reference (bandgap).** Better absolute accuracy is
  plausible, but it needs a `consumes` edge and a block that does not exist
  yet.
- Rejected: **input pin.** Moves the accuracy problem to the integrator and
  leaves the block unverifiable on its own; kept as the stretch alternative.
- Risk handed to design: ±1.5% over PVT without a bandgap is hard. The
  fallback (±3%) exists for that; the target is not relaxed in advance.

### (c) Comparator — recommend continuous-time

A clocked comparator bounds latency by its clock period (a < 5 ns target
needs a > 200 MHz clock and a clock input this block does not otherwise
need) and aliases droops shorter than a period against row 7. A
continuous-time comparator keeps latency independent of any clock. The
`sky130-comparator` clocked latched comparator stays a candidate (e.g. as a
regenerative second stage) and is entered in `reuse.lock.json` as
`status: evaluate`. **It is not adopted here**; adopt it, or record why not,
once it is simulation-validated. Its status, read from that repo's README on
2026-10-20 (not re-measured): schematic designed and laid out with DRC/LVS
evidence; four of five spec rows ratified, including *Decision time vs.
overdrive* at ≤ 1.5 ns at 50 mV overdrive (measured 0.68 ns schematic,
0.53 ns post-layout, `tt`/27 °C); the *Supply / power* row is still DRAFT.
It is a 1.8 V core-device block (`nfet_01v8`/`pfet_01v8`), so under (a) it
could only sit in a 1.8 V-class sub-domain of the detector, not on the
3.3 V rail directly.

- Rejected: **clocked comparator as the front end** (above).

### Open questions from #2

- **Rail model.** Both forms are used (`target-spec.md`, *Rail model*): the
  netlist-derived LDO model is evidence, the behavioural envelope fitted to
  the ratified rows is an assumption, and is labelled so. An ideal step is
  an extra case only.
- **Consumer and flag speed.** Interface is recorded; no consumer is
  declared, so per-consumer latency is **deferred** until one is. The
  < 5 ns target is rationale-sized, not consumer-derived.
- **POR.** Stated in the spec by name: a different block from the POR in
  `sky130-temp-por`.
- **Area.** **Deferred**: no number until a floorplan exists. Not silently
  dropped; it is a row with the deferral recorded.
- **Corner model files.** Named per `sky130-ldo` DR-004 and verified
  against this repo's own pin, which #4 has since landed (`sim/pdk.json`:
  open_pdks `f6eeac7d…`; ngspice 46 in `sim/toolchain.json`). The LDO is
  pinned to a different open_pdks revision (`c6d73a35…`); the spec's *PVT
  corner box* records what is and is not identical between the two.

### Changes to README numbers

1. Threshold levels fixed at 4 / 6 / 9 / 12% below nominal. The README gave
   only a 3–12% range; the positions are mine.
2. Lowest level may not sit below 2% + accuracy: at ±1.5% a 3% level can
   trip at 1.773 V, inside the LDO's ±2% window (≥ 1.764 V), contradicting
   the false-flag row. Hence ≥ 3.5% at target and ≥ 5% for the single-level
   fallback (±3%). The README range is otherwise unchanged.
3. Area and consumer latency added as rows with explicit deferral; the README
   had none.

No number is relaxed.

## Alternatives considered

Per judgment call above. For the table as a whole: ratifying without the
derived immunity floor was rejected because it would ratify a spec whose own
rows conflict.

## Consequences

- Fixes the target for #3 items 5–8. Rows 5 and 6 (accuracy without a
  bandgap, latency from a 3.3 V domain through level limiting) are the
  expected hard rows and are handed to design unresolved.
- Statistical row for `klt yield` evidence: row 5 (threshold accuracy).
- Any finding bearing on the LDO is filed on `sky130-ldo`; none so far.

## Status notes

`proposed` until the operator approves the PR landing it. The three
recommendations in (a)–(c) are the items to rule on. No klayout-tools gap
was met while scoping (documents only, no tool used beyond planning), so
none was filed.
