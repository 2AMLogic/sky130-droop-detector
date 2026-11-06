#!/usr/bin/env bash
# tb_flag_logic (spec row 10): sticky flag + clear, plus the live (non-sticky) flag.
#   A. design/flag_logic.spice alone, scripted live_in / clr sequence (set, hold, clear,
#      CLR while the condition persists, short pulse).
#   B. design/detector_top.spice with the rail = behavioural envelope droops, a CLR
#      between droops and a CLR while a droop persists.
# Analog levels and the sequence are graded by verification/flag_logic/check.py against
# an executable reference of the spec (VOH >= 1.44 V, VOL <= 0.36 V at 100 fF).
# Single corner (tt, 27 C, 3.3 V), local ngspice. Fails closed on a missing/mismatched PDK pin,
# a missing result or a sequence violation. Writes a SIMULATED record.
# Cold start: a fresh clone needs the pinned PDK (sim/pdk.json install line), ngspice, klt,
# jq, python3. The latch power-up state is not assumed: CLR is asserted for the first
# 20 ns (A) / 30 ns (B) and the checker ignores sticky until the first CLR.
# Env: PDK_ROOT (optional), KLT (default: klt), RECORD (output path, default stdout),
#      PDK_PIN (pin file, default sim/pdk.json; overridden for negative controls),
#      TRACE_DIR (if set, keep trace_a.txt / trace_b.txt there for the verification wrapper).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sim="$here/.."
chk="$sim/../verification/flag_logic/check.py"
. "$sim/lib/pdk_pin.sh"
pdk_pin_resolve
lnet="$sim/../design/flag_logic.spice"; tnet="$sim/../design/detector_top.spice"
for n in "$lnet" "$tnet" "$chk"; do [ -r "$n" ] || { echo "FAIL: unreadable: $n" >&2; exit 2; }; done
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
fail3() { echo "FAIL: $1" >&2; [ -n "${2:-}" ] && cat "$2" >&2; exit 3; }
res() { sed -n "s/^RESULT $2 = //p" "$1" | head -n1; }

# "a:b a:b ..." (ns) -> 0 / 3.3 V pwl with 0.2 ns edges
pwl3() { awk -v iv="$1" 'BEGIN{n=split(iv,a," "); s="0 0"; for(i=1;i<=n;i++){split(a[i],x,":"); s=s sprintf(" %.3fn 0 %.3fn 3.3 %.3fn 3.3 %.3fn 0",x[1],x[1]+0.2,x[2],x[2]+0.2)} print s}'; }

# ---- A: flag_logic alone ------------------------------------------------------------
live_iv="50:80 150:300 380:385"
clr_iv="0:20 110:130 170:200 330:350"
tstop=450
sed "s#__PDK_LIB__#$lib#;s#__NETLIST__#$lnet#;s#__LIVE_PWL__#$(pwl3 "$live_iv")#;s#__CLR_PWL__#$(pwl3 "$clr_iv")#;s#__TSTOP__#${tstop}n#g;s#__TRACE__#$work/trace_a.txt#" \
  "$here/tb_flag_logic.spice" > "$work/a.sp"
ngspice -b -o "$work/a.log" "$work/a.sp" >/dev/null 2>&1 || fail3 "ngspice exited non-zero (A)" "$work/a.log"
[ -s "$work/trace_a.txt" ] || fail3 "no trace written (A)" "$work/a.log"
python3 -I "$chk" "$work/trace_a.txt" --settle 8 > "$work/chk_a.txt" || { cat "$work/chk_a.txt" >&2; fail3 "sequence check A failed"; }

# ---- B: detector_top, rail model --------------------------------------------------------
rail="$(awk 'BEGIN{thr=1.728; D=thr-0.1; f=(1.8-thr)/(1.8-D); s="0 1.8";
  n=split("100:30 250:150",d," ");
  for(i=1;i<=n;i++){split(d[i],x,":"); t0=x[1]; w=x[2]; h=w-2*(1-f);
    s=s sprintf(" %.4fn 1.8 %.4fn %.4f %.4fn %.4f %.4fn 1.8", t0, t0+1, D, t0+1+h, D, t0+2+h)}
  print s}')"
