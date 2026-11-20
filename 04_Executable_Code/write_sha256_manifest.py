#!/usr/bin/env python3
from pathlib import Path
import csv, hashlib

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "SHA256SUMS.csv"
EXCLUDED_DIRS = {".git", "__pycache__", ".venv", "venv", "Verification_Rerun", "Plots_Recreated", "RECOMPUTED_annual", "RECOMPUTED_seasonal"}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

items = []
for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or path == OUT:
        continue
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        continue
    if path.name in {".DS_Store", "Thumbs.db"} or path.suffix in {".pyc"}:
        continue
    items.append((rel.as_posix(), path.stat().st_size, sha256(path)))

with OUT.open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["relative_path", "bytes", "sha256"])
    w.writerows(items)

print(f"Wrote {len(items)} file hashes to {OUT.name}")
