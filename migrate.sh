#!/bin/bash
#
# Run the incremental migration pipeline.
#
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
exec python3 -m aihelpers.incremental_migrate "$@"
