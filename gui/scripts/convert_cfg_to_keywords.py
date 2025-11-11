import json
import os
import re
from pathlib import Path
from collections import OrderedDict

def extract_default_values(cfg_content):
    """Extract default values from CFG content."""
    defaults = {}
    
    for line in cfg_content.split('\n'):
        line = line.strip()
        
        # Skip lines that don't contain DEFAULT
        if 'DEFAULT' not in line:
            continue
            
        # Find the DEFAULT part
        default_start = line.upper().find('DEFAULT(')
        if default_start == -1:
            continue
            
        # Get the part after DEFAULT(
        default_part = line[default_start + 8:].strip()  # +8 for 'DEFAULT('
        
        # Find the closing parenthesis
        paren_count = 1
        end_pos = 0
        for i, char in enumerate(default_part):
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count == 0:
                    end_pos = i
                    break
        
        if end_pos == 0:  # No matching closing parenthesis
            continue
            
        # Extract the content inside DEFAULT(...)
        content = default_part[:end_pos].strip()
        
        # Split into value and description
        if ',' in content:
            value, description = content.split(',', 1)
            value = value.strip(' "\'')
            description = description.strip(' "\'')
        else:
            value = content.strip(' "\'')
            description = ''
            
        # Find the parameter name (last word before DEFAULT)
        before_default = line[:default_start].strip()
        if before_default:
            param_name = before_default.split()[-1]
            defaults[param_name] = {
                'value': value,
                'description': description
            }
    
    return defaults

def extract_optional_attributes(cfg_content):
    """Extract optional attributes and their default values from CFG content."""
    optional_attrs = {}
    
    # Split the content into lines
    for line in cfg_content.split('\n'):
        line = line.strip()
        
        # Skip lines that don't contain the optional marker
        if '//' not in line or '[OPTIONAL]' not in line.upper():
            continue
            
        # Get the part after the optional marker
        opt_part = line[line.upper().find('[OPTIONAL]') + 10:].strip()
        
        # Split into attribute name and default value
        if '=' in opt_part:
            attr_part, value_part = opt_part.split('=', 1)
            attr_name = attr_part.strip()
            
            # Clean up the value (remove any trailing comments)
            value = value_part.split('//')[0].strip()
            
            # Only add if we have a valid attribute name
            if attr_name:
                optional_attrs[attr_name] = value
    
    return optional_attrs

def extract_format_section(cfg_content):
    """
    Extract the FORMAT section from a Radioss CFG file.
    
    Args:
        cfg_content (str): The content of the CFG file
        
    Returns:
        dict: Dictionary containing format information with keys:
              - 'header': The header comment (e.g., "*CONSTRAINED_EXTRA_NODES_SET")
              - 'comments': List of comment lines
              - 'card_format': The format string (e.g., "%10d%10d%10d")
              - 'fields': List of field names (e.g., ['compid', 'entityid', 'iflag'])
    """
    # Pattern to match the FORMAT section
    pattern = r'FORMAT\s*\(([^)]+)\)\s*\{([^}]*)\}'
    match = re.search(pattern, cfg_content, re.DOTALL)
    
    if not match:
        return None
    
    format_info = OrderedDict()
    format_info['header'] = ''
    format_info['comments'] = []
    format_info['card_format'] = ''
    format_info['fields'] = []
    format_info['format_version'] = match.group(1).strip()
    
    format_content = match.group(2).strip()
    lines = [line.strip() for line in format_content.split('\n') if line.strip()]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Extract header (e.g., 'HEADER("*CONSTRAINED_EXTRA_NODES_SET")')
        if line.startswith('HEADER('):
            format_info['header'] = line.split('(', 1)[1].rsplit(')', 1)[0].strip('\"\'')
            
        # Extract comments (e.g., 'COMMENT("$      PID      NSID     IFLAG")')
        elif line.startswith('COMMENT('):
            comment = line.split('(', 1)[1].rsplit(')', 1)[0].strip('\"\'')
            format_info['comments'].append(comment)
            
        # Extract card format (e.g., 'CARD("%10d%10d%10d",compid,entityid,iflag)')
        elif line.startswith('CARD('):
            # Extract format string and fields
            card_parts = line[len('CARD('):-1].split(',', 1)
            format_str = card_parts[0].strip().strip('\"\'')
            format_info['card_format'] = format_str
            
            # Extract field names
            if len(card_parts) > 1:
                fields = [f.strip() for f in card_parts[1].split(',')]
                format_info['fields'] = fields
    
    return format_info



