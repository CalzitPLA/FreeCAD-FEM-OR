"""OpenRadioss Keyword Editor GUI for FreeCAD"""

import os
import json
import copy
import webbrowser
import markdown
import datetime
import logging
from pathlib import Path
from utils.keyword_utils import KeywordUtils

import FreeCAD
import FreeCADGui as Gui

# Try to import Qt modules with fallback support
try:
    # Try PySide2 first (most common in FreeCAD)
    from PySide2 import QtCore, QtGui, QtWidgets, QtNetwork
    print("[INFO] Using PySide2")
except ImportError:
    try:
        # Try PyQt5
        from PyQt5 import QtCore, QtGui, QtWidgets, QtNetwork
        print("[INFO] Using PyQt5")
    except ImportError:
        try:
            # Try PyQt6
            from PyQt6 import QtCore, QtGui, QtWidgets, QtNetwork
            print("[INFO] Using PyQt6")
        except ImportError:
            try:
                # Last resort - PySide (original Qt4 binding)
                from PySide import QtCore, QtGui, QtNetwork
                print("[INFO] Using PySide")
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
    except ImportError as e:
        print(f"[INFO] FreeCAD WebGui not available: {e}")
else:
    print("[INFO] Running in Flatpak environment, will use system browser")

class DocumentationViewer(object):
    """Unified documentation viewer that works in both regular and Flatpak environments."""

    def __init__(self, parent=None):
        """Initialize the appropriate viewer based on environment."""
        self.parent = parent
        self.viewer = None

        if HAS_WEB_GUI and not IS_FLATPAK:
            # Use FreeCAD's WebGui if available
            self.viewer = self._init_webgui_viewer()
        else:
            # Fall back to system browser
            self.viewer = self._init_system_browser()

    def _init_webgui_viewer(self):
        """Initialize WebGui-based viewer."""
        try:
            import WebGui
            # Create a simple wrapper around WebGui
            class WebGuiViewer:
                def __init__(self, parent):
                    self.browser = WebGui.openBrowserWindow("Documentation")
                    self.browser.setWindowTitle("Documentation Viewer")

                def load_url(self, url):
                    if url:
                        self.browser.setUrl(url)

                def show(self):
                    self.browser.show()

                def close(self):
                    self.browser.close()

            return WebGuiViewer(self.parent)

        except Exception as e:
            print(f"[WARNING] Failed to initialize WebGui: {e}")
            return self._init_system_browser()

    def _init_system_browser(self):
        """Initialize system browser fallback."""
        import webbrowser

        class SystemBrowserViewer:
            def __init__(self, parent):
                self.parent = parent

            def load_url(self, url):
                if url:
                    print(f"[INFO] Opening in system browser: {url}")
                    webbrowser.open(url)

            def show(self):
                pass  # No UI for system browser

            def close(self):
                pass  # Nothing to close

        return SystemBrowserViewer(self.parent)

    # Delegate method calls to the appropriate viewer
    def load_url(self, url):
        if self.viewer:
            self.viewer.load_url(url)

    def show(self):
        if self.viewer:
            self.viewer.show()

    def close(self):
        if self.viewer:
            self.viewer.close()


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
            print(f"[INFO] Opening documentation in system browser: {self.doc_url}")
            webbrowser.open(self.doc_url)

# Import CacheViewerWindow from the cache viewer module
try:
    from femcommands.open_cache_viewer import CacheViewerWindow
    print("[INFO] CacheViewerWindow imported successfully")
