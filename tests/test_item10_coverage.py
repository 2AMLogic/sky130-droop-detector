"""PDK-free: every tracked bench runner / .py under sim/ and verification/ must be in attest/item10.json."""
import json, pathlib, subprocess, sys

root = pathlib.Path(__file__).resolve().parent.parent
tracked = subprocess.check_output(
    ["git", "ls-files", "sim/*/run.sh", "verification/*/run.sh", "sim/**/*.py", "verification/**/*.py"],
    cwd=root, text=True).split()
covered = {a for c in json.loads((root / "attest/item10.json").read_text())["checks"] for a in c["argv"]}
missing = sorted(set(tracked) - covered)
if missing:
    sys.exit("not covered by attest/item10.json: " + ", ".join(missing))
