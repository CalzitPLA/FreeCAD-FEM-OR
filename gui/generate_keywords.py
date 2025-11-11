#!/usr/bin/env python3
"""
Script to generate the openradioss_keywords_with_parameters.json file
by combining data from the keyword database and whitelist.
"""

import os
import json
import logging
import re
import sys
from typing import Dict, List, Any, Set, Optional
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class KeywordGenerator:
    def __init__(self, base_dir: str):
        """Initialize the keyword generator with base directory."""
        self.base_dir = Path(base_dir)
        self.db_path = self.base_dir / "json" / "keyword_database_results.json"
        self.whitelist_path = self.base_dir / "json" / "keywords_clean.json"
        self.output_path = self.base_dir / "openradioss_keywords_with_parameters.json"
        
    def normalize_name(self, name: str) -> str:
        """Normalize a keyword name for comparison.
        
        Handles various formats:
        - Removes leading asterisks
        - Removes text in parentheses and extra whitespace
        - Converts to uppercase
        - Handles both whitelist entries and database entries consistently
        """
        if not name or not isinstance(name, str):
            return ''
            
        # Remove text in parentheses and extra whitespace
        clean = re.sub(r'\s*\([^)]*\)', '', name).strip()
        
        # Convert to uppercase and remove leading asterisks
        clean = clean.upper().lstrip('*')
        
        # Remove any remaining comments or extra whitespace
        clean = clean.split('#')[0].strip()
        
        return clean
    
    def get_name_variations(self, name: str) -> Set[str]:
        """Generate all possible variations of a keyword name."""
        if not name:
            return set()
            
        name = name.strip()
        variations = set()
        
        # Add original name
        variations.add(name)
        
        # Add uppercase version
        upper_name = name.upper()
        variations.add(upper_name)
        
        # Handle leading asterisks
        if name.startswith('*'):
            # Add without leading *
            no_star = name[1:].strip()
            variations.add(no_star)
            variations.add(no_star.upper())
            
            # Add with space after * if not present
            if not name.startswith('* '):
                variations.add('* ' + no_star)
        else:
            # Add with leading *
            with_star = '*' + name
            variations.add(with_star)
            variations.add(with_star.upper())
            
            # Add with space after *
            with_star_space = '* ' + name
            variations.add(with_star_space)
            variations.add(with_star_space.upper())
            
        # Add common variations for material and section definitions
        if name.startswith(('MAT_', 'SECTION_')):
            # For material/section cards, also match without the prefix
            parts = name.split('_', 1)
            if len(parts) > 1:
                variations.add(parts[1])  # Just the number part
                variations.add(parts[1].upper())
            
        return variations
    
    def load_keyword_database(self) -> Dict[str, Any]:
        """Load the keyword database from JSON file."""
        logger.info(f"Loading keyword database from: {self.db_path}")
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict) or 'successful' not in data:
                logger.error("Invalid database format: 'successful' key not found")
                return {}
                
            logger.info(f"Loaded {len(data['successful'])} keywords from database")
            return data
            
        except Exception as e:
            logger.error(f"Error loading keyword database: {e}")
            return {}
    
    def load_whitelist(self) -> List[Dict[str, Any]]:
        """Load the whitelist from JSON file."""
        logger.info(f"Loading whitelist from: {self.whitelist_path}")
        try:
            with open(self.whitelist_path, 'r', encoding='utf-8') as f:
                whitelist = json.load(f)
                
            if not isinstance(whitelist, list):
                logger.error("Whitelist should be a list of keyword entries")
                return []
                
            logger.info(f"Loaded {len(whitelist)} whitelist entries")
            return whitelist
            
        except Exception as e:
            logger.error(f"Error loading whitelist: {e}")
            return []
    
    def extract_parameters(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract parameters from a keyword's data field with enhanced attribute handling.
        
        This method processes various data structures to extract parameters, including:
        - Direct parameters in 'parameters' key
        - Field definitions in 'field_' prefixed keys
        - ATTRIBUTES section for parameter metadata
        - FORMAT section for parameter formatting
        - DEFAULTS section for default values
        """
        if not data or not isinstance(data, dict):
            return []
            
        parameters = []
        param_map = {}
        defaults = data.get('DEFAULTS', {})
        attributes = data.get('ATTRIBUTES', {})
        format_info = data.get('FORMAT', {})
        
        # First, extract parameters from ATTRIBUTES section
        if attributes and isinstance(attributes, dict):
            for attr_name, attr_data in attributes.items():
                # Skip internal or non-parameter attributes
                if attr_name in ['KEYWORD_STR', 'CommentEnumField', 'EncTypeEnumField', 'LSD_TitleOpt', 'RegTypeEnumField']:
                    continue
                    
                param = {
                    'name': attr_name,
                    'description': attr_data.get('description', '').strip(),
                    'type': attr_data.get('type', 'text').lower(),
                    'default': defaults.get(attr_name, '')
                }
                
                # Map parameter name to its index for later reference
                param_map[attr_name] = len(parameters)
                parameters.append(param)
        
        # Process FORMAT section to get parameter order and formatting
        if format_info and isinstance(format_info, dict):
            cards = format_info.get('cards', [])
            if cards and isinstance(cards, list):
                for card in cards:
                    if not isinstance(card, dict):
                        continue
                        
                    # Extract format string to understand parameter order
                    fmt_str = card.get('format', '')
                    if not fmt_str:
                        continue
                        
                    # Simple parsing of format string to extract parameter names
                    # This is a basic implementation and might need refinement
                    # based on the actual format string patterns
                    param_refs = []
                    for part in fmt_str.split(','):
                        part = part.strip()
                        if not part:
                            continue
                            
                        # Look for parameter references in the format string
                        # This is a simplified approach and might need adjustment
                        if part in param_map:
                            param_refs.append(part)
                    
                    # Update parameter order based on format string
                    if param_refs:
                        # Reorder parameters based on format string
                        ordered_params = []
                        for ref in param_refs:
                            if ref in param_map:
                                idx = param_map[ref]
                                if 0 <= idx < len(parameters):
                                    ordered_params.append(parameters[idx])
                        
                        # If we found ordered parameters, use them
                        if ordered_params:
                            # Add any parameters that weren't in the format string but are in the attributes
                            remaining_params = [p for p in parameters if p['name'] not in param_refs]
                            parameters = ordered_params + remaining_params
        
        # Process direct parameters if no attributes were found
        if not parameters:
            if 'parameters' in data:
                # If parameters are already in the expected format, use them directly
                if isinstance(data['parameters'], list):
                    return data['parameters']
                # Otherwise, try to convert from the database format
                elif isinstance(data['parameters'], dict):
                    return [{'name': k, **v} for k, v in data['parameters'].items()]
            
            # Try to extract parameters from field_* keys
            for key, value in data.items():
                if key.startswith('field_') and isinstance(value, dict):
                    param = {
                        'name': key.replace('field_', ''),
                        'description': value.get('description', '').strip(),
                        'type': value.get('type', 'text').lower(),
                        'default': value.get('default', '')
                    }
                    parameters.append(param)
        
        # Ensure all parameters have required fields
        for param in parameters:
            param.setdefault('description', '')
            param.setdefault('type', 'text')
            param.setdefault('default', '')
            
            # Convert type to a standard format
            if isinstance(param['type'], str):
                param['type'] = param['type'].lower()
                if 'int' in param['type']:
                    param['type'] = 'int'
                elif 'float' in param['type'] or 'double' in param['type']:
                    param['type'] = 'float'
                elif 'bool' in param['type']:
                    param['type'] = 'bool'
                else:
                    param['type'] = 'text'
            else:
                param['type'] = 'text'
        
        return parameters
    
    def generate_keywords(self) -> List[Dict[str, Any]]:
        """Generate the final list of keywords by combining database and whitelist."""
        # Load data
        db_data = self.load_keyword_database()
        if not db_data:
            logger.error("No database data loaded")
            return []
            
        whitelist = self.load_whitelist()
        if not whitelist:
            logger.warning("No whitelist entries found, using all keywords")
        
        # Create a mapping of normalized names to database entries
        db_keywords = {}
        for kw in db_data.get('successful', []):
            if not isinstance(kw, dict):
                continue
                
            # Get the keyword name
            kw_name = kw.get('keyword', '')
            if not kw_name:
                continue
                
            # Normalize the name
            clean_name = self.normalize_name(kw_name)
            if not clean_name:
                continue
                
            # Skip DEFAULTS section
            if clean_name == 'DEFAULTS':
                continue
                
            # Store the first occurrence of this keyword
            if clean_name not in db_keywords:
                db_keywords[clean_name] = kw
        
        logger.info(f"Found {len(db_keywords)} unique keywords in database")
        
        # Process whitelist
        whitelist_map = {}
        whitelist_variations = {}
        
        for entry in whitelist:
            name = entry.get('name')
            if not name:
                continue
                
            clean_name = self.normalize_name(name)
            if clean_name:
                whitelist_map[clean_name] = entry
                
                # Generate all variations for this whitelist entry
                variations = self.get_name_variations(clean_name)
                for var in variations:
                    if var not in whitelist_variations:
                        whitelist_variations[var] = []
                    whitelist_variations[var].append(clean_name)
        
        logger.info(f"Processing {len(whitelist_map)} whitelist entries with {len(whitelist_variations)} variations")
        
        # Generate the final list of keywords
        result = []
        matched_whitelist = set()
        used_db_keywords = set()
        
        # First pass: process whitelist entries with exact or variation matches
        for clean_name, whitelist_entry in whitelist_map.items():
            # Try exact match first
            if clean_name in db_keywords:
                db_entry = db_keywords[clean_name]
                used_db_keywords.add(clean_name)
                
                # Create the merged keyword
                keyword = {
                    'name': whitelist_entry.get('name', clean_name),
                    'category': whitelist_entry.get('category', 'General'),
                    'description': whitelist_entry.get('description', ''),
                    'documentation': whitelist_entry.get('documentation', ''),
                    'file': db_entry.get('file', ''),
                    'data': db_entry.get('data', {})
                }
                
                # Extract parameters
                keyword['parameters'] = self.extract_parameters(db_entry.get('data', {}))
                
                result.append(keyword)
                matched_whitelist.add(clean_name)
                
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Added whitelist keyword (exact match): {keyword['name']} with {len(keyword['parameters'])} parameters")
            else:
                # Try to find a matching database entry using variations
                variations = self.get_name_variations(clean_name)
                matched = False
                
                for var in variations:
                    if var in db_keywords and var not in used_db_keywords:
                        db_entry = db_keywords[var]
                        used_db_keywords.add(var)
                        
                        # Create the merged keyword
                        keyword = {
                            'name': whitelist_entry.get('name', clean_name),
                            'category': whitelist_entry.get('category', 'General'),
                            'description': whitelist_entry.get('description', ''),
                            'documentation': whitelist_entry.get('documentation', ''),
                            'file': db_entry.get('file', ''),
                            'data': db_entry.get('data', {})
                        }
                        
                        # Extract parameters
                        keyword['parameters'] = self.extract_parameters(db_entry.get('data', {}))
                        
                        result.append(keyword)
                        matched_whitelist.add(clean_name)
                        matched = True
                        
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"Added whitelist keyword (variation match): {keyword['name']} as {var} with {len(keyword['parameters'])} parameters")
                        break
                
                if not matched:
                    logger.warning(f"No match found for whitelist entry: {whitelist_entry.get('name', clean_name)}")
        
        # Second pass: include any database entries that match common patterns
        for clean_name, db_entry in db_keywords.items():
            if clean_name in used_db_keywords:
                continue
                
            # Always include standard keywords
            standard_keywords = {
                'NODE', 'ELEMENT', 'PART', 'MATERIAL', 'SECTION', 'CONTACT',
                'CONTROL', 'DATABASE', 'DEFINE', 'INITIAL', 'BOUNDARY',
                'CONSTRAINED', 'LOAD', 'SET', 'INCLUDE', 'KEYWORD', 'END',
                'PARAM', 'PARAMETER', 'PARAMETERS', 'TITLE', 'TERMINATION',
                'OUTPUT', 'RESTART', 'TIME', 'STEP', 'ANALYSIS', 'SOLUTION'
            }
            
            # Common prefixes for important keyword types
            prefixes = (
                'MAT_', 'MATERIAL_', 'SECTION_', 'SEC_', 'CONTACT_', 'CONT_', 
                'CONTROL_', 'CTRL_', 'DATABASE_', 'DB_', 'ELEMENT_', 'ELEM_', 
                'EL_', 'SET_', 'NSET_', 'ESET_', 'PSET_', 'SSET_', 'DEFINE_', 
                'DEF_', 'INITIAL_', 'INIT_', 'BOUNDARY_', 'BOUND_', 'LOAD_',
                'CONSTRAINED_', 'CONST_', 'PART_', 'NODE_', 'NODAL_', 'PLOT_',
                'PLOTTING_', 'PRINT_', 'OUTPUT_', 'TIME_', 'STEP_', 'ANALYSIS_',
                'SOLUTION_', 'SOLVE_', 'SOLVER_', 'PROPERTY_', 'PROP_', 'PROFILE_',
                'PROF_', 'MATRIX_', 'MAT_', 'MASS_', 'DAMPING_', 'STIFFNESS_',
                'STIFF_', 'RIGID_', 'RIGIDWALL_', 'SURFACE_', 'SURF_', 'INTERFACE_',
                'INTER_', 'JOINT_', 'COUPLING_', 'COUP_', 'LINK_', 'BEAM_',
                'SHELL_', 'SOLID_', 'TSHELL_', 'BEAM_', 'TRUSS_', 'SPRING_',
                'DAMPER_', 'MASS_', 'GAP_', 'DASHPOT_', 'JOINT_', 'JNT_',
                'CONSTRAINT_', 'CONST_', 'RBE_', 'RBE2_', 'RBE3_', 'RB2_', 'RB3_',
                'RIGID_', 'RGD_', 'RGD2_', 'RGD3_', 'RGD4_', 'RGD5_', 'RGD6_',
                'RGD7_', 'RGD8_', 'RGD9_', 'RGD10_', 'RGD11_', 'RGD12_', 'RGD13_',
                'RGD14_', 'RGD15_', 'RGD16_', 'RGD17_', 'RGD18_', 'RGD19_', 'RGD20_',
                'RGD21_', 'RGD22_', 'RGD23_', 'RGD24_', 'RGD25_', 'RGD26_', 'RGD27_',
                'RGD28_', 'RGD29_', 'RGD30_', 'RGD31_', 'RGD32_', 'RGD33_', 'RGD34_',
                'RGD35_', 'RGD36_', 'RGD37_', 'RGD38_', 'RGD39_', 'RGD40_', 'RGD41_',
                'RGD42_', 'RGD43_', 'RGD44_', 'RGD45_', 'RGD46_', 'RGD47_', 'RGD48_',
                'RGD49_', 'RGD50_', 'RGD51_', 'RGD52_', 'RGD53_', 'RGD54_', 'RGD55_',
                'RGD56_', 'RGD57_', 'RGD58_', 'RGD59_', 'RGD60_', 'RGD61_', 'RGD62_',
                'RGD63_', 'RGD64_', 'RGD65_', 'RGD66_', 'RGD67_', 'RGD68_', 'RGD69_',
                'RGD70_', 'RGD71_', 'RGD72_', 'RGD73_', 'RGD74_', 'RGD75_', 'RGD76_',
                'RGD77_', 'RGD78_', 'RGD79_', 'RGD80_', 'RGD81_', 'RGD82_', 'RGD83_',
                'RGD84_', 'RGD85_', 'RGD86_', 'RGD87_', 'RGD88_', 'RGD89_', 'RGD90_',
                'RGD91_', 'RGD92_', 'RGD93_', 'RGD94_', 'RGD95_', 'RGD96_', 'RGD97_',
                'RGD98_', 'RGD99_', 'RGD100_'
            )
            
            # Common suffixes for important keyword types
            suffixes = (
                '_MATERIAL', '_MAT', '_PROPERTY', '_PROP', '_SECTION', '_SEC',
                '_CONTACT', '_CONT', '_ELEMENT', '_ELEM', '_EL', '_SET', '_LOAD',
                '_BOUNDARY', '_BOUND', '_CONSTRAINT', '_CONST', '_INITIAL', '_INIT',
                '_DATABASE', '_DB', '_CONTROL', '_CTRL', '_OUTPUT', '_PRINT',
                '_PLOT', '_TIME', '_STEP', '_ANALYSIS', '_SOLUTION', '_SOLVE',
                '_SOLVER', '_MATRIX', '_MASS', '_DAMPING', '_STIFFNESS', '_STIFF',
                '_RIGID', '_RIGIDWALL', '_SURFACE', '_SURF', '_INTERFACE', '_INTER',
                '_JOINT', '_COUPLING', '_COUP', '_LINK', '_BEAM', '_SHELL',
                '_SOLID', '_TSHELL', '_TRUSS', '_SPRING', '_DAMPER', '_MASS',
                '_GAP', '_DASHPOT', '_JNT', '_RBE', '_RBE2', '_RBE3', '_RB2',
                '_RB3', '_RGD', '_RGD2', '_RGD3', '_RGD4', '_RGD5', '_RGD6',
                '_RGD7', '_RGD8', '_RGD9', '_RGD10', '_RGD11', '_RGD12', '_RGD13',
                '_RGD14', '_RGD15', '_RGD16', '_RGD17', '_RGD18', '_RGD19', '_RGD20',
                '_RGD21', '_RGD22', '_RGD23', '_RGD24', '_RGD25', '_RGD26', '_RGD27',
                '_RGD28', '_RGD29', '_RGD30', '_RGD31', '_RGD32', '_RGD33', '_RGD34',
                '_RGD35', '_RGD36', '_RGD37', '_RGD38', '_RGD39', '_RGD40', '_RGD41',
                '_RGD42', '_RGD43', '_RGD44', '_RGD45', '_RGD46', '_RGD47', '_RGD48',
                '_RGD49', '_RGD50', '_RGD51', '_RGD52', '_RGD53', '_RGD54', '_RGD55',
                '_RGD56', '_RGD57', '_RGD58', '_RGD59', '_RGD60', '_RGD61', '_RGD62',
                '_RGD63', '_RGD64', '_RGD65', '_RGD66', '_RGD67', '_RGD68', '_RGD69',
                '_RGD70', '_RGD71', '_RGD72', '_RGD73', '_RGD74', '_RGD75', '_RGD76',
                '_RGD77', '_RGD78', '_RGD79', '_RGD80', '_RGD81', '_RGD82', '_RGD83',
                '_RGD84', '_RGD85', '_RGD86', '_RGD87', '_RGD88', '_RGD89', '_RGD90',
                '_RGD91', '_RGD92', '_RGD93', '_RGD94', '_RGD95', '_RGD96', '_RGD97',
                '_RGD98', '_RGD99', '_RGD100'
            )
            
            # Check if this keyword should be included
            include = False
            
            # Check standard keywords
            if clean_name in standard_keywords:
                include = True
            # Check prefixes
            elif any(clean_name.startswith(prefix) for prefix in prefixes):
                include = True
            # Check suffixes
            elif any(clean_name.endswith(suffix) for suffix in suffixes):
                include = True
            # Check for numeric suffixes (e.g., MAT1, MAT2, etc.)
            elif any(clean_name.startswith(prefix) and clean_name[len(prefix):].isdigit() 
                   for prefix in ['MAT', 'MATERIAL', 'SEC', 'SECTION', 'CONTACT', 'CONT', 
                                 'ELEMENT', 'ELEM', 'EL', 'SET', 'LOAD', 'BOUNDARY', 'BOUND',
                                 'CONSTRAINT', 'CONST', 'INITIAL', 'INIT', 'DATABASE', 'DB',
                                 'CONTROL', 'CTRL', 'OUTPUT', 'PRINT', 'PLOT', 'TIME', 'STEP',
                                 'ANALYSIS', 'SOLUTION', 'SOLVE', 'SOLVER', 'PROPERTY', 'PROP',
                                 'PROFILE', 'PROF', 'MATRIX', 'MAT', 'MASS', 'DAMPING',
                                 'STIFFNESS', 'STIFF', 'RIGID', 'RIGIDWALL', 'SURFACE', 'SURF',
                                 'INTERFACE', 'INTER', 'JOINT', 'COUPLING', 'COUP', 'LINK',
                                 'BEAM', 'SHELL', 'SOLID', 'TSHELL', 'TRUSS', 'SPRING',
                                 'DAMPER', 'GAP', 'DASHPOT', 'JNT', 'RBE', 'RBE2', 'RBE3',
                                 'RB2', 'RB3', 'RGD', 'RGD2', 'RGD3', 'RGD4', 'RGD5', 'RGD6',
                                 'RGD7', 'RGD8', 'RGD9']):
                include = True
            
            if include:
                # Try to find a matching whitelist entry by name
                category = 'General'
                description = ''
                documentation = ''
                
                # Check if we have a similar whitelist entry
                for wl_name, wl_entry in whitelist_map.items():
                    if (wl_name in clean_name or clean_name in wl_name or
                        any(var in clean_name for var in self.get_name_variations(wl_name))):
                        category = wl_entry.get('category', 'General')
                        description = wl_entry.get('description', '')
                        documentation = wl_entry.get('documentation', '')
                        break
                
                keyword = {
                    'name': clean_name,
                    'category': category,
                    'description': description,
                    'documentation': documentation,
                    'file': db_entry.get('file', ''),
                    'data': db_entry.get('data', {})
                }
                
                # Extract parameters
                keyword['parameters'] = self.extract_parameters(db_entry.get('data', {}))
                
                result.append(keyword)
                used_db_keywords.add(clean_name)
                
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Added database keyword: {clean_name} with {len(keyword['parameters'])} parameters")
        
        logger.info(f"Generated {len(result)} keywords in total")
        return result
    
    def save_keywords(self, keywords: List[Dict[str, Any]]) -> bool:
        """Save the generated keywords to the output file."""
        try:
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(keywords, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved {len(keywords)} keywords to {self.output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving keywords: {e}")
            return False

def main():
    """Main function to run the keyword generator."""
    # Get the directory of the current script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create the generator
    generator = KeywordGenerator(base_dir)
    
    # Generate the keywords
    keywords = generator.generate_keywords()
    
    # Save the results
    if keywords:
        generator.save_keywords(keywords)
        logger.info("Keyword generation completed successfully")
    else:
        logger.error("No keywords were generated")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
