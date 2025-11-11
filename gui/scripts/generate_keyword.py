import json
from typing import Dict, Any, Union

def load_json_data(json_file: str) -> Dict[str, Any]:
    """Load and parse the JSON file containing the CFG data."""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_value(var_name: str, defaults: Dict[str, Any], attributes: Dict[str, Any]) -> str:
    """Get the value of a variable, checking both defaults and attributes."""
    # First try to get from defaults
    if var_name in defaults:
        return str(defaults[var_name])
    
    # Then try to get from attributes
    if var_name in attributes:
        attr = attributes[var_name]
        if 'default' in attr:
            return str(attr['default'])
    
    # Return empty string if not found
    return "0"  # or whatever default value makes sense for your case

def format_card_line(card_format: str, defaults: Dict[str, Any], attributes: Dict[str, Any], card_comment: str = "") -> tuple[str, str]:
    """Format a single card line with actual values using comma separation.
    Returns a tuple of (comment_line, data_line) where comment_line contains variable names.
    """
    # Extract the format string and variable names
    format_parts = card_format.split(',', 1)
    if len(format_parts) < 2:
        return "", ""
    
    format_str = format_parts[0].strip().strip('"')
    var_names = [v.strip() for v in format_parts[1].split(',')]
    
    # Get values and build comment line
    values = []
    comment_parts = []
    for var in var_names:
        # Clean up variable name for comment
        clean_var = var.split('(')[0]  # Remove function calls
        comment_parts.append(clean_var)
        
        # Get the value
        if '(' in var and ')' in var:
            # Handle function calls by extracting the first parameter
            func_var = var.split('(')[1].split(',')[0].strip()
            value = get_value(func_var, defaults, attributes)
        else:
            value = get_value(var, defaults, attributes)
        values.append(str(value))
    
    # Create comment line with variable names
    comment_line = f"$ {', '.join(comment_parts)}"
    if card_comment:
        comment_line = f"$ {card_comment}\n" + comment_line
    
    # Create data line with values
    data_line = ','.join(values)
    
    return comment_line, data_line

def generate_keyword(data: Dict[str, Any]) -> str:
    """Generate the complete keyword from the parsed data with comments."""
    output = ["*KEYWORD"]
    
    # Add the main header if it exists
    format_data = data.get('FORMAT', {})
    if format_data.get('header'):
        output.append(f"$ {format_data['header']}")
    
    defaults = data.get('DEFAULTS', {})
    attributes = data.get('ATTRIBUTES', {})
    
    # Process cards
    for card in format_data.get('cards', []):
        if not card['format'].strip():
            continue
            
        try:
            comment_line, data_line = format_card_line(
                card['format'], 
                defaults, 
                attributes,
                card.get('comment', '')
            )
            if data_line:
                output.append(comment_line)
                output.append(data_line)
        except Exception as e:
            print(f"Error formatting card: {e}")
            continue
    
    # Add footer
    output.append("*END")
    return '\n'.join(output)

def main():
    import sys
    import os
    
    if len(sys.argv) != 2:
        print("Usage: python generate_keyword.py <input_json>")
        sys.exit(1)
    
    input_json = sys.argv[1]
    
    try:
        # Load the JSON data
        data = load_json_data(input_json)
        
        # Generate the keyword
        keyword = generate_keyword(data)
        
        # Write to output file
        output_file = os.path.splitext(input_json)[0] + '.key'
        with open(output_file, 'w') as f:
            f.write(keyword)
            
        print(f"Successfully generated keyword file: {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()