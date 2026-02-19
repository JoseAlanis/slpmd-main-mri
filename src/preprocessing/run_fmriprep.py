#!/usr/bin/env python3
"""
Python wrapper for running fMRIPrep via the project shell runner.

Author:      José C. García Alanis
Date:        February 2026
Affiliation: Neuromodulation Unit, Philipps-Universität Marburg

Description:
    Calls the project-level shell script `scripts/run_fmriprep.sh` and forwards
    standardized arguments for running fMRIPrep in Docker.

Usage:
    python src/data_to_bids/run_fmriprep.py \
      -b /path/to/study_root \
      -i bidsdata \
      -O bidsdata/derivatives \
      -a participant \
      --fs-license /path/to/license.txt \
      -s sub-01 \
      -e ses-001 \
      --output-spaces MNI152NLin2009cAsym \
      --nprocs 4 \
      --omp-nthreads 2 \
      --work-dir work \
      --sudo \
      --dry-run

References:
    - fMRIPrep CLI:
      https://fmriprep.org/en/stable/usage.html#command-line-arguments
"""

__author__ = "José C. García Alanis"
__affiliation__ = "Neuromodulation Unit, Philipps-Universität Marburg"
__date__ = "2026-02"
__version__ = "0.1.0"

import argparse
import subprocess
from pathlib import Path


def find_repo_script(script_rel: Path) -> Path:
    """
    Walk upward from this file location until we find script_rel.
    Expected layout:
      repo_root/
        scripts/run_fmriprep.sh
        src/data_to_bids/run_fmriprep.py
    """
    start = Path(__file__).resolve()
    for parent in [start.parent] + list(start.parents):
        candidate = parent / script_rel
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not find {script_rel} by walking up from {start}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Python wrapper that calls scripts/run_fmriprep.sh with provided arguments."
    )

    p.add_argument("-b", "--base", required=True, help="Host base path.")
    p.add_argument("-i", "--input-dir", required=True, help="Input BIDS dir (relative to base or absolute).")
    p.add_argument("-O", "--output-dir", required=True, help="Output base dir (relative to base or absolute).")
    p.add_argument(
        "-a", "--analysis-level",
        choices=["participant", "group"],
        required=True,
        help="fMRIPrep analysis level.",
    )

    p.add_argument("--fs-license", required=True, help="Path to FreeSurfer license.txt on host.")
    p.add_argument("--output-subdir", default="fmriprep",
                   help="Subfolder under /out for outputs (use '.' to write directly into /out).")

    p.add_argument("-s", "--subjects", nargs="+", default=None,
                   help="Subject IDs (md101 or sub-md101). Only used for participant level.")
    p.add_argument("-e", "--sessions", nargs="+", default=None,
                   help="Session IDs (mrt1 or ses-mrt1). Only used for participant level.")
    p.add_argument("--output-spaces", nargs="+", default=["MNI152NLin2009cAsym"],
                   help="Output spaces (one or more).")

    p.add_argument("--nprocs", type=int, default=4, help="Number of processes.")
    p.add_argument("--omp-nthreads", type=int, default=2, help="OMP threads per process.")
    p.add_argument("--work-dir", default="work",
                   help="Work dir (relative to base or absolute). Resolution is handled by the shell script.")

    p.add_argument("--image", default="nipreps/fmriprep:25.2.4", help="Docker image tag.")
    p.add_argument("--sudo", action="store_true", help="Run docker with sudo (passed through).")
    p.add_argument("--dry-run", action="store_true", help="Print commands, do not run.")

    p.add_argument("--script", default=None,
                   help="Path to run_fmriprep.sh (defaults to scripts/run_fmriprep.sh found from repo root).")

    p.add_argument("extra", nargs=argparse.REMAINDER,
                   help="Extra args after '--' are passed to run_fmriprep.sh.")

    return p


def main() -> int:
    args = build_parser().parse_args()

    sh_path = Path(args.script).expanduser().resolve() if args.script else find_repo_script(
        Path("scripts") / "run_fmriprep.sh"
    )

    cmd = [
        str(sh_path),
        "-b", args.base,
        "-i", args.input_dir,
        "-O", args.output_dir,
        "-a", args.analysis_level,
        "--fs-license", args.fs_license,
        "--output-subdir", args.output_subdir,
        "--nprocs", str(args.nprocs),
        "--omp-nthreads", str(args.omp_nthreads),
        "--work-dir", args.work_dir,
        "--image", args.image,
        "--output-spaces", *args.output_spaces,
    ]

    if args.subjects:
        cmd += ["-s", *args.subjects]
    if args.sessions:
        cmd += ["-e", *args.sessions]
    if args.sudo:
        cmd += ["--sudo"]
    if args.dry_run:
        cmd += ["--dry-run"]
    if args.extra:
        cmd += args.extra

    print("Command:")
    print("  " + " ".join(cmd))

    subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
