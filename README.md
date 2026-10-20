# sky130-droop-detector

A fast supply-droop detector on
[SkyWater sky130](https://github.com/google/skywater-pdk), the 130 nm open
PDK — it watches a regulated rail and raises a digital flag within
nanoseconds when the rail falls below a programmed threshold — designed by
AI agents driving [klayout-tools](https://github.com/2AMLogic/klayout-tools)
and the open-source xschem + ngspice flow.

**Status: just opened, specification phase.** Nothing is designed yet.

**Built agent-native.** Every specification, decision record, testbench, and
line of documentation here is produced by AI agents working from a ratified
spec and an append-only evidence trail — not human-authored work that agents
merely assisted with. Verification is the product: every claim traces to a
recorded result under PVT corners. Where the agents hit friction with the
open-source tooling — most often
[klayout-tools](https://github.com/2AMLogic/klayout-tools) — that friction is
filed as a public issue against the tool itself, so the fix benefits everyone
using sky130, not just this repo.

## Why this block, on this PDK

The sibling [sky130-ldo](https://github.com/2AMLogic/sky130-ldo) regulates a
1.8 V rail, and its spec bounds how far that rail may move under a load step.
A droop detector is the companion that *observes* the rail: when a load
transient, a supply glitch or a regulator fault pulls the rail below a safe
level, it tells the digital side fast enough to act — stall a clock, hold a
state machine, or log the event.

It is a good canary because its hard requirement is **speed under the very
condition it detects**. The detector must decide in nanoseconds while the
rail it is watching, and possibly the rail it is running from, is
collapsing. That makes the reference, the comparator and their supply
connections the whole design, and it exercises transient simulation against
a realistic rail model rather than a DC operating point.

## Scope

- **In scope**: the threshold reference (or its interface), a
  continuous-time or fast-clocked comparator, a small threshold-select
  network, a glitch filter and sticky flag, and the testbench rail model
  built from `sky130-ldo`'s ratified output behaviour.
- **Not in scope**: the regulator. The monitored rail comes from
  `sky130-ldo`; this repo specifies its interface to that rail and stops.
- **A different block from the POR in `sky130-temp-por`.** A POR resolves a
  slow power-up and brown-out with a hysteretic trip; this detector resolves
  nanosecond-scale excursions on a rail that is already up. Same family of
  circuits, different block; the spec says so by name.

## Target specification (PROPOSED — see [`spec/target-spec.md`](spec/target-spec.md), issue #2)

All rows are *targets*, not results. The ratified-on-merge source of truth is
[`spec/target-spec.md`](spec/target-spec.md) with
[`DR-001`](spec/decision-records/DR-001-target-spec-ratification.md); this
table must match it. The monitored rail is the `sky130-ldo` output (1.8 V
nominal, ±2% regulation window, 0–50 mA, per that repo's ratified spec at
`aaaae71`).

| Parameter | Fallback | Target | Stretch |
|---|---|---|---|
| Monitored rail | 1.8 V (`sky130-ldo` output) | 1.8 V | any rail 1.6–1.95 V |
| Detector supply | 3.3 V LDO input rail | 3.3 V LDO input rail | — |
| Threshold reference | generated in-tree | generated in-tree, no sibling `consumes` edge | external pin (operator decision) |
| Threshold settings | 1 fixed level, ≥ 5% below nominal | 4 levels, at 4 / 6 / 9 / 12% below nominal | 8 levels, programmable |
| Threshold accuracy over PVT | ±3% of nominal | ±1.5% of nominal | ±0.75% |
| Detection latency (100 mV overdrive) | < 20 ns | < 5 ns | < 1 ns |
| Minimum detected droop width | 50 ns | 10 ns | 2 ns |
| False-flag immunity | no flag for excursions inside the LDO's ±2% window | same, across PVT and noise | — |
| Glitch filter | rejects comparator pulses shorter than a designed width | same; must pass the minimum-width droop, delay counted in latency | — |
| Quiescent current | < 100 µA | < 50 µA | < 20 µA |
| Output | sticky digital flag + clear | same, plus a live (non-sticky) flag | — |
| Area | deferred (no floorplan yet) | deferred | — |
| Signoff | DRC + LVS clean | DRC + LVS clean, post-layout re-verified | — |

Maturity ladder: spec ratified → schematic simulated across PVT against
the rail model → layout DRC/LVS-clean → post-layout re-verification →
shuttle seat → measured silicon. **Current position: spec proposed, awaiting ratification.**

## Tool flow

- **Design and simulation**: xschem + ngspice, sky130 corner models,
  transient benches driven by a rail model derived from `sky130-ldo`.
- **Glitch filter and flag logic**: a handful of cells, simulated in
  ngspice; if it grows beyond that, cocotb + Icarus and Yosys/OpenROAD.
- **Layout, DRC, LVS**: klayout-tools (`klt`).

## Reproduce

Needs `ngspice`, `jq` and [`klt`](https://github.com/2AMLogic/klayout-tools)
(pinned in `sim/toolchain.json`), plus the sky130A PDK at the revision pinned
in `sim/pdk.json`:

```
pip install ciel==2.6.1
ciel enable --pdk-family sky130 -l sky130_fd_pr f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7
sim/smoke/run.sh
```

The `ciel` install line is quoted from `2AMLogic/sky130-comparator#178`. The
runner refuses to simulate if the installed PDK's `SOURCES` differs from the
pin, and prints a record (ngspice version, PDK sha, sha256 of each model
file, simulated results). The committed record is
`sim/smoke/records/2026-10-17-smoke-tt.txt`.

## Repo layout

```
spec/          target spec + decision records
design/        schematics / netlists (xschem)
sim/           testbenches + PVT corner results (ngspice)
verification/  rail-model and flag-logic checks
layout/        GDS + DRC/LVS reports (klayout-tools driven)
measurements/  silicon characterization (empty until tape-out)
```

## T1 evidence

The block's evidence-tier state is graded by `klt signoff`, not hand-read.
The block manifest is
[`manifests/sky130-droop-detector.json`](manifests/sky130-droop-detector.json)
and the committed verdict of record is
[`manifests/sky130-droop-detector.signoff.json`](manifests/sky130-droop-detector.signoff.json).
Pre-spec, every item is honestly `unmet` (`tier: null`). The
`klayout-tools` version is pinned in
[`.github/klt-version`](.github/klt-version); CI fails if the record drifts
from a fresh render. To regenerate it:

```
uvx --from "klayout-tools==$(cat .github/klt-version)" klt signoff --manifest manifests/sky130-droop-detector.json --format json > manifests/sky130-droop-detector.signoff.json
```

(`klt signoff` exits 3 when any item is unmet; that is a valid run.)

## License

Apache License 2.0 — see [LICENSE](LICENSE).
