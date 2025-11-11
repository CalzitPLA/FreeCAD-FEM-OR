to#!/usr/bin/env python3
"""
Python HM Reader Implementation
Based on OpenRadioss HM Reader Library functions
Provides Python equivalent of HM reader Fortran functions
"""

import os
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path

class PythonHMReader:
    """
    Python implementation of OpenRadioss HM Reader Library
    Provides equivalent functionality to the Fortran HM reader functions
    """

    def __init__(self, cfg_root: str):
        self.cfg_root = cfg_root
        self.keyword_database: Dict[str, Any] = {}
        self.current_keyword: Optional[str] = None
        self.current_index: int = 0
        self.categories: set = set()

    def initialize_database(self):
        """Initialize the keyword database by scanning CFG files"""
        print("HM Reader: Initializing database...")

        # Scan all format directories
        format_dirs = self._find_format_directories()

        for fmt_dir in format_dirs:
            print(f"HM Reader: Processing {os.path.basename(fmt_dir)}...")
            self._scan_format_directory(fmt_dir)

        print(f"HM Reader: Database initialized with {len(self.keyword_database)} keywords")
        return len(self.keyword_database)

    def _find_format_directories(self) -> List[str]:
        """Find all available format directories"""
        format_dirs = []

        if not os.path.exists(self.cfg_root):
            print(f"HM Reader Error: CFG root directory not found: {self.cfg_root}")
            return format_dirs

        # Find all subdirectories that contain CFG files
        for item in os.listdir(self.cfg_root):
            item_path = os.path.join(self.cfg_root, item)
            if os.path.isdir(item_path):
                # Check if directory contains CFG files
                cfg_files = list(Path(item_path).rglob("*.cfg"))
                if cfg_files:
                    format_dirs.append(item_path)

        return sorted(format_dirs)

    def _scan_format_directory(self, fmt_dir: str):
        """Scan a format directory for CFG files"""
        for root, dirs, files in os.walk(fmt_dir):
            for file in files:
                if file.endswith('.cfg'):
                    cfg_path = os.path.join(root, file)
                    self._parse_cfg_file(cfg_path)

    def _parse_cfg_file(self, cfg_path: str):
        """Parse a single CFG file and add to database"""
        try:
            content = self._read_cfg_file(cfg_path)
            if not content:
                return

            # Extract format type from path
            format_type = self._detect_format_from_path(cfg_path)

            # Parse based on format type
            if format_type == 'LS_DYNA':
                self._parse_ls_dyna_cfg(content, cfg_path)
            elif format_type == 'OPENRADIOSS':
                self._parse_openradioss_cfg(content, cfg_path)

        except Exception as e:
            print(f"HM Reader: Error parsing {cfg_path}: {e}")

    def _detect_format_from_path(self, cfg_path: str) -> str:
        """Detect format type from file path"""
        if 'Keyword971' in cfg_path:
            return 'LS_DYNA'
        elif any(radioss in cfg_path for radioss in ['radioss', 'RADIOSS']):
            return 'OPENRADIOSS'
        return 'UNKNOWN'

    def _read_cfg_file(self, cfg_path: str) -> Optional[str]:
        """Read CFG file with encoding fallback"""
        encodings = ['utf-8', 'iso-8859-1', 'cp1252', 'utf-16']

        for encoding in encodings:
            try:
                with open(cfg_path, 'r', encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
            except FileNotFoundError:
                return None

        return None

    def _parse_ls_dyna_cfg(self, content: str, cfg_path: str):
        """Parse LS-DYNA format CFG file"""
        # Extract keyword header from GUI section
        keyword_header = self._extract_keyword_header(content)

        # Extract parameters from ATTRIBUTES section
        parameters = self._extract_parameters(content, 'LS_DYNA')

        # Extract category from path
        category = self._extract_category_from_path(cfg_path)

        # Extract keyword name from ASSIGN statements or file name
        keyword_names = self._extract_keyword_names(content, cfg_path)

        for keyword_name in keyword_names:
            if keyword_name.startswith('_'):
                continue

            # Create keyword entry in database
            self.keyword_database[keyword_name] = {
                'name': keyword_name,
                'header': keyword_header or f"*{keyword_name}",
                'category': category,
                'parameters': parameters,
                'source_file': os.path.basename(cfg_path),
                'format_type': 'LS_DYNA',
                'card_formats': self._extract_card_formats(content),
                'identifiers': self._extract_identifiers(content),
                'definitions': self._extract_definitions(content)
            }

            self.categories.add(category)

    def _parse_openradioss_cfg(self, content: str, cfg_path: str):
        """Parse OpenRadioss format CFG file"""
        # Similar parsing for OpenRadioss format
        keyword_header = self._extract_keyword_header(content)
        parameters = self._extract_parameters(content, 'OPENRADIOSS')
        category = self._extract_category_from_path(cfg_path)
        keyword_names = self._extract_keyword_names(content, cfg_path)

        for keyword_name in keyword_names:
            if keyword_name.startswith('_'):
                continue

            self.keyword_database[keyword_name] = {
                'name': keyword_name,
                'header': keyword_header or f"*{keyword_name}",
                'category': category,
                'parameters': parameters,
                'source_file': os.path.basename(cfg_path),
                'format_type': 'OPENRADIOSS',
                'card_formats': self._extract_card_formats(content),
                'identifiers': self._extract_identifiers(content),
                'definitions': self._extract_definitions(content)
            }

            self.categories.add(category)

    def _extract_keyword_header(self, content: str) -> str:
        """Extract keyword header from GUI section"""
        gui_section = re.search(r'GUI[^}]*{([^}]*)}', content, re.DOTALL)
        if not gui_section:
            return ""

        gui_content = gui_section.group(1)

        # Look for ASSIGN statements that set KEYWORD_STR
        assign_matches = re.findall(r'ASSIGN\(KEYWORD_STR,\s*"([^"]*)"\)', gui_content)
        if assign_matches:
            return assign_matches[0]

        # Look for HEADER statements
        header_matches = re.findall(r'HEADER\("([^"]*)"', gui_content)
        if header_matches:
            return header_matches[0]

        return ""

    def _extract_keyword_names(self, content: str, cfg_path: str) -> List[str]:
        """Extract keyword names from CFG content or file path"""
        keyword_names = []

        # Try to extract from GUI section first
        gui_section = re.search(r'GUI[^}]*{([^}]*)}', content, re.DOTALL)
        if gui_section:
            gui_content = gui_section.group(1)

            # Look for ASSIGN statements
            assign_matches = re.findall(r'ASSIGN\(KEYWORD_STR,\s*"([^"]*)"\)', gui_content)
            for assign_match in assign_matches:
                keyword_name = assign_match.strip('*').replace('/', '_').replace('-', '_')
                if keyword_name and not keyword_name.startswith('_'):
                    keyword_names.append(keyword_name.upper())

        # Fallback to file name if no keywords found
        if not keyword_names:
            filename = os.path.basename(cfg_path).replace('.cfg', '')
            if filename.startswith('mat'):
                keyword_names.append(filename.replace('mat', 'MAT_').upper())
            else:
                keyword_names.append(filename.upper())

        return keyword_names

    def _extract_parameters(self, content: str, format_type: str) -> List[Dict[str, Any]]:
        """Extract parameters from ATTRIBUTES section"""
        parameters = []

        # Find ATTRIBUTES section
        attr_section = re.search(r'ATTRIBUTES[^}]*{([^}]*)}', content, re.DOTALL)
        if not attr_section:
            return parameters

        attr_content = attr_section.group(1)

        # Pattern for parameter definitions
        param_matches = re.findall(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*VALUE\(([^,)]+),\s*"([^"]*)"', attr_content)

        for param_match in param_matches:
            param_name = param_match[0]
            param_type = param_match[1]
            param_desc = param_match[2]

            if param_name.startswith('_'):
                continue

            parameter = {
                'name': param_name,
                'type': param_type,
                'description': param_desc,
                'dimension': self._extract_dimension_from_gui(content, param_name),
                'required': self._is_parameter_required(content, param_name),
                'field_0': param_name.lower(),
                'array_size': None,
                'is_array': False
            }

            parameters.append(parameter)

        return parameters

    def _extract_dimension_from_gui(self, content: str, param_name: str) -> str:
        """Extract dimension information from GUI section"""
        gui_section = re.search(r'GUI[^}]*{([^}]*)}', content, re.DOTALL)
        if not gui_section:
            return ""

        gui_content = gui_section.group(1)

        # Look for DIMENSION information
        dim_match = re.search(rf'SCALAR\({re.escape(param_name)}\)\s*{{\s*DIMENSION\s*=\s*"([^"]*)"', gui_content)
        if dim_match:
            return dim_match.group(1)

        return ""

    def _is_parameter_required(self, content: str, param_name: str) -> bool:
        """Check if parameter is mandatory"""
        gui_section = re.search(r'GUI[^}]*{([^}]*)}', content, re.DOTALL)
        if not gui_section:
            return False

        gui_content = gui_section.group(1)

        # Look for mandatory section
        mandatory_section = re.search(r'mandatory:\s*(.*?)(?=optional:|$)', gui_content, re.DOTALL)
        if mandatory_section and param_name in mandatory_section.group(1):
            return True

        return False

    def _extract_card_formats(self, content: str) -> List[Dict[str, Any]]:
        """Extract card formats from FORMAT section"""
        card_formats = []

        # Find FORMAT section
        format_section = re.search(r'FORMAT\([^)]+\)\s*{([^}]*)}', content, re.DOTALL)
        if not format_section:
            return card_formats

        format_content = format_section.group(1)

        # Find CARD lines
        card_matches = re.findall(r'CARD\("([^"]*)"', format_content)
        comment_matches = re.findall(r'COMMENT\("([^"]*)"', format_content)

        for i, card_match in enumerate(card_matches):
            card_info = {
                'type': 'card',
                'format': card_match,
                'line_number': i + 1
            }
            if i < len(comment_matches):
                card_info['comment'] = comment_matches[i]
            card_formats.append(card_info)

        return card_formats

    def _extract_identifiers(self, content: str) -> Dict[str, str]:
        """Extract identifiers from SKEYWORDS_IDENTIFIER section"""
        identifiers = {}

        # Find SKEYWORDS_IDENTIFIER section
        skey_section = re.search(r'SKEYWORDS_IDENTIFIER[^}]*{([^}]*)}', content, re.DOTALL)
        if not skey_section:
            return identifiers

        skey_content = skey_section.group(1)

        # Extract identifier mappings
        id_matches = re.findall(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+)', skey_content)
        for id_match in id_matches:
            id_name = id_match[0].strip()
            id_value = id_match[1].strip()

            if id_name.startswith('//') or not id_name:
                continue

            identifiers[id_name] = id_value

        return identifiers

    def _extract_definitions(self, content: str) -> Dict[str, Any]:
        """Extract definitions from DEFINITIONS section"""
        definitions = {}

        # Find DEFINITIONS section
        def_section = re.search(r'DEFINITIONS[^}]*{([^}]*)}', content, re.DOTALL)
        if not def_section:
            return definitions

        def_content = def_section.group(1)

        # Extract DATA_NAMES
        data_names_match = re.search(r'DATA_NAMES\s*=\s*\(([^)]*)\)', def_content)
        if data_names_match:
            data_names = [name.strip() for name in data_names_match.group(1).split(',') if name.strip()]
            definitions['data_names'] = data_names

        return definitions

    def _extract_category_from_path(self, cfg_path: str) -> str:
        """Extract category from file path"""
        path_parts = cfg_path.split(os.sep)
        for part in path_parts:
            if part.upper() in ['MAT', 'PROP', 'LOADS', 'CARDS', 'INTER', 'FAIL', 'DAMP',
                               'SENSOR', 'TABLE', 'OUTPUTBLOCK', 'RBODY', 'TRANSFORM']:
                return part.replace('_', ' ').title()
        return "General"

    # HM Reader API Functions (Python equivalents of Fortran functions)

    def HM_OPTION_COUNT(self, keyword: str) -> int:
        """Count number of occurrences of a keyword (equivalent to HM_OPTION_COUNT)"""
        count = 0
        for kw_name, kw_data in self.keyword_database.items():
            if kw_name.startswith(keyword.upper()) or keyword.upper() in kw_name:
                count += 1
        return count

    def HM_OPTION_START(self, keyword: str) -> bool:
        """Start reading a keyword section (equivalent to HM_OPTION_START)"""
        self.current_keyword = keyword.upper()
        self.current_index = 0
        return self.HM_OPTION_COUNT(keyword) > 0

    def HM_OPTION_NEXT(self) -> bool:
        """Move to next occurrence of current keyword (equivalent to HM_OPTION_NEXT)"""
        if not self.current_keyword:
            return False

        self.current_index += 1
        return self.current_index < self.HM_OPTION_COUNT(self.current_keyword)

    def HM_OPTION_READ_KEY(self, keyword: str) -> Tuple[str, str, str, str, int, int, str]:
        """Read keyword with header information (equivalent to HM_OPTION_READ_KEY)"""
        # This is a simplified version - in real HM reader this would read from input file
        # For now, return dummy values
        return "", "", "", "", 0, 0, ""

    def HM_GET_INTV(self, param_name: str) -> int:
        """Get integer value (equivalent to HM_GET_INTV)"""
        # This would normally read from the input file
        # For now, return 0 as placeholder
        return 0

    def HM_GET_FLOATV(self, param_name: str) -> float:
        """Get float value (equivalent to HM_GET_FLOATV)"""
        # This would normally read from the input file
        # For now, return 0.0 as placeholder
        return 0.0

    def HM_GET_STRING(self, param_name: str) -> str:
        """Get string value (equivalent to HM_GET_STRING)"""
        # This would normally read from the input file
        # For now, return empty string as placeholder
        return ""

    def HM_GET_BOOLV(self, param_name: str) -> bool:
        """Get boolean value (equivalent to HM_GET_BOOLV)"""
        # This would normally read from the input file
        # For now, return False as placeholder
        return False

    def HM_GET_INTV_ARRAY_INDEX(self, param_name: str, index: int) -> int:
        """Get integer array value at index (equivalent to HM_GET_INTV_ARRAY_INDEX)"""
        return 0

    def HM_GET_FLOATV_ARRAY_INDEX(self, param_name: str, index: int) -> float:
        """Get float array value at index (equivalent to HM_GET_FLOATV_ARRAY_INDEX)"""
        return 0.0

    def HM_GET_FLOATV_DIM(self, param_name: str) -> float:
        """Get float value with physical dimension (equivalent to HM_GET_FLOATV_DIM)"""
        return 0.0

    def get_keyword_info(self, keyword_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a keyword"""
        return self.keyword_database.get(keyword_name.upper())

    def list_keywords_by_category(self, category: str) -> List[str]:
        """List all keywords in a specific category"""
        return [name for name, kw in self.keyword_database.items()
                if kw['category'] == category]

    def list_all_categories(self) -> List[str]:
        """List all available categories"""
        return sorted(list(self.categories))

    def search_keywords(self, pattern: str) -> List[str]:
        """Search keywords by pattern"""
        pattern = pattern.upper()
        return [name for name in self.keyword_database.keys()
                if pattern in name or name.startswith(pattern)]

def test_hm_reader():
    """Test the Python HM reader implementation"""
    print("=== Python HM Reader Test ===")

    # Initialize HM reader
    cfg_root = "/home/nemo/Dokumente/Sandbox/Fem_upgraded/gui/CFG_Openradioss"
    hm_reader = PythonHMReader(cfg_root)

    # Initialize database
    count = hm_reader.initialize_database()
    print(f"Database initialized with {count} keywords")

    # Test HM reader functions
    print("\n=== HM Reader Function Tests ===")

    # Test counting
    part_count = hm_reader.HM_OPTION_COUNT("PART")
    print(f"PART keywords: {part_count}")

    mat_count = hm_reader.HM_OPTION_COUNT("MAT")
    print(f"MAT keywords: {mat_count}")

    # Test search
    mat_keywords = hm_reader.search_keywords("MAT_")
    print(f"MAT keywords found: {len(mat_keywords)}")
    print(f"Sample MAT keywords: {mat_keywords[:5]}")

    # Test keyword info
    if mat_keywords:
        sample_keyword = mat_keywords[0]
        info = hm_reader.get_keyword_info(sample_keyword)
        if info:
            print(f"\nSample keyword info for {sample_keyword}:")
            print(f"  Header: {info['header']}")
            print(f"  Category: {info['category']}")
            print(f"  Parameters: {len(info['parameters'])}")
            print(f"  Format: {info['format_type']}")
            print(f"  Format tags: {info.get('format_tags', [])}")

    # Test categories
    categories = hm_reader.list_all_categories()
    print(f"\nAvailable categories: {categories}")

    return hm_reader

if __name__ == "__main__":
    test_hm_reader()
