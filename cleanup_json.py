#!/usr/bin/env python3
"""
Clean up unnecessary JSON files from the Fem_upgraded workbench.
"""

import os
from pathlib import Path

# Base directory
base_dir = Path(__file__).parent.absolute()

# JSON files to keep (relative to base_dir)
FILES_TO_KEEP = {
    'templates.json',
    'ls_dyna_syntax_user_friendly.json',
    'gui/ls_dyna_syntax_user_friendly.json',
    'gui/openradioss_keywords_clean.json',
    'gui/openradioss_keywords_with_parameters.json',
}

# File patterns to remove
PATTERNS_TO_REMOVE = [
    'comprehensive_*.json',
    '*_sample.json',
    'backup_*.json',
    '*_review.json',
    '*_clean.json',
    '*_with_parameters.json',
    'hm_reader_keywords.json',
    'enhanced_hm_reader_keywords.json'
]

def get_json_files():
    """Get all JSON files in the directory."""
    return list(base_dir.rglob('*.json'))

def should_keep(file_path):
    """Check if a file should be kept."""
    rel_path = file_path.relative_to(base_dir)
    
    # Always keep files in the whitelist
    if str(rel_path) in FILES_TO_KEEP:
        return True
        
    # Check if file matches any remove pattern
    for pattern in PATTERNS_TO_REMOVE:
        if rel_path.match(pattern):
            return False
            
    # Keep files in gui/ directory
    if 'gui' in str(rel_path.parts):
        return True
        
    # Keep by default (be conservative)
    return True

def cleanup():
    """Clean up unnecessary JSON files."""
    print("Scanning for JSON files...")
    json_files = get_json_files()
    
    files_to_remove = []
    files_to_keep = []
    
    for file_path in json_files:
        if should_keep(file_path):
            files_to_keep.append(file_path)
        else:
            files_to_remove.append(file_path)
    
    # Print summary
    print("\nFiles to keep:")
    for f in sorted(files_to_keep, key=lambda x: str(x)):
        print(f"  KEEP: {f.relative_to(base_dir)}")
    
    print("\nFiles to remove:")
    for f in sorted(files_to_remove, key=lambda x: str(x)):
        print(f"  REMOVE: {f.relative_to(base_dir)}")
    
    # Ask for confirmation
    confirm = input(f"\nRemove {len(files_to_remove)} files? (y/N): ")
    if confirm.lower() != 'y':
        print("Cleanup cancelled.")
        return
    
    # Remove files
    removed_count = 0
    for file_path in files_to_remove:
        try:
            file_path.unlink()
            print(f"Removed: {file_path.relative_to(base_dir)}")
            removed_count += 1
        except Exception as e:
            print(f"Error removing {file_path}: {e}")
    
    print(f"\nCleanup complete. Removed {removed_count} files.")

if __name__ == "__main__":
    cleanup()
