#!/usr/bin/env bash
set -euo pipefail
export PATH="/c/msys64/ucrt64/bin:/usr/bin:${PATH}"
cd /c/gitProjects/Stockfish/src
mingw32-make -j build
