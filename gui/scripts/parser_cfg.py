#!/usr/bin/env python3
"""
Radioss CFG File Parser

This script parses Radioss CFG files and extracts their structure and parameters.
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from collections import OrderedDict


class CfgParser:
    """Parser for Radioss CFG files."""

    def __init__(self, file_path: Union[str, os.PathLike]):
        """Initialize the parser with a CFG file path.
        
        Args:
            file_path: Path to the CFG file to parse
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        self.keyword_name = self.file_path.stem.upper()
        self.content = self._read_file()        
        self.attributes, self.defaults, self.format_data, self.header = self._parse_sections(self.content)
        
    def _read_file(self) -> List[str]:
        """Read the CFG file content.
        
        Returns:
            List of lines from the file
        """
        try:
            with open(self.file_path, 'r') as f:
                return f.readlines()  # This returns a list of lines
        except Exception as e:
            raise IOError(f"Error reading file {self.file_path}: {str(e)}")
        
    def _parse_sections(self, lines):
        # Initialize all variables at the start
        attributes = {}
        defaults = {}
        format_data = {}
        header = ""
        
        state = None
        current_comment = ""
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Handle comments
            if line.startswith('//'):
                current_comment = line[2:].strip()
                continue
                
            # Check for section headers
            if line.startswith('ATTRIBUTES'):
                state = 'attributes'
                attributes = self._parse_attributes(lines, i + 1)
            elif line.startswith('DEFAULTS'):
                state = 'defaults'
                defaults = self._parse_defaults(lines, i + 1)
            elif line.startswith('FORMAT'):
                state = 'format'
                format_data, header = self._parse_format(lines, i + 1)
            elif line.startswith('SKEYWORDS_IDENTIFIER'):
                state = 'skeywords_identifier'
                # Handle SKEYWORDS_IDENTIFIER if needed
            else:
                # Handle other cases or unknown sections
                pass
                
        return attributes, defaults, format_data, header

    def _parse_attributes(self, lines: List[str], start_idx: int) -> Dict[str, Dict[str, str]]:
        """Parse the ATTRIBUTES section into a dictionary.
        
        Args:
            lines: List of lines from the CFG file
            start_idx: Starting index of the ATTRIBUTES section
            
        Returns:
            Dictionary mapping attribute names to their properties
        """
        attributes = {}
        i = start_idx
        brace_count = 0
        in_attributes = False
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('//'):
                i += 1
                continue
                
            # Count braces to handle nested structures
            if '{' in line:
                if not in_attributes:
                    in_attributes = True
                else:
                    brace_count += line.count('{')
                    
            if '}' in line:
                close_count = line.count('}')
                if brace_count > 0:
                    brace_count -= close_count
                else:
                    # This is the closing brace of ATTRIBUTES section
                    break
                    
            # Only parse attributes when we're inside the ATTRIBUTES section
            if in_attributes and '=' in line and 'VALUE' in line:
                #print("Attribute found:", line)
                # Split into name and value parts
                try:
                    name_part, value_part = [p.strip() for p in line.split('=', 1)]
                    attr_name = name_part.strip()
                    
                    # Extract type and description from VALUE(...)
                    value_match = re.search(r'VALUE\s*\(\s*([^,]+?)\s*,\s*"([^"]*?)"\s*\)', value_part)
                    if value_match:
                        attr_type = value_match.group(1).strip()
                        attr_desc = value_match.group(2).strip()
                        
                        attributes[attr_name] = {
                            'type': attr_type,
                            'description': attr_desc
                        }
                except ValueError:
                    # Skip malformed lines
                    pass
                    
            i += 1
            
        return attributes

    def _parse_defaults(self, lines: List[str], start_idx: int) -> Dict[str, Any]:
        """Parse the DEFAULTS section into a dictionary.
        
        Args:
            lines: List of lines from the CFG file
            start_idx: Starting index of the DEFAULTS section
            
        Returns:
            Dictionary mapping parameter names to their default values
        """
        defaults = {}
        i = start_idx
        brace_count = 0
        in_defaults = False
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('//'):
                i += 1
                continue
                
            # Count braces to handle nested structures
            if '{' in line:
                if not in_defaults:
                    in_defaults = True
                else:
                    brace_count += line.count('{')
                    
            if '}' in line:
                close_count = line.count('}')
                if brace_count > 0:
                    brace_count -= close_count
                else:
                    # This is the closing brace of DEFAULTS section
                    break
                    
            # Only parse defaults when we're inside the DEFAULTS section
            if in_defaults and '=' in line and not line.startswith(('//', '{', '}')):
                #print(line)
                try:
                    # Split into name and value parts
                    name_part, value_part = [p.strip() for p in line.split('=', 1)]
                    param_name = name_part.strip()
                    value_str = value_part.rstrip(';').strip()
                    
                    # Try to convert to appropriate type
                    if value_str.isdigit():
                        value = int(value_str)
                    elif value_str.replace('.', '', 1).isdigit():
                        value = float(value_str)
                    else:
                        value = value_str.strip('"\'')  # Remove quotes from strings
                        
                    defaults[param_name] = value
                    
                except (ValueError, IndexError):
                    # Skip malformed lines
                    pass
                    
            i += 1
            
        return defaults
        
    def _parse_format(self, lines: List[str], start_idx: int) -> tuple[Dict[str, Any], str]:
        """Parse the FORMAT section into a structured dictionary."""
        format_data = {
            'header': "",           # For HEADER line
            'format_type': None,    # e.g., "Keyword971"
            'cards': [],            # List of card dictionaries
            'comments': [],         # List of comment lines
            'assignments': [],      # List of ASSIGN statements
            'subobjects': []        # List of SUBOBJECTS
        }
        
        i = start_idx
        brace_count = 0
        current_comment = ""
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
                
            # Handle HEADER
            if line.startswith('HEADER(') and line.endswith(');'):
                format_data['header'] = line[7:-2].strip('"\'')
                
            # Handle COMMENTS
            elif line.startswith('//'):
                current_comment = line[2:].strip()
                
            # Handle CARD
            elif line.startswith('CARD('):
                try:
                    # Extract format string and parameters
                    card_parts = line[len('CARD('):].rsplit(')', 1)
                    format_str = card_parts[0].strip('"\'')
                    params = [p.strip() for p in card_parts[1].split(',')] if len(card_parts) > 1 else []
                    
                    format_data['cards'].append({
                        'format': format_str,
                        'parameters': params,
                        'comment': current_comment
                    })
                    current_comment = ""  # Reset comment after using it
                    
                except (IndexError, ValueError) as e:
                    print(f"Error parsing CARD: {e}")
                    
            # Handle ASSIGN
            elif line.startswith('ASSIGN('):
                try:
                    parts = line[len('ASSIGN('):].rsplit(')', 1)[0].split(',')
                    format_data['assignments'].append({
                        'variable': parts[0].strip(),
                        'value': parts[1].strip(),
                        'mode': parts[2].strip() if len(parts) > 2 else None
                    })
                except (IndexError, ValueError) as e:
                    print(f"Error parsing ASSIGN: {e}")
                    
            # Handle format type (e.g., "FORMAT(Keyword971)")
            elif line.startswith('FORMAT(') and ')' in line:
                format_data['format_type'] = line.split('(')[1].split(')')[0].strip()
                
            # Count braces to find end of FORMAT section
            if '{' in line:
                brace_count += line.count('{')
            if '}' in line:
                brace_count -= line.count('}')
                if brace_count <= 0:
                    break
                    
            i += 1
            
        return format_data, format_data['header']

    def to_dict(self) -> Dict[str, Any]:
        """Convert the parsed data to a dictionary that can be serialized to JSON."""
        result = {}
        
        # Add ATTRIBUTES if it exists
        if hasattr(self, 'attributes') and hasattr(self.attributes, 'items'):
            result['ATTRIBUTES'] = dict(self.attributes)
        
        # Add DEFAULTS if it exists
        if hasattr(self, 'defaults') and hasattr(self.defaults, 'items'):
            result['DEFAULTS'] = dict(self.defaults)
        
        # Add FORMAT data if it exists
        if hasattr(self, 'format_data') and isinstance(self.format_data, dict):
            format_data = {
                'format_type': self.format_data.get('format_type'),
                'cards': [
                    {
                        'format': card.get('format', ''),
                        'parameters': card.get('parameters', []),
                        'comment': card.get('comment', ''),
                        'header': card.get('header', '')
                    }
                    for card in self.format_data.get('cards', [])
                ],
                'subobjects': self.format_data.get('subobjects', []),
                'assignments': self.format_data.get('assignments', [])
            }
            result['FORMAT'] = format_data
    
        return result

    def to_json(self, indent: int = 2) -> str:
        """Convert the parsed data to a JSON string.
        
        Args:
            indent: Number of spaces to use for indentation (None for compact output)
            
        Returns:
            JSON string representation of the parsed data
        """
        import json
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
        
def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Parse Radioss CFG files')
    parser.add_argument('file', help='Path to the CFG file to parse')
    parser.add_argument('-o', '--output', help='Output file path (default: stdout)')
    parser.add_argument('--indent', type=int, default=2, help='Number of spaces for JSON indentation')
    
    args = parser.parse_args()
    
    try:
        cfg_parser = CfgParser(args.file)
        json_output = cfg_parser.to_json(indent=args.indent)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"Output written to {args.output}")
        else:
            print(json_output)
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    import sys
    main()