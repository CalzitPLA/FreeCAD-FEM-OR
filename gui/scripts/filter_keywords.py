#!/usr/bin/env python3
"""
Filter unified_keywords.json to only include keywords that exist in keywords_clean.json.
This ensures we maintain all the detailed information from the unified file
while only including keywords that have documentation.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Set, Any

def load_json_file(file_path: str) -> Any:
    """Load JSON data from a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json_file(data: Any, file_path: str) -> None:
    """Save data to a JSON file with proper formatting."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def normalize_keyword_name(name: str) -> str:
    """Normalize keyword name for comparison."""
    # Remove leading * if present and convert to uppercase
    return name.lstrip('*').upper()

def get_clean_keyword_names(clean_keywords: List[Dict]) -> Set[str]:
    """Extract all possible name variations from clean keywords."""
    names = set()
    for kw in clean_keywords:
        if 'name' in kw:
            names.add(normalize_keyword_name(kw['name']))
        if 'title' in kw:
            names.add(normalize_keyword_name(kw['title']))
    return names

def filter_unified_keywords(unified_data: Dict, clean_keywords: List[Dict]) -> Dict:
    """Filter unified keywords to only include those in clean_keywords."""
    clean_names = get_clean_keyword_names(clean_keywords)
    
    filtered_keywords = []
    matched_count = 0
    
    for kw in unified_data['keywords']:
        # Check all possible name variations in the unified keyword
        kw_names = set()
        if 'name' in kw:
            kw_names.add(normalize_keyword_name(kw['name']))
        if 'title' in kw:
            kw_names.add(normalize_keyword_name(kw['title']))
        
        # Check if any variation matches a clean keyword
        if any(name in clean_names for name in kw_names):
            matched_count += 1
            filtered_keywords.append(kw)
    
    # Update metadata
    result = {
        'metadata': {
            'source': 'Filtered from unified_keywords.json using keywords_clean.json',
            'total_keywords': len(filtered_keywords),
            'original_keywords': len(unified_data['keywords']),
            'matched_keywords': matched_count,
            'coverage': f"{(matched_count / len(clean_keywords) * 100):.1f}% of clean keywords matched"
        },
        'keywords': filtered_keywords
    }
    
    return result

def main():
    # Define file paths
    base_dir = Path("/home/nemo/Dokumente/Sandbox/Fem_upgraded")
    unified_file = base_dir / "gui" / "json" / "unified_keywords.json"
    clean_file = base_dir / "gui" / "json" / "keywords_clean.json"
    output_file = base_dir / "gui" / "json" / "filtered_keywords.json"
    
    print("Loading unified keywords...")
    unified_data = load_json_file(unified_file)
    print(f"Loaded {len(unified_data['keywords'])} unified keywords")
    
    print("Loading clean keywords...")
    clean_keywords = load_json_file(clean_file)
    print(f"Loaded {len(clean_keywords)} clean keywords")
    
    print("\nFiltering keywords...")
    filtered_data = filter_unified_keywords(unified_data, clean_keywords)
    
    # Save the filtered data
    save_json_file(filtered_data, output_file)
    
    # Print summary
    print("\n=== Filtering Complete ===")
    print(f"Original unified keywords: {len(unified_data['keywords'])}")
    print(f"Clean keywords: {len(clean_keywords)}")
    print(f"Matched keywords: {filtered_data['metadata']['matched_keywords']}")
    print(f"Coverage: {filtered_data['metadata']['coverage']}")
    print(f"\nOutput saved to: {output_file}")

if __name__ == "__main__":
    main()
