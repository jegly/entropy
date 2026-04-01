# ENTROPY - Cryptographically Secure Random Data Generator

A powerful command-line tool for generating random data files using system entropy sources. Perfect for testing, benchmarking, and entropy analysis.

## Features

- **Multiple formats**: Text, binary, images, audio
- **Entropy sources**: Crypto-secure, fast, mixed, hardware RNG
- **Analysis**: Shannon entropy calculation, visualization, hexdump
- **Flexible output**: Single files, multi-file splits, streaming
- **Smart dependencies**: Auto-detects and prompts for apt packages
- **Debian/Ubuntu native**: No pip, no PyPI - only apt packages

## Quick Start

```bash
# Make executable
chmod +x entropy.py

# Generate 10GB of random text
./entropy.py -10gb -txt

# Generate 500MB random image with analysis
./entropy.py -500mb -img --visualize --analyze

# Generate 2GB binary with mixed entropy sources
./entropy.py -2gb -bin --mixed --benchmark

Installation

# Core (always works)
chmod +x entropy.py
sudo cp entropy.py /usr/local/bin/entropy

# Optional enhancements
sudo apt install python3-pil      # Better images
sudo apt install sox              # Advanced audio
sudo apt install gnupg            # Encryption support

Usage Examples
Basic Generation

./entropy.py -10gb -txt          # 10GB text file
./entropy.py -500mb -bin         # 500MB binary
./entropy.py -2gb -img           # 2GB image (approx)
./entropy.py -100mb -audio       # 100MB WAV file

Advanced Features

# Mixed entropy with visualization
./entropy.py -500mb -img --mixed --visualize

# Split across multiple files
./entropy.py -10gb -bin -multi 10

# Reproducible test data
./entropy.py -50mb -txt --seed 42 --pattern gaussian

# Stream and encrypt
./entropy.py -1gb -bin --stream --encrypt | ssh server "cat > data.bin"

# Analysis only
./entropy.py -1mb -bin --analyze --hexdump

Entropy Sources

./entropy.py -10gb -bin                    # Default: crypto-secure
./entropy.py -10gb -bin --fast             # Fast non-crypto
./entropy.py -10gb -bin --mixed            # Highest quality
./entropy.py -10gb -bin --use-env          # Add system environment
./entropy.py -10gb -bin --interactive      # Collect user input

Command Reference
Required Arguments

    SIZE: -10gb, -500mb, -2tb, -1kb

Format (default: -bin)

    -txt - Text files (printable ASCII)

    -bin - Binary files (raw random bytes)

    -img - Image files (PNG format)

    -audio - Audio files (WAV format)

Entropy Sources

    -crypto - Cryptographically secure (default)

    --fast - Fast non-crypto (Mersenne Twister)

    --mixed - Combine multiple sources

    --use-env - System environment data

    --interactive - User input entropy

    --microphone - Microphone noise

    --camera - Camera static

Analysis & Visualization

    --visualize - Generate byte frequency heatmap

    --analyze - Calculate Shannon entropy

    --hexdump - Show first/last 256 bytes

    --benchmark - Performance test

    --monitor-entropy - System entropy pool status

Output Control

    -multi N - Split across N files

    --stream - Output to stdout

    --encrypt - GPG encryption

    --split-into DIR1,DIR2 - Multiple directories

Advanced

    --seed N - Reproducible randomness

    --pattern TYPE - uniform|gaussian|zipf

    --markov - Markov chain text

    --lorem - Lorem ipsum style

    --chaos - Random directory structure

System

    -force - Overwrite without asking

    -ask - Prompt before overwrite

    -quiet - Suppress progress

    -yes - Auto-install dependencies

    -no-install - Never install

Help

./entropy.py --help    # Compact help
./entropy.py --man     # Detailed manual

Dependencies
Core (always works)

    Python 3.6+

Optional (apt install)

sudo apt install python3-pil      # Enhanced images
sudo apt install sox              # Advanced audio
sudo apt install ffmpeg           # Video support
sudo apt install gnupg            # Encryption
sudo apt install python3-evdev    # Mouse entropy
sudo apt install alsa-utils       # Microphone (arecord)
sudo apt install v4l-utils        # Camera (v4l2-ctl)

Exit Codes

    0 - Success

    1 - General error

    2 - Missing dependencies

    3 - Disk full

    4 - Interrupted by user

License

MIT License

Author - JEGLY www.github.com/jegly/entropy



---