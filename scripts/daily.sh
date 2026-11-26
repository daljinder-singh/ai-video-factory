#!/usr/bin/env bash
# Daily job: make one video about today's trending educational topic and upload it to YouTube as PRIVATE.
# Run by the systemd user timer "videofactory-daily" (see README). Log: output/daily.log
cd "$(dirname "$0")/.." || exit 1
mkdir -p output
{
  echo "===== $(date '+%F %T') daily run ====="
  if ! ./run.sh --series trending --upload; then
    echo "Trending run failed; making a video from a random series instead"
    ./run.sh --series random --upload
  fi
} >> output/daily.log 2>&1
