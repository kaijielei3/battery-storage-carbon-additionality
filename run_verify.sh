#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
python "$ROOT/04_Executable_Code/verify_release.py" --root "$ROOT" --out "$ROOT/08_Audit/Verification_Rerun"
