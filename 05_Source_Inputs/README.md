# Source inputs

`V77_RTS_SELECTED_UPLOAD.zip` contains the RTS-GMLC source tables and 2020 day-ahead load,
wind, solar, rooftop PV, hydro, and CSP time-series files used by the dispatch model.
Its internal `V77_RTS_EXTRACT_MANIFEST.csv` records the source-member paths, byte counts,
and SHA-256 hashes for the extracted files.

`V82_RTS_RESERVES_UPLOAD.zip` contains the seven reserve products in their raw source layouts,
the normalized 8,784-hour series used by the model, and a manifest with per-series hashes.
The model reads `V82_RTS_RESERVE_HOURLY.csv` from this archive.

The upstream RTS-GMLC Git commit identifier was not recorded in the supplied research archive.
The exact input files used are therefore preserved here, with their internal extraction manifests
and repository-level hashes. The source ZIPs include `DATA_USE_DISCLAIMER.txt`.
See `../DATA_SOURCES_AND_LICENSES.md` for source attribution and use terms.
