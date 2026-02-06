#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_heudiconv.sh -b BASE_HOST_PATH -i INPUT_DIR -O OUTPUT_DIR -s SUBJECT -e SESSION [--dry-run]

Example:
  run_heudiconv.sh -b /data -i MS2DP -O MS2DP_conv -s sub-01 -e ses-01
  run_heudiconv.sh -b /data -i MS2DP -O MS2DP_conv -s sub-01 -e ses-01 --dry-run
EOF
}

DRY_RUN=0

# Handle long options first
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --help) usage; exit 0 ;;
  esac
done

BASE_HOST=""
INPUT_DIR=""
OUTPUT_DIR=""
subj=""
sess=""

# Parse short options (ignore long ones)
while getopts ":b:i:O:s:e:h-:" opt; do
  case "$opt" in
    b) BASE_HOST="$OPTARG" ;;
    i) INPUT_DIR="$OPTARG" ;;
    O) OUTPUT_DIR="$OPTARG" ;;
    s) subj="$OPTARG" ;;
    e) sess="$OPTARG" ;;
    h) usage; exit 0 ;;
    -)
      # Handles things like --dry-run if they reach getopts
      case "$OPTARG" in
        dry-run) DRY_RUN=1 ;;
        help) usage; exit 0 ;;
        *) echo "Unknown option: --$OPTARG" >&2; usage; exit 2 ;;
      esac
      ;;
    \?) echo "Unknown option: -$OPTARG" >&2; usage; exit 2 ;;
    :)  echo "Missing argument for: -$OPTARG" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$BASE_HOST" || -z "$INPUT_DIR" || -z "$OUTPUT_DIR" || -z "$subj" || -z "$sess" ]]; then
  echo "Error: -b, -i, -O, -s, and -e are required." >&2
  usage
  exit 2
fi

if [[ ! -d "$BASE_HOST" ]]; then
  echo "Error: BASE_HOST_PATH is not a directory: $BASE_HOST" >&2
  exit 1
fi
if [[ ! -d "$BASE_HOST/$INPUT_DIR" ]]; then
  echo "Error: INPUT_DIR does not exist under base: $BASE_HOST/$INPUT_DIR" >&2
  exit 1
fi

mkdir -p "$BASE_HOST/$OUTPUT_DIR"

INPUT_CONT="/base/$INPUT_DIR"
OUTPUT_CONT="/base/$OUTPUT_DIR"

# Build the command as an array (prevents quoting bugs)
cmd=(
  sudo docker run --rm -it
  -v "${BASE_HOST}:/base"
  nipy/heudiconv:1.3.4
  -d "${INPUT_CONT}/{subject}/{session}/A/*"
  -o "${OUTPUT_CONT}"
  -f convertall
  -s "${subj}"
  -ss "${sess}"
  -c none
  --overwrite
)

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "DRY RUN: would execute:"
  printf '  %q' "${cmd[@]}"
  echo
  exit 0
fi

"${cmd[@]}"
