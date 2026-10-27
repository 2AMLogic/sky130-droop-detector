#!/usr/bin/env bash
# tb_comparator: nominal-corner latency / offset / supply current of design/comparator.spice
# at the highest (1.728 V) and lowest (1.584 V) taps. Single corner (tt, 27 C), two local
# ngspice runs. Fails closed on a missing/mismatched PDK pin or a missing result.
# Writes a SIMULATED record.
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
net="$sim/../design/comparator.spice"
[ -r "$net" ] || { echo "FAIL: netlist unreadable: $net" >&2; exit 2; }
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT

taps=(1.728 1.584)
for vth in "${taps[@]}"; do
  sed "s#__PDK_LIB__#$lib#;s#__NETLIST__#$net#;s#__VTH__#$vth#;s#__VLOW__#$(awk -v t="$vth" 'BEGIN{printf "%.3f", t-0.1}')#" "$here/tb_comparator.spice" > "$work/tb_$vth.spice"
  ngspice -b -o "$work/ngspice_$vth.log" "$work/tb_$vth.spice" >/dev/null 2>&1 || {
    echo "FAIL: ngspice exited non-zero at tap $vth; log:" >&2; cat "$work/ngspice_$vth.log" >&2; exit 3; }
  for k in iq_ua vtrip tfull tf50; do
    grep -Eq "^RESULT $k = [0-9.eE+-]+" "$work/ngspice_$vth.log" || {
      echo "FAIL: no '$k' result at tap $vth in ngspice log" >&2; cat "$work/ngspice_$vth.log" >&2; exit 3; }
  done
done
get() { sed -n "s/^RESULT $2 = //p" "$work/ngspice_$1.log" | head -n1; }

cdir="$(dirname "$lib")"
{ echo "$lib"; sed -n '/^\.lib tt$/,/^\.endl tt$/p' "$lib" | sed -n 's/^\.include *//p' | sed "s#^#$cdir/#"; } > "$work/files"
rec="${RECORD:-/dev/stdout}"
{
  echo "label: SIMULATED (not measured); testbench sim/tb_comparator/tb_comparator.spice; corner tt, 27 C, detector supply 3.3 V"
  echo "stimulus: monitored rail = IDEAL SOURCE; comparator only (no glitch filter), 5 fF load on flag; NOT the row 6 grading (that is tb_latency with the rail model and filter)"
  echo "latency stimulus: rail falls from 1.8 V to tap - 100 mV with a 1 ns linear edge; t = 0 is the instant it reaches tap - 100 mV; latency = t = 0 to flag at 50% of its swing (1.65 V)"
  echo "ngspice: $(ngspice --version | grep -m1 -o 'ngspice-[0-9.]*')"
  echo "klt: $($KLT --version)"
  echo "pdk_sources: $got"
  echo "netlist_sha256: $(sha256sum "$net" | cut -d' ' -f1)  design/comparator.spice"
  echo "model_files_sha256:"
  while read -r f; do [ -r "$f" ] || { echo "FAIL: unreadable model file $f" >&2; exit 2; }
    printf '  %s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "${f#"$root"/}"; done < "$work/files"
  echo "results (compared with spec rows 6 and 11 only as figures; row 11 is detector total, this is the comparator part):"
  for vth in "${taps[@]}"; do
    awk -v t="$vth" -v iq="$(get "$vth" iq_ua)" -v vt="$(get "$vth" vtrip)" \
        -v a="$(get "$vth" tfull)" -v b="$(get "$vth" tf50)" 'BEGIN{
      printf "  tap %.3f V: latency = %.3f ns (row 6 target < 5 ns, comparator only); input-referred offset = %+.2f mV (trip %.5f V - tap, slow ramp); supply current idle = %.2f uA (row 11 target < 50 uA, whole detector)\n", t, (b-a)*1e9, (vt-t)*1e3, vt, iq}'
  done
} > "$work/record"
cat "$work/record" > "$rec"
