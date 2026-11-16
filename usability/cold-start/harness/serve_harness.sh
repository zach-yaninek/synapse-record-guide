#!/bin/sh
# serve_harness.sh: start the shift agent's token proxy and the recorder, both on loopback.
#
#   agent's MCP client -> recorder 127.0.0.1:8798 -> token proxy 127.0.0.1:8799 -> RECORD_UPSTREAM
#
# The token proxy is agents/token_proxy.py from this repository. It reads the shift agent's
# client credentials from SHIFT_ENV_FILE into its own environment only, never prints them,
# and adds a fresh bearer token to each request it forwards. The recorder appends every
# exchange to WIRE_LOG. Stop both with Ctrl-C (or by ending this script).
#
# Usage:
#   RECORD_UPSTREAM=https://<record host>/mcp SHIFT_ENV_FILE=/path/to/.env.shift \
#   WIRE_LOG=/path/to/wire.jsonl PYTHON=python3.13 sh serve_harness.sh
set -eu
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../../.." && pwd)
python=${PYTHON:-python3.13}
: "${RECORD_UPSTREAM:?set RECORD_UPSTREAM to the /mcp URL of the record}"
: "${SHIFT_ENV_FILE:?set SHIFT_ENV_FILE to the credentials file of the shift agent}"
: "${WIRE_LOG:?set WIRE_LOG to the log file of the recorder}"
(set -a; . "$SHIFT_ENV_FILE"; set +a; cd "$repo"; exec "$python" -m agents.token_proxy \
    --listen 127.0.0.1:8799 --upstream "$RECORD_UPSTREAM") &
proxy=$!
"$python" "$here/recorder.py" --listen 127.0.0.1:8798 --upstream http://127.0.0.1:8799/mcp --log "$WIRE_LOG" &
recorder=$!
trap 'kill "$proxy" "$recorder" 2>/dev/null' EXIT INT TERM
wait
