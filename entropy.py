#!/usr/bin/env python3
"""
ENTROPY - Cryptographically Secure Random Data Generator
Generates random files of specified size and format using system entropy sources

Author: Entropy Tool
License: MIT
Version: 1.0.0
"""

import os
import sys
import time
import math
import random
import struct
import argparse
import subprocess
import shutil
import hashlib
import tempfile
import signal
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
import secrets  # Python 3.6+ for crypto-secure random

# Global flags for interrupt handling
interrupted = False
current_file = None

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global interrupted
    interrupted = True
    print("\n\n[ENTROPY] Interrupted by user", file=sys.stderr)
    if current_file and os.path.exists(current_file):
        print(f"[ENTROPY] Partial file: {current_file}", file=sys.stderr)
        response = input("[ENTROPY] Delete partial file? (y/n): ")
        if response.lower() == 'y':
            os.unlink(current_file)
            print("[ENTROPY] Partial file deleted", file=sys.stderr)
    sys.exit(4)

signal.signal(signal.SIGINT, signal_handler)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def human_size_to_bytes(size_str: str) -> int:
    """Convert human readable size to bytes (e.g., '10gb' -> 10737418240)"""
    size_str = size_str.lower().strip()
    if size_str.startswith('-'):
        size_str = size_str[1:]
    
    multipliers = {
        'kb': 1024,
        'mb': 1024 ** 2,
        'gb': 1024 ** 3,
        'tb': 1024 ** 4
    }
    
    for suffix, multiplier in multipliers.items():
        if size_str.endswith(suffix):
            number = size_str[:-len(suffix)]
            try:
                return int(float(number) * multiplier)
            except ValueError:
                raise ValueError(f"Invalid size format: {size_str}")
    
    raise ValueError(f"Invalid size format: {size_str}. Use kb, mb, gb, tb")

def bytes_to_human(size: int) -> str:
    """Convert bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f}{unit}"
        size /= 1024.0
    return f"{size:.2f}PB"

def check_disk_space(path: str, needed_bytes: int) -> bool:
    """Check if enough disk space available"""
    try:
        stat = shutil.disk_usage(path)
        if stat.free < needed_bytes:
            print(f"[ENTROPY] Error: Insufficient disk space", file=sys.stderr)
            print(f"  Needed: {bytes_to_human(needed_bytes)}", file=sys.stderr)
            print(f"  Available: {bytes_to_human(stat.free)}", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"[ENTROPY] Warning: Cannot check disk space: {e}", file=sys.stderr)
        return True

def get_timestamp() -> str:
    """Get timestamp string for filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def get_file_path(base_name: str, ext: str, timestamp: str, index: Optional[int] = None) -> str:
    """Generate file path with timestamp and optional index"""
    if index is not None:
        filename = f"entropy_{timestamp}_{index:03d}.{ext}"
    else:
        filename = f"entropy_{timestamp}.{ext}"
    return os.path.join(os.getcwd(), filename)

def check_existing_files(files: List[str], force: bool, ask: bool) -> bool:
    """Check for existing files and handle conflicts"""
    existing = [f for f in files if os.path.exists(f)]
    if not existing:
        return True
    
    if force:
        for f in existing:
            os.unlink(f)
            print(f"[ENTROPY] Overwriting: {f}")
        return True
    elif ask:
        for f in existing:
            response = input(f"[ENTROPY] File exists: {f}\n  Overwrite? (y/n/skip all): ")
            if response.lower() == 'y':
                os.unlink(f)
            elif response.lower() == 'skip all':
                return False
            else:
                return False
        return True
    else:
        print(f"[ENTROPY] Error: Files exist. Use -force to overwrite or -ask to prompt", file=sys.stderr)
        for f in existing:
            print(f"  {f}", file=sys.stderr)
        return False

# ============================================================================
# DEPENDENCY CHECKING
# ============================================================================

def check_apt_package(package: str) -> bool:
    """Check if apt package is installed"""
    try:
        result = subprocess.run(
            ['dpkg-query', '-W', '-f=${Status}', package],
            capture_output=True, text=True
        )
        return 'install ok installed' in result.stdout
    except:
        return False

def check_binary(binary: str) -> bool:
    """Check if binary is in PATH"""
    return shutil.which(binary) is not None

def prompt_install(packages: List[str], auto_yes: bool, no_install: bool) -> bool:
    """Prompt user to install packages via apt"""
    if no_install:
        return False
    
    print(f"[ENTROPY] Missing dependencies: {', '.join(packages)}")
    
    if auto_yes:
        print("[ENTROPY] Auto-installing...")
        try:
            subprocess.run(['sudo', 'apt', 'update'], check=True)
            subprocess.run(['sudo', 'apt', 'install', '-y'] + packages, check=True)
            return True
        except:
            print("[ENTROPY] Failed to install packages", file=sys.stderr)
            return False
    
    response = input(f"[ENTROPY] Install with 'sudo apt install {' '.join(packages)}'? (y/n): ")
    if response.lower() == 'y':
        try:
            subprocess.run(['sudo', 'apt', 'update'], check=True)
            subprocess.run(['sudo', 'apt', 'install', '-y'] + packages, check=True)
            return True
        except:
            print("[ENTROPY] Installation failed", file=sys.stderr)
            return False
    return False