def convert_cfg_to_keywords(input_json, output_json):
    """
    Convert the extracted CFG data to a format compatible with the keyword editor.
    
    Args:
        input_json (str): Path to the input JSON file with extracted CFG data
        output_json (str): Path to save the converted JSON file
    """
    with open(input_json, 'r') as f:
        cfg_data = json.load(f)
    
    keywords = []
    
    for file_path, data in cfg_data.items():
        # Skip files with errors
        if 'error' in data:
            continue
            
        # Get the keyword name from the file path
        keyword_name = Path(file_path).stem.upper()
        
        # Skip internal HM attributes
        if 'HM INTERNAL' in keyword_name or 'HM_INTERNAL' in keyword_name:
            continue
            
        # Skip if no attributes or common values
        if not data.get('attributes') and not data.get('common_values'):
            continue
            
        # Get the original CFG content if available
        cfg_content = data.get('content', '')
        
        # Extract optional attributes and default values
        optional_attrs = extract_optional_attributes(cfg_content)
        default_values = extract_default_values(cfg_content)
        
        
        # Extract FORMAT section if it exists
        format_section = extract_format_section(cfg_content)
        
        # Merge defaults from DEFAULTS section into default_values
        for param, param_data in default_values.items():
            if param not in default_values:  # Don't override existing defaults
                default_values[param] = param_data
        
        keyword = {
            'name': keyword_name,
            'category': 'RADIOSS',
            'description': f"Radioss keyword {keyword_name}",
            'parameters': [],
            'optional_attributes': optional_attrs,
            'format': format_section if format_section else None
        }
        
        # Add attributes as parameters
        for section_name, section in data.get('attributes', {}).items():
            # Skip internal sections
            section_upper = section_name.upper()
            if section_upper in ['HM INTERNAL', 'HM_INTERNAL', 'HM-INTERNAL']:
                continue
                
            for param_name, param_data in section.items():
                param_full_name = f"{section_name}.{param_name}"
                param_type = param_data.get('type', 'STRING').upper()
                
                # Initialize parameter info with basic data
                param_info = {
                    'name': param_full_name,
                    'type': param_type,
                    'description': (param_data.get('description') or '').strip(),
                    'default': '',
                    'required': True,
                    'sources': []
                }
                
                # Check different sources for default values (in order of priority)
                found_default = False
                
                # 1. Check exact match with full parameter name
                if param_full_name in default_values:
                    default_data = default_values[param_full_name]
                    param_info['default'] = default_data.get('value', '')
                    if not param_info['description'] and 'description' in default_data:
                        param_info['description'] = default_data['description']
                    param_info['sources'].append(default_data.get('source', 'DEFAULT'))
                    found_default = True
                
                # 2. Check match with just the parameter name
                elif param_name in default_values:
                    default_data = default_values[param_name]
                    param_info['default'] = default_data.get('value', '')
                    if not param_info['description'] and 'description' in default_data:
                        param_info['description'] = default_data['description']
                    param_info['sources'].append(default_data.get('source', 'DEFAULT'))
                    found_default = True
                
                # 3. Check optional attributes
                elif param_name in optional_attrs:
                    param_info['default'] = optional_attrs[param_name]
                    param_info['required'] = False
                    param_info['sources'].append('OPTIONAL_ATTR')
                
                # Add options if available
                if 'options' in param_data:
                    param_info['options'] = param_data['options']
                
                keyword['parameters'].append(param_info)
        
        # Add common values as parameters
        for common in data.get('common_values', []):
            param_name = common.get('name', '').strip()
            if not param_name or param_name.upper() == 'HM INTERNAL':
                continue
                
            # Find default value from default_values or optional_attrs
            default_val = common.get('value', '')
            if not default_val and param_name in optional_attrs:
                default_val = optional_attrs[param_name]
            
            param_info = {
                'name': param_name,
                'type': common.get('type', 'FLOAT'),
                'description': common.get('description', '').strip(),
                'default': default_val,
                'required': param_name not in optional_attrs
            }
            
            # Add options if available
            if 'options' in common:
                param_info['options'] = common['options']
            
            keyword['parameters'].append(param_info)
        
        if keyword['parameters']:  # Only add if we have parameters
            keywords.append(keyword)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Save the converted data
    with open(output_file, 'w') as f:
        json.dump(keywords, f, indent=2)
    
    print(f"Converted {len(keywords)} keywords to {output_file}")

if __name__ == "__main__":
    input_file = "/home/nemo/Dokumente/Sandbox/Fem_upgraded/gui/json/output_final.json"
    output_file = "/home/nemo/Dokumente/Sandbox/Fem_upgraded/gui/json/radioss_keywords.json"
    
    convert_cfg_to_keywords(input_file, output_file)
