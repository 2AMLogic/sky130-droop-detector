#!/usr/bin/env bash
# tb_threshold_mc: spec row 5 (threshold accuracy) mismatch + process Monte Carlo of the
# detector trip point at all four select codes. Static trip, tt-box supply 3.3 V, 27 C,
# ideal slowly-swept monitored rail. 12 `klt sim` requests (4 levels x {5 *_mm sections
# vary=mismatch, `mc` section vary=both, negative control}) go to the Spot batch fleet with
# --batch-set; NOTHING falls back to a local grid (a failed submit exits 4).
# Graded by `klt yield`: target_sigma 3 (lower confidence bound) and min_converged_samples
# 300 against level +/-27 mV, per level and process group, each with the ladder-mismatch
# negative control. Fails closed on a missing/mismatched PDK pin, a missing/short/non-numeric
# result, or an undetected negative control. Writes a SIMULATED record.
# Env: PDK_ROOT (optional), KLT (sim client, default klt), KLT_YIELD (default pinned uvx klayout-tools[yield]==0.8.0 klt), RECORD_DIR (output dir; default stdout only),
#      PDK_PIN (pin file; overridden for negative controls), KEEP (dir to keep reports in).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
sim="$here/.."
pin="${PDK_PIN:-$sim/pdk.json}"
variant="$(jq -er .variant "$pin")"
want="$(jq -er .sources_line "$pin")"
KLT="${KLT:-klt}"   # klt sim client: must match the fleet runner (0.9.x); the 0.8.0 pin is refused with exit 87 (version skew)
KLT_YIELD="${KLT_YIELD:-uvx --from klayout-tools[yield]==0.8.0 klt}"   # pinned release incl. the klt-yield-native wheel; the host klt lacks it
fail() { echo "FAIL: $1" >&2; exit "${2:-1}"; }

found="$($KLT pdk find --pdk "$variant" ${PDK_ROOT:+--pdk-root "$PDK_ROOT"} 2>&1)" || {
  echo "$found" >&2; fail "klt pdk find could not resolve $variant (PDK_ROOT=${PDK_ROOT:-unset}); pin is: $want" 2; }
root="$(sed -n 's/^root: //p' <<<"$found")"
src="$root/$variant/SOURCES"
[ -n "$root" ] && [ -s "$src" ] || fail "SOURCES missing or empty at '$src'; pin is: $want" 2
got="$(head -n1 "$src")"
[ "$got" = "$want" ] || fail "PDK revision mismatch; pin is '$want', found '$got' in $src" 2
[ -r "$root/$variant/libs.tech/combined/sky130.lib.spice" ] || fail "model lib unreadable under $root" 2
[ -r "$sim/../design/detector_top.spice" ] || fail "design/detector_top.spice unreadable" 2

work="${KEEP:-$(mktemp -d)}"; mkdir -p "$work"; [ -n "${KEEP:-}" ] || trap 'rm -rf "$work"' EXIT
params="$(python3 -I "$here/gen_requests.py" "$work/req")"

# Idempotent re-run: a request whose report is already complete (status pass, KEEP dir) is not
# re-submitted; an incomplete one (e.g. lost_shard after a capacity refusal) is moved aside as
# evidence and re-submitted with the same request, hence the same seeds.
todo=()
for q in "$work"/req/l*_*.request.json; do
  n="$(basename "$q" .json)"; rep="$work/out/$n/report.json"
  if [ -r "$rep" ] && [ "$(jq -r .status "$rep")" = pass ]; then continue; fi
  if [ -d "$work/out/$n" ]; then mv "$work/out/$n" "$work/out/$n.attempt-$(date +%s)"; fi
  todo+=("$(basename "$q")")
done
rc=0
if [ "${#todo[@]}" -gt 0 ]; then
  (cd "$work/req" && $KLT sim --batch-set "${todo[@]}" --backend batch --max-in-flight 2 --max-concurrent-jobs 3 --capacity-retries 3 --wait-for-capacity 900 -o "$work/out" --format json \
    >"$work/set.json" 2>"$work/stderr.log") || rc=$?
