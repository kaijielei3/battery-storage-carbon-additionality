# Data sources and use terms

## RTS-GMLC inputs

The dispatch inputs are based on the Reliability Test System – Grid Modernization Lab Consortium
(RTS-GMLC), maintained at:

https://github.com/GridMod/RTS-GMLC

The two archives in `05_Source_Inputs/` contain the exact selected source files used for the
calculations and the reserve time-series files used by the seven-product model. Each archive
contains a copy of `DATA_USE_DISCLAIMER.txt`. The RTS-GMLC repository identifies DOE/NREL/ALLIANCE
as the data source and asks that the data-use notice accompany copies. The NREL data-use terms
are reproduced in that file and are available at:

https://data.nrel.gov/node/90/license

The original extraction manifest records source-member paths and SHA-256 values. The upstream
Git commit identifier was not present in the supplied archive; the exact selected input files are
retained in this repository so the archived model inputs do not depend on a future upstream branch.

Please credit DOE/NREL/ALLIANCE in publications that use these data. Do not imply endorsement by
DOE, NREL, or ALLIANCE.

## Other equipment and life-cycle sources

The component evidence used in the reference calculations is listed in
`09_Reference_and_LCA_Evidence/Reference_Register.csv` and
`09_Reference_and_LCA_Evidence/SOURCE_PROVENANCE_REGISTER.csv`.

The register links to the BYD battery-module EPD, the Nortrafo transformer EPD, the DNV battery
system LCA report, the Sineng converter data sheet, and other cited sources. Those third-party
source documents are linked rather than mirrored in this repository. Their original terms remain
applicable.

The component values are source-specific reference quantities. They are not a harmonized,
complete bill of materials or a project-wide life-cycle footprint.

## Original code and project files

No general open-source license has been selected for the original code and project materials in
this repository. Third-party data and documents remain subject to their own terms. See `LICENSE.md`.
