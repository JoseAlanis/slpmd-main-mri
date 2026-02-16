#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_heudiconv_batch.sh -b BASE_HOST_PATH -i INPUT_DIR -O OUTPUT_DIR -s <subj...> -e <sess...> [options]

Required:
  -b, --base PATH                 Absolute host path mounted as /base
  -i, --input-dir NAME            Folder under /base used for input (e.g. bidsdata)
  -O, --output-dir NAME           Folder under /base used for output (e.g. bidsdata_conv)
  -s, --subjects  S1 [S2 ...]     One or more subject IDs
  -e, --sessions  E1 [E2 ...]     One or more session IDs

Options:
  --heuristic PATH                Heuristic path inside /base (default: /base/heuristic.py)
  --image IMAGE                   Docker image (default: nipy/heudiconv:1.3.3)
  --overwrite [true|false]        Overwrite existing outputs (default: false). If flag is present without value => true.
  --dry-run                       Print commands, do not run
  -h, --help                      Show this help

Examples:
  run_heudiconv_batch.sh -b /data -i bidsdata -O bidsdata -s 01 02 -e 001 002
  run_heudiconv_batch.sh -b /data -i bidsdata -O bidsdata_conv -s 01 -e 001 --overwrite true
  run_heudiconv_batch.sh -b /data -i bidsdata -O bidsdata_conv -s 01 02 -e 001 --dry-run
EOF
}

# Defaults
BASE_HOST=""
INPUT_DIR=""
OUTPUT_DIR=""
HEURISTIC="/base/heuristic.py"
IMAGE="nipy/heudiconv:1.3.3"
OVERWRITE="false"
DRY_RUN=0

subjects=()
sessions=()

# Parse args (supports multi-value -s/-e lists)
while [[ $# -gt 0 ]]; do
  case "$1" in
    -b|--base)
      BASE_HOST="${2:-}"; shift 2
      ;;
    -i|--input-dir)
      INPUT_DIR="${2:-}"; shift 2
      ;;
    -O|--output-dir)
      OUTPUT_DIR="${2:-}"; shift 2
      ;;
    -s|--subjects)
      shift 1
      while [[ $# -gt 0 && "$1" != -* ]]; do
        subjects+=("$1")
        shift 1
      done
      ;;
    -e|--sessions)
      shift 1
      while [[ $# -gt 0 && "$1" != -* ]]; do
        sessions+=("$1")
        shift 1
      done
      ;;
    --heuristic)
      HEURISTIC="${2:-}"; shift 2
      ;;
    --image)
      IMAGE="${2:-}"; shift 2
      ;;
    --overwrite)
      # Accept: --overwrite (means true) or --overwrite true|false
      if [[ $# -ge 2 && "${2:-}" != -* ]]; then
        OVERWRITE="$2"; shift 2
      else
        OVERWRITE="true"; shift 1
      fi
      ;;
    --dry-run)
      DRY_RUN=1; shift 1
      ;;
    -h|--help)
      usage; exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

# Validate required
if [[ -z "$BASE_HOST" || -z "$INPUT_DIR" || -z "$OUTPUT_DIR" || ${#subjects[@]} -eq 0 || ${#sessions[@]} -eq 0 ]]; then
  echo "Error: -b/-i/-O/-s/-e are required." >&2
  usage
  exit 2
fi

case "$OVERWRITE" in
  true|false) ;;
  *)
    echo "Error: --overwrite must be true or false (got: $OVERWRITE)" >&2
    exit 2
    ;;
esac

if [[ ! -d "$BASE_HOST" ]]; then
  echo "Error: base path is not a directory: $BASE_HOST" >&2
  exit 1
fi

if [[ ! -d "$BASE_HOST/$INPUT_DIR" ]]; then
  echo "Error: input dir does not exist under base: $BASE_HOST/$INPUT_DIR" >&2
  exit 1
fi

mkdir -p "$BASE_HOST/$OUTPUT_DIR"

# Normalize heuristic path to container path
if [[ "$HEURISTIC" != /base/* ]]; then
  HEURISTIC="/base/${HEURISTIC#/}"
fi

INPUT_CONT="/base/$INPUT_DIR"
OUTPUT_CONT="/base/$OUTPUT_DIR"

for subject in "${subjects[@]}"; do
  for session in "${sessions[@]}"; do
    echo "Processing subject ${subject}, session ${session}"

    output_dir_host="${BASE_HOST}/${OUTPUT_DIR}/sub-${subject}/ses-${session}"
    if [[ -d "$output_dir_host" && "$OVERWRITE" != "true" ]]; then
      echo "Output directory exists, skipping: ${output_dir_host}"
      echo "Use --overwrite true to force overwriting."
      continue
    fi

    cmd=(
      sudo docker run --rm -it
      -v "${BASE_HOST}:/base"
      "${IMAGE}"
      -d "${INPUT_CONT}/{subject}/{session}/A/*"
      -o "${OUTPUT_CONT}/"
      -f "${HEURISTIC}"
      -s "${subject}"
      -ss "${session}"
      -c dcm2niix
      -b
    )

    if [[ "$OVERWRITE" == "true" ]]; then
      cmd+=(--overwrite)
    fi

    if [[ "$DRY_RUN" -eq 1 ]]; then
      printf '  %q' "${cmd[@]}"
      echo
    else
      "${cmd[@]}"
    fi
  done
done

echo "Done."
