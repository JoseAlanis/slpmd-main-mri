#!/usr/bin/env python3
"""
Python wrapper for running HeuDiConv via the project shell runner.

Author:      José C. García Alanis
Date:        February 2026
Affiliation: Neuromodulation Unit, Philipps-Universität Marburg

Description:
    This module provides a command-line interface that calls the project-level
    shell script `scripts/run_heudiconv.sh`. The wrapper standardizes argument
    passing (base path, input/output directories, subjects, sessions) and keeps
    the pipeline callable via Python (useful for reproducibility and integration
    with other Python tooling).

    The underlying conversion is performed with HeuDiConv inside a Docker
    container. The heuristic file determines how sequences are mapped into a
    BIDS-compatible directory structure.

Usage:
    Preferred (module execution from repo root):
        PYTHONPATH=src python -m data_to_bids.run_heudiconv \
            -b /path/to/study_root \
            -i raw_mri_data \
            -O nifti_bids \
            -s md101 \
            -e mrt1 mrt2 mrt3 \
            --heuristic nifti_bids/heuristic.py \
            --image nipy/heudiconv:1.3.4

    Also supported (direct file execution):
        python src/data_to_bids/run_heudiconv.py \
            -b /path/to/study_root \
            -i raw_mri_data \
            -O nifti_bids \
            -s md101 \
            -e mrt1 mrt2 mrt3 \
            --heuristic nifti_bids/heuristic.py \
            --image nipy/heudiconv:1.3.4

Notes:
    - This wrapper locates `scripts/run_heudiconv.sh` by walking upward from its
      own file location until it finds the repository's `scripts/` directory.
    - The heuristic path passed via --heuristic is expected to be reachable from
      the mounted base path used by the Docker container (i.e., under -b/--base).
    - For the full set of conversion options, see HeuDiConv documentation.

References:
    - HeuDiConv documentation:
      https://heudiconv.readthedocs.io/en/latest/
    - HeuDiConv heuristics overview:
      https://heudiconv.readthedocs.io/en/latest/heuristics.html
"""

__author__ = "José C. García Alanis"
__affiliation__ = "Neuromodulation Unit, Philipps-Universität Marburg"
__date__ = "2026-02"
__version__ = "0.1.0"

import argparse
import subprocess
import sys
from pathlib import Path


def find_repo_script(script_rel: Path) -> Path:
    """
    Walk upward from this file's directory until we find script_rel.
    Expected layout:
      repo_root/
        scripts/run_heudiconv.sh
        src/data_to_bids/run_heudiconv.py
    """
    start = Path(__file__).resolve()
    for parent in [start.parent] + list(start.parents):
        candidate = parent / script_rel
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not find {script_rel} by walking up from {start}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Python wrapper that calls scripts/run_heudiconv.sh with provided arguments."
    )

    p.add_argument("-b", "--base", required=True,
                   help="Base host path mounted to /base in the container.")
    p.add_argument("-i", "--input-dir", required=True,
                   help="Input directory under base (e.g. raw_mri_data).")
    p.add_argument("-O", "--output-dir", required=True,
                   help="Output directory under base (e.g. nifti_bids).")
    p.add_argument("-s", "--subjects", nargs="+", required=True,
                   help="One or more subject IDs.")
    p.add_argument("-e", "--sessions", nargs="+", required=True,
                   help="One or more session IDs.")

    p.add_argument("--heuristic", default=None,
                   help="Heuristic path (passed through to run_heudiconv.sh).")
    p.add_argument("--image", default=None,
                   help="Docker image tag (passed through to run_heudiconv.sh).")

    p.add_argument("--overwrite", choices=["true", "false"], default="false",
                   help="Overwrite outputs (passed through).")
    p.add_argument("--dry-run", action="store_true",
                   help="Print commands, do not run (passed through).")

    # Anything after '--' is forwarded verbatim to the shell script
    p.add_argument("extra", nargs=argparse.REMAINDER,
                   help="Extra args after '--' are passed to run_heudiconv.sh.")

    return p


def main() -> int:
    args = build_parser().parse_args()

    try:
        sh_path = find_repo_script(Path("scripts") / "run_heudiconv.sh")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    cmd = [
        str(sh_path),
        "-b", args.base,
        "-i", args.input_dir,
        "-O", args.output_dir,
        "-s", *args.subjects,
        "-e", *args.sessions,
        "--overwrite", args.overwrite,
    ]

    if args.heuristic:
        cmd += ["--heuristic", args.heuristic]
    if args.image:
        cmd += ["--image", args.image]
    if args.dry_run:
        cmd += ["--dry-run"]

    if args.extra:
        # If you call: python -m data_to_bids.run_heudiconv ... -- --some-flag value
        cmd += args.extra

    # Always show the exact command being run
    print("Command:")
    print("  " + " ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        return e.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
