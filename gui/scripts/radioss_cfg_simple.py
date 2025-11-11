#!/usr/bin/env python3
"""
Simple Radioss CFG Parser - Extracts common values and attributes from Radioss CFG files
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any
import logging
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cfg_parser.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class CommonValue:
    """Represents a common value found in CFG files"""
    name: str
    value_type: str
    default: str = ""
    description: str = ""

class RadiossCfgParser:
    """Simple parser for Radioss CFG files"""
    
    def __init__(self):
        self.patterns = {
            'title': r'^/\*\s*(.*?)\s*\*/',
            'keyword': r'^(\w+)\s*$',
            'parameter': r'#\s*(\d+)\s+(\w+)\s+(\w+)(?:\s+([^#]*?))?\s*(?:#\s*(.*))?$',
            'value_def': r'(\w+)\s*=\s*VALUE\s*\(\s*([^,)]+)(?:\s*,\s*"([^"]*)")?\s*\)',
            'attr_section': r'ATTRIBUTES\s*\(\s*(\w+)\s*\)\s*\{([^}]*)\}',
            'common_value': r'^\s*(\w+)\s*=\s*([^#;\n]+)(?:\s*#\s*(.*))?$',
            'section': r'^\s*\[([^]]+)\]\s*$',
        }
    
    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a single CFG file"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Skip empty files
            if not content.strip():
                return {
                    'file': str(file_path),
                    'attributes': {},
                    'common_values': [],
                    'error': 'Empty file'
                }
                
            result = {
                'file': str(file_path),
                'attributes': {},
                'common_values': []
            }
            
            # Try to extract attributes and common values
            try:
                result['attributes'] = self._extract_attributes(content)
            except Exception as e:
                logger.debug(f"Error extracting attributes from {file_path}: {e}")
                result['attributes'] = {}
                
            try:
                result['common_values'] = self._extract_common_values(content)
            except Exception as e:
                logger.debug(f"Error extracting common values from {file_path}: {e}")
                result['common_values'] = []
                
            return result
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return {
                'file': str(file_path), 
                'error': str(e),
                'attributes': {},
                'common_values': []
            }
    
    def _extract_attributes(self, content: str) -> Dict[str, Any]:
        """Extract attributes from all ATTRIBUTES sections"""
        attrs = {}
        try:
            # More flexible pattern to match ATTRIBUTES sections
            attr_matches = list(re.finditer(r'ATTRIBUTES\s*\(\s*(\w+)\s*\)\s*\{([^}]*)\}', content, re.DOTALL))
            
            if not attr_matches:
                # Try alternative pattern
                attr_matches = list(re.finditer(r'ATTRIBUTES\s*\(\s*(\w+)\s*\)\s*\{([^}]*?)\s*\}', content, re.DOTALL))
                
            for match in attr_matches:
                try:
                    section_name = match.group(1).strip()
                    section_content = match.group(2)
                    
                    if section_name not in attrs:
                        attrs[section_name] = {}
                    
                    # Extract value definitions in the section
                    value_matches = list(re.finditer(r'(\w+)\s*=\s*VALUE\s*\(\s*([^,)]+)(?:\s*,\s*"([^"]*)")?\s*\)', section_content))
                    for val_match in value_matches:
                        try:
                            name = val_match.group(1).strip()
                            value_type = val_match.group(2).strip()
                            description = (val_match.group(3) or '').strip()
                            
                            attrs[section_name][name] = {
                                'type': value_type,
                                'description': description
                            }
                        except Exception as e:
                            logger.debug(f"Error processing attribute value: {e}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error processing attribute section: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Error in _extract_attributes: {e}")
            
        return attrs
    
    def _extract_common_values(self, content: str) -> List[Dict[str, str]]:
        """Extract common values like titles, keywords, and parameters"""
        values = []
        current_section = None
        
        # Extract title (from file header)
        if title_match := re.search(self.patterns['title'], content):
            values.append({
                'name': 'TITLE',
                'type': 'string',
                'value': title_match.group(1).strip(),
                'section': 'METADATA'
            })
        
        # Extract keyword (first non-comment, non-whitespace line)
        if keyword_match := re.search(self.patterns['keyword'], content, re.MULTILINE):
            values.append({
                'name': 'KEYWORD',
                'type': 'string',
                'value': keyword_match.group(1).strip(),
                'section': 'METADATA'
            })
        
        # Extract common values from ATTRIBUTES sections
        for attr_section in re.finditer(self.patterns['attr_section'], content, re.DOTALL):
            section_name = attr_section.group(1).strip()
            section_content = attr_section.group(2)
            
            # Extract values like: NAME = VALUE(TYPE, "Description")
            for value_match in re.finditer(r'\s*(\w+)\s*=\s*VALUE\s*\(\s*([^,)]+)(?:\s*,\s*"([^"]*)")?\s*\)', section_content):
                name, value_type, description = value_match.groups()
                values.append({
                    'name': name.strip(),
                    'type': value_type.strip(),
                    'description': (description or '').strip(),
                    'section': f'ATTRIBUTES_{section_name}'
                })
                
            # Extract simple assignments like: NAME = VALUE;
            for assign_match in re.finditer(r'\s*(\w+)\s*=\s*([^;]+);', section_content):
                name, value = assign_match.groups()
                values.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'section': f'ATTRIBUTES_{section_name}'
                })
        
        # Extract SKEYWORDS_IDENTIFIER values
        for skey_section in re.finditer(r'SKEYWORDS_IDENTIFIER\s*\(\w+\)\s*\{([^}]*)\}', content, re.DOTALL):
            section_name = skey_section.group(1).strip()
            section_content = skey_section.group(2)
            
            for assign_match in re.finditer(r'(\w+)\s*=\s*([^;]+);', section_content):
                name, value = assign_match.groups()
                values.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'section': f'SKEYWORDS_{section_name}'
                })
        
        # Extract GUI section values
        for gui_section in re.finditer(r'GUI\s*\(\w+\)\s*\{([^}]*)\}', content, re.DOTALL):
            section_name = gui_section.group(1).strip()
            section_content = gui_section.group(2)
            
            # Extract RADIO buttons
            for radio_match in re.finditer(r'RADIO\s*\((\w+)\)\s*\{([^}]*)\}', section_content, re.DOTALL):
                radio_name = radio_match.group(1)
                radio_content = radio_match.group(2)
                
                options = []
                for option_match in re.finditer(r'ADD\s*\(([^,)]+)(?:\s*,\s*"([^"]*)")?', radio_content):
                    value = option_match.group(1).strip('" ')
                    label = option_match.group(2) or value
                    options.append({
                        'value': value,
                        'label': label.strip('" ')
                    })
                
                values.append({
                    'name': radio_name,
                    'type': 'RADIO',
                    'options': options,
                    'section': f'GUI_{section_name}'
                })
        
        return values

def process_files(root_dir: str, output_file: str) -> None:
    """Process all CFG files in the directory"""
    parser = RadiossCfgParser()
    root_path = Path(root_dir)
    results = {}
    
    # Find and process CFG files
    cfg_files = list(root_path.rglob('*.cfg'))
    total = len(cfg_files)
    
    if not cfg_files:
        logger.error(f"No CFG files found in {root_dir}")
        return
    
    logger.info(f"Found {total} CFG files to process")
    
    for i, cfg_file in enumerate(cfg_files, 1):
        try:
            rel_path = str(cfg_file.relative_to(root_path))
            if i % 100 == 0 or i == total:
                logger.info(f"Processing {i}/{total}: {rel_path}")
            
            result = parser.parse_file(cfg_file)
            results[rel_path] = result
                
        except Exception as e:
            logger.error(f"Error processing {cfg_file}: {e}")
    
    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nProcessing complete. Results saved to {output_file}")
    logger.info(f"Successfully processed {len(results)}/{total} files")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract data from Radioss CFG files'
    )
    parser.add_argument(
        'directory',
        help='Directory containing Radioss CFG files'
    )
    parser.add_argument(
        '-o', '--output',
        default='radioss_cfg_output.json',
        help='Output JSON file (default: radioss_cfg_output.json)'
    )
    
    args = parser.parse_args()
    process_files(args.directory, args.output)

if __name__ == "__main__":
    main()
