#!/bin/bash

> _data/conferences.yml
for f in _data/conferences_raw/*.yml; do
  cat "$f" >> _data/conferences.yml
  # Append a newline if the file doesn't end with one
  if [ -s "$f" ] && [ "$(tail -c1 "$f" | wc -l)" -eq 0 ]; then
    echo >> _data/conferences.yml
  fi
done
