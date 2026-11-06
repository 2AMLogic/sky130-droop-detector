#!/usr/bin/env bash
# tb_supply_headroom: spec row 2, does design/detector_top.spice still decide correctly with the
# monitored rail collapsing while the 3.3 V detector supply is nominal (3.3 V), at its minimum
# (2.97 V) and at 2.97 V sagging further with the event? Also checks that the supply sag alone
# (rail static at 1.8 V) does not flag. Single corner (tt, 27 C), one local ngspice process.
# Fails closed on a missing/mismatched PDK pin, an ngspice failure, a failed .meas, or a missing
# result key. Writes a SIMULATED record; misses are reported, not hidden.
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

# Levels: name nominal-trip select-s0 select-s1 (row 4).
LEVELS=("l0 1.728 0 0" "l1 1.692 3.3 0" "l2 1.638 0 3.3" "l3 1.584 3.3 3.3")
# Supply conditions: name start-volts sag-depth-volts (sag is an ASSUMED stimulus, see the .spice).
SUPPLIES=("v3p30 3.3 0" "v2p97 2.97 0" "v2p97_sag100m 2.97 0.1" "v2p97_sag300m 2.97 0.3")
keys=()
: > "$work/cases.ctl"
for sp in "${SUPPLIES[@]}"; do read -r sn sv sag <<<"$sp"
  vlow="$(awk -v v="$sv" -v s="$sag" 'BEGIN{printf "%.3f", v-s}')"
  for lv in "${LEVELS[@]}"; do read -r ln lnom s0 s1 <<<"$lv"
    d="$(awk -v l="$lnom" 'BEGIN{printf "%.4f", l-0.1}')"
    for mode in droop quiet; do
      if [ "$mode" = droop ]; then rail="1.8 $d 100n 1n 1n 60n 1u"; else rail="1.8 1.8 100n 1n 1n 60n 1u"; fi
      name="r2_${sn}_${ln}_${mode}"
      cat >> "$work/cases.ctl" <<EOF
alter Vs0 dc = $s0
alter Vs1 dc = $s1
alter Vdd pulse = [ $sv $vlow 90n 10n 10n 100n 1u ]
alter Vrail pulse = [ $rail ]
tran 0.05n 300n
meas tran lmax max v(live) from=95n to=300n
meas tran vol find v(live) at=85n
echo "RESULT ${name}_lmax = \$&lmax"
echo "RESULT ${name}_vol = \$&vol"
EOF
      keys+=("${name}_lmax" "${name}_vol")
      if [ "$mode" = droop ]; then cat >> "$work/cases.ctl" <<EOF
meas tran voh find v(live) at=160n
let half = (voh+vol)/2
meas tran tl when v(live)=\$&half rise=1 from=95n
let lat = (tl-1.01e-7)*1e9
echo "RESULT ${name}_lat_ns = \$&lat"
echo "RESULT ${name}_voh = \$&voh"
EOF
        keys+=("${name}_lat_ns" "${name}_voh"); fi
    done
  done
done

sed -e "s#__PDK_LIB__#$lib#;s#__NETLIST__#$net#" -e "/^__CASES__\$/{r $work/cases.ctl" -e "d}" "$here/tb_supply_headroom.spice" > "$work/tb.spice"
ngspice_run "$work/tb.spice" "$work/ngspice.log"
if [ -n "${NEGCTL_DROP_KEY:-}" ]; then sed -i "/^RESULT ${NEGCTL_DROP_KEY} = /d" "$work/ngspice.log"; fi
if grep -Eqi '(^| )(tl|voh|vol|lmax) +.*failed|measure.*failed' "$work/ngspice.log"; then
  echo "FAIL: a .meas failed (no crossing found); log:" >&2; cat "$work/ngspice.log" >&2; exit 3; fi
require_results "$work/ngspice.log" "${keys[@]}"

pdk_model_files tt "$work/files"
rec="${RECORD:-/dev/stdout}"
{
  echo "label: SIMULATED (not measured); testbench sim/tb_supply_headroom/tb_supply_headroom.spice; corner tt, 27 C (single corner; no PVT sweep)"
  echo "stimulus: monitored rail = BEHAVIOURAL ENVELOPE (assumption, spec 'Rail model' form 2): 1.8 V -> threshold - 100 mV, 1 ns edges, 60 ns hold, 1 kohm load ('droop'), or held at 1.8 V ('quiet'). Detector supply 3.3 V / 2.97 V / 2.97 V sagging by 0.1 V / by 0.3 V: the sag depths and timing are ASSUMED (the spec fixes none): 10 ns edges, starting 10 ns before the rail edge, held 100 ns"
  echo "measure: droop must ASSERT (live >= 1.44 V VOH floor from 95 ns to 300 ns, live before the event <= 0.36 V); quiet (supply sag only) must stay QUIET (live <= 0.36 V VOL ceiling and never above 1.95 V); latency as in tb_latency (t=0 at full overdrive, live at 50% of its swing); 100 fF load (assumption)"
  echo "ngspice: $(ngspice --version | grep -m1 -o 'ngspice-[0-9.]*')"
  echo "klt: $($KLT --version)"
  echo "pdk_sources: $got"
  echo "netlist_sha256: $(sha256sum "$net" | cut -d' ' -f1)  design/detector_top.spice"
  echo "model_files_sha256:"
  while read -r f; do [ -r "$f" ] || { echo "FAIL: unreadable model file $f" >&2; exit 2; }
    printf '  %s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "${f#"$root"/}"; done < "$work/files"
  echo "results:"
  bad=0
  for sp in "${SUPPLIES[@]}"; do read -r sn sv sag <<<"$sp"
    for lv in "${LEVELS[@]}"; do read -r ln lnom _ <<<"$lv"
      n="r2_${sn}_${ln}_droop"; q="r2_${sn}_${ln}_quiet"
      if awk -v m="$(get ${n}_lmax)" -v v="$(get ${n}_vol)" 'BEGIN{exit !(m>=1.44 && m<=1.95 && v<=0.36)}'; then da=ASSERTS; else da="DOES NOT ASSERT"; bad=$((bad+1)); fi
      if awk -v m="$(get ${q}_lmax)" 'BEGIN{exit !(m<=0.36)}'; then qa=QUIET; else qa="FALSE FLAG"; bad=$((bad+1)); fi
      if [ "$da" = ASSERTS ]; then lat="$(printf '%.3f ns' "$(get ${n}_lat_ns)")"; else lat="n/a (no assertion)"; fi
      printf '  supply %.2f V sag %.1f V, %s (%.3f V): droop %s (live max %.4f V, latency %s, voh %.3f V); sag-only %s (live max %.4f V)\n' \
        "$sv" "$sag" "$ln" "$lnom" "$da" "$(get ${n}_lmax)" "$lat" "$(get ${n}_voh)" "$qa" "$(get ${q}_lmax)"
    done
  done
  echo "cases not behaving as required: $bad of 32 (reported, not graded against the PVT box; single corner)"
} > "$work/record"
cat "$work/record" > "$rec"
