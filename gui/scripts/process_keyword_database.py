#!/usr/bin/env python3
"""
Process the keyword database results and generate a clean version with web links.
"""
import json
import os
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('process_keyword_database.log'),
        logging.StreamHandler()
    ]
)

def load_json_file(file_path):
    """Load a JSON file and return its contents."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading {file_path}: {str(e)}")
        raise

def load_clean_keywords(clean_keywords_path):
    """Load the clean keywords and extract web links."""
    clean_keywords = {}
    try:
        with open(clean_keywords_path, 'r') as f:
            for line in f:
                if '=' in line:
                    keyword, url = line.strip().split('=', 1)
                    clean_keywords[keyword.strip()] = url.strip()
    except FileNotFoundError:
        logging.warning(f"Clean keywords file not found: {clean_keywords_path}")
    return clean_keywords

def process_keyword_database(results_path, clean_keywords_path, output_path):
    """Process the keyword database results and generate a clean version."""
    # Load the results
    try:
        results = load_json_file(results_path)
    except Exception as e:
        logging.error(f"Failed to load results: {str(e)}")
        return
    
    # Load clean keywords with web links
    clean_keywords = load_clean_keywords(clean_keywords_path)
    
    # Process successful keywords
    processed = {}
    for item in results.get('successful', []):
        keyword = item['keyword']
        
        # Skip unsupported keywords
        if 'UNSUPPORTED' in keyword.upper():
            continue
            
        # Get web link if available
        web_link = clean_keywords.get(keyword, '')
        
        # Add to processed dictionary
        processed[keyword] = {
            'file': item['file'],
            'data': item['data'],
            'web_link': web_link
        }
    
    # Save the processed results
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(processed, f, indent=2)
        logging.info(f"Processed {len(processed)} keywords. Results saved to {output_path}")
    except Exception as e:
        logging.error(f"Error saving processed results: {str(e)}")

def main():
    # Configuration
    base_dir = Path('/home/nemo/Dokumente/Sandbox/Fem_upgraded')
    
    # Input files
    results_file = base_dir / 'gui' / 'json' / 'keep' / 'keyword_database_results.json'
    clean_keywords_file = base_dir / 'gui' / 'json' / 'clean_keywords.txt'  # Update this path
    
    # Output file
    output_file = base_dir / 'gui' / 'json' / 'processed_keywords.json'
    
    # Process the keyword database
    process_keyword_database(
        results_file,
        clean_keywords_file,
        output_file
    )

if __name__ == "__main__":
    main()