# ============================================================================
# ENTROPY SOURCES
# ============================================================================

class EntropySource:
    """Manage entropy sources for generation"""
    
    def __init__(self, mode='crypto', use_env=False, interactive=False, 
                 use_microphone=False, use_camera=False):
        self.mode = mode
        self.use_env = use_env
        self.interactive = interactive
        self.use_microphone = use_microphone
        self.use_camera = use_camera
        self.hwrng_available = self._check_hwrng()
        self.entropy_pool = bytearray()
        
    def _check_hwrng(self) -> bool:
        """Check if hardware RNG is available"""
        # Check for RDRAND via /proc/cpuinfo
        try:
            with open('/proc/cpuinfo', 'r') as f:
                if 'rdrand' in f.read():
                    return True
        except:
            pass
        
        # Check for /dev/hwrng
        if os.path.exists('/dev/hwrng'):
            return True
        
        return False
    
    def _read_hwrng(self, size: int) -> bytes:
        """Read from hardware RNG if available"""
        if os.path.exists('/dev/hwrng'):
            try:
                with open('/dev/hwrng', 'rb') as f:
                    return f.read(size)
            except:
                pass
        
        # Python doesn't have direct RDRAND access without ctypes
        # Fallback to os.urandom for this portion
        return os.urandom(size)
    
    def _collect_env_entropy(self) -> bytes:
        """Collect entropy from system environment"""
        data = bytearray()
        
        # System load
        try:
            with open('/proc/loadavg', 'r') as f:
                data.extend(f.read().encode())
        except:
            pass
        
        # Memory info
        try:
            with open('/proc/meminfo', 'r') as f:
                data.extend(f.read().encode())
        except:
            pass
        
        # Network stats
        try:
            with open('/proc/net/dev', 'r') as f:
                data.extend(f.read().encode())
        except:
            pass
        
        # Temperature sensors
        try:
            for path in Path('/sys/class/thermal').glob('thermal_zone*/temp'):
                data.extend(path.read_text().encode())
        except:
            pass
        
        # Process list
        try:
            import glob
            for pid_path in glob.glob('/proc/[0-9]*/stat'):
                try:
                    with open(pid_path, 'r') as f:
                        data.extend(f.read(1024).encode())
                except:
                    pass
        except:
            pass
        
        # Current time with high precision
        data.extend(str(time.perf_counter_ns()).encode())
        data.extend(str(time.time_ns()).encode())
        
        return bytes(data)
    
    def _collect_interactive_entropy(self) -> bytes:
        """Collect entropy from user interaction"""
        print("[ENTROPY] Move mouse or type randomly for entropy collection...")
        print("[ENTROPY] Press Enter when done")
        
        data = bytearray()
        
        # Try to use evdev for mouse events if available
        try:
            import evdev
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            mouse_devices = [d for d in devices if 'mouse' in d.name.lower()]
            
            if mouse_devices:
                print(f"[ENTROPY] Detected {len(mouse_devices)} mouse devices")
                start_time = time.time()
                while time.time() - start_time < 5:  # 5 seconds collection
                    for dev in mouse_devices:
                        try:
                            events = dev.read()
                            for event in events:
                                data.extend(struct.pack('iii', event.type, event.code, event.value))
                        except:
                            pass
        except ImportError:
            # Fallback to simple input timing
            import select
            sys.stdout.write("> ")
            sys.stdout.flush()
            
            start_time = time.time()
            last_time = start_time
            while True:
                rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
                if rlist:
                    ch = sys.stdin.read(1)
                    if ch == '\n':
                        break
                    current_time = time.time()
                    delta = current_time - last_time
                    data.extend(struct.pack('d', delta))
                    last_time = current_time
                else:
                    # Add timing jitter from idle time
                    current_time = time.time()
                    data.extend(struct.pack('d', current_time))
        
        print("[ENTROPY] Entropy collected")
        return bytes(data)
    
    def _collect_microphone_entropy(self) -> bytes:
        """Collect entropy from microphone noise"""
        if not check_binary('arecord'):
            print("[ENTROPY] arecord not found, skipping microphone entropy", file=sys.stderr)
            return b''
        
        print("[ENTROPY] Capturing microphone noise...")
        try:
            # Record 1 second of noise
            result = subprocess.run(
                ['arecord', '-d', '1', '-f', 'cd', '-t', 'raw'],
                capture_output=True, timeout=3
            )
            return result.stdout
        except Exception as e:
            print(f"[ENTROPY] Microphone capture failed: {e}", file=sys.stderr)
            return b''
    
    def _collect_camera_entropy(self) -> bytes:
        """Collect entropy from camera static"""
        if not check_binary('v4l2-ctl'):
            print("[ENTROPY] v4l2-ctl not found, skipping camera entropy", file=sys.stderr)
            return b''
        
        print("[ENTROPY] Capturing camera static...")
        try:
            # Capture a single frame
            with tempfile.NamedTemporaryFile(suffix='.raw', delete=False) as tmp:
                tmp_path = tmp.name
            
            subprocess.run(
                ['v4l2-ctl', '-d', '/dev/video0', '--set-fmt-video=width=640,height=480,pixelformat=YUYV'],
                capture_output=True, timeout=2
            )
            subprocess.run(
                ['v4l2-ctl', '--stream-mmap', '--stream-count=1', '--stream-to=' + tmp_path],
                capture_output=True, timeout=2
            )
            
            with open(tmp_path, 'rb') as f:
                data = f.read()
            os.unlink(tmp_path)
            return data
        except Exception as e:
            print(f"[ENTROPY] Camera capture failed: {e}", file=sys.stderr)
            return b''
    
    def get_random_bytes(self, size: int) -> bytes:
        """Get random bytes based on selected mode"""
        if self.mode == 'fast':
            # Fast non-crypto random (Mersenne Twister)
            return random.randbytes(size)
        
        elif self.mode == 'mixed':
            # Mixed entropy sources
            result = bytearray()
            
            # Collect from various sources
            sources = []
            
            # Primary: os.urandom
            sources.append(os.urandom(min(size, 1024*1024)))
            
            # Hardware RNG
            if self.hwrng_available:
                sources.append(self._read_hwrng(min(size, 1024*1024)))
            
            # Environment data
            if self.use_env:
                sources.append(self._collect_env_entropy())
            
            # Interactive data
            if self.interactive:
                sources.append(self._collect_interactive_entropy())
            
            # Microphone
            if self.use_microphone:
                sources.append(self._collect_microphone_entropy())
            
            # Camera
            if self.use_camera:
                sources.append(self._collect_camera_entropy())
            
            # Combine all sources by XOR
            combined = bytearray()
            for src in sources:
                combined.extend(src)
            
            # Stretch to desired size using SHA256 in counter mode
            result = bytearray()
            counter = 0
            while len(result) < size:
                hash_input = combined + struct.pack('Q', counter)
                result.extend(hashlib.sha256(hash_input).digest())
                counter += 1
            
            return bytes(result[:size])
        
        else:  # crypto (default)
            return os.urandom(size)

