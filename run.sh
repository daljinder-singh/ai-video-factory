#!/usr/bin/env bash
# Make a video. All options are passed through, e.g.: ./run.sh --topic "Black hole" --lang hinglish
cd "$(dirname "$0")"
PYTHONPATH=src exec .venv/bin/python -u -m videofactory "$@"
