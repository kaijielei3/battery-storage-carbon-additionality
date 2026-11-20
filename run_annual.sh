#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
python "$ROOT/04_Executable_Code/V84_annual_restartable.py" --source "$ROOT/05_Source_Inputs/V77_RTS_SELECTED_UPLOAD.zip" --reserves "$ROOT/05_Source_Inputs/V82_RTS_RESERVES_UPLOAD.zip" --out "$ROOT/RECOMPUTED_annual" --prices 0,25 --max-windows 53 --timeout 120
