#!/usr/bin/env bash
# Rail-model check: the testbench rail must reproduce the sky130-ldo interface rows
# before any detector row relies on it (spec/target-spec.md, "Rail model", row 1).
#   1. Behavioural envelope (ASSUMPTION): W1-W5, the LDO-compliant transient and the
#      row 6/7 fast-edge droops are asserted against their bounds (one local klt sim unit).
#   2. Netlist form (EVIDENCE): the sky130-ldo netlist at the pinned commit under the
#      4 C_out/ESR corner points of the ratified window, tt / 27 C / 3.3 V only. The grid
#      is 4 klt sim requests submitted with `--batch-set` (Spot batch fleet; never run
#      locally). Figures are REPORTED, NOT GRADED (spec: the LDO misses some of its rows).
# Fails closed: a missing/mismatched PDK pin or LDO source pin, a drifted netlist, a
# failed batch submit, or any failed envelope bound exits non-zero.
# Env: PDK_ROOT (optional), KLT (default: klt), RECORD (output path, default stdout),
#      ENVELOPE_NEGCTL_MV (negative control: push the W5 spike this many mV out of bound).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sim="$here/.."
variant="$(jq -er .variant "$sim/pdk.json")"
want="$(jq -er .sources_line "$sim/pdk.json")"
KLT="${KLT:-klt}"
NEGCTL="${ENVELOPE_NEGCTL_MV:-0}"
fail() { echo "FAIL: $1" >&2; exit "${2:-2}"; }

# --- PDK pin (same check as sim/smoke/run.sh) ---------------------------------
found="$($KLT pdk find --pdk "$variant" ${PDK_ROOT:+--pdk-root "$PDK_ROOT"} 2>&1)" || {
  echo "$found" >&2; fail "klt pdk find could not resolve $variant (PDK_ROOT=${PDK_ROOT:-unset}); pin is: $want"; }
root="$(sed -n 's/^root: //p' <<<"$found")"
src="$root/$variant/SOURCES"
[ -n "$root" ] && [ -s "$src" ] || fail "SOURCES missing or empty at '$src'; pin is: $want"
got="$(head -n1 "$src")"
[ "$got" = "$want" ] || fail "PDK revision mismatch; pin is '$want', found '$got' in $src"
lib="$root/$variant/libs.tech/combined/sky130.lib.spice"
[ -r "$lib" ] || fail "model lib unreadable: $lib"
export PDK_ROOT="$root" PDK="$variant"

# --- LDO source pin and netlist drift ----------------------------------------------
ldo="$here/ldo-source.json"
ldo_commit="$(jq -er .commit "$ldo")"
for k in schematic symbol; do
  f="$here/src/$(basename "$(jq -er ".$k" "$ldo")")"
  [ -r "$f" ] || fail "vendored LDO $k missing: $f"
  [ "$(sha256sum "$f" | cut -d' ' -f1)" = "$(jq -er ".${k}_sha256" "$ldo")" ] \
    || fail "vendored LDO $k does not match the pinned sha256 (commit $ldo_commit)"
done
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
tail -n +4 "$here/ldo_3v3in_1v8out.spice" > "$work/ldo_headerless.spice"   # drop the 3-line provenance header
$KLT netlist --pdk "$variant" --pdk-root "$root" --rcfile "$here/xschemrc" --block --check \
  -o "$work/ldo_headerless.spice" "$here/src/ldo_3v3in_1v8out.sch" >"$work/netlist-check.log" 2>&1 \
  || { cat "$work/netlist-check.log" >&2; fail "committed LDO netlist drifted from the pinned schematic (klt netlist --check)" 3; }
netlist_sha="$(sha256sum "$here/ldo_3v3in_1v8out.spice" | cut -d' ' -f1)"

# --- 1. behavioural envelope --------------------------------------------------------
mkdir -p "$work/env"
python3 -I "$here/gen_envelope.py" "$work/env" "$NEGCTL"
env_rc=0
$KLT sim "$work/env/envelope.request.json" --backend local -o "$work/env/out" --format json \
  >"$work/env/report.json" 2>"$work/env/stderr.log" || env_rc=$?
