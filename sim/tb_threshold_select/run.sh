#!/usr/bin/env bash
# tb_threshold_select: static trip level per select code of design/threshold_ref.spice.
# Single corner (tt, 27 C), local ngspice. Fails closed on a missing/mismatched
# PDK pin, a missing result, or non-monotonic levels. Writes a SIMULATED record.
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
sed "s#__PDK_LIB__#$lib#;s#__NETLIST__#$net#" "$here/tb_threshold_select.spice" > "$work/tb.spice"
ngspice -b -o "$work/ngspice.log" "$work/tb.spice" >/dev/null 2>&1 || {
  echo "FAIL: ngspice exited non-zero; log:" >&2; cat "$work/ngspice.log" >&2; exit 3; }

for k in vref_v iq_ua vtrip_l0 vtrip_l1 vtrip_l2 vtrip_l3; do
  grep -Eq "^RESULT $k = [0-9.eE+-]+" "$work/ngspice.log" || { echo "FAIL: no '$k' result in ngspice log" >&2; cat "$work/ngspice.log" >&2; exit 3; }
done
get() { sed -n "s/^RESULT $1 = //p" "$work/ngspice.log" | head -n1; }
awk -v a="$(get vtrip_l0)" -v b="$(get vtrip_l1)" -v c="$(get vtrip_l2)" -v d="$(get vtrip_l3)" \
  'BEGIN{exit !(a>b && b>c && c>d)}' || { echo "FAIL: levels not strictly decreasing with select code" >&2; exit 3; }

# Model files the netlist pulls in: the lib itself plus the tt-section includes.
cdir="$(dirname "$lib")"
{ echo "$lib"; sed -n '/^\.lib tt$/,/^\.endl tt$/p' "$lib" | sed -n 's/^\.include *//p' | sed "s#^#$cdir/#"; } > "$work/files"
rec="${RECORD:-/dev/stdout}"
nom=(1.728 1.692 1.638 1.584)
{
  echo "label: SIMULATED (not measured); testbench sim/tb_threshold_select/tb_threshold_select.spice; corner tt, 27 C, detector supply 3.3 V"
  echo "stimulus: monitored rail = IDEAL SOURCE (DC sweep); comparator = ideal behavioural source (no offset), so vtrip is the selected tap voltage"
  echo "ngspice: $(ngspice --version | grep -m1 -o 'ngspice-[0-9.]*')"
  echo "klt: $($KLT --version)"
  echo "pdk_sources: $got"
  echo "netlist_sha256: $(sha256sum "$net" | cut -d' ' -f1)  design/threshold_ref.spice"
  echo "model_files_sha256:"
  while read -r f; do [ -r "$f" ] || { echo "FAIL: unreadable model file $f" >&2; exit 2; }
    printf '  %s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "${f#"$root"/}"; done < "$work/files"
  echo "results:"
  echo "  vref_v = $(get vref_v)"
  echo "  iq_ua (whole threshold_ref, code 00, 3.3 V, op) = $(get iq_ua)"
  echo "  target band: +/-27 mV (+/-1.5% of 1.8 V); fallback band: +/-54 mV (+/-3%); no verdict for spec row 5 is made here (single corner, ideal comparator)"
  for i in 0 1 2 3; do
    v="$(get vtrip_l$i)"
    awk -v i="$i" -v v="$v" -v n="${nom[$i]}" 'BEGIN{dm=(v-n)*1e3; printf "  vtrip_l%d = %.5f V; nominal %.3f V; delta %+.2f mV = %+.3f %% of 1.8 V\n", i, v, n, dm, dm/18}'
  done
} > "$work/record"
cat "$work/record" > "$rec"
