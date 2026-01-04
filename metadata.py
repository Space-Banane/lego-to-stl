"""
Metadata handler module for creating and managing .set.json files.
Handles color mapping and set information storage.
"""

import json
import csv
import os
from typing import Dict, List, Optional
from pathlib import Path


class MetadataHandler:
    """Handles creation and management of set metadata files."""
    
    def __init__(self, colors_csv_path: str = "colors.csv"):
        """
        Initialize the metadata handler.
        
        Args:
            colors_csv_path: Path to the colors.csv file
        """
        self.colors_csv_path = colors_csv_path
        self.colors_map = self._load_colors()
    
    def _load_colors(self) -> Dict[str, Dict[str, str]]:
        """
        Load colors from colors.csv into a dictionary.
        
        Returns:
            Dictionary mapping color_id to color information
        """
        colors = {}
        
        try:
            with open(self.colors_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    colors[row['id']] = {
                        'name': row['name'],
                        'rgb': row['rgb'],
                        'is_trans': row['is_trans'].lower() == 'true'
                    }
            
            print(f"✓ Loaded {len(colors)} colors from {self.colors_csv_path}")
            return colors
            
        except Exception as e:
            print(f"Error loading colors.csv: {e}")
            return {}
    
    def get_color_info(self, color_id: str) -> Optional[Dict[str, any]]:
        """
        Get color information for a given color ID.
        
        Args:
            color_id: The color ID as string
            
        Returns:
            Dictionary with color info or None if not found
        """
        return self.colors_map.get(color_id)
    
    def create_set_metadata(
        self,
        set_number: str,
        metadata: Dict[str, str],
        parts: List[Dict[str, str]],
        output_dir: str = "sets"
    ) -> bool:
        """
        Create a .set.json file with complete set information.
        
        Args:
            set_number: The LEGO set number (e.g., "10245")
            metadata: Dictionary with name, released, inventory, theme
            parts: List of parts from Rebrickable API (nested format)
            output_dir: Base directory for sets (default: "sets")
            
        Returns:
            True if successful, False otherwise
        """
        set_dir = os.path.join(output_dir, set_number)
        os.makedirs(set_dir, exist_ok=True)
        
        # Process parts with color information
        parts_with_colors = []
        missing_colors = set()
        
        for part in parts:
            # Handle nested API format: part has 'part', 'color', 'quantity' fields
            part_obj = part.get('part', {})
            color_obj = part.get('color', {})
            
            part_num = part_obj.get('part_num', '')
            color_id = str(color_obj.get('id', ''))  # Color ID from API
            quantity = part.get('quantity', 1)
            is_spare = part.get('is_spare', False)
            
            color_info = self.get_color_info(color_id)
            
            # Use API color info if not in our CSV
            if not color_info:
                missing_colors.add(color_id)
                color_info = {
                    'name': color_obj.get('name', 'Unknown'),
                    'rgb': color_obj.get('rgb', '000000'),
                    'is_trans': color_obj.get('is_trans', False)
                }
            
            part_data = {
                'part_num': part_num,
                'color_id': color_id,
                'color_name': color_info['name'],
                'color_rgb': color_info['rgb'],
                'is_transparent': color_info['is_trans'],
                'quantity': int(quantity) if isinstance(quantity, (int, float)) else 1,
                'is_spare': is_spare
            }
            
            parts_with_colors.append(part_data)
        
        if missing_colors:
            print(f"⚠ Warning: Missing color data for IDs: {', '.join(missing_colors)}")
        
        # Create the complete metadata structure
        set_data = {
            'set_number': set_number,
            'name': metadata.get('name', ''),
            'released': metadata.get('released', ''),
            'inventory': metadata.get('inventory', ''),
            'theme': metadata.get('theme', ''),
            'total_parts': len(parts_with_colors),
            'unique_parts': len(set(p['part_num'] for p in parts_with_colors)),
            'parts': parts_with_colors
        }
        
        # Write to .set.json
        json_path = os.path.join(set_dir, '.set.json')
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(set_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Created metadata file: {json_path}")
            print(f"  - {set_data['total_parts']} total parts")
            print(f"  - {set_data['unique_parts']} unique parts")
            
            return True
            
        except Exception as e:
            print(f"Error creating metadata file: {e}")
            return False
    
    def load_set_metadata(self, set_number: str, output_dir: str = "sets") -> Optional[Dict]:
        """
        Load existing .set.json file for a set.
        
        Args:
            set_number: The LEGO set number
            output_dir: Base directory for sets
            
        Returns:
            Dictionary with set data or None if not found
        """
        json_path = os.path.join(output_dir, set_number, '.set.json')
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error loading metadata: {e}")
            return None
    
    def set_exists(self, set_number: str, output_dir: str = "sets") -> bool:
        """
        Check if a set has already been processed.
        
        Args:
            set_number: The LEGO set number
            output_dir: Base directory for sets
            
        Returns:
            True if set exists, False otherwise
        """
        json_path = os.path.join(output_dir, set_number, '.set.json')
        return os.path.exists(json_path)
    
    def get_parts_to_convert(self, set_number: str, output_dir: str = "sets") -> List[Dict]:
        """
        Get list of unique parts that need STL conversion.
        
        Args:
            set_number: The LEGO set number
            output_dir: Base directory for sets
            
        Returns:
            List of unique part dictionaries
        """
        metadata = self.load_set_metadata(set_number, output_dir)
        if not metadata:
            return []
        
        # Get unique parts (same part can appear in multiple colors)
        unique_parts = {}
        for part in metadata['parts']:
            part_num = part['part_num']
            if part_num not in unique_parts:
                unique_parts[part_num] = part
        
        return list(unique_parts.values())


if __name__ == "__main__":
    # Test the metadata handler
    handler = MetadataHandler()
    
    # Example metadata and parts (API format)
    metadata = {
        'name': 'Santa\'s Workshop',
        'released': '2014',
        'inventory': '884',
        'theme': 'Seasonal'
    }
    
    # API format with nested part/color objects
    parts = [
        {'part': {'part_num': '3024'}, 'color': {'id': 0, 'name': 'Black', 'rgb': '05131D'}, 'quantity': 6, 'is_spare': False},
        {'part': {'part_num': '3024'}, 'color': {'id': 4, 'name': 'Red', 'rgb': 'C91A09'}, 'quantity': 2, 'is_spare': False},
        {'part': {'part_num': '3894'}, 'color': {'id': 72, 'name': 'Dark Bluish Gray', 'rgb': '6C6E68'}, 'quantity': 4, 'is_spare': False},
    ]
    
    # Test creation
    success = handler.create_set_metadata('test-set', metadata, parts)
    
    if success:
        # Test loading
        loaded = handler.load_set_metadata('test-set')
        print(f"\nLoaded set: {loaded['name']}")
        print(f"Parts to convert: {len(handler.get_parts_to_convert('test-set'))}")
