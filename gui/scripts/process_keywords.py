#!/usr/bin/env python3
"""
Process OpenRadioss keywords from CFG files and merge with clean keywords.
"""
import os
import json
from pathlib import Path

def parse_cfg_file(cfg_path):
    """Parse a single CFG file and extract parameter information."""
    params = []
    current_section = None
    
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
                
            # Check for section headers
            if line.startswith('ATTRIBUTES'):
                current_section = 'attributes'
                continue
                
            # Parse parameter definitions
            if current_section == 'attributes' and '=' in line:
                # Extract parameter name and description
                parts = line.split('=')
                if len(parts) >= 2:
                    param_name = parts[0].strip()
                    # Extract description from comments
                    desc = line.split('//', 1)[1].strip() if '//' in line else ''
                    params.append({
                        'name': param_name,
                        'description': desc,
                        'type': 'FLOAT'  # Default type
                    })
    except Exception as e:
        print(f"Error parsing CFG file {cfg_path}: {str(e)}")
        
    return params

def process_cfg_files(cfg_dir):
    """Process all CFG files in the given directory."""
    cfg_dir = Path(cfg_dir)
    keywords = {}
    
    for cfg_file in cfg_dir.rglob('*.cfg'):
        keyword_name = cfg_file.stem.upper()
        params = parse_cfg_file(cfg_file)
        keywords[keyword_name] = {
            'name': keyword_name,
            'file': str(cfg_file),
            'parameters': params
        }
    
    return keywords

def load_clean_keywords(clean_json_path):
    """Load the clean keywords from JSON file."""
    with open(clean_json_path, 'r', encoding='utf-8') as f:
        return {kw['name'].upper(): kw for kw in json.load(f)}

def merge_keywords(cfg_keywords, clean_keywords):
    """Merge CFG keywords with clean keywords."""
    merged = {}
    
    # First add all clean keywords to preserve structure
    for name, kw in clean_keywords.items():
        merged[name] = kw.copy()
    
    # Update with CFG data
    for name, cfg_kw in cfg_keywords.items():
        if name in merged:
            # Update with CFG parameters if they exist
            if 'parameters' in cfg_kw and cfg_kw['parameters']:
                merged[name]['parameters'] = cfg_kw['parameters']
            # Add file path
            merged[name]['file'] = cfg_kw['file']
    
    return merged

def main():
    # Paths
    base_dir = Path(__file__).parent
    cfg_dir = base_dir / 'gui' / 'CFG_Openradioss'
    clean_json_path = base_dir / 'gui' / 'json' / 'keywords_clean.json'
    output_path = base_dir / 'gui' / 'json' / 'keywords_merged.json'
    
    # Process files
    print(f"Processing CFG files from: {cfg_dir}")
    cfg_keywords = process_cfg_files(cfg_dir)
    
    print(f"Loading clean keywords from: {clean_json_path}")
    clean_keywords = load_clean_keywords(clean_json_path)
    
    print("Merging keyword data...")
    merged_keywords = merge_keywords(cfg_keywords, clean_keywords)
    
    # Save merged keywords
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(list(merged_keywords.values()), f, indent=2)
    
    print(f"Saved merged keywords to: {output_path}")
    print(f"Processed {len(merged_keywords)} keywords")

if __name__ == "__main__":
    main()
