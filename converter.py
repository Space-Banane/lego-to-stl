"""
STL converter module for converting LDraw .dat files to STL format.
Uses the ldraw2stl tool via subprocess.
"""

import subprocess
import os
import platform
from pathlib import Path
from typing import Optional, List, Dict
import shutil


class STLConverter:
    """Handles conversion of LDraw .dat files to STL format."""
    
    def __init__(
        self,
        ldraw_dir: str = "ldraw",
        ldraw2stl_bin: str = "ldraw2stl/bin/dat2stl",
        output_base_dir: str = "sets"
    ):
        """
        Initialize the STL converter.
        
        Args:
            ldraw_dir: Path to the LDraw library directory
            ldraw2stl_bin: Path to the dat2stl executable
            output_base_dir: Base directory for set outputs
        """
        self.ldraw_dir = os.path.abspath(ldraw_dir)
        self.ldraw2stl_bin = ldraw2stl_bin
        self.output_base_dir = output_base_dir
        self.is_windows = platform.system() == "Windows"
        
        # Check if Perl is available
        self._check_perl()
    
    def _check_perl(self) -> bool:
        """Check if Perl is installed and accessible."""
        try:
            result = subprocess.run(
                ["perl", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("✓ Perl is available")
                return True
            else:
                print("⚠ Warning: Perl not found. Install Strawberry Perl on Windows.")
                return False
        except Exception as e:
            print(f"⚠ Warning: Could not check Perl: {e}")
            return False
    
    def part_exists(self, part_number: str) -> bool:
        """
        Check if a part .dat file exists in the LDraw library.
        
        Args:
            part_number: The part number (e.g., "3024")
            
        Returns:
            True if part exists, False otherwise
        """
        part_path = os.path.join(self.ldraw_dir, "parts", f"{part_number}.dat")
        exists = os.path.exists(part_path)
        
        if not exists:
            # Try with lowercase
            part_path = os.path.join(self.ldraw_dir, "parts", f"{part_number.lower()}.dat")
            exists = os.path.exists(part_path)
        
        return exists
    
    def convert_part(
        self,
        part_number: str,
        output_path: str,
        use_cache: bool = True
    ) -> bool:
        """
        Convert a single LDraw .dat file to STL.
        
        Args:
            part_number: The part number (e.g., "3024")
            output_path: Full path for the output STL file
            use_cache: Whether to use caching (recommended)
            
        Returns:
            True if successful, False otherwise
        """
        # Check if part exists
        if not self.part_exists(part_number):
            print(f"⚠ Warning: Part {part_number}.dat not found in LDraw library")
            return False
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Build command
        part_file = os.path.join(self.ldraw_dir, "parts", f"{part_number}.dat")
        
        cmd = [
            "perl",
            self.ldraw2stl_bin,
            "--file", part_file,
            "--ldrawdir", self.ldraw_dir
        ]
        
        if use_cache:
            cmd.append("--cache")
        
        try:
            # Run conversion
            if self.is_windows:
                # On Windows, use PowerShell's Out-File with ASCII encoding
                # Run perl command and capture output
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=False,  # Get binary output
                    timeout=60
                )
                
                if result.returncode != 0:
                    stderr = result.stderr.decode('utf-8', errors='ignore')
                    print(f"✗ Error converting {part_number}: {stderr}")
                    return False
                
                # Write output to file (ASCII encoding for STL)
                with open(output_path, 'wb') as f:
                    f.write(result.stdout)
            else:
                # On Unix-like systems, use shell redirection
                with open(output_path, 'w') as f:
                    result = subprocess.run(
                        cmd,
                        stdout=f,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=60
                    )
                
                if result.returncode != 0:
                    print(f"✗ Error converting {part_number}: {result.stderr}")
                    return False
            
            print(f"✓ Converted {part_number}.dat → {os.path.basename(output_path)}")
            return True
            
        except subprocess.TimeoutExpired:
            print(f"✗ Timeout converting {part_number}")
            return False
        except Exception as e:
            print(f"✗ Error converting {part_number}: {e}")
            return False
    
    def convert_set(
        self,
        set_number: str,
        parts: List[Dict[str, any]],
        skip_existing: bool = True
    ) -> Dict[str, any]:
        """
        Convert all parts for a LEGO set.
        
        Args:
            set_number: The LEGO set number
            parts: List of part dictionaries from metadata
            skip_existing: Skip parts that already have STL files
            
        Returns:
            Dictionary with conversion statistics
        """
        stl_dir = os.path.join(self.output_base_dir, set_number, "stls")
        os.makedirs(stl_dir, exist_ok=True)
        
        stats = {
            'total': 0,
            'converted': 0,
            'skipped': 0,
            'failed': 0,
            'missing': 0,
            'failed_parts': []
        }
        
        # Get unique parts (avoid converting same part multiple times)
        unique_parts = {}
        for part in parts:
            part_num = part['part_num']
            if part_num not in unique_parts:
                unique_parts[part_num] = part
        
        stats['total'] = len(unique_parts)
        
        print(f"\nConverting {stats['total']} unique parts for set {set_number}...")
        print("=" * 60)
        
        for part_num, part_data in unique_parts.items():
            output_path = os.path.join(stl_dir, f"{part_num}.stl")
            
            # Skip if already exists
            if skip_existing and os.path.exists(output_path):
                stats['skipped'] += 1
                print(f"⊘ Skipped {part_num} (already exists)")
                continue
            
            # Check if part exists in library
            if not self.part_exists(part_num):
                stats['missing'] += 1
                stats['failed_parts'].append({
                    'part_num': part_num,
                    'reason': 'Part not found in LDraw library'
                })
                continue
            
            # Convert the part
            success = self.convert_part(part_num, output_path)
            
            if success:
                stats['converted'] += 1
            else:
                stats['failed'] += 1
                stats['failed_parts'].append({
                    'part_num': part_num,
                    'reason': 'Conversion failed'
                })
        
        print("=" * 60)
        print(f"\nConversion Summary:")
        print(f"  Total unique parts: {stats['total']}")
        print(f"  ✓ Converted: {stats['converted']}")
        print(f"  ⊘ Skipped: {stats['skipped']}")
        print(f"  ✗ Failed: {stats['failed']}")
        print(f"  ⚠ Missing: {stats['missing']}")
        
        if stats['failed_parts']:
            print(f"\nFailed parts:")
            for failed in stats['failed_parts'][:10]:  # Show first 10
                print(f"  - {failed['part_num']}: {failed['reason']}")
            if len(stats['failed_parts']) > 10:
                print(f"  ... and {len(stats['failed_parts']) - 10} more")
        
        return stats
    
    def get_stl_path(self, set_number: str, part_number: str) -> str:
        """
        Get the path to an STL file for a given part.
        
        Args:
            set_number: The LEGO set number
            part_number: The part number
            
        Returns:
            Path to the STL file
        """
        return os.path.join(self.output_base_dir, set_number, "stls", f"{part_number}.stl")
    
    def stl_exists(self, set_number: str, part_number: str) -> bool:
        """
        Check if an STL file exists for a part.
        
        Args:
            set_number: The LEGO set number
            part_number: The part number
            
        Returns:
            True if STL exists, False otherwise
        """
        return os.path.exists(self.get_stl_path(set_number, part_number))


if __name__ == "__main__":
    # Test the converter
    converter = STLConverter()
    
    # Test with a simple part
    test_part = "3024"  # Plate 1x1
    test_output = "test_output/3024.stl"
    
    print(f"Testing conversion of part {test_part}...")
    print(f"Part exists: {converter.part_exists(test_part)}")
    
    if converter.part_exists(test_part):
        success = converter.convert_part(test_part, test_output)
        if success:
            print(f"✓ Test successful! Output: {test_output}")
            # Check file size
            size = os.path.getsize(test_output)
            print(f"  File size: {size:,} bytes")