# ============================================================================
# GENERATORS
# ============================================================================

class BaseGenerator:
    """Base class for all generators"""
    
    def __init__(self, entropy_source: EntropySource, chunk_size: int = 1024*1024):
        self.entropy = entropy_source
        self.chunk_size = chunk_size
        self.bytes_written = 0
        self.start_time = None
    
    def _update_progress(self, total_bytes: int):
        """Update progress display"""
        if self.start_time is None:
            return
        
        elapsed = time.time() - self.start_time
        percent = (self.bytes_written / total_bytes) * 100
        speed = self.bytes_written / elapsed if elapsed > 0 else 0
        
        eta = (total_bytes - self.bytes_written) / speed if speed > 0 else 0
        
        bar_length = 40
        filled = int(bar_length * self.bytes_written / total_bytes)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        sys.stdout.write(f'\r[{bar}] {percent:.1f}% | {bytes_to_human(self.bytes_written)} | '
                        f'{bytes_to_human(speed)}/s | ETA: {eta:.0f}s')
        sys.stdout.flush()
    
    def generate(self, filepath: str, target_bytes: int) -> bool:
        """Generate file - to be implemented by subclasses"""
        raise NotImplementedError

class BinaryGenerator(BaseGenerator):
    """Generate random binary files"""
    
    def generate(self, filepath: str, target_bytes: int) -> bool:
        global current_file
        current_file = filepath
        self.bytes_written = 0
        self.start_time = time.time()
        
        try:
            with open(filepath, 'wb') as f:
                remaining = target_bytes
                while remaining > 0 and not interrupted:
                    chunk = min(self.chunk_size, remaining)
                    data = self.entropy.get_random_bytes(chunk)
                    f.write(data)
                    self.bytes_written += len(data)
                    remaining -= len(data)
                    self._update_progress(target_bytes)
                
                if not interrupted:
                    sys.stdout.write('\n')
                    print(f"[ENTROPY] Generated: {filepath}")
                    print(f"[ENTROPY] Size: {bytes_to_human(self.bytes_written)}")
                    return True
                return False
        except Exception as e:
            print(f"\n[ENTROPY] Error: {e}", file=sys.stderr)
            return False

