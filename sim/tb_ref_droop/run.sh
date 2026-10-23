#!/usr/bin/env bash
# tb_ref_droop: reference/threshold shift vs a collapsing monitored rail and a sagging detector supply.
# Single corner (tt, 27 C), local ngspice. Fails closed on a missing/mismatched
# PDK pin, or a missing result. Writes a SIMULATED record.
# Env: PDK_ROOT (optional, passed to klt), KLT (default: klt), RECORD (output path),
#      PDK_PIN (pin file, default sim/pdk.json; overridden for negative controls).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sim="$here/.."
pin="${PDK_PIN:-$sim/pdk.json}"
variant="$(jq -er .variant "$pin")"
want="$(jq -er .sources_line "$pin")"
KLT="${KLT:-klt}"

found="$($KLT pdk find --pdk "$variant" ${PDK_ROOT:+--pdk-root "$PDK_ROOT"} 2>&1)" || {
  echo "FAIL: klt pdk find could not resolve $variant (PDK_ROOT=${PDK_ROOT:-unset}); pin is: $want" >&2
  echo "$found" >&2; exit 2; }
root="$(sed -n 's/^root: //p' <<<"$found")"
src="$root/$variant/SOURCES"
[ -n "$root" ] && [ -s "$src" ] || { echo "FAIL: SOURCES missing or empty at '$src'; pin is: $want" >&2; exit 2; }
got="$(head -n1 "$src")"
[ "$got" = "$want" ] || { echo "FAIL: PDK revision mismatch; pin is '$want', found '$got' in $src" >&2; exit 2; }

lib="$root/$variant/libs.tech/combined/sky130.lib.spice"
[ -r "$lib" ] || { echo "FAIL: model lib unreadable: $lib" >&2; exit 2; }
net="$sim/../design/threshold_ref.spice"
[ -r "$net" ] || { echo "FAIL: netlist unreadable: $net" >&2; exit 2; }
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
sed "s#__PDK_LIB__#$lib#;s#__NETLIST__#$net#" "$here/tb_ref_droop.spice" > "$work/tb.spice"
ngspice -b -o "$work/ngspice.log" "$work/tb.spice" >/dev/null 2>&1 || {
  echo "FAIL: ngspice exited non-zero; log:" >&2; cat "$work/ngspice.log" >&2; exit 3; }

for k in vref_nom_v vref_shift_rail_mv vref_tran_dev_max_mv vref_tran_dev_min_mv vref_shift_supply_mv \
         vtrip_l0_nom vtrip_l1_nom vtrip_l2_nom vtrip_l3_nom vtrip_l0_rail vtrip_l3_rail vtrip_l0_supply vtrip_l3_supply; do
  grep -Eq "^RESULT $k = [0-9.eE+-]+" "$work/ngspice.log" || { echo "FAIL: no '$k' result in ngspice log" >&2; cat "$work/ngspice.log" >&2; exit 3; }
done
get() { sed -n "s/^RESULT $1 = //p" "$work/ngspice.log" | head -n1; }

cdir="$(dirname "$lib")"
{ echo "$lib"; sed -n '/^\.lib tt$/,/^\.endl tt$/p' "$lib" | sed -n 's/^\.include *//p' | sed "s#^#$cdir/#"; } > "$work/files"
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
