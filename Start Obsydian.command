#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ -d 'dist/Obsydian Finder.app' ]; then
  exec open 'dist/Obsydian Finder.app'
fi
exec .venv/bin/python launch.py