jq -e '.corners|length>0' "$work/env/report.json" >/dev/null 2>&1 \
  || { cat "$work/env/stderr.log" >&2; fail "envelope klt sim produced no report (exit $env_rc)" 3; }
env_status="$(jq -r .status "$work/env/report.json")"
env_n="$(jq '.corners[0].measurements|length' "$work/env/report.json")"
env_bad="$(jq -r '.corners[0].measurements[]|select(.status!="pass")|"  \(.name) = \(.value) (\(.status))"' "$work/env/report.json")"

# --- 2. netlist form, 4 C_out/ESR points via the batch fleet ------------------------
# One request template and one point list (name:cdir:cout:resr). ESR = 0 uses cdir (ngspice
# cannot take a 0 ohm resistor); ESR > 0 uses cout in series with resr, parked at 10m when unused.
POINTS=(c0p33u_esr0:0.33u:0:10m c0p33u_esr500m:0:0.33u:500m c4p7u_esr0:4.7u:0:10m c4p7u_esr500m:0:4.7u:500m)
mkdir -p "$work/nf"
cp "$here/netlist_form.spice" "$here/ldo_3v3in_1v8out.spice" "$work/nf/"
for pt in "${POINTS[@]}"; do
  IFS=: read -r p cdir cout resr <<<"$pt"
  cat > "$work/nf/netlist_form_$p.spice" <<EOF
* Netlist-form rail model, one C_out/ESR point: $p.
* ESR = 0 uses CDIR (no series element, ngspice cannot take a 0 ohm resistor);
* ESR > 0 uses COUT in series with RESR. RESR is parked at 10m when unused.
.param cdir=$cdir cout=$cout resr=$resr
.include netlist_form.spice
EOF
  sed "s/@NETLIST@/netlist_form_$p.spice/" > "$work/nf/netlist_form_$p.request.json" <<'EOF'
{
  "netlist": "@NETLIST@",
  "models": {
    "pdk": "sky130A",
    "lib": "libs.tech/combined/sky130.lib.spice"
  },
  "corners": {
    "process": [
      "tt"
    ],
    "temperature_c": [
      27
    ]
  },
  "analysis": {
    "kind": "tran",
    "args": "200n 3m"
  },
  "measurements": [
    {
      "name": "v_pre",
      "spice": ".meas tran v_pre avg v(vout) from=0.8m to=0.999m"
    },
    {
      "name": "vmin_rise",
      "spice": ".meas tran vmin_rise min v(vout) from=1m to=2.001m"
    },
    {
      "name": "vmax_rise",
      "spice": ".meas tran vmax_rise max v(vout) from=1m to=2.001m"
    },
    {
      "name": "vmin_fall",
      "spice": ".meas tran vmin_fall min v(vout) from=2.001m to=3m"
    },
    {
      "name": "vmax_fall",
      "spice": ".meas tran vmax_fall max v(vout) from=2.001m to=3m"
    },
    {
      "name": "recovery_rise_us",
      "expr": "vecmax(((abs(v(vout)-1.8)-0.018)/(abs(abs(v(vout)-1.8)-0.018)+1e-15)+1)/2*((time-1m)/(abs(time-1m)+1e-15)+1)/2*((2.001m-time)/(abs(2.001m-time)+1e-15)+1)/2*(time-1m))*1e6"
    },
    {
      "name": "recovery_fall_us",
      "expr": "vecmax(((abs(v(vout)-1.8)-0.018)/(abs(abs(v(vout)-1.8)-0.018)+1e-15)+1)/2*((time-2.001m)/(abs(time-2.001m)+1e-15)+1)/2*((3m-time)/(abs(3m-time)+1e-15)+1)/2*(time-2.001m))*1e6"
    }
  ]
}
EOF
done
nf_rc=0
(cd "$work/nf" && $KLT sim --batch-set netlist_form_*.request.json -o "$work/nf/out" --format json \
  >"$work/nf/set.json" 2>"$work/nf/stderr.log") || nf_rc=$?