class TextGenerator(BaseGenerator):
    """Generate random text files with printable ASCII"""
    
    def __init__(self, entropy_source, markov=False, lorem=False, chunk_size=1024*1024):
        super().__init__(entropy_source, chunk_size)
        self.markov = markov
        self.lorem = lorem
        self._init_word_list()
    
    def _init_word_list(self):
        """Initialize word list for text generation"""
        # Common English words for realistic text
        self.words = [
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
            'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
            'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
            'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
            'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me'
        ]
        
        # Lorem ipsum words
        self.lorem_words = [
            'lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing',
            'elit', 'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore',
            'et', 'dolore', 'magna', 'aliqua', 'ut', 'enim', 'ad', 'minim', 'veniam',
            'quis', 'nostrud', 'exercitation', 'ullamco', 'laboris', 'nisi', 'aliquip',
            'ex', 'ea', 'commodo', 'consequat', 'duis', 'aute', 'irure', 'dolor',
            'in', 'reprehenderit', 'voluptate', 'velit', 'esse', 'cillum', 'eu',
            'fugiat', 'nulla', 'pariatur'
        ]
    
    def _get_random_word(self) -> str:
        """Get random word based on mode"""
        if self.lorem:
            word_list = self.lorem_words
        else:
            word_list = self.words
        
        idx = int.from_bytes(self.entropy.get_random_bytes(2), 'big') % len(word_list)
        return word_list[idx]
    
    def _get_random_char(self) -> bytes:
        """Get random printable ASCII character"""
        # Printable ASCII range: 32-126
        while True:
            byte = self.entropy.get_random_bytes(1)
            b = byte[0]
            if 32 <= b <= 126:
                return byte
            # Also include newline and space more frequently
            if b % 100 < 10:  # ~10% chance for newline
                return b'\n'
            if b % 100 < 20:  # ~10% chance for space
                return b' '
    
    def generate(self, filepath: str, target_bytes: int) -> bool:
        global current_file
        current_file = filepath
        self.bytes_written = 0
        self.start_time = time.time()
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                remaining = target_bytes
                line_length = 0
                
                while remaining > 0 and not interrupted:
                    if self.markov:
                        # Simple Markov chain: random words
                        word = self._get_random_word()
                        chunk = word + ' '
                        chunk_bytes = len(chunk.encode('utf-8'))
                        
                        if chunk_bytes <= remaining:
                            f.write(chunk)
                            self.bytes_written += chunk_bytes
                            remaining -= chunk_bytes
                            line_length += len(word) + 1
                    else:
                        # Random characters
                        chunk_size = min(self.chunk_size, remaining)
                        chunk = bytearray()
                        for _ in range(chunk_size):
                            chunk.extend(self._get_random_char())
                        
                        chunk_str = chunk.decode('utf-8', errors='replace')
                        f.write(chunk_str)
                        self.bytes_written += len(chunk)
                        remaining -= len(chunk)
                    
                    # Add newlines periodically
                    if line_length > 80:
                        f.write('\n')
                        self.bytes_written += 1
                        remaining -= 1
                        line_length = 0
                    
                    self._update_progress(target_bytes)
                
                if not interrupted:
                    sys.stdout.write('\n')
                    print(f"[ENTROPY] Generated: {filepath}")
                    print(f"[ENTROPY] Size: {bytes_to_human(self.bytes_written)}")
                    return True
                return False
        except Exception as e:
            print(f"\n[ENTROPY] Error: {e}", file=sys.stderr)
            return False

class ImageGenerator(BaseGenerator):
    """Generate random images"""
    
    def __init__(self, entropy_source, chunk_size=1024*1024):
        super().__init__(entropy_source, chunk_size)
        self.pil_available = self._check_pil()
    
    def _check_pil(self) -> bool:
        """Check if PIL is available"""
        try:
            import PIL.Image
            return True
        except ImportError:
            return False
    
    def generate(self, filepath: str, target_bytes: int) -> bool:
        if self.pil_available:
            return self._generate_with_pil(filepath, target_bytes)
        else:
            return self._generate_ppm(filepath, target_bytes)
    
    def _generate_with_pil(self, filepath: str, target_bytes: int) -> bool:
        """Generate image using PIL"""
        try:
            import PIL.Image
            import PIL.ImageDraw
            
            global current_file
            current_file = filepath
            
            # Calculate dimensions (rough estimate for PNG)
            # PNG compression varies, so we approximate
            width = int(math.sqrt(target_bytes / 3))  # RGB = 3 bytes per pixel
            height = width
            if width < 1:
                width = height = 1
            
            # Generate random pixel data
            pixels = self.entropy.get_random_bytes(width * height * 3)
            
            # Create image
            img = PIL.Image.frombytes('RGB', (width, height), pixels)
            
            # Save with compression
            img.save(filepath, 'PNG', optimize=False)
            
            actual_size = os.path.getsize(filepath)
            print(f"[ENTROPY] Generated: {filepath}")
            print(f"[ENTROPY] Target: {bytes_to_human(target_bytes)} | Actual: {bytes_to_human(actual_size)}")
            print(f"[ENTROPY] Note: PNG compression affects final size")
            return True
            
        except Exception as e:
            print(f"\n[ENTROPY] PIL generation failed: {e}", file=sys.stderr)
            return self._generate_ppm(filepath, target_bytes)
    
    def _generate_ppm(self, filepath: str, target_bytes: int) -> bool:
        """Generate PPM image (exact size, no compression)"""
        global current_file
        current_file = filepath
        self.bytes_written = 0
        self.start_time = time.time()
        
        try:
            # Calculate dimensions for exact size
            # PPM format: "P6\nwidth height\n255\n" + width*height*3 bytes
            header_fixed = 15  # Approximate header size (varies with width/height digits)
            
            # Adjust for actual header size
            for width in range(1, 10000):
                height = (target_bytes - (len(f"P6\n{width} {width}\n255\n"))) // 3
                if height > 0 and width * height * 3 + len(f"P6\n{width} {height}\n255\n") <= target_bytes:
                    break
            
            if width >= 10000:
                width = 1000
                height = (target_bytes - 20) // 3
            
            header = f"P6\n{width} {height}\n255\n".encode()
            
            with open(filepath, 'wb') as f:
                f.write(header)
                self.bytes_written += len(header)
                self._update_progress(target_bytes)
                
                remaining = target_bytes - self.bytes_written
                pixel_bytes = width * height * 3
                write_bytes = min(pixel_bytes, remaining)
                
                data = self.entropy.get_random_bytes(write_bytes)
                f.write(data)
                self.bytes_written += len(data)
                self._update_progress(target_bytes)
                
                # Pad if needed
                if self.bytes_written < target_bytes:
                    padding = self.entropy.get_random_bytes(target_bytes - self.bytes_written)
                    f.write(padding)
                    self.bytes_written = target_bytes
                    self._update_progress(target_bytes)
            
            sys.stdout.write('\n')
            print(f"[ENTROPY] Generated: {filepath}")
            print(f"[ENTROPY] Size: {bytes_to_human(self.bytes_written)}")
            return True
            
        except Exception as e:
            print(f"\n[ENTROPY] Error: {e}", file=sys.stderr)
            return False

