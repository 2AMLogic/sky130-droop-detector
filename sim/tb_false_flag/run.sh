#!/usr/bin/env bash
# tb_false_flag: spec row 8, false-flag immunity. design/detector_top.spice at all four
# select codes sees the waveform set W1-W5 inside the LDO +-2 % window (1.764-1.836 V);
# zero live/sticky flags is required. Two rail forms (spec "Rail model"):
#   envelope (ASSUMPTION): W1-W5, W5 also as an ideal step (additional case)
#   netlist-derived (EVIDENCE): the sky130-ldo netlist under a 1<->50 mA load step; the
#     settled W1 level is graded; the load-step excursion is REPORTED only (the LDO model
#     itself leaves the window there, so a flag is not a false flag).
# ONE corner (default tt / 27 C / 3.3 V), two sequential local ngspice runs (single unit,
# not a grid). Fails closed on a missing/mismatched PDK pin, a missing result key, or any
# flag in a graded case (exit 4, after writing the record). Writes a SIMULATED record.
# Env: PDK_ROOT, KLT (default klt), RECORD (output path, default stdout),
#      PDK_PIN (negative control: pin file), NEGCTL_DROP=<key> (negative control: delete
#      that RESULT line), NEGCTL_MV=<mV> (negative control: push W4 that far below the
#      window so the detector must flag), PROC / TEMP_C / VSUP (corner, default tt/27/3.3).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sim="$here/.."
bench=tb_false_flag
PROC="${PROC:-tt}"; TEMP_C="${TEMP_C:-27}"; VSUP="${VSUP:-3.3}"
NEGCTL_MV="${NEGCTL_MV:-0}"
export OMP_NUM_THREADS=1
. "$sim/lib/pdk_pin.sh"
pdk_pin_resolve
net="$sim/../design/detector_top.spice"
[ -r "$net" ] || { echo "FAIL: netlist unreadable: $net" >&2; exit 2; }
ldo="$sim/tb_rail_model_check/ldo_3v3in_1v8out.spice"
[ -r "$ldo" ] || { echo "FAIL: LDO netlist unreadable: $ldo" >&2; exit 2; }
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT

subst() { sed "s#__PDK_LIB__#$lib#;s#__NETLIST__#$net#;s#__LDO__#$ldo#;s#__PROC__#$PROC#;s#__TEMP__#$TEMP_C#;s#__VSUP__#$VSUP#" "$1"; }
cases="$(python3 -I "$here/gen_envelope_ff.py" "$work/env.raw" "$NEGCTL_MV")"
subst "$work/env.raw" > "$work/env.spice"
subst "$here/tb_false_flag_netlist.spice" > "$work/net.spice"
if [ -n "${NEGCTL_DROP:-}" ]; then sed -i "/RESULT $NEGCTL_DROP =/d" "$work/env.spice" "$work/net.spice"; fi
for leg in env net; do
  ngspice -b -o "$work/$leg.log" "$work/$leg.spice" >/dev/null 2>&1 || {
    echo "FAIL: ngspice ($leg leg) exited non-zero; log:" >&2; tail -40 "$work/$leg.log" >&2; exit 3; }
done

need() { grep -Eq "^RESULT $2 = [0-9.eE+-]+" "$work/$1.log" || { echo "FAIL: no '$2' result in the $1 leg" >&2; tail -40 "$work/$1.log" >&2; exit 3; }; }
get() { sed -n "s/^RESULT $2 = //p" "$work/$1.log" | head -n1; }
for c in $cases; do
  need env "${c}_vmin"; need env "${c}_vmax"
  for i in 0 1 2 3; do need env "${c}_live_l$i"; done
done
for i in 0 1 2 3; do need env "sticky_l$i"; need net "net_w1_live_l$i"; need net "net_w1_sticky_l$i"; need net "net_w4_live_l$i"; done
need net net_w1_vmin; need net net_w1_vmax; need net net_w4_vmin; need net net_w4_vmax

