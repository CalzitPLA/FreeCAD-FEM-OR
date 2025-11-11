import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

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

def find_matching_keyword(keyword_name: str, keywords_list: List[Dict]) -> Optional[Dict]:
    """Find a keyword in the list that matches the given name with flexible matching."""
    if not keyword_name:
        return None
        
    normalized_name = normalize_keyword_name(keyword_name)
    
    # Try different match strategies in order of strictness
    strategies = [
        # 1. Exact match with name or title
        lambda kw: ('name' in kw and normalize_keyword_name(kw['name']) == normalized_name) or 
                  ('title' in kw and normalize_keyword_name(kw['title']) == normalized_name),
                  
        # 2. Match without parameters in parentheses
        lambda kw: (any(normalize_keyword_name(kw.get(field, '')).split('(')[0].strip() == 
                       normalized_name.split('(')[0].strip() 
                       for field in ['name', 'title'] if field in kw)),
        
        # 3. Match with common prefix (e.g., "CONTACT" matches "CONTACT_AIRBAG")
        lambda kw: (any(normalized_name in normalize_keyword_name(kw.get(field, '')) or 
                       normalize_keyword_name(kw.get(field, '')).startswith(normalized_name + '_') or
                       normalized_name.startswith(normalize_keyword_name(kw.get(field, '')).split('_')[0] + '_')
                       for field in ['name', 'title'] if field in kw)),
        
        # 4. Match with words in any order (split by _ and check all words are present)
        lambda kw: (any(
            all(word in normalize_keyword_name(kw.get(field, '')) 
                for word in normalized_name.split('_') if word)
            for field in ['name', 'title'] if field in kw
        ))
    ]
    
    # Try each strategy in order
    for strategy in strategies:
        for kw in keywords_list:
            if strategy(kw):
                return kw
    
    # If we get here, no match was found
    return None

def merge_keyword_data(dynamic_kw: Dict, clean_kw: Optional[Dict]) -> Dict:
    """Merge data from dynamic and clean keyword entries."""
    # Start with dynamic keyword data as base
    merged = dynamic_kw.copy()
    
    if not clean_kw:
        return merged
    
    # Merge in data from clean keyword (prefer clean data for these fields)
    merged.update({
        'id': clean_kw.get('id'),
        'description': clean_kw.get('description') or merged.get('description', ''),
        'documentation': clean_kw.get('documentation', merged.get('documentation', '')),
        'category': clean_kw.get('category', merged.get('category', 'General'))
    })
    
    return merged

def combine_keywords(dynamic_file: str, clean_file: str, output_file: str) -> Dict:
    """Combine data from dynamic_cfg_editor_keywords.json and keywords_clean.json."""
    print(f"Loading keywords from {dynamic_file}...")
    dynamic_keywords = load_json_file(dynamic_file)
    print(f"Loaded {len(dynamic_keywords)} keywords from {dynamic_file}")
    
    print(f"Loading documentation from {clean_file}...")
    clean_keywords = load_json_file(clean_file)
    print(f"Loaded {len(clean_keywords)} documented keywords from {clean_file}")
    
    # Create a list to store the merged keywords
    merged_keywords = []
    matched_count = 0
    
    # First pass: process all dynamic keywords
    for dyn_kw in dynamic_keywords:
        # Get the best name for matching
        kw_name = dyn_kw.get('title') or dyn_kw.get('name', '')
        
        # Find matching clean keyword
        clean_kw = find_matching_keyword(kw_name, clean_keywords)
        
        if clean_kw:
            matched_count += 1
        
        # Merge the data
        merged = merge_keyword_data(dyn_kw, clean_kw)
        merged_keywords.append(merged)
    
    # Second pass: find any clean keywords that weren't in the dynamic list
    matched_names = set()
    for kw in merged_keywords:
        if 'name' in kw:
            matched_names.add(normalize_keyword_name(kw['name']))
        if 'title' in kw:
            matched_names.add(normalize_keyword_name(kw['title']))
    
    for clean_kw in clean_keywords:
        kw_name = clean_kw.get('name', '')
        if kw_name and normalize_keyword_name(kw_name) not in matched_names:
            # This keyword wasn't in the dynamic list, add it
            merged_keywords.append({
                'name': clean_kw['name'],
                'title': clean_kw.get('title', clean_kw['name']),
                'category': clean_kw.get('category', 'General'),
                'description': clean_kw.get('description', ''),
                'documentation': clean_kw.get('documentation', ''),
                'parameters': clean_kw.get('parameters', []),
                'source': 'keywords_clean.json'
            })
    
    # Create the final structure
    result = {
        'metadata': {
            'source_files': [dynamic_file, clean_file],
            'total_keywords': len(merged_keywords),
            'keywords_with_documentation': matched_count,
            'documentation_coverage': f"{(matched_count / len(merged_keywords) * 100):.1f}%"
        },
        'keywords': merged_keywords
    }
    
    # Save the result
    save_json_file(result, output_file)
    
    return result

def main():
    # Define file paths
    base_dir = Path("/home/nemo/Dokumente/Sandbox/Fem_upgraded")
    dynamic_file = base_dir / "gui" / "json" / "dynamic_cfg_editor_keywords.json"
    clean_file = base_dir / "gui" / "json" / "keywords_clean.json"
    output_file = base_dir / "gui" / "json" / "unified_keywords.json"
    
    # Run the combination
    print(f"Starting keyword combination...")
    result = combine_keywords(str(dynamic_file), str(clean_file), str(output_file))
    
    # Print summary
    print("\n=== Keyword Combination Complete ===")
    print(f"Total keywords: {result['metadata']['total_keywords']}")
    print(f"Keywords with documentation: {result['metadata']['keywords_with_documentation']}")
    print(f"Documentation coverage: {result['metadata']['documentation_coverage']}")
    print(f"\nOutput saved to: {output_file}")

if __name__ == "__main__":
    main()
