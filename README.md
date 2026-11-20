# Carbon pricing and the climate additionality of grid-scale battery storage

This repository contains the model inputs, Python code, archived operating results, and validation files for a chronological dispatch study of grid-scale battery storage.

The case study adds a 10 MW / 40 MWh lithium iron phosphate battery at bus 101 of the 2020 RTS-GMLC test system. The annual experiment compares storage and no-storage dispatch under carbon charges of USD 0/t and USD 25/t. Separate seasonal experiments use four 168-hour windows and carbon charges of USD 0, 25, 75, and 200/t.

## Main archived results

The annual paired simulations cover all 8,784 hours of the 2020 leap year.

| Carbon charge | Avoided direct combustion CO₂ | Interpretation |
|---:|---:|---|
| USD 0/t | −980.65 t | Storage increases direct combustion CO₂ |
| USD 25/t | +4,328.94 t | Storage avoids direct combustion CO₂ |

The difference between the two storage effects is 5,309.59 t CO₂. These are model results from matched dispatch cases, not measured market outcomes.

## Repository contents

- `03_Figures_and_Tables/` — annual, monthly, and seasonal summary tables and figures.
- `04_Executable_Code/` — dispatch models, annual restartable runner, independent verifier, plotting script, and package requirements.
- `05_Source_Inputs/` — the exact selected RTS-GMLC and reserve input archives used by the calculations, with extraction manifests and data-use notices.
- `06_Results/` — four annual hourly trajectories, annual summaries, and 212 saved window records (CSV, JSON, and NPZ).
- `07_Seasonal_Results/` — the 32 seasonal arm outputs and paired summaries.
- `08_Audit/` — data dictionary, prior validation records, and figures regenerated from the archived numeric tables.
- `09_Reference_and_LCA_Evidence/` — source registers, equipment reference calculations, and the PCS process calculator.

The manuscript and journal-specific submission files are not included.

## Quick start

Use Python 3.13.5 with the package versions listed in `TESTED_ENVIRONMENT.md`.

```bash
python -m pip install -r 04_Executable_Code/requirements.txt
```

### 1. Verify the archived annual results

This checks the saved hourly trajectories, calendar, battery state-of-charge recursion, power limits, network limits, reserve adequacy, window records, state-vector hash chain, annual totals, monthly reconciliation, seasonal pairs, and the SHA-256 identity of the two input archives.

```bash
python 04_Executable_Code/verify_release.py --root . --out 08_Audit/Verification_Rerun
```

On Windows, double-click `RUN_VERIFY_WINDOWS.cmd`.

The verifier checks the archived outputs; it does not solve the optimization again. The original archive passed 58 checks. The verifier in this repository adds eight checks for the input-archive hashes.

### 2. Recreate the three figures

```bash
python 04_Executable_Code/plot_from_archive.py --root . --out 08_Audit/Plots_Recreated
```

On Windows, double-click `RUN_PLOTS_WINDOWS.cmd`.

The plots are rebuilt from the archived annual, monthly, and seasonal CSV summaries.

### 3. Re-run the full annual dispatch experiment

```bash
python 04_Executable_Code/V84_annual_restartable.py --source 05_Source_Inputs/V77_RTS_SELECTED_UPLOAD.zip --reserves 05_Source_Inputs/V82_RTS_RESERVES_UPLOAD.zip --out RECOMPUTED_annual --prices 0,25 --max-windows 53 --timeout 120
```

On Windows, double-click `RUN_ANNUAL_WINDOWS.cmd`.

The run consists of 53 sequential windows per arm, with a maximum of 168 implemented hours per window (the final window contains 48 hours). It therefore solves 212 LP windows across the two carbon prices and two battery states. Each window inherits the preceding thermal-generator state and returns the battery state of charge to 20 MWh at the window boundary. The output directory is separate from the archived results.

### 4. Re-run the seasonal experiments

