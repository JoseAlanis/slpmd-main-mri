# data_to_bids

Helpers for converting DICOM data to a BIDS layout with HeuDiConv and for post-processing
fieldmap/scans metadata afterward.

## Components
- `run_heudiconv.py`: Python wrapper around `scripts/run_heudiconv.sh`. It standardizes
  arguments (base path, input/output dirs, subjects, sessions) and runs HeuDiConv in Docker.
  The heuristic path passed via `--heuristic` must be reachable under the mounted base path.
- `post_process_cli.py`: CLI to post-process a BIDS dataset by renaming fieldmap files,
  updating `*_scans.tsv`, and patching fieldmap JSON metadata. Use `--dry-run` to preview
  changes and `--sudo` if files were created by Docker as root.
- `post_process_core.py`: Reusable functions used by the CLI.
- `templates/heuristic.py`: Reference heuristic template for organizing sequences into BIDS.
  Copy and adapt it to your protocol; it is not used automatically.

## Typical workflow
1. Convert DICOMs to BIDS with HeuDiConv (via the wrapper).
2. Post-process fieldmap naming and metadata.

## Examples
Run HeuDiConv (module execution from repo root):
```bash
PYTHONPATH=src python -m data_to_bids.run_heudiconv \
  -b /data/study_root \
  -i raw_mri_data \
  -O nifti_bids \
  -s md101 \
  -e mrt1 mrt2 \
  --heuristic nifti_bids/heuristic.py \
  --image nipy/heudiconv:1.3.4
```

Post-process fieldmaps and scans metadata:
```bash
PYTHONPATH=src python -m data_to_bids.post_process_cli \
  -b /data/study_root/nifti_bids \
  -s 01 02 \
  -e 001 002 \
  --dry-run
```

## Inputs/outputs (example tree)
Input DICOMs under the base path (mounted to `/base` in Docker):
```text
/data/study_root/
  raw_mri_data/
    md101/
      mrt1/
        A/
          DICOM_FILES...
```

Output BIDS layout (after conversion and post-processing):
```text
/data/study_root/
  nifti_bids/
    sub-md101/
      ses-mrt1/
        anat/
          sub-md101_ses-mrt1_T1w.nii.gz
        fmap/
          sub-md101_ses-mrt1_magnitude.nii.gz
          sub-md101_ses-mrt1_fieldmap.nii.gz
          sub-md101_ses-mrt1_fieldmap.json
        func/
          sub-md101_ses-mrt1_task-rest_run-01_bold.nii.gz
        sub-md101_ses-mrt1_scans.tsv
```

## Notes
- The wrapper locates `scripts/run_heudiconv.sh` by walking up from its own file location.
- HeuDiConv runs in Docker; `scripts/run_heudiconv.sh` expects a base path mounted to `/base`.
- Post-processing uses `pandas` to update `*_scans.tsv`.
