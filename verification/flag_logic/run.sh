#!/usr/bin/env bash
# verification/flag_logic: truth-table / sequence check of the row 10 flags.
# Runs sim/tb_flag_logic (A: flag_logic alone, B: detector_top under the rail model),
# which grades both traces with check.py against the executable reference, then
# runs the negative control: the same traces with a deliberately broken flag sequence
# (CLR ignored / sticky follows live / CLR dominant) must FAIL the check.
# Exit 0 only if the real traces pass AND every broken sequence is caught.
# Env as sim/tb_flag_logic/run.sh (PDK_ROOT, KLT, PDK_PIN); RECORD = this check's output.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dir="$(mktemp -d)"; trap 'rm -rf "$dir"' EXIT
TRACE_DIR="$dir" RECORD="$dir/sim-record.txt" "$here/../../sim/tb_flag_logic/run.sh"
rec="${RECORD:-/dev/stdout}"
{
  echo "label: SIMULATED traces (tt, 27 C, 3.3 V) checked against the spec reference model; see sim/tb_flag_logic"
  cat "$dir/sim-record.txt" | sed -n '/^  [AB] sequence check/p'
  for part in a b; do
    s=8; [ "$part" = b ] && s=15
    for mode in clr-ignored sticky-follows-live clr-dominant; do
      if python3 -I "$here/check.py" "$dir/trace_$part.txt" --settle "$s" --break "$mode" >"$dir/neg.txt"; then
        echo "FAIL: negative control '$mode' on part $part was NOT caught" >&2; exit 4
      fi
      echo "negative control part $part, broken sequence '$mode': caught: $(tail -n1 "$dir/neg.txt")"
    done
  done
} > "$dir/out"
cat "$dir/out" > "$rec"
