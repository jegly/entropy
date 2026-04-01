#!/usr/bin/env python3
"""Basic functional tests for entropy tool"""

import os
import sys
import subprocess
import tempfile
import unittest

class TestEntropyBasic(unittest.TestCase):
    """Basic test cases"""
    
    def setUp(self):
        """Create temporary directory for test files"""
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up test files"""
        os.chdir(self.original_dir)
        import shutil
        shutil.rmtree(self.test_dir)
    
    def run_entropy(self, args):
        """Run entropy script with args"""
        script_path = os.path.join(os.path.dirname(__file__), '..', 'entropy.py')
        cmd = [sys.executable, script_path] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result
    
    def test_binary_generation(self):
        """Test binary file generation"""
        result = self.run_entropy(['-1mb', '-bin'])
        self.assertEqual(result.returncode, 0)
        
        # Check file exists
        files = os.listdir('.')
        bin_files = [f for f in files if f.endswith('.bin')]
        self.assertEqual(len(bin_files), 1)
        
        # Check file size (approximately 1MB)
        size = os.path.getsize(bin_files[0])
        self.assertAlmostEqual(size, 1024*1024, delta=1024)
    
    def test_text_generation(self):
        """Test text file generation"""
        result = self.run_entropy(['-1mb', '-txt'])
        self.assertEqual(result.returncode, 0)
        
        # Check file exists
        files = os.listdir('.')
        txt_files = [f for f in files if f.endswith('.txt')]
        self.assertEqual(len(txt_files), 1)
        
        # Check file is readable text
        with open(txt_files[0], 'r') as f:
            content = f.read(1024)
            # Should contain printable characters
            self.assertTrue(any(c.isprintable() for c in content))
    
    def test_multi_file(self):
        """Test multi-file generation"""
        result = self.run_entropy(['-2mb', '-bin', '-multi', '2'])
        self.assertEqual(result.returncode, 0)
        
        # Check files exist
        files = os.listdir('.')
        bin_files = [f for f in files if f.endswith('.bin')]
        self.assertEqual(len(bin_files), 2)
        
        # Check total size
        total_size = sum(os.path.getsize(f) for f in bin_files)
        self.assertAlmostEqual(total_size, 2*1024*1024, delta=1024*10)
    
    def test_analysis(self):
        """Test entropy analysis"""
        result = self.run_entropy(['-100kb', '-bin', '--analyze'])
        self.assertEqual(result.returncode, 0)
        self.assertIn('Shannon entropy', result.stdout)
        self.assertIn('bits/byte', result.stdout)
    
    def test_help(self):
        """Test help output"""
        result = self.run_entropy(['--help'])
        self.assertEqual(result.returncode, 0)
        self.assertIn('ENTROPY', result.stdout)
    
    def test_invalid_size(self):
        """Test invalid size handling"""
        result = self.run_entropy(['-999zzz', '-bin'])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid size', result.stderr)

if __name__ == '__main__':
    unittest.main()
