BASE_HOST="/media/josealanis/epfx0/jose/neuromod/main_study/mri_data/"
BASE_CONT="/base"

sudo docker run --rm -it \
  -v "${BASE_HOST}:${BASE_CONT}" \
  nipy/heudiconv:1.3.4 \
  -d "${BASE_CONT}/MS2DP/{subject}/{session}/*" \
  -o "${BASE_CONT}/MS2DP_conv/" \
  -f convertall \
  -s 01 \
  -ss 001 \
  -c none \
  --overwrite