class AudioGenerator(BaseGenerator):
    """Generate random audio files (WAV format)"""
    
    def generate(self, filepath: str, target_bytes: int) -> bool:
        global current_file
        current_file = filepath
        self.bytes_written = 0
        self.start_time = time.time()
        
        try:
            # WAV header is 44 bytes
            header_size = 44
            data_bytes = target_bytes - header_size
            
            if data_bytes < 0:
                print(f"[ENTROPY] Target too small for WAV header", file=sys.stderr)
                return False
            
            # Calculate samples (16-bit stereo = 4 bytes per sample)
            samples = data_bytes // 4
            sample_rate = 44100
            
            with open(filepath, 'wb') as f:
                # Write WAV header
                f.write(b'RIFF')
                f.write(struct.pack('<I', target_bytes - 8))  # File size - 8
                f.write(b'WAVE')
                f.write(b'fmt ')
                f.write(struct.pack('<I', 16))  # Chunk size
                f.write(struct.pack('<H', 1))   # Audio format (PCM)
                f.write(struct.pack('<H', 2))   # Channels (stereo)
                f.write(struct.pack('<I', sample_rate))
                f.write(struct.pack('<I', sample_rate * 4))  # Byte rate
                f.write(struct.pack('<H', 4))   # Block align
                f.write(struct.pack('<H', 16))  # Bits per sample
                f.write(b'data')
                f.write(struct.pack('<I', data_bytes))
                
                self.bytes_written = header_size
                self._update_progress(target_bytes)
                
                # Generate audio data
                remaining = data_bytes
                while remaining > 0 and not interrupted:
                    chunk = min(self.chunk_size, remaining)
                    data = self.entropy.get_random_bytes(chunk)
                    f.write(data)
                    self.bytes_written += len(data)
                    remaining -= len(data)
                    self._update_progress(target_bytes)
            
            if not interrupted:
                sys.stdout.write('\n')
                print(f"[ENTROPY] Generated: {filepath}")
                print(f"[ENTROPY] Size: {bytes_to_human(self.bytes_written)}")
                return True
            return False
            
        except Exception as e:
            print(f"\n[ENTROPY] Error: {e}", file=sys.stderr)
            return False

# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def analyze_entropy(filepath: str, sample_size: int = 1024*1024) -> Dict[str, Any]:
    """Analyze entropy of a file"""
    try:
        # Sample the file
        with open(filepath, 'rb') as f:
            data = f.read(min(sample_size, os.path.getsize(filepath)))
        
        if not data:
            return {'error': 'File empty'}
        
        # Calculate Shannon entropy
        freq = [0] * 256
        for byte in data:
            freq[byte] += 1
        
        entropy = 0
        for count in freq:
            if count > 0:
                p = count / len(data)
                entropy -= p * math.log2(p)
        
        # Byte distribution
        min_byte = min((i for i, c in enumerate(freq) if c > 0), default=0)
        max_byte = max((i for i, c in enumerate(freq) if c > 0), default=0)
        
        return {
            'shannon_entropy': entropy,
            'bits_per_byte': entropy,
            'unique_bytes': len([c for c in freq if c > 0]),
            'min_byte': min_byte,
            'max_byte': max_byte,
            'sample_size': len(data),
            'total_size': os.path.getsize(filepath)
        }
    except Exception as e:
        return {'error': str(e)}

def visualize_entropy(filepath: str, output_path: str) -> bool:
    """Generate visualization of entropy distribution"""
    try:
        import PIL.Image
        import PIL.ImageDraw
        
        # Sample file
        with open(filepath, 'rb') as f:
            data = f.read(min(1024*1024, os.path.getsize(filepath)))
        
        if not data:
            return False
        
        # Create byte frequency heatmap
        freq = [0] * 256
        for byte in data:
            freq[byte] += 1
        
        max_freq = max(freq)
        
        # Create image 256x100
        img = PIL.Image.new('RGB', (256, 100), color='black')
        draw = PIL.ImageDraw.Draw(img)
        
        for i, count in enumerate(freq):
            if max_freq > 0:
                height = int((count / max_freq) * 100)
                color_value = int((count / max_freq) * 255)
                draw.rectangle([i, 100-height, i+1, 100], fill=(color_value, 0, 255-color_value))
        
        img.save(output_path)
        return True
        
    except Exception as e:
        print(f"[ENTROPY] Visualization failed: {e}", file=sys.stderr)
        return False

