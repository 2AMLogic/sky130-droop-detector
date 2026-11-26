#!/usr/bin/env bash
# Cold-start entry point for the testbenches declared in sim/inventory.json (T1 item 9),
# one bench at a time. The bench list is the inventory's `testbenches`, with sim/smoke
# first so its fast PDK/ngspice check fails before the longer benches start; an
# inventory that is missing, malformed or empty stops the run before any bench is
# dispatched (exit 2).
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
inv="$here/inventory.json"
[ -r "$inv" ] || { echo "FAIL: testbench inventory unreadable: $inv" >&2; exit 2; }
raw="$(jq -er '
  (.testbenches | select(type == "array" and length > 0 and all(type == "string" and length > 0))) as $tb
  | ($tb | map(select(. == "sim/smoke/run.sh")))
    + ($tb | map(select(. != "sim/smoke/run.sh")))
  | .[]
' "$inv")" || { echo "FAIL: could not parse testbenches from $inv" >&2; exit 2; }
mapfile -t benches <<<"$raw"
for b in "${benches[@]}"; do
  echo "== ${b%/run.sh}" >&2
  "$root/$b" >/dev/null || { echo "FAIL: $b exited $?" >&2; exit 1; }
done
echo "all ${#benches[@]} benches ran" >&2
