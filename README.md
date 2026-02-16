# slpmd-main-mri

## Requirements (for DICOM to BIDS)
- Docker (used by HeuDiConv via `scripts/run_heudiconv.sh`)
- HeuDiConv Docker image (defaults to `nipy/heudiconv:1.3.3` in scripts)

## Quick start
- DICOM-to-BIDS workflow docs live in `src/data_to_bids/README.md`.
- Run HeuDiConv via the Python wrapper, then post-process fieldmaps/scans metadata.
