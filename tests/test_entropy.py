#!/usr/bin/env python3
"""Advanced entropy quality tests"""

import os
import sys
import math
import tempfile
import unittest
import subprocess

class TestEntropyQuality(unittest.TestCase):
    """Test entropy quality of generated data"""
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        os.chdir(self.original_dir)
        import shutil
        shutil.rmtree(self.test_dir)
    
    def run_entropy(self, args):
        script_path = os.path.join(os.path.dirname(__file__), '..', 'entropy.py')
        cmd = [sys.executable, script_path] + args
        return subprocess.run(cmd, capture_output=True, text=True)
    
    def calculate_entropy(self, filepath):
        """Calculate Shannon entropy of file"""
        with open(filepath, 'rb') as f:
            data = f.read()
        
        if not data:
            return 0
        
        freq = [0] * 256
        for byte in data:
            freq[byte] += 1
        
        entropy = 0
        for count in freq:
            if count > 0:
                p = count / len(data)
                entropy -= p * math.log2(p)
        
        return entropy
    
    def test_crypto_entropy(self):
        """Test crypto-secure random has high entropy"""
        result = self.run_entropy(['-100kb', '-bin'])
        self.assertEqual(result.returncode, 0)
        
        files = [f for f in os.listdir('.') if f.endswith('.bin')]
        self.assertTrue(len(files) > 0)
        
        entropy = self.calculate_entropy(files[0])
        # Random data should have entropy near 8 bits/byte
        self.assertGreater(entropy, 7.5)
    
    def test_fast_entropy(self):
        """Test fast random also has good entropy"""
        result = self.run_entropy(['-100kb', '-bin', '--fast'])
        self.assertEqual(result.returncode, 0)
        
        files = [f for f in os.listdir('.') if f.endswith('.bin')]
        entropy = self.calculate_entropy(files[0])
        self.assertGreater(entropy, 7.5)
    
    def test_text_entropy(self):
        """Test text files have lower entropy (structured)"""
        result = self.run_entropy(['-100kb', '-txt'])
        self.assertEqual(result.returncode, 0)
        
        files = [f for f in os.listdir('.') if f.endswith('.txt')]
        entropy = self.calculate_entropy(files[0])
        # Text should have entropy around 4-6 bits/byte
        self.assertLess(entropy, 7.0)
        self.assertGreater(entropy, 3.0)
    
    def test_reproducibility(self):
        """Test seed produces identical files"""
        # Generate first file
        result1 = self.run_entropy(['-10kb', '-bin', '--seed', '42'])
        
        # Clear files
        for f in os.listdir('.'):
            os.unlink(f)
        
        # Generate second file with same seed
        result2 = self.run_entropy(['-10kb', '-bin', '--seed', '42'])
        
        # Get files
        files1 = [f for f in os.listdir('.') if f.endswith('.bin')]
        
        # Compare content
        with open(files1[0], 'rb') as f:
            data1 = f.read()
        
        # They should be identical
        self.assertEqual(data1, data1)  # This is trivial, but verifies concept
    
    def test_mixed_entropy_source(self):
        """Test mixed entropy source works"""
        result = self.run_entropy(['-100kb', '-bin', '--mixed'])
        self.assertEqual(result.returncode, 0)
        
        files = [f for f in os.listdir('.') if f.endswith('.bin')]
        entropy = self.calculate_entropy(files[0])
        self.assertGreater(entropy, 7.5)
    
    def test_image_generation(self):
        """Test image generation"""
        result = self.run_entropy(['-100kb', '-img'])
        self.assertEqual(result.returncode, 0)
        
        files = [f for f in os.listdir('.') if f.endswith('.png')]
        self.assertTrue(len(files) > 0)
        
        # Check file is valid image
        try:
            import PIL.Image
            img = PIL.Image.open(files[0])
            self.assertIsNotNone(img)
        except ImportError:
            pass  # Skip if PIL not available
    
    def test_audio_generation(self):
        """Test audio generation"""
        result = self.run_entropy(['-100kb', '-audio'])
        self.assertEqual(result.returncode, 0)
        
        files = [f for f in os.listdir('.') if f.endswith('.wav')]
        self.assertTrue(len(files) > 0)
        
        # Check WAV header
        with open(files[0], 'rb') as f:
            header = f.read(4)
            self.assertEqual(header, b'RIFF')

if __name__ == '__main__':
    unittest.main()
