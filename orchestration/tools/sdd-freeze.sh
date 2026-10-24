#!/usr/bin/env bash
exec python3 "$(dirname "$0")/../../integration/ci/sdd_state.py" freeze "$@"
