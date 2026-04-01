#!/bin/bash
# Stress test for entropy tool

echo "=== ENTROPY Stress Test ==="
echo "WARNING: This will generate significant disk I/O"
echo "Press Ctrl+C to cancel"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Create test directory
mkdir -p entropy_stress_test
cd entropy_stress_test

# 1. Large file generation
echo "1. Generating 100MB file..."
time ../entropy.py -100mb -bin
echo ""

# 2. Many small files
echo "2. Generating 100x1MB files..."
time for i in {1..100}; do
    ../entropy.py -1mb -bin -multi 1
done
echo ""

# 3. Mixed formats
echo "3. Generating mixed formats..."
../entropy.py -10mb -txt
../entropy.py -10mb -img
../entropy.py -10mb -audio
echo ""

# 4. Maximum entropy mode
echo "4. Maximum entropy (mixed + environment)..."
time ../entropy.py -50mb -bin --mixed --use-env --analyze
echo ""

# 5. Fastest mode
echo "5. Fastest mode (--fast)..."
time ../entropy.py -100mb -bin --fast
echo ""

# 6. Concurrent generation
echo "6. Concurrent generation (3 processes)..."
time for i in {1..3}; do
    ../entropy.py -50mb -bin -multi 1 &
done
wait
echo ""

# Cleanup
cd ..
echo "Cleaning up..."
rm -rf entropy_stress_test

echo "=== Stress test completed ==="
