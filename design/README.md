# design

- `threshold_ref.sch` — threshold reference and four-level tap network with a
  2-bit select (`s1 s0`: 00 → 4%, 01 → 6%, 10 → 9%, 11 → 12% below 1.8 V,
  i.e. 1.728 / 1.692 / 1.638 / 1.584 V). Generated from the 3.3 V detector
  supply (DR-001 (a)/(b)): a resistor-fed diode-connected `nfet_g5v0d10v5`
  stack, a poly-resistor tap ladder scaled from that reference, and
  `g5v0d10v5` transmission-gate muxes. No device is connected to the monitored
  1.8 V rail. The tap values are scaled at tt / 27 C / 3.3 V only; the
  reference is not compensated for supply or temperature (see the records in
  `sim/tb_ref_droop/records/`).
- `threshold_ref.spice` — committed `klt netlist --block` output. Staleness
  check: `klt netlist design/threshold_ref.sch -o design/threshold_ref.spice
  --block --check --pdk sky130A --rcfile <PDK>/libs.tech/xschem/xschemrc`
  must report `match`.

- `comparator.sch` — continuous-time comparator on the 3.3 V detector supply
  (DR-001 (c)): a resistor-biased NMOS differential pair (`g5v0d10v5`) with a
  PMOS mirror load and two inverter stages. Inputs `vmon` (monitored 1.8 V
  rail) and `vth` (the selected `threshold_ref` tap) go to transistor gates
  only, so no device supply pin connects to the monitored rail and no sense
  network is needed. `flag` is high (from `vdd33`) while `vmon < vth`; the
  glitch filter (#27) is its only load. Pins: `vmon vth vdd33 gnd flag`.
  Resized for spec row 6 at the 2.97 V supply corner (#77, 2026-11-14): tail
  `M2` `mult` 4 -> 6, PMOS mirror `M5`/`M6` W 4 -> 2, second-stage inverter
  `M7`/`M8` W 8/1 -> 4/0.5 (ratio held, so its trip point and therefore the
  comparator's input offset barely move), output inverter `M9`/`M10` W 8/4 ->
  4/2. The input pair `M3`/`M4` (W=4, L=0.5) and the bias leg `R1`/`M1` are
  unchanged. See *Row 6 sizing* below for the measurements behind each change.
- `comparator.spice` — committed `klt netlist --block` output, same staleness
  command as above with `comparator` in place of `threshold_ref`.

- `glitch_filter.sch` — row 9 filter on the 3.3 V detector supply: a poly-resistor
  / MIM-capacitor low-pass (about 4 kohm, about 170 fF) followed by two
  inverters, so a `flag` pulse shorter than the RC trip time never reaches
  the output. Pins: `flag_in vdd33 gnd flag_f`. **Design intent, not
  simulated:** reject width about 0.7 ns and added delay about 0.7 ns (RC to
  the inverter threshold, tt / 27 C / 3.3 V, hand estimate), both far below
  the row 7 width (target 10 ns), so no row 7 droop is hidden; the delay
  comes out of the row 6 (< 5 ns) budget alongside the comparator and
  output-stage delay. Neither figure is graded; `sim/tb_filter` (row 9) and
  `sim/tb_latency` (row 6) own that, over all corners.
- `flag_logic.sch` — row 10 flags on `vdd33`: a set-dominant NAND latch (set =
  filtered live flag, reset = `clr`, so a `clr` while the condition persists
  re-sets it), `live` (follows the filtered flag) and `sticky` outputs, and a
  level limiter (three diode-connected `g5v0d10v5` NFETs set a gate bias, an
  NFET source follower makes a limited `vlim`; the two output inverters pull
  up from `vlim`) so outputs are 1.8 V-class CMOS and cannot exceed 1.95 V
  while the monitored rail is collapsing. Pins: `live_in clr vdd33 gnd live
  sticky`. Design intent only: the `vlim` value is unsimulated across PVT
  and the added bias current (about 1-2 uA) is not yet charged to row 11.
  The output stage's share of the row 6 budget is no longer an estimate:
  **1.242 ns measured** (SIMULATED, tt / 27 C, 2.97 V supply, l0, bench
  `sim/tb_supply_headroom`, pre-resize netlist), which replaces the earlier
  "about 1 ns" scratch probe. The output path was resized for row 6 (#77,
  2026-11-14): input inverter `M5`/`M6` W 4/2 -> 8/4, output inverters
  `M19`/`M21` (PMOS, source `vlim`) W 12 -> 24 and `M20`/`M22` W 2 -> 4, and
  the `vlim` reservoir `C1` 10x10 -> 14x14 um (the reservoir, not the output
  devices, is where most of that gain comes from: the output edge is supplied
  from `C1`, which droops about 275 mV during the edge before `R2`/`M4`
  recharge it). **The limiter string itself (`R1`, `M1`-`M3`, `M4`, `R2`) is
  deliberately untouched, so static `vlim` does not move** — measured
  identical at 1.69708 V at a 3.63 V supply before and after.
- `detector_top.sch` — wires `threshold_ref`, `comparator`, `glitch_filter` and
  `flag_logic`. Pins: `vmon s0 s1 clr vdd33 gnd live sticky`. `vmon` goes
  only to the comparator's gate; `threshold_ref`'s `vref` output is unused at
  the top. `s1 s0` encoding as above.
- `*.sym` — symbols the top schematic instantiates; `xschemrc` puts this
  directory on xschem's symbol path (and sources the PDK's own rc).
- `glitch_filter.spice`, `flag_logic.spice`, `detector_top.spice` — committed
  `klt netlist --block` output (the top netlist includes the sub-blocks).

Staleness check for every schematic (replaces the `--rcfile <PDK>/...` form
above, which cannot resolve the top's sub-symbols): `klt netlist
design/<name>.sch -o design/<name>.spice --block --check --pdk sky130A
--rcfile design/xschemrc` must report `match`. The T1 item 1 inventory is
`attest/item1.json` (evidence `evidence/item1.json`).

Filter and flag-logic benches: `sim/tb_filter`, `sim/tb_flag_logic`, `verification/flag_logic` (see `sim/README.md`); no bench yet for the top at other rows. See the repo README for scope.

## Row 6 sizing at the 2.97 V supply corner (#77, 2026-11-14)

Every figure here is **SIMULATED**, single corner **tt / 27 C**, ngspice-47,
`klt 0.9.2.dev1022`, open_pdks `f6eeac7`. No corner or Monte Carlo verdict is
made; #34 and #35 own those campaigns. The named testbench and supply are given
for each figure.

### What the 2.97 V latency miss actually was

Measured against the pre-resize netlist (`sim/tb_supply_headroom` stimulus,
l0, latency defined as in spec row 6), splitting "less overdrive" from
"weaker bias" by driving each independently:

| supply | rail driven to | effective overdrive | `live` latency | comparator `flag` |
|---|---|---|---|---|
| 3.30 V | 1.628 V (bench) | 100.3 mV | 4.128 ns | 2.217 ns |
| 3.30 V | 1.70112 V | 27.4 mV | 6.121 ns | 4.214 ns |
| 2.97 V | 1.55536 V | 100.0 mV | 4.976 ns | 2.827 ns |
| 2.97 V | 1.628 V (bench) | 27.4 mV | 7.351 ns | 5.206 ns |

`threshold_ref`'s tap moves with the detector supply (`vth` 1.72852 V at 3.3 V
-> 1.65536 V at 2.97 V, -73.2 mV, about 0.24 V/V), while the bench's droop
target is fixed at *nominal* threshold - 100 mV. So at 2.97 V the stimulus
delivers 27.4 mV of real overdrive, not the 100 mV spec row 6 names as its
binding condition. Of the 3.223 ns lost between the first and last rows,
**1.993 ns (62 %) is the shrunken overdrive, 0.848 ns (26 %) is the
comparator's own supply-dependent bias, and 0.382 ns (12 %) is the
interaction.** The reference's supply coefficient, not comparator speed, is
the larger term; it is row 5 / #76 work and is out of scope here.

### The four non-asserting cases are not a level-limiter failure

At a 2.97 V supply sagging 0.3 V to 2.67 V the comparator output never moves
(`flag` max **19.6 uV**), while `vlim` holds at **1.45631 V**, above the
1.44 V VOH floor. The reason is the same reference drift: at 2.67 V the taps
have fallen to 1.57748 V (l0) and 1.46443 V (l3), while the bench drives the
rail only to 1.628 V and 1.484 V respectively — **the rail never crosses the
threshold, so not asserting is correct behaviour for the reference the
comparator is given.** Resizing the comparator or the limiter cannot change
this, and this sizing does not: still 4 of 32 cases, the same four.

### Where the 7.351 ns went (pre-resize, 2.97 V, l0)

| stage | cumulative | share |
|---|---|---|
| first stage to `o1` 50 % | 3.484 ns | 47 % |
| comparator inverter chain to `flag` | 5.206 ns | 23 % |
| glitch filter to `flag_f` | 6.109 ns | 12 % |
| `flag_logic` to `live` | 7.351 ns | 17 % |

The first stage dominated because `o1` is an RC node that must traverse about
1.29 V of the dead zone the 145 mV standing input imposes on it, with only the
small current imbalance a 27 mV overdrive produces. Shrinking the second-stage
inverter **at a fixed W_p/W_n ratio** cuts that node's capacitance without
moving its trip point (and so without moving the comparator's offset), and also
removes the crowbar current it drew with `o1` sitting mid-rail. Raising the
tail buys the rest — measured, with a negative control, in *How the tail
multiplier reaches ngspice* below. The glitch filter is row 9's and was not
touched.

### Sizings tried (spec row 6 target < 5 ns; spec row 11 target < 50 uA)

Latency is `sim/tb_supply_headroom`'s 2.97 V static-supply case at all four
levels; Iq is code 00/01/10/11 at 3.3 V. The committed and chosen rows are from
the committed records named below; the two intermediate rows are from a
single-corner exploration harness, **not** from a committed bench record.

| comparator tail | 2.97 V latency l0..l3 (ns) | 3.3 V worst (ns) | Iq code 00/01/10/11 (uA) | row 6 < 5 ns? | Iq <= 2026-11-05 at every code? |
|---|---|---|---|---|---|
| committed 2026-11-05 (old sizing) | 7.351 / 7.756 / 7.489 / 7.543 | 4.959 | 51.592 / 39.364 / 38.066 / 37.713 | no | baseline |
| `mult`=4, rest as chosen (harness) | 5.342 / 5.385 / 5.428 / 5.459 | 3.624 | 43.599 / 38.761 / 37.938 / 37.665 | **no** | **yes** |
| `mult`=5, rest as chosen (harness) | 4.940 / 4.978 / 5.012 / 5.034 | 3.349 | 45.454 / 41.249 / 40.477 / 40.211 | no (l2, l3) | no |
| **`mult`=6 — chosen** | **4.668 / 4.696 / 4.725 / 4.742** | **3.191** | **47.576 / 43.767 / 43.023 / 42.757** | **yes** | **no (codes 01/10/11)** |

Also tried and rejected: widening the input pair `M3`/`M4` to W=12 made it
*worse* (7.970 ns at 2.97 V l0) — the added capacitance on `o1` and `d1`
outweighs the extra gm. Narrowing only the mirror (`M5`/`M6` W=2) at the old
stage-2 sizing was latency-neutral.

**No sizing in this space satisfies both halves of the criterion.** The chosen
row trades about +4.4 to +5.0 uA at the three non-binding codes for -4.0 uA at
code 00, which is the only code that was over the row 11 target: all four codes
are now inside `< 50 uA`, where before code 00 sat at 51.592 uA. The `mult`=4
row is the alternative that holds every code at or below the 2026-11-05 figures
and misses row 6 at 2.97 V by 0.34 to 0.46 ns.

### How the tail multiplier reaches ngspice (and the control that proves it)

`M2`'s `mult` is the one attribute in this design whose path from schematic to
simulated device is not obvious by eye, so it is recorded here. Reviewing this
by grepping an instance's **first** line will show the multiplier missing and
the tail looking 1:1 with the bias leg — it is not.

`klt netlist` emits a device instance's parameters wrapped onto a `+`
continuation line, and the multiplier lands there, as **both** forms:

```
XM2 tl nb gnd gnd sky130_fd_pr__nfet_g5v0d10v5 L=1 W=2 nf=1 ad=0.58 ... sd=0
+ mult=6 m=6
```

Of the two, **`m=` is the one that acts**: it is ngspice's own subcircuit
multiplier on the `X` instance. The vendor `mult=` is inert for these devices —
`sky130_fd_pr__{n,p}fet_g5v0d10v5` declares `.param ... mult = 1` but never
passes it to the inner MOSFET (no `m = {mult}` on the `m...` line), so a
netlist carrying only `mult=N` would simulate a 1x device. Both forms are
present in every netlist here, so the schematic, the netlist and the simulated
circuit agree; `klt netlist --check` reports `match`, which for this attribute
is correct. Consequences to keep in mind: grep an instance's first line only,
or diff with a `^XM` anchor, and a multiplier change is invisible (the header
line is byte-identical before and after); and the inert `mult=` must not be
read as the acting one. Filed upstream as a generic tool-surface gap
(2AMLogic/klayout-tools#5687).

**Negative control** (SIMULATED, tt / 27 C, ngspice-47, `klt 0.9.2.dev1024`,
open_pdks `f6eeac7`; exploration harness — the chosen sizing with only
`XM2`'s `m=` forced to 1, **not** a committed bench record, and its
`netlist_sha256` therefore does not match `design/detector_top.spice`):

| `XM2` multiplier | 2.97 V latency l0..l3 (ns) | Iq code 00/01/10/11 (uA) |
|---|---|---|
| `mult=6 m=1` (multiplier defeated) | 10.564 / 10.685 / 10.821 / 10.927 | 44.321 / 32.258 / 30.622 / 30.156 |
| `mult=6 m=6` (committed) | 4.668 / 4.696 / 4.725 / 4.742 | 47.576 / 43.767 / 43.023 / 42.757 |

Defeating the multiplier alone costs **5.9 to 6.2 ns** of latency and removes
**11.5 uA** at code 01, so the 6x tail is load-bearing for row 6 and is the
source of the row 11 rise at the three non-binding codes. The converse
control confirms which form acts: `mult=1 m=6` reproduces the committed Iq at
all four codes exactly (47.576 / 43.767 / 43.023 / 42.757 uA), so the vendor
attribute contributes nothing and `m=` does the work.

This also separates the two halves of the Iq change, at a fixed 2.97 V /
3.3 V stimulus:

| step | code 00 | code 01 | code 10 | code 11 |
|---|---|---|---|---|
| 2026-11-05 sizing, tail `m=4` | 51.592 | 39.364 | 38.066 | 37.713 |
| + mirror / stage-2 / output resize (tail still `m=4`) | 43.599 | 38.761 | 37.938 | 37.665 |
| + tail `m=4` -> `m=6` (chosen) | 47.576 | 43.767 | 43.023 | 42.757 |

The resizing takes **-7.99 uA** at code 00 and almost nothing (-0.6 to -0.05 uA)
at the others — the second-stage crowbar it removes is largest at the highest
tap. The tail step then adds **+3.98 to +5.09 uA** at every code. That is the
trade the chosen row makes, and why code 00 falls while 01/10/11 rise.

The `mult`=4 harness row above was re-derived independently on 2026-11-14 at
this sizing: **5.342 / 5.382 / 5.426 / 5.455 ns** and Iq **43.599 / 38.761 /
37.938 / 37.665 uA** — the Iq figures reproduce exactly and the latencies to
within 4 ps of the row as tabulated.

### The 3.63 V supply corner

Spec row 2 names 3.63 V and no committed record covered it, so
`sim/tb_supply_headroom` gained `SUPPLIES_OVERRIDE` / `LEVELS_OVERRIDE` (the
graded default set is unchanged; the record's case total is now computed from
the sets actually run). Record:
`sim/tb_supply_headroom/records/2026-11-14-tb_supply_headroom-tt-3p63V-probe.txt`.

- **Row 10 holds.** Highest output anywhere at 3.63 V, l3 droop: `sticky`
  **1.81181 V** (this sizing) vs **1.80169 V** (pre-resize) — +10 mV, against
  the 1.95 V ceiling, so 138 mV of margin. `live` max 1.80794 V, `voh`
  1.68894 V, latency 2.605 ns. The limiter-loading change does not approach the
  ceiling.
- **A pre-existing row 5 / row 8 problem is exposed at 3.63 V, and is not
  this issue's.** `vth` at code 00 rises to **1.79409 V** at a 3.63 V supply,
  inside the LDO +-2 % window (1.764-1.836 V), so the code-00 trip point sits
  **above** the nominal 1.8 V rail: 1.80929 V with this sizing, **1.81561 V
  before it**. Both assert `live` continuously with the rail at nominal, which
  is why the l0 case of the 3.63 V probe exits 3 (its latency `.meas` finds no
  rising edge — the bench failing closed, correctly). This sizing improves it
  by 6.3 mV and cannot fix it: the cause is `threshold_ref`'s supply
  coefficient. Filed as #83.

### Records superseded by this sizing

`sim/` is append-only, and every record carries the `netlist_sha256` of the
netlist it simulated, so a record whose hash no longer matches
`design/detector_top.spice` is self-evidently superseded. Re-run at this
sizing on 2026-11-14: `tb_supply_headroom`, `tb_latency`, `tb_iq`,
`tb_comparator`, `tb_min_width`, `tb_filter`, `tb_flag_logic`,
`tb_false_flag`, `tb_threshold_accuracy`. **Not** re-run:
`sim/tb_threshold_mc` (12 `klt sim` requests to the batch fleet; Monte Carlo
is out of scope here and belongs to #35), and `tb_ref_droop` /
`tb_threshold_select`, which exercise `threshold_ref.spice` only and are
unaffected.