clr_b="0:30 160:180 300:320 450:470"
sed "s#__PDK_LIB__#$lib#;s#__NETLIST__#$tnet#;s#__RAIL_PWL__#$rail#;s#__CLR_PWL__#$(pwl3 "$clr_b")#;s#__TSTOP__#500n#g;s#__TRACE__#$work/trace_b.txt#" \
  "$here/tb_flag_logic_top.spice" > "$work/b.sp"
ngspice -b -o "$work/b.log" "$work/b.sp" >/dev/null 2>&1 || fail3 "ngspice exited non-zero (B)" "$work/b.log"
[ -s "$work/trace_b.txt" ] || fail3 "no trace written (B)" "$work/b.log"
python3 -I "$chk" "$work/trace_b.txt" --settle 15 --live-in-high 1.65 > "$work/chk_b.txt" || { cat "$work/chk_b.txt" >&2; fail3 "sequence check B failed"; }
for k in vmax_live vmax_sticky; do
  [ -n "$(res "$work/b.log" $k)" ] || fail3 "no '$k' result (B)" "$work/b.log"
  [ -n "$(res "$work/a.log" $k)" ] || fail3 "no '$k' result (A)" "$work/a.log"
done
# no output above 1.95 V (spec Output: no output that exceeds 1.95 V)
for l in a b; do for k in vmax_live vmax_sticky; do
  awk -v v="$(res "$work/$l.log" $k)" 'BEGIN{exit !(v<=1.95)}' || fail3 "$k = $(res "$work/$l.log" $k) V exceeds 1.95 V (part $l)"
done; done

if [ -n "${TRACE_DIR:-}" ]; then mkdir -p "$TRACE_DIR"; cp "$work/trace_a.txt" "$work/trace_b.txt" "$TRACE_DIR/"; fi

pdk_model_files tt "$work/files"
rec="${RECORD:-/dev/stdout}"
{
  echo "label: SIMULATED (not measured); testbench sim/tb_flag_logic/tb_flag_logic.spice and tb_flag_logic_top.spice; corner tt, 27 C, detector supply 3.3 V (single corner; PVT is #34/#35)"
  echo "stimulus A: ideal live_in / clr, 0.2 ns edges; live_in high $live_iv ns, clr high $clr_iv ns; 100 fF on live and sticky (ASSUMPTION, spec row 10)"
  echo "stimulus B: detector_top, select 00 (1.728 V); rail = BEHAVIOURAL ENVELOPE (assumption, spec 'Rail model' form 2): PWL droops to threshold - 100 mV, 1 ns edges, widths 30 ns and 150 ns starting at 100 ns and 250 ns, +10 mV 20 MHz ripple in series; clr high $clr_b ns (160-180 between droops, 300-320 while the second droop persists)"
  echo "ngspice: $(ngspice --version | grep -m1 -o 'ngspice-[0-9.]*')"
  echo "klt: $($KLT --version)"
  echo "pdk_sources: $got"
  echo "netlist_sha256: $(sha256sum "$lnet" | cut -d' ' -f1)  design/flag_logic.spice"
  echo "netlist_sha256: $(sha256sum "$tnet" | cut -d' ' -f1)  design/detector_top.spice"
  echo "checker_sha256: $(sha256sum "$chk" | cut -d' ' -f1)  verification/flag_logic/check.py"
  echo "model_files_sha256:"
  while read -r f; do [ -r "$f" ] || { echo "FAIL: unreadable model file $f" >&2; exit 2; }
    printf '  %s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "${f#"$root"/}"; done < "$work/files"
  echo "results:"
  echo "  A sequence check: $(tail -n1 "$work/chk_a.txt")"
  echo "  B sequence check: $(tail -n1 "$work/chk_b.txt")"
  echo "  output extremes A: live $(res "$work/a.log" vmin_live) .. $(res "$work/a.log" vmax_live) V; sticky $(res "$work/a.log" vmin_sticky) .. $(res "$work/a.log" vmax_sticky) V"
  echo "  output maximum B: live $(res "$work/b.log" vmax_live) V; sticky $(res "$work/b.log" vmax_sticky) V (bound 1.95 V; VOH >= 1.44 V, VOL <= 0.36 V judged by the checker)"
  echo "  settling window ignored after an input edge: 8 ns (A), 15 ns (B); the outputs take about 5 ns after an input edge to reach VOH at 100 fF (observed in A); propagation delay is graded by tb_latency, not here"
  echo "  no verdict for spec row 10 over PVT is made here"
} > "$work/record"
cat "$work/record" > "$rec"
