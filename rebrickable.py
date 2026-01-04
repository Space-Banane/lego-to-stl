"""
Rebrickable API client for fetching LEGO set data.
Uses the official API for set metadata and parts list.
"""
from dotenv import load_dotenv
import requests
import os
from typing import Optional, Dict, List


class RebrickableClient:
    """Client for interacting with the Rebrickable API."""

    BASE_URL = "https://rebrickable.com/api/v3/lego"
    
    def __init__(self, api_key: Optional[str] = None):
        load_dotenv()
        self.api_key = api_key or os.environ.get("REBRICKABLE_API_KEY")
        if not self.api_key:
            raise ValueError("Rebrickable API key must be provided via parameter or REBRICKABLE_API_KEY env variable")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"key {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "ldraw2stl/lego-experiments"
        })

    def get_set_metadata(self, set_number: str) -> Optional[Dict[str, any]]:
        """
        Fetch set metadata from the API.
        Args:
            set_number: The LEGO set number (e.g., "10245-1")
        Returns:
            Dictionary with metadata or None if not found
        """
        url = f"{self.BASE_URL}/sets/{set_number}/"
        try:
            resp = self.session.get(url)
            if resp.status_code == 404:
                print(f"Set {set_number} not found")
                return None
            resp.raise_for_status()
            data = resp.json()
            # Map to legacy keys for compatibility
            metadata = {
                'inventory_id': data.get('set_num', ''),
                'name': data.get('name', ''),
                'released': data.get('year', ''),
                'inventory': data.get('num_parts', ''),
                'theme': data.get('theme_id', ''),
                'raw': data
            }
            return metadata
        except Exception as e:
            print(f"Error fetching set metadata: {e}")
            return None

    def get_parts_list(self, set_number: str, page_size: int = 1000) -> Optional[List[Dict[str, str]]]:
        """
        Download the parts list for the given set number.
        Args:
            set_number: The LEGO set number (e.g., "10245-1")
            page_size: Number of results per page (default: 1000)
        Returns:
            List of dictionaries representing the parts
        """
        url = f"{self.BASE_URL}/sets/{set_number}/parts/"
        params = {"page": 1, "page_size": page_size}
        all_parts = []
        try:
            while True:
                resp = self.session.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                all_parts.extend(results)
                if not data.get("next"):
                    break
                params["page"] += 1
            return all_parts
        except Exception as e:
            print(f"Error fetching parts list: {e}")
            return None

    def fetch_set_data(self, set_number: str) -> Optional[Dict[str, any]]:
        """
        Complete workflow: fetch metadata and download parts list.
        Args:
            set_number: The LEGO set number (e.g., "10245-1")
        Returns:
            Dictionary containing 'metadata' and 'parts' or None if failed
        """
        metadata = self.get_set_metadata(set_number)
        if not metadata:
            return None
        print(f"✓ Fetched metadata: {metadata['name']} (Set: {set_number})")
        parts = self.get_parts_list(set_number)
        if not parts:
            print(f"Could not fetch parts list for set {set_number}")
            return None
        print(f"✓ Downloaded {len(parts)} parts")
        return {
            'metadata': metadata,
            'parts': parts,
            'set_number': set_number
        }

    def validate_set(self, set_number: str) -> Optional[Dict[str, any]]:
        """
        Validate if a LEGO set exists using the API.
        Args:
            set_number: The LEGO set number (e.g., "10245-1" or "10245")
        Returns:
            Metadata dict if found, else None
        """
        # Try with -1 suffix if not present
        if '-' not in set_number:
            set_number_full = f"{set_number}-1"
        else:
            set_number_full = set_number
        metadata = self.get_set_metadata(set_number_full)
        if metadata:
            return metadata
        # If not found and already had -1, try without
        if '-' in set_number:
            base_num = set_number.split('-')[0]
            metadata = self.get_set_metadata(base_num)
            if metadata:
                return metadata
        return None

if __name__ == "__main__":
    # Test the API client with set 10245-1
    import sys
    set_num = "10245-1"
    if len(sys.argv) > 1:
        set_num = sys.argv[1]
    client = RebrickableClient()
    data = client.fetch_set_data(set_num)
    if data:
        print("\n" + "="*50)
        print(f"Set: {data['metadata']['name']}")
        print(f"Released: {data['metadata']['released']}")
        print(f"Theme ID: {data['metadata']['theme']}")
        print(f"Parts: {len(data['parts'])}")
        print("\nFirst 5 parts:")
        for i, part in enumerate(data['parts'][:5], 1):
            part_num = part.get('part', {}).get('part_num', 'N/A')
            color = part.get('color', {}).get('name', 'N/A')
            qty = part.get('quantity', 'N/A')
            print(f"  {i}. Part {part_num}, Color {color}, Qty {qty}")
