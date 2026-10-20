# Target specification — PROPOSED (ratifies via the PR that lands it)

**Status: proposed.** Ratified by the operator's approval of the PR that lands
[`DR-001`](decision-records/DR-001-target-spec-ratification.md) (the
ratification-via-PR path `sky130-ldo` used for its DR-006). Until that PR
merges, nothing here is binding. Ratification fixes what the **targets**
are; it is not a claim any design meets them — no design exists yet.

Every figure below is a **target, fallback or stretch**, not a result. No
simulated figure appears in this file. Whenever a result is later recorded
it is labelled as simulated, with its corner and testbench, under `sim/`
(append-only).

## Different block from the POR

This block is **not** the power-on-reset in `2AMLogic/sky130-temp-por`. That
POR resolves a slow power-up and brown-out with a hysteretic trip; this
detector resolves nanosecond-scale excursions on a rail that is already up.
Same family of circuits, different block, no shared requirements. Corollary
(see *Output*): while the monitored rail ramps up at enable, it is below
every threshold, so this detector's live flag is asserted by design; it is
not a power-good signal.

## Interface to the monitored rail (from `sky130-ldo`)

The monitored rail is the `sky130-ldo` output. Source for every row:
[`2AMLogic/sky130-ldo@aaaae71ee5b9edea017ccb1ccf6cfbd3f5f99f94`](https://github.com/2AMLogic/sky130-ldo/tree/aaaae71ee5b9edea017ccb1ccf6cfbd3f5f99f94),
`spec/target-spec.md` (headed RATIFIED there; DR-006 is its ratification
record). Rows are copied, not re-derived; the cited commit, not that repo's
`main`, is the reference.

| LDO parameter | Value (verbatim from source) | Source |
|---|---|---|
| Input | 3.3 V ±10% (2.97–3.63 V); `pfet_g5v0d10v5` pass device | `sky130-ldo@aaaae71`, `spec/target-spec.md`, "Input" row, DR-001 |
| Output | 1.8 V ±2% (fixed) | same, "Output" row |
| Load | 0–50 mA | same, "Load" row |
| Load transient | 1↔50 mA step, ~1 µs edges: peak excursion ≤ 150 mV, recover to ±1% in ≤ 20 µs, over the ratified C_out/ESR window | same, "Load transient" row |
| C_out / ESR window | 0.33–4.7 µF, 0–500 mΩ, no minimum ESR, ceramic-stable | same, "Load transient" row note, DR-002 |
| Corner naming | process {tt, ff, ss, fs, sf} bound to the identically-named `.lib` sections of `libs.tech/combined/sky130.lib.spice` | same, "Verification corners", DR-004 |

Derived from these rows (arithmetic, mine, not the LDO's):

- ±2% window = **1.764–1.836 V**.
- Allowed load-transient peak excursion of 150 mV = 8.3% of nominal, i.e. down
  to 1.650 V. A transient that is *compliant* with the LDO spec therefore
  crosses the 4% and 6% levels below even at the worst-case trip point of
  row 5 (1.692 − 0.027 = 1.665 V > 1.650 V). It does **not** reliably cross
  the 9% level: 1.650 V sits 12 mV above the nominal 1.638 V trip, inside the
  ±27 mV row 5 band, so whether a full-size compliant transient flags at 9% is
  design-dependent and is not graded either way. That is intended: the
  detector reports droops the LDO is allowed to produce. It is why the
  false-flag set below stops at the ±2% window and not at the LDO transient.
- The LDO's implementation does not yet meet several of its own ratified
  rows (its own disclosure). This spec binds to the ratified rows as the
  interface; the LDO netlist is used as evidence of what the LDO *does* (see
  *Rail model*), never as proof of what it is allowed to do.

## Target table

| # | Parameter | Fallback | Target | Stretch | Binding conditions | Planned testbench (not yet written) |
|---|---|---|---|---|---|---|
| 1 | Monitored rail | 1.8 V (`sky130-ldo` output) | 1.8 V | any rail 1.6–1.95 V | Interface rows above; rail model = both models in *Rail model* | `sim/tb_rail_model_check` (rail model reproduces the LDO interface rows before any detector row relies on it) |
| 2 | Detector supply | same as target; a different supply architecture needs a superseding DR, not a quiet fallback | 3.3 V LDO input rail (2.97–3.63 V), independent of the monitored rail; 5 V-class devices only where the 3.3 V domain needs them | — | Supply corners 2.97 / 3.3 / 3.63 V; an input-rail sag case is part of the set (below) | `sim/tb_supply_headroom` (flag decision with monitored rail collapsing and the 3.3 V rail at its minimum, and at a sagging minimum) |
| 3 | Threshold reference | generated in-tree | generated in-tree, derived from the detector supply; no sibling `consumes` edge | external pin (needs an operator decision) | Must not move with the monitored rail; PVT per corner box | `sim/tb_ref_droop` (reference vs a rail collapsing to 0.9 V, vs the 3.3 V rail at 2.97 V) |
| 4 | Threshold settings | 1 fixed level, ≥ 5% below nominal (see 5) | 4 levels at **4 / 6 / 9 / 12%** below nominal (1.728 / 1.692 / 1.638 / 1.584 V) | 8 levels, programmable | Select by 2-bit digital input; nominal 1.8 V | `sim/tb_threshold_select` |
| 5 | Threshold accuracy over PVT | ±3% of nominal (±54 mV) | ±1.5% of nominal (±27 mV) | ±0.75% (±13.5 mV) | Full corner box; static trip point, slow rail ramp; MC mismatch on this row. Immunity floor: lowest level ≥ 2% + accuracy below nominal, so 3.5% at target, 5% at fallback | `sim/tb_threshold_accuracy` (corner grid) and `sim/tb_threshold_mc` (device mismatch, `klt yield`) |
| 6 | Detection latency at 100 mV overdrive | < 20 ns | < 5 ns | < 1 ns | Rail edge crossing the selected threshold by 100 mV; latency = threshold crossing to flag at 50% of its swing; glitch-filter delay included; rail from the rail model, not an ideal step alone | `sim/tb_latency` |
| 7 | Minimum detected droop width | 50 ns | 10 ns | 2 ns | Droop of 100 mV overdrive, width measured at the threshold; every level, every corner | `sim/tb_min_width` |
| 8 | False-flag immunity | no flag for excursions inside the LDO ±2% window (1.764–1.836 V) | same, across PVT and noise | — | Waveform set W1–W5 below; zero flags | `sim/tb_false_flag` |
| 9 | Glitch filter | rejects comparator output pulses shorter than a width set in design | same; reject width < row 7 width, delay counted in row 6 | — | The filter must not hide a droop of the row 7 width at any corner | `sim/tb_filter` |
| 10 | Output flags | sticky flag + clear | sticky flag + clear, plus a live (non-sticky) flag | — | See *Output* | `sim/tb_flag_logic`, `verification/flag_logic` |
| 11 | Quiescent current | < 100 µA | < 50 µA | < 20 µA | Detector supply current, all levels enabled, flag idle, every corner | `sim/tb_iq` |
| 12 | Area | not specified here | not specified here | — | **Deferred**: no number until a floorplan exists; DR-001 records the deferral | — |
| 13 | Signoff | DRC + LVS clean | DRC + LVS clean, post-layout re-verified | — | `klt drc`, `klt lvs`, post-layout re-run of rows 5–8 | `layout/` reports, graded through the block manifest `manifests/sky130-droop-detector.json` and its committed `klt signoff` report (#5, landed) |

### False-flag waveform set (row 8)

None of these may flag at any corner. Each is applied with the rail model,
at all four levels.

- **W1** — static rail anywhere in 1.764–1.836 V.
- **W2** — ordinary regulation ripple: ±1% of nominal sinusoid, 1 kHz–10 MHz
  (amplitude chosen so the swing stays inside the ±2% window).
- **W3** — noise: broadband noise on the rail with a 1.8 V ±2% envelope.
- **W4** — slow excursion to the window edge (1.764 V) and back, on the
  load-transient time scale (1 µs edges, recovery ≤ 20 µs).
- **W5** — a fast spike to the window edge (1 ns edges, 5 ns wide; a
  behavioural-envelope case, see *Rail model*), the
  cheap place for a glitch filter to be wrong.

Excursions below the window (the ones that *must* flag) are the row 6/7
sets, plus the LDO's compliant transient down to 1.650 V at the 4% and 6%
levels (at 9% it is inside the row 5 band and not graded; at 12% it must
not flag).

### Output (rows 10, and the consumer interface)

- Live flag: asserted while the rail is below the selected threshold (after
  the filter); deasserts when the rail recovers above it.
- Sticky flag: latched on the first assertion of the live flag; cleared by an
  active-high `CLR` input. A `CLR` while the condition persists does not
  clear it (the latch re-sets).
- Levels: for a 1.8 V CMOS consumer, VOH ≥ 1.44 V and VOL ≤ 0.36 V, **valid
  while the monitored rail is collapsing** (the output is driven from the
  detector supply, with no output that exceeds 1.95 V). Load capacitance is
  an **assumption** (100 fF) until a consumer declares one.
- Enable: while the monitored rail ramps up the live flag is high; the
  consumer masks it at start-up. The sticky flag is cleared once the rail
  is up. This is not a power-good signal (see the POR statement).
- Speed: no consumer is declared. The row 6 target (< 5 ns) is sized so a
  synchronous consumer at 100–200 MHz can act within one or two cycles.
  That is a rationale, not a requirement, and is recorded as such. Per-
  consumer latency is **deferred** (DR-001).

## Rail model

No detector row is verified against an ideal stepped source alone. The
testbench rail has two forms. Each row is graded on the form that can
physically reproduce its stimulus (operator ruling, 2026-10-20, on #8):

1. **Netlist-derived (evidence).** The `sky130-ldo` schematic
   (`design/ldo_3v3in_1v8out.sch`) at the pinned commit, netlisted with
   `klt netlist`, loaded by the ratified C_out/ESR window and a 1↔50 mA load
   step. This is evidence of what that LDO does, including where it misses
   its own spec.
2. **Behavioural envelope (assumption).** A source bounded by the ratified
   rows (peak excursion ≤ 150 mV, ±1% recovery within 20 µs) plus the fast
   edges of W5 and rows 6–7 that the LDO's 1 µs transient does not exercise.
   It is an assumption, not a measurement, and is labelled so wherever used.

Plus an ideal step, as a third, additional case only.

**Which form grades which row.** The netlist-derived model, loaded by the
ratified C_out/ESR window (≥ 0.33 µF, ≤ 500 mΩ) and the ~1 µs load edges,
cannot produce a nanosecond-scale droop: a 50 mA step gives ≈ 25 mV of ESR
step and ΔV = I·t/C ≈ 1.5 mV in 10 ns. So:

- **Netlist-derived model** grades rows 1 and 8 (W1–W4) and the
  compliant-transient must-flag case (4% and 6% levels).
- **Behavioural envelope** (with the fast edges it adds) grades rows 6, 7
  and W5; the ideal step is run alongside as the additional case. These
  rows are therefore graded against an *assumed* stimulus, labelled so in
  their records.
- Rows 2, 3, 5, 9, 10, 11 are supply- or logic-side rows; their rail is
  the netlist-derived model where a rail waveform is needed and the
  behavioural envelope where a fast edge is needed (rows 2 and 9).

## PVT corner box

- Process: tt, ff, ss, fs, sf — the `.lib` sections of the same names in
  `libs.tech/combined/sky130.lib.spice` (DR-004 of `sky130-ldo`).
- Temperature: −40 / 27 / 125 °C.
- Detector supply: 2.97 / 3.3 / 3.63 V. Monitored rail starting point:
  1.764 / 1.8 / 1.836 V. Both vary independently.
- Row 5 adds a device-mismatch Monte Carlo on the local-mismatch sections
  `tt_mm`, `ss_mm`, `ff_mm`, `sf_mm`, `fs_mm` (per-instance `AGAUSS()`
  terms) and the process Monte Carlo section `mc` of the same library.
  All exist in the pinned library: the combined `sky130.lib.spice` installed
  at the pin has sha256 `48de7c67…133c84`
  (`sim/smoke/records/2026-10-17-smoke-tt.txt`), byte-identical to the copy
  `sky130-ldo`'s DR-004 read at its own pin, where those sections are listed
  at lines 730–838 and 1378. Which of the two mechanisms grades row 5, and
  the pass criterion (N draws, sigma), is set by the row's testbench record,
  not here.
- **PDK/ngspice pin: landed, #4.** `sim/pdk.json` pins open_pdks
  `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7` (`sky130A`, installed with
  `ciel`); `sim/toolchain.json` pins ngspice 46, xschem 3.4.7 and
  klayout-tools 0.7.0. Every graded row runs against that pin. Note that
  `sky130-ldo@aaaae71` is pinned to open_pdks
  `c6d73a35f524070e85faff4a6a9eef49553ebc2b` (its `sim/pdk.json`); the
  combined `.lib` file is identical between the two pins but the FET model
  file `continuous/models_fet.spice` is not (sha256 `1adf908f…` at this pin
  vs `18be82d0…` at the LDO's), so the netlist-derived rail model below is
  the LDO netlist simulated under *this* repo's pin — evidence about that
  netlist here, not a re-run of the LDO's own records.
- Corner letters do not predict severity (`sky130-ldo` DR-004 caveat). The
  binding corner is found by measurement per row, never by inference.
- Multi-corner and Monte Carlo runs are submitted as `klt sim` requests
  (corners / `monte_carlo`) and run on the batch fleet, not as local loops.

## Not in this spec

Regulator design (that is `sky130-ldo`); the POR (`sky130-temp-por`);
simulation results; layout. If a finding bears on the LDO it is filed on
`sky130-ldo`.
