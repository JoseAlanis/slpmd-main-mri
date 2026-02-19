#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_fmriprep.sh -b BASE_HOST -i INPUT_DIR -O OUTPUT_DIR -a {participant|group} --fs-license PATH [options]

Required:
  -b, --base PATH                 Host base path
  -i, --input-dir NAME|PATH       Input BIDS dir (relative to base or absolute). Mounted read-only to /data
  -O, --output-dir NAME|PATH      Output base dir (relative to base or absolute). Mounted to /out
  -a, --analysis-level LEVEL      participant or group
  --fs-license PATH               Path to FreeSurfer license.txt on the host

Optional:
  --output-subdir NAME            Subfolder under /out for fMRIPrep outputs (default: fmriprep)
                                 (set to "." to write directly into /out)
  -s, --subjects S1 [S2 ...]      Subject IDs (md101 or sub-md101). Passed as --participant-label (without 'sub-')
  -e, --sessions E1 [E2 ...]      Session IDs (mrt1 or ses-mrt1). Passed as --session-label (without 'ses-') (participant only)
  --output-spaces S1 [S2 ...]     Output spaces (default: MNI152NLin2009cAsym)
  --nprocs N                      Number of processes (default: 4)
  --omp-nthreads N                OMP threads per process (default: 2)
  --work-dir NAME|PATH            Work dir (relative to base or absolute). Default: work
  --image IMAGE                   Docker image (default: nipreps/fmriprep:25.2.4)
  --sudo                          Run docker with sudo (sudo docker ...)
  --dry-run                       Print the docker command, do not run
  -h, --help                      Show this help
EOF
}

BASE_HOST=""
INPUT_DIR=""
OUTPUT_DIR=""
ANALYSIS_LEVEL=""
FS_LICENSE=""
OUTPUT_SUBDIR="fmriprep"
IMAGE="nipreps/fmriprep:25.2.4"
NPROCS=4
OMP_NTHREADS=2
WORK_DIR="work"
DRY_RUN=0
USE_SUDO=0
OUTPUT_SPACES=("MNI152NLin2009cAsym")

