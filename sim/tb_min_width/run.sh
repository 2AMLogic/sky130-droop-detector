#!/usr/bin/env bash
# tb_min_width: spec row 7, minimum detected droop width of design/detector_top.spice.
# Single corner (tt, 27 C, 3.3 V), one local ngspice process playing 4 levels x widths 2/10/50 ns
# (behavioural-envelope droop to threshold - 100 mV, 1 ns edges down and back, width set at the
# threshold crossings). The live flag must assert (reach the 1.44 V VOH floor). Fails closed on a
# missing/mismatched PDK pin, an ngspice failure, a failed .meas, a stimulus whose measured width
# is off its target, or a missing result key. Writes a SIMULATED record; misses are reported.
# Env: PDK_ROOT (optional, passed to klt), KLT (default: klt), RECORD (output path),
#      PDK_PIN (pin file, default sim/pdk.json; overridden for negative controls),
#      NEGCTL_DROP_KEY (negative control: delete this result key from the log before the check).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sim="$here/.."
. "$sim/lib/pdk_pin.sh"
. "$sim/lib/ngspice_run.sh"
pdk_pin_resolve
net="$sim/../design/detector_top.spice"
[ -r "$net" ] || { echo "FAIL: netlist unreadable: $net" >&2; exit 2; }
sim_workdir
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"   # shared host: keep ngspice modest

# Levels: name nominal-trip select-s0 select-s1 (row 4); widths in ns: row 7 stretch/target/fallback.
LEVELS=("l0 1.728 0 0" "l1 1.692 3.3 0" "l2 1.638 0 3.3" "l3 1.584 3.3 3.3")
WIDTHS=(2 10 50)
keys=()
: > "$work/cases.ctl"
for lv in "${LEVELS[@]}"; do read -r ln lnom s0 s1 <<<"$lv"
  d="$(awk -v l="$lnom" 'BEGIN{printf "%.4f", l-0.1}')"
  for w in "${WIDTHS[@]}"; do
    # width at the crossings = hold + 2 * 1 ns * 0.1 V / (1.8 V - D): solve for the hold
    hold="$(awk -v w="$w" -v d="$d" 'BEGIN{printf "%.4f", w-0.2/(1.8-d)}')"
    name="r7_${ln}_w${w}"
    cat >> "$work/cases.ctl" <<EOF
alter Vs0 dc = $s0
alter Vs1 dc = $s1
alter Vrail pulse = [ 1.8 $d 100n 1n 1n ${hold}n 1u ]
tran 0.02n 300n
meas tran wid trig v(rail) val=$lnom fall=1 targ v(rail) val=$lnom rise=1
meas tran lmax max v(live) from=95n to=300n
meas tran vol find v(live) at=90n
let wid_ns = wid*1e9
echo "RESULT ${name}_wid_ns = \$&wid_ns"
echo "RESULT ${name}_lmax = \$&lmax"
echo "RESULT ${name}_vol = \$&vol"
EOF
    keys+=("${name}_wid_ns" "${name}_lmax" "${name}_vol")
  done
done

sed -e "s#__PDK_LIB__#$lib#;s#__NETLIST__#$net#" -e "/^__CASES__\$/{r $work/cases.ctl" -e "d}" "$here/tb_min_width.spice" > "$work/tb.spice"
ngspice_run "$work/tb.spice" "$work/ngspice.log"
if [ -n "${NEGCTL_DROP_KEY:-}" ]; then sed -i "/^RESULT ${NEGCTL_DROP_KEY} = /d" "$work/ngspice.log"; fi
if grep -Eqi '(^| )(wid|lmax|vol) +.*failed|measure.*failed' "$work/ngspice.log"; then
  echo "FAIL: a .meas failed (no crossing found); log:" >&2; cat "$work/ngspice.log" >&2; exit 3; fi
