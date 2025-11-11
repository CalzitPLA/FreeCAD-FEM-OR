"""OpenRadioss Keyword Editor GUI for FreeCAD"""

import os
import json
import copy
import webbrowser
import markdown
import datetime
from pathlib import Path

import FreeCAD
import FreeCADGui as Gui

# Try to import Qt modules with fallback support
try:
    # Try PySide2 first (most common in FreeCAD)
    from PySide2 import QtCore, QtGui, QtWidgets, QtNetwork
    #print("[INFO] Using PySide2")
except ImportError:
    try:
        # Try PyQt5
        from PyQt5 import QtCore, QtGui, QtWidgets, QtNetwork
        #print("[INFO] Using PyQt5")
    except ImportError:
        try:
            # Try PyQt6
            from PyQt6 import QtCore, QtGui, QtWidgets, QtNetwork
            #print("[INFO] Using PyQt6")
        except ImportError:
            try:
                # Last resort - PySide (original Qt4 binding)
                from PySide import QtCore, QtGui, QtNetwork
                #print("[INFO] Using PySide")
                # For PySide, QtWidgets classes are in QtGui
                QtWidgets = QtGui
            except ImportError:
                raise ImportError("No Qt bindings found. Please install PySide2, PyQt5, PyQt6, or PySide.")

# Qt4-style widget aliases for compatibility
QAction = QtWidgets.QAction
QVBoxLayout = QtWidgets.QVBoxLayout
QHBoxLayout = QtWidgets.QHBoxLayout
QSplitter = QtWidgets.QSplitter
QComboBox = QtWidgets.QComboBox
QListWidget = QtWidgets.QListWidget
QListWidgetItem = QtWidgets.QListWidgetItem
QTextEdit = QtWidgets.QTextEdit
QTableWidget = QtWidgets.QTableWidget
QTableWidgetItem = QtWidgets.QTableWidgetItem
QLabel = QtWidgets.QLabel
QFileDialog = QtWidgets.QFileDialog
QMessageBox = QtWidgets.QMessageBox
QMenuBar = QtWidgets.QMenuBar
QPushButton = QtWidgets.QPushButton
QLineEdit = QtWidgets.QLineEdit
QStackedWidget = QtWidgets.QStackedWidget
QDialogButtonBox = QtWidgets.QDialogButtonBox
QTabWidget = QtWidgets.QTabWidget
QInputDialog = QtWidgets.QInputDialog

# For PySide (Qt4) compatibility, also define QWidget
try:
    QWidget = QtWidgets.QWidget
except AttributeError:
    # PySide (Qt4) compatibility - QWidget might be in QtGui
    try:
        QWidget = QtGui.QWidget
    except AttributeError:
        # Last resort - create a basic QWidget class
        class QWidget(QtGui.QWidget if hasattr(QtGui, 'QWidget') else object):
            def __init__(self, parent=None):
                if hasattr(QtGui, 'QWidget'):
                    QtGui.QWidget.__init__(self, parent)
                else:
                    self.parent = parent

# Environment detection
IS_FLATPAK = os.path.exists('/.flatpak-info')
HAS_WEB_GUI = False

# Web engine detection flags
HAS_WEB_ENGINE = False
HAS_WEBKIT = False
HAS_PYQT6_WEBENGINE = False
HAS_PYSIDE6 = False

if not IS_FLATPAK:
    try:
        import WebGui
        if hasattr(FreeCAD, 'GuiUp') and FreeCAD.GuiUp and hasattr(WebGui, 'openBrowserWindow'):
            HAS_WEB_GUI = True
            print("[INFO] Using FreeCAD WebGui for documentation")
        else:
            print("[INFO] FreeCAD WebGui not properly initialized")
    except ImportError:
        pass

else:
    print("[INFO] Running in Flatpak environment, will use system browser")

class DocumentationViewer(QtGui.QDialog):
    """Simple dialog that opens documentation in system browser."""

    def __init__(self, parent=None):
        super(DocumentationViewer, self).__init__(parent)
        self.setWindowTitle("Documentation")
        self.setMinimumSize(400, 300)

        # Create layout
        layout = QtGui.QVBoxLayout(self)

        # Create text area for instructions
        self.text_area = QtGui.QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setHtml("""
        <div style="text-align: center; padding: 20px;">
            <h2>Documentation Viewer</h2>
            <p>Documentation will open in your system's default web browser.</p>
            <p>Click the button below to view the documentation.</p>
        </div>
        """)

        # Create button to open documentation
        self.open_button = QtGui.QPushButton("Open Documentation in Browser")
        self.open_button.clicked.connect(self.open_in_browser)

        # Create close button
        self.close_button = QtGui.QPushButton("Close")
        self.close_button.clicked.connect(self.accept)

        # Button layout
        button_layout = QtGui.QHBoxLayout()
        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.close_button)

        # Add widgets to layout
        layout.addWidget(self.text_area)
        layout.addLayout(button_layout)

        self.doc_url = None

    def show_documentation(self, doc_url, section=None, scroll_lines=0):
        """Store the documentation URL for later use."""
        self.doc_url = doc_url
        if section and not doc_url.endswith(f'#{section}'):
            self.doc_url = f"{doc_url}#{section}"

        # Update text area with URL info
        if self.doc_url:
            self.text_area.setHtml(f"""
            <div style="text-align: center; padding: 20px;">
                <h2>Documentation Available</h2>
                <p><strong>URL:</strong> {self.doc_url}</p>
                <p>Click the button below to open in your browser.</p>
            </div>
            """)
        else:
            self.text_area.setHtml("""
            <div style="text-align: center; padding: 20px;">
                <h2>No Documentation</h2>
                <p>No documentation URL is available for this keyword.</p>
            </div>
            """)

    def open_in_browser(self):
        """Open the stored documentation URL in the system browser."""
        if self.doc_url:
            #print(f"[INFO] Opening documentation in system browser: {self.doc_url}")
            webbrowser.open(self.doc_url)

        # Import CacheViewerWindow from the cache viewer module
        try:
            from femcommands.open_cache_viewer import CacheViewerWindow
            #print("[INFO] CacheViewerWindow imported successfully")
        except ImportError as e:
            #print(f"[WARNING] Failed to import CacheViewerWindow: {e}")
            #print("[WARNING] Cache viewer functionality will be limited")
            # Define a basic fallback class
            class CacheViewerWindow(QtWidgets.QDialog):
                def __init__(self, cache_data, parent=None):
                    super(CacheViewerWindow, self).__init__(parent)
                    self.setWindowTitle("Cache Viewer - Limited")
                    layout = QtWidgets.QVBoxLayout(self)
                    layout.addWidget(QtWidgets.QLabel("Cache viewer functionality not available"))
                    self.cache_data = cache_data


