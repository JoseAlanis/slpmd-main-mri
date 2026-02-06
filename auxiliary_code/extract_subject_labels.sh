#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 -r <root_path> [-o <output_csv>] [-h]

Options:
  -r  Root directory that contains MD*_MRI folders (required)
  -o  Output CSV path (default: labels.csv)
  -h  Show this help

Example:
  $0 -r /data/studies -o labels.csv
EOF
}

root=""
out="labels.csv"

while getopts ":r:o:h" opt; do
  case "$opt" in
    r) root="$OPTARG" ;;
    o) out="$OPTARG" ;;
    h) usage; exit 0 ;;
    \?) echo "Error: Unknown option -$OPTARG" >&2; usage; exit 2 ;;
    :)  echo "Error: Option -$OPTARG requires an argument" >&2; usage; exit 2 ;;
  esac
done
shift $((OPTIND - 1))

if [[ -z "$root" ]]; then
  echo "Error: -r <root_path> is required" >&2
  usage
  exit 2
fi
if [[ ! -d "$root" ]]; then
  echo "Error: root_path is not a directory: $root" >&2
  exit 1
fi

# Normalize root (remove trailing slash unless it's "/")
if [[ "$root" != "/" ]]; then
  root="${root%/}"
fi

# CSV header (semicolon-separated)
printf 'top_folder;scan_folder;relative_path;patient_name;patient_id;study_date\n' > "$out"

# CSV-escape helper (wrap in quotes; double any internal quotes)
csv_escape() {
  local s="$1"
  s=${s//\"/\"\"}
  printf '"%s"' "$s"
}

# Extract "Field Name: VALUE" from LABEL.HTM.
# Works even if file is UTF-16-ish (has lots of \x00 bytes) and everything is on one line.
extract_field() {
  local file="$1"
  local field="$2"
  local val

  val="$(
    FIELD="$field" perl -0777 -ne '
      my $field = quotemeta($ENV{FIELD} // "");
      s/\x00//g;                       # handle UTF-16LE/BE-ish content
      s/&nbsp;|&#160;/ /gi;            # common HTML spaces
      if (/$field\s*:\s*([^<]*)/i) {   # capture up to next "<" (e.g., before <BR>)
        my $v = $1;
        $v =~ s/^\s+|\s+$//g;
        print $v;
      }
    ' "$file" 2>/dev/null || true
  )"

  if [[ -z "$val" ]] || [[ "${val,,}" == "null" ]]; then
    printf "NA"
  else
    printf "%s" "$val"
  fi
}

# Iterate expected structure: root/MD*_MRI/MD*_MRT*
find "$root" -mindepth 1 -maxdepth 1 -type d -name 'MD*_MRI' -print0 |
while IFS= read -r -d '' mri_dir; do
  top_folder="$(basename "$mri_dir")"
  prefix="${top_folder%_MRI}"  # e.g. MD100

  find "$mri_dir" -mindepth 1 -maxdepth 1 -type d -name "${prefix}_MRT*" -print0 |
  while IFS= read -r -d '' scan_dir; do
    scan_folder="$(basename "$scan_dir")"

    rel="${scan_dir#"$root"/}"
    rel="${rel#./}"

    # Find LABEL.HTM (case-insensitive) in scan_dir (not recursive)
    label_file="$(
      find "$scan_dir" -maxdepth 1 -type f \( -iname 'LABEL.HTM' \) -print -quit 2>/dev/null || true
    )"

    patient_name="NA"
    patient_id="NA"
    study_date="NA"

    if [[ -n "$label_file" ]]; then
      patient_name="$(extract_field "$label_file" "Patient Name")"
      patient_id="$(extract_field "$label_file" "Patient ID")"
      study_date="$(extract_field "$label_file" "Study Date")"
    fi

    printf '%s;%s;%s;%s;%s;%s\n' \
      "$(csv_escape "$top_folder")" \
      "$(csv_escape "$scan_folder")" \
      "$(csv_escape "$rel")" \
      "$(csv_escape "$patient_name")" \
      "$(csv_escape "$patient_id")" \
      "$(csv_escape "$study_date")" >> "$out"
  done
done

echo "Wrote: $out"
