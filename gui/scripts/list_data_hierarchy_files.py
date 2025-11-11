#!/usr/bin/env python3
"""
List all data_hierarchy.cfg files in the CFG_Openradioss directory and save to JSON.
"""
import os
import json
from pathlib import Path

def find_data_hierarchy_files(base_dir):
    """Find all data_hierarchy.cfg files in the directory tree."""
    data_hierarchy_files = []
    
    for root, _, files in os.walk(base_dir):
        if 'data_hierarchy.cfg' in files:
            full_path = os.path.join(root, 'data_hierarchy.cfg')
            rel_path = os.path.relpath(full_path, base_dir)
            
            # Extract version from path (the parent directory name)
            version = os.path.basename(os.path.dirname(full_path))
            
            data_hierarchy_files.append({
                'full_path': full_path,
                'relative_path': rel_path,
                'version': version,
                'directory': os.path.dirname(full_path)
            })
    
    # Sort by version for better readability
    data_hierarchy_files.sort(key=lambda x: x['version'])
    return data_hierarchy_files

def main():
    base_dir = "/home/nemo/Dokumente/Sandbox/Fem_upgraded/gui/CFG_Openradioss"
    output_file = "/home/nemo/Dokumente/Sandbox/Fem_upgraded/gui/json/data_hierarchy_files.json"
    
    print(f"Searching for data_hierarchy.cfg files in: {base_dir}")
    files = find_data_hierarchy_files(base_dir)
    
    print(f"\nFound {len(files)} data_hierarchy.cfg files:")
    for i, file_info in enumerate(files, 1):
        print(f"{i:3d}. {file_info['version']:20} - {file_info['relative_path']}")
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(files, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()