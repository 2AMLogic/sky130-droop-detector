#!/usr/bin/env bash
# tb_threshold_mc: spec row 5 (threshold accuracy) mismatch + process Monte Carlo of the
# detector trip point, graded per (select code, process section, temperature, detector supply)
# over the ratified PVT box: 4 codes x {tt,ss,ff,sf,fs}_mm (vary=mismatch) + mc (vary=both)
# x {-40,27,125} C x {2.97,3.3,3.63} V = 216 groups. Static trip, ideal slowly-swept
# monitored rail, N = 300 per group from the recorded seed. 36 `klt sim` requests (one per
# code, kind and supply, each sweeping the 3 temperatures: the .meas WHEN threshold is a
# literal at half the applied supply) go to the Spot batch fleet with --batch-set; NOTHING
# falls back to a local grid (a failed submit exits 4). Graded by `klt yield`: target_sigma 3
# (lower confidence bound) and min_converged_samples 300 against each level's nominal
# +/-27 mV, every group with the ladder-offset negative control of its own section at the
# same code, temperature and supply (mc against tt_mm). Fails closed on a missing/mismatched
# PDK pin, a missing/short/non-numeric/duplicated/misfiled result, or an undetected negative
# control. Writes a SIMULATED record whose matrix, criterion, control and input hashes are
# read back from the generator's manifest, never typed here.
# Resume (KEEP dir): a collected report is reused only when its status is pass AND the hash
# of the inputs it was produced from (request JSON + generated deck + included netlist,
# recorded beside it in inputs.json) equals the hash of the freshly generated request.
# Anything else is moved aside as .attempt-* evidence and re-submitted with the same
# request, hence the same seeds, so no report of an earlier design or request is reused.
# Exit: 0 pass; 1 unexpected; 2 pin / netlist / request generation; 4 evidence incomplete;
#       5 no usable klt yield report; 6 negative control not detected; 7 grade misses row 5.
# Env: PDK_ROOT (optional), KLT (sim client, default klt), KLT_YIELD (default pinned uvx klayout-tools[yield]==0.8.0 klt), RECORD_DIR (output dir; default stdout only),
#      PDK_PIN (pin file), KEEP (dir to keep requests and reports in, reused across runs).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sim="$here/.."
KLT="${KLT:-klt}"   # klt sim client: must match the fleet runner (0.9.x); the 0.8.0 pin is refused with exit 87 (version skew)
KLT_YIELD="${KLT_YIELD:-uvx --from klayout-tools[yield]==0.8.0 klt}"   # pinned release incl. the klt-yield-native wheel; the host klt lacks it
fail() { echo "FAIL: $1" >&2; exit "${2:-1}"; }

. "$sim/lib/pdk_pin.sh"
pdk_pin_resolve
[ -r "$sim/../design/detector_top.spice" ] || fail "design/detector_top.spice unreadable" 2

work="${KEEP:-$(mktemp -d)}"; mkdir -p "$work"; [ -n "${KEEP:-}" ] || trap 'rm -rf "$work"' EXIT
matrix="$work/matrix.json"
python3 -I "$here/gen_requests.py" "$work/req" > "$matrix" \
  || fail "request generation failed (see the message above); nothing submitted" 2

# member_dir <request>: the directory klt collected a --batch-set member into, or nothing.
# Collect layout is version-dependent: klt >= 0.9.3 writes out/<request>/, klt <= 0.9.2
# wrote out/<request>.request/.
member_dir() {
  local d
  for d in "$work/out/$1" "$work/out/$1.request"; do
    [ -r "$d/report.json" ] && { echo "$d"; return 0; }
  done
  return 1
}

todo=()
dirs=()
# KEEP may also contain requests from an older matrix. Submit only current members.
members="$(jq -er '.members | to_entries[] | [.key, .value.sha256] | @tsv' "$matrix")" \
  || fail "cannot read request members from the generator's manifest" 2
while IFS=$'\t' read -r n want; do
  [ -f "$work/req/$n.request.json" ] && [ -r "$work/req/$n.request.json" ] \
    || fail "manifest request $n.request.json is missing or unreadable" 2
  [ -n "$want" ] || fail "the generator's manifest has no input hash for $n" 1
  d=""
  if d="$(member_dir "$n")" && [ -r "$d/inputs.json" ] && [ "$(jq -r .sha256 "$d/inputs.json")" = "$want" ] \
     && [ "$(jq -r .status "$d/report.json")" = pass ]; then
    dirs+=("$d"); continue
  fi
  for old in "$work/out/$n" "$work/out/$n.request"; do
    if [ -e "$old" ]; then mv "$old" "$old.attempt-$(date +%s)"; fi
  done
  todo+=("$n.request.json")
done <<< "$members"
rc=0
if [ "${#todo[@]}" -gt 0 ]; then
  (cd "$work/req" && $KLT sim --batch-set "${todo[@]}" --backend batch --max-in-flight 2 --max-concurrent-jobs 3 --capacity-retries 3 --wait-for-capacity 900 -o "$work/out" --format json \
    >"$work/set.json" 2>"$work/stderr.log") || rc=$?
