#!/usr/bin/env bash
# tb_filter (spec row 9): the glitch filter rejects comparator-output pulses shorter
# than its designed width and does not hide a droop of the row 7 width.
#   A. design/glitch_filter.spice alone, pulse-width sweep -> reject width bracket.
#   B. design/detector_top.spice at all four select levels, rail = behavioural
#      envelope droops of 50 / 10 / 2 ns width (row 7 fallback / target / stretch).
# Single corner (tt, 27 C, 3.3 V), local ngspice (one corner is not a grid; PVT
# corners are #34/#35). Fails closed on a missing/mismatched PDK pin, a missing
# result, or a failed bound. Writes a SIMULATED record.
# Cold start: a fresh clone needs only the pinned PDK (sim/pdk.json install line),
# ngspice, klt, jq and awk; no state carries between runs.
# Env: PDK_ROOT (optional), KLT (default: klt), RECORD (output path, default stdout),
#      PDK_PIN (pin file, default sim/pdk.json; overridden for negative controls).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sim="$here/.."
. "$sim/lib/pdk_pin.sh"
. "$sim/lib/ngspice_run.sh"
pdk_pin_resolve
fnet="$sim/../design/glitch_filter.spice"; tnet="$sim/../design/detector_top.spice"
for n in "$fnet" "$tnet"; do [ -r "$n" ] || { echo "FAIL: netlist unreadable: $n" >&2; exit 2; }; done
sim_workdir

fail3() { echo "FAIL: $1" >&2; [ -n "${2:-}" ] && cat "$2" >&2; exit 3; }
runsim() { NGSPICE_CTX="($1)" ngspice_run "$1" "$2"; }   # deck log

# ---- A. pulse-width sweep on the filter alone ------------------------------------
# widths in ns, one per line
pulse_deck() { # widths-file tag
  local pwl="0 0" meas="" t=50 i=0 w
  while read -r w; do
    pwl="$pwl $(awk -v t=$t -v w=$w 'BEGIN{printf "%.4fn 0 %.4fn 3.3 %.4fn 3.3 %.4fn 0", t, t+0.05, t+w, t+w+0.05}')"
    meas="$meas
meas tran pk$i max v(out) from=$(awk -v t=$t 'BEGIN{printf "%.4fn", t-1}') to=$(awk -v t=$t -v w=$w 'BEGIN{printf "%.4fn", t+w+30}')
echo \"RESULT pk$i = \$&pk$i\""
    t=$(awk -v t=$t 'BEGIN{print t+40}'); i=$((i+1))
  done < "$1"
  sed "s#__PDK_LIB__#$lib#;s#__NETLIST__#$fnet#;s#__PWL__#$pwl#;s#__TSTOP__#${t}n#" "$here/tb_filter_pulse.spice" |
    awk -v m="$meas" '{ if ($0=="__MEAS__") print m; else print }' > "$work/$2.sp"
  echo "$i"
}
awk 'BEGIN{for(w=0.1;w<=3.001;w+=0.1)printf "%.2f\n",w; print 5; print 10; print 50}' > "$work/w1"
n1="$(pulse_deck "$work/w1" a1)"
runsim "$work/a1.sp" "$work/a1.log"
# bracket: largest rejected (pk < 1.65) and smallest passed width within the sweep
bracket() { # widths log n
  awk -v lg="$2" -v n="$3" 'BEGIN{
    while((getline l < ARGV[1])>0){w[k++]=l} 
    while((getline l < lg)>0){ if(l ~ /^RESULT pk/){split(l,a," "); sub("pk","",a[2]); p[a[2]]=a[4]} }
    lo=-1; hi=-1
    for(i=0;i<n;i++){ if(!(i in p)){print "MISSING"; exit} 
      if(p[i]<1.65){lo=i} else if(hi<0){hi=i} }
    print w[lo], p[lo], w[hi], p[hi] }' "$1" /dev/null
}
for i in $(seq 0 $((n1-1))); do require_results "$work/a1.log" "pk$i"; done
read -r wrej pkrej wpas pkpas <<<"$(bracket "$work/w1" "$work/a1.log" "$n1")"
[ "${wrej:-}" != "MISSING" ] && [ -n "$wrej" ] && [ "$wrej" != "-1" ] || fail3 "no rejected pulse in the sweep (filter passes everything)" "$work/a1.log"
awk -v r="$wrej" -v p="$wpas" 'BEGIN{exit !(p>r)}' || fail3 "no passed pulse above the rejected width in the sweep"
# refine between the coarse bracket (0.01 ns steps)
awk -v a="$wrej" -v b="$wpas" 'BEGIN{for(w=a;w<=b+1e-9;w+=0.01)printf "%.3f\n",w}' > "$work/w2"
n2="$(pulse_deck "$work/w2" a2)"
runsim "$work/a2.sp" "$work/a2.log"
for i in $(seq 0 $((n2-1))); do require_results "$work/a2.log" "pk$i"; done
read -r wrej pkrej wpas pkpas <<<"$(bracket "$work/w2" "$work/a2.log" "$n2")"
[ "$wrej" != "MISSING" ] && [ -n "$wrej" ] && [ -n "$wpas" ] || fail3 "refined sweep has no bracket" "$work/a2.log"
# the refined bracket's two ends (and the first coarse width above the reject width
# that passes) are the "just below" / "just above" points; "at" is the bracket itself.
# pulses of 5, 10, 50 ns (tail of w1) must pass
for k in $((n1-3)) $((n1-2)) $((n1-1)); do
  v="$(result_of "$work/a1.log" "pk$k")"
  awk -v v="$v" 'BEGIN{exit !(v>=1.65)}' || fail3 "pulse #$k of the wide set (index $k) did not pass the filter: pk=$v V" "$work/a1.log"