class OpenRadiossKeywordEditorDialog(QtGui.QDialog):
    """Main dialog for the OpenRadioss Keyword Editor."""

    def __init__(self, parent=None):
        # Set window flags to remove title bar buttons
        super(OpenRadiossKeywordEditorDialog, self).__init__(parent, 
            QtCore.Qt.Window | 
            QtCore.Qt.CustomizeWindowHint | 
            QtCore.Qt.WindowTitleHint | 
            QtCore.Qt.WindowCloseButtonHint)
            
        print("\n=== DEBUG: Initializing OpenRadiossKeywordEditorDialog ===")
            
        # Initialize instance variables
        self.keywords = []
        self.current_keyword = None
        self.param_inputs = {}  # Store parameter input widgets
        self.keyword_cache = []  # Cache for generated keywords
        self.json_keywords = []  # Store keywords from JSON
        self.raw_keyword_data = {}  # Store raw keyword data for lazy loading
        self.keyword_metadata = []  # Store keyword metadata
        self.clean_keywords = {}  # Store clean keyword data
        
        # Initialize cache paths and load existing cache
        from femcommands.open_cache_viewer import CACHE_FILE, CACHE_DIR, load_cache_from_disk
        self.CACHE_FILE = CACHE_FILE
        self.CACHE_DIR = CACHE_DIR
        
        # Initialize keyword cache
        self.keyword_cache = []
        self.load_cache()

        # Template configuration
        self.template_mode = "full"  # "full", "basic", "minimal"

        # Load settings first
        self.load_settings()

        # Initialize UI components
        self.setup_ui()
        self.show_welcome_message()
        
        # Load keyword metadata (lazy loading)
        print("\n[DEBUG] Starting to load keyword metadata...")
        self.initialize_keyword_metadata()
        print("[DEBUG] Keyword metadata loading complete.")
        
        # Load keywords using the whitelist filter
        print("\n[DEBUG] Starting to load and filter keywords...")
        self.keywords = self.load_keywords()
        print(f"[DEBUG] Loaded {len(self.keywords)} keywords after filtering")
        
        # Update the UI with the loaded keywords
        if hasattr(self, 'update_category_list'):
            self.update_category_list()
        
    def initialize_keyword_metadata(self):
        """Initialize only the metadata for keywords, not the full data"""
        try:
                # Paths to keyword files
            db_path = os.path.join(os.path.dirname(__file__), 'json', 'keep', 'keyword_database_results.json')
            clean_path = os.path.join(os.path.dirname(__file__), 'json', 'keywords_clean.json')
            
            if not os.path.exists(db_path):
                raise FileNotFoundError(f"Keyword database not found at {db_path}")
            if not os.path.exists(clean_path):
                print("[WARNING] Clean keywords file not found, web links will not be available")
                pass
            
            # Load the database
            with open(db_path, 'r', encoding='utf-8') as f:
                db_data = json.load(f)
            
            # Load clean keywords for metadata
            if os.path.exists(clean_path):
                with open(clean_path, 'r', encoding='utf-8') as f:
                    clean_data = json.load(f)
                    self.clean_keywords = {kw['name']: kw for kw in clean_data if 'name' in kw}
            
            # Store raw data and create metadata entries
            successful_keywords = db_data.get('successful', [])
            #print(f"[INFO] Loaded metadata for {len(successful_keywords)} keywords")
            
            self.keyword_metadata = []
            for kw in successful_keywords:
                keyword = kw.get('keyword', '').strip()
                if not keyword or 'UNSUPPORTED' in keyword.upper():
                    continue
                
                # Store raw data for lazy loading
                self.raw_keyword_data[keyword] = kw
                
                # Create metadata entry
                clean_kw = self.clean_keywords.get(keyword, {})
                kw_meta = {
                    'name': keyword,
                    'syntax': keyword,
                    'description': clean_kw.get('description', 
                        kw.get('data', {}).get('ATTRIBUTES', {}).get('DESCRIPTION', {}).get('value', 'No description available')),
                    'category': self._determine_category(keyword, kw.get('data', {})),
                    'has_web_link': 'web_link' in clean_kw,
                    'has_example': 'EXAMPLE' in kw.get('data', {}) or 'example' in clean_kw,
                    'has_notes': 'NOTES' in kw.get('data', {}) or 'notes' in clean_kw
                }
                
                self.keyword_metadata.append(kw_meta)
            
            if self.keyword_metadata:
                # Use the already filtered keywords from load_keywords()
                # Don't filter again to avoid double filtering
                self.keywords = self.keyword_metadata  # Use all metadata for display
                
                # Update the UI
                self.update_category_list()
                self.update_keyword_list()
                
                # UI is updated, no status message needed
                pass
            else:
                # No valid keywords found
                pass
            
        except Exception as e:
            import traceback
            #print(f"Error initializing keyword metadata: {str(e)}\n{traceback.format_exc()}")
            pass
    
    def load_keyword_details(self, keyword_name):
        """Load full details for a keyword when it's selected"""
        if not keyword_name or keyword_name not in self.raw_keyword_data:
            return None
            
        #print(f"[DEBUG] Loading details for keyword: {keyword_name}")
        
        kw = self.raw_keyword_data[keyword_name]
        clean_kw = self.clean_keywords.get(keyword_name, {})
        kw_data = kw.get('data', {})
        attrs = kw_data.get('ATTRIBUTES', {})
        
        # Extract parameters and convert to dictionary format
        param_list = self._extract_parameters(attrs)
        params_dict = {}
        for param in param_list:
            param_name = param.pop('name')
            params_dict[param_name] = param
        
        # Create full keyword entry
        kw_entry = {
            'name': keyword_name,
            'syntax': keyword_name,
            'description': clean_kw.get('description') or 
                         attrs.get('DESCRIPTION', {}).get('value', 'No description available'),
            'category': self._determine_category(keyword_name, kw_data),
            'parameters': params_dict
        }
        
        # Add web link from clean keywords if available
        if 'web_link' in clean_kw:
            kw_entry['web_link'] = clean_kw['web_link']
        
        # Add any additional metadata from database
        if 'EXAMPLE' in kw_data:
            kw_entry['example'] = kw_data['EXAMPLE']
        if 'NOTES' in kw_data:
            kw_entry['notes'] = kw_data['NOTES']
        
        # Add any additional metadata from clean keywords (overwrites database)
        for field in ['example', 'notes', 'syntax']:
            if field in clean_kw and clean_kw[field]:
                kw_entry[field] = clean_kw[field]
        
        return kw_entry
    
    def _determine_category(self, keyword, kw_data):
        """Determine the category for a keyword based on its name and data."""
        # Try to extract from keyword prefix (e.g., *MAT_* for materials)
        if keyword.startswith('*MAT_'):
            return 'Materials'
        elif keyword.startswith(('*ELEMENT_', '*SHELL_', '*SOLID_', '*BEAM_')):
            return 'Elements'
        elif keyword.startswith(('*SET_', '*SUBSET_')):
            return 'Sets'
        elif keyword.startswith(('*LOAD_', '*FORCE_', '*PRESSURE_')):
            return 'Loads'
        elif keyword.startswith(('*BOUNDARY_', '*INITIAL_')):
            return 'Boundary Conditions'
        elif keyword.startswith(('*CONTACT_', '*INTER_')):
            return 'Contacts'
        elif keyword.startswith(('*DATABASE_', '*OUTPUT_')):
            return 'Output'
        elif keyword.startswith(('*CONTROL_', '*TERMINATION_')):
            return 'Control'
        else:
            return 'General'
    
    def _extract_parameters(self, attrs):
        """Extract parameters from keyword attributes.
        
        Args:
            attrs (dict): Dictionary of attributes from the keyword database
            
        Returns:
            list: List of parameter dictionaries with name, type, description, and default value
        """
        #print("\n[DEBUG] _extract_parameters called")
        #print(f"  [DEBUG] Received attrs: {list(attrs.keys())}")
        
        params = []
        
        for name, data in attrs.items():
            # Skip internal fields
            if name in ('KEYWORD_STR', 'LSD_TitleOpt', 'TITLE'):
                #print(f"  [DEBUG] Skipping internal field: {name}")
                continue
                
            #print(f"\n  [DEBUG] Processing parameter: {name}")
            #print(f"    [DEBUG] Raw data: {data}")
            
            # Get parameter type with fallback to string if not specified
            param_type = data.get('type', 'STRING')
            #print(f"    [DEBUG] Parameter type: {param_type}")
            
            # Create parameter dictionary
            param = {
                'name': name,
                'description': data.get('description', '').strip(),
                'type': param_type,
                'default': data.get('default', '')
            }
            #print(f"    [DEBUG] Initial param: {param}")
            
            # Handle different parameter types
            if param_type == 'INT':
                param['default'] = str(data.get('default', '0'))
                #print(f"    [DEBUG] Processed as INT, default: {param['default']}")
            elif param_type == 'FLOAT':
                param['default'] = str(data.get('default', '0.0'))
                #print(f"    [DEBUG] Processed as FLOAT, default: {param['default']}")
            elif param_type == 'BOOL':
                param['default'] = str(int(bool(data.get('default', '0'))))
                param['values'] = ['0', '1']
                #print(f"    [DEBUG] Processed as BOOL, default: {param['default']}")
            
            # Handle enums/dropdowns
            if 'values' in data and isinstance(data['values'], list):
                #print(f"    [DEBUG] Found values list: {data['values']}")
                param['values'] = []
                for value in data['values']:
                    if isinstance(value, dict):
                        if 'value' in value:
                            param['values'].append(str(value['value']))
                        elif 'name' in value:
                            param['values'].append(str(value['name']))
                    else:
                        param['values'].append(str(value))
                
                if param['values']:
                    param['type'] = 'ENUM'
                    #print(f"    [DEBUG] Set as ENUM with values: {param['values']}")
                    # If no default is set, use the first value as default
                    if not param['default'] and param['values']:
                        param['default'] = param['values'][0]
                        #print(f"    [DEBUG] Set default to first value: {param['default']}")
            
            # Handle min/max values if present
            if 'min' in data:
                param['min'] = str(data['min'])
                #print(f"    [DEBUG] Set min value: {param['min']}")
            if 'max' in data:
                param['max'] = str(data['max'])
                #print(f"    [DEBUG] Set max value: {param['max']}")
            
            # Add parameter if it has a valid type
            if param['type']:
                params.append(param)
                #print(f"    [DEBUG] Added parameter: {name} (type: {param_type})")
            else:
                print(f"    [WARNING] Skipping parameter {name} - invalid type")
                pass
        
        #print(f"\n[DEBUG] Extracted {len(params)} parameters in total")
        #for i, p in enumerate(params, 1):
        #    print(f"  {i}. {p['name']} ({p['type']}): {p.get('default', '')} - {p.get('description', '')}")
            
        return params
    
    def find_keywords_file(self):
        """Find the keywords JSON file in various possible locations."""
        #print("\n[DEBUG] Starting find_keywords_file()")
        
        # Get the workbench root directory
        workbench_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        #print(f"[DEBUG] Workbench root: {workbench_root}")
        
        # List of possible locations to check (in order of priority)
        possible_paths = [
            # Development path - gui/json in workbench root (OpenRadioss specific)
            os.path.join(workbench_root, 'gui', 'json', 'openradioss_keywords_with_parameters.json'),
            os.path.join(workbench_root, 'gui', 'json', 'openradioss_keywords_clean.json'),
            os.path.join(workbench_root, 'gui', 'json', 'keywords_with_parameters.json'),
            os.path.join(workbench_root, 'gui', 'json', 'keywords_clean.json'),
            
            # System-wide Flatpak path (if running in Flatpak)
            '/var/lib/flatpak/app/org.freecad.FreeCAD/current/active/files/FreeCAD/Mod/Fem_upgraded/gui/json/openradioss_keywords_with_parameters.json',
            '/var/lib/flatpak/app/org.freecad.FreeCAD/current/active/files/FreeCAD/Mod/Fem_upgraded/gui/json/openradioss_keywords_clean.json',
            '/var/lib/flatpak/app/org.freecad.FreeCAD/current/active/files/FreeCAD/Mod/Fem_upgraded/gui/json/keywords_with_parameters.json',
            '/var/lib/flatpak/app/org.freecad.FreeCAD/current/active/files/FreeCAD/Mod/Fem_upgraded/gui/json/keywords_clean.json',
            
            # Flatpak user data directory (less likely but possible)
            os.path.join(os.path.expanduser('~'), '.var/app/org.freecad.FreeCAD/data/FreeCAD/Mod/Fem_upgraded/gui/json/openradioss_keywords_with_parameters.json'),
            os.path.join(os.path.expanduser('~'), '.var/app/org.freecad.FreeCAD/data/FreeCAD/Mod/Fem_upgraded/gui/json/openradioss_keywords_clean.json'),
            os.path.join(os.path.expanduser('~'), '.var/app/org.freecad.FreeCAD/data/FreeCAD/Mod/Fem_upgraded/gui/json/keywords_with_parameters.json'),
            os.path.join(os.path.expanduser('~'), '.var/app/org.freecad.FreeCAD/data/FreeCAD/Mod/Fem_upgraded/gui/json/keywords_clean.json')
        ]
        
        #print("[DEBUG] Checking possible paths in order:")
        # Check each possible path in order
        for i, path in enumerate(possible_paths, 1):
            #print(f"[{i}] Checking: {path}")
            if path and os.path.exists(path):
                #print(f"[INFO] Found keywords file at: {path}")
                return path
            else:
                #print(f"[DEBUG]   Path does not exist")
                pass
                
        # Last resort: search the entire workbench directory
        #print("\n[WARNING] File not found in standard locations, searching workbench directory...")
        #print(f"[DEBUG] Starting recursive search in: {workbench_root}")
        
        found_files = []
        for root, dirs, files in os.walk(workbench_root):
            # Check for OpenRadioss specific files first
            if 'openradioss_keywords_with_parameters.json' in files:
                path = os.path.join(root, 'openradioss_keywords_with_parameters.json')
                found_files.append(('openradioss_keywords_with_parameters.json', path))
            if 'openradioss_keywords_clean.json' in files:
                path = os.path.join(root, 'openradioss_keywords_clean.json')
                found_files.append(('openradioss_keywords_clean.json', path))
            # Fall back to generic filenames
            if 'keywords_with_parameters.json' in files:
                path = os.path.join(root, 'keywords_with_parameters.json')
                found_files.append(('keywords_with_parameters.json', path))
            if 'keywords_clean.json' in files:
                path = os.path.join(root, 'keywords_clean.json')
                found_files.append(('keywords_clean.json', path))
        
        if found_files:
            #print("\n[DEBUG] Found the following matching files:")
            for i, (name, path) in enumerate(found_files, 1):
                #print(f"[{i}] {name} at: {path}")
                pass
            # Return the first found file
            return found_files[0][1]
                
        #print("[ERROR] No keywords JSON file found in any location")
        #print("[DEBUG] find_keywords_file() completed without finding file\n")
        return None

    def load_keywords(self):
        """Load and filter keywords using keywords_clean.json as a whitelist."""
        print("\n=== DEBUG: LOADING KEYWORDS ===")
        try:
            # 1. Load the whitelist (keywords_clean.json)
            clean_path = os.path.join(os.path.dirname(__file__), 'json', 'keywords_clean.json')
            print(f"[DEBUG] Loading whitelist from: {clean_path}")
            
            if not os.path.exists(clean_path):
                print(f"[DEBUG] ERROR: Whitelist file not found at {clean_path}")
                self.keywords = []
                return []

            with open(clean_path, 'r', encoding='utf-8') as f:
                whitelist_keywords = json.load(f)
                
            print(f"[DEBUG] Loaded {len(whitelist_keywords)} whitelist entries")
            
            # Create a set of whitelisted keyword names (uppercase for case-insensitive matching)
            whitelist_names = {kw.get('name', '').strip().upper() for kw in whitelist_keywords}
            whitelist_names = {name for name in whitelist_names if name}  # Remove empty strings
            
            print(f"[DEBUG] Extracted {len(whitelist_names)} unique keyword names from whitelist")

            # 2. Load the full keyword database with all parameters
            db_path = os.path.join(os.path.dirname(__file__), 'json', 'keep', 'keyword_database_results.json')
            print(f"[DEBUG] Loading keyword database from: {db_path}")
            
            if not os.path.exists(db_path):
                print(f"[DEBUG] ERROR: Keyword database not found at {db_path}")
                self.keywords = []
                return []
                
            with open(db_path, 'r', encoding='utf-8') as f:
                all_keywords = json.load(f)
                
            print(f"[DEBUG] Loaded {len(all_keywords)} keywords from database")
            
            # 3. Filter the full database based on the whitelist
            self.keywords = []
            for kw in all_keywords:
                kw_name = kw.get('name', '').strip()
                if kw_name and kw_name.upper() in whitelist_names:
                    self.keywords.append(kw)
            
            print(f"[DEBUG] After filtering: {len(self.keywords)} keywords match the whitelist")
            
            if self.keywords:
                print("[DEBUG] First few filtered keywords:")
                for kw in self.keywords[:5]:
                    params = kw.get('parameters', [])
                    print(f"  - {kw.get('name', 'Unnamed')} ({len(params)} parameters)")
            else:
                print("[DEBUG] No keywords matched the whitelist")
            
            # Update the UI with the filtered keywords
            self.update_category_list()
            
            return self.keywords

        except Exception as e:
            print(f"[DEBUG] Error in load_keywords: {str(e)}")
            import traceback
            traceback.print_exc()
            self.keywords = []
            return []
    
    def _load_keywords_file(self, filename):
        """Helper method to load a keywords file by name."""
        try:
            # Get the workbench root directory
            workbench_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Try to find the file in the gui/json directory
            json_path = os.path.join(workbench_root, 'gui', 'json', filename)
            
            if not os.path.exists(json_path):
                # Try the Flatpak system path
                json_path = f'/var/lib/flatpak/app/org.freecad.FreeCAD/current/active/files/FreeCAD/Mod/Fem_upgraded/gui/json/{filename}'
                
                if not os.path.exists(json_path):
                    # Try the Flatpak user data directory
                    json_path = os.path.join(
                        os.path.expanduser('~'),
                        '.var/app/org.freecad.FreeCAD/data/FreeCAD/Mod/Fem_upgraded/gui/json/',
                        filename
                    )
            
            if not os.path.exists(json_path):
                #print(f"[WARNING] Could not find {filename} in any known location")
                return None
                
            #print(f"[INFO] Loading {filename} from: {json_path}")
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except json.JSONDecodeError as e:
            #print(f"[ERROR] Error parsing {filename}: {str(e)}")
            return None
        except Exception as e:
            #print(f"[ERROR] Error loading {filename}: {str(e)}")
            return None

    def auto_load_from_cfg(self):
        """Automatically load keywords from CFG files on startup with comprehensive fallback."""
        #print("[AUTO_LOAD] Checking for available keyword sources...")
        # Priority 1: Try dynamic CFG loader first (most comprehensive)
        try:
            #print("[AUTO_LOAD] Attempting dynamic CFG loading...")

            cfg_loader_path = os.path.join(os.path.dirname(__file__), '..', 'dynamic_cfg_keyword_loader_fixed.py')
            if os.path.exists(cfg_loader_path):
                import sys
                parent_dir = os.path.dirname(os.path.dirname(__file__))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)

                import dynamic_cfg_keyword_loader_fixed as cfg_loader_module
                loader = cfg_loader_module.DynamicCfgKeywordLoader()
                keywords = loader.load_all_keywords()

                if keywords and len(keywords) > 0:
                    #print(f"[AUTO_LOAD] SUCCESS: Loaded {len(keywords)} keywords from dynamic CFG loader")
                    self.save_keywords_as_json(self._convert_cfg_to_editor_format(keywords))
                    return keywords
                else:
                    #print("[AUTO_LOAD] Dynamic CFG loader returned no keywords, trying fallback methods...")
                    pass
            else:
                #print(f"[AUTO_LOAD] Dynamic CFG loader not found at {cfg_loader_path}")
                pass
        except Exception as e:
            #print(f"[AUTO_LOAD] Dynamic CFG loading failed: {e}")
            pass

        # Priority 2: Try direct CFG parsing (fallback)
        try:
            #print("[AUTO_LOAD] Attempting direct CFG file parsing...")

            cfg_root = os.path.join(os.path.dirname(__file__), 'CFG_Openradioss', 'radioss2025')
            if os.path.exists(cfg_root):
                keywords = self.parse_cfg_files(cfg_root)
                if keywords and len(keywords) > 0:
                    #print(f"[AUTO_LOAD] SUCCESS: Loaded {len(keywords)} keywords from direct CFG parsing")
                    self.save_keywords_as_json(keywords)
                    return keywords
                else:
                    #print("[AUTO_LOAD] No keywords found in CFG files")
                    pass
            else:
                #print(f"[AUTO_LOAD] CFG directory not found at {cfg_root}")
                pass
        except Exception as e:
            #print(f"[AUTO_LOAD] Direct CFG parsing failed: {e}")
            pass

        # Priority 3: Try existing JSON files
        try:
            #print("[AUTO_LOAD] Attempting to load from existing JSON files...")

            # Try comprehensive format first
            json_path = os.path.join(os.path.dirname(__file__), 'json', 'comprehensive_hm_reader_keywords.json')
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    keywords = json.load(f)
                if keywords:
                    #print(f"[INFO] Loaded {len(keywords)} keywords from comprehensive HM reader format")
                    return keywords

            # Try enhanced format
            json_path = os.path.join(os.path.dirname(__file__), 'json', 'enhanced_hm_reader_keywords.json')
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    keywords = json.load(f)
                #print(f"[AUTO_LOAD] SUCCESS: Loaded {len(keywords)} keywords from enhanced JSON")
                return keywords

            #print("[AUTO_LOAD] No existing JSON files found")

        except Exception as e:
            #print(f"[AUTO_LOAD] JSON loading failed: {e}")
            pass

        # Final fallback: empty list
        #print("[AUTO_LOAD] All loading methods failed, starting with empty keyword list")
        #print("[AUTO_LOAD] Users can manually refresh from CFG files using File > Refresh menu")
        return []

    def auto_refresh_cfg_keywords(self):
        """Automatically refresh keywords from CFG files in the background."""
        #print("[AUTO_REFRESH] Starting background CFG refresh...")

        try:
            # Import and run the dynamic CFG loader
            import sys
            cfg_loader_path = os.path.join(os.path.dirname(__file__), '..', 'dynamic_cfg_keyword_loader_fixed.py')
            if os.path.exists(cfg_loader_path):
                parent_dir = os.path.dirname(os.path.dirname(__file__))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)

                import dynamic_cfg_keyword_loader_fixed as cfg_loader_module
                loader = cfg_loader_module.DynamicCfgKeywordLoader()
                keywords = loader.load_all_keywords()

                if keywords and len(keywords) > len(self.keywords):
                    #print(f"[AUTO_REFRESH] Found {len(keywords)} new keywords (current: {len(self.keywords)})")
                    self.keywords = keywords
                    self.save_keywords_as_json(self._convert_cfg_to_editor_format(keywords))
                    self.update_category_list()
                    self.update_keyword_list()

                    # Show notification if significant number of new keywords
                    #if len(keywords) > len(self.keywords) + 10:
                        #print(f"[AUTO_REFRESH] Notifying user of {len(keywords)} keywords available")
                        # Could add a notification here if needed
                #else:
                    #print(f"[AUTO_REFRESH] No new keywords found (current: {len(self.keywords)})")
            else:
                #print(f"[AUTO_REFRESH] Dynamic CFG loader not available")
                pass

        except Exception as e:
            #print(f"[AUTO_REFRESH] Background refresh failed: {e}")
            pass

    def start_auto_refresh_timer(self):
        """Start automatic background refresh timer for CFG keywords."""
        try:
            from PySide2.QtCore import QTimer
            self.auto_refresh_timer = QTimer(self)
            self.auto_refresh_timer.timeout.connect(self._check_cfg_updates)
            # Check every 5 minutes (300,000 milliseconds)
            self.auto_refresh_timer.start(300000)
            #print("[AUTO_REFRESH] Started automatic background refresh timer (5-minute intervals)")
        except Exception as e:
            #print(f"[AUTO_REFRESH] Could not start timer: {e}")
            pass

    def _check_cfg_updates(self):
        """Check for CFG updates in the background (called by timer)."""
        #print("[AUTO_REFRESH] Checking for CFG updates...")
        try:
            # Import and run the dynamic CFG loader
            import sys
            cfg_loader_path = os.path.join(os.path.dirname(__file__), '..', 'dynamic_cfg_keyword_loader_fixed.py')
            if os.path.exists(cfg_loader_path):
                parent_dir = os.path.dirname(os.path.dirname(__file__))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)

                import dynamic_cfg_keyword_loader_fixed as cfg_loader_module
                loader = cfg_loader_module.DynamicCfgKeywordLoader()
                keywords = loader.load_all_keywords()

                if keywords and len(keywords) > len(self.keywords):
                    #print(f"[AUTO_REFRESH] Found {len(keywords)} new keywords (current: {len(self.keywords)})")
                    self.keywords = keywords
                    self.save_keywords_as_json(self._convert_cfg_to_editor_format(keywords))
                    self.update_category_list()
                    self.update_keyword_list()

                    # Show notification if significant number of new keywords
                    if len(keywords) > len(self.keywords) + 10:
                        #print(f"[AUTO_REFRESH] Notifying user of {len(keywords)} keywords available")
                        # Could add a notification here if needed
                        pass
                else:
                    #print(f"[AUTO_REFRESH] No new keywords found (current: {len(self.keywords)})")
                    pass
            else:
                #print(f"[AUTO_REFRESH] Dynamic CFG loader not available")
                pass

        except Exception as e:
            #print(f"[AUTO_REFRESH] Background refresh failed: {e}")
            pass

    def load_settings(self):
        """Load user settings from file."""
        try:
            settings_file = os.path.join(os.path.dirname(__file__), 'json', 'openradioss_keyword_editor_settings.json')
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    self.template_mode = settings.get('template_mode', 'full')
        except Exception as e:
            #print(f"[WARNING] Could not load settings: {e}")
            self.template_mode = 'full'

    def save_settings(self):
        """Save user settings to file."""
        try:
            # Ensure json directory exists
            json_dir = os.path.join(os.path.dirname(__file__), 'json')
            os.makedirs(json_dir, exist_ok=True)
            
            settings_file = os.path.join(json_dir, 'openradioss_keyword_editor_settings.json')
            settings = {
                'template_mode': self.template_mode
            }
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            #print(f"[WARNING] Could not save settings: {e}")
            pass

    def configure_template_mode(self):
        """Allow user to configure template mode."""
        modes = ["Minimal", "Basic", "Full"]
        current_index = {"minimal": 0, "basic": 1, "full": 2}[self.template_mode]

        mode, ok = QInputDialog.getItem(self, "Template Mode",
                                      "Select template complexity level:",
                                      modes, current_index, False)

        if ok:
            old_mode = self.template_mode
            self.template_mode = mode.lower()

            # Update UI based on new mode
            self.update_template_menu()

            # Save settings
            self.save_settings()

            QMessageBox.information(self, "Template Mode Changed",
                                  f"Template mode changed from {old_mode.title()} to {mode}.\n\n"
                                  "The template menu will now show only templates appropriate for this mode.")

    def update_template_menu(self):
        """Update template menu based on current template mode."""
        # This method will be called after mode changes to update menu visibility
        # For now, we'll keep all templates available but could filter them here
        pass

    def on_category_changed(self, index):
        """Handle category selection change."""
        self.update_keyword_list()

    def on_keyword_selected(self, item):
        """Handle keyword selection from the list by showing documentation in embedded browser."""
        if not item:
            return
            
        keyword_name = item.text()
        #print(f"[DEBUG] Keyword selected: {keyword_name}")
        
        # Get the keyword data stored in the item's UserRole
        self.current_keyword = item.data(QtCore.Qt.UserRole)
        if not self.current_keyword:
            #print(f"[ERROR] No data found for keyword: {keyword_name}")
            return
            
        #print(f"[DEBUG] Selected keyword: {self.current_keyword.get('name', 'Unknown')}")
        #print(f"[DEBUG] Keyword data keys: {list(self.current_keyword.keys())}")
        
        # Get documentation URL from various possible locations
        doc_url = None
        
        # 1. Check clean keywords first as they have the most reliable data
        clean_kw = self.clean_keywords.get(keyword_name, {})
        if 'documentation' in clean_kw and clean_kw['documentation']:
            doc_url = clean_kw['documentation']
            #print(f"[DEBUG] Found documentation in clean keywords: {doc_url}")
            
        # 2. Check if we already have a formatted URL
        if not doc_url and 'formatted_doc_url' in self.current_keyword and self.current_keyword['formatted_doc_url']:
            doc_url = self.current_keyword['formatted_doc_url']
            #print(f"[DEBUG] Using pre-formatted URL: {doc_url}")
            
        # 3. Check documentation field in current keyword
        if not doc_url and 'documentation' in self.current_keyword and self.current_keyword['documentation']:
            doc_url = self.current_keyword['documentation']
            #print(f"[DEBUG] Found documentation in current keyword: {doc_url}")
            
        # 4. Check web_link in clean keywords as fallback
        if not doc_url and 'web_link' in clean_kw and clean_kw['web_link']:
            doc_url = clean_kw['web_link']
            #print(f"[DEBUG] Found web_link in clean keywords: {doc_url}")
        
        # Format the URL if we found one
        if doc_url:
            # If it's a relative URL, prepend the base URL
            if not doc_url.startswith(('http://', 'https://')):
                base_url = "https://help.altair.com/hwsolvers/rad/topics/solvers/rad/"
                
                # Special handling for material keywords
                if keyword_name.startswith('*MAT_'):
                    # For material cards, use the material documentation page with anchor
                    # Extract material number - handle different formats like *MAT_001, *MAT_ELASTIC, etc.
                    mat_part = keyword_name[5:]  # Remove '*MAT_'
                    
                    # If it's a numeric material (e.g., *MAT_001), extract just the number
                    if mat_part and mat_part[0].isdigit():
                        mat_num = ''
                        for c in mat_part:
                            if c.isdigit():
                                mat_num += c
                            else:
                                break
                        if mat_num:  # If we found a number, use it
                            doc_url = f"{base_url}mat_ls-dyna_r.htm#material_{mat_num}"
                            #print(f"[DEBUG] Formatted numeric material documentation URL: {doc_url}")
                        else:
                            # Fallback to using the full material name
                            anchor = keyword_name.strip('*').lower()
                            anchor = ''.join(c if c.isalnum() else '_' for c in anchor)
                            doc_url = f"{base_url}{anchor}_lsdyna_r.htm"
                            #print(f"[DEBUG] Formatted named material documentation URL: {doc_url}")
                    else:
                        # For named materials (e.g., *MAT_ELASTIC), use the standard format
                        anchor = keyword_name.strip('*').lower()
                        anchor = ''.join(c if c.isalnum() else '_' for c in anchor)
                        doc_url = f"{base_url}{anchor}_lsdyna_r.htm"
                        #print(f"[DEBUG] Formatted named material documentation URL: {doc_url}")
                else:
                    # For non-material keywords, use the standard format
                    anchor = keyword_name.strip('*').lower()
                    # Replace special characters with underscores
                    anchor = ''.join(c if c.isalnum() else '_' for c in anchor)
                    doc_url = f"{base_url}{anchor}_lsdyna_r.htm"
                    #print(f"[DEBUG] Formatted standard documentation URL: {doc_url}")
            
            # Store the formatted URL back in the keyword data
            self.current_keyword['formatted_doc_url'] = doc_url
            #print(f"[DEBUG] Stored formatted URL in keyword data")
        else:
            # Try to generate a default URL for known keyword types
            base_url = "https://help.altair.com/hwsolvers/rad/topics/solvers/rad/"
            
            if keyword_name.startswith('*MAT_'):
                # For material cards - handle both numeric and named materials
                mat_part = keyword_name[5:]  # Remove '*MAT_'
                
                # If it's a numeric material (e.g., *MAT_001), extract just the number
                if mat_part and mat_part[0].isdigit():
                    mat_num = ''
                    for c in mat_part:
                        if c.isdigit():
                            mat_num += c
                        else:
                            break
                    if mat_num:  # If we found a number, use it
                        doc_url = f"{base_url}mat_ls-dyna_r.htm#material_{mat_num}"
                        #print(f"[DEBUG] Generated default numeric material documentation URL: {doc_url}")
                
                # If we don't have a URL yet, try the named material approach
                if not doc_url:
                    anchor = keyword_name.strip('*').lower()
                    anchor = ''.join(c if c.isalnum() else '_' for c in anchor)
                    doc_url = f"{base_url}{anchor}_lsdyna_r.htm"
                    #print(f"[DEBUG] Generated default named material documentation URL: {doc_url}")
                    
            elif keyword_name.startswith('*'):
                # For other keywords, try the standard format
                anchor = keyword_name.strip('*').lower()
                anchor = ''.join(c if c.isalnum() else '_' for c in anchor)
                doc_url = f"{base_url}{anchor}_lsdyna_r.htm"
                #print(f"[DEBUG] Generated default documentation URL: {doc_url}")
            
            if doc_url:
                # Store the generated URL for future use
                self.current_keyword['formatted_doc_url'] = doc_url
        
        # #print clean keywords for this keyword
        clean_kw = self.clean_keywords.get(keyword_name, {})
        #print(f"[DEBUG] Clean keyword data: {clean_kw}")
        
        # Load full keyword details
        keyword_details = self.load_keyword_details(keyword_name)
        if keyword_details:
            # Update the UI with the keyword details
            self.update_keyword_ui(keyword_details)
        
        # Enable the cache button when a keyword is selected
        if hasattr(self, 'cache_button'):
            self.cache_button.setEnabled(True)
            
        # Enable the help button if there's documentation
        if hasattr(self, 'help_button'):
            help_enabled = bool(doc_url)
            self.help_button.setEnabled(help_enabled)
            #print(f"[DEBUG] Help button enabled: {help_enabled}")
        
        # If there's a documentation URL, log it
        if doc_url:
            #print(f"[DEBUG] Documentation available for {keyword_name} at {doc_url}")
            pass
        else:
            #print(f"[DEBUG] No documentation URL found for {keyword_name}")
            pass

    def _build_cfg_keyword_map(self, cfg_keywords):
        """Build optimized lookup maps for CFG keywords."""
        # Primary map: lowercase name -> keyword
        name_map = {}
        
        # Secondary maps for common variations
        no_underscore_map = {}  # name_without_underscores -> keyword
        no_prefix_map = {}      # name_without_prefix -> keyword
        alt_name_map = {}       # alternative_name -> keyword
        
        for kw in cfg_keywords:
            name = kw.get('name', '').strip()
            if not name:
                continue
                
            # Primary lookup with exact case-insensitive match
            name_lower = name.lower()
            name_map[name_lower] = kw
            
            # Common variations for flexible matching
            no_underscore = name_lower.replace('_', '')
            no_prefix = name_lower.split('_', 1)[-1] if '_' in name_lower else name_lower
            
            if no_underscore != name_lower:
                no_underscore_map[no_underscore] = kw
                
            if no_prefix != name_lower:
                no_prefix_map[no_prefix] = kw
                
            # Handle common alternative naming patterns
            if name_lower.startswith('*mat_'):
                # For material cards, create an entry without the material number
                base_name = '*mat_' + '_'.join(name_lower.split('_')[1:])
                if base_name != name_lower:
                    alt_name_map[base_name] = kw
                    
        return {
            'exact': name_map,
            'no_underscore': no_underscore_map,
            'no_prefix': no_prefix_map,
            'alt_names': alt_name_map
        }

    def _find_cfg_keyword(self, name, cfg_maps):
        """Find a keyword in CFG maps with flexible matching."""
        if not name:
            return None
            
        name = name.strip().lower()
        
        # Try exact match first
        if name in cfg_maps['exact']:
            return cfg_maps['exact'][name]
            
        # Try without underscores
        no_underscore = name.replace('_', '')
        if no_underscore in cfg_maps['no_underscore']:
            return cfg_maps['no_underscore'][no_underscore]
            
        # Try without prefix
        if '_' in name:
            no_prefix = name.split('_', 1)[-1]
            if no_prefix in cfg_maps['no_prefix']:
                return cfg_maps['no_prefix'][no_prefix]
                
        # Try alternative names
        if name in cfg_maps['alt_names']:
            return cfg_maps['alt_names'][name]
            
        return None

    def clean_keyword_name(self, keyword):
        """Clean and normalize a keyword name from the database.
        
        Args:
            keyword: Raw keyword string from the database
            
        Returns:
            Cleaned and normalized keyword name, or None if invalid
        """
        if not keyword or not isinstance(keyword, str):
            return None
            
        # Remove comments (everything after //)
        keyword = keyword.split('//')[0].strip()
        
        # Handle multi-line keywords (take the last line)
        if '\n' in keyword:
            lines = [line.strip() for line in keyword.split('\n') if line.strip()]
            if lines:
                keyword = lines[-1]  # Take the last non-empty line
        
        # Remove any remaining whitespace and normalize
        keyword = ' '.join(keyword.split())
        
        # Only return if it looks like a valid keyword
        return keyword if keyword.startswith('*') else None

    def filter_keywords_by_whitelist(self, base_keywords):
        """Filter keywords to only include those present in the whitelist (keywords_clean.json)."""
        print("\n=== DEBUG: STARTING KEYWORD FILTERING ===")
        print(f"[DEBUG] Received {len(base_keywords)} keywords to filter")
        
        try:
            # Load the whitelist
            whitelist_path = os.path.join(os.path.dirname(__file__), 'json', 'keywords_clean.json')
            print(f"[DEBUG] Loading whitelist from: {whitelist_path}")
            
            if not os.path.exists(whitelist_path):
                print("[DEBUG] ERROR: Whitelist file not found!")
                return base_keywords
                
            with open(whitelist_path, 'r', encoding='utf-8') as f:
                whitelist = json.load(f)
            
            print(f"[DEBUG] Loaded whitelist with {len(whitelist)} entries")
            
            # Build whitelist names with cleaning
            whitelist_names = set()
            print("\n[DEBUG] Processing whitelist entries:")
            for i, kw in enumerate(whitelist, 1):
                name = kw.get('name', '').strip()
                clean_name = self.clean_keyword_name(name)
                print(f"  [WHITELIST] {i:3d}. Original: {repr(name):<40} Cleaned: {repr(clean_name)}")
                if clean_name:
                    whitelist_names.add(clean_name.upper())
            
            print(f"\n[DEBUG] Total whitelist entries after cleaning: {len(whitelist_names)}")
            print("[DEBUG] First 10 whitelist names:")
            for i, name in enumerate(sorted(list(whitelist_names))[:10], 1):
                print(f"  {i:2d}. {name}")
            
            # Process base keywords
            filtered_keywords = []
            print(f"\n[DEBUG] Processing {len(base_keywords)} input keywords:")
            
            for i, kw in enumerate(base_keywords, 1):
                kw_name = kw.get('name', '').strip()
                clean_kw_name = self.clean_keyword_name(kw_name)
                
                if i <= 5 or i % 50 == 0:  # Show first 5 and then every 50th for brevity
                    print(f"\n[DEBUG] {i:4d}/{len(base_keywords)}. Processing keyword:")
                    print(f"  [KEYWORD] Original: {repr(kw_name)}")
                    print(f"  [KEYWORD] Cleaned: {repr(clean_kw_name)}")
                
                if not clean_kw_name:
                    if i <= 5:  # Only show first few skips to avoid too much output
                        print("  [FILTER] -> Invalid keyword, skipping")
                    continue
                
                clean_upper = clean_kw_name.upper()
                
                if i <= 5 or i % 50 == 0:  # Show first 5 and then every 50th for brevity
                    print(f"  [FILTER] Checking if '{clean_upper}' is in whitelist...")
                
                if clean_upper in whitelist_names:
                    if i <= 5:  # Only show first few matches to avoid too much output
                        print("  [FILTER] -> MATCH FOUND in whitelist!")
                    kw['name'] = clean_kw_name
                    filtered_keywords.append(kw)
                else:
                    if i <= 5:  # Only show first few non-matches to avoid too much output
                        print(f"  [FILTER] -> Not in whitelist (looking for: {clean_upper})")
            
            print(f"\n=== DEBUG: FILTERING COMPLETE ===")
            print(f"[DEBUG] Total input keywords: {len(base_keywords)}")
            print(f"[DEBUG] Keywords after filtering: {len(filtered_keywords)}")
            print(f"[DEBUG] Whitelist size: {len(whitelist_names)}")
            print(f"[DEBUG] First 5 filtered keywords: {[k.get('name') for k in filtered_keywords[:5]]}")
            
            return filtered_keywords if filtered_keywords else base_keywords
            
        except Exception as e:
            #print(f"\n[ERROR] in filter_keywords_by_whitelist: {str(e)}")
            import traceback
            traceback.print_exc()
            return base_keywords

        
    def load_keywords(self):
        """Load and filter keywords using keywords_clean.json."""
        print("\n=== DEBUG: LOADING KEYWORDS ===")
        try:
            # Load the filtered keywords from keywords_clean.json
            clean_path = os.path.join(os.path.dirname(__file__), 'json', 'keywords_clean.json')
            print(f"[DEBUG] Loading filtered keywords from: {clean_path}")
            
            if not os.path.exists(clean_path):
                print(f"[DEBUG] ERROR: Keywords file not found at {clean_path}")
                return []

            with open(clean_path, 'r', encoding='utf-8') as f:
                filtered_keywords = json.load(f)
                
            print(f"[DEBUG] Loaded {len(filtered_keywords)} filtered keywords")
            
            # Debug output for first few keywords
            if filtered_keywords:
                print("[DEBUG] First few filtered keywords:")
                for kw in filtered_keywords[:5]:
                    params = kw.get('parameters', [])
                    print(f"  - {kw.get('name', 'Unnamed')} ({len(params)} parameters)")
            
            return filtered_keywords

        except Exception as e:
            print(f"[DEBUG] Error in load_keywords: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def filter_keywords_with_documentation(self, keywords, json_keywords):
        """Filter keywords to only include those with documentation.
        
        This method filters the provided keywords to only include those that have
        corresponding documentation in the json_keywords list. It handles various
        naming conventions and formats to maximize matches.
        
        Args:
            keywords: List of keyword dictionaries to filter
            json_keywords: List of keyword dictionaries with documentation
            
        Returns:
            List of filtered keyword dictionaries with merged documentation
        """
        if not keywords:
            #print("[DEBUG] No keywords to filter")
            return []
            
        if not json_keywords:
            #print("[DEBUG] No JSON keywords provided for filtering")
            return keywords  # Return all keywords if no JSON data is available
            
        #print(f"[DEBUG] Filtering {len(keywords)} keywords against {len(json_keywords)} documented keywords")
        
        # Create a dict of normalized keyword names to their documentation
        documented_keywords = {}
        
        # Pre-process all documented keywords for faster lookup
        for kw in json_keywords:
            # Get all possible name variations for this keyword
            names = set()
            
            # Add both name and title fields if they exist
            for field in ['name', 'title']:
                if field in kw and kw[field]:
                    name = kw[field]
                    # Add exact name
                    names.add(name)
                    # Add normalized version (uppercase, no leading *)
                    normalized = name.lstrip('*').upper()
                    names.add(normalized)
                    # Add with/without leading *
                    if not name.startswith('*'):
                        names.add('*' + name)
                    else:
                        names.add(name[1:])
            
            # Add all variations to our lookup dict
            for name in names:
                if name:  # Only add non-empty names
                    documented_keywords[name] = kw
        
        #print(f"[DEBUG] Created lookup with {len(documented_keywords)} keyword variations")
        
        # Filter keywords to only those with documentation
        filtered = []
        not_found = []
        
        for kw in keywords:
            # Get all possible names for this keyword
            kw_names = set()
            
            # Add both name and title fields if they exist
            for field in ['name', 'title']:
                if field in kw and kw[field]:
                    name = kw[field]
                    # Add exact name
                    kw_names.add(name)
                    # Add normalized version (uppercase, no leading *)
                    normalized = name.lstrip('*').upper()
                    kw_names.add(normalized)
                    # Add with/without leading *
                    if not name.startswith('*'):
                        kw_names.add('*' + name)
                    else:
                        kw_names.add(name[1:])
            
            # Check if any of the name variations match a documented keyword
            found_match = False
            doc_kw = None
            
            for name in kw_names:
                if name in documented_keywords:
                    found_match = True
                    doc_kw = documented_keywords[name]
                    break
            
            if found_match and doc_kw:
                # Create a new dict to avoid modifying the original
                new_kw = kw.copy()
                
                # Debug info for non-exact matches
                if 'name' in kw and doc_kw.get('name', '').upper() != kw['name'].upper():
                    #print(f"[DEBUG] Matched '{kw.get('name')}' with documentation for '{doc_kw.get('name', '')}'")
                    pass
                
                # Merge documentation from JSON if available
                new_kw.update({
                    'description': doc_kw.get('description', kw.get('description', '')),
                    'documentation': doc_kw.get('documentation', kw.get('documentation', '')),
                    'category': doc_kw.get('category', kw.get('category', 'General')),
                    # Keep the original source if it exists
                    'source': kw.get('source', doc_kw.get('source', 'unknown'))
                })
                
                # If the JSON has parameters and our keyword doesn't, or has empty parameters, use them
                if 'parameters' in doc_kw and (not kw.get('parameters') or not kw['parameters']):
                    new_kw['parameters'] = doc_kw['parameters']
                
                filtered.append(new_kw)
            else:
                not_found.append(kw.get('name', 'Unknown'))
        
        # #print summary of missing documentation
        if not_found:
            #print(f"[DEBUG] Could not find documentation for {len(not_found)} keywords. Examples:")
            for name in not_found[:10]:  # Show first 10 missing
                #print(f"  - {name}")
                pass
            if len(not_found) > 10:
                #print(f"  ... and {len(not_found) - 10} more")
                pass
        
        #print(f"[DEBUG] Filtered {len(filtered)}/{len(keywords)} keywords with documentation")
        return filtered

    def save_keywords_as_json(self, keywords):
        """Save keywords as JSON for faster loading next time (comprehensive format with format tags)."""
        try:
            # Ensure json directory exists
            json_dir = os.path.join(os.path.dirname(__file__), 'json')
            os.makedirs(json_dir, exist_ok=True)
            
            # Save comprehensive format as primary
            comprehensive_file = os.path.join(json_dir, 'comprehensive_hm_reader_keywords.json')
            with open(comprehensive_file, 'w', encoding='utf-8') as f:
                json.dump(keywords, f, indent=2, ensure_ascii=False)

            # Also save enhanced HM reader format for compatibility
            enhanced_file = os.path.join(json_dir, 'enhanced_hm_reader_keywords.json')
            with open(enhanced_file, 'w', encoding='utf-8') as f:
                json.dump(keywords, f, indent=2, ensure_ascii=False)

            # Also save basic HM reader format for compatibility
            basic_hm_file = os.path.join(json_dir, 'hm_reader_keywords.json')
            with open(basic_hm_file, 'w', encoding='utf-8') as f:
                json.dump(keywords, f, indent=2, ensure_ascii=False)

            # Also save basic format for compatibility
            basic_keywords = []
            for kw in keywords:
                basic_kw = {
                    'name': kw.get('name', ''),
                    'category': kw.get('category', 'General'),
                    'title': kw.get('title', ''),
                    'description': kw.get('description', ''),
                    'source_file': kw.get('source_file', ''),
                    'parameters': kw.get('parameters', [])
                }
                basic_keywords.append(basic_kw)

            # Create json directory if it doesn't exist
            json_dir = os.path.join(os.path.dirname(__file__), 'json')
            os.makedirs(json_dir, exist_ok=True)
            
            # Save clean version
            clean_file = os.path.join(json_dir, 'openradioss_keywords_clean.json')
            with open(clean_file, 'w', encoding='utf-8') as f:
                json.dump(basic_keywords, f, indent=2, ensure_ascii=False)

            # Save detailed version with parameters
            detailed_file = os.path.join(json_dir, 'openradioss_keywords_with_parameters.json')
            with open(detailed_file, 'w', encoding='utf-8') as f:
                json.dump(keywords, f, indent=2, ensure_ascii=False)

            #print(f"[INFO] Saved {len(keywords)} keywords in comprehensive format with format detection")

        except Exception as e:
            #print(f"[WARNING] Could not save keywords to JSON: {e}")
            pass

    def refresh_keywords_from_cfg(self):
        """Refresh keywords using dynamic CFG file loading (no hardcoded data)."""
        #print("[INFO] Refreshing keywords using dynamic CFG file loading...")

        try:
            # Import and run the dynamic CFG loader
            import sys
            cfg_loader_path = os.path.join(os.path.dirname(__file__), '..', 'dynamic_cfg_keyword_loader_fixed.py')
            if os.path.exists(cfg_loader_path):
                # Add the parent directory to sys.path for imports
                parent_dir = os.path.dirname(os.path.dirname(__file__))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)

                # Import the dynamic loader
                import dynamic_cfg_keyword_loader_fixed as cfg_loader_module

                # Create loader and load keywords
                loader = cfg_loader_module.DynamicCfgKeywordLoader()
                keywords = loader.load_all_keywords()

                if keywords:
                    self.keywords = keywords

                    # Save in editor-compatible format
                    editor_keywords = self._convert_cfg_to_editor_format(keywords)
                    self.save_keywords_as_json(editor_keywords)

                    self.update_category_list()
                    self.update_keyword_list()
                    self.show_welcome_message()

                    # Count by category for user information
                    category_counts = {}
                    for kw in self.keywords:
                        cat = kw.get('category', 'General')
                        category_counts[cat] = category_counts.get(cat, 0) + 1

                    QMessageBox.information(self, "Keywords Refreshed",
                                          f"Successfully refreshed {len(self.keywords)} keywords using dynamic CFG loading!\n\n"
                                          "The keyword database now includes:\n"
                                          f"• {category_counts.get('Materials', 0)} material keywords with complete parameter definitions\n"
                                          f"• {category_counts.get('Control Cards', 0)} control card keywords with format specifications\n"
                                          f"• {category_counts.get('Properties', 0)} property keywords with solver compatibility\n"
                                          f"• {category_counts.get('Loads', 0)} load keywords with entity targeting\n"
                                          f"• {category_counts.get('Contact', 0)} contact keywords with friction properties\n"
                                          "• All keywords loaded dynamically from CFG files (no hardcoded data)\n"
                                          "• Complete LS-DYNA syntax generation with format cards\n"
                                          "• Parameter validation and type checking")
                else:
                    QMessageBox.warning(self, "No Keywords Found",
                                      "No keywords were found using dynamic CFG loading.\n\n"
                                      "Please check that CFG files are available in the expected locations.")
            else:
                QMessageBox.warning(self, "CFG Loader Not Found",
                                  f"Dynamic CFG loader not found at:\n{cfg_loader_path}\n\n"
                                  "Please ensure the dynamic_cfg_keyword_loader_fixed.py file exists.")

        except Exception as e:
            QMessageBox.critical(self, "Refresh Error",
                               f"Failed to refresh keywords using dynamic CFG loader:\n{str(e)}")
            #print(f"[ERROR] Dynamic CFG refresh failed: {e}")

    def _clean_description(self, description):
        """Clean up the keyword description."""
        if not description:
            return "No description available."

        # Remove any copyright notices
        if '  ' in description:
            description = description.split('  ')[0].strip()

    def show_examples_section(self, section_name):
        """Show examples section in the description tab."""
        examples_html = {
            "latest": """
            <div style="padding: 20px;">
                <h2>Latest OpenRadioss Examples</h2>
                <p>Recent examples showcasing advanced OpenRadioss features:</p>
                <ul>
                    <li><strong>Crash Analysis:</strong> Full vehicle crash simulation with airbag deployment</li>
                    <li><strong>Forming:</strong> Sheet metal forming with adaptive remeshing</li>
                    <li><strong>Impact:</strong> Bird strike analysis on aircraft components</li>
                    <li><strong>Multiphysics:</strong> Fluid-structure interaction examples</li>
                </ul>
                <p>These examples demonstrate the latest solver capabilities and modeling techniques.</p>
            </div>
            """,
            "introductory": """
            <div style="padding: 20px;">
                <h2>Introductory Examples</h2>
                <p>Basic examples to help you get started with OpenRadioss:</p>
                <ul>
                    <li><strong>Simple Beam:</strong> Linear static analysis of a cantilever beam</li>
                    <li><strong>Plate with Hole:</strong> Stress concentration analysis</li>
                    <li><strong>Drop Test:</strong> Basic impact simulation</li>
                    <li><strong>Modal Analysis:</strong> Natural frequency calculation</li>
                </ul>
                <p>Perfect for learning the fundamentals of OpenRadioss modeling.</p>
            </div>
            """,
            "implicit": """
            <div style="padding: 20px;">
                <h2>Implicit Analysis Examples</h2>
                <p>Examples demonstrating implicit solution methods:</p>
                <ul>
                    <li><strong>Linear Static:</strong> Static structural analysis</li>
                    <li><strong>Modal Analysis:</strong> Eigenvalue extraction</li>
                    <li><strong>Nonlinear Static:</strong> Large deformation analysis</li>
                    <li><strong>Steady-State Thermal:</strong> Heat transfer analysis</li>
                </ul>
                <p>These examples show proper setup for implicit simulations.</p>
            </div>
            """,
            "openradioss": """
            <div style="padding: 20px;">
                <h2>OpenRadioss Examples</h2>
                <p>Comprehensive examples specific to OpenRadioss features:</p>
                <ul>
                    <li><strong>Material Models:</strong> Advanced material law implementations</li>
                    <li><strong>Contact Algorithms:</strong> Various contact type demonstrations</li>
                    <li><strong>ALE Methods:</strong> Arbitrary Lagrangian-Eulerian examples</li>
                    <li><strong>SPH:</strong> Smoothed Particle Hydrodynamics</li>
                    <li><strong>Multiphysics:</strong> Coupled thermal-mechanical analysis</li>
                </ul>
                <p>These examples highlight OpenRadioss-specific capabilities and best practices.</p>
            </div>
            """
        }

        html_content = examples_html.get(section_name, """
        <div style="padding: 20px;">
            <h2>Examples</h2>
            <p>No examples available for this section.</p>
        </div>
        """)

        if hasattr(self, 'desc_tab'):
            self.desc_tab.setHtml(html_content)

        # Switch to description tab
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setCurrentWidget(self.desc_tab)

    def update_category_list(self):
        """Update the category dropdown with unique categories from keywords."""
        if not self.keywords:
            return

        categories = set()
        for kw in self.keywords:
            if 'category' in kw:
                categories.add(kw['category'])

        self.category_combo.clear()
        self.category_combo.addItem("All Categories")
        self.category_combo.addItems(sorted(categories))

    def update_keyword_list(self):
        """Update the keyword list based on the selected category."""
        if not self.keywords:
            #print("[DEBUG] update_keyword_list: No keywords available")
            return

        current_category = self.category_combo.currentText()
        #print(f"[DEBUG] update_keyword_list: Updating for category: {current_category}")
        #print(f"[DEBUG] Total keywords: {len(self.keywords)}")
        
        # Debug: #print first few keywords
        #print("[DEBUG] First 5 keywords:")
        for i, kw in enumerate(self.keywords[:5]):
            #print(f"  {i+1}. Name: {kw.get('name', 'N/A')!r}")
            #print(f"     Display: {kw.get('display_name', 'N/A')!r}")
            #print(f"     Category: {kw.get('category', 'N/A')}")
            pass
        
        self.keywords_list.clear()
        added_count = 0

        for kw in self.keywords:
            if current_category == "All Categories" or kw.get('category') == current_category:
                # Use display_name if available, otherwise use the original name
                display_name = kw.get('display_name', kw.get('name', 'Unnamed'))
                
                # Debug output for first 5 items
                if added_count < 5:
                    #print(f"[DEBUG] Adding item {added_count+1}:")
                    #print(f"  Name: {kw.get('name', 'N/A')!r}")
                    #print(f"  Display name: {display_name!r}")
                    #print(f"  Category: {kw.get('category', 'N/A')}")
                    pass
                
                item = QListWidgetItem(display_name)
                item.setData(QtCore.Qt.UserRole, kw)  # Store the full keyword data
                self.keywords_list.addItem(item)
                added_count += 1
                
                if added_count == 5:  # Only show first 5 for brevity
                    #print("[DEBUG] ... and more items ...")
                    pass

        # Connect the item selection signal
        self.keywords_list.itemClicked.connect(self.on_keyword_selected)

    def show_keyword_list_view(self):
        """Switch back to the keyword list view."""
        if hasattr(self, 'stacked_widget'):
            self.stacked_widget.setCurrentIndex(0)
        if hasattr(self, 'back_button'):
            self.back_button.setVisible(False)

    def show_web_view(self, url, section=None, scroll_lines=0):
        """Show the web view with the given URL using DocumentationViewer.

        Args:
            url: The URL to load
            section: Optional section ID to scroll to
            scroll_lines: Number of lines to scroll down after loading
        """
        if not hasattr(self, '_doc_viewer'):
            self._doc_viewer = DocumentationViewer(self)
            # Note: DocumentationViewer doesn't need back button connection
            # as it's a separate dialog for viewing documentation

        self._doc_viewer.show_documentation(url, section=section, scroll_lines=scroll_lines)
        self._doc_viewer.show()
        self._doc_viewer.raise_()
        self._doc_viewer.activateWindow()

    def show_help_section(self, section_name, scroll_lines=None):
        """Show a specific help section and scroll to the OpenRadioss Input section.

        Args:
            section_name: Name of the section to show (e.g., 'search_help', 'tutorials')
            scroll_lines: Number of lines to scroll down (default: None, uses preset values)
        """
        base_url = "https://2021.help.altair.com/2021/hwsolvers/rad/topics/solvers/rad"

        # Define scroll positions for each section to align OpenRadioss Input at the top
        section_scrolls = {
            "search_help": 1800,
            "whats_new": 1500,
            "overview": 1200,
            "tutorials": 1000,
            "user_guide": 2000,
            "reference_guide": 2500,
            "example_guide": 800,
            "verification": 800,
            "faq": 700,
            "theory": 1800,
            "subroutines": 1500,
            "starter": 2000,
            "engine": 2000,
            "index": 1200
        }

        section_map = {
            "search_help": "search_help_openradioss_r.htm",
            "whats_new": "whats_new_openradioss_r.htm",
            "overview": "overview_openradioss_r.htm",
            "tutorials": "tutorials_openradioss_r.htm",
            "user_guide": "user_guide_openradioss_r.htm",
            "reference_guide": "reference_guide_openradioss_r.htm",
            "example_guide": "example_guide_openradioss_r.htm",
            "verification": "verification_problems_openradioss_r.htm",
            "faq": "faq_openradioss_r.htm",
            "theory": "theory_manual_openradioss_r.htm",
            "subroutines": "user_subroutines_openradioss_r.htm",
            "starter": "starter_input_openradioss_r.htm",
            "engine": "engine_input_openradioss_r.htm",
            "index": "index_openradioss_r.htm"
        }

        if section_name in section_map:
            url = f"{base_url}/{section_map[section_name]}"
            # Use preset scroll position if not specified
            scroll_pos = scroll_lines if scroll_lines is not None else section_scrolls.get(section_name, 1000)
            # Add a small delay to ensure the page is loaded before scrolling
            self.show_web_view(url, section="openradioss-input", scroll_lines=scroll_pos)

    def show_keyword_list_view(self):
        """Switch back to the keyword list view."""
        if hasattr(self, 'stacked_widget'):
            self.stacked_widget.setCurrentIndex(0)
        if hasattr(self, 'back_button'):
            self.back_button.setVisible(False)

    def setup_ui(self):
        # Create the main window layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Create menu bar
        menubar = QMenuBar()
        main_layout.setMenuBar(menubar)

        # Add File menu
        file_menu = menubar.addMenu("&File")

        # Add file actions
        refresh_action = file_menu.addAction("Refresh from Dynamic CFG Files")
        refresh_action.setToolTip("Load keywords directly from CFG files (no hardcoded data)")
        refresh_action.triggered.connect(self.refresh_keywords_from_cfg)

        # Add auto-refresh action
        auto_refresh_action = file_menu.addAction("Auto-Refresh CFG Keywords")
        auto_refresh_action.setToolTip("Check for new keywords from CFG files in background")
        auto_refresh_action.triggered.connect(self.auto_refresh_cfg_keywords)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.reject)

        # Add Help menu
        help_menu = menubar.addMenu("&Help")

        # Add Examples menu
        examples_menu = menubar.addMenu("&Examples")

        # Add Templates menu
        template_menu = menubar.addMenu("&Templates")

        # Add help actions
        search_help_action = help_menu.addAction("Search Help")
        search_help_action.triggered.connect(lambda: self.show_help_section("search_help"))

        tutorials_action = help_menu.addAction("Tutorials")
        tutorials_action.triggered.connect(lambda: self.show_help_section("tutorials"))

        reference_action = help_menu.addAction("Reference Guide")
        reference_action.triggered.connect(lambda: self.show_help_section("reference_guide"))

        # Template menu is temporarily disabled
        # All template-related actions are commented out to prevent errors
        pass

        # Template actions are temporarily disabled
        # explicit_action = template_menu.addAction("Explicit Analysis")
        # explicit_action.triggered.connect(self.load_explicit_template)
        # 
        # # Add template mode configuration action
        # template_mode_action = template_menu.addAction("Template Mode")
        # template_mode_action.triggered.connect(self.configure_template_mode)
        pass

        # Add example actions
        latest_examples_action = examples_menu.addAction("Latest Examples")
        latest_examples_action.triggered.connect(lambda: self.show_examples_section("latest"))

        introductory_action = examples_menu.addAction("Introductory Examples")
        introductory_action.triggered.connect(lambda: self.show_examples_section("introductory"))

        implicit_examples_action = examples_menu.addAction("Implicit Examples")
        implicit_examples_action.triggered.connect(lambda: self.show_examples_section("implicit"))

        openradioss_examples_action = examples_menu.addAction("OpenRadioss Examples")
        openradioss_examples_action.triggered.connect(lambda: self.show_examples_section("openradioss"))

        # Create main splitter for the content
        self.main_splitter = QSplitter(QtCore.Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)

        # Status bar removed as per user request

        # Left panel (navigation)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Category filter
        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self.on_category_changed)
        left_layout.addWidget(self.category_combo)

        # Keywords list
        self.keywords_list = QListWidget()
        self.keywords_list.itemClicked.connect(self.on_keyword_selected)
        left_layout.addWidget(self.keywords_list)

        # Add left panel to splitter
        self.main_splitter.addWidget(left_panel)

        # Right panel (details)
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)

        # Keyword header
        self.keyword_header = QLabel()
        self.keyword_header.setTextFormat(QtCore.Qt.RichText)
        self.keyword_header.setOpenExternalLinks(True)
        self.right_layout.addWidget(self.keyword_header)

        # Add a tab widget for details view
        self.tab_widget = QTabWidget()

        # Description tab
        self.desc_tab = QTextEdit()
        self.desc_tab.setReadOnly(True)
        self.tab_widget.addTab(self.desc_tab, "Description")

        # Parameters tab
        self.params_tab = QTableWidget()
        self.params_tab.setColumnCount(3)  # Parameter, Value, Description
        self.params_tab.setHorizontalHeaderLabels(["Parameter", "Value", "Description"])
        self.params_tab.horizontalHeader().setStretchLastSection(True)
        self.tab_widget.addTab(self.params_tab, "Parameters")

        # Generated keyword tab
        self.generated_tab = QTextEdit()
        self.generated_tab.setReadOnly(True)
        self.tab_widget.addTab(self.generated_tab, "Generated Keyword")

        # Cached keywords tab
        self.cache_tab = QTextEdit()
        self.cache_tab.setReadOnly(True)
        self.tab_widget.addTab(self.cache_tab, "Cached Keywords (0)")

        # Add the tab widget to the right panel's layout
        self.right_layout.addWidget(self.tab_widget)

        # Add right panel to splitter
        self.main_splitter.addWidget(self.right_panel)

        # Set initial sizes
        self.main_splitter.setSizes([200, 600])

        # Create a horizontal layout for the action buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        # Left side buttons (action buttons)
        left_button_layout = QtWidgets.QHBoxLayout()
        
        # Add buttons to the left layout
        self.generate_button = QtWidgets.QPushButton("Generate Keyword")
        self.generate_button.clicked.connect(self.generate_keyword)
        left_button_layout.addWidget(self.generate_button)
        
        # Add spacer
        left_button_layout.addSpacing(10)
        
        # Help button
        self.help_button = QtWidgets.QPushButton("Help")
        self.help_button.clicked.connect(self.show_keyword_help)
        self.help_button.setEnabled(False)  # Disabled until a keyword with documentation is selected
        self.help_button.setToolTip("Show help documentation for the selected keyword")
        left_button_layout.addWidget(self.help_button)
        
        # Add left button layout to main button layout
        button_layout.addLayout(left_button_layout)
        
        # Add stretch to push right-side buttons to the right
        button_layout.addStretch()
        
        # Right side buttons (action buttons)
        right_button_layout = QtWidgets.QHBoxLayout()
        
        # Cache management button
        self.cache_button = QtWidgets.QPushButton("Add to Cache")
        self.cache_button.clicked.connect(self.cache_keyword)
        self.cache_button.setEnabled(False)  # Initially disabled until keyword is selected
        self.cache_button.setToolTip("Add the current keyword to the cache")
        right_button_layout.addWidget(self.cache_button)
        
        # Add spacer
        right_button_layout.addSpacing(10)
        
        # Update file button
        self.update_file_button = QtWidgets.QPushButton("Update .k File")
        self.update_file_button.clicked.connect(self.update_k_file)
        right_button_layout.addWidget(self.update_file_button)
        
        # Add right button layout to main button layout
        button_layout.addLayout(right_button_layout)
        
        # Add the main button layout to the main layout
        main_layout.addLayout(button_layout)
        
        # Create a separate button box for standard dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.close_and_save)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def update_keyword_ui(self, keyword_details):
        """Update the UI with the details of the selected keyword."""
        if not keyword_details:
            return
            
        # Update the keyword header
        keyword_name = keyword_details.get('name', 'Unknown')
        self.keyword_header.setText(f"<h2>{keyword_name}</h2>")
        
        # Update the description tab
        description = keyword_details.get('description', 'No description available.')
        self.desc_tab.setHtml(f"""
        <html><body>
            <h3>Description</h3>
            <p>{description}</p>
            
            {f"<h3>Example</h3><pre>{keyword_details['example']}</pre>" if 'example' in keyword_details else ''}
            
            {f"<h3>Notes</h3><p>{keyword_details['notes']}</p>" if 'notes' in keyword_details else ''}
        </body></html>
        """)
        
        # Update the parameters tab
        self.params_tab.setRowCount(0)  # Clear existing rows
        
        if 'parameters' in keyword_details and keyword_details['parameters']:
            parameters = keyword_details['parameters']
            # Handle both dictionary and list formats for parameters
            if isinstance(parameters, dict):
                param_items = parameters.items()
            elif isinstance(parameters, list):
                param_items = [(p.get('name', f'param_{i}'), p) for i, p in enumerate(parameters)]
            else:
                param_items = []
            
            self.params_tab.setRowCount(len(param_items))
            
            for i, (param_name, param_data) in enumerate(param_items):
                # Ensure param_data is a dictionary
                if not isinstance(param_data, dict):
                    param_data = {'value': param_data}
                
                # Parameter name
                name_item = QtWidgets.QTableWidgetItem(str(param_name))
                self.params_tab.setItem(i, 0, name_item)
                
                # Get parameter type and default value
                param_type = str(param_data.get('type', 'STRING')).upper()
                default_value = param_data.get('default', param_data.get('value', ''))
                
                # Create appropriate widget based on parameter type
                if 'values' in param_data and param_data['values']:
                    # Create a combobox for ENUM type
                    combo = QtWidgets.QComboBox()
                    values = param_data['values']
                    if not isinstance(values, (list, tuple)):
                        values = [values]
                    combo.addItems([str(v) for v in values])
                    
                    # Set current value if it exists in the values list
                    if default_value is not None and str(default_value) in [str(v) for v in values]:
                        index = combo.findText(str(default_value))
                        if index >= 0:
                            combo.setCurrentIndex(index)
                    elif values:
                        combo.setCurrentIndex(0)
                        
                    self.params_tab.setCellWidget(i, 1, combo)
                    
                elif param_type == 'BOOL':
                    # Create a checkbox for boolean values
                    checkbox = QtWidgets.QCheckBox()
                    checkbox.setChecked(str(default_value).lower() in ('1', 'true', 'yes', 't'))
                    checkbox_layout = QtWidgets.QHBoxLayout()
                    checkbox_layout.addWidget(checkbox)
                    checkbox_layout.setAlignment(QtCore.Qt.AlignCenter)
                    checkbox_layout.setContentsMargins(0, 0, 0, 0)
                    
                    widget = QtWidgets.QWidget()
                    widget.setLayout(checkbox_layout)
                    self.params_tab.setCellWidget(i, 1, widget)
                    
                else:
                    # Default to line edit for other types
                    value = str(default_value) if default_value is not None else ''
                    value_item = QtWidgets.QTableWidgetItem(value)
                    
                    # Set input validation based on type
                    if param_type == 'INT':
                        value_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                        # Add input validation for integers
                        validator = QtGui.QIntValidator()
                        if 'min' in param_data:
                            validator.setBottom(int(param_data['min']))
                        if 'max' in param_data:
                            validator.setTop(int(param_data['max']))
                        self.params_tab.setItem(i, 1, value_item)
                    elif param_type == 'FLOAT':
                        value_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                        # Add input validation for floats
                        validator = QtGui.QDoubleValidator()
                        if 'min' in param_data:
                            validator.setBottom(float(param_data['min']))
                        if 'max' in param_data:
                            validator.setTop(float(param_data['max']))
                        self.params_tab.setItem(i, 1, value_item)
                    else:
                        # Default string input
                        self.params_tab.setItem(i, 1, value_item)
                
                # Parameter description with type information
                desc = str(param_data.get('description', param_data.get('help', 'No description available')))
                type_info = f"<b>Type:</b> {param_type}"
                
                # Add min/max range if available
                range_str = []
                if 'min' in param_data:
                    range_str.append(f"min: {param_data['min']}")
                if 'max' in param_data:
                    range_str.append(f"max: {param_data['max']}")
                if range_str:
                    type_info += f" ({', '.join(range_str)})"
                
                desc_item = QtWidgets.QTableWidgetItem(f"{desc}\n\n{type_info}")
                self.params_tab.setItem(i, 2, desc_item)
                
                # Store parameter info for later use
                self.param_inputs[param_name] = {
                    'widget': self.params_tab.cellWidget(i, 1) or self.params_tab.item(i, 1),
                    'type': param_type,
                    'data': param_data
                }
            
            # Resize columns to fit content
            self.params_tab.resizeColumnsToContents()
            self.params_tab.resizeRowsToContents()
        
        # Clear the generated keyword tab until user clicks Generate
        self.generated_tab.setPlainText("# Click 'Generate Keyword' to generate the keyword")
    
    def show_keyword_help(self):
        """Show help documentation for the currently selected keyword."""
        if not hasattr(self, 'current_keyword') or not self.current_keyword:
            return
            
        doc_url = self.current_keyword.get('formatted_doc_url')
        if doc_url:
            self.show_web_view(doc_url)
        else:
            QtWidgets.QMessageBox.information(
                self,
                "No Documentation Available",
                f"No online documentation is available for {self.current_keyword.get('name', 'the selected keyword')}."
            )
    
    def show_welcome_message(self):
        """Display welcome message in the details panel."""
        keywords_count = len(self.keywords) if self.keywords else 0
        loading_status = " Keywords loaded from CFG files" if keywords_count > 0 else "  No keywords loaded yet"

        welcome_html = """
        <div style="text-align: center; padding: 20px;">
            <h1>Welcome to OpenRadioss Keyword Editor</h1>
            <p style="font-size: 14px; color: #666; margin-top: 20px;">
                This tool helps you create and manage OpenRadioss input files for your simulations.
            </p>
            <div style="margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 5px; text-align: left;">
                <h3> Automatic CFG Loading Status:</h3>
                <p><strong>{loading_status}</strong></p>
                <p>  <strong>{keywords_count}</strong> keywords available in {len(set(kw.get('category', 'General') for kw in self.keywords)) if self.keywords else 0} categories</p>
                <p>  Keywords are automatically loaded from CFG files on startup</p>
                <p>  File &gt; Refresh from Dynamic CFG Files (manual refresh available)</p>
                <br>
                <h3>Getting Started:</h3>
                <ul>
                    <li>Browse OpenRadioss keywords using the list on the left</li>
                    <li>Filter by category using the dropdown menu</li>
                    <li>Select a keyword to view its documentation and parameters</li>
                    <li>Configure parameters and generate keyword text</li>
                    <li>Cache keywords to build complete analysis setups</li>
                    <li>Generate final K-file for OpenRadioss solver</li>
                </ul>
            </div>
        </div>
        """

        # Safely set the welcome message, checking if UI elements exist
        if hasattr(self, 'desc_tab'):
            self.desc_tab.setHtml(welcome_html)

        # Set up keyword header if it exists
        if not hasattr(self, 'keyword_header') and hasattr(self, 'right_layout'):
            self.keyword_header = QLabel()
            self.keyword_header.setTextFormat(QtCore.Qt.RichText)
            self.keyword_header.setOpenExternalLinks(True)
            self.right_layout.insertWidget(0, self.keyword_header)

        if hasattr(self, 'keyword_header'):
            self.keyword_header.setText("<h2>Welcome</h2>")

        # Clear parameters if the table exists
        if hasattr(self, 'params_tab'):
            self.params_tab.setRowCount(0)

        # Get keyword count for UI updates
        keywords_count = len(self.keywords) if self.keywords else 0
        if keywords_count == 0:
            return
            
        # Get the current keyword name
        keyword_name = self.current_keyword.get('name', '')
        if not keyword_name:
            QtWidgets.QMessageBox.warning(self, "Invalid Keyword", 
                                       "No valid keyword selected.")
            return
            
        # Collect parameters from the form
        parameters = {}
        for param_name, widget_info in self.param_inputs.items():
            if isinstance(widget_info, dict):
                widget = widget_info.get('widget')
                if widget is not None:
                    if hasattr(widget, 'currentText'):  # QComboBox
                        value = widget.currentText()
                    elif hasattr(widget, 'text'):  # QLineEdit
                        value = widget.text()
                    elif hasattr(widget, 'value'):  # QSpinBox, QDoubleSpinBox
                        value = widget.value()
                    else:
                        value = str(widget)
                    parameters[param_name] = value
        
        # Create the keyword data structure
        keyword_data = {
            'name': keyword_name,
            'parameters': parameters,
            'description': self.current_keyword.get('description', '')
        }

    def open_cache_viewer(self):
        """Open the cache viewer window."""
        try:
            from femcommands.open_cache_viewer import CacheViewerWindow
            
            # Ensure we have the latest cache data
            if hasattr(self, 'keyword_cache'):
                cache_data = self.keyword_cache
            else:
                cache_data = []
                
            # Create and show the cache viewer
            self.cache_viewer = CacheViewerWindow(
                keyword_cache=cache_data,
                parent=self
            )
            self.cache_viewer.show()
            
            # Connect signals
            self.cache_viewer.cacheUpdated.connect(self.on_cache_updated)
            
        except ImportError as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Could not open cache viewer: {str(e)}\n\n"
                "The cache viewer module could not be imported.\n"
                "Please check your installation."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while opening the cache viewer: {str(e)}"
            )
    
    def on_cache_updated(self, cache_data):
        """Handle cache updates from the cache viewer."""
        if hasattr(self, 'keyword_cache'):
            self.keyword_cache = cache_data
            self._update_cache_display()
    
    def cache_keyword(self):
        """Cache the generated keyword."""
        if not hasattr(self, 'generated_tab') or not hasattr(self, 'current_keyword'):
            QtWidgets.QMessageBox.warning(
                self,
                "No Keyword",
                "No keyword has been generated yet. Please generate a keyword first."
            )
            return
        
        # Get the generated keyword text
        keyword_text = self.generated_tab.toPlainText().strip()
        if not keyword_text or keyword_text == "# Click 'Generate Keyword' to generate the keyword":
            QtWidgets.QMessageBox.warning(
                self,
                "No Keyword",
                "No keyword has been generated yet. Please generate a keyword first."
            )
            return
        
        try:
            # Initialize keyword cache if it doesn't exist
            if not hasattr(self, 'keyword_cache') or self.keyword_cache is None:
                self.keyword_cache = []
            
            # Create cache entry with proper format
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            keyword_name = self.current_keyword.get('name', 'Unknown')
            
            cache_entry = {
                'name': keyword_name,
                'text': keyword_text,
                'timestamp': timestamp,
                'keyword_name': keyword_name  # Keep both for backward compatibility
            }
            
            # Add to in-memory cache
            self.keyword_cache.append(cache_entry)
            
            # Save to disk
            if self.save_cache_to_json():
                QtWidgets.QMessageBox.information(
                    self,
                    "Keyword Cached",
                    f"Keyword '{keyword_name}' has been added to the cache.\n\n"
                    f"Total cached keywords: {len(self.keyword_cache)}"
                )
                
                # Update the display
                self._update_cache_display()
                
                # If cache viewer is open, update it
                if hasattr(self, 'cache_viewer') and self.cache_viewer.isVisible():
                    self.cache_viewer.update_cache(self.keyword_cache)
                    
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Cache Warning",
                    f"Keyword '{keyword_name}' was added to the in-memory cache "
                    "but could not be saved to disk.\n\n"
                    f"Cache file: {self.CACHE_FILE}"
                )
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while caching the keyword: {str(e)}"
            )
            import traceback
            print("Error in cache_keyword:")
            traceback.print_exc()
    
    def _collect_parameters(self):
        """Collect parameters from the current form."""
        parameters = {}
        if not hasattr(self, 'param_inputs'):
            return parameters
            
        for param_name, widget_info in self.param_inputs.items():
            if not isinstance(widget_info, dict):
                continue
                
            widget = widget_info.get('widget')
            if widget is None:
                continue
                
            try:
                # Get the value based on widget type
                if hasattr(widget, 'currentText'):  # QComboBox
                    value = widget.currentText()
                elif hasattr(widget, 'isChecked'):  # QCheckBox
                    value = 'YES' if widget.isChecked() else 'NO'
                elif hasattr(widget, 'text'):  # QLineEdit, QTextEdit
                    value = widget.text()
                elif hasattr(widget, 'value'):  # QSpinBox, QDoubleSpinBox
                    value = widget.value()
                elif hasattr(widget, 'toPlainText'):  # QTextEdit
                    value = widget.toPlainText()
                else:
                    value = str(widget)
                    
                parameters[param_name] = value
                
            except Exception as e:
                print(f"[WARNING] Could not get value for parameter '{param_name}': {str(e)}")
                parameters[param_name] = ""
            
        return parameters
        
    def _update_cache_display(self):
        """Update the cache tab with the current cache contents."""
        if not hasattr(self, 'cache_tab') or not hasattr(self, 'keyword_cache'):
            return
            
        if not self.keyword_cache:
            self.cache_tab.setPlainText("No keywords in cache.")
            if hasattr(self, 'tab_widget') and hasattr(self.tab_widget, 'count') and self.tab_widget.count() > 3:
                self.tab_widget.setTabText(3, "Cached Keywords (0)")
            return
            
        # Update the tab title with the count
        if hasattr(self, 'tab_widget') and hasattr(self.tab_widget, 'count') and self.tab_widget.count() > 3:
            self.tab_widget.setTabText(3, f"Cached Keywords ({len(self.keyword_cache)})")
            
        try:
            # Create a formatted display of the cache
            cache_text = []
            for i, item in enumerate(self.keyword_cache, 1):
                name = item.get('keyword_name', item.get('name', 'Unnamed'))
                timestamp = item.get('timestamp', 'No timestamp')
                text = item.get('text', '')
                
                # Format the entry
                cache_text.append(f"{'='*80}")
                cache_text.append(f"{i}. {name} - {timestamp}")
                cache_text.append("-" * 80)
                cache_text.append(text.strip())
                cache_text.append("\n")
                
            if cache_text:
                self.cache_tab.setPlainText("\n".join(cache_text))
            else:
                self.cache_tab.setPlainText("No valid cache entries found.")
                
            # Auto-scroll to the bottom to show the most recent entry
            cursor = self.cache_tab.textCursor()
            cursor.movePosition(QtGui.QTextCursor.End)
            self.cache_tab.setTextCursor(cursor)
            
        except Exception as e:
            print(f"[ERROR] Failed to update cache display: {str(e)}")
            self.cache_tab.setPlainText("Error: Could not display cache contents. See console for details.")
            
    def show_keyword_help(self):
        """Show help documentation for the currently selected keyword."""
        if not hasattr(self, 'current_keyword') or not self.current_keyword:
            return
            
        doc_url = self.current_keyword.get('formatted_doc_url')
        
        # Enable cache button when a keyword is selected
        if hasattr(self, 'cache_button'):
            self.cache_button.setEnabled(True)
            self.cache_button.clicked.connect(self.cache_keyword)
            
        # Initialize HTML content
        html = """
        <div style="font-family: Arial, sans-serif; margin: 10px;">
            <h2>{0}</h2>
            <div style="margin-bottom: 20px;">
                <p>{1}</p>
            </div>
            <h3>Parameters:</h3>
            <table border="1" cellpadding="5" cellspacing="0" style="width: 100%; border-collapse: collapse;">
                <tr style="background-color: #f0f0f0;">
                    <th>Parameter</th>
                    <th>Type</th>
                    <th>Default</th>
                    <th>Description</th>
                </tr>
        """.format(
            self.current_keyword.get('name', 'Unnamed Keyword'),
            self.current_keyword.get('description', 'No description available.')
        )
        
        # Handle parameters (both list and dict formats)
        if 'parameters' in self.current_keyword:
            parameters = self.current_keyword['parameters']
            
            # Convert list of parameters to dict if needed
            if isinstance(parameters, list):
                param_dict = {}
                for param in parameters:
                    if isinstance(param, dict):
                        name = param.get('name', 'unnamed')
                        param_dict[name] = param
                parameters = param_dict
            
            # Add parameter rows
            if isinstance(parameters, dict):
                for i, (param_name, param_data) in enumerate(parameters.items()):
                    row_bg = '#ffffff' if i % 2 == 0 else '#f9f9f9'
                    param_type = param_data.get('type', 'any') if isinstance(param_data, dict) else 'any'
                    param_default = param_data.get('default', '') if isinstance(param_data, dict) else ''
                    param_desc = param_data.get('description', '') if isinstance(param_data, dict) else str(param_data)
                    
                    html += f"""
                    <tr style="background-color: {row_bg};">
                        <td><b>{param_name}</b></td>
                        <td>{param_type}</td>
                        <td>{param_default}</td>
                        <td>{param_desc}</td>
                    </tr>"""
            
            html += """
            </table>
        </div>"""
        
        # Check if we have a JSON keyword for additional info
        json_kw = self.current_keyword.get('json_data', {})
        if json_kw and 'examples' in json_kw:
            html += """
            <div class="section">
                <h3>Examples</h3>
                <pre style="background-color: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto;">
            """
            
            if isinstance(json_kw['examples'], list):
                for example in json_kw['examples']:
                    html += f"{example}\n"
            else:
                html += f"{json_kw['examples']}"
                
            html += "</pre></div>"
        
        # Add JavaScript for handling external links
        html += """
        <script>
        // Make external links open in default browser
        document.addEventListener('click', function(e) {
            let target = e.target;
            // Handle clicks on links or their children (like icons)
            while (target && target !== document) {
                if (target.tagName === 'A' && target.hasAttribute('onclick')) {
                    // Let the onclick handler take care of it
                    return true;
                } else if (target.tagName === 'A' && target.href) {
                    if (target.target === '_blank') {
                        window.open(target.href, '_blank');
                        e.preventDefault();
                    }
                    break;
                }
                target = target.parentNode;
            }
        });
        </script>
        </body>
        </html>
        """
        
        self.desc_tab.setHtml(html)

    def generate_keyword(self):
        """Generate the keyword based on current parameters."""
        #print("\n[DEBUG] generate_keyword called")
        try:
            if not self.current_keyword:
                warning_msg = "No current keyword set"
                #print(f"  [WARNING] {warning_msg}")
                QtWidgets.QMessageBox.warning(self, "No Keyword Selected", 
                                           "Please select a keyword first.")
                return None
                
            #print(f"  [DEBUG] Current keyword: {self.current_keyword.get('name', 'Unnamed')}")
            #print(f"  [DEBUG] Current parameters: {self.current_keyword.get('parameters', {})}")
                
            # Get the current keyword name
            keyword_name = self.current_keyword.get('name', '')
            if not keyword_name:
                QtWidgets.QMessageBox.warning(self, "Invalid Keyword", 
                                           "No valid keyword selected.")
                return None
                
            # Collect parameters from the form
            parameters = {}
            #print("  [DEBUG] Collecting parameters from form...")
            
            # Get parameters from the table
            if not hasattr(self, 'params_tab'):
                #print("  [WARNING] No parameter table found (self.params_tab)")
                pass
            else:
                row_count = self.params_tab.rowCount()
                #print(f"  [DEBUG] Found {row_count} parameters in table")
                
                for row in range(row_count):
                    try:
                        # Get parameter name from first column
                        name_item = self.params_tab.item(row, 0)
                        if not name_item:
                            continue
                            
                        param_name = name_item.text()
                        if not param_name:
                            continue
                            
                        # Get the widget or item from the value column (column 1)
                        value_widget = self.params_tab.cellWidget(row, 1)
                        
                        if value_widget:
                            # Handle different widget types
                            if isinstance(value_widget, QtWidgets.QComboBox):
                                value = value_widget.currentText()
                            elif hasattr(value_widget, 'layout') and value_widget.layout() and value_widget.layout().count() > 0:
                                # Handle widget containers (like for checkboxes)
                                child_widget = value_widget.layout().itemAt(0).widget()
                                if isinstance(child_widget, QtWidgets.QCheckBox):
                                    value = '1' if child_widget.isChecked() else '0'
                                else:
                                    value = '0'  # Default for unknown widget types
                            else:
                                value = '0'  # Default for unknown widget types
                        else:
                            # Try to get value from QTableWidgetItem if no widget
                            value_item = self.params_tab.item(row, 1)
                            value = value_item.text() if value_item else ''
                        
                        parameters[param_name] = value
                        #print(f"    [PARAM] {param_name} = {value}")
                        
                    except Exception as e:
                        #print(f"    [ERROR] Error getting value for parameter in row {row}: {str(e)}")
                        parameters[param_name] = ""  # Use empty string as fallback
            
            # Create the keyword data structure
            keyword_data = {
                'name': keyword_name,
                'parameters': parameters,
                'description': self.current_keyword.get('description', '')
            }
            
            #print(f"  [DEBUG] Generated keyword data: {keyword_data}")
            
            # Try to update the generated keyword display
            try:
                if hasattr(self, 'generated_tab') and hasattr(self.generated_tab, 'setPlainText'):
                    # Get current timestamp for the header
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Start with a header
                    formatted = f"${'='*70}\n"
                    formatted += f"$ {keyword_name} - Generated by OpenRadioss Keyword Editor\n"
                    formatted += f"$ Generated on: {timestamp}\n"
                    formatted += f"${'='*70}\n\n"
                    
                    # Add documentation URL if available
                    doc_url = self.current_keyword.get('documentation')
                    if not doc_url and keyword_name in self.clean_keywords:
                        doc_url = self.clean_keywords[keyword_name].get('documentation')
                    
                    if doc_url:
                        formatted += f"$ Documentation: {doc_url}\n\n"
                    
                    # Define parameter order for this keyword
                    param_order = [
                        'CommentEnumField', 'Rho', 'LSDYNA_AOPT', 'LSD_MAT_REF', 
                        'LSD_MAT142_MACF', 'LSDYNA_XP', 'LSDYNA_YP', 'LSDYNA_ZP',
                        'LSDYNA_A1', 'LSDYNA_A2', 'LSDYNA_A3', 'LSDYNA_V1',
                        'LSDYNA_V2', 'LSDYNA_V3', 'LSDYNA_D1', 'LSDYNA_D2',
                        'LSDYNA_D3', 'LSDYNA_BETA'
                    ]
                    
                    # Add parameter descriptions as comments
                    formatted += "$ Parameter descriptions:\n"
                    for param in param_order:
                        if param in parameters:
                            # Get parameter description if available
                            param_desc = f"{param}"
                            if 'parameters' in self.current_keyword and param in self.current_keyword['parameters']:
                                desc = self.current_keyword['parameters'][param].get('description', '')
                                if desc:
                                    param_desc += f" - {desc}"
                            formatted += f"$   {param_desc}\n"
                    
                    formatted += "\n"
                    
                    # Add the actual keyword line with values
                    formatted += f"${'='*70}\n"
                    formatted += f"${' ' + keyword_name + ' ':-^70}\n"
                    formatted += f"${'='*70}\n"
                    
                    # First line with parameter values
                    first_line = [keyword_name]
                    
                    # Add parameters in the correct order
                    for param in param_order:
                        if param in parameters:
                            first_line.append(str(parameters[param]))
                        else:
                            default_val = '0.0' if any(c in param for c in 'XYZ') else '0'
                            first_line.append(default_val)
                    
                    # Add the parameter values line
                    formatted += ",".join(first_line) + "\n\n"
                    
                    # Add any remaining parameters that weren't in the standard order
                    remaining_params = [p for p in parameters.keys() if p not in param_order]
                    if remaining_params:
                        formatted += f"$ Additional parameters not in standard order:\n"
                        for param in remaining_params:
                            formatted += f"$   {param} = {parameters[param]}\n"
                        formatted += "\n"
                    
                    # Add footer
                    formatted += f"${'='*70}\n"
                    formatted += f"$ End of {keyword_name}\n"
                    formatted += f"${'='*70}\n"
                    
                    self.generated_tab.setPlainText(formatted)
                    #print("  [DEBUG] Updated generated keyword display with LS-DYNA format")
                else:
                    #print("  [WARNING] Could not find generated_tab or setPlainText method")
                    pass
            except Exception as e:
                #print(f"  [ERROR] Error updating generated keyword display: {str(e)}")
                pass
            
            # Show success message
            QtWidgets.QMessageBox.information(self, "Success", 
                                           f"Successfully generated {keyword_name} keyword.")
            
            return keyword_data
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error Generating Keyword", 
                                         f"An error occurred while generating the keyword: {str(e)}")
            #import traceback
            #traceback.print_exc()
            return None
            
    def update_k_file(self):
        """Update the .k file with the generated keyword."""
        try:
            # Get the generated keyword text
            keyword_text = self.generated_tab.toPlainText().strip()
            if not keyword_text or keyword_text == "# No keyword selected":
                QtWidgets.QMessageBox.warning(self, "No Keyword",
                                  "No keyword has been generated yet.")
                return

            # Get the target .k file path
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save Keyword to .k File", "", "Keyword Files (*.k);;All Files (*)")
            
            if not file_path:
                return  # User cancelled
                
            # Ensure the file has .k extension
            if not file_path.lower().endswith('.k'):
                file_path += '.k'
            
            # Write the keyword to the file
            with open(file_path, 'w') as f:
                f.write(keyword_text)
                
            QtWidgets.QMessageBox.information(self, "Success",
                              f"Keyword successfully saved to:\n{file_path}")
                              
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error",
                            f"Failed to save .k file:\n{str(e)}")
            #import traceback
            #traceback.print_exc()

    def load_cache(self):
        """Load the keyword cache from disk."""
        try:
            from femcommands.open_cache_viewer import load_cache_from_disk
            self.keyword_cache = load_cache_from_disk()
            if not isinstance(self.keyword_cache, list):
                self.keyword_cache = []
            self._update_cache_display()
        except Exception as e:
            print(f"Error loading cache: {e}")
            self.keyword_cache = []
    
    def save_cache_to_json(self):
        """Save the keyword cache to a JSON file."""
        if not hasattr(self, 'keyword_cache') or not self.keyword_cache:
            return False
            
        try:
            # Ensure the cache directory exists
            os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
            
            # Prepare cache data in the correct format
            cache_data = []
            for item in self.keyword_cache:
                if isinstance(item, dict):
                    cache_data.append({
                        'name': item.get('keyword_name', item.get('name', 'Unnamed')),
                        'text': item.get('text', ''),
                        'timestamp': item.get('timestamp', '')
                    })
            
            # Save the cache to the JSON file
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving keyword cache: {e}")
            return False
            
    def close_and_save(self):
        """Save cache and close the dialog."""
        if hasattr(self, 'keyword_cache') and self.keyword_cache:
            # Save cache to JSON file before closing
            self.save_cache_to_json()
        self.accept()

    def closeEvent(self, event):
        """Handle window close event."""
        # Save cache before closing if there are cached keywords
        if hasattr(self, 'keyword_cache') and self.keyword_cache:
            try:
                # Save cache to JSON file
                self.save_cache_to_json()
                
                # Also save to JSON cache file if needed
                with open(self.CACHE_FILE, 'w') as f:
                    json.dump(self.keyword_cache, f, indent=2)
                #print(f"Saved {len(self.keyword_cache)} keywords to cache at {self.CACHE_FILE}")
            except Exception as e:
                #print(f"Error saving keyword cache: {e}")
                pass
            
        # Save settings and close any open dialogs
        try:
            # Save settings
            self.save_settings()
            
            # Close any open dialogsq
            if hasattr(self, 'cache_viewer') and self.cache_viewer:
                self.cache_viewer.close()
                
        except Exception as e:
            #print(f"Error in closeEvent: {e}")
            pass
        finally:
            # Always accept the close event
            event.accept()