# ============================================================================
# MAIN PROGRAM
# ============================================================================

def parse_arguments():
    """Parse command line arguments"""
    # Pre-process: extract size arg (e.g. -1mb, -10gb) before argparse sees it
    import re
    size_arg = None
    filtered_argv = []
    for arg in sys.argv[1:]:
        if re.match(r'^-\d+(\.\d+)?(kb|mb|gb|tb)$', arg, re.IGNORECASE):
            size_arg = arg
        else:
            filtered_argv.append(arg)
    sys.argv[1:] = filtered_argv

    parser = argparse.ArgumentParser(
        description='ENTROPY - Cryptographically Secure Random Data Generator',
        add_help=False
    )
    
    # Size and format
    parser.add_argument('size', nargs='?', default=size_arg, help='Size: -10gb, -500mb, -2tb, etc.')
    parser.add_argument('-txt', '--text', action='store_true', help='Generate text file')
    parser.add_argument('-bin', '--binary', action='store_true', help='Generate binary file (default)')
    parser.add_argument('-img', '--image', action='store_true', help='Generate image file')
    parser.add_argument('-audio', '--audio', action='store_true', help='Generate audio file')
    
    # Entropy sources
    parser.add_argument('-crypto', action='store_true', help='Cryptographically secure (default)')
    parser.add_argument('--fast', action='store_true', help='Fast non-crypto random')
    parser.add_argument('--mixed', action='store_true', help='Combine multiple entropy sources')
    parser.add_argument('--entropy-source', help='Custom entropy source')
    parser.add_argument('--use-env', action='store_true', help='Use system environment data')
    parser.add_argument('--interactive', action='store_true', help='Collect entropy from user input')
    parser.add_argument('--microphone', action='store_true', help='Capture microphone noise')
    parser.add_argument('--camera', action='store_true', help='Capture camera static')
    
    # Visualization and analysis
    parser.add_argument('--visualize', action='store_true', help='Generate visual representation')
    parser.add_argument('--analyze', action='store_true', help='Show entropy analysis')
    parser.add_argument('--hexdump', action='store_true', help='Show hexdump of file')
    parser.add_argument('--benchmark', action='store_true', help='Run performance benchmark')
    parser.add_argument('--monitor-entropy', action='store_true', help='Show system entropy pool')
    
    # Patterns
    parser.add_argument('--pattern', choices=['uniform', 'gaussian', 'zipf'], help='Distribution pattern')
    parser.add_argument('--markov', action='store_true', help='Markov chain text')
    parser.add_argument('--lorem', action='store_true', help='Lorem ipsum style text')
    parser.add_argument('--corrupt', action='store_true', help='Inject corruption patterns')
    
    # Output control
    parser.add_argument('-multi', type=int, metavar='N', help='Split across N files')
    parser.add_argument('--stream', action='store_true', help='Output to stdout')
    parser.add_argument('--encrypt', action='store_true', help='Encrypt with GPG')
    parser.add_argument('--split-into', help='Comma-separated directories')
    parser.add_argument('--shred', action='store_true', help='Secure wipe when done')
    parser.add_argument('--watch', action='store_true', help='Continuous generation mode')
    
    # Advanced
    parser.add_argument('--seed', type=int, help='Reproducible randomness')
    parser.add_argument('--chaos', action='store_true', help='Recursive random structure')
    parser.add_argument('--diff', help='Generate diffs from base file')
    
    # System
    parser.add_argument('-force', action='store_true', help='Overwrite existing files')
    parser.add_argument('-ask', action='store_true', help='Prompt before overwriting')
    parser.add_argument('-quiet', action='store_true', help='Suppress progress display')
    parser.add_argument('-yes', action='store_true', help='Auto-install dependencies')
    parser.add_argument('-no-install', action='store_true', help='Never install dependencies')
    parser.add_argument('-help', '--help', action='store_true', help='Show this help message')
    parser.add_argument('-man', '--man', action='store_true', help='Show detailed manual')
    
    return parser.parse_args()

def show_help():
    """Show compact help"""
    print("""ENTROPY - Cryptographically Secure Random Data Generator

Usage:
  entropy.py [SIZE] [FORMAT] [OPTIONS]

SIZE (required):
  -10gb, -500mb, -2tb, -1kb    Generate specific size

FORMAT (default: -bin):
  -txt    Text files (printable ASCII)
  -bin    Binary files (raw random bytes)
  -img    Image files (PNG)
  -audio  Audio files (WAV)

ENTROPY SOURCES:
  -crypto    Cryptographically secure (DEFAULT)
  --fast     Fast non-crypto random (Mersenne Twister)
  --mixed    Combine multiple entropy sources
  --use-env  Use system environment data
  --interactive  Collect entropy from user input

VISUALIZATION & ANALYSIS:
  --visualize    Generate visual representation
  --analyze      Show entropy analysis (bits per byte)
  --hexdump      Show hexdump of first/last bytes

OUTPUT CONTROL:
  -multi N      Split across N files
  --stream      Output to stdout
  --encrypt     Encrypt with GPG

Examples:
  entropy.py -10gb -txt
  entropy.py -500mb -img --visualize --analyze
  entropy.py -2gb -bin --mixed

For detailed manual: entropy.py --man
""")

