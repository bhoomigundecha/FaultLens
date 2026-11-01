#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# FaultLens — fault switch for the trimmed Astronomy Shop
#
# Flips feature flags in src/flagd/demo.flagd.json. flagd watches the file and
# applies the change within ~1 s — no restarts. (This is exactly what flagd-ui
# does; we just skip running that 200 MB container.)
#
#   ./faultlens/fault.sh list                         # show all flags + current state
#   ./faultlens/fault.sh payment-failure 50%          # named scenario
#   ./faultlens/fault.sh paymentFailure 100%          # or raw flag + variant
#   ./faultlens/fault.sh reset                        # everything back to "off"
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."
FLAGS=src/flagd/demo.flagd.json

# Friendly scenario names → flagd flag (case statement: macOS ships bash 3.2)
scenario_flag() {
  case "$1" in
    payment-failure) echo paymentFailure ;;               # 10% 25% 50% 75% 90% 100%
    payment-down)    echo paymentUnreachable ;;           # on
    cart-failure)    echo cartFailure ;;                  # 10% … 100%
    catalog-failure) echo productCatalogFailure ;;        # on (one product fails)
    db-contention)   echo productCatalogLockContention ;; # on (DB latency)
    shipping-slow)   echo intlShippingSlowdown ;;         # 5sec 10sec
    email-leak)      echo emailMemoryLeak ;;              # 1x 10x 100x 1000x 10000x
    *)               echo "$1" ;;
  esac
}

cmd="${1:-list}"
case "$cmd" in
  list)
    python3 - "$FLAGS" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))["flags"]
for k, v in sorted(d.items()):
    mark = "  " if v["defaultVariant"] == "off" else "🔥"
    print(f"{mark} {k:32} {v['defaultVariant']:8} options: {', '.join(v['variants'])}")
PY
    exit 0 ;;
  reset) flag="__all__"; variant="off" ;;
  *) flag="$(scenario_flag "$cmd")"; variant="${2:-on}" ;;
esac

python3 - "$FLAGS" "$flag" "$variant" <<'PY'
import json, sys
path, flag, variant = sys.argv[1:]
doc = json.load(open(path))
flags = doc["flags"]
targets = list(flags) if flag == "__all__" else [flag]
for f in targets:
    if f not in flags:
        sys.exit(f"unknown flag '{f}'. Run: ./faultlens/fault.sh list")
    if variant not in flags[f]["variants"]:
        if flag == "__all__": continue
        sys.exit(f"'{f}' has no variant '{variant}'. Options: {', '.join(flags[f]['variants'])}")
    flags[f]["defaultVariant"] = variant
import os, tempfile
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
with os.fdopen(fd, "w") as fh:
    json.dump(doc, fh, indent=2); fh.write("\n")
os.chmod(tmp, 0o644)
os.replace(tmp, path)   # atomic: flagd never sees a half-written file
line = f"[{__import__('time').strftime('%Y-%m-%d %H:%M:%S')}] {'ALL FLAGS' if flag=='__all__' else flag} → {variant}"
print(line)
# history file so fault times can be matched against backend logs later
open(os.path.join(os.path.dirname(path), "..", "..", "faultlens", "fault-history.log"), "a").write(line + "\n")
PY
