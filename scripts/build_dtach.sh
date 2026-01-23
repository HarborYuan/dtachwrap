#!/bin/bash
set -e

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VENDOR_SRC="$REPO_ROOT/src/dtachwrap/_vendor/src/dtach"
VENDOR_BIN_DIR="$REPO_ROOT/src/dtachwrap/_vendor/bin"

echo "Building dtach from $VENDOR_SRC..."

# Ensure bin dir exists
mkdir -p "$VENDOR_BIN_DIR"

# Go to source
cd "$VENDOR_SRC"

# Clean previous build
if [ -f Makefile ]; then
    make distclean || make clean || true
fi

# Configure
echo "Running ./configure..."
./configure

# Make
NUM_CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)
echo "Running make with $NUM_CORES cores..."
make -j$NUM_CORES

# Strip (optional but recommended for size)
echo "Stripping binary..."
strip dtach || true

# Install (copy to bin dir)
cp dtach "$VENDOR_BIN_DIR/dtach"
chmod 755 "$VENDOR_BIN_DIR/dtach"

echo "dtach built and placed in $VENDOR_BIN_DIR/dtach"
