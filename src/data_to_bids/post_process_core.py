"""
Post-processing utilities for BIDS fieldmap outputs.

Author:      José C. García Alanis
Date:        February 2026
Affiliation: Neuromodulation Unit, Philipps-Universität Marburg

Description:
    Reusable functions to post-process a BIDS dataset after DICOM-to-BIDS conversion.
    Focuses on fieldmap file naming, scans.tsv consistency, and fieldmap JSON metadata.

References:
    - BIDS MRI specification:
      https://bids-specification.readthedocs.io/en/stable/modality-specific-files/magnetic-resonance-imaging-data.html
    - Neurostars thread:
      https://neurostars.org/t/does-direct-field-mapping-for-field-map-require-magnitude-nii-gz/20299/16
"""

__author__ = "José C. García Alanis"
__affiliation__ = "Neuromodulation Unit, Philipps-Universität Marburg"
__date__ = "2026-02"
__version__ = "0.1.0"


import os
import glob
import json
from typing import Iterable, List, Optional

import pandas as pd


def normalize_subject(s: str) -> str:
    return s if s.startswith("sub-") else f"sub-{s}"


def normalize_session(s: str) -> str:
    return s if s.startswith("ses-") else f"ses-{s}"


def iter_session_paths(subject_path: str, sessions_filter: Optional[List[str]] = None) -> Iterable[str]:
    """
    Yield session directories under subject_path.
    If sessions_filter is provided (e.g. ["ses-001", "ses-mrt1"]), only yield those if they exist.
    """
    if sessions_filter:
        for ses in sessions_filter:
            ses_path = os.path.join(subject_path, ses)
            if os.path.isdir(ses_path):
                yield ses_path
            else:
                print(f"Session directory not found: {ses_path}")
    else:
        for ses_path in sorted(glob.glob(os.path.join(subject_path, "ses-*"))):
            if os.path.isdir(ses_path):
                yield ses_path


def rename_fieldmap_files(
    subjects: List[str],
    base_dir: str = ".",
    sessions_filter: Optional[List[str]] = None,
    dry_run: bool = False,
) -> None:
    """
    Renames files in ses-*/fmap:
      fieldmap1 -> magnitude
      fieldmap2 -> fieldmap
    """
    for subject in subjects:
        subject_path = os.path.join(base_dir, subject)
        if not os.path.isdir(subject_path):
            print(f"Directory not found: {subject_path}")
            continue

        for ses_path in iter_session_paths(subject_path, sessions_filter=sessions_filter):
            fmap_dir = os.path.join(ses_path, "fmap")
            if not os.path.isdir(fmap_dir):
                continue

            for filename in sorted(os.listdir(fmap_dir)):
                src_path = os.path.join(fmap_dir, filename)
                if not os.path.isfile(src_path):
                    continue

                if "fieldmap1" in filename:
                    new_filename = filename.replace("fieldmap1", "magnitude")
                elif "fieldmap2" in filename:
                    new_filename = filename.replace("fieldmap2", "fieldmap")
                else:
                    continue

                dst_path = os.path.join(fmap_dir, new_filename)

                if os.path.exists(dst_path):
                    print(f"Skip rename (target exists): {src_path} -> {dst_path}")
                    continue

                if dry_run:
                    print(f"Would rename: {src_path} -> {dst_path}")
                else:
                    print(f"Renaming: {src_path} -> {dst_path}")
                    os.rename(src_path, dst_path)


def update_scans_tsv(
    subjects: List[str],
    base_dir: str = ".",
    sessions_filter: Optional[List[str]] = None,
    dry_run: bool = False,
) -> None:
    """
    Updates *_scans.tsv in each session by replacing in the 'filename' column:
      fieldmap1 -> magnitude
      fieldmap2 -> fieldmap
    """
    for subject in subjects:
        subject_path = os.path.join(base_dir, subject)
        if not os.path.isdir(subject_path):
            print(f"Directory not found: {subject_path}")
            continue

        for ses_path in iter_session_paths(subject_path, sessions_filter=sessions_filter):
            for tsv_file in sorted(glob.glob(os.path.join(ses_path, "*_scans.tsv"))):
                try:
                    df = pd.read_csv(tsv_file, sep="\t")

                    if "filename" not in df.columns:
                        print(f"'filename' column not found in: {tsv_file}")
                        continue

                    original = df["filename"].copy()

                    df["filename"] = df["filename"].str.replace("fieldmap1", "magnitude", regex=False)
                    df["filename"] = df["filename"].str.replace("fieldmap2", "fieldmap", regex=False)

                    if df["filename"].equals(original):
                        print(f"No changes needed for: {tsv_file}")
                        continue

                    changed_rows = int((df["filename"] != original).sum())

                    if dry_run:
                        print(f"Would update TSV ({changed_rows} rows): {tsv_file}")
                    else:
                        print(f"Updating TSV ({changed_rows} rows): {tsv_file}")
                        df.to_csv(tsv_file, sep="\t", index=False)

                except Exception as e:
                    print(f"Error processing {tsv_file}: {e}")


def update_fieldmap_json(
    subjects: List[str],
    base_dir: str = ".",
    sessions_filter: Optional[List[str]] = None,
    b0_identifier: str = "b0map_fmap0",
    dry_run: bool = False,
) -> None:
    """
    Adds/updates IntendedFor and B0FieldIdentifier in the fieldmap JSON.
    Expects fieldmap JSON name after renaming:
      {subject}_{ses-id}_fieldmap.json
    """
    for subject in subjects:
        subject_path = os.path.join(base_dir, subject)
        if not os.path.isdir(subject_path):
            print(f"Directory not found: {subject_path}")
            continue

        for ses_path in iter_session_paths(subject_path, sessions_filter=sessions_filter):
            ses_id = os.path.basename(ses_path)
            func_dir = os.path.join(ses_path, "func")
            fmap_dir = os.path.join(ses_path, "fmap")

            if not os.path.isdir(func_dir) or not os.path.isdir(fmap_dir):
                print(f"Missing func or fmap directory in: {ses_path}")
                continue

            bold_files = sorted(
                glob.glob(os.path.join(func_dir, "*_bold.nii.gz")))
            intended_for = [
                "bids::" + os.path.relpath(bold_file, start=base_dir).replace(
                    os.sep, "/")
                for bold_file in bold_files
            ]

            pattern = os.path.join(fmap_dir, f"{subject}_{ses_id}_fieldmap.json")
            matches = glob.glob(pattern)
            if not matches:
                print(f"No fieldmap JSON found in: {fmap_dir} (pattern: {pattern})")
                continue

            fmap_json_path = matches[0]

            try:
                with open(fmap_json_path, "r") as f:
                    fmap_data = json.load(f)

                new_data = dict(fmap_data)
                new_data["IntendedFor"] = intended_for
                new_data["B0FieldIdentifier"] = b0_identifier

                if new_data == fmap_data:
                    print(f"No changes needed for: {fmap_json_path}")
                    continue

                if dry_run:
                    print(f"Would update JSON: {fmap_json_path}")
                else:
                    print(f"Updating JSON: {fmap_json_path}")
                    with open(fmap_json_path, "w") as f:
                        json.dump(new_data, f, indent=4)

            except Exception as e:
                print(f"Error updating {fmap_json_path}: {e}")