subjects=()
sessions=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -b|--base) BASE_HOST="${2:-}"; shift 2 ;;
    -i|--input-dir) INPUT_DIR="${2:-}"; shift 2 ;;
    -O|--output-dir) OUTPUT_DIR="${2:-}"; shift 2 ;;
    -a|--analysis-level) ANALYSIS_LEVEL="${2:-}"; shift 2 ;;
    --fs-license) FS_LICENSE="${2:-}"; shift 2 ;;
    --output-subdir) OUTPUT_SUBDIR="${2:-}"; shift 2 ;;
    --image) IMAGE="${2:-}"; shift 2 ;;
    --nprocs) NPROCS="${2:-}"; shift 2 ;;
    --omp-nthreads) OMP_NTHREADS="${2:-}"; shift 2 ;;
    --work-dir) WORK_DIR="${2:-}"; shift 2 ;;
    --sudo) USE_SUDO=1; shift 1 ;;
    --dry-run) DRY_RUN=1; shift 1 ;;
    -s|--subjects)
      shift 1
      while [[ $# -gt 0 && "$1" != -* ]]; do
        subjects+=("$1"); shift 1
      done
      ;;
    -e|--sessions)
      shift 1
      while [[ $# -gt 0 && "$1" != -* ]]; do
        sessions+=("$1"); shift 1
      done
      ;;
    --output-spaces)
      shift 1
      OUTPUT_SPACES=()
      while [[ $# -gt 0 && "$1" != -* ]]; do
        OUTPUT_SPACES+=("$1"); shift 1
      done
      ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$BASE_HOST" || -z "$INPUT_DIR" || -z "$OUTPUT_DIR" || -z "$ANALYSIS_LEVEL" || -z "$FS_LICENSE" ]]; then
  echo "Error: -b, -i, -O, -a, and --fs-license are required." >&2
  usage
  exit 2
fi

case "$ANALYSIS_LEVEL" in
  participant|group) ;;
  *)
    echo "Error: --analysis-level must be 'participant' or 'group' (got: $ANALYSIS_LEVEL)" >&2
    exit 2
    ;;
esac

if [[ ! -d "$BASE_HOST" ]]; then
  echo "Error: base path is not a directory: $BASE_HOST" >&2
  exit 1
fi

if [[ ! -f "$FS_LICENSE" ]]; then
  echo "Error: FreeSurfer license not found: $FS_LICENSE" >&2
  exit 1
fi

# Resolve host paths (absolute or relative-to-base)
if [[ "$INPUT_DIR" = /* ]]; then
  INPUT_HOST="$INPUT_DIR"
else
  INPUT_HOST="$BASE_HOST/$INPUT_DIR"
fi

if [[ "$OUTPUT_DIR" = /* ]]; then
  OUTPUT_HOST="$OUTPUT_DIR"
else
  OUTPUT_HOST="$BASE_HOST/$OUTPUT_DIR"
fi

if [[ ! -d "$INPUT_HOST" ]]; then
  echo "Error: input BIDS dir not found: $INPUT_HOST" >&2
  exit 1
fi

mkdir -p "$OUTPUT_HOST"

# MRIQC-style work dir resolution (relative -> BASE_HOST)
if [[ -n "$WORK_DIR" ]]; then
  if [[ "$WORK_DIR" = /* ]]; then
    WORK_HOST="$WORK_DIR"
  else
    WORK_HOST="$BASE_HOST/$WORK_DIR"
  fi
else
  WORK_HOST=""
fi

if [[ -n "$WORK_HOST" ]]; then
  mkdir -p "$WORK_HOST"
fi

# Output path inside container
OUT_CONT="/out/${OUTPUT_SUBDIR}"
if [[ "$OUTPUT_SUBDIR" == "." ]]; then
  OUT_CONT="/out"
fi

# Normalize participant labels: strip "sub-"
norm_subjects=()
for s in "${subjects[@]}"; do
  norm_subjects+=("${s#sub-}")
done

norm_sessions=()
for s in "${sessions[@]}"; do
  norm_sessions+=("${s#ses-}")
done

DOCKER=(docker)
if [[ "$USE_SUDO" -eq 1 ]]; then
  DOCKER=(sudo docker)
fi

cmd=(
  "${DOCKER[@]}" run -ti --rm
  -v "${INPUT_HOST}:/data:ro"
  -v "${OUTPUT_HOST}:/out"
  -v "${FS_LICENSE}:/opt/freesurfer/license.txt:ro"
)

if [[ -n "$WORK_HOST" ]]; then
  cmd+=(-v "${WORK_HOST}:/work")
fi

cmd+=(
  "${IMAGE}"
  /data "${OUT_CONT}" "${ANALYSIS_LEVEL}"
  --fs-license-file /opt/freesurfer/license.txt
  --nprocs "${NPROCS}"
  --omp-nthreads "${OMP_NTHREADS}"
  --output-spaces "${OUTPUT_SPACES[@]}"
)

# Use /work only if we mounted it
if [[ -n "$WORK_HOST" ]]; then
  cmd+=(-w /work)
fi

if [[ "$ANALYSIS_LEVEL" == "participant" ]]; then
  if [[ ${#norm_subjects[@]} -gt 0 ]]; then
    cmd+=(--participant-label "${norm_subjects[@]}")
  fi
  if [[ ${#norm_sessions[@]} -gt 0 ]]; then
    cmd+=(--session-label "${norm_sessions[@]}")
  fi
else
  if [[ ${#norm_subjects[@]} -gt 0 || ${#norm_sessions[@]} -gt 0 ]]; then
    echo "Note: -s/--subjects and -e/--sessions are ignored for analysis level 'group'."
  fi
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "DRY RUN: would execute:"
  printf '  %q' "${cmd[@]}"
  echo
  exit 0
fi

"${cmd[@]}"
