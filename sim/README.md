# sim

Testbenches and PVT corner results (ngspice). Results here are append-only
evidence.

- `pdk.json` — pinned PDK revision (open_pdks commit).
- `toolchain.json` — ngspice / xschem / klayout-tools versions.
- `smoke/` — one-command check that the pinned PDK and toolchain run:
  `sim/smoke/run.sh`. It fails closed on a missing or mismatched PDK
  revision. Smoke is tt / 27 C / 1.8 V by design; PVT corners belong to the
  spec benches, not here. Records and negative-control output are in
  `smoke/records/`.
