#!/bin/bash
# Advanced examples for entropy tool

echo "=== ENTROPY Advanced Examples ==="
echo ""

# 1. Mixed entropy sources
echo "1. Mixed entropy sources (highest quality)..."
./entropy.py -5mb -bin --mixed --analyze
echo ""

# 2. Reproducible with seed
echo "2. Reproducible random data (seed 42)..."
./entropy.py -1mb -txt --seed 42 --pattern gaussian
./entropy.py -1mb -txt --seed 42 --pattern gaussian
echo "Compare: The two files should be identical"
ls -lh entropy_*seed*.txt
echo ""

# 3. Lorem ipsum text
echo "3. Lorem ipsum style text..."
./entropy.py -500kb -txt --lorem --analyze
echo ""

# 4. Markov chain text
echo "4. Markov chain text (more realistic)..."
./entropy.py -500kb -txt --markov --analyze
echo ""

# 5. Benchmark mode
echo "5. Benchmark mode..."
./entropy.py -100mb -bin --benchmark
echo ""

# 6. Monitor entropy pool
echo "6. Monitor system entropy..."
./entropy.py -1mb -bin --monitor-entropy
echo ""

# 7. Split across directories (requires sudo for /tmp)
echo "7. Split across multiple directories..."
./entropy.py -10mb -bin -multi 3 --split-into /tmp,/var/tmp,.
echo ""

# 8. Stream to file (no timestamp)
echo "8. Streaming to custom file..."
./entropy.py -1mb -bin --stream > custom_output.bin
ls -lh custom_output.bin
rm custom_output.bin
echo ""

echo "=== Advanced examples completed ==="