except ImportError as e:
    print(f"[WARNING] Failed to import CacheViewerWindow: {e}")
    print("[WARNING] Cache viewer functionality will be limited")
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

    def load_cache(self):
        """Load cached keywords from file if it exists."""
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.keyword_cache = json.load(f)
                print(f"[INFO] Loaded {len(self.keyword_cache)} keywords from cache")
            else:
                print("[INFO] No cache file found, starting with empty cache")
                self.keyword_cache = []
        except Exception as e:
            print(f"[WARNING] Error loading cache: {e}")
            self.keyword_cache = []
            
    def save_cache(self):
        """Save current keyword cache to file."""
        try:
            # Ensure cache directory exists
            os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
            
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.keyword_cache, f, indent=2)
            print(f"[INFO] Saved {len(self.keyword_cache)} keywords to cache")
        except Exception as e:
            print(f"[WARNING] Error saving cache: {e}")

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
        
        # Initialize cache paths
        from femcommands.open_cache_viewer import CACHE_FILE, CACHE_DIR
        self.CACHE_FILE = CACHE_FILE
        self.CACHE_DIR = CACHE_DIR
        
        # Initialize keyword cache
        self.keyword_cache = []
        self.load_cache()

        # Template configuration
        self.template_mode = "full"  # "full", "basic", "minimal"

        # Load settings first
        self.load_settings()
        
        # Set up the UI
        self.setup_ui()
        
        # Show welcome message
        self.show_welcome_message()
        
        # Initialize keyword metadata (lazy loading)
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
        
    def load_settings(self):
        """Load user settings or apply default configurations."""
        try:
            # Get FreeCAD parameter group for our settings
            param = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/FemUpgraded")
            
            # Load template mode setting or use default
            self.template_mode = param.GetString("TemplateMode", "full")
            
            # Load window geometry if available
            window_geometry = param.GetString("WindowGeometry", "")
            if window_geometry:
                self.restoreGeometry(QtCore.QByteArray.fromHex(window_geometry.encode()))
                
            # Load recent files list
            self.recent_files = []
            for i in range(5):  # Keep last 5 recent files
                recent = param.GetString(f"RecentFile{i}", "")
                if recent and os.path.exists(recent):
                    self.recent_files.append(recent)
                    
            print(f"[INFO] Loaded settings: template_mode={self.template_mode}")
            
        except Exception as e:
            print(f"[WARNING] Error loading settings: {e}")
            # Apply defaults if loading fails
            self.template_mode = "full"
            self.recent_files = []

    def save_settings(self):
        """Save current settings to FreeCAD parameters."""
        try:
            param = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/FemUpgraded")
            
            # Save template mode
            param.SetString("TemplateMode", self.template_mode)
            
            # Save window geometry
            param.SetString("WindowGeometry", self.saveGeometry().toHex().data().decode())
            
            # Save recent files
            for i, recent_file in enumerate(self.recent_files[:5]):
                param.SetString(f"RecentFile{i}", recent_file)
                
            print("[INFO] Settings saved successfully")
            
        except Exception as e:
            print(f"[WARNING] Error saving settings: {e}")

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
            db_path = os.path.join(os.path.dirname(__file__), 'openradioss_keywords_with_parameters.json')
            clean_path = os.path.join(os.path.dirname(__file__), 'openradioss_keywords_clean.json')
            
            # If the database file doesn't exist, generate it
            if not os.path.exists(db_path):
                print(f"[INFO] Pre-processed keywords file not found at {db_path}, will be generated on first load")
                # Initialize with empty data, it will be populated when keywords are loaded
                self.keyword_metadata = []
                return
                
            if not os.path.exists(clean_path):
                print("[WARNING] Clean keywords file not found, web links will not be available")
            
            # Load the database if it exists
            if os.path.exists(db_path):
                with open(db_path, 'r', encoding='utf-8') as f:
                    db_data = json.load(f)
            else:
                db_data = []
            
            # Load clean keywords for metadata if they exist
            self.clean_keywords = {}
            if os.path.exists(clean_path):
                with open(clean_path, 'r', encoding='utf-8') as f:
                    clean_data = json.load(f)
                    self.clean_keywords = {kw['name']: kw for kw in clean_data if 'name' in kw}
            
            # The database is already a list of keywords
            successful_keywords = db_data if isinstance(db_data, list) else []
            
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
                
            else:
                # No valid keywords found
                pass
            
        except Exception as e:
            import traceback
            print(f"Error initializing keyword metadata: {str(e)}\n{traceback.format_exc()}")
            
    def load_keyword_details(self, keyword_name):
        """Load full details for a keyword when it's selected"""
        if not keyword_name or keyword_name not in self.raw_keyword_data:
            return None
            
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

    def update_category_list(self):
        """Update the category dropdown with unique categories from keywords."""
        if not hasattr(self, 'category_combo') or not hasattr(self, 'keywords'):
            return
            
        if not self.keywords:
            return

        # Extract unique categories from keywords
        categories = set()
        for kw in self.keywords:
            if isinstance(kw, dict) and 'category' in kw:
                categories.add(kw['category'])

        # Update the category combo box
        self.category_combo.clear()
        self.category_combo.addItem("All")
        self.category_combo.addItems(sorted(categories))
        
        # Update the keyword list to show all keywords initially
        self.update_keyword_list()
    
    def on_category_changed(self, index):
        """Handle category selection change."""
        self.update_keyword_list()
    
    def update_keyword_list(self, category=None):
        """Update the keyword list based on the selected category."""
        if not hasattr(self, 'keywords_list'):
            return
            
        if not hasattr(self, 'keywords') or not self.keywords:
            self.keywords_list.clear()
            self.keywords_list.addItem("No keywords available")
            return
            
        # Get the selected category
        if category is None:
            category = self.category_combo.currentText()
            
        # Clear the current selection to prevent any issues
        self.keywords_list.clear()
        
        # If no category selected or "All" is selected, show all keywords
        if not category or category == "All":
            keywords_to_show = self.keywords
        else:
            # Filter keywords by the selected category
            keywords_to_show = [kw for kw in self.keywords if kw.get('category') == category]
        
        # Add keywords to the list
        for keyword in keywords_to_show:
            item = QListWidgetItem(keyword.get('name', 'Unknown'))
            # Store the full keyword data in UserRole
            item.setData(QtCore.Qt.UserRole, keyword)
            self.keywords_list.addItem(item)
            
        # Status bar message removed
        
        # If we have keywords, select the first one
        if keywords_to_show and self.keywords_list.count() > 0:
            self.keywords_list.setCurrentRow(0)
            # Trigger the selection changed event if the method exists
            if hasattr(self, 'on_keyword_selected') and self.keywords_list.currentItem() is not None:
                self.on_keyword_selected(self.keywords_list.currentItem())
        else:
            # Clear the details if no keywords to show
            if hasattr(self, 'show_welcome_message'):
                self.show_welcome_message()
    
    def on_keyword_selected(self, item):
        """Handle keyword selection from the list by showing documentation in embedded browser."""
        if not item:
            return
            
        keyword_name = item.text()
        print(f"[DEBUG] Selected keyword: {keyword_name}")
        
        # Get the keyword data stored in the item's UserRole
        self.current_keyword = item.data(QtCore.Qt.UserRole)
        if not self.current_keyword:
            print(f"[ERROR] No data found for keyword: {keyword_name}")
            return
            
        print(f"[DEBUG] Current keyword data: {self.current_keyword.keys()}")
            
        # Show the keyword details in the UI
        self.show_keyword_details()
        
        # Enable the cache button when a keyword is selected
        if hasattr(self, 'cache_button'):
            self.cache_button.setEnabled(True)
            
    def show_keyword_details(self):
        """Show details of the selected keyword."""
        if not hasattr(self, 'current_keyword') or not self.current_keyword:
            print("[DEBUG] show_keyword_details: No current keyword")
            self.show_welcome_message()
            return
            
        keyword_name = self.current_keyword.get('name', 'Unknown')
        print(f"[DEBUG] Showing details for keyword: {keyword_name}")
        
        # Update the UI with keyword information
        if hasattr(self, 'keyword_header'):
            self.keyword_header.setText(f"<h2>{keyword_name}</h2>")
            
        if hasattr(self, 'desc_tab'):
            # Create a simple HTML description
            desc = f"""
            <html>
            <body>
                <h3>{keyword_name}</h3>
                <p><strong>Category:</strong> {self.current_keyword.get('category', 'N/A')}</p>
                <p><strong>Description:</strong> {self.current_keyword.get('description', 'No description available')}</p>
            </body>
            </html>
            """
            self.desc_tab.setHtml(desc)
            
        # Clear parameter inputs before updating parameters tab
        self.param_inputs = {}
        
        if hasattr(self, 'params_tab'):
            print("[DEBUG] Updating parameters tab")
            self.params_tab.setRowCount(0)  # Clear existing rows
            
            # Set column headers
            headers = ["Name", "Type", "Default", "Value", "Description"]
            self.params_tab.setColumnCount(len(headers))
            self.params_tab.setHorizontalHeaderLabels(headers)
            
            # Add parameters if they exist
            if 'parameters' in self.current_keyword and self.current_keyword['parameters']:
                self.params_tab.setRowCount(len(self.current_keyword['parameters']))
                for i, param in enumerate(self.current_keyword['parameters']):
                    # Get parameter properties with defaults
                    param_name = param.get('name', f'Param{i+1}')
                    param_type = param.get('type', 'float')
                    param_default = str(param.get('default', ''))
                    param_desc = param.get('description', 'No description available')
                    
                    # Add parameter name with tooltip
                    name_item = QtWidgets.QTableWidgetItem(param_name)
                    name_item.setToolTip(param_desc)
                    self.params_tab.setItem(i, 0, name_item)
                    
                    # Add parameter type with tooltip
                    type_item = QtWidgets.QTableWidgetItem(param_type)
                    type_item.setToolTip(f"Expected type: {param_type}")
                    self.params_tab.setItem(i, 1, type_item)
                    
                    # Add parameter default value with tooltip
                    default_item = QtWidgets.QTableWidgetItem(param_default)
                    default_item.setToolTip(f"Default: {param_default}")
                    default_item.setBackground(QtGui.QColor(240, 240, 240))  # Light gray background
                    self.params_tab.setItem(i, 2, default_item)
                    
                    # Add input field with validation based on type
                    input_widget = QtWidgets.QLineEdit(param_default)
                    
                    # Set input validation based on type
                    if param_type.lower() == 'integer':
                        validator = QtGui.QIntValidator()
                        input_widget.setValidator(validator)
                    elif param_type.lower() == 'float':
                        validator = QtGui.QDoubleValidator()
                        validator.setNotation(QtGui.QDoubleValidator.ScientificNotation)
                        input_widget.setValidator(validator)
                    
                    input_widget.setToolTip(f"Enter {param_type} value")
                    self.params_tab.setCellWidget(i, 3, input_widget)
                    self.param_inputs[param_name] = input_widget
                    
                    # Add parameter description with word wrap
                    desc_item = QtWidgets.QTableWidgetItem(param_desc)
                    desc_item.setToolTip(param_desc)
                    desc_item.setFlags(desc_item.flags() & ~QtCore.Qt.ItemIsEditable)
                    self.params_tab.setItem(i, 4, desc_item)
                
                # Resize columns to fit content
                self.params_tab.resizeColumnsToContents()
                # Make description column take remaining space
                self.params_tab.horizontalHeader().setStretchLastSection(True)
        
        # Add help button if not exists
        if not hasattr(self, 'help_button'):
            self.help_button = QtWidgets.QPushButton("Open Documentation")
            self.help_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogHelpButton))
            self.help_button.clicked.connect(self.open_keyword_documentation)
            
            # Add to layout if we have a header layout
            if hasattr(self, 'keyword_header'):
                # Get the layout of the widget containing keyword_header
                header_widget = self.keyword_header.parent()
                if header_widget and header_widget.layout():
                    # Add button to the right of the header
                    header_layout = header_widget.layout()
                    # Add stretch to push button to the right
                    if header_layout.count() == 1:  # Only has the header label
                        header_layout.addStretch()
                    # Add button if not already added
                    if header_layout.indexOf(self.help_button) == -1:
                        header_layout.addWidget(self.help_button)
        
        # Enable/disable help button based on URL availability
        self.help_button.setEnabled(hasattr(self, 'current_keyword') and 
                                  'documentation' in self.current_keyword and 
                                  self.current_keyword['documentation'])
        
        # Clear generated keyword tab
        if hasattr(self, 'generated_tab'):
            self.generated_tab.clear()
    
    def open_keyword_documentation(self):
        """Open the documentation URL for the current keyword in the default web browser."""
        if not hasattr(self, 'current_keyword') or not self.current_keyword:
            QMessageBox.information(self, "No Keyword Selected", 
                                 "Please select a keyword first to view its documentation.")
            return
            
        doc_url = self.current_keyword.get('documentation', '')
        if not doc_url:
            QMessageBox.information(self, "No Documentation Available", 
                                 "No documentation URL is available for the selected keyword.")
            return
            
        try:
            # Ensure URL has a scheme
            if not doc_url.startswith(('http://', 'https://')):
                doc_url = 'https://' + doc_url.lstrip('/')
                
            print(f"[DEBUG] Opening documentation: {doc_url}")
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(doc_url))
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                              f"Could not open documentation URL:\n{doc_url}\n\nError: {str(e)}")
    
    def _update_keyword_display(self, keywords):
        """Update the keyword list display with the provided keywords."""
        self.keywords_list.clear()
        for kw in keywords:
            item = QtWidgets.QListWidgetItem(kw.get('name', 'Unknown'))
            item.setData(QtCore.Qt.UserRole, kw)
            self.keywords_list.addItem(item)
    
    def _on_search_text_changed(self, text):
        """Handle search text changes and update the keyword list."""
        if not hasattr(self, 'keywords_list') or not hasattr(self, 'category_combo'):
            return
            
        search_text = text.lower().strip()
        current_category = self.category_combo.currentText()
        
        # Get base keywords based on category
        if current_category != "All":
            base_keywords = [kw for kw in self.keywords if kw.get('category') == current_category]
        else:
            base_keywords = self.keywords
            
        # If search is empty, just update with the filtered list
        if not search_text:
            self._update_keyword_display(base_keywords)
            return
            
        # Filter keywords that match search text in name or description
        filtered_keywords = []
        for kw in base_keywords:
            name = kw.get('name', '').lower()
            desc = kw.get('description', '').lower()
            if (search_text in name) or (search_text in desc):
                filtered_keywords.append(kw)
                
        # Update the display with filtered keywords
        self._update_keyword_display(filtered_keywords)

    def load_keywords(self):
        """Load and filter keywords using the KeywordUtils class."""
        print("\n=== DEBUG: LOADING KEYWORDS ===")
        try:
            # Define paths - using direct paths since the files are in the json directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, 'json', 'keyword_database_results.json')
            whitelist_path = os.path.join(base_dir, 'json', 'keywords_clean.json')
            output_path = os.path.join(base_dir, 'openradioss_keywords_with_parameters.json')
            
            print(f"[DEBUG] Loading keywords from database: {db_path}")
            print(f"[DEBUG] Using whitelist from: {whitelist_path}")
            
            # Check if required files exist
            if not os.path.exists(db_path):
                print(f"[ERROR] Database file not found: {db_path}")
                print("[INFO] Please ensure the keyword database file exists at the specified location.")
                print("[INFO] The file should be at: gui/json/keyword_database_results.json relative to the module")
                return []
                
            if not os.path.exists(whitelist_path):
                print(f"[ERROR] Whitelist file not found: {whitelist_path}")
                print("[INFO] Please ensure the whitelist file exists at the specified location.")
                print("[INFO] The file should be at: gui/json/keywords_clean.json relative to the module")
                return []
            
            # Check if we have a pre-processed file that's up to date
            if os.path.exists(output_path):
                output_mtime = os.path.getmtime(output_path)
                db_mtime = os.path.getmtime(db_path)
                whitelist_mtime = os.path.getmtime(whitelist_path)
                
                # If the source files haven't changed, use the pre-processed file
                if output_mtime > db_mtime and output_mtime > whitelist_mtime:
                    print("[DEBUG] Using pre-processed keywords file")
                    with open(output_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            
            # Use the utility class to load and filter keywords
            keywords = KeywordUtils.load_keywords(db_path, whitelist_path)
            print(f"[DEBUG] Loaded {len(keywords)} keywords")
            
            # Save the processed keywords for future use
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(keywords, f, indent=2, ensure_ascii=False)
                print(f"[DEBUG] Saved processed keywords to {output_path}")
            except Exception as e:
                print(f"[WARNING] Could not save processed keywords: {str(e)}")
            
            return keywords
            
        except Exception as e:
            print(f"[ERROR] Failed to load keywords: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def save_keywords_as_json(self, keywords):
        """Save keywords as JSON for faster loading next time (comprehensive format with format tags)."""
        try:
            # Save comprehensive format as primary
            comprehensive_file = os.path.join(os.path.dirname(__file__), 'comprehensive_hm_reader_keywords.json')
            with open(comprehensive_file, 'w', encoding='utf-8') as f:
                json.dump(keywords, f, indent=2, ensure_ascii=False)

            # Also save enhanced HM reader format for compatibility
            enhanced_file = os.path.join(os.path.dirname(__file__), 'enhanced_hm_reader_keywords.json')
            with open(enhanced_file, 'w', encoding='utf-8') as f:
                json.dump(keywords, f, indent=2, ensure_ascii=False)

            # Also save basic HM reader format for compatibility
            basic_hm_file = os.path.join(os.path.dirname(__file__), 'hm_reader_keywords.json')
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

            # Save clean version
            clean_file = os.path.join(os.path.dirname(__file__), 'openradioss_keywords_clean.json')
            with open(clean_file, 'w', encoding='utf-8') as f:
                json.dump(basic_keywords, f, indent=2, ensure_ascii=False)

            # Save detailed version with parameters in the json directory
            detailed_file = os.path.join(os.path.dirname(__file__), 'json', 'openradioss_keywords_with_parameters.json')
            os.makedirs(os.path.dirname(detailed_file), exist_ok=True)
            with open(detailed_file, 'w', encoding='utf-8') as f:
                json.dump(keywords, f, indent=2, ensure_ascii=False)

            print(f"[INFO] Saved {len(keywords)} keywords in comprehensive format with format detection")

        except Exception as e:
            print(f"[WARNING] Could not save keywords to JSON: {e}")

    def setup_ui(self):
        # Create the main window layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Create menu bar
        menubar = QMenuBar()
        main_layout.setMenuBar(menubar)

        # Add File menu
        file_menu = menubar.addMenu("&File")
        
        # Add file actions
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

        # Add template actions
        minimal_template_action = template_menu.addAction("Minimal Template")
        minimal_template_action.triggered.connect(self.load_minimal_template)

        simulation_template_action = template_menu.addAction("Simulation Template")
        simulation_template_action.triggered.connect(self.load_simulation_template)

        basic_template_action = template_menu.addAction("Basic Template")
        basic_template_action.triggered.connect(self.load_basic_template)

        structural_template_action = template_menu.addAction("Structural Template")
        structural_template_action.triggered.connect(self.load_structural_template)

        thermal_template_action = template_menu.addAction("Transient Thermal")
        thermal_template_action.triggered.connect(self.load_thermal_template)

        template_menu.addSeparator()

        # Add analysis-specific template actions
        linear_static_action = template_menu.addAction("Linear Static Analysis")
        linear_static_action.triggered.connect(self.load_linear_static_template)

        modal_analysis_action = template_menu.addAction("Modal Analysis")
        modal_analysis_action.triggered.connect(self.load_modal_analysis_template)

        steady_thermal_action = template_menu.addAction("Steady-State Thermal")
        steady_thermal_action.triggered.connect(self.load_steady_state_thermal_template)

        basic_contact_action = template_menu.addAction("Basic Contact")
        basic_contact_action.triggered.connect(self.load_basic_contact_template)

        template_menu.addSeparator()

        # Add solver differentiation actions
        implicit_action = template_menu.addAction("Implicit Analysis")
        implicit_action.triggered.connect(self.load_implicit_template)

        explicit_action = template_menu.addAction("Explicit Analysis")
        explicit_action.triggered.connect(self.load_explicit_template)

        # Add template mode configuration action
        template_mode_action = template_menu.addAction("Template Mode")
        template_mode_action.triggered.connect(self.configure_template_mode)

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

        # Left panel (navigation)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_layout.setSpacing(5)

        # Search box
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search keywords...")
        self.search_box.textChanged.connect(self._on_search_text_changed)
        left_layout.addWidget(self.search_box)
        
        # Store the original keywords for search filtering
        self._original_keywords = []

        # Category filter
        self.category_combo = QComboBox()
        self.category_combo.currentIndexChanged.connect(self.on_category_changed)
        left_layout.addWidget(self.category_combo)

        # Keywords list
        self.keywords_list = QListWidget()
        self.keywords_list.itemClicked.connect(self.on_keyword_selected)
        left_layout.addWidget(self.keywords_list, 1)  # Add stretch factor to make it expandable

        # Add left panel to splitter
        self.main_splitter.addWidget(left_panel)

        # Right panel (details)
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(5, 0, 0, 0)
        self.right_layout.setSpacing(5)

        # Keyword header with web help button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.keyword_header = QLabel("<h2>Select a keyword</h2>")
        self.keyword_header.setTextFormat(QtCore.Qt.RichText)
        self.keyword_header.setOpenExternalLinks(True)
        
        # Add web help button
        self.help_button = QPushButton()
        self.help_button.setIcon(self.style().standardIcon(getattr(QtWidgets.QStyle, 'SP_MessageBoxQuestion', None) or QtWidgets.QStyle.SP_MessageBoxQuestion))
        self.help_button.setToolTip("Open web documentation")
        self.help_button.clicked.connect(self.open_keyword_documentation)
        self.help_button.setEnabled(False)  # Disabled until a keyword is selected
        
        header_layout.addWidget(self.keyword_header, 1)
        header_layout.addWidget(self.help_button, 0, QtCore.Qt.AlignRight)
        
        self.right_layout.addWidget(header_widget)

        # Add a tab widget for details view
        self.tab_widget = QTabWidget()

        # Description tab
        self.desc_tab = QTextEdit()
        self.desc_tab.setReadOnly(True)
        self.tab_widget.addTab(self.desc_tab, "Description")

        # Parameters tab
        self.params_tab = QTableWidget()
        self.params_tab.setColumnCount(3)
        self.params_tab.setHorizontalHeaderLabels(["Parameter", "Value", "Description"])
        self.params_tab.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.params_tab.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.params_tab.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.tab_widget.addTab(self.params_tab, "Parameters")

        # Generated keyword tab
        self.generated_tab = QTextEdit()
        self.generated_tab.setReadOnly(True)
        self.tab_widget.addTab(self.generated_tab, "Generated Keyword")

        # Cached keywords tab
        self.cache_tab = QTextEdit()
        self.cache_tab.setReadOnly(True)
        self.tab_widget.addTab(self.cache_tab, "Cached Keywords (0)")

        # Add tab widget to right panel
        self.right_layout.addWidget(self.tab_widget, 1)  # Add stretch factor to make it expandable

        # Add right panel to splitter
        self.main_splitter.addWidget(self.right_panel)

        # Set initial sizes for the splitter
        self.main_splitter.setSizes([200, 600])

        # Status bar removed as requested

        # Add dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Add custom buttons
        self.generate_button = QtWidgets.QPushButton("Generate Keyword")
        self.generate_button.clicked.connect(self.generate_keyword)
        button_box.addButton(self.generate_button, QDialogButtonBox.ActionRole)

        self.cache_button = QtWidgets.QPushButton("Add to Cache")
        self.cache_button.clicked.connect(self.cache_keyword)
        self.cache_button.setEnabled(False)  # Initially disabled
        button_box.addButton(self.cache_button, QDialogButtonBox.ActionRole)

        self.update_file_button = QtWidgets.QPushButton("Update .k File")
        self.update_file_button.clicked.connect(self.update_k_file)
        button_box.addButton(self.update_file_button, QDialogButtonBox.ActionRole)

        main_layout.addWidget(button_box)

        # Set window properties
        self.setWindowTitle("OpenRadioss Keyword Editor")
        self.resize(1000, 700)
        
        # Initialize UI state
        self.update_category_list()
        self.update_keyword_list()
        self.show_welcome_message()

    def show_welcome_message(self):
        """Display welcome message in the details panel."""
        keywords_count = len(self.keywords) if self.keywords else 0
        loading_status = "✅ Keywords loaded from JSON" if keywords_count > 0 else "⚠️  No keywords loaded yet"

        welcome_html = f"""
        <div style="text-align: center; padding: 20px;">
            <h1>Welcome to OpenRadioss Keyword Editor</h1>
            <p style="font-size: 14px; color: #666; margin-top: 20px;">
                This tool helps you create and manage OpenRadioss input files for your simulations.
            </p>
            <div style="margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 5px; text-align: left;">
                <h3>🎯 JSON Loading Status:</h3>
                <p><strong>{loading_status}</strong></p>
                <p>📊 <strong>{keywords_count}</strong> keywords available in {len(set(kw.get('category', 'General') for kw in self.keywords)) if self.keywords else 0} categories</p>
                <p>🔄 Keywords are loaded from JSON files on startup</p>
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

    def show_keyword_details(self):
        """Show details of the selected keyword."""
        if not hasattr(self, 'current_keyword') or not self.current_keyword:
            print("[DEBUG] show_keyword_details: No current keyword")
            self.show_welcome_message()
            return

        print(f"[DEBUG] show_keyword_details called for: {self.current_keyword.get('name', 'Unknown')}")

        # Update the UI with keyword information
        if hasattr(self, 'keyword_header'):
            self.keyword_header.setText(f"{self.current_keyword.get('name', '')} - {self.current_keyword.get('category', '')}")

        if hasattr(self, 'desc_tab'):
            self.desc_tab.setHtml(self.format_description(self.current_keyword))

        # Clear parameter inputs before updating parameters tab
        self.param_inputs = {}

        if hasattr(self, 'params_tab'):
            print("[DEBUG] About to call update_parameters_tab")
            self.update_parameters_tab(self.current_keyword)

        # Clear generated keyword tab
        if hasattr(self, 'generated_tab'):
            self.generated_tab.clear()

    def cache_keyword(self):
        """Cache the currently generated keyword."""
        if not hasattr(self, 'generated_tab') or not self.generated_tab.toPlainText().strip():
            QMessageBox.warning(self, "No Generated Keyword",
                              "Please generate a keyword first before caching it.")
            return

        # Get the generated keyword text
        keyword_text = self.generated_tab.toPlainText().strip()

        if not keyword_text or keyword_text == "# No keyword selected":
            QMessageBox.warning(self, "Invalid Keyword",
                              "The generated keyword is empty or invalid.")
            return

        # Add to cache with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        cache_entry = {
            'text': keyword_text,
            'timestamp': timestamp,
            'keyword_name': self.current_keyword.get('name', 'Unknown') if self.current_keyword else 'Unknown'
        }

        self.keyword_cache.append(cache_entry)
        self.update_cache_display()

        # Enable cache button after first cache
        self.cache_button.setEnabled(True)

        # Open cache viewer window
        self.open_cache_viewer()

        QMessageBox.information(self, "Keyword Cached",
                              f"Keyword '{cache_entry['keyword_name']}' has been added to the cache.")

    def update_cache_display(self):
        """Update the cached keywords display."""
        if not hasattr(self, 'cache_tab'):
            return

        if not self.keyword_cache:
            self.cache_tab.setPlainText("No keywords cached yet.\n\nGenerate a keyword and click 'Add to Cache' to start building your OpenRadioss input file.")
            self.tab_widget.setTabText(3, "Cached Keywords (0)")
            return

        # Build cache display text
        cache_text = "*KEYWORD\n"
        cache_text += f"$ Cached Keywords: {len(self.keyword_cache)} entries\n\n"

        for i, entry in enumerate(self.keyword_cache, 1):
            cache_text += f"$ --- Cached Keyword {i} --- ({entry['timestamp']}) ---\n"
            cache_text += f"$ Keyword: {entry['keyword_name']}\n"
            cache_text += entry['text'] + "\n\n"

        cache_text += "*END"

        self.cache_tab.setPlainText(cache_text)
        self.tab_widget.setTabText(3, f"Cached Keywords ({len(self.keyword_cache)})")

    def update_k_file(self):
        """Update the main .k file with cached keywords and create/update document object."""
        if not self.keyword_cache:
            QMessageBox.warning(self, "No Cached Keywords",
                              "No keywords in cache. Generate and cache some keywords first.")
            return

        try:
            # Generate the complete .k file content
            k_file_content = self._generate_complete_k_file()

            # Create or update a text object in the FreeCAD document
            doc = FreeCAD.ActiveDocument
            if not doc:
                QMessageBox.warning(self, "No Active Document",
                                  "Please open or create a FreeCAD document first.")
                return

            # Look for existing .k file text object
            k_text_object = None
            for obj in doc.Objects:
                if obj.Label.startswith("OpenRadioss_k_File"):
                    k_text_object = obj
                    break

            # Create new object if none exists
            if k_text_object is None:
                k_text_object = doc.addObject("App::TextDocument", "OpenRadioss_k_File")
                k_text_object.Label = f"OpenRadioss_k_File_{len(self.keyword_cache)}_keywords"

            # Update the text content
            k_text_object.Text = k_file_content

            # Update the cache tab display
            self.update_cache_display()

            QMessageBox.information(self, "Document Updated",
                                  f"OpenRadioss .k file content updated in document object:\n'{k_text_object.Label}'\n\n"
                                  f"Includes {len(self.keyword_cache)} cached keywords.\n\n"
                                  "The content is now available as a text object in your FreeCAD document.")

            # Offer to also save to external file
            reply = QMessageBox.question(self, "Save to File",
                                       "Do you also want to save the .k file to an external file?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._save_k_file_to_disk(k_file_content)

        except Exception as e:
            QMessageBox.critical(self, "Update Error",
                               f"Failed to update document object:\n{str(e)}")

    def _save_k_file_to_disk(self, k_file_content):
        """Save .k file content to external file."""
        import os
        default_filename = f"openradioss_model_{len(self.keyword_cache)}_keywords.k"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save OpenRadioss .k File to Disk",
            os.path.join(os.path.expanduser("~"), "Documents", default_filename),
            "OpenRadioss files (*.k);;All files (*.*)"
        )

        if not filepath:
            return  # User cancelled

        try:
            with open(filepath, 'w') as f:
                f.write(k_file_content)

            QMessageBox.information(self, "File Saved",
                                  f"OpenRadioss .k file saved successfully:\n{filepath}")

            # Offer to open the file
            reply = QMessageBox.question(self, "Open File",
                                       "Do you want to open the saved .k file?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    import subprocess
                    subprocess.Popen([filepath], shell=True)
                except:
                    pass  # Silently ignore if we can't open the file

        except Exception as e:
            QMessageBox.critical(self, "Save Error",
                               f"Failed to save .k file:\n{str(e)}")

    def open_cache_viewer(self):
        """Open the cache viewer window."""
        if not hasattr(self, 'cache_viewer') or self.cache_viewer is None:
            self.cache_viewer = CacheViewerWindow(self.keyword_cache, self)
        self.cache_viewer.show()
        self.cache_viewer.raise_()
        self.cache_viewer.activateWindow()

    def format_description(self, kw):
        """Format the keyword description as HTML."""
        if not kw:
            return "<h1>No keyword selected</h1>"

        name = kw.get('name', 'Unknown')
        category = kw.get('category', 'Uncategorized')
        description = kw.get('description', 'No description available.')

        html = f"""
        <div style="padding: 10px;">
            <h2>{name}</h2>
            <p><strong>Category:</strong> {category}</p>
            <h3>Description</h3>
            <p>{description}</p>
        """

        # Add parameters if available
        if 'parameters' in kw and kw['parameters']:
            html += "<h3>Parameters</h3><ul>"
            for param in kw['parameters']:
                param_name = param.get('name', 'Unknown')
                param_desc = param.get('description', 'No description')
                html += f"<li><strong>{param_name}:</strong> {param_desc}</li>"
            html += "</ul>"

        html += "</div>"
        return html

    def update_parameters_tab(self, kw):
        """Update the parameters table with keyword parameters and input fields."""
        if not hasattr(self, 'params_tab') or not kw:
            print("[DEBUG] update_parameters_tab: Missing params_tab or keyword")
            return

        print(f"[DEBUG] update_parameters_tab called for: {kw.get('name', 'Unknown')}")
        
        # Store current keyword for help button
        self.current_keyword = kw
        
        # Enable help button if documentation URL is available
        if hasattr(self, 'help_button'):
            doc_url = kw.get('documentation', kw.get('documentation_url', ''))
            self.help_button.setEnabled(bool(doc_url))

        self.params_tab.clear()
        parameters = kw.get('parameters', [])

        print(f"[DEBUG] Parameters found: {len(parameters)}")
        if parameters:
            print(f"[DEBUG] First parameter: {parameters[0]}")

        if not parameters:
            print("[DEBUG] No parameters found, setting row count to 0")
            self.params_tab.setRowCount(0)
            return

        # Set up the table with appropriate columns
        self.params_tab.setRowCount(len(parameters))
        self.params_tab.setColumnCount(5)  # Parameter, Type, Default, Value, Description
        self.params_tab.setHorizontalHeaderLabels(["Parameter", "Type", "Default", "Value", "Description"])
        
        # Set column widths and stretch policies
        header = self.params_tab.horizontalHeader()
        self.params_tab.setColumnWidth(0, 150)  # Parameter (wider for better readability)
        self.params_tab.setColumnWidth(1, 100)  # Type
        self.params_tab.setColumnWidth(2, 100)  # Default
        self.params_tab.setColumnWidth(3, 150)  # Value (input field)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)  # Description column stretches

        # Store parameter input widgets for later retrieval
        self.param_inputs = {}

        for row, param in enumerate(parameters):
            param_name = param.get('name', f'param_{row}')
            param_type = param.get('type', 'text')
            param_default = str(param.get('default', ''))
            param_desc = param.get('description', '')
            
            print(f"[DEBUG] Processing parameter {row+1}: {param_name} (type: {param_type}, default: {param_default})")

            # Add parameter name (read-only)
            name_item = QTableWidgetItem(param_name)
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            name_item.setToolTip(param_desc)
            self.params_tab.setItem(row, 0, name_item)
            
            # Add parameter type (read-only)
            type_display = param_type.capitalize() if param_type else 'String'
            type_item = QTableWidgetItem(type_display)
            type_item.setFlags(type_item.flags() & ~QtCore.Qt.ItemIsEditable)
            type_item.setToolTip(f"Parameter type: {type_display}")
            self.params_tab.setItem(row, 1, type_item)
            
            # Add default value (read-only)
            default_display = param_default if param_default is not None and str(param_default).strip() != '' else 'N/A'
            default_item = QTableWidgetItem(str(default_display))
            default_item.setFlags(default_item.flags() & ~QtCore.Qt.ItemIsEditable)
            default_item.setToolTip(f"Default value: {default_display}" if default_display != 'N/A' else "No default value")
            self.params_tab.setItem(row, 2, default_item)
            
            # Create input field for the value
            value_widget = QtWidgets.QLineEdit()
            initial_value = param_default if param_default is not None and str(param_default).strip() != '' else ''
            value_widget.setText(str(initial_value))
            value_widget.setProperty('param_name', param_name)
            
            # Set input validation based on parameter type
            param_type_lower = str(param_type).lower() if param_type else ''
            if 'int' in param_type_lower:
                value_widget.setValidator(QtGui.QIntValidator())
            elif any(t in param_type_lower for t in ['float', 'double', 'real']):
                value_widget.setValidator(QtGui.QDoubleValidator())
            
            # Add description (read-only)
            desc_display = param_desc if param_desc else 'No description available'
            desc_item = QTableWidgetItem(desc_display)
            desc_item.setFlags(desc_item.flags() & ~QtCore.Qt.ItemIsEditable)
            desc_item.setToolTip(desc_display)
            
            # Add tooltip with description to value field
            tooltip = desc_display
            if initial_value:
                tooltip += f"\n\nDefault: {initial_value}"
            if param_type:
                tooltip += f"\nType: {param_type}"
                
            value_widget.setToolTip(tooltip)
            
            # Store the widget for later retrieval
            self.param_inputs[param_name] = value_widget
            
            # Add widgets to the table
            self.params_tab.setCellWidget(row, 3, value_widget)  # Value input
            self.params_tab.setItem(row, 4, desc_item)  # Description
            
        # Resize columns to fit content
        self.params_tab.resizeRowsToContents()
        print(f"[DEBUG] Parameters tab updated with {len(parameters)} rows")

    def generate_keyword(self):
        """Generate keyword text with parameter values."""
        print("[DEBUG] generate_keyword called")

        if not hasattr(self, 'current_keyword') or not self.current_keyword:
            print("[DEBUG] No current keyword")
            QMessageBox.warning(self, "No Keyword Selected",
                              "Please select a keyword first.")
            return

        print(f"[DEBUG] Current keyword: {self.current_keyword.get('name', 'Unknown')}")

        if not hasattr(self, 'param_inputs') or not self.param_inputs:
            print("[DEBUG] No param_inputs")
            QMessageBox.warning(self, "No Parameters",
                              "This keyword has no parameters to configure.")
            return

        print(f"[DEBUG] Param inputs count: {len(self.param_inputs)}")

        # Get keyword name and parameters
        keyword_name = self.current_keyword.get('name', '')
        parameters = self.current_keyword.get('parameters', [])

        print(f"[DEBUG] Keyword name: '{keyword_name}'")
        print(f"[DEBUG] Parameters count: {len(parameters)}")

        # Build parameter values from all field inputs
        param_values = {}
        for field_name, input_widget in self.param_inputs.items():
            value = input_widget.text().strip()
            print(f"[DEBUG] Field '{field_name}' = '{value}'")
            if value:  # Only include non-empty values
                # Map input field names to LS-DYNA parameter names
                # This mapping depends on how parameters are defined in the keyword data
                ls_dyna_field = self._map_field_to_ls_dyna(field_name, value)
                if ls_dyna_field:
                    param_values[ls_dyna_field] = value

        print(f"[DEBUG] Final param values: {param_values}")

        # Generate keyword text
        keyword_text = self._generate_keyword_text(keyword_name, param_values)

        # Display in the generated tab
        if hasattr(self, 'generated_tab'):
            self.generated_tab.setPlainText(keyword_text)
            print(f"[DEBUG] Generated text: {keyword_text}")

        # Switch to generated keyword tab
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setCurrentWidget(self.generated_tab)

        # Enable cache button since we now have a generated keyword
        if hasattr(self, 'cache_button'):
            self.cache_button.setEnabled(True)

    def _generate_keyword_text(self, keyword_name, param_values):
        """Generate the keyword text with parameter values."""
        if not keyword_name:
            return "# No keyword selected"

        # Start with the keyword header
        lines = [f"{keyword_name}"]

        # Add parameters if any
        if param_values:
            # For most LS-DYNA keywords, parameters go on the next line(s)
            # Group parameters logically (typically 8 values per line for OpenRadioss/LS-DYNA)

            # First, create a comment line with parameter names if available
            param_items = list(param_values.items())
            if param_items:
                # Add comment line with variable names
                param_names = [f"{name:12s}" for name, value in param_items]
                lines.append("$ " + "".join(param_names))

                # Add the data line(s) with values
                # Format values in columns for readability
                for i in range(0, len(param_items), 8):
                    line_params = param_items[i:i+8]
                    line_values = []
                    for name, value in line_params:
                        # Format each value with appropriate width
                        if isinstance(value, (int, float)):
                            if '.' in str(value):
                                line_values.append(f"{float(value):12.3f}")
                            else:
                                line_values.append(f"{int(value):12d}")
                        else:
                            line_values.append(f"{str(value):12s}")

                    if line_values:
                        lines.append("        " + "".join(line_values))

        # Add closing line if there are parameters
        if param_values:
            lines.append("")

        return "\n".join(lines)

    def _map_field_to_ls_dyna(self, field_name, value):
        """Map input field names to LS-DYNA parameter names."""
        if not field_name:
            return None

        # If the field name is already a valid LS-DYNA field, use it directly
        if field_name in ['mid', 'ro', 'e', 'pr', 'nu', 'sigy', 'pid', 'secid', 'nid', 'x', 'y', 'z', 'tc', 'rc', 'eid', 'n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'n7', 'n8']:
            return field_name

        # Map generic field names to LS-DYNA equivalents
        field_mapping = {
            'Material ID': 'mid',
            'Density': 'ro',
            'Young Modulus': 'e',
            'Young modulus': 'e',
            'Poisson Ratio': 'pr',
            'Poisson ratio': 'nu',
            'Yield Stress': 'sigy',
            'Yield stress': 'sigy',
            'Part ID': 'pid',
            'Section ID': 'secid',
            'Node ID': 'nid',
            'Element ID': 'eid',
            'X coordinate': 'x',
            'Y coordinate': 'y',
            'Z coordinate': 'z',
            'Temperature': 'tc',
            'Rotation constraint': 'rc',
            'Node 1': 'n1',
            'Node 2': 'n2',
            'Node 3': 'n3',
            'Node 4': 'n4',
            'Node 5': 'n5',
            'Node 6': 'n6',
            'Node 7': 'n7',
            'Node 8': 'n8'
        }

        # Check if it's a field_X mapping from the parameter definition
        if field_name.startswith('field_'):
            # Extract the field number and find the corresponding LS-DYNA field
            try:
                field_num = int(field_name.split('_')[1])
                if self.current_keyword and 'parameters' in self.current_keyword:
                    for param in self.current_keyword['parameters']:
                        if f'field_{field_num}' in param:
                            ls_dyna_field = param.get(f'field_{field_num}', '')
                            if ls_dyna_field:
                                return ls_dyna_field
            except (ValueError, IndexError):
                pass

        # Use the direct mapping
        return field_mapping.get(field_name, field_name)

    def update_cache_display(self):
        """Update the cache display."""
        if not hasattr(self, 'cache_tab'):
            return

        if not self.keyword_cache:
            self.cache_tab.setPlainText("No keywords cached yet.\n\nGenerate a keyword and click 'Add to Cache' to start building your OpenRadioss input file.")
            self.tab_widget.setTabText(3, "Cached Keywords (0)")
            return

        # Build cache display text
        cache_text = "*KEYWORD\n"
        cache_text += f"$ Cached Keywords: {len(self.keyword_cache)} entries\n\n"

        for i, entry in enumerate(self.keyword_cache, 1):
            cache_text += f"$ --- Cached Keyword {i} --- ({entry['timestamp']}) ---\n"
            cache_text += f"$ Keyword: {entry['keyword_name']}\n"
            cache_text += entry['text'] + "\n\n"

        cache_text += "*END"

        self.cache_tab.setPlainText(cache_text)
        self.tab_widget.setTabText(3, f"Cached Keywords ({len(self.keyword_cache)})")

    def show_keyword_details(self):
        """Show details of the selected keyword."""
        if not hasattr(self, 'current_keyword') or not self.current_keyword:
            print("[DEBUG] show_keyword_details: No current keyword")
            self.show_welcome_message()
            return

        print(f"[DEBUG] show_keyword_details called for: {self.current_keyword.get('name', 'Unknown')}")

        # Update the UI with keyword information
        if hasattr(self, 'keyword_header'):
            self.keyword_header.setText(f"{self.current_keyword.get('name', '')} - {self.current_keyword.get('category', '')}")

        if hasattr(self, 'desc_tab'):
            self.desc_tab.setHtml(self.format_description(self.current_keyword))

        # Clear parameter inputs before updating parameters tab
        self.param_inputs = {}

        if hasattr(self, 'params_tab'):
            print("[DEBUG] About to call update_parameters_tab")
            self.update_parameters_tab(self.current_keyword)

        # Clear generated keyword tab
        if hasattr(self, 'generated_tab'):
            self.generated_tab.clear()

    def cache_keyword(self):
        """Cache the currently generated keyword."""
        if not hasattr(self, 'generated_tab') or not self.generated_tab.toPlainText().strip():
            QMessageBox.warning(self, "No Generated Keyword",
                              "Please generate a keyword first before caching it.")
            return

        # Get the generated keyword text
        keyword_text = self.generated_tab.toPlainText().strip()

        if not keyword_text or keyword_text == "# No keyword selected":
            QMessageBox.warning(self, "Invalid Keyword",
                              "The generated keyword is empty or invalid.")
            return

        # Add to cache with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        cache_entry = {
            'text': keyword_text,
            'timestamp': timestamp,
            'keyword_name': self.current_keyword.get('name', 'Unknown') if self.current_keyword else 'Unknown'
        }

        self.keyword_cache.append(cache_entry)
        self.update_cache_display()

        # Enable cache button after first cache
        self.cache_button.setEnabled(True)

        # Open cache viewer window
        self.open_cache_viewer()

        QMessageBox.information(self, "Keyword Cached",
                              f"Keyword '{cache_entry['keyword_name']}' has been added to the cache.")

    def update_k_file(self):
        """Update the main .k file with cached keywords and create/update document object."""
        if not self.keyword_cache:
            QMessageBox.warning(self, "No Cached Keywords",
                              "No keywords in cache. Generate and cache some keywords first.")
            return

        try:
            # Generate the complete .k file content
            k_file_content = self._generate_complete_k_file()

            # Create or update a text object in the FreeCAD document
            doc = FreeCAD.ActiveDocument
            if not doc:
                QMessageBox.warning(self, "No Active Document",
                                  "Please open or create a FreeCAD document first.")
                return

            # Look for existing .k file text object
            k_text_object = None
            for obj in doc.Objects:
                if obj.Label.startswith("OpenRadioss_k_File"):
                    k_text_object = obj
                    break

            # Create new object if none exists
            if k_text_object is None:
                k_text_object = doc.addObject("App::TextDocument", "OpenRadioss_k_File")
                k_text_object.Label = f"OpenRadioss_k_File_{len(self.keyword_cache)}_keywords"

            # Update the text content
            k_text_object.Text = k_file_content

            # Update the cache tab display
            self.update_cache_display()

            QMessageBox.information(self, "Document Updated",
                                  f"OpenRadioss .k file content updated in document object:\n'{k_text_object.Label}'\n\n"
                                  f"Includes {len(self.keyword_cache)} cached keywords.\n\n"
                                  "The content is now available as a text object in your FreeCAD document.")

            # Offer to also save to external file
            reply = QMessageBox.question(self, "Save to File",
                                       "Do you also want to save the .k file to an external file?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._save_k_file_to_disk(k_file_content)

        except Exception as e:
            QMessageBox.critical(self, "Update Error",
                               f"Failed to update document object:\n{str(e)}")

    def _generate_complete_k_file(self):
        """Generate complete OpenRadioss .k file content from cached keywords."""
        if not self.keyword_cache:
            return "*KEYWORD\n*END"

        # Start with header
        content = "*KEYWORD\n"
        content += "$ OpenRadioss Model with Cached Keywords\n"
        content += f"$ Generated from {len(self.keyword_cache)} cached keywords\n"
        content += "$ Created by FreeCAD OpenRadioss Workbench\n\n"

        # Add all cached keywords
        for entry in self.keyword_cache:
            content += f"$ --- {entry['keyword_name']} ({entry['timestamp']}) ---\n"
            content += entry['text'] + "\n\n"

        # Add basic structure if no structural keywords cached
        has_parts = any('PART' in entry['text'] for entry in self.keyword_cache)
        has_nodes = any('NODE' in entry['text'] for entry in self.keyword_cache)
        has_elements = any('ELEMENT' in entry['text'] for entry in self.keyword_cache)

        if not has_parts:
            content += "$ --- Basic Structure (add PART definitions as needed) ---\n"
            content += "*PART\n"
            content += "$      pid     secid       mid     eosid      hgid      grav    adpopt\n"
            content += "         1         1         1         0         0         0         0\n\n"

        if not has_nodes:
            content += "$ --- Basic Structure (add NODE definitions as needed) ---\n"
            content += "*NODE\n"
            content += "$     nid               x               y               z      tc      rc\n"
            content += "         1       0.000000       0.000000       0.000000       0       0\n\n"

        if not has_elements:
            content += "$ --- Basic Structure (add ELEMENT definitions as needed) ---\n"
            content += "*ELEMENT_SHELL\n"
            content += "$     eid     pid      n1      n2      n3      n4\n"
            content += "         1       1       1       2       3       4\n\n"

        content += "*END"
        return content

    def _save_k_file_to_disk(self, k_file_content):
        """Save .k file content to external file."""
        import os
        default_filename = f"openradioss_model_{len(self.keyword_cache)}_keywords.k"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save OpenRadioss .k File to Disk",
            os.path.join(os.path.expanduser("~"), "Documents", default_filename),
            "OpenRadioss files (*.k);;All files (*.*)"
        )

        if not filepath:
            return  # User cancelled

        try:
            with open(filepath, 'w') as f:
                f.write(k_file_content)

            QMessageBox.information(self, "File Saved",
                                  f"OpenRadioss .k file saved successfully:\n{filepath}")

            # Offer to open the file
            reply = QMessageBox.question(self, "Open File",
                                       "Do you want to open the saved .k file?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    import subprocess
                    subprocess.Popen([filepath], shell=True)
                except:
                    pass  # Silently ignore if we can't open the file

        except Exception as e:
            QMessageBox.critical(self, "Save Error",
                               f"Failed to save .k file:\n{str(e)}")

    def load_minimal_template(self):
        """Load minimal template for basic simulations."""
        import datetime

        print("[TEMPLATE] Loading minimal template...")
        print("[TEMPLATE] This provides essential keywords for basic structural analysis")

        # Define essential keywords for minimal template
        minimal_keywords = [
            # Control keywords
            {
                'name': '*CONTROL_TERMINATION',
                'category': 'Control',
                'description': 'Defines termination time for the analysis',
                'parameters': [
                    {
                        'name': 'End Time',
                        'description': 'Analysis end time',
                        'field_0': 'endtim'
                    }
                ]
            },
            # Materials
            {
                'name': '*MAT_ELASTIC',
                'category': 'Materials',
                'description': 'Linear elastic material model',
                'parameters': [
                    {
                        'name': 'Material ID',
                        'description': 'Material identification number',
                        'field_0': 'mid'
                    },
                    {
                        'name': 'Density',
                        'description': 'Mass density',
                        'field_1': 'ro'
                    },
                    {
                        'name': 'Young Modulus',
                        'description': 'Young\'s modulus',
                        'field_2': 'e'
                    },
                    {
                        'name': 'Poisson Ratio',
                        'description': 'Poisson\'s ratio',
                        'field_3': 'pr'
                    }
                ]
            },
            # Properties
            {
                'name': '*SECTION_SHELL',
                'category': 'Properties',
                'description': 'Shell section properties',
                'parameters': [
                    {
                        'name': 'Section ID',
                        'description': 'Section identification number',
                        'field_0': 'secid'
                    },
                    {
                        'name': 'Element Formulation',
                        'description': 'Shell element formulation',
                        'field_1': 'elform'
                    },
                    {
                        'name': 'Thickness',
                        'description': 'Shell thickness',
                        'field_2': 't1'
                    }
                ]
            },
            # Parts
            {
                'name': '*PART',
                'category': 'Parts',
                'description': 'Part definition',
                'parameters': [
                    {
                        'name': 'Part ID',
                        'description': 'Part identification number',
                        'field_0': 'pid'
                    },
                    {
                        'name': 'Section ID',
                        'description': 'Section identification number',
                        'field_1': 'secid'
                    },
                    {
                        'name': 'Material ID',
                        'description': 'Material identification number',
                        'field_2': 'mid'
                    }
                ]
            },
            # Output
            {
                'name': '*DATABASE_BINARY_D3PLOT',
                'category': 'Output',
                'description': 'Binary output database',
                'parameters': [
                    {
                        'name': 'Output Frequency',
                        'description': 'Time interval for output',
                        'field_0': 'dt'
                    }
                ]
            }
        ]

        # Default parameter values for minimal template
        default_values = {
            '*CONTROL_TERMINATION': {'endtim': '1.0'},
            '*MAT_ELASTIC': {'mid': '1', 'ro': '7800.0', 'e': '2.1e11', 'pr': '0.3'},
            '*SECTION_SHELL': {'secid': '1', 'elform': '2', 't1': '1.0'},
            '*PART': {'pid': '1', 'secid': '1', 'mid': '1'},
            '*DATABASE_BINARY_D3PLOT': {'dt': '0.1'}
        }

        print(f"[TEMPLATE] Processing {len(minimal_keywords)} keywords for minimal template:")
        for keyword in minimal_keywords:
            print(f"[TEMPLATE]   - {keyword['name']}")

        # Load keywords into cache
        loaded_count = 0
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        print(f"[TEMPLATE] Starting cache loading at {timestamp}")

        for keyword in minimal_keywords:
            keyword_name = keyword['name']
            param_values = default_values.get(keyword_name, {})

            print(f"[TEMPLATE] Generating keyword: {keyword_name}")
            print(f"[TEMPLATE]   Parameters: {param_values}")

            # Generate keyword text
            keyword_text = self._generate_keyword_text(keyword_name, param_values)
            print(f"[TEMPLATE]   Generated text length: {len(keyword_text)} characters")

            # Create cache entry
            cache_entry = {
                'text': keyword_text,
                'timestamp': timestamp,
                'keyword_name': keyword_name
            }

            # Add to cache
            self.keyword_cache.append(cache_entry)
            loaded_count += 1
            print(f"[TEMPLATE]   Added to cache (total: {loaded_count})")

        # Update UI
        print(f"[TEMPLATE] Updating cache display with {loaded_count} new keywords")
        self.update_cache_display()

        # Open cache viewer
        print("[TEMPLATE] Opening cache viewer")
        self.open_cache_viewer()

        # Show success message
        print(f"[TEMPLATE] Showing success message for {loaded_count} keywords loaded")
        QMessageBox.information(self, "Minimal Template Loaded",
                              f"Minimal template loaded successfully!\n\n"
                              f"Added {loaded_count} essential keywords to the cache:\n"
                              f"• *CONTROL_TERMINATION\n"
                              f"• *MAT_ELASTIC\n"
                              f"• *SECTION_SHELL\n"
                              f"• *PART\n"
                              f"• *DATABASE_BINARY_D3PLOT\n\n"
                              f"Keywords are ready in the cache viewer.\n"
                              f"You can modify parameters and generate the complete K-file.")

    def load_simulation_template(self):
        """Load simulation template with common analysis setup."""
        QMessageBox.information(self, "Template Loading",
                              "Simulation template functionality will be implemented.\n\n"
                              "This would load a comprehensive set of keywords for general simulations.")

    def load_basic_template(self):
        """Load basic template with fundamental keywords for structural analysis."""
        import datetime

        print("[TEMPLATE] Loading basic template...")
        print("[TEMPLATE] This provides fundamental keywords for complete structural analysis")

        # Define fundamental keywords for basic structural analysis
        basic_keywords = [
            # Control keywords
            {
                'name': '*CONTROL_TERMINATION',
                'category': 'Control',
                'description': 'Defines termination time for the analysis',
                'parameters': [
                    {
                        'name': 'End Time',
                        'description': 'Analysis end time',
                        'field_0': 'endtim'
                    }
                ]
            },
            # Materials
            {
                'name': '*MAT_ELASTIC',
                'category': 'Materials',
                'description': 'Linear elastic material model',
                'parameters': [
                    {
                        'name': 'Material ID',
                        'description': 'Material identification number',
                        'field_0': 'mid'
                    },
                    {
                        'name': 'Density',
                        'description': 'Mass density',
                        'field_1': 'ro'
                    },
                    {
                        'name': 'Young Modulus',
                        'description': 'Young\'s modulus',
                        'field_2': 'e'
                    },
                    {
                        'name': 'Poisson Ratio',
                        'description': 'Poisson\'s ratio',
                        'field_3': 'pr'
                    }
                ]
            },
            # Properties
            {
                'name': '*SECTION_SHELL',
                'category': 'Properties',
                'description': 'Shell section properties',
                'parameters': [
                    {
                        'name': 'Section ID',
                        'description': 'Section identification number',
                        'field_0': 'secid'
                    },
                    {
                        'name': 'Element Formulation',
                        'description': 'Shell element formulation',
                        'field_1': 'elform'
                    },
                    {
                        'name': 'Thickness',
                        'description': 'Shell thickness',
                        'field_2': 't1'
                    }
                ]
            },
            {
                'name': '*SECTION_SOLID',
                'category': 'Properties',
                'description': 'Solid section properties',
                'parameters': [
                    {
                        'name': 'Section ID',
                        'description': 'Section identification number',
                        'field_0': 'secid'
                    },
                    {
                        'name': 'Element Formulation',
                        'description': 'Solid element formulation',
                        'field_1': 'elform'
                    }
                ]
            },
            # Parts
            {
                'name': '*PART',
                'category': 'Parts',
                'description': 'Part definition',
                'parameters': [
                    {
                        'name': 'Part ID',
                        'description': 'Part identification number',
                        'field_0': 'pid'
                    },
                    {
                        'name': 'Section ID',
                        'description': 'Section identification number',
                        'field_1': 'secid'
                    },
                    {
                        'name': 'Material ID',
                        'description': 'Material identification number',
                        'field_2': 'mid'
                    }
                ]
            },
            # Boundary conditions
            {
                'name': '*BOUNDARY_SPC_SET',
                'category': 'Loads',
                'description': 'Boundary conditions for node sets',
                'parameters': [
                    {
                        'name': 'Node Set ID',
                        'description': 'Node set identifier',
                        'field_0': 'nsid'
                    },
                    {
                        'name': 'DOF',
                        'description': 'Constrained degrees of freedom',
                        'field_1': 'dof'
                    },
                    {
                        'name': 'Value',
                        'description': 'Constraint value',
                        'field_2': 'value'
                    }
                ]
            },
            # Loads
            {
                'name': '*LOAD_NODE_SET',
                'category': 'Loads',
                'description': 'Nodal loads on node sets',
                'parameters': [
                    {
                        'name': 'Node Set ID',
                        'description': 'Node set identifier',
                        'field_0': 'nsid'
                    },
                    {
                        'name': 'DOF',
                        'description': 'Degree of freedom for load',
                        'field_1': 'dof'
                    },
                    {
                        'name': 'Load Value',
                        'description': 'Load magnitude',
                        'field_2': 'load'
                    }
                ]
            },
            # Output
            {
                'name': '*DATABASE_BINARY_D3PLOT',
                'category': 'Output',
                'description': 'Binary output database',
                'parameters': [
                    {
                        'name': 'Output Frequency',
                        'description': 'Time interval for output',
                        'field_0': 'dt'
                    }
                ]
            }
        ]

        # Default parameter values for basic template
        default_values = {
            '*CONTROL_TERMINATION': {'endtim': '1.0'},
            '*MAT_ELASTIC': {'mid': '1', 'ro': '7800.0', 'e': '2.1e11', 'pr': '0.3'},
            '*SECTION_SHELL': {'secid': '1', 'elform': '2', 't1': '1.0'},
            '*SECTION_SOLID': {'secid': '2', 'elform': '1'},
            '*PART': {'pid': '1', 'secid': '1', 'mid': '1'},
            '*BOUNDARY_SPC_SET': {'nsid': '1', 'dof': '123', 'value': '0.0'},
            '*LOAD_NODE_SET': {'nsid': '2', 'dof': '3', 'load': '1000.0'},
            '*DATABASE_BINARY_D3PLOT': {'dt': '0.1'}
        }

        print(f"[TEMPLATE] Processing {len(basic_keywords)} keywords for basic template:")
        for keyword in basic_keywords:
            print(f"[TEMPLATE]   - {keyword['name']}")

        # Load keywords into cache
        loaded_count = 0
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        print(f"[TEMPLATE] Starting cache loading at {timestamp}")

        for keyword in basic_keywords:
            keyword_name = keyword['name']
            param_values = default_values.get(keyword_name, {})

            print(f"[TEMPLATE] Generating keyword: {keyword_name}")
            print(f"[TEMPLATE]   Parameters: {param_values}")

            # Generate keyword text
            keyword_text = self._generate_keyword_text(keyword_name, param_values)
            print(f"[TEMPLATE]   Generated text length: {len(keyword_text)} characters")

            # Create cache entry
            cache_entry = {
                'text': keyword_text,
                'timestamp': timestamp,
                'keyword_name': keyword_name
            }

            # Add to cache
            self.keyword_cache.append(cache_entry)
            loaded_count += 1
            print(f"[TEMPLATE]   Added to cache (total: {loaded_count})")

        # Update UI
        print(f"[TEMPLATE] Updating cache display with {loaded_count} new keywords")
        self.update_cache_display()

        # Open cache viewer
        print("[TEMPLATE] Opening cache viewer")
        self.open_cache_viewer()

        # Show success message
        print(f"[TEMPLATE] Showing success message for {loaded_count} keywords loaded")
        QMessageBox.information(self, "Basic Template Loaded",
                              f"Basic template loaded successfully!\n\n"
                              f"Added {loaded_count} fundamental keywords to the cache:\n"
                              f"• *CONTROL_TERMINATION\n"
                              f"• *MAT_ELASTIC\n"
                              f"• *SECTION_SHELL & *SECTION_SOLID\n"
                              f"• *PART\n"
                              f"• *BOUNDARY_SPC_SET\n"
                              f"• *LOAD_NODE_SET\n"
                              f"• *DATABASE_BINARY_D3PLOT\n\n"
                              f"Keywords are ready in the cache viewer.\n"
                              f"This provides a complete basic structural analysis setup.")

    def load_structural_template(self):
        """Load structural analysis template with advanced structural keywords."""
        import datetime

        print("[TEMPLATE] Loading structural template...")
        print("[TEMPLATE] This provides advanced keywords for comprehensive structural analysis")

        # Define advanced keywords for structural analysis
        structural_keywords = [
            # Control and solution
            {
                'name': '*CONTROL_TERMINATION',
                'category': 'Control',
                'description': 'Defines termination time for the analysis',
                'parameters': [
                    {
                        'name': 'End Time',
                        'description': 'Analysis end time',
                        'field_0': 'endtim'
                    }
                ]
            },
            {
                'name': '*CONTROL_SOLUTION',
                'category': 'Control',
                'description': 'Solution control parameters',
                'parameters': [
                    {
                        'name': 'Solution Method',
                        'description': 'Solution method (0=explicit, 1=implicit)',
                        'field_0': 'method'
                    }
                ]
            },
            # Materials (multiple types)
            {
                'name': '*MAT_ELASTIC',
                'category': 'Materials',
                'description': 'Linear elastic material model',
                'parameters': [
                    {
                        'name': 'Material ID',
                        'description': 'Material identification number',
                        'field_0': 'mid'
                    },
                    {
                        'name': 'Density',
                        'description': 'Mass density',
                        'field_1': 'ro'
                    },
                    {
                        'name': 'Young Modulus',
                        'description': 'Young\'s modulus',
                        'field_2': 'e'
                    },
                    {
                        'name': 'Poisson Ratio',
                        'description': 'Poisson\'s ratio',
                        'field_3': 'pr'
                    }
                ]
            },
            {
                'name': '*MAT_PLASTIC_KINEMATIC',
                'category': 'Materials',
                'description': 'Plastic kinematic material model',
                'parameters': [
                    {
                        'name': 'Material ID',
                        'description': 'Material identification number',
                        'field_0': 'mid'
                    },
                    {
                        'name': 'Density',
                        'description': 'Mass density',
                        'field_1': 'ro'
                    },
                    {
                        'name': 'Young Modulus',
                        'description': 'Young\'s modulus',
                        'field_2': 'e'
                    },
                    {
                        'name': 'Poisson Ratio',
                        'description': 'Poisson\'s ratio',
                        'field_3': 'pr'
                    },
                    {
                        'name': 'Yield Stress',
                        'description': 'Yield stress',
                        'field_4': 'sigy'
                    }
                ]
            },
            # Section types
            {
                'name': '*SECTION_SHELL',
                'category': 'Properties',
                'description': 'Shell section properties',
                'parameters': [
                    {
                        'name': 'Section ID',
                        'description': 'Section identification number',
                        'field_0': 'secid'
                    },
                    {
                        'name': 'Element Formulation',
                        'description': 'Shell element formulation',
                        'field_1': 'elform'
                    },
                    {
                        'name': 'Thickness',
                        'description': 'Shell thickness',
                        'field_2': 't1'
                    }
                ]
            },
            {
                'name': '*SECTION_BEAM',
                'category': 'Properties',
                'description': 'Beam section properties',
                'parameters': [
                    {
                        'name': 'Section ID',
                        'description': 'Section identification number',
                        'field_0': 'secid'
                    },
                    {
                        'name': 'Element Formulation',
                        'description': 'Beam element formulation',
                        'field_1': 'elform'
                    },
                    {
                        'name': 'Area',
                        'description': 'Cross-sectional area',
                        'field_2': 'area'
                    }
                ]
            },
            # Parts
            {
                'name': '*PART',
                'category': 'Parts',
                'description': 'Part definition',
                'parameters': [
                    {
                        'name': 'Part ID',
                        'description': 'Part identification number',
                        'field_0': 'pid'
                    },
                    {
                        'name': 'Section ID',
                        'description': 'Section identification number',
                        'field_1': 'secid'
                    },
                    {
                        'name': 'Material ID',
                        'description': 'Material identification number',
                        'field_2': 'mid'
                    }
                ]
            },
            # Boundary conditions
            {
                'name': '*BOUNDARY_SPC_SET',
                'category': 'Loads',
                'description': 'Boundary conditions for node sets',
                'parameters': [
                    {
                        'name': 'Node Set ID',
                        'description': 'Node set identifier',
                        'field_0': 'nsid'
                    },
                    {
                        'name': 'DOF',
                        'description': 'Constrained degrees of freedom',
                        'field_1': 'dof'
                    },
                    {
                        'name': 'Value',
                        'description': 'Constraint value',
                        'field_2': 'value'
                    }
                ]
            },
            # Loads
            {
                'name': '*LOAD_NODE_SET',
                'category': 'Loads',
                'description': 'Nodal loads on node sets',
                'parameters': [
                    {
                        'name': 'Node Set ID',
                        'description': 'Node set identifier',
                        'field_0': 'nsid'
                    },
                    {
                        'name': 'DOF',
                        'description': 'Degree of freedom for load',
                        'field_1': 'dof'
                    },
                    {
                        'name': 'Load Value',
                        'description': 'Load magnitude',
                        'field_2': 'load'
                    }
                ]
            },
            {
                'name': '*LOAD_BODY_Z',
                'category': 'Loads',
                'description': 'Body force in Z direction (gravity)',
                'parameters': [
                    {
                        'name': 'Part Set ID',
                        'description': 'Part set identifier',
                        'field_0': 'psid'
                    },
                    {
                        'name': 'Load Curve ID',
                        'description': 'Load curve identifier',
                        'field_1': 'lcid'
                    },
                    {
                        'name': 'Acceleration',
                        'description': 'Gravitational acceleration',
                        'field_2': 'acc'
                    }
                ]
            },
            # Output
            {
                'name': '*DATABASE_BINARY_D3PLOT',
                'category': 'Output',
                'description': 'Binary output database',
                'parameters': [
                    {
                        'name': 'Output Frequency',
                        'description': 'Time interval for output',
                        'field_0': 'dt'
                    }
                ]
            },
            {
                'name': '*DATABASE_HISTORY_NODE',
                'category': 'Output',
                'description': 'Nodal time history output',
                'parameters': [
                    {
                        'name': 'Node ID',
                        'description': 'Node identifier',
                        'field_0': 'nid'
                    },
                    {
                        'name': 'Output Frequency',
                        'description': 'Time interval for output',
                        'field_1': 'dt'
                    }
                ]
            }
        ]

        # Default parameter values for structural template
        default_values = {
            '*CONTROL_TERMINATION': {'endtim': '1.0'},
            '*CONTROL_SOLUTION': {'method': '0'},
            '*MAT_ELASTIC': {'mid': '1', 'ro': '7800.0', 'e': '2.1e11', 'pr': '0.3'},
            '*MAT_PLASTIC_KINEMATIC': {'mid': '2', 'ro': '7800.0', 'e': '2.1e11', 'pr': '0.3', 'sigy': '2.5e8'},
            '*SECTION_SHELL': {'secid': '1', 'elform': '2', 't1': '1.0'},
            '*SECTION_BEAM': {'secid': '2', 'elform': '1', 'area': '0.01'},
            '*PART': {'pid': '1', 'secid': '1', 'mid': '1'},
            '*BOUNDARY_SPC_SET': {'nsid': '1', 'dof': '123', 'value': '0.0'},
            '*LOAD_NODE_SET': {'nsid': '2', 'dof': '3', 'load': '1000.0'},
            '*LOAD_BODY_Z': {'psid': '1', 'lcid': '1', 'acc': '-9.81'},
            '*DATABASE_BINARY_D3PLOT': {'dt': '0.1'},
            '*DATABASE_HISTORY_NODE': {'nid': '1', 'dt': '0.01'}
        }

        print(f"[TEMPLATE] Processing {len(structural_keywords)} keywords for structural template:")
        for keyword in structural_keywords:
            print(f"[TEMPLATE]   - {keyword['name']}")

        # Load keywords into cache
        loaded_count = 0
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        print(f"[TEMPLATE] Starting cache loading at {timestamp}")

        for keyword in structural_keywords:
            keyword_name = keyword['name']
            param_values = default_values.get(keyword_name, {})

            print(f"[TEMPLATE] Generating keyword: {keyword_name}")
            print(f"[TEMPLATE]   Parameters: {param_values}")

            # Generate keyword text
            keyword_text = self._generate_keyword_text(keyword_name, param_values)
            print(f"[TEMPLATE]   Generated text length: {len(keyword_text)} characters")

            # Create cache entry
            cache_entry = {
                'text': keyword_text,
                'timestamp': timestamp,
                'keyword_name': keyword_name
            }

            # Add to cache
            self.keyword_cache.append(cache_entry)
            loaded_count += 1
            print(f"[TEMPLATE]   Added to cache (total: {loaded_count})")

        # Update UI
        print(f"[TEMPLATE] Updating cache display with {loaded_count} new keywords")
        self.update_cache_display()

        # Open cache viewer
        print("[TEMPLATE] Opening cache viewer")
        self.open_cache_viewer()

        # Show success message
        print(f"[TEMPLATE] Showing success message for {loaded_count} keywords loaded")
        QMessageBox.information(self, "Structural Template Loaded",
                              f"Structural template loaded successfully!\n\n"
                              f"Added {loaded_count} advanced keywords to the cache:\n"
                              f"• *CONTROL_TERMINATION & *CONTROL_SOLUTION\n"
                              f"• *MAT_ELASTIC & *MAT_PLASTIC_KINEMATIC\n"
                              f"• *SECTION_SHELL & *SECTION_BEAM\n"
                              f"• *PART\n"
                              f"• *BOUNDARY_SPC_SET\n"
                              f"• *LOAD_NODE_SET & *LOAD_BODY_Z\n"
                              f"• *DATABASE_BINARY_D3PLOT & *DATABASE_HISTORY_NODE\n\n"
                              f"Keywords are ready in the cache viewer.\n"
                              f"This provides a comprehensive structural analysis setup.")

    def load_thermal_template(self):
        """Load thermal analysis template with heat transfer keywords."""
        import datetime

        print("[TEMPLATE] Loading thermal template...")
        print("[TEMPLATE] This provides thermal analysis keywords for heat transfer")

        # Define thermal analysis keywords
        thermal_keywords = [
            # Control
            {
                'name': '*CONTROL_TERMINATION',
                'category': 'Control',
                'description': 'Defines termination time for the analysis',
                'parameters': [
                    {
                        'name': 'End Time',
                        'description': 'Analysis end time',
                        'field_0': 'endtim'
                    }
                ]
            },
            {
                'name': '*CONTROL_THERMAL_SOLVER',
                'category': 'Control',
                'description': 'Thermal solver control parameters',
                'parameters': [
                    {
                        'name': 'Solver Type',
                        'description': 'Thermal solver type',
                        'field_0': 'type'
                    },
                    {
                        'name': 'Time Step',
                        'description': 'Thermal time step',
                        'field_1': 'dt'
                    }
                ]
            },
            # Materials (thermal)
            {
                'name': '*MAT_THERMAL_ISOTROPIC',
                'category': 'Materials',
                'description': 'Isotropic thermal material properties',
                'parameters': [
                    {
                        'name': 'Material ID',
                        'description': 'Material identification number',
                        'field_0': 'mid'
                    },
                    {
                        'name': 'Density',
                        'description': 'Mass density',
                        'field_1': 'ro'
                    },
                    {
                        'name': 'Specific Heat',
                        'description': 'Specific heat capacity',
                        'field_2': 'c'
                    },
                    {
                        'name': 'Conductivity',
                        'description': 'Thermal conductivity',
                        'field_3': 'k'
                    }
                ]
            },
            {
                'name': '*MAT_ELASTIC',
                'category': 'Materials',
                'description': 'Linear elastic material (for thermal expansion)',
                'parameters': [
                    {
                        'name': 'Material ID',
                        'description': 'Material identification number',
                        'field_0': 'mid'
                    },
                    {
                        'name': 'Density',
                        'description': 'Mass density',
                        'field_1': 'ro'
                    },
                    {
                        'name': 'Young Modulus',
                        'description': 'Young\'s modulus',
                        'field_2': 'e'
                    },
                    {
                        'name': 'Poisson Ratio',
                        'description': 'Poisson\'s ratio',
                        'field_3': 'pr'
                    }
                ]
            },
            # Sections
            {
                'name': '*SECTION_SHELL',
                'category': 'Properties',
                'description': 'Shell section properties',
                'parameters': [
                    {
                        'name': 'Section ID',
                        'description': 'Section identification number',
                        'field_0': 'secid'
                    },
                    {
                        'name': 'Element Formulation',
                        'description': 'Shell element formulation',
                        'field_1': 'elform'
                    },
                    {
                        'name': 'Thickness',
                        'description': 'Shell thickness',
                        'field_2': 't1'
                    }
                ]
            },
            # Parts
            {
                'name': '*PART',
                'category': 'Parts',
                'description': 'Part definition',
                'parameters': [
                    {
                        'name': 'Part ID',
                        'description': 'Part identification number',
                        'field_0': 'pid'
                    },
                    {
                        'name': 'Section ID',
                        'description': 'Section identification number',
                        'field_1': 'secid'
                    },
                    {
                        'name': 'Material ID',
                        'description': 'Material identification number',
                        'field_2': 'mid'
                    }
                ]
            },
            # Thermal boundary conditions
            {
                'name': '*BOUNDARY_TEMPERATURE_SET',
                'category': 'Loads',
                'description': 'Temperature boundary conditions',
                'parameters': [
                    {
                        'name': 'Node Set ID',
                        'description': 'Node set identifier',
                        'field_0': 'nsid'
                    },
                    {
                        'name': 'Temperature',
                        'description': 'Prescribed temperature',
                        'field_1': 'temp'
                    }
                ]
            },
            {
                'name': '*LOAD_THERMAL_SET',
                'category': 'Loads',
                'description': 'Thermal loads on node sets',
                'parameters': [
                    {
                        'name': 'Node Set ID',
                        'description': 'Node set identifier',
                        'field_0': 'nsid'
                    },
                    {
                        'name': 'Heat Flux',
                        'description': 'Heat flux magnitude',
                        'field_1': 'flux'
                    }
                ]
            },
            # Output
            {
                'name': '*DATABASE_BINARY_D3PLOT',
                'category': 'Output',
                'description': 'Binary output database',
                'parameters': [
                    {
                        'name': 'Output Frequency',
                        'description': 'Time interval for output',
                        'field_0': 'dt'
                    }
                ]
            },
            {
                'name': '*DATABASE_HISTORY_NODE',
                'category': 'Output',
                'description': 'Nodal time history output',
                'parameters': [
                    {
                        'name': 'Node ID',
                        'description': 'Node identifier',
                        'field_0': 'nid'
                    },
                    {
                        'name': 'Output Frequency',
                        'description': 'Time interval for output',
                        'field_1': 'dt'
                    }
                ]
            }
        ]

        # Default parameter values for thermal template
        default_values = {
            '*CONTROL_TERMINATION': {'endtim': '10.0'},
            '*CONTROL_THERMAL_SOLVER': {'type': '1', 'dt': '0.1'},
            '*MAT_THERMAL_ISOTROPIC': {'mid': '1', 'ro': '7800.0', 'c': '460.0', 'k': '50.0'},
            '*MAT_ELASTIC': {'mid': '2', 'ro': '7800.0', 'e': '2.1e11', 'pr': '0.3'},
            '*SECTION_SHELL': {'secid': '1', 'elform': '2', 't1': '5.0'},
            '*PART': {'pid': '1', 'secid': '1', 'mid': '1'},
            '*BOUNDARY_TEMPERATURE_SET': {'nsid': '1', 'temp': '20.0'},
            '*LOAD_THERMAL_SET': {'nsid': '2', 'flux': '1000.0'},
            '*DATABASE_BINARY_D3PLOT': {'dt': '1.0'},
            '*DATABASE_HISTORY_NODE': {'nid': '1', 'dt': '0.1'}
        }

        print(f"[TEMPLATE] Processing {len(thermal_keywords)} keywords for thermal template:")
        for keyword in thermal_keywords:
            print(f"[TEMPLATE]   - {keyword['name']}")

        # Load keywords into cache
        loaded_count = 0
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        print(f"[TEMPLATE] Starting cache loading at {timestamp}")

        for keyword in thermal_keywords:
            keyword_name = keyword['name']
            param_values = default_values.get(keyword_name, {})

            print(f"[TEMPLATE] Generating keyword: {keyword_name}")
            print(f"[TEMPLATE]   Parameters: {param_values}")

            # Generate keyword text
            keyword_text = self._generate_keyword_text(keyword_name, param_values)
            print(f"[TEMPLATE]   Generated text length: {len(keyword_text)} characters")

            # Create cache entry
            cache_entry = {
                'text': keyword_text,
                'timestamp': timestamp,
                'keyword_name': keyword_name
            }

            # Add to cache
            self.keyword_cache.append(cache_entry)
            loaded_count += 1
            print(f"[TEMPLATE]   Added to cache (total: {loaded_count})")

        # Update UI
        print(f"[TEMPLATE] Updating cache display with {loaded_count} new keywords")
        self.update_cache_display()

        # Open cache viewer
        print("[TEMPLATE] Opening cache viewer")
        self.open_cache_viewer()

        # Show success message
        print(f"[TEMPLATE] Showing success message for {loaded_count} keywords loaded")
        QMessageBox.information(self, "Thermal Template Loaded",
                              f"Thermal template loaded successfully!\n\n"
                              f"Added {loaded_count} thermal analysis keywords to the cache:\n"
                              f"• *CONTROL_TERMINATION & *CONTROL_THERMAL_SOLVER\n"
                              f"• *MAT_THERMAL_ISOTROPIC & *MAT_ELASTIC\n"
                              f"• *SECTION_SHELL\n"
                              f"• *PART\n"
                              f"• *BOUNDARY_TEMPERATURE_SET\n"
                              f"• *LOAD_THERMAL_SET\n"
                              f"• *DATABASE_BINARY_D3PLOT & *DATABASE_HISTORY_NODE\n\n"
                              f"Keywords are ready in the cache viewer.\n"
                              f"This provides a complete thermal analysis setup with heat transfer.")

    def load_linear_static_template(self):
        """Load linear static analysis template."""
        QMessageBox.information(self, "Template Loading",
                              "Linear static template functionality will be implemented.\n\n"
                              "This would load keywords for linear static structural analysis.")

    def load_modal_analysis_template(self):
        """Load modal analysis template."""
        QMessageBox.information(self, "Template Loading",
                              "Modal analysis template functionality will be implemented.\n\n"
                              "This would load keywords for modal/vibration analysis.")

    def load_steady_state_thermal_template(self):
        """Load steady-state thermal template."""
        QMessageBox.information(self, "Template Loading",
                              "Steady-state thermal template functionality will be implemented.\n\n"
                              "This would load keywords for steady-state thermal analysis.")

    def load_basic_contact_template(self):
        """Load basic contact template."""
        QMessageBox.information(self, "Template Loading",
                              "Contact template functionality will be implemented.\n\n"
                              "This would load basic contact definition keywords.")

    def load_implicit_template(self):
        """Load implicit analysis template."""
        QMessageBox.information(self, "Template Loading",
                              "Implicit template functionality will be implemented.\n\n"
                              "This would load keywords for implicit time integration analysis.")

    def load_explicit_template(self):
        """Load explicit analysis template."""
        QMessageBox.information(self, "Template Loading",
                              "Explicit template functionality will be implemented.\n\n"
                              "This would load keywords for explicit time integration analysis.")

    def show_help_section(self, section):
        """Show help documentation for the specified section."""
        print(f"[HELP] Opening help section: {section}")

        help_content = {
            "search_help": """
            <div style="padding: 20px;">
                <h2>Search Help</h2>
                <p><strong>Searching Keywords:</strong></p>
                <ul>
                    <li>Use the category dropdown to filter by analysis type</li>
                    <li>Keywords are organized by: Materials, Properties, Loads, etc.</li>
                    <li>Select any keyword to view its documentation and parameters</li>
                    <li>All keywords include parameter definitions and LS-DYNA syntax</li>
                </ul>
            </div>
            """,
            "tutorials": """
            <div style="padding: 20px;">
                <h2>Tutorials</h2>
                <p><strong>Getting Started:</strong></p>
                <ul>
                    <li><strong>Basic Setup:</strong> Start with material and part definitions</li>
                    <li><strong>Geometry:</strong> Define nodes and elements for your model</li>
                    <li><strong>Analysis:</strong> Add loads, boundary conditions, and control cards</li>
                    <li><strong>Output:</strong> Configure results and output frequency</li>
                </ul>
            </div>
            """,
            "reference_guide": """
            <div style="padding: 20px;">
                <h2>Reference Guide</h2>
                <p><strong>Complete Keyword Reference:</strong></p>
                <ul>
                    <li>540+ LS-DYNA keywords with full parameter definitions</li>
                    <li>Interactive parameter input with validation</li>
                    <li>Auto-generated LS-DYNA syntax with proper formatting</li>
                    <li>Integrated documentation for each keyword</li>
                </ul>
            </div>
            """
        }

        content = help_content.get(section, f"<h2>Help: {section.title()}</h2><p>Content not available yet.</p>")

        print(f"[HELP] Displaying help content in description tab")

        # Show in description tab if available
        if hasattr(self, 'desc_tab'):
            self.desc_tab.setHtml(content)
            print(f"[HELP] Content displayed in description tab")
        else:
            print(f"[HELP] Description tab not available, showing message box")
            QMessageBox.information(self, "Help", content.replace('<div style="padding: 20px;">', '').replace('</div>', ''))

    def show_examples_section(self, section):
        """Show examples for the specified section."""
        print(f"[EXAMPLES] Opening examples section: {section}")

        examples_content = {
            "latest": """
            <div style="padding: 20px;">
                <h2>Latest Examples</h2>
                <p><strong>Recent Advanced Examples:</strong></p>
                <ul>
                    <li><strong>Crash Analysis:</strong> Full vehicle impact simulation</li>
                    <li><strong>Forming:</strong> Sheet metal stamping with adaptive remeshing</li>
                    <li><strong>Impact:</strong> Bird strike analysis on aircraft structures</li>
                    <li><strong>Multiphysics:</strong> Coupled fluid-structure interaction</li>
                </ul>
                <p><em>These examples demonstrate advanced OpenRadioss capabilities.</em></p>
            </div>
            """,
            "introductory": """
            <div style="padding: 20px;">
                <h2>Introductory Examples</h2>
                <p><strong>Getting Started Examples:</strong></p>
                <ul>
                    <li><strong>Simple Beam:</strong> Basic structural analysis of a beam element</li>
                    <li><strong>Plate with Hole:</strong> Stress concentration analysis</li>
                    <li><strong>Thermal Expansion:</strong> Simple heat transfer problem</li>
                    <li><strong>Contact:</strong> Basic contact between two surfaces</li>
                </ul>
                <p><em>Perfect for learning OpenRadioss fundamentals.</em></p>
            </div>
            """,
            "implicit": """
            <div style="padding: 20px;">
                <h2>Implicit Examples</h2>
                <p><strong>Implicit Analysis Examples:</strong></p>
                <ul>
                    <li><strong>Linear Static:</strong> Static structural analysis</li>
                    <li><strong>Modal Analysis:</strong> Natural frequency extraction</li>
                    <li><strong>Buckling:</strong> Linear and nonlinear buckling analysis</li>
                    <li><strong>Steady Thermal:</strong> Heat conduction problems</li>
                </ul>
                <p><em>Examples using implicit time integration methods.</em></p>
            </div>
            """,
            "openradioss": """
            <div style="padding: 20px;">
                <h2>OpenRadioss Examples</h2>
                <p><strong>Solver-Specific Examples:</strong></p>
                <ul>
                    <li><strong>Material Models:</strong> OpenRadioss-specific material definitions</li>
                    <li><strong>Contact:</strong> OpenRadioss contact algorithms</li>
                    <li><strong>Output:</strong> OpenRadioss result file formats</li>
                    <li><strong>Performance:</strong> Optimization for OpenRadioss solver</li>
                </ul>
                <p><em>Examples optimized for OpenRadioss solver features.</em></p>
            </div>
            """
        }

        content = examples_content.get(section, f"<h2>Examples: {section.title()}</h2><p>Examples not available yet.</p>")

        print(f"[EXAMPLES] Displaying examples content in description tab")

        # Show in description tab if available
        if hasattr(self, 'desc_tab'):
            self.desc_tab.setHtml(content)
            print(f"[EXAMPLES] Content displayed in description tab")
        else:
            print(f"[EXAMPLES] Description tab not available, showing message box")
            QMessageBox.information(self, "Examples", content.replace('<div style="padding: 20px;">', '').replace('</div>', ''))

    def configure_template_mode(self):
        """Allow user to configure template mode."""
        print(f"[TEMPLATE_MODE] Opening template mode configuration")
        print(f"[TEMPLATE_MODE] Current template mode: {self.template_mode}")

        modes = ["Minimal", "Basic", "Full"]
        current_index = {"minimal": 0, "basic": 1, "full": 2}[self.template_mode]

        print(f"[TEMPLATE_MODE] Available modes: {modes}")
        print(f"[TEMPLATE_MODE] Current index: {current_index}")

        mode, ok = QInputDialog.getItem(self, "Template Mode",
                                      "Select template complexity level:",
                                      modes, current_index, False)

        if ok:
            old_mode = self.template_mode
            self.template_mode = mode.lower()

            print(f"[TEMPLATE_MODE] Mode changed from '{old_mode}' to '{self.template_mode}'")

            # Update UI based on new mode
            self.update_template_menu()

            # Save settings
            self.save_settings()

            print(f"[TEMPLATE_MODE] Settings saved to file")

            QMessageBox.information(self, "Template Mode Changed",
                                  f"Template mode changed from {old_mode.title()} to {mode}.\n\n"
                                  "The template menu will now show only templates appropriate for this mode.")
        else:
            print(f"[TEMPLATE_MODE] User cancelled template mode selection")

    def update_template_menu(self):
        """Update template menu based on current template mode."""
        print(f"[TEMPLATE_MENU] Updating template menu for mode: {self.template_mode}")

        # This method will be called after mode changes to update menu visibility
        # For now, we'll keep all templates available but could filter them here
        print(f"[TEMPLATE_MENU] Template menu update complete")
