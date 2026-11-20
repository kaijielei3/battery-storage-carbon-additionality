#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
python "$ROOT/04_Executable_Code/plot_from_archive.py" --root "$ROOT" --out "$ROOT/08_Audit/Plots_Recreated"