done

# ---- B. detector_top, rail-model droops at four levels ----------------------------
thr=(1.728 1.692 1.638 1.584)
widths=(50 10 2)
for lvl in 0 1 2 3; do
  s0=$(( lvl & 1 ? 3 : 0 )); s1=$(( lvl & 2 ? 3 : 0 ))
  [ "$s0" = 3 ] && s0=3.3; [ "$s1" = 3 ] && s1=3.3
  pwl="0 1.8"; meas=""; i=0; t0=100
  for w in "${widths[@]}"; do
    read -r p m < <(awk -v thr="${thr[$lvl]}" -v w="$w" -v t0="$t0" -v i="$i" 'BEGIN{
      D=thr-0.1; f=(1.8-thr)/(1.8-D); h=w-2*(1-f); if(h<0){print "NEG"; exit}
      te=t0+2+h;
      printf "%.4fn_1.8_%.4fn_%.4f_%.4fn_%.4f_%.4fn_1.8 ", t0, t0+1, D, t0+1+h, D, te;
      printf "pre%d:%.4f:%.4f pk%d:%.4f:%.4f end%d:%.4f:%.4f\n", i, t0-50, t0, i, t0, te+40, i, te+80, te+200 }')
    [ "$p" != NEG ] || { echo "FAIL: width $w ns unreachable at 1 ns edges" >&2; exit 3; }
    pwl="$pwl $(tr '_' ' ' <<<"$p")"
    for spec in $m; do
      IFS=: read -r nm a b <<<"$spec"
      case "$nm" in pre*|pk*|end*) fn=max;; esac
      meas="$meas
meas tran $nm max v(live) from=${a}n to=${b}n
echo \"RESULT l${lvl}_$nm = \$&$nm\""
    done
    t0=$((t0+300)); i=$((i+1))
  done
  sed "s#__PDK_LIB__#$lib#;s#__NETLIST__#$tnet#;s#__S0__#$s0#;s#__S1__#$s1#;s#__PWL__#$pwl#;s#__TSTOP__#${t0}n#" "$here/tb_filter_droop.spice" |
    awk -v m="$meas" '{ if ($0=="__MEAS__") print m; else print }' > "$work/b$lvl.sp"
  runsim "$work/b$lvl.sp" "$work/b$lvl.log"
  for j in 0 1 2; do for q in pre pk end; do require_results "$work/b$lvl.log" "l${lvl}_$q$j"; done; done
done

