"""
Keyword loading and filtering utilities for OpenRadioss Keyword Editor.

This module handles loading keywords from JSON files, filtering them based on whitelists,
and merging data from different sources.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KeywordUtils:
    """Utility class for handling keyword loading and filtering operations."""
    
    @staticmethod
    def load_keyword_database(db_path: str) -> List[Dict[str, Any]]:
        """
        Load the full keyword database from a JSON file.
        
        Args:
            db_path: Path to the keyword database JSON file
            
        Returns:
            List of keyword dictionaries
        """
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load keyword database from {db_path}: {str(e)}")
            return []
    
    @staticmethod
    def load_whitelist(whitelist_path: str) -> List[Dict[str, Any]]:
        """
        Load the whitelist of keywords to include.
        
        Args:
            whitelist_path: Path to the whitelist JSON file
            
        Returns:
            List of whitelisted keyword dictionaries
        """
        try:
            with open(whitelist_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load whitelist from {whitelist_path}: {str(e)}")
            return []
    
    @classmethod
    def filter_keywords_by_whitelist(
        cls,
        base_keywords: List[Dict[str, Any]],
        whitelist: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter keywords based on a whitelist with enhanced matching.
        
        Handles various naming conventions including:
        - Case insensitivity
        - Leading/trailing whitespace
        - Optional leading asterisks
        - Newline handling in keyword names
        - Partial matches for material and section definitions
        
        Args:
            base_keywords: List of all available keywords
            whitelist: List of whitelisted keyword names with metadata
            
        Returns:
            Filtered list of keywords with merged metadata
        """
        def normalize_name(name: str) -> str:
            """Normalize a keyword name for comparison."""
            if not name or not isinstance(name, str):
                return ''
            # Remove comments and extra whitespace, take first line, convert to uppercase
            return name.split('#')[0].split('\n')[0].strip().upper()
            
        def get_name_variations(name: str) -> set:
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

        try:
            # Track all variations of whitelist names for matching
            whitelist_variations = {}
            whitelist_original_names = {}
            
            # Track which whitelist entries have been matched
            matched_whitelist = set()
            filtered_keywords = []
            
            logger.info(f"Processing {len(whitelist)} whitelist entries...")
            
            # First, process the whitelist to build our matching patterns
            for w in whitelist:
                if 'name' not in w or not w['name']:
                    logger.debug(f"Skipping empty whitelist entry: {w}")
                    continue
                    
                name = w['name']
                clean_name = normalize_name(name)
                
                # Store the original name for this clean name
                whitelist_original_names[clean_name] = w
                
                # Generate all possible variations for matching
                variations = get_name_variations(clean_name)
                
                # Store the relationship between variations and the clean name
                for var in variations:
                    if var not in whitelist_variations:
                        whitelist_variations[var] = []
                    whitelist_variations[var].append(clean_name)
                
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Whitelist entry: {name} -> {clean_name} (variations: {', '.join(variations)})")
            
            # Define special handling for different keyword types
            keyword_categories = {
                'material': ['MAT_', 'MATERIAL_'],
                'section': ['SECTION_', 'SEC_'],
                'contact': ['CONTACT_', 'CONT_'],
                'control': ['CONTROL_', 'CTRL_'],
                'database': ['DATABASE_', 'DB_'],
                'element': ['ELEMENT_', 'ELEM_', 'EL_'],
                'set': ['SET_', 'NSET_', 'ESET_', 'PSET_', 'SSET_'],
                'define': ['DEFINE_', 'DEF_'],
                'initial': ['INITIAL_', 'INIT_']
            }
            
            # Standard keywords that should always be included
            standard_keywords = {
                'NODE', 'ELEMENT', 'PART', 'MATERIAL', 'SECTION', 'CONTACT',
                'CONTROL', 'DATABASE', 'DEFINE', 'INITIAL', 'BOUNDARY',
                'CONSTRAINED', 'LOAD', 'SET', 'INCLUDE', 'KEYWORD', 'END'
            }
            
            # Track which base keywords we've already included to avoid duplicates
            included_keywords = set()
            
            # First pass: try to match whitelist entries exactly
            for kw in base_keywords:
                kw_name = kw.get('name') or kw.get('keyword', '')
                if not kw_name:
                    continue
                
                clean_kw_name = normalize_name(kw_name)
                if not clean_kw_name:
                    continue
                    
                # Skip if we've already included this keyword
                if clean_kw_name in included_keywords:
                    continue
                
                # Get all possible variations of this keyword
                kw_variations = get_name_variations(clean_kw_name)
                
                # Check for direct matches with whitelist variations
                matched = False
                matched_clean_name = None
                
                for var in kw_variations:
                    if var in whitelist_variations:
                        # Found a match with a whitelist variation
                        matched = True
                        matched_clean_name = whitelist_variations[var][0]  # Take first match
                        matched_whitelist.add(matched_clean_name)
                        break
                
                # If no direct match, check for standard keywords or category prefixes
                if not matched:
                    # Check if this is a standard keyword
                    if clean_kw_name in standard_keywords:
                        matched = True
                    else:
                        # Check if this matches any of our category prefixes
                        for category, prefixes in keyword_categories.items():
                            if any(clean_kw_name.startswith(prefix) for prefix in prefixes):
                                matched = True
                                break
                
                if matched:
                    # Get the whitelist entry for this keyword if it exists
                    whitelist_entry = None
                    if matched_clean_name and matched_clean_name in whitelist_original_names:
                        whitelist_entry = whitelist_original_names[matched_clean_name]
                    
                    # Create a copy of the keyword to modify
                    kw_copy = kw.copy()
                    
                    # Use the name from the whitelist if available, otherwise use the cleaned name
                    if whitelist_entry:
                        kw_copy['name'] = whitelist_entry['name']  # Preserve original case and formatting
                        
                        # Merge in metadata from whitelist
                        for key in ['category', 'description', 'documentation']:
                            if key in whitelist_entry and key not in kw_copy:
                                kw_copy[key] = whitelist_entry[key]
                    else:
                        kw_copy['name'] = clean_kw_name
                    
                    # Add to our results
                    filtered_keywords.append(kw_copy)
                    included_keywords.add(clean_kw_name)
                    
                    if logger.isEnabledFor(logging.DEBUG):
                        source = f" (from whitelist: {matched_clean_name})" if matched_clean_name else ""
                        logger.debug(f"Included keyword: {kw_copy['name']}{source}")
            
            # Second pass: try to find partial matches for any remaining whitelist entries
            unmatched_whitelist = set(whitelist_original_names.keys()) - matched_whitelist
            
            if unmatched_whitelist:
                logger.info(f"Found {len(unmatched_whitelist)} whitelist entries without exact matches")
                
                for clean_name in sorted(unmatched_whitelist):
                    whitelist_entry = whitelist_original_names[clean_name]
                    
                    # Try to find a base keyword that contains or is contained by the whitelist name
                    best_match = None
                    best_score = 0
                    
                    for kw in base_keywords:
                        kw_name = kw.get('name') or kw.get('keyword', '')
                        if not kw_name:
                            continue
                            
                        clean_kw_name = normalize_name(kw_name)
                        if not clean_kw_name or clean_kw_name in included_keywords:
                            continue
                        
                        # Calculate a simple similarity score
                        score = 0
                        
                        # Check if one contains the other (case insensitive)
                        if clean_name in clean_kw_name or clean_kw_name in clean_name:
                            # Longer match is better
                            score = max(len(clean_name), len(clean_kw_name))
                        
                        # Check for common prefixes
                        for i, (c1, c2) in enumerate(zip(clean_name, clean_kw_name)):
                            if c1 != c2:
                                break
                            score += 1
                        
                        if score > best_score and score >= 3:  # Require at least 3 matching characters
                            best_score = score
                            best_match = kw
                    
                    if best_match:
                        kw_name = best_match.get('name') or best_match.get('keyword', '')
                        clean_kw_name = normalize_name(kw_name)
                        
                        # Create a copy of the keyword with whitelist metadata
                        kw_copy = best_match.copy()
                        kw_copy['name'] = whitelist_entry['name']  # Use whitelist name
                        
                        # Merge in metadata from whitelist
                        for key in ['category', 'description', 'documentation']:
                            if key in whitelist_entry and key not in kw_copy:
                                kw_copy[key] = whitelist_entry[key]
                        
                        filtered_keywords.append(kw_copy)
                        included_keywords.add(clean_kw_name)
                        matched_whitelist.add(clean_name)
                        
                        logger.info(f"Matched whitelist entry '{whitelist_entry['name']}' "
                                  f"to similar keyword: {clean_kw_name}")
            
            # Log statistics about the matching process
            total_whitelist = len(whitelist_original_names)
            total_matched = len(matched_whitelist)
            total_unmatched = total_whitelist - total_matched
            
            logger.info("\n=== KEYWORD MATCHING SUMMARY ===")
            logger.info(f"Total whitelist entries: {total_whitelist}")
            logger.info(f"Matched whitelist entries: {total_matched}")
            logger.info(f"Unmatched whitelist entries: {total_unmatched}")
            logger.info(f"Total keywords after filtering: {len(filtered_keywords)}")
            
            # Log details about unmatched whitelist entries
            if total_unmatched > 0:
                logger.info("\nUnmatched whitelist entries:")
                for clean_name in sorted(set(whitelist_original_names.keys()) - matched_whitelist):
                    logger.info(f"  - {whitelist_original_names[clean_name].get('name', clean_name)}")
                
                # Try to suggest potential matches for the first few unmatched entries
                sample_size = min(5, total_unmatched)
                if sample_size > 0:
                    logger.info("\nPotential matches for some unmatched entries:")
                    unmatched_sample = [
                        whitelist_original_names[n] 
                        for n in sorted(set(whitelist_original_names.keys()) - matched_whitelist)[:sample_size]
                    ]
                    
                    for entry in unmatched_sample:
                        entry_name = entry.get('name', '')
                        clean_entry_name = normalize_name(entry_name)
                        
                        # Find similar keywords in the base set
                        similar = []
                        for kw in base_keywords:
                            kw_name = kw.get('name') or kw.get('keyword', '')
                            if not kw_name:
                                continue
                                
                            clean_kw_name = normalize_name(kw_name)
                            if clean_kw_name and clean_kw_name != clean_entry_name:
                                # Simple similarity check
                                if (clean_entry_name in clean_kw_name or 
                                    clean_kw_name in clean_entry_name or
                                    clean_entry_name.split('_')[0] == clean_kw_name.split('_')[0]):
                                    similar.append(clean_kw_name)
                                    if len(similar) >= 3:  # Limit number of suggestions
                                        break
                        
                        if similar:
                            logger.info(f"  {entry_name} -> Similar to: {', '.join(similar[:3])}")
                        else:
                            logger.info(f"  {entry_name} -> No similar keywords found")
            
            logger.info("\n=== END MATCHING SUMMARY ===\n")
            
            return filtered_keywords
            
        except Exception as e:
            logger.error(f"Error filtering keywords: {str(e)}")
            logger.error(traceback.format_exc())
            
            # In case of error, return the unfiltered list rather than failing completely
            return base_keywords  # Return all keywords if there's an error
            
    @staticmethod
    def _extract_parameters_from_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract parameters from a keyword's data field.
        
        Args:
            data: The data dictionary from a keyword
            
        Returns:
            List of parameter dictionaries
        """
        if not data or not isinstance(data, dict):
            return []
            
        # Skip DEFAULTS section as it's handled separately
        if 'DEFAULTS' in data:
            return []
            
        parameters = []
        
        # Check for parameters in the data structure
        if 'parameters' in data:
            # If parameters are already in the expected format, use them directly
            if isinstance(data['parameters'], list):
                return data['parameters']
            # Otherwise, try to convert from the database format
            elif isinstance(data['parameters'], dict):
                return [{'name': k, **v} for k, v in data['parameters'].items()]
        
        # Try to extract parameters from the data structure
        for key, value in data.items():
            if key.startswith('field_') and isinstance(value, dict):
                param = {
                    'name': key,
                    'description': value.get('description', ''),
                    'type': value.get('type', 'text'),
                    'default': value.get('default', '')
                }
                parameters.append(param)
        
        return parameters
    
    @classmethod
    def filter_and_merge_keywords(
        cls,
        all_keywords: Dict[str, Any],
        whitelist_keywords: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter and merge keywords with their whitelist data.
        
        Args:
            all_keywords: Dictionary containing 'successful' list of keywords
            whitelist_keywords: List of whitelisted keywords with additional metadata
            
        Returns:
            List of merged keyword dictionaries
        """
        try:
            logger.info("Starting keyword filtering and merging...")
            
            # 1. Get the list of keywords from the 'successful' key
            if not isinstance(all_keywords, dict) or 'successful' not in all_keywords:
                logger.error("Invalid keyword database format: 'successful' key not found")
                return []
                
            keyword_list = all_keywords['successful']
            
            # 2. Create a mapping of keyword names to their data
            keyword_map = {}
            for kw in keyword_list:
                if not isinstance(kw, dict):
                    continue
                    
                # Extract the keyword name from the 'keyword' field
                keyword_entry = kw.get('keyword', '')
                if isinstance(keyword_entry, str):
                    # Get the first line of the keyword entry
                    keyword_name = keyword_entry.split('\n')[0].strip()
                    if keyword_name.upper() == 'DEFAULTS':
                        # Handle DEFAULTS section if present
                        defaults = kw.get('data', {})
                        if defaults:
                            logger.info(f"Found DEFAULTS section with {len(defaults)} parameters")
                        continue
                        
                    if keyword_name:
                        keyword_map[keyword_name.upper()] = kw
            
            # 3. Process whitelist keywords
            whitelist_names = {w.get('name', '').strip().upper() for w in whitelist_keywords if w.get('name')}
            matched_whitelist_names = set()
            filtered_keywords = []
            
            logger.info(f"Found {len(whitelist_names)} unique whitelist keywords")
            logger.info(f"Found {len(keyword_map)} keywords in database")
            
            # 4. First pass: Try exact matches
            for whitelist_kw in whitelist_keywords:
                whitelist_name = whitelist_kw.get('name', '').strip()
                if not whitelist_name:
                    continue
                    
                whitelist_upper = whitelist_name.upper()
                
                # Try exact match first
                kw = keyword_map.get(whitelist_upper)
                if kw:
                    matched_whitelist_names.add(whitelist_upper)
                    keyword_entry = kw.get('keyword', '')
                    keyword_name = keyword_entry.split('\n')[0].strip()
                    
                    # Create the merged keyword entry
                    merged_kw = {
                        'name': keyword_name,
                        'category': whitelist_kw.get('category', 'General'),
                        'description': whitelist_kw.get('description', ''),
                        'documentation': whitelist_kw.get('documentation', ''),
                        'file': kw.get('file', ''),
                        'data': kw.get('data', {})
                    }
                    
                    # Add parameters from the whitelist if they exist
                    if 'parameters' in whitelist_kw:
                        merged_kw['parameters'] = whitelist_kw['parameters']
                    else:
                        # Extract parameters from the data if not in whitelist
                        merged_kw['parameters'] = cls._extract_parameters_from_data(kw.get('data', {}))
                    
                    filtered_keywords.append(merged_kw)
                    logger.debug(f"Added keyword: {keyword_name} with {len(merged_kw.get('parameters', []))} parameters")
            
            # 5. Second pass: Try case-insensitive matching for any remaining whitelist keywords
            remaining_whitelist = [w for w in whitelist_keywords 
                                 if w.get('name', '').strip().upper() not in matched_whitelist_names]
            
            logger.info(f"Found {len(remaining_whitelist)} whitelist keywords without exact matches")
            
            for whitelist_kw in remaining_whitelist:
                whitelist_name = whitelist_kw.get('name', '').strip()
                if not whitelist_name:
                    continue
                    
                whitelist_upper = whitelist_name.upper()
                
                # Try to find a case-insensitive match
                matched_kw = None
                for kw_name, kw in keyword_map.items():
                    if kw_name.upper() == whitelist_upper:
                        matched_kw = kw
                        break
                
                if matched_kw and kw_name not in matched_whitelist_names:
                    matched_whitelist_names.add(kw_name)
                    keyword_entry = matched_kw.get('keyword', '')
                    keyword_name = keyword_entry.split('\n')[0].strip()
                    
                    # Create the merged keyword entry
                    merged_kw = {
                        'name': keyword_name,
                        'category': whitelist_kw.get('category', 'General'),
                        'description': whitelist_kw.get('description', ''),
                        'documentation': whitelist_kw.get('documentation', ''),
                        'file': matched_kw.get('file', ''),
                        'data': matched_kw.get('data', {})
                    }
                    
                    # Add parameters from the whitelist if they exist
                    if 'parameters' in whitelist_kw:
                        merged_kw['parameters'] = whitelist_kw['parameters']
                    else:
                        # Extract parameters from the data if not in whitelist
                        merged_kw['parameters'] = cls._extract_parameters_from_data(matched_kw.get('data', {}))
                    
                    filtered_keywords.append(merged_kw)
                    logger.debug(f"Added keyword (case-insensitive match): {keyword_name}")
            
            logger.info(f"Total keywords after filtering: {len(filtered_keywords)}")
            logger.info(f"Matched {len(matched_whitelist_names)} out of {len(whitelist_names)} whitelist keywords")
                
            logger.info(f"Filtered and merged {len(filtered_keywords)} keywords")
            return filtered_keywords
            
        except Exception as e:
            logger.error(f"Error in filter_and_merge_keywords: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    @classmethod
    def load_keywords(
        cls,
        db_path: str,
        whitelist_path: str
    ) -> List[Dict[str, Any]]:
        """
        Load and filter keywords from the database using a whitelist.
        
        Args:
            db_path: Path to the keyword database JSON file
            whitelist_path: Path to the whitelist JSON file
            
        Returns:
            List of filtered and merged keywords
        """
        try:
            # Load the full keyword database
            all_keywords = cls.load_keyword_database(db_path)
            if not all_keywords:
                logger.error("No keywords loaded from database")
                return []
            
            # Load the whitelist
            whitelist_keywords = cls.load_whitelist(whitelist_path)
            if not whitelist_keywords:
                logger.warning("No whitelist entries found, using all keywords")
                whitelist_keywords = [{'name': kw.get('keyword', '').split('\n')[0].strip()} 
                                   for kw in all_keywords if kw.get('keyword')]
            
            # Filter and merge keywords
            return cls.filter_and_merge_keywords(all_keywords, whitelist_keywords)
            
        except Exception as e:
            logger.error(f"Error loading keywords: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return []
