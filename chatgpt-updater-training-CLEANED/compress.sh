#!/bin/sh

if [ -z "$1" ]; then
  echo "Usage: $0 <SUBDIR>"
  exit 1
fi

TARGET="$1"

jq -c . $TARGET/*.json > $TARGET.jsonl