fi
python3 -I "$here/build_yield.py" "$work/out" "$work/samples.json" "$work/limits.json" || {
  tail -n 20 "$work/stderr.log" >&2
  jq -r '.requests[]?|select(.error!=null)|.error.message' "$work/set.json" 2>/dev/null >&2 || true
  fail "batch submit/collect incomplete (exit $rc); not falling back to a local grid" 4; }
$KLT_YIELD yield "$work/samples.json" --limits "$work/limits.json" --format json >"$work/yield.json" 2>"$work/yield.err" || true
jq -e '.measurements|length>0' "$work/yield.json" >/dev/null 2>&1 || { cat "$work/yield.err" >&2; fail "klt yield produced no report" 5; }

if [ -n "${RECORD_DIR:-}" ]; then mkdir -p "$RECORD_DIR"; cp "$work/yield.json" "$RECORD_DIR/klt-yield.json"; fi
first="$(ls "$work"/out/l0_mm.request/report.json)"
{
  echo "label: SIMULATED (not measured); testbench sim/tb_threshold_mc; corner box: process {tt,ss,ff,sf,fs}_mm (vary=mismatch) + mc (vary=both), 27 C, detector supply 3.3 V"
  echo "stimulus: monitored rail = IDEAL SOURCE, DC sweep 0.5 mV steps (static trip, spec row 5); trip = rail where design/detector_top.spice comparator node flag crosses 1.65 V; value resolution 0.1 mV (klt measureprec)"
  echo "monte_carlo: $params"
  echo "ngspice/engine: $(jq -r '.environment.engine_version // "unknown"' "$first")  engine_host: $(jq -r '.environment.engine_host // "unknown"' "$first")"
  echo "klt (sim client): $($KLT --version); klt (yield): $($KLT_YIELD --version)"
  echo "pdk_sources_local: $got"
  echo "models_lib_sha256 (as run): $(jq -r '.environment.models_lib_sha256 // "unknown"' "$first")"
  echo "netlist_sha256: $(sha256sum "$sim/../design/detector_top.spice" | cut -d' ' -f1)  design/detector_top.spice"
  echo "batch job ids:"
  for r in "$work"/out/l*_*.request/report.json; do
    echo "  $(basename "$(dirname "$r")" .request): $(jq -r '.environment.remote.job_id // "none"' "$r")"; done
  echo "grading: klt yield target_sigma 3 (lower confidence bound), min_converged_samples 300, limits level +/-27 mV (spec row 5 target), untrimmed"
  echo "negative control: ladder segment XR2 L=94.073 -> 88 in design/detector_top.spice copy, tt_mm mismatch MC, same seed and N"
  echo "klt yield status: $(jq -r .status "$work/yield.json")"
  jq -r '.measurements[]|"  \(.name): n=\(.n) mean=\(.mean) sd=\(.stddev) status=\(.status) sigma_to_spec=\(.capability.sigma_to_spec) sigma_target_met=\(.sigma_target.met) sample_size=\(.sample_size.verdict) neg_control=\(.negative_control.verdict)"' "$work/yield.json" 2>/dev/null || true
} > "$work/record.txt"
cat "$work/record.txt"
[ -z "${RECORD_DIR:-}" ] || cp "$work/record.txt" "$RECORD_DIR/record.txt"
nc_bad="$(jq -r '[.measurements[]|select(.negative_control.verdict!="detected")|.name]|join(",")' "$work/yield.json")"
[ -z "$nc_bad" ] || fail "negative control not detected for: $nc_bad" 6
status="$(jq -r .status "$work/yield.json")"
[ "$status" = pass ] || { echo "RESULT: spec row 5 statistical grade is $status (see record)" >&2; exit 7; }