```bash
python 04_Executable_Code/V84_seven_product_ED.py --source 05_Source_Inputs/V77_RTS_SELECTED_UPLOAD.zip --reserves 05_Source_Inputs/V82_RTS_RESERVES_UPLOAD.zip --out RECOMPUTED_seasonal --starts 0,2184,4392,6576 --hours 168 --prices 0,25,75,200 --timeout 90
```

On Windows, double-click `RUN_SEASONAL_WINDOWS.cmd`.

This produces the four selected 168-hour windows at each of the four carbon prices, with storage and no-storage arms.

### 5. Recreate the PCS reference calculation

```bash
python 09_Reference_and_LCA_Evidence/PCS_reference_calculator.py
```

This regenerates the PCS process ledger and source register. The hardware values are source-specific reference calculations, not a harmonized whole-station life-cycle inventory.

### 6. Refresh the repository file hashes

```bash
python 04_Executable_Code/write_sha256_manifest.py
```

This updates `SHA256SUMS.csv` for the tracked repository files. The manifest excludes itself, `.git`, caches, and generated rerun folders.

## Model scope

The annual model is a rolling chronological linear economic-dispatch formulation, not a full-horizon annual optimization and not a binary thermal unit-commitment model.

The main operating specification includes:

- 73 buses and 120 AC branches represented with a DC power-flow approximation.
- 158 source generator records; the annual dispatch uses 102 candidate generation variables.
- 72 fossil units with inter-hour ramp constraints.
- Seven separately allocated reserve products, with shared generator headroom, source eligibility, regional restrictions, and response-time/ramp limits.
- A 10 MW / 40 MWh battery with 85% round-trip efficiency and state of charge bounded between 8 and 40 MWh.
- Fixed rooftop PV and hydro injections, with wind and utility PV dispatched within available output.
- A 168-hour rolling implementation with thermal-generator continuation and a 20 MWh terminal battery state at each window boundary.

The battery is modeled as an energy resource and is not counted as a provider of the seven reserve products. Reserve activation, N−1 contingency deliverability, stochastic dispatch, binary unit commitment, thermal minimum-output constraints, and reservoir hydro optimization are not modeled. The annual results should be interpreted within these boundaries.

Direct combustion GWP100 in the archived outputs uses the source CO₂, CH₄, and N₂O factors, with characterization factors of 27 for CH₄ and 273 for N₂O. Upstream fuel-cycle emissions are not included in that direct-combustion account.

The life-cycle section is a threshold framework. The equipment values in `09_Reference_and_LCA_Evidence/` come from separate source declarations and process references; they are not combined into a harmonized, complete station footprint or a numerical whole-plant net GWP100 result.

## Reproducibility notes

- The exact selected input files used by the model are retained in `05_Source_Inputs/`. Their internal manifests record the source-member paths and file hashes.
- The upstream RTS-GMLC Git commit identifier was not preserved in the supplied archive. The included input archives therefore serve as the fixed input snapshot for this release.
- The original solver environment was not fully recorded. `TESTED_ENVIRONMENT.md` identifies the environment used to test this prepared repository.
- The saved hourly files contain system-level emissions, storage operation, line-loading ratios, and reserve totals. They do not preserve every per-generator primal variable for every hour; those variables can be regenerated by re-solving the model.
- Different SciPy/HiGHS versions may select different cost-equivalent optima. Numerical comparison should focus on the objective, emissions accounting, and constraint tolerances, not bitwise equality of every dispatch variable.
- The full annual rerun is computationally more demanding than the read-only verification.

## Data sources and citation

RTS-GMLC source information and the applicable data-use notice are documented in `DATA_SOURCES_AND_LICENSES.md` and `05_Source_Inputs/DATA_USE_DISCLAIMER.txt`. Publications using the RTS-GMLC data should credit DOE/NREL/ALLIANCE.

The equipment and life-cycle references are listed in `09_Reference_and_LCA_Evidence/Reference_Register.csv`. The original third-party EPDs and reports are linked there rather than redistributed here.

For author information, see `CITATION.cff`.