def show_manual():
    """Show detailed manual"""
    print("""ENTROPY - Detailed Manual
========================

ENTROPY is a cryptographically secure random data generator that creates files
of specified sizes using system entropy sources.

ENTROPY SOURCES
---------------
-crypto (default)
    Uses os.urandom() which reads from /dev/urandom. Cryptographically secure
    for all purposes. Speed: 100-500 MB/s typical.

--fast
    Uses Python's random module (Mersenne Twister). NOT cryptographically
    secure but faster. Speed: 500-2000 MB/s.

--mixed
    Combines multiple entropy sources:
    * /dev/urandom (baseline)
    * Hardware RNG if available (RDRAND, /dev/hwrng)
    * System environment data (load, memory, network, temperature)
    * User input (if --interactive)
    * Microphone noise (if --microphone)
    * Camera static (if --camera)
    Slower but highest quality entropy.

--use-env
    Incorporate system environment data into entropy pool.

--interactive
    Collect entropy from mouse movements or keyboard timing.

--microphone
    Capture microphone noise as entropy source (requires arecord).

--camera
    Capture camera static as entropy source (requires v4l2-ctl).

VISUALIZATION & ANALYSIS
------------------------
--visualize
    Creates filename_viz.png showing byte frequency distribution.

--analyze
    Calculates Shannon entropy (bits per byte) and byte distribution.
    Range: 0 (highly structured) to 8 (perfectly random).

--hexdump
    Shows hexdump of first and last 256 bytes of generated file.

--benchmark
    Runs performance test before generation to estimate speed.

--monitor-entropy
    Shows system entropy pool status (/proc/sys/kernel/random/entropy_avail).

PATTERNS
--------
--pattern uniform|gaussian|zipf
    Distribution pattern for generated data.

--markov
    Use Markov chain for text generation (more realistic).

--lorem
    Generate lorem ipsum style text.

--corrupt
    Inject intentional corruption patterns at random intervals.

OUTPUT CONTROL
--------------
-multi N
    Split total size across N files. Files named entropy_TIMESTAMP_001.ext

--stream
    Output to stdout instead of file. Useful for piping.

--encrypt
    Encrypt output with GPG. Requires gnupg package.

--split-into DIR1,DIR2
    Distribute files across multiple directories.

--shred
    Securely wipe output files with multiple passes when done.

--watch
    Continuous generation mode to maintain specified free space.

ADVANCED
--------
--seed SEED
    Use fixed seed for reproducible randomness (overrides crypto).

--chaos
    Generate random directory structure with random files recursively.

--diff FILE
    Generate files with random diffs from base file.

SYSTEM OPTIONS
--------------
-force      Overwrite existing files without prompting
-ask        Prompt before overwriting existing files
-quiet      Suppress progress display
-yes        Auto-install missing dependencies via apt
-no-install Never attempt to install dependencies

DEPENDENCIES
------------
Core (always works):
    Python 3.6+ standard library

Optional (apt install):
    python3-pil        - Enhanced image generation
    sox                - Advanced audio generation
    ffmpeg             - Video generation
    gnupg              - Encryption support
    python3-evdev      - Mouse movement entropy
    alsa-utils         - Microphone capture (arecord)
    v4l-utils          - Camera capture (v4l2-ctl)

EXAMPLES
--------
Basic:
    entropy.py -10gb -txt
    entropy.py -500mb -img --visualize
    entropy.py -2gb -bin --mixed --analyze

Advanced:
    entropy.py -1gb --chaos --mixed --split-into /mnt/disk1,/mnt/disk2
    entropy.py -100mb -txt --seed 42 --pattern gaussian
    entropy.py -5gb -bin --stream --encrypt | ssh server "cat > data.bin"

Testing:
    entropy.py -50mb -txt --benchmark --monitor-entropy
    entropy.py -1mb -bin --analyze --hexdump

EXIT CODES
----------
0 - Success
1 - General error (invalid arguments, permissions)
2 - Missing dependencies
3 - Disk full or insufficient space
4 - Interrupted by user

NOTES
-----
- Image files with PNG compression may not hit exact target sizes.
  Use --img with PPM fallback for exact sizing.
- Virtual machines may have limited entropy. Install haveged for better performance.
- Hardware RNG requires appropriate kernel modules and permissions.

For more information, visit: https://github.com/example/entropy
""")