fi
# Record beside each freshly collected report which inputs produced it (its inputs.json is
# what the resume test above compares on the next run and build_yield.py insists on).
if [ "${#todo[@]}" -gt 0 ]; then
  for q in "${todo[@]}"; do
    n="$(basename "$q" .request.json)"
    if d="$(member_dir "$n")"; then
      jq --arg n "$n" '.members[$n] | {sha256, inputs}' "$matrix" > "$d/inputs.json"
      dirs+=("$d")
    fi
  done
fi
python3 -I "$here/build_yield.py" "$matrix" "$work/out" "$work/samples.json" "$work/limits.json" || {
  if [ -r "$work/stderr.log" ]; then tail -n 20 "$work/stderr.log" >&2; fi
  jq -r '.requests[]?|select(.error!=null)|.error.message' "$work/set.json" 2>/dev/null >&2 || true
  fail "batch submit/collect incomplete (exit $rc); not falling back to a local grid" 4; }
$KLT_YIELD yield "$work/samples.json" --limits "$work/limits.json" --format json >"$work/yield.json" 2>"$work/yield.err" || true
jq -e '.measurements|length>0' "$work/yield.json" >/dev/null 2>&1 || { cat "$work/yield.err" >&2; fail "klt yield produced no report" 5; }
graded="$(jq '.measurements|length' "$work/yield.json")"
[ "$graded" = "$(jq .group_count "$matrix")" ] || fail "klt yield graded $graded of $(jq .group_count "$matrix") groups (see $work/yield.json warnings)" 5

if [ -n "${RECORD_DIR:-}" ]; then mkdir -p "$RECORD_DIR"; cp "$work/yield.json" "$RECORD_DIR/klt-yield.json"; fi
first="${dirs[0]}/report.json"
mapfile -t dirs < <(printf '%s\n' "${dirs[@]}" | sort)
{
  echo "label: SIMULATED (not measured); testbench sim/tb_threshold_mc; corner box: $(jq -r .record.corner_box "$matrix")"
  echo "stimulus: $(jq -r .record.stimulus "$matrix")"
  echo "monte_carlo: $(jq -c '{seed, n, levels, process_mm, process_mc, temperature_c, supply_v}' "$matrix")"
  echo "ngspice/engine: $(jq -r '.environment.engine_version // "unknown"' "$first")  engine_host: $(jq -r '.environment.engine_host // "unknown"' "$first")"
  echo "klt (sim client): $($KLT --version); klt (yield): $($KLT_YIELD --version)"
  echo "pdk_sources_local: $got"
  echo "models_lib_sha256 (as run): $(jq -r '.environment.models_lib_sha256 // "unknown"' "$first")"
  echo "netlist_sha256: $(jq -r .netlist_sha256 "$matrix")  $(jq -r .netlist "$matrix") (as included by every tb_l*_mm_* and tb_l*_mc_* deck)"
  echo "netlist_control_sha256: $(jq -r .netlist_control_sha256 "$matrix")  generated control copy of $(jq -r .netlist "$matrix") (ladder XR2 offset), as included by every tb_l*_ctl_* deck"
  echo "inputs_sha256: $(jq -r .inputs_sha256 "$matrix")  over the per-request hashes of all $(jq -r .request_count "$matrix") requests (request JSON + generated deck + included netlist)"
  echo "batch job ids:"
  for d in "${dirs[@]}"; do
    echo "  $(basename "$d" .request): $(jq -rs '[.[].job_id]|sort|join(" ")' "$d"/batch-receipt*.json 2>/dev/null || echo none)"; done
  echo "grading: $(jq -r '"klt yield target_sigma \(.measurements|map(.target_sigma|tostring)|unique|join(", ")) (lower confidence bound), min_converged_samples \(.measurements|map(.min_converged_samples|tostring)|unique|join(", ")), limits each level nominal +/-\(.measurements|map((.max-.min)/2*1000|round|tostring)|unique|join(", ")) mV for every (code, section, temperature, supply) group, confidence \(.confidence) (spec row 5 target), untrimmed"' "$work/limits.json")"
  echo "negative control: $(jq -r .record.negative_control "$matrix")"
  echo "klt yield status: $(jq -r .status "$work/yield.json")"
  jq -r '.measurements[]|"  \(.name): n=\(.n) mean=\(.distribution.mean) sd=\(.distribution.stddev) status=\(.status) sigma_to_spec=\(.capability.sigma_to_spec) sigma_target_met=\(.sigma_target.met) sample_size=\(.sample_size.verdict) neg_control=\(.negative_control.verdict)"' "$work/yield.json" 2>/dev/null || true
} > "$work/record.txt"
cat "$work/record.txt"
[ -z "${RECORD_DIR:-}" ] || cp "$work/record.txt" "$RECORD_DIR/record.txt"
nc_bad="$(jq -r '[.measurements[]|select(.negative_control.verdict!="detected")|.name]|join(",")' "$work/yield.json")"
[ -z "$nc_bad" ] || fail "negative control not detected for: $nc_bad" 6
status="$(jq -r .status "$work/yield.json")"
[ "$status" = pass ] || { echo "RESULT: spec row 5 statistical grade is $status (see record)" >&2; exit 7; }
