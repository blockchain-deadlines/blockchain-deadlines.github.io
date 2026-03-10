#!/bin/bash

> _data/conferences.yml
for f in _data/conferences_raw/*.yml; do
  cat "$f" >> _data/conferences.yml
  # Append a newline if the file doesn't end with one
  [ -s "$f" ] && [ "$(tail -c1 "$f" | wc -l)" -eq 0 ] && echo >> _data/conferences.yml
done
