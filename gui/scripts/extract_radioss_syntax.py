#!/usr/bin/env python3
"""
Enhanced Radioss CFG Parser - Extracts common values and attributes from Radioss CFG files
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import logging
from dataclasses import dataclass, field
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cfg_parser_enhanced.log')
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
    source_file: str = ""

class RadiossCfgParser:
    """Parser for Radioss CFG files with enhanced common value extraction"""
    
    def __init__(self):
        self.common_patterns = {
            'title': r'^/\*\s*(.*?)\s*\*/',  # Matches /* title */ at start of file
            'keyword': r'^(\w+)\s*$',  # Matches keyword on its own line
            'parameter': r'#\s*(\d+)\s+([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)\s*([^#]*)',  # Parameter definitions
            'value_definition': r'(\w+)\s*=\s*(VALUE|ARRAY|SCALAR)\s*\(\s*([^,)]+)(?:\s*,\s*"([^"]*)")?\s*\)',
            'attribute_section': r'ATTRIBUTES\s*\(\s*([A-Za-z0-9_]+)\s*\)\s*\{([^}]*)\}',
            'defaults_section': r'DEFAULTS\s*\(\s*([A-Za-z0-9_]+)\s*\)\s*\{([^}]*)\}',
            'format_section': r'FORMAT\s*\(\s*([A-Za-z0-9_]+)\s*\)\s*\{([^}]*)\}',
            'common_attributes': r'ATTRIBUTES\s*\(\s*COMMON\s*\)\s*\{([^}]*)\}',
            'value_assign': r'^\s*(\w+)\s*=\s*([^;]+);',
            'array_item': r'ARRAY\s*\(\s*([^)]+)\s*\)',
            'scalar_value': r'SCALAR\s*\(\s*([^,)]+)(?:\s*,\s*"([^"]*)")?\s*\)',
        }
        
    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a CFG file and extract common values and attributes"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            result = {
                'file': str(file_path),
                'attributes': self._extract_attributes(content),
                'common_values': self._extract_common_values(content),
                'metadata': self._extract_metadata(content)
            }
            return result
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return {
                'file': str(file_path),
                'error': str(e)
            }
    
    def _extract_attributes(self, content: str) -> Dict[str, Any]:
        """Extract all attributes from the content"""
        attrs = {}
        
        # Extract all attribute sections
        for match in re.finditer(self.common_patterns['attribute_section'], content, re.DOTALL):
            attr_type = match.group(1).strip()
            attr_content = match.group(2)
            
            if attr_type not in attrs:
                attrs[attr_type] = {}
            
            # Extract value definitions in the attribute section
            for val_match in re.finditer(self.common_patterns['value_assign'], attr_content, re.MULTILINE):
                name, value = val_match.groups()
                attrs[attr_type][name.strip()] = value.strip(' \t\n\r')
                
        # Extract common attributes specifically
        common_attrs = {}
        common_match = re.search(self.common_patterns['common_attributes'], content, re.DOTALL)
        if common_match:
            common_content = common_match.group(1)
            for val_match in re.finditer(self.common_patterns['value_definition'], common_content):
                name, val_type, value, description = val_match.groups()
                common_attrs[name.strip()] = {
                    'type': val_type.strip(),
                    'value': value.strip() if value else '',
                    'description': (description or '').strip()
                }
        
        if common_attrs:
            attrs['COMMON'] = common_attrs
            
        return attrs
    
    def _extract_common_values(self, content: str) -> Dict[str, Any]:
        """Extract common values and structural elements from the file"""
        result = {
            'titles': [],
            'keywords': [],
            'parameters': [],
            'sections': {}
        }
        
        # Extract title/description
        for title_match in re.finditer(self.common_patterns['title'], content, re.MULTILINE):
            result['titles'].append(title_match.group(1).strip())
        
        # Extract keywords
        for keyword_match in re.finditer(r'^\s*(\w+)\s*$', content, re.MULTILINE):
            keyword = keyword_match.group(1).strip()
            if keyword and keyword not in result['keywords']:
                result['keywords'].append(keyword)
        
        # Extract parameters with their descriptions
        for match in re.finditer(self.common_patterns['parameter'], content):
            param_id, param_name, param_type, param_rest = match.groups()
            param_desc = ''
            
            # Try to extract description after parameter definition
            if desc_match := re.search(
                r'#\s*' + re.escape(param_id) + r'\s+\S+\s+\S+\s+\S+\s*(.*?)(?=\s*#\d|\Z)', 
                content, 
                re.DOTALL
            ):
                param_desc = desc_match.group(1).strip()
            
            result['parameters'].append({
                'id': param_id.strip(),
                'name': param_name.strip(),
                'type': param_type.strip(),
                'description': param_desc,
                'default': param_rest.strip() if param_rest else ''
            })
        
        # Extract sections
        section_patterns = {
            'DEFAULTS': self.common_patterns['defaults_section'],
            'FORMAT': self.common_patterns['format_section'],
            'ATTRIBUTES': self.common_patterns['attribute_section']
        }
        
        for section_type, pattern in section_patterns.items():
            for section_match in re.finditer(pattern, content, re.DOTALL):
                section_name = section_match.group(1).strip()
                section_content = section_match.group(2).strip()
                
                if section_type not in result['sections']:
                    result['sections'][section_type] = {}
                
                section_items = {}
                # Extract key-value pairs in the section
                for item_match in re.finditer(r'^\s*(\w+)\s*=\s*([^;]+);', section_content, re.MULTILINE):
                    key = item_match.group(1).strip()
                    value = item_match.group(2).strip()
                    section_items[key] = value
                
                if section_items:
                    result['sections'][section_type][section_name] = section_items
        
        return result
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract additional metadata from the file"""
        return {
            'has_attributes_section': 'ATTRIBUTES(COMMON)' in content,
            'has_parameters': bool(re.search(r'#\s*\d+\s+\w+\s+\w+', content)),
            'has_functions': bool(re.search(r'\w+\s*=\s*\w+\s*\(', content))
        }

