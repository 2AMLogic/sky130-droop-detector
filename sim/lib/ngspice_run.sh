# Shared ngspice run / result-check helpers for the sim/*/run.sh bench drivers. Source it;
# do not execute it. Fail-closed: every failure prints "FAIL: ..." to stderr plus the last
# 40 lines of the offending log, and exits 3 (bench problems; 2 is reserved for pin / PDK
# problems, see pdk_pin.sh).
# Optional: set NGSPICE_CTX (e.g. "at tap 0.9") to append context to the FAIL messages.

# sim_workdir: create the scratch dir $work (removed on exit) in the caller's scope.
sim_workdir() { work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT; }

# ngspice_log_fail <message> <log>: print FAIL: <message> and the log tail, exit 3.
ngspice_log_fail() { echo "FAIL: $1" >&2; tail -40 "$2" >&2; exit 3; }

# ngspice_run <deck> <log>: one batch ngspice run; sets RESULT_LOG=<log> for get.
ngspice_run() {
  RESULT_LOG="$2"
  ngspice -b -o "$2" "$1" >/dev/null 2>&1 \
    || ngspice_log_fail "ngspice exited non-zero${NGSPICE_CTX:+ $NGSPICE_CTX}; log:" "$2"
}

# require_results <log> <key>...: every key needs a numeric "RESULT <key> = <number>" line.
require_results() {
  local log="$1" k; shift
  for k in "$@"; do
    grep -Eq "^RESULT $k = [0-9.eE+-]+" "$log" \
      || ngspice_log_fail "no '$k' result${NGSPICE_CTX:+ $NGSPICE_CTX} in ngspice log" "$log"
  done
}

# result_of <log> <key>: the value text of the first "RESULT <key> = ..." line (empty if none).
result_of() { sed -n "s/^RESULT $2 = //p" "$1" | head -n1; }

# get <key>: result_of on the log of the last ngspice_run.
get() { result_of "$RESULT_LOG" "$1"; }
