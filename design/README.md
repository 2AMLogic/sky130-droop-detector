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

No comparator, filter or flag logic yet. See the repo README for scope.
