#!/usr/bin/env bash
# Cold-start entry point for every committed testbench (T1 item 9), one bench at a time.
# Each bench is a single local ngspice process, except tb_rail_model_check, whose 4-point
# netlist-form grid goes to the Spot batch fleet through `klt sim --batch-set`
# (KLT_SIM_BACKEND=batch; never run locally).
# Needs: the pinned PDK (sim/pdk.json "install"), ngspice, klt, jq, python3. Optional env:
# PDK_ROOT (passed to every bench), KLT (default klt).
# Records are NOT written: RECORD is forced to /dev/null so a reproduction run never
# touches the append-only sim/*/records/. Fails on the first bench that exits non-zero.
# Corner / Monte Carlo campaigns are separate (#34, #35); each bench here is one corner.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$here/.."
export RECORD=/dev/null
benches=(
  sim/smoke
  sim/tb_rail_model_check
  sim/tb_supply_headroom
  sim/tb_ref_droop
  sim/tb_threshold_select
  sim/tb_threshold_accuracy
  sim/tb_latency
  sim/tb_min_width
  sim/tb_false_flag
  sim/tb_filter
  sim/tb_flag_logic
  verification/flag_logic
  sim/tb_iq
  sim/tb_comparator
)
for b in "${benches[@]}"; do
  echo "== $b" >&2
  "$root/$b/run.sh" >/dev/null || { echo "FAIL: $b/run.sh exited $?" >&2; exit 1; }
done
echo "all ${#benches[@]} benches ran" >&2
