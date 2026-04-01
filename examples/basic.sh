#!/bin/bash
# Basic examples for entropy tool

echo "=== ENTROPY Basic Examples ==="
echo ""

# 1. Generate 1MB binary file
echo "1. Generating 1MB binary file..."
./entropy.py -1mb -bin
echo ""

# 2. Generate 1MB text file
echo "2. Generating 1MB text file..."
./entropy.py -1mb -txt
echo ""

# 3. Generate 1MB image
echo "3. Generating 1MB image..."
./entropy.py -1mb -img
echo ""

# 4. Generate 1MB audio
echo "4. Generating 1MB audio..."
./entropy.py -1mb -audio
echo ""

# 5. Generate with analysis
echo "5. Generating with entropy analysis..."
./entropy.py -500kb -bin --analyze
echo ""

# 6. Generate with visualization
echo "6. Generating with visualization..."
./entropy.py -500kb -img --visualize
echo ""

# 7. Generate multiple files
echo "7. Generating 5 files total 5MB..."
./entropy.py -5mb -bin -multi 5
echo ""

echo "=== All examples completed ==="
ls -lh entropy_*