# ---- grade -----------------------------------------------------------------------
# Row 9 bounds this bench grades (tt / 27 C / 3.3 V only):
#   reject width exists, below 10 ns (row 7 target width);
#   5/10/50 ns comparator-output pulses pass the filter;
#   the live flag asserts (peak >= 1.44 V, the 1.8 V CMOS VOH) for the 50 ns and 10 ns
#   droops at every level, and is <= 0.36 V (VOL) before each droop and after it.
#   The 2 ns droop (row 7 stretch) is REPORTED, not graded.
awk -v r="$wrej" 'BEGIN{exit !(r+0<10)}' || fail3 "reject width $wrej ns is not below the row 7 target width (10 ns)"
for lvl in 0 1 2 3; do
  for j in 0 1; do
    pk="$(result_of "$work/b$lvl.log" "l${lvl}_pk$j")"
    awk -v v="$pk" 'BEGIN{exit !(v>=1.44)}' || fail3 "level $lvl droop #$j: live flag peak $pk V < 1.44 V (droop hidden)" "$work/b$lvl.log"
  done
  for j in 0 1 2; do for q in pre end; do
    v="$(result_of "$work/b$lvl.log" "l${lvl}_$q$j")"
    awk -v v="$v" 'BEGIN{exit !(v<=0.36)}' || fail3 "level $lvl droop #$j: live flag $q = $v V > 0.36 V (false flag / stuck)" "$work/b$lvl.log"
  done; done
done

# ---- record -----------------------------------------------------------------------
pdk_model_files tt "$work/files"
rec="${RECORD:-/dev/stdout}"
{
  echo "label: SIMULATED (not measured); testbench sim/tb_filter/tb_filter_pulse.spice and tb_filter_droop.spice; corner tt, 27 C, detector supply 3.3 V (single corner; PVT is #34/#35)"
  echo "stimulus A: ideal 0->3.3 V pulses, 0.05 ns edges, width at 50 % (stands in for comparator output); stimulus B: rail = BEHAVIOURAL ENVELOPE (assumption, spec 'Rail model' form 2): PWL droop to threshold - 100 mV, 1 ns linear edges, width at the threshold crossings, +10 mV 20 MHz ripple in series; 100 fF on live"
  echo "ngspice: $(ngspice --version | grep -m1 -o 'ngspice-[0-9.]*')"
  echo "klt: $($KLT --version)"
  echo "pdk_sources: $got"
  echo "netlist_sha256: $(sha256sum "$fnet" | cut -d' ' -f1)  design/glitch_filter.spice"
  echo "netlist_sha256: $(sha256sum "$tnet" | cut -d' ' -f1)  design/detector_top.spice"
  echo "model_files_sha256:"
  while read -r f; do [ -r "$f" ] || { echo "FAIL: unreadable model file $f" >&2; exit 2; }
    printf '  %s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "${f#"$root"/}"; done < "$work/files"
  echo "results A (filter alone, pass = output peak >= 1.65 V):"
  echo "  widest rejected pulse = $wrej ns (output peak $pkrej V)"
  echo "  narrowest passed pulse = $wpas ns (output peak $pkpas V); sweep resolution 0.01 ns, so reject width is in ($wrej, $wpas] ns"
  echo "  just below / at / just above the reject width: $wrej / bracket / $wpas ns"
  echo "  5, 10, 50 ns pulses: output peaks $(result_of "$work/a1.log" "pk$((n1-3))") / $(result_of "$work/a1.log" "pk$((n1-2))") / $(result_of "$work/a1.log" "pk$((n1-1))") V (all pass)"
  echo "  graded: reject width < 10 ns (row 7 target): $wrej ns -> ok"
  echo "results B (detector_top; live flag peak in V over each droop; 50 / 10 / 2 ns widths; VOH bound 1.44 V, VOL bound 0.36 V):"
  for lvl in 0 1 2 3; do
    echo "  level $lvl (threshold ${thr[$lvl]} V): peak $(result_of "$work/b$lvl.log" "l${lvl}_pk0") / $(result_of "$work/b$lvl.log" "l${lvl}_pk1") / $(result_of "$work/b$lvl.log" "l${lvl}_pk2") V; pre-droop max $(result_of "$work/b$lvl.log" "l${lvl}_pre0") V; post-droop max $(result_of "$work/b$lvl.log" "l${lvl}_end0") V"
  done
  for lvl in 0 1 2 3; do
    awk -v v="$(result_of "$work/b$lvl.log" "l${lvl}_pk2")" -v l="$lvl" 'BEGIN{printf "  2 ns droop (row 7 stretch), level %d: %s\n", l, (v>=1.44 ? "flagged" : "NOT flagged (stretch width not met at this corner)")}'
  done
  echo "  graded: 50 ns and 10 ns droops flag at all four levels; no flag before/after. 2 ns (row 7 stretch) is reported only."
  echo "  no verdict for spec row 9 over PVT is made here"
} > "$work/record"
cat "$work/record" > "$rec"
