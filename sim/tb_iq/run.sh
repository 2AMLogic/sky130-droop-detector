#!/usr/bin/env bash
# tb_iq: quiescent detector-supply current of design/detector_top.spice (spec row 11), one
# copy per select code, monitored rail at 1.8 V, flag idle. ONE corner per invocation
# (default tt / 27 C / 3.3 V, local ngspice); PROC / TEMP_C / VSUP select another corner.
# Fails closed on a missing/mismatched PDK pin, a missing result key, or a flag that is
# not idle (live > 0.36 V) in the averaging window. Writes a SIMULATED record.
# Env: PDK_ROOT, KLT (default klt), RECORD (output path, default stdout),
#      PDK_PIN (pin file, default sim/pdk.json; negative control),
#      NEGCTL_DROP=<key> (negative control: delete that RESULT line from the bench),
#      PROC (default tt), TEMP_C (default 27), VSUP (default 3.3).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sim="$here/.."
bench=tb_iq
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

keys="iq_l0_ua iq_l1_ua iq_l2_ua iq_l3_ua idle_max_l0 idle_max_l1 idle_max_l2 idle_max_l3 sticky_max_l0"
require_results "$work/ngspice.log" $keys
for i in 0 1 2 3; do
  awk -v v="$(get idle_max_l$i)" 'BEGIN{exit !(v<0.36)}' || { echo "FAIL: live flag not idle (VOL > 0.36 V) in the averaging window, level $i" >&2; exit 3; }
done
awk -v v="$(get sticky_max_l0)" 'BEGIN{exit !(v<0.36)}' || { echo "FAIL: sticky flag not cleared in the averaging window" >&2; exit 3; }

pdk_model_files "$PROC" "$work/files"
rec="${RECORD:-/dev/stdout}"
{
  echo "label: SIMULATED (not measured); testbench sim/$bench/$bench.spice; corner $PROC, $TEMP_C C, detector supply $VSUP V; one corner"
  echo "stimulus: monitored rail = IDEAL DC SOURCE at 1.8 V (quiescent figure); CLR pulsed once at 1-5 us to clear power-up sticky state; current = mean of -i(Vdd) over 20-40 us, live and sticky idle (< 0.36 V)"
  pdk_record_header netlist_sha256 "$net" design/detector_top.spice
  echo "results:"
  echo "  spec row 11 bands: fallback < 100 uA; target < 50 uA; stretch < 20 uA. Row needs every corner; this record is one corner and makes no row verdict"
  for i in 0 1 2 3; do
    v="$(get iq_l${i}_ua)"
    awk -v i="$i" -v v="$v" 'BEGIN{b=(v<20)?"inside stretch band":(v<50)?"inside target band":(v<100)?"inside fallback band only":"OUTSIDE fallback band"; printf "  iq_code%d = %.3f uA; %s\n", i, v, b}'
  done
} > "$work/record"
cat "$work/record" > "$rec"
