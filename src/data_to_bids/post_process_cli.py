#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

# Allow both:
#   PYTHONPATH=src python -m data_to_bids.post_process_cli ...
# and:
#   python src/data_to_bids/post_process_cli.py ...
try:
    from .post_process_core import (
        normalize_subject,
        normalize_session,
        rename_fieldmap_files,
        update_scans_tsv,
        update_fieldmap_json,
    )
except ImportError:
    from post_process_core import (  # type: ignore
        normalize_subject,
        normalize_session,
        rename_fieldmap_files,
        update_scans_tsv,
        update_fieldmap_json,
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Post-process BIDS fmap + scans.tsv + fieldmap JSON metadata.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    p.add_argument(
        "-b", "--base-dir",
        required=True,
        help="Base directory containing BIDS subject folders (e.g. .../bidsdata).",
    )
    p.add_argument(
        "-s", "--subjects",
        nargs="+",
        required=True,
        help="Subject IDs (e.g. 01 02 or sub-01 sub-02).",
    )
    p.add_argument(
        "-e", "--sessions",
        nargs="+",
        default=None,
        help="Session IDs (e.g. 001 mrt1 or ses-001 ses-mrt1). If omitted, processes all ses-*.",
    )

    p.add_argument(
        "--b0-identifier",
        default="b0map_fmap0",
        help="Value for B0FieldIdentifier in fieldmap JSON.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change, but do not modify files.",
    )

    # Step selection: if none set, run all
    p.add_argument("--rename-files", action="store_true", help="Run only the file renaming step (or combine with others).")
    p.add_argument("--update-scans", action="store_true", help="Run only the scans.tsv update step (or combine with others).")
    p.add_argument("--update-json", action="store_true", help="Run only the fieldmap JSON update step (or combine with others).")

    # Privileges
    p.add_argument(
        "--sudo",
        action="store_true",
        help="Re-run this command via sudo (useful if files were created by Docker as root).",
    )

    return p


def _maybe_rerun_with_sudo(args: argparse.Namespace) -> None:
    # Only relevant on Unix-like systems
    if not hasattr(os, "geteuid"):
        return

    if not args.sudo:
        return

    if os.geteuid() == 0:
        return  # already root

    # Re-run this exact script as root. This is the most robust because it does not rely on PYTHONPATH.
    cmd = ["sudo", "-E", sys.executable, os.path.abspath(__file__)] + sys.argv[1:]

    print("Re-running with sudo:")
    print("  " + " ".join(cmd))

    subprocess.run(cmd, check=True)
    raise SystemExit(0)


def main() -> int:
    args = build_parser().parse_args()

    _maybe_rerun_with_sudo(args)

    subjects = [normalize_subject(x) for x in args.subjects]
    sessions_filter = [normalize_session(x) for x in args.sessions] if args.sessions else None

    run_any = args.rename_files or args.update_scans or args.update_json
    run_rename = args.rename_files or not run_any
    run_scans = args.update_scans or not run_any
    run_json = args.update_json or not run_any

    if run_rename:
        rename_fieldmap_files(
            subjects,
            base_dir=args.base_dir,
            sessions_filter=sessions_filter,
            dry_run=args.dry_run,
        )

    if run_scans:
        update_scans_tsv(
            subjects,
            base_dir=args.base_dir,
            sessions_filter=sessions_filter,
            dry_run=args.dry_run,
        )

    if run_json:
        update_fieldmap_json(
            subjects,
            base_dir=args.base_dir,
            sessions_filter=sessions_filter,
            b0_identifier=args.b0_identifier,
            dry_run=args.dry_run,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
