#!/usr/bin/env python3
"""
Python wrapper for running MRIQC via the project shell runner.

Author:      José C. García Alanis
Date:        February 2026
Affiliation: Neuromodulation Unit, Philipps-Universität Marburg

Description:
    This module calls the project-level shell script `scripts/run_mriqc.sh` and
    forwards standardized arguments for running MRIQC in Docker.

Notes:
    - MRIQC uses --participant-label for selecting subjects (typically without the
      'sub-' prefix).
    - The --no-sub flag disables submission of anonymized IQMs.

References:
    - MRIQC usage:
      https://mriqc.readthedocs.io/en/stable/running.html
"""

__author__ = "José C. García Alanis"
__affiliation__ = "Neuromodulation Unit, Philipps-Universität Marburg"
__date__ = "2026-02"
__version__ = "0.1.0"

import argparse
import subprocess
from pathlib import Path


def find_repo_script(script_rel: Path) -> Path:
    start = Path(__file__).resolve()
    for parent in [start.parent] + list(start.parents):
        candidate = parent / script_rel
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not find {script_rel} by walking up from {start}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Python wrapper that calls scripts/run_mriqc.sh with provided arguments."
    )

    p.add_argument("-b", "--base", required=True, help="Host base path.")
    p.add_argument("-i", "--input-dir", required=True, help="Input BIDS dir (relative to base or absolute).")
    p.add_argument("-O", "--output-dir", required=True, help="Output dir (relative to base or absolute).")
    p.add_argument(
        "-a", "--analysis-level",
        choices=["participant", "group"],
        required=True,
        help="MRIQC analysis level.",
    )

    p.add_argument("-s", "--subjects", nargs="+", default=None, help="Subject IDs (md101 or sub-md101).")
    p.add_argument("-e", "--sessions", nargs="+", default=None, help="Session IDs (mrt1 or ses-mrt1).")

    p.add_argument("--nprocs", type=int, default=4, help="Number of processes.")
    p.add_argument("--omp-nthreads", type=int, default=2, help="OMP threads per process.")
    p.add_argument("--work-dir", default=None, help="Working directory (relative to base or absolute).")
    p.add_argument("--image", default="nipreps/mriqc:24.0.2", help="Docker image tag.")

    p.add_argument("--allow-submission", action="store_true",
                   help="Do NOT pass --no-sub (default behavior is to pass --no-sub).")
    p.add_argument("--no-verbose-reports", action="store_true",
                   help="Do NOT pass --verbose-reports (default behavior is to pass --verbose-reports).")
    p.add_argument("--sudo", action="store_true",
                   help="Run docker with sudo (passed through to scripts/run_mriqc.sh).")
    p.add_argument("--dry-run", action="store_true", help="Print commands, do not run.")

    p.add_argument("--script", default=None,
                   help="Path to run_mriqc.sh (defaults to scripts/run_mriqc.sh found from repo root).")

    p.add_argument("extra", nargs=argparse.REMAINDER,
                   help="Extra args after '--' are passed to run_mriqc.sh.")

    return p


def main() -> int:
    args = build_parser().parse_args()

    sh_path = Path(args.script).expanduser().resolve() if args.script else find_repo_script(
        Path("scripts") / "run_mriqc.sh"
    )

    cmd = [
        str(sh_path),
        "-b", args.base,
        "-i", args.input_dir,
        "-O", args.output_dir,
        "-a", args.analysis_level,
        "--nprocs", str(args.nprocs),
        "--omp-nthreads", str(args.omp_nthreads),
        "--image", args.image,
    ]

    if args.subjects:
        cmd += ["-s", *args.subjects]
    if args.sessions:
        cmd += ["-e", *args.sessions]
    if args.work_dir:
        cmd += ["--work-dir", args.work_dir]
    if args.allow_submission:
        cmd += ["--allow-submission"]
    if args.no_verbose_reports:
        cmd += ["--no-verbose-reports"]
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