for pt in "${POINTS[@]}"; do
  p="${pt%%:*}"
  rep="$work/nf/out/netlist_form_$p.request/report.json"
  [ -r "$rep" ] && jq -e '.corners[0].measurements|length>0' "$rep" >/dev/null 2>&1 \
    && [ "$(jq -r '[.corners[0].measurements[]|select(.value==null)]|length' "$rep")" = 0 ] \
    || { tail -n 20 "$work/nf/stderr.log" >&2
         jq -r '.requests[]|select(.error!=null)|.error.message' "$work/nf/set.json" 2>/dev/null >&2 || true
         fail "batch submit/collect failed for point $p (exit $nf_rc); not falling back to a local grid" 4; }
done

rec="${RECORD:-/dev/stdout}"
{
  echo "label: SIMULATED (not measured); testbench sim/tb_rail_model_check; corner tt, 27 C, VIN 3.3 V, VREF 1.2 V, EN 3.3 V (no PVT sweep)"
  echo "ngspice: $(ngspice --version | grep -m1 -o 'ngspice-[0-9.]*')"
  echo "klt: $($KLT --version)"
  echo "pdk_sources: $got"
  echo "model_lib_sha256: $(sha256sum "$lib" | cut -d' ' -f1)"
  echo "ldo_source: $(jq -r .repo "$ldo")@$ldo_commit $(jq -r .schematic "$ldo")"
  echo "ldo_schematic_sha256: $(jq -r .schematic_sha256 "$ldo")"
  echo "ldo_netlist_sha256: $netlist_sha  (sim/tb_rail_model_check/ldo_3v3in_1v8out.spice, klt netlist --check: match)"
  echo "ldo_pdk_note: the LDO repo pins a different open_pdks; this is that netlist simulated under THIS repo's pin"
  echo
  echo "== behavioural envelope (ASSUMPTION, not a measurement; asserted) =="
  echo "stimulus: W1-W5, LDO-compliant transient (-150 mV, 1 us edges), row 6/7 droops to threshold-100 mV (1 ns edges), ideal step (additional)"
  echo "negative_control_mv: $NEGCTL"
  echo "assertions: $env_n declared, status $env_status"
  [ -z "$env_bad" ] || { echo "failed:"; echo "$env_bad"; }
  jq -r '.corners[0].measurements[]|select(.name|test("^(w4_recovery_us|ct_vmin|ct_recovery_us|w5_dn_vmin|w5_up_vmax)$"))|"  \(.name) = \(.value)"' "$work/env/report.json"
  echo
  echo "== netlist form (EVIDENCE; REPORTED, NOT GRADED: netlist-form figures are not checked against bounds) =="
  echo "load: 1 mA <-> 50 mA, 1 us edges; pre-step level = mean over 0.8-0.999 ms; recovery = last exit from 1.8 V +-1 % after the edge"
  echo "backend: klt sim --batch-set (4 requests, one C_out/ESR point each)"
  for pt in "${POINTS[@]}"; do
    p="${pt%%:*}"
    rep="$work/nf/out/netlist_form_$p.request/report.json"
    echo "point $p: job_id=$(jq -r '.environment.remote.job_id // "none"' "$rep")"
    jq -r '.corners[0].measurements|map({(.name):.value})|add
      | (([.v_pre-.vmin_rise,.vmax_rise-.v_pre,.v_pre-.vmin_fall,.vmax_fall-.v_pre]|max)*1e3) as $pk
      | "  v_pre_v=\(.v_pre) peak_excursion_mv=\($pk*100|round/100) recovery_us=\([.recovery_rise_us,.recovery_fall_us]|max)  (rise \(.recovery_rise_us), fall \(.recovery_fall_us))"' "$rep"
  done
} > "$work/record"
cat "$work/record" > "$rec"
[ "$env_status" = pass ] || { echo "FAIL: envelope bound check failed:" >&2; echo "$env_bad" >&2; exit 5; }
