# Scripts

Quick notes on what each Bash script in this folder does. Run any script with `-h`/`--help` to see full usage.

## extract_subject_labels.sh
- Scans a study root for `MD*_MRI/MD*_MRT*` folders.
- Finds `LABEL.HTM` in each scan folder and extracts `Patient Name`, `Patient ID`, and `Study Date`.
- Writes a semicolon-separated CSV (default `labels.csv`) with a header; use `-r` to point at the root and `-o` to set output.
Example:
```bash
./scripts/extract_subject_labels.sh -r /data/studies -o /tmp/labels.csv
```

## run_heudiconv_single.sh
- Runs the `nipy/heudiconv:1.3.3` Docker image for a single subject/session.
- Uses the `convertall` heuristic with `-c none` to inspect DICOMs and emit heudiconv outputs under the chosen output directory.
- Requires `sudo` + Docker; use `-b` (base host path), `-i` (input dir), `-O` (output dir), `-s` (subject), `-e` (session), and optional `--dry-run`.
Example:
```bash
./scripts/run_heudiconv_single.sh -b /data -i MS2DP -O MS2DP_conv -s sub-01 -e ses-01 --dry-run
```

## run_heudiconv.sh
- Batch runs heudiconv for multiple subjects/sessions using a heuristic file (default `/base/heuristic.py`).
- Converts DICOMs to BIDS using `dcm2niix` inside the Docker image (default `nipy/heudiconv:1.3.3`).
- Supports `--overwrite` and `--dry-run`; requires `sudo` + Docker and an input/output directory under the mounted base path.
Example:
```bash
./scripts/run_heudiconv.sh -b /data -i bidsdata -O bidsdata_conv -s 01 02 -e 001 002 --dry-run
```
