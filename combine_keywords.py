import json
from pathlib import Path

def load_json_file(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def combine_keywords(keywords_file, syntax_file, output_file):
    # Load both JSON files
    keywords_data = load_json_file(keywords_file)
    syntax_data = load_json_file(syntax_file)
    
    # Initialize the result structure
    combined_data = {
        "title": "LS-DYNA Keywords with Documentation Links",
        "keywords": []
    }
    
    # Create a mapping of keyword names to their configurations from the syntax file
    syntax_keywords = {}
    if "ls_dyna_syntax" in syntax_data and "examples" in syntax_data["ls_dyna_syntax"]:
        for example_name, example_data in syntax_data["ls_dyna_syntax"]["examples"].items():
            if "keyword" in example_data:
                keyword_name = example_data["keyword"]
                syntax_keywords[keyword_name] = example_data
    
    # Process each keyword from the clean keywords file
    for keyword in keywords_data:
        keyword_name = keyword["name"]
        
        # Find matching syntax configuration
        syntax_config = None
        
        # Try exact match first
        if keyword_name in syntax_keywords:
            syntax_config = syntax_keywords[keyword_name]
        else:
            # Try matching without parameters in parentheses
            base_name = keyword_name.split('(')[0].strip()
            for syn_key, syn_data in syntax_keywords.items():
                if syn_key.startswith(base_name):
                    syntax_config = syn_data
                    break
        
        # Create the combined entry
        combined_entry = {
            "id": keyword.get("id"),
            "name": keyword_name,
            "category": keyword.get("category"),
            "description": keyword.get("description"),
            "documentation": keyword.get("documentation", ""),
            "syntax": syntax_config
        }
        
        combined_data["keywords"].append(combined_entry)
    
    # Save the combined data to a new JSON file
    with open(output_file, 'w') as f:
        json.dump(combined_data, f, indent=2)
    
    return combined_data

if __name__ == "__main__":
    # Define file paths
    base_dir = Path("/home/nemo/Dokumente/Sandbox/Fem_upgraded")
    keywords_file = base_dir / "gui" / "json" / "keywords_clean.json"
    syntax_file = base_dir / "gui" / "json" / "ls_dyna_syntax_user_friendly.json"
    output_file = base_dir / "gui" / "json" / "combined_keywords.json"
    
    # Run the combination
    combined_data = combine_keywords(keywords_file, syntax_file, output_file)
    print(f"Combined {len(combined_data['keywords'])} keywords. Output saved to {output_file}")
