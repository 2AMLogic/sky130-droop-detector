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
  A scratch single-corner probe suggested the output stage costs
  about 1 ns, so the row 6 target (< 5 ns) is tight with the comparator
  (see `sim/tb_comparator/records/`); recorded as a risk for `sim/tb_latency`,
  not a result.
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

No testbench exists yet for the filter, flag logic or top. See the repo README for scope.
