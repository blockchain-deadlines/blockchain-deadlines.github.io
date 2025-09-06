#!/bin/sh

if [ -z "$1" ]; then
  echo "Usage: $0 <SUBDIR>"
  exit 1
fi

TARGET="$1"

for f in $TARGET/*.json; do
  jq 'walk(if type=="object" then del(.parsed_arguments, .refusal, .audio, .function_call, .parsed, .annotations) else . end)' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done
