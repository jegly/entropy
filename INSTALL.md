# Installation Guide

## Quick Install

```bash
# Download
wget https://raw.githubusercontent.com/www.github.com/jegly/entropy/main/entropy.py

# Make executable
chmod +x entropy.py

# Optional: Install to PATH
sudo cp entropy.py /usr/local/bin/entropy

# Test
./entropy.py -1mb -bin


Complete Installation
1. System Requirements

    Debian/Ubuntu Linux (or derivative)

    Python 3.6 or higher

    50MB free disk space (for tool)

    Root access for optional dependencies

2. Core Installation

# Verify Python
python3 --version

# Download
curl -O https://raw.githubusercontent.com/jegly/entropy/main/entropy.py

# Make executable
chmod +x entropy.py

# Verify
./entropy.py --help

3. Optional Dependencies
Image Support

sudo apt install python3-pil

Audio Support

sudo apt install sox
# or
sudo apt install ffmpeg

Encryption Support

sudo apt install gnupg


Advanced Entropy Sources


# Mouse movement
sudo apt install python3-evdev

# Microphone
sudo apt install alsa-utils

# Camera
sudo apt install v4l-utils

# Hardware RNG
sudo apt install rng-tools


4. System-Wide Installation


# Copy to system path
sudo cp entropy.py /usr/local/bin/entropy

# Now run from anywhere
entropy -1gb -txt

5. Tab Completion (Optional)

Add to ~/.bashrc:

_entropy_completion() {
    local cur=${COMP_WORDS[COMP_CWORD]}
    COMPREPLY=($(compgen -W "-txt -bin -img -audio --help --man -force -multi --analyze --visualize --mixed --fast" -- $cur))
}
complete -F _entropy_completion entropy

6. Verification

# Test all features
entropy -1mb -txt
entropy -1mb -bin
entropy -1mb -img
entropy -1mb -audio

# Test analysis
entropy -1mb -bin --analyze

# Test entropy sources
entropy -1mb -bin --mixed
entropy -1mb -bin --use-env


Troubleshooting
"Command not found"

    Ensure Python is installed: python3 --version

    Make script executable: chmod +x entropy.py

    Add to PATH or use ./entropy.py

"Permission denied"

chmod +x entropy.py

"No module named PIL"

sudo apt install python3-pil


"Low entropy warning"

sudo apt install haveged
sudo systemctl enable haveged
sudo systemctl start haveged


"Disk full"

    Check free space: df -h

    Delete old files: rm entropy_*.bin


# Remove system install
sudo rm /usr/local/bin/entropy

# Remove local file
rm entropy.py

# Remove optional dependencies (if desired)
sudo apt remove python3-pil sox ffmpeg gnupg


Docker Installation (Alternative)
FROM ubuntu:22.04
RUN apt update && apt install -y python3 python3-pil
COPY entropy.py /usr/local/bin/entropy
RUN chmod +x /usr/local/bin/entropy
ENTRYPOINT ["entropy"]

Build and run:

docker build -t entropy .
docker run entropy -1mb -bin


---