def process_directory(root_dir: str, output_file: str) -> None:
    """
    Process all CFG files in a directory and save results to JSON.
    """
    parser = RadiossCfgParser()
    results = {}
    root_path = Path(root_dir)
    
    # Find all CFG files recursively
    cfg_files = list(root_path.rglob('*.cfg'))
    total_files = len(cfg_files)
    
    if not cfg_files:
        logger.error(f"No CFG files found in {root_dir}")
        return
        
    logger.info(f"Found {total_files} CFG files to process")
    
    for i, cfg_file in enumerate(cfg_files, 1):
        try:
            rel_path = str(cfg_file.relative_to(root_path))
            logger.info(f"[{i}/{total_files}] Processing: {rel_path}")
            
            result = parser.parse_file(cfg_file)
            results[rel_path] = result
                
        except Exception as e:
            logger.error(f"Error processing {cfg_file}: {e}", exc_info=True)
    
    # Save results to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nProcessing complete. Results saved to {output_file}")
    logger.info(f"Successfully processed {len(results)}/{total_files} files")

def analyze_results(input_file: str, output_file: str) -> None:
    """Analyze the extracted data and generate statistics"""
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    stats = {
        'total_files': len(data),
        'files_with_attributes': 0,
        'files_with_parameters': 0,
        'unique_parameter_types': set(),
        'common_attributes': {},
        'parameter_statistics': {}
    }
    
    for file_path, file_data in data.items():
        # Count files with attributes
        if file_data.get('attributes'):
            stats['files_with_attributes'] += 1
        
        # Count files with parameters
        if any('id' in value for value in file_data.get('common_values', [])):
            stats['files_with_parameters'] += 1
        
        # Collect unique parameter types
        for value in file_data.get('common_values', []):
            if 'type' in value:
                stats['unique_parameter_types'].add(value['type'])
        
        # Count common attributes
        for attr_name, attr_data in file_data.get('attributes', {}).items():
            if attr_name not in stats['common_attributes']:
                stats['common_attributes'][attr_name] = {
                    'type': attr_data.get('type'),
                    'description': attr_data.get('description', ''),
                    'count': 0
                }
            stats['common_attributes'][attr_name]['count'] += 1
    
    # Sort common attributes by frequency
    stats['common_attributes'] = dict(sorted(
        stats['common_attributes'].items(),
        key=lambda x: x[1]['count'],
        reverse=True
    ))
    
    # Save analysis
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Analysis complete. Results saved to {output_file}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract common values and attributes from Radioss CFG files'
    )
    parser.add_argument(
        'directory',
        help='Directory containing Radioss CFG files'
    )
    parser.add_argument(
        '-o', '--output',
        default='radioss_cfg_analysis.json',
        help='Output JSON file (default: radioss_cfg_analysis.json)'
    )
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Run analysis on the extracted data'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    if args.analyze:
        analyze_results(args.output, f"analysis_{args.output}")
    else:
        process_directory(args.directory, args.output)

if __name__ == "__main__":
    main()