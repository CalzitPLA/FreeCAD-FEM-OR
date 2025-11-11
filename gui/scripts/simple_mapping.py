#!/usr/bin/env python3
"""
Enhanced script to extract keyword mappings from data_hierarchy.cfg files with full paths.
Handles quoted strings in USER_NAMES and preserves underscores in keyword names.
"""
import os
import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
INPUT_JSON = os.path.join(PROJECT_ROOT, "gui", "json", "data_hierarchy_files.json")
OUTPUT_JSON = os.path.join(PROJECT_ROOT, "gui", "json", "keyword_mapping_verbose.json")
CFG_BASE_DIR = os.path.join(PROJECT_ROOT, "gui", "CFG_Openradioss")

# Regular expressions
HIERARCHY_PATTERN = r'HIERARCHY\s*\{.*?FILE\s*=\s*"([^"]+)".*?USER_NAMES\s*=\s*\(([^)]*)\)'
VERSION_PATTERN = r'Keyword(\d+)(?:_(R\d+(?:\.\d+)*))?'

def parse_user_names(names_str: str) -> List[str]:
    """Parse USER_NAMES string, handling quoted strings with commas."""
    names = []
    current = []
    in_quotes = False
    quote_char = None
    
    for char in names_str:
        if char in ('"', "'") and (not in_quotes or char == quote_char):
            in_quotes = not in_quotes
            if in_quotes:
                quote_char = char
            else:
                quote_char = None
            current.append(char)
        elif char == ',' and not in_quotes:
            name = ''.join(current).strip()
            if name:
                names.append(name.strip('\'"'))
            current = []
        else:
            current.append(char)
    
    # Add the last name if exists
    if current:
        name = ''.join(current).strip()
        if name:
            names.append(name.strip('\'"'))
    
    return names

def extract_mappings(file_path: str, version_dir: str) -> Dict[str, dict]:
    """Extract keyword mappings from a single data_hierarchy.cfg file with full paths."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return {}

    mappings = {}
    hierarchy_blocks = re.finditer(HIERARCHY_PATTERN, content, re.DOTALL)
    version_name = os.path.basename(version_dir)
    
    # Extract version info
    version_match = re.search(VERSION_PATTERN, version_name, re.IGNORECASE)
    version_info = {
        'base_version': version_match.group(1) if version_match else 'unknown',
        'release': version_match.group(2) if version_match and version_match.group(2) else 'base',
        'version_name': version_name
    }

    for match in hierarchy_blocks:
        if len(match.groups()) >= 2:
            rel_path = match.group(1).strip()
            names_str = match.group(2).strip()
            
            # Skip empty paths or names
            if not rel_path or not names_str:
                continue
                
            # Create full path and normalize it
            full_path = str(Path(version_dir) / rel_path)
            
            # Process user names with proper handling of quoted strings
            user_names = parse_user_names(names_str)
            
            # Add mappings with asterisk
            for name in user_names:
                if not name:
                    continue
                    
                keyword = f"*{name}" if not name.startswith('*') else name
                
                # Only add if this keyword isn't already mapped
                if keyword not in mappings:
                    mappings[keyword] = {
                        'relative_path': rel_path.replace('\\', '/'),
                        'full_path': full_path.replace('\\', '/'),
                        'version': version_info['version_name'],
                        'base_version': version_info['base_version'],
                        'release': version_info['release'],
                        'source_file': os.path.basename(file_path)
                    }

    return mappings

def load_file_list() -> List[dict]:
    """Load the list of data_hierarchy.cfg files to process."""
    try:
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            file_list = json.load(f)
        return file_list
    except Exception as e:
        print(f"Error loading input JSON {INPUT_JSON}: {e}", file=sys.stderr)
        sys.exit(1)

def save_mappings(mappings: dict, output_file: str) -> None:
    """Save the keyword mappings to a JSON file."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Sort keys for consistent output
        sorted_mappings = dict(sorted(mappings.items()))
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(
                sorted_mappings, 
                f, 
                indent=2, 
                ensure_ascii=False,
                sort_keys=True
            )
        print(f"\nSuccessfully saved {len(mappings)} keywords to {output_file}")
    except Exception as e:
        print(f"Error saving mappings to {output_file}: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    print(f"Loading file list from {INPUT_JSON}...")
    file_list = load_file_list()
    print(f"Found {len(file_list)} data_hierarchy.cfg files to process")
    
    all_mappings = {}
    stats = {
        'total_files': len(file_list),
        'processed_files': 0,
        'total_keywords': 0,
        'unique_keywords': 0,
        'errors': 0
    }
    
    print("\n" + "=" * 80)
    print(f"{'#':<4} {'Version':<20} {'Keywords':<10} Status")
    print("=" * 80)
    
    for i, file_info in enumerate(file_list, 1):
        file_path = file_info.get('full_path')
        version = file_info.get('version', 'unknown')
        
        if not file_path or not os.path.exists(file_path):
            print(f"{i:<4} {version:<20} {'-':<10} [ERROR] File not found: {file_path}")
            stats['errors'] += 1
            continue
            
        version_dir = os.path.dirname(file_path)
        
        try:
            mappings = extract_mappings(file_path, version_dir)
            new_keywords = len(mappings)
            stats['total_keywords'] += new_keywords
            stats['processed_files'] += 1
            
            # Update global mappings (first match wins)
            for k, v in mappings.items():
                if k not in all_mappings:
                    all_mappings[k] = v
            
            status = f"[OK] Mapped {new_keywords} keywords"
            print(f"{i:<4} {version:<20} {new_keywords:<10} {status}")
            
        except Exception as e:
            stats['errors'] += 1
            print(f"{i:<4} {version:<20} {'-':<10} [ERROR] {str(e)[:80]}")
    
    # Final statistics
    stats['unique_keywords'] = len(all_mappings)
    
    print("\n" + "=" * 80)
    print("Processing complete!")
    print(f"- Processed {stats['processed_files']}/{stats['total_files']} files")
    print(f"- Found {stats['total_keywords']} total keyword occurrences")
    print(f"- Extracted {stats['unique_keywords']} unique keywords")
    if stats['errors'] > 0:
        print(f"- Encountered {stats['errors']} errors")
    
    # Save the results
    save_mappings(all_mappings, OUTPUT_JSON)

if __name__ == "__main__":
    main()