require_results "$work/ngspice.log" "${keys[@]}"
# Stimulus fidelity: the measured width at the threshold crossings must be within 2 % of the case width.
for lv in "${LEVELS[@]}"; do read -r ln _ <<<"$lv"; for w in "${WIDTHS[@]}"; do
  awk -v m="$(get r7_${ln}_w${w}_wid_ns)" -v w="$w" 'BEGIN{exit !(m>=0.98*w && m<=1.02*w)}' \
    || { echo "FAIL: stimulus r7_${ln}_w${w} measured width $(get r7_${ln}_w${w}_wid_ns) ns is not within 2% of $w ns" >&2; exit 3; }
done; done

pdk_model_files tt "$work/files"
rec="${RECORD:-/dev/stdout}"
asserts() { awk -v m="$1" -v v="$2" 'BEGIN{exit !(m>=1.44 && v<=0.36)}'; }
{
  echo "label: SIMULATED (not measured); testbench sim/tb_min_width/tb_min_width.spice; corner tt, 27 C, detector supply 3.3 V (single corner; no PVT sweep)"
  echo "stimulus: monitored rail = BEHAVIOURAL ENVELOPE (assumption, spec 'Rail model' form 2): 1.8 V -> threshold - 100 mV -> 1.8 V, 1 ns linear edges, width measured at the threshold crossings (stimulus width checked within 2 % of the case width), 1 kohm load"
  echo "measure: 'asserts' = detector_top.live (comparator + glitch filter + flag logic, 100 fF load, assumption) reaches the spec VOH floor of 1.44 V at any time from 95 ns to 300 ns (it may assert after the rail has recovered); live before the droop must be <= 0.36 V (VOL ceiling)"
  echo "ngspice: $(ngspice --version | grep -m1 -o 'ngspice-[0-9.]*')"
  echo "klt: $($KLT --version)"
  echo "pdk_sources: $got"
  echo "netlist_sha256: $(sha256sum "$net" | cut -d' ' -f1)  design/detector_top.spice"
  echo "model_files_sha256:"
  while read -r f; do [ -r "$f" ] || { echo "FAIL: unreadable model file $f" >&2; exit 2; }
    printf '  %s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "${f#"$root"/}"; done < "$work/files"
  echo "results:"
  for lv in "${LEVELS[@]}"; do read -r ln lnom _ <<<"$lv"
    for w in "${WIDTHS[@]}"; do
      lm="$(get r7_${ln}_w${w}_lmax)"; vo="$(get r7_${ln}_w${w}_vol)"
      if asserts "$lm" "$vo"; then a="ASSERTS"; else a="DOES NOT ASSERT"; fi
      printf '  r7 %s (%.3f V) width %2d ns (measured %.3f ns): live max = %.4f V; live before droop = %.4f V; %s\n' "$ln" "$lnom" "$w" "$(get r7_${ln}_w${w}_wid_ns)" "$lm" "$vo" "$a"
    done
  done
  tier=""
  for w in "${WIDTHS[@]}"; do ok=1
    for lv in "${LEVELS[@]}"; do read -r ln _ <<<"$lv"
      asserts "$(get r7_${ln}_w${w}_lmax)" "$(get r7_${ln}_w${w}_vol)" || ok=0; done
    tier="$tier $w:$ok"; done
  echo "all-four-levels assert by width (ns:1=yes):$tier"
  awk -v t="$tier" 'BEGIN{n=split(t,a," "); for(i=1;i<=n;i++){split(a[i],b,":"); y[b[1]]=b[2]}
    print "tier at this single corner: " ((y[2]==1)?"stretch (2 ns) met":(y[10]==1)?"target (10 ns) met; stretch (2 ns) not met":(y[50]==1)?"fallback (50 ns) met; target (10 ns) NOT met":"fallback (50 ns) NOT met");
    print "no verdict for the row over the PVT box is made here (single corner); #34/#35 own the corner campaigns"}'
} > "$work/record"
cat "$work/record" > "$rec"
