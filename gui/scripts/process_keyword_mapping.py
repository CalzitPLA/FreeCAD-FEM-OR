#!/usr/bin/env python3
"""
Process the keyword mapping JSON file and extract information about each keyword.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Any

def load_keyword_mapping(file_path: str) -> Dict[str, Any]:
    """Load and parse the keyword mapping JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def process_keywords(mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process the keyword mapping and extract relevant information."""
    results = []
    
    for keyword, data in mapping.items():
        result = {
            'keyword': keyword,
            'relative_path': data.get('relative_path', ''),
            'full_path': data.get('full_path', ''),
            'version': data.get('version', ''),
            'category': '',
            'config_file': ''
        }
        
        # Extract category from relative path (first directory)
        if '/' in data.get('relative_path', ''):
            result['category'] = data['relative_path'].split('/')[0]
        
        # Extract config file name
        result['config_file'] = os.path.basename(data.get('relative_path', ''))
        
        results.append(result)
    
    return results

def generate_report(keywords: List[Dict[str, Any]], output_file: str = None) -> str:
    """Generate a report from the processed keywords."""
    # Group by category
    categories = {}
    for kw in keywords:
        category = kw['category'] or 'UNCATEGORIZED'
        if category not in categories:
            categories[category] = []
        categories[category].append(kw)
    
    # Generate report
    report = []
    report.append("=" * 80)
    report.append("KEYWORD MAPPING REPORT")
    report.append("=" * 80)
    report.append(f"Total keywords: {len(keywords)}")
    report.append(f"Categories: {len(categories)}")
    report.append("\n")
    
    # Sort categories alphabetically
    for category in sorted(categories.keys()):
        kws = categories[category]
        report.append(f"[{category}] ({len(kws)} keywords)")
        report.append("-" * 80)
        
        # Sort keywords alphabetically
        for kw in sorted(kws, key=lambda x: x['keyword']):
            report.append(f"{kw['keyword']:40} | {kw['config_file']}")
        report.append("")
    
    report_text = "\n".join(report)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report_text)
    
    return report_text

def main():
    # Path to the keyword mapping file
    mapping_file = "/home/nemo/Dokumente/Sandbox/Fem_upgraded/gui/json/keep/keyword_mapping_verbose.json"
    output_file = "keyword_mapping_report.txt"
    
    if not os.path.exists(mapping_file):
        print(f"Error: Mapping file not found at {mapping_file}")
        return
    
    print(f"Loading keyword mapping from {mapping_file}...")
    mapping = load_keyword_mapping(mapping_file)
    
    print(f"Processing {len(mapping)} keywords...")
    keywords = process_keywords(mapping)
    
    print(f"Generating report to {output_file}...")
    report = generate_report(keywords, output_file)
    
    print("\nSummary:")
    print(f"- Total keywords processed: {len(keywords)}")
    categories = set(kw['category'] for kw in keywords)
    print(f"- Categories found: {len(categories)}")
    print(f"- Report saved to: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    main()
