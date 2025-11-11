#!/usr/bin/env python3
"""
Generate a mapping between keywords and their CFG files from data_hierarchy.cfg files.
"""
import os
import json
import re
import time
from pathlib import Path
from collections import defaultdict

# Verbosity levels
VERBOSITY = 1  # 0=errors only, 1=info, 2=debug

# Regular expressions to parse data_hierarchy.cfg files
HIERARCHY_BLOCK_RE = re.compile(
    r'HIERARCHY\s*\{'
    r'(?:[^{}]*(?:\{[^{}]*\})*[^{}]*)*?'
    r'\}',
    re.DOTALL
)

KEYWORD_RE = re.compile(r'KEYWORD\s*=\s*([^;\n]+);', re.IGNORECASE)
FILE_RE = re.compile(r'FILE\s*=\s*"([^"]+)"', re.IGNORECASE)
USER_NAMES_RE = re.compile(r'USER_NAMES\s*=\s*\(([^)]*)\)', re.IGNORECASE | re.DOTALL)

def log(level, message):
    """Log messages based on verbosity level."""
    if level <= VERBOSITY:
        prefix = {
            0: "[ERROR] ",
            1: "[INFO]  ",
            2: "[DEBUG] "
        }.get(level, "")
        print(f"{prefix}{message}")

def parse_hierarchy_file(file_path):
    """Parse a data_hierarchy.cfg file and return a dictionary of keyword to CFG file mappings."""
    log(2, f"  Parsing {os.path.basename(file_path)}...")
    start_time = time.time()
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        log(0, f"Error reading {file_path}: {str(e)}")
        return {}
    
    mappings = {}
    blocks = list(HIERARCHY_BLOCK_RE.finditer(content))
    log(2, f"  Found {len(blocks)} hierarchy blocks to process")
    
    for i, block in enumerate(blocks, 1):
        if i % 100 == 0 or i == len(blocks):
            log(2, f"  Processed {i}/{len(blocks)} blocks...")
            
        block_content = block.group(0)
        
        # Extract file path (commented or not)
        file_match = FILE_RE.search(block_content)
        if not file_match:
            continue
        file_path = file_match.group(1).strip()
        
        # Extract user names (aliases)
        user_names_match = USER_NAMES_RE.search(block_content)
        if not user_names_match:
            continue
            
        # Process user names
        names_str = user_names_match.group(1).strip()
        user_names = [n.strip().strip('"\'') for n in names_str.split(',') if n.strip()]
        
        # Add all variations to the mappings with asterisk
        for kw in user_names:
            if kw:  # Skip empty keywords
                keyword = f"*{kw}"
                if keyword not in mappings:  # First match wins
                    mappings[keyword] = file_path
                    log(2, f"    Mapped {keyword} -> {file_path}")
    
    log(2, f"  Extracted {len(mappings)} unique keywords in {time.time() - start_time:.2f}s")
    return mappings

def load_data_hierarchy_files(json_file):
    """Load the list of data_hierarchy.cfg files from JSON."""
    with open(json_file, 'r') as f:
        return json.load(f)

def generate_mapping(hierarchy_files):
    """Generate a mapping from all data_hierarchy.cfg files."""
    keyword_map = defaultdict(list)
    total_files = len(hierarchy_files)
    processed_files = 0
    start_time = time.time()
    
    log(1, f"\nStarting to process {total_files} hierarchy files...")
    log(1, "=" * 80)
    log(1, "File Processing Progress:")
    log(1, "=" * 80)
    
    for file_info in hierarchy_files:
        processed_files += 1
        file_path = file_info['full_path']
        version = file_info['version']
        
        log(1, f"\n[File {processed_files}/{total_files}] Processing {version}...")
        log(2, f"  Full path: {file_path}")
        
        try:
            file_start_time = time.time()
            mappings = parse_hierarchy_file(file_path)
            print(file_path)
            print(mappings.items)
            
            for keyword, cfg_path in mappings.items():
                # Convert path to use forward slashes
                cfg_path = cfg_path.replace('\\', '/')
                # Add version information
                keyword_map[keyword].append({
                    'file': cfg_path,
                    'version': version,
                    'source': file_path
                })
            
            # Log processing time for this file
            file_time = time.time() - file_start_time
            log(1, f"  ✓ Processed in {file_time:.2f}s - Mapped {len(mappings)} keywords")
            
        except Exception as e:
            log(0, f"  ✗ Error processing {file_path}: {str(e)}")
            continue

def save_mapping(mapping, output_file):
    """Save the mapping to a JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

def main():
    # Configuration
    data_hierarchy_json = "/home/nemo/Dokumente/Sandbox/Fem_upgraded/gui/json/data_hierarchy_files.json"
    output_file = "/home/nemo/Dokumente/Sandbox/Fem_upgraded/gui/json/keyword_mapping_from_hierarchy.json"
    
    log(1, "Starting keyword mapping generation")
    log(1, "=" * 50)
    
    # Load hierarchy files
    log(1, f"Loading data hierarchy files from {data_hierarchy_json}")
    try:
        hierarchy_files = load_data_hierarchy_files(data_hierarchy_json)
        log(1, f"Successfully loaded {len(hierarchy_files)} data_hierarchy.cfg files")
    except Exception as e:
        log(0, f"Failed to load hierarchy files: {str(e)}")
        return 1
    
    # Generate mapping
    log(1, "\nStarting keyword mapping generation...")
    log(1, "-" * 50)
    
    start_time = time.time()
    try:
        print("hierarchy_files")
        print(hierarchy_files)
        mapping = generate_mapping(hierarchy_files)
        elapsed = time.time() - start_time
        
        log(1, "\n" + "=" * 50)
        log(1, f"Completed processing in {elapsed:.2f} seconds")
        log(1, f"Total unique keywords mapped: {len(mapping):,}")
        
        # Calculate some statistics
        versions_per_keyword = [len(versions) for versions in mapping.values()]
        avg_versions = sum(versions_per_keyword) / len(versions_per_keyword) if mapping else 0
        
        log(1, f"Average versions per keyword: {avg_versions:.1f}")
        log(1, f"Most common keywords:")
        
        # Show top 5 keywords with most versions
        sorted_keywords = sorted(mapping.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        for i, (keyword, versions) in enumerate(sorted_keywords, 1):
            log(1, f"  {i}. {keyword}: {len(versions)} versions")
        
        # Save results
        log(1, f"\nSaving mapping to {output_file}...")
        save_mapping(mapping, output_file)
        log(1, "Mapping saved successfully!")
        
        return 0
        
    except KeyboardInterrupt:
        log(1, "\n\nProcess interrupted by user. Saving current progress...")
        if 'mapping' in locals() and mapping:
            save_mapping(mapping, output_file)
            log(1, f"Partially completed mapping saved to {output_file}")
        return 1
    except Exception as e:
        log(0, f"\nError during mapping generation: {str(e)}")
        log(0, "No mapping was saved due to the error.")
        return 1

if __name__ == "__main__":
    main()