pdk_model_files "$PROC" "$work/files"
rec="${RECORD:-/dev/stdout}"
bad=0
{
  echo "label: SIMULATED (not measured); testbench sim/$bench/ (gen_envelope_ff.py + tb_false_flag_netlist.spice); corner $PROC, $TEMP_C C, detector supply $VSUP V; one corner"
  echo "stimulus: rail model, NOT an ideal source alone. envelope form = ASSUMPTION (behavioural envelope, spec \"Rail model\" form 2) for W1-W5; netlist form = EVIDENCE (sky130-ldo netlist, C_out 0.33 uF, ESR 0, 1<->50 mA load step) for W1 settled level and the W4-type load transient (reported). W5 also as an ideal step (additional case)"
  echo "negative-control push (mV below the window on W4): $NEGCTL_MV"
  pdk_record_header netlist_sha256 "$net" design/detector_top.spice ldo_netlist_sha256 "$ldo" sim/tb_rail_model_check/ldo_3v3in_1v8out.spice
  echo "results (flag asserted = v(live) or v(sticky) >= 0.36 V, the spec VOL bound; levels = codes 00/01/10/11 = 4/6/9/12 % below nominal):"
  for c in $cases; do
    out="$(awk -v a="$(get env ${c}_live_l0)" -v b="$(get env ${c}_live_l1)" -v c="$(get env ${c}_live_l2)" -v d="$(get env ${c}_live_l3)" \
      'BEGIN{m=a; if(b>m)m=b; if(c>m)m=c; if(d>m)m=d; printf "%.3e %s", m, (m<0.36)?"no flag":"FLAG"}')"
    printf '  %s [envelope, graded]: rail %.4f..%.4f V; max live over 4 levels %s\n' "$c" "$(get env ${c}_vmin)" "$(get env ${c}_vmax)" "$out"
    case "$out" in *FLAG) bad=1;; esac
  done
  for i in 0 1 2 3; do
    v="$(get env sticky_l$i)"
    awk -v v="$v" -v i="$i" 'BEGIN{printf "  sticky level %d over the whole envelope run [graded]: max %.3e V; %s\n", i, v, (v<0.36)?"no flag":"FLAG"}'
    awk -v v="$v" 'BEGIN{exit !(v>=0.36)}' && bad=1
  done
  printf '  W1 settled level [netlist-derived, graded]: rail %.4f..%.4f V\n' "$(get net net_w1_vmin)" "$(get net net_w1_vmax)"
  for i in 0 1 2 3; do
    awk -v a="$(get net net_w1_live_l$i)" -v b="$(get net net_w1_sticky_l$i)" -v i="$i" 'BEGIN{printf "    level %d: max live %.3e V, max sticky %.3e V; %s\n", i, a, b, (a<0.36&&b<0.36)?"no flag":"FLAG"}'
    awk -v a="$(get net net_w1_live_l$i)" -v b="$(get net net_w1_sticky_l$i)" 'BEGIN{exit !(a>=0.36||b>=0.36)}' && bad=1
  done
  printf '  load-step excursion [netlist-derived, REPORTED, not graded as a false flag]: rail %.4f..%.4f V (window 1.764..1.836 V)\n' "$(get net net_w4_vmin)" "$(get net net_w4_vmax)"
  awk -v lo="$(get net net_w4_vmin)" -v hi="$(get net net_w4_vmax)" 'BEGIN{ if (lo<1.764||hi>1.836) print "    the LDO netlist model itself leaves the +-2 % window under this load step, so a flag here is not a false flag; this bears on sky130-ldo, not on this block"; else print "    rail stayed inside the window; flags below would be false flags"}'
  for i in 0 1 2 3; do
    awk -v a="$(get net net_w4_live_l$i)" -v i="$i" 'BEGIN{printf "    level %d: max live %.3e V (%s)\n", i, a, (a<0.36)?"no flag":"flag asserted"}'
  done
  if [ "$bad" = 0 ]; then echo "verdict (this corner, graded cases only): zero flags"; else echo "verdict (this corner, graded cases only): FLAGS ASSERTED"; fi
} > "$work/record"
cat "$work/record" > "$rec"
[ "$bad" = 0 ] || { echo "FAIL: flag asserted in a graded false-flag case" >&2; exit 4; }
