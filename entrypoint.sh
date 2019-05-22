#!/bin/bash
set -e

if [ "$1" = 'google_sheets_replicator' ]; then
    python google_sheets_data_replicator.py --id $REPLICATOR_CONFIG_SHEET
    exit 0
fi

exec "$@"