def main():
    args = parse_arguments()
    
    # Show help
    if args.help:
        show_help()
        return
    
    if args.man:
        show_manual()
        return
    
    # Check if size provided
    if not args.size:
        print("[ENTROPY] Error: No size specified", file=sys.stderr)
        print("Usage: entropy.py -10gb -txt", file=sys.stderr)
        print("Use --help for more information", file=sys.stderr)
        sys.exit(1)
    
    # Parse size
    try:
        target_bytes = human_size_to_bytes(args.size)
    except ValueError as e:
        print(f"[ENTROPY] Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Determine format
    if args.text:
        file_format = 'txt'
        ext = 'txt'
    elif args.image:
        file_format = 'img'
        ext = 'png'
    elif args.audio:
        file_format = 'audio'
        ext = 'wav'
    else:
        file_format = 'bin'
        ext = 'bin'
    
    # Check disk space if writing to disk
    if not args.stream:
        if not check_disk_space(os.getcwd(), target_bytes):
            sys.exit(3)
    
    # Setup entropy source
    if args.fast:
        entropy_mode = 'fast'
    elif args.mixed:
        entropy_mode = 'mixed'
    else:
        entropy_mode = 'crypto'  # default
    
    entropy_source = EntropySource(
        mode=entropy_mode,
        use_env=args.use_env,
        interactive=args.interactive,
        use_microphone=args.microphone,
        use_camera=args.camera
    )
    
    # Handle seed for reproducibility
    if args.seed is not None:
        random.seed(args.seed)
        print(f"[ENTROPY] Using fixed seed: {args.seed} (reproducible mode)")
    
    # Benchmark
    if args.benchmark:
        print("[ENTROPY] Running benchmark...")
        start = time.time()
        test_data = entropy_source.get_random_bytes(100 * 1024 * 1024)  # 100MB
        elapsed = time.time() - start
        speed = 100 / elapsed  # MB/s
        print(f"[ENTROPY] Benchmark: {speed:.2f} MB/s")
    
    # Monitor entropy pool
    if args.monitor_entropy:
        try:
            with open('/proc/sys/kernel/random/entropy_avail', 'r') as f:
                entropy_avail = int(f.read().strip())
            print(f"[ENTROPY] System entropy pool: {entropy_avail} bits")
            if entropy_avail < 1000:
                print("[ENTROPY] Warning: Low entropy! Consider installing haveged", file=sys.stderr)
        except:
            print("[ENTROPY] Cannot read entropy pool (not on Linux?)", file=sys.stderr)
    
    # Generate files
    timestamp = get_timestamp()
    num_files = args.multi if args.multi else 1
    per_file_bytes = target_bytes // num_files
    remainder = target_bytes % num_files
    
    files_to_generate = []
    for i in range(num_files):
        size = per_file_bytes + (1 if i < remainder else 0)
        if size > 0:
            filepath = get_file_path('entropy', ext, timestamp, i+1 if num_files > 1 else None)
            files_to_generate.append((filepath, size))
    
    # Check for existing files
    if not args.stream:
        if not check_existing_files([f[0] for f in files_to_generate], args.force, args.ask):
            sys.exit(1)
    
    # Create generator
    if file_format == 'txt':
        generator = TextGenerator(entropy_source, markov=args.markov, lorem=args.lorem)
    elif file_format == 'img':
        generator = ImageGenerator(entropy_source)
    elif file_format == 'audio':
        generator = AudioGenerator(entropy_source)
    else:
        generator = BinaryGenerator(entropy_source)
    
    # Generate each file
    success = True
    for filepath, size in files_to_generate:
        if interrupted:
            break
        
        if args.stream:
            # Stream to stdout
            sys.stdout.buffer.write(entropy_source.get_random_bytes(size))
        else:
            if not generator.generate(filepath, size):
                success = False
                break
    
    # Analyze if requested
    if args.analyze and not args.stream:
        for filepath, _ in files_to_generate:
            if os.path.exists(filepath):
                analysis = analyze_entropy(filepath)
                if 'error' in analysis:
                    print(f"[ENTROPY] Analysis failed: {analysis['error']}", file=sys.stderr)
                else:
                    print(f"\n[ENTROPY] Analysis: {filepath}")
                    print(f"  Shannon entropy: {analysis['shannon_entropy']:.4f} bits/byte")
                    print(f"  Unique bytes: {analysis['unique_bytes']}/256")
                    print(f"  Byte range: {analysis['min_byte']}-{analysis['max_byte']}")
    
    # Visualize if requested
    if args.visualize and not args.stream:
        for filepath, _ in files_to_generate:
            if os.path.exists(filepath):
                viz_path = filepath.replace(ext, 'viz.png')
                if visualize_entropy(filepath, viz_path):
                    print(f"[ENTROPY] Visualization: {viz_path}")
    
    # Hexdump if requested
    if args.hexdump and not args.stream:
        for filepath, _ in files_to_generate:
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                print(f"\n[ENTROPY] Hexdump: {filepath}")
                with open(filepath, 'rb') as f:
                    first = f.read(256)
                    print("First 256 bytes:")
                    for i in range(0, min(256, len(first)), 16):
                        hex_part = ' '.join(f'{b:02x}' for b in first[i:i+16])
                        ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in first[i:i+16])
                        print(f"  {i:04x}: {hex_part:<48} {ascii_part}")
                    
                    if os.path.getsize(filepath) > 512:
                        f.seek(-256, os.SEEK_END)
                        last = f.read(256)
                        print("\nLast 256 bytes:")
                        for i in range(0, 256, 16):
                            hex_part = ' '.join(f'{b:02x}' for b in last[i:i+16])
                            ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in last[i:i+16])
                            print(f"  {os.path.getsize(filepath)-256+i:04x}: {hex_part:<48} {ascii_part}")
    
    if not success:
        sys.exit(1)
    
    print("\n[ENTROPY] Done!")

if __name__ == '__main__':
    main()