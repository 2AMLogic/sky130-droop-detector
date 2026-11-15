"""PDK-free: the local-ngspice thread policy lives only in sim/lib/ngspice_run.sh.

Guards the deduplication of #85. Two halves, because an absence check alone can be
satisfied by deleting the policy entirely:

  1. No tracked file under sim/ outside sim/lib/ may set `num_threads` or
     `OMP_NUM_THREADS` -- in a deck, a driver, or a deck generator. The effective knob
     is the in-deck `set num_threads`, which `ngspice_run` forces for every bench; a
     second copy in a bench can only disagree with it.
  2. sim/lib/ngspice_run.sh must still define SIM_NGSPICE_THREADS and still force it
     into every deck it runs, so the policy is actually applied and not merely absent.
"""
import pathlib, re, subprocess, sys

root = pathlib.Path(__file__).resolve().parent.parent
HELPER = "sim/lib/ngspice_run.sh"

# `set num_threads=...` (deck or generated deck text) or any OMP_NUM_THREADS mention.
SETTING = re.compile(r"num_threads\s*=|OMP_NUM_THREADS")

tracked = subprocess.check_output(["git", "ls-files", "sim/"], cwd=root, text=True).split()
offenders = []
for rel in tracked:
    # sim/lib/ is where the policy belongs; prose cannot set a thread count, and sim/README.md
    # is required to describe the policy, so .md is documentation rather than a second knob.
    if rel.startswith("sim/lib/") or rel.endswith(".md"):
        continue
    try:
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
    except (OSError, IsADirectoryError):
        continue
    for n, line in enumerate(text.splitlines(), 1):
        if SETTING.search(line):
            offenders.append(f"{rel}:{n}: {line.strip()}")

errors = []
if offenders:
    errors.append(
        "thread count set outside " + HELPER + " (the policy belongs in that one file; "
        "see its header for which knob ngspice actually honours):\n  "
        + "\n  ".join(offenders))

helper = (root / HELPER).read_text(encoding="utf-8")
if not re.search(r"^SIM_NGSPICE_THREADS=[0-9]+$", helper, re.M):
    errors.append(HELPER + " no longer defines SIM_NGSPICE_THREADS=<n>: the repo has no "
                           "local-ngspice thread policy at all.")
if "set num_threads=" not in helper or "sim_thread_cap" not in helper:
    errors.append(HELPER + " no longer forces `set num_threads=` into the deck via "
                           "sim_thread_cap: the policy is defined but not applied, so every "
                           "bench silently inherits the host's ngspice init files.")
# A call site, not the definition: `sim_thread_cap() {` has no whitespace before its "(".
if not re.search(r"^\s*sim_thread_cap\s+\S", helper, re.M):
    errors.append(HELPER + " defines sim_thread_cap but never calls it, so no deck is capped.")

if errors:
    sys.exit("\n".join(errors))
print("ok: local-ngspice thread policy is only in " + HELPER)
