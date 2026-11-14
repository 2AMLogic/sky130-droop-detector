#!/usr/bin/env bash
# tb_threshold_accuracy: static trip point per select code of design/detector_top.spice
# (spec row 5, corner-grid half): real reference + comparator + filter + flag logic, slow
# monitored-rail ramp. ONE corner per invocation (default tt / 27 C / 3.3 V, local ngspice);
# PROC / TEMP_C / VSUP select another corner so the #34 campaign can drive this bench.
# Fails closed on a missing/mismatched PDK pin, a missing result key, a flag that is not
# idle at the start of the ramp, or levels that are not strictly decreasing with the code.
# Writes a SIMULATED record. Device-mismatch Monte Carlo is NOT here (tb_threshold_mc, #35).
# Env: PDK_ROOT, KLT (default klt), RECORD (output path, default stdout),
#      PDK_PIN (pin file, default sim/pdk.json; negative control),
#      NEGCTL_DROP=<key> (negative control: delete that RESULT line from the bench),
#      PROC (default tt), TEMP_C (default 27), VSUP (default 3.3).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sim="$here/.."
bench=tb_threshold_accuracy
PROC="${PROC:-tt}"; TEMP_C="${TEMP_C:-27}"; VSUP="${VSUP:-3.3}"
. "$sim/lib/pdk_pin.sh"
. "$sim/lib/ngspice_run.sh"
pdk_pin_resolve
net="$sim/../design/detector_top.spice"
[ -r "$net" ] || { echo "FAIL: netlist unreadable: $net" >&2; exit 2; }
sim_workdir
sed "s#__PDK_LIB__#$lib#;s#__NETLIST__#$net#;s#__PROC__#$PROC#;s#__TEMP__#$TEMP_C#;s#__VSUP__#$VSUP#" \
  "$here/$bench.spice" > "$work/tb.spice"
if [ -n "${NEGCTL_DROP:-}" ]; then sed -i "/RESULT $NEGCTL_DROP =/d" "$work/tb.spice"; fi
ngspice_run "$work/tb.spice" "$work/ngspice.log"

keys="vtrip_l0 vtrip_l1 vtrip_l2 vtrip_l3 idle_max_l0 idle_max_l1 idle_max_l2 idle_max_l3"
require_results "$work/ngspice.log" $keys
for i in 0 1 2 3; do
  awk -v v="$(get idle_max_l$i)" 'BEGIN{exit !(v<0.36)}' || { echo "FAIL: live flag not idle (VOL > 0.36 V) before the ramp, level $i" >&2; exit 3; }
done
awk -v a="$(get vtrip_l0)" -v b="$(get vtrip_l1)" -v c="$(get vtrip_l2)" -v d="$(get vtrip_l3)" \
  'BEGIN{exit !(a>b && b>c && c>d)}' || { echo "FAIL: levels not strictly decreasing with select code" >&2; exit 3; }

pdk_model_files "$PROC" "$work/files"
rec="${RECORD:-/dev/stdout}"
nom=(1.728 1.692 1.638 1.584)
{
  echo "label: SIMULATED (not measured); testbench sim/$bench/$bench.spice; corner $PROC, $TEMP_C C, detector supply $VSUP V; one corner, no Monte Carlo"
  echo "stimulus: monitored rail = IDEAL SOURCE, 1.8 -> 1.55 V linear over 250 us (1 mV/us, static trip point); real design/detector_top.spice; trip = vmon where live crosses 0.9 V"
  pdk_record_header netlist_sha256 "$net" design/detector_top.spice
  echo "results:"
  echo "  target band: +/-27 mV (+/-1.5% of 1.8 V); fallback band: +/-54 mV (+/-3%); immunity floor: highest level must sit below the 1.764 V window edge (3.5% below nominal at target)"
  echo "  no verdict for spec row 5 is made here: one corner, untrimmed, no mismatch Monte Carlo (tb_threshold_mc, #35)"
  for i in 0 1 2 3; do
    v="$(get vtrip_l$i)"
    awk -v i="$i" -v v="$v" -v n="${nom[$i]}" 'BEGIN{dm=(v-n)*1e3; a=dm<0?-dm:dm; b=(a<=27)?"inside target band":(a<=54)?"inside fallback band only":"OUTSIDE fallback band";
      printf "  vtrip_l%d = %.5f V; nominal %.3f V; delta %+.2f mV = %+.3f %% of 1.8 V; %s\n", i, v, n, dm, dm/18, b}'
  done
  awk -v v="$(get vtrip_l0)" 'BEGIN{m=(1.764-v)*1e3; printf "  immunity: highest level (code 00) trips at %.5f V, %+.2f mV below the 1.764 V window edge; %s\n", v, m, (m>0)?"margin positive at this corner":"NO MARGIN: would flag inside the LDO window"}'
} > "$work/record"
cat "$work/record" > "$rec"
