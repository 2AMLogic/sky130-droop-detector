#!/usr/bin/env bash
# tb_ref_droop: reference/threshold shift vs a collapsing monitored rail and a sagging detector supply.
# Single corner (tt, 27 C), local ngspice. Fails closed on a missing/mismatched
# PDK pin, or a missing result. Writes a SIMULATED record.
# Env: PDK_ROOT (optional, passed to klt), KLT (default: klt), RECORD (output path),
#      PDK_PIN (pin file, default sim/pdk.json; overridden for negative controls).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sim="$here/.."
. "$sim/lib/pdk_pin.sh"
. "$sim/lib/ngspice_run.sh"
pdk_pin_resolve
net="$sim/../design/threshold_ref.spice"
[ -r "$net" ] || { echo "FAIL: netlist unreadable: $net" >&2; exit 2; }
sim_workdir
sed "s#__PDK_LIB__#$lib#;s#__NETLIST__#$net#" "$here/tb_ref_droop.spice" > "$work/tb.spice"
ngspice_run "$work/tb.spice" "$work/ngspice.log"

require_results "$work/ngspice.log" vref_nom_v vref_shift_rail_mv vref_tran_dev_max_mv vref_tran_dev_min_mv vref_shift_supply_mv \
  vtrip_l0_nom vtrip_l1_nom vtrip_l2_nom vtrip_l3_nom vtrip_l0_rail vtrip_l3_rail vtrip_l0_supply vtrip_l3_supply

pdk_model_files tt "$work/files"
rec="${RECORD:-/dev/stdout}"
nom=(1.728 1.692 1.638 1.584)
lv() { # tag title
  echo "  $2"
  for i in 0 1 2 3; do
    awk -v i="$i" -v v="$(get vtrip_l${i}_$1)" -v n="${nom[$i]}" 'BEGIN{dm=(v-n)*1e3; printf "    vtrip_l%d = %.5f V; nominal %.3f V; delta %+.2f mV = %+.3f %% of 1.8 V\n", i, v, n, dm, dm/18}'
  done
}
{
  echo "label: SIMULATED (not measured); testbench sim/tb_ref_droop/tb_ref_droop.spice; corner tt, 27 C"
  echo "stimulus: IDEAL SOURCES (coupling check only, not the rail-model verdict): monitored rail 1.8 -> 0.9 V (DC and a 5 ns edge); detector supply 3.3 -> 2.97 V (DC)"
  echo "ngspice: $(ngspice --version | grep -m1 -o 'ngspice-[0-9.]*')"
  echo "klt: $($KLT --version)"
  echo "pdk_sources: $got"
  echo "netlist_sha256: $(sha256sum "$net" | cut -d' ' -f1)  design/threshold_ref.spice"
  echo "model_files_sha256:"
  while read -r f; do [ -r "$f" ] || { echo "FAIL: unreadable model file $f" >&2; exit 2; }
    printf '  %s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "${f#"$root"/}"; done < "$work/files"
  echo "results:"
  echo "  vref_nom_v = $(get vref_nom_v)"
  echo "  vref_shift_mv, monitored rail 1.8 -> 0.9 V: DC $(get vref_shift_rail_mv) mV; during 5 ns edge max $(get vref_tran_dev_max_mv) / min $(get vref_tran_dev_min_mv) mV"
  echo "  vref_shift_mv, detector supply 3.3 -> 2.97 V: $(get vref_shift_supply_mv) mV (this stimulus legitimately moves the reference: it is derived from the supply)"
  echo "  target band: +/-27 mV (+/-1.5% of 1.8 V); fallback band: +/-54 mV (+/-3%); no verdict for spec row 5 is made here (single corner, ideal comparator)"
  lv nom "levels at nominal (rail 1.8 V, supply 3.3 V):"
  lv rail "levels with monitored rail at 0.9 V:"
  lv supply "levels with detector supply at 2.97 V:"
} > "$work/record"
cat "$work/record" > "$rec"
