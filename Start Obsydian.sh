#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ -x 'dist/Obsydian Finder/Obsydian Finder' ]; then
  exec 'dist/Obsydian Finder/Obsydian Finder'
fi
exec .venv/bin/python launch.py
