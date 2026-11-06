#!/usr/bin/env bash
# tb_latency: spec row 6, detection latency at 100 mV overdrive of design/detector_top.spice.
# Single corner (tt, 27 C, 3.3 V), one local ngspice process playing 4 levels x 3 start points
# (behavioural-envelope rail, 1 ns edges) plus the ideal step alongside. Fails closed on a
# missing/mismatched PDK pin, an ngspice failure, a failed .meas, or a missing result key.
# Writes a SIMULATED record. Latency verdicts are reported, never used to relax the row.
# Env: PDK_ROOT (optional, passed to klt), KLT (default: klt), RECORD (output path),
#      PDK_PIN (pin file, default sim/pdk.json; overridden for negative controls),
#      NEGCTL_DROP_KEY (negative control: delete this result key from the log before the check).
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
net="$sim/../design/detector_top.spice"
[ -r "$net" ] || { echo "FAIL: netlist unreadable: $net" >&2; exit 2; }
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"   # shared host: keep ngspice modest

# Levels: name nominal-trip select-s0 select-s1 (row 4); starts: row 6 start points.
LEVELS=("l0 1.728 0 0" "l1 1.692 3.3 0" "l2 1.638 0 3.3" "l3 1.584 3.3 3.3")
STARTS=("lo 1.764" "nom 1.8" "hi 1.836")
keys=()
: > "$work/cases.ctl"
# case NAME START LEVEL S0 S1 EDGE_SPICE T0_SECONDS
case_text() {
  local name="$1" s="$2" l="$3" s0="$4" s1="$5" edge="$6" t0="$7" d
  d="$(awk -v l="$l" 'BEGIN{printf "%.4f", l-0.1}')"
  cat >> "$work/cases.ctl" <<EOF
alter Vs0 dc = $s0
alter Vs1 dc = $s1
alter Vrail pulse = [ $s $d 100n $edge $edge 60n 1u ]
tran 0.05n 300n
meas tran voh find v(live) at=160n
meas tran vol find v(live) at=90n
let half = (voh+vol)/2
meas tran tl when v(live)=\$&half rise=1 from=95n
let lat = (tl-$t0)*1e9
echo "RESULT ${name}_lat_ns = \$&lat"
echo "RESULT ${name}_voh = \$&voh"
echo "RESULT ${name}_vol = \$&vol"
EOF
  keys+=("${name}_lat_ns" "${name}_voh" "${name}_vol")
}
for lv in "${LEVELS[@]}"; do read -r ln lnom s0 s1 <<<"$lv"
  for st in "${STARTS[@]}"; do read -r sn sv <<<"$st"
    case_text "r6_${ln}_${sn}" "$sv" "$lnom" "$s0" "$s1" 1n 1.01e-7
  done
  case_text "ideal_${ln}" 1.8 "$lnom" "$s0" "$s1" 1p 1.00001e-7
done

sed -e "s#__PDK_LIB__#$lib#;s#__NETLIST__#$net#" -e "/^__CASES__\$/{r $work/cases.ctl" -e "d}" "$here/tb_latency.spice" > "$work/tb.spice"
ngspice -b -o "$work/ngspice.log" "$work/tb.spice" >/dev/null 2>&1 || {
  echo "FAIL: ngspice exited non-zero; log:" >&2; cat "$work/ngspice.log" >&2; exit 3; }
if [ -n "${NEGCTL_DROP_KEY:-}" ]; then sed -i "/^RESULT ${NEGCTL_DROP_KEY} = /d" "$work/ngspice.log"; fi
if grep -Eqi '(^| )(tl|voh|vol) +.*failed|measure.*failed' "$work/ngspice.log"; then
  echo "FAIL: a .meas failed (no crossing found); log:" >&2; cat "$work/ngspice.log" >&2; exit 3; fi
for k in "${keys[@]}"; do
  grep -Eq "^RESULT $k = [0-9.eE+-]+" "$work/ngspice.log" || { echo "FAIL: no '$k' result in ngspice log" >&2; exit 3; }
done
get() { sed -n "s/^RESULT $1 = //p" "$work/ngspice.log" | head -n1; }

cdir="$(dirname "$lib")"
{ echo "$lib"; sed -n '/^\.lib tt$/,/^\.endl tt$/p' "$lib" | sed -n 's/^\.include *//p' | sed "s#^#$cdir/#"; } > "$work/files"
rec="${RECORD:-/dev/stdout}"
{
  echo "label: SIMULATED (not measured); testbench sim/tb_latency/tb_latency.spice; corner tt, 27 C, detector supply 3.3 V (single corner; no PVT sweep)"
  echo "stimulus: monitored rail = BEHAVIOURAL ENVELOPE (assumption, spec 'Rail model' form 2), 1 ns linear fall to threshold - 100 mV, 60 ns hold, 1 kohm load; ideal step (1 ps edge) from 1.8 V shown as the additional case only"
  echo "measure: t=0 is the instant the stimulus reaches threshold - 100 mV (full overdrive), not the threshold crossing; latency = t=0 to detector_top.live at 50% of its swing (swing = live at 90 ns to live at 160 ns, end of hold); comparator + glitch filter + flag logic included; 100 fF load (assumption); a negative latency means live asserted before full overdrive (rail crossed the threshold earlier on the edge)"
  echo "ngspice: $(ngspice --version | grep -m1 -o 'ngspice-[0-9.]*')"
  echo "klt: $($KLT --version)"
  echo "pdk_sources: $got"
  echo "netlist_sha256: $(sha256sum "$net" | cut -d' ' -f1)  design/detector_top.spice"
  echo "model_files_sha256:"
  while read -r f; do [ -r "$f" ] || { echo "FAIL: unreadable model file $f" >&2; exit 2; }
    printf '  %s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "${f#"$root"/}"; done < "$work/files"
  echo "results (latency in ns; voh/vol = live high/low level in V):"
  for lv in "${LEVELS[@]}"; do read -r ln lnom _ <<<"$lv"
    for st in "${STARTS[@]}"; do read -r sn sv <<<"$st"
      printf '  r6 %s (%.3f V) start %s (%.3f V): latency = %.3f ns; voh %.3f V; vol %.4f V\n' "$ln" "$lnom" "$sn" "$sv" \
        "$(get r6_${ln}_${sn}_lat_ns)" "$(get r6_${ln}_${sn}_voh)" "$(get r6_${ln}_${sn}_vol)"
    done
    printf '  ideal step %s (%.3f V) start nom (1.800 V): latency = %.3f ns [additional case only]\n' "$ln" "$lnom" "$(get ideal_${ln}_lat_ns)"
  done
  worst="$(for lv in "${LEVELS[@]}"; do read -r ln _ <<<"$lv"; for sn in lo nom hi; do get "r6_${ln}_${sn}_lat_ns"; done; done | sort -g | tail -n1)"
  echo "worst envelope-rail latency over 4 levels x 3 starts = $worst ns"
  awk -v w="$worst" 'BEGIN{
    printf "tier at this single corner: %s\n", (w<1)?"stretch (< 1 ns) met": (w<5)?"target (< 5 ns) met; stretch (< 1 ns) not met": (w<20)?"fallback (< 20 ns) met; target (< 5 ns) NOT met":"fallback (< 20 ns) NOT met";
    print "no verdict for the row over the PVT box is made here (single corner); #34/#35 own the corner campaigns"}'
} > "$work/record"
cat "$work/record" > "$rec"
