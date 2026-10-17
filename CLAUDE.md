# sky130-droop-detector — agent instructions

Open-source canary block: a fast supply-droop detector on the SkyWater
sky130 PDK, the companion to `sky130-ldo`, designed and verified by AI
agents.

- **PDK**: SkyWater sky130 (open PDK, google/skywater-pdk). Analog: xschem +
  ngspice. If the flag logic grows past a few cells: cocotb + Icarus, Yosys,
  OpenROAD. Layout, DRC, and LVS through klayout-tools (`klt`).
- **Deciding while the rail collapses is the point, and the risk.** The
  detector must resolve a nanosecond-scale droop while the monitored rail,
  and possibly its own supply, is moving. The reference must not droop with
  the rail, the comparator must not slow down when its headroom shrinks, and
  the glitch filter must not hide a real droop or flag ordinary regulation
  ripple. Which rail powers the detector is the first architectural
  decision; argue it in a decision record. Never verify against an ideal
  stepped source alone — the rail model is part of every testbench.
- **Scope discipline.** The regulator comes from `sky130-ldo`. Do not design
  one here. Take its ratified output behaviour (1.8 V ±2%, 0–50 mA, its load
  transient and C_out/ESR window) as the interface, cite that repo at a
  named commit in `spec/`, and stop. If a finding
  here bears on the LDO (a droop it should not allow, an interface gap),
  file it on `sky130-ldo`. `sky130-comparator` builds a clocked comparator on
  this PDK: record it in `reuse.lock.json`'s `in_tree` ledger with
  `status: evaluate`, and adopt it or record why not once it is
  simulation-validated. The POR in `sky130-temp-por` is a different block;
  say so in the spec by name.
- **Friction protocol (the canary's job)**: every time klayout-tools is
  awkward, missing a capability, or wrong for what you need, file an issue at
  `2AMLogic/klayout-tools` describing the tool gap generically — that tracker
  is scoped to the tool, so keep design-specific detail out of it and describe
  the gap, not the design.
- **Verification is the product**: no claim without a testbench. PVT corners
  on every recorded result; `sim/` results are append-only evidence. Every
  simulated figure is labelled as simulated, with its corner and testbench.
- Spec changes go through `spec/` with a decision record; agents do not relax
  the ratified spec to make results pass.
- **Four thresholds at < 5 ns is the target.** One fixed threshold at < 20 ns
  is the fallback and < 1 ns is a stretch. Do not let the stretch drive the
  comparator architecture before the target closes.
