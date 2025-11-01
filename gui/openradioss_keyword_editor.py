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

    def __init__(self, parent=None):
        # Set window flags to remove title bar buttons
        super(OpenRadiossKeywordEditorDialog, self).__init__(parent, 
            QtCore.Qt.Window | 
            QtCore.Qt.CustomizeWindowHint | 
            QtCore.Qt.WindowTitleHint | 
            QtCore.Qt.WindowCloseButtonHint)
        self.keywords = []
        self.current_keyword = None
        self.param_inputs = {}  # Store parameter input widgets
        self.keyword_cache = []  # Cache for generated keywords
        self.json_keywords = []  # Store keywords from JSON
        
        # Initialize cache paths
        from femcommands.open_cache_viewer import CACHE_FILE, CACHE_DIR
        self.CACHE_FILE = CACHE_FILE
        self.CACHE_DIR = CACHE_DIR

        # Template configuration
        self.template_mode = "full"  # "full", "basic", "minimal"

        # Load settings first
        self.load_settings()

        # Initialize UI components first to show loading status
        self.setup_ui()
        self.show_welcome_message()
        self.update_status_bar("Loading keywords...", is_loading=True)
        
        # Schedule keyword loading to keep UI responsive
        QtCore.QTimer.singleShot(100, self.initialize_keywords)

    def initialize_keywords(self):
        """Initialize keywords from both CFG and JSON sources"""
        try:
            # Load keywords from JSON first
            self.load_keywords_from_json()
            
            # Then load from CFG (this will filter against JSON keywords)
            print("[AUTO_LOAD] Starting automatic CFG keyword loading...")
            self.keywords = self.auto_load_from_cfg() or []
            
            # Update UI with loaded keywords
            self.update_category_list()
            self.update_keyword_list()
            
            # Update status
            keywords_count = len(self.keywords)
            if keywords_count > 0:
                categories_count = len(set(kw.get('category', 'General') for kw in self.keywords))
                self.update_status_bar(
                    f"Ready with {keywords_count} keywords in {categories_count} categories", 
                    is_loading=False
                )
            else:
                self.update_status_bar("No matching keywords found between CFG and JSON sources", 
                                    is_loading=False)
            
            # Start automatic background refresh timer (check every 5 minutes)
            self.start_auto_refresh_timer()
            
        except Exception as e:
            import traceback
            print(f"Error initializing keywords: {str(e)}\n{traceback.format_exc()}")
            self.update_status_bar("Error loading keywords - check console for details", 
                                is_loading=False)
    
    def load_keywords_from_json(self):
        """Load keywords from the JSON file with documentation"""
        try:
            import os
            import json
            
            # Get the path to the JSON file
            json_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "gui", "json", "keywords_clean.json"
            )
            
            if not os.path.exists(json_path):
                print(f"[WARNING] Keywords JSON file not found at {json_path}")
                return []
                
            with open(json_path, 'r', encoding='utf-8') as f:
                self.json_keywords = json.load(f)
                
            print(f"[INFO] Loaded {len(self.json_keywords)} keywords from JSON")
            return self.json_keywords
            
        except Exception as e:
            import traceback
            print(f"[ERROR] Failed to load keywords from JSON: {str(e)}\n{traceback.format_exc()}")
            return []

    def auto_load_from_cfg(self):
        """Automatically load keywords from CFG files on startup with comprehensive fallback."""
        print("[AUTO_LOAD] Checking for available keyword sources...")
        self.update_status_bar("Loading keywords from CFG files...", is_loading=True)

        # Priority 1: Try dynamic CFG loader first (most comprehensive)
        try:
            print("[AUTO_LOAD] Attempting dynamic CFG loading...")
            self.update_status_bar("Checking dynamic CFG loader...", is_loading=True)

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
                    print(f"[AUTO_LOAD] SUCCESS: Loaded {len(keywords)} keywords from dynamic CFG loader")
                    self.update_status_bar(f"Loaded {len(keywords)} keywords from dynamic CFG", is_loading=False)
                    self.save_keywords_as_json(self._convert_cfg_to_editor_format(keywords))
                    return keywords
                else:
                    print("[AUTO_LOAD] Dynamic CFG loader returned no keywords, trying fallback methods...")
                    self.update_status_bar("Dynamic CFG empty, trying fallback methods...", is_loading=True)
            else:
                print(f"[AUTO_LOAD] Dynamic CFG loader not found at {cfg_loader_path}")
                self.update_status_bar("Dynamic CFG not found, trying fallback...", is_loading=True)
        except Exception as e:
            print(f"[AUTO_LOAD] Dynamic CFG loading failed: {e}")
            self.update_status_bar("Dynamic CFG failed, trying fallback...", is_loading=True)

        # Priority 2: Try direct CFG parsing (fallback)
        try:
            print("[AUTO_LOAD] Attempting direct CFG file parsing...")
            self.update_status_bar("Parsing CFG files directly...", is_loading=True)

            cfg_root = os.path.join(os.path.dirname(__file__), 'CFG_Openradioss', 'radioss2025')
            if os.path.exists(cfg_root):
                keywords = self.parse_cfg_files(cfg_root)
                if keywords and len(keywords) > 0:
                    print(f"[AUTO_LOAD] SUCCESS: Loaded {len(keywords)} keywords from direct CFG parsing")
                    self.update_status_bar(f"Loaded {len(keywords)} keywords from CFG files", is_loading=False)
                    self.save_keywords_as_json(keywords)
                    return keywords
                else:
                    print("[AUTO_LOAD] No keywords found in CFG files")
                    self.update_status_bar("No keywords found in CFG files", is_loading=True)
            else:
                print(f"[AUTO_LOAD] CFG directory not found at {cfg_root}")
                self.update_status_bar(f"CFG directory not found: {cfg_root}", is_loading=True)
        except Exception as e:
            print(f"[AUTO_LOAD] Direct CFG parsing failed: {e}")
            self.update_status_bar("CFG parsing failed, trying cached data...", is_loading=True)

        # Priority 3: Try existing JSON files
        try:
            print("[AUTO_LOAD] Attempting to load from existing JSON files...")
            self.update_status_bar("Loading from cached JSON files...", is_loading=True)

            # Try comprehensive format first
            json_path = os.path.join(os.path.dirname(__file__), 'json', 'comprehensive_hm_reader_keywords.json')
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    keywords = json.load(f)
                if keywords:
                    print(f"[INFO] Loaded {len(keywords)} keywords from comprehensive HM reader format")
                    return keywords

            # Try enhanced format
            json_path = os.path.join(os.path.dirname(__file__), 'json', 'enhanced_hm_reader_keywords.json')
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    keywords = json.load(f)
                print(f"[AUTO_LOAD] SUCCESS: Loaded {len(keywords)} keywords from enhanced JSON")
                self.update_status_bar(f"Loaded {len(keywords)} keywords from cache", is_loading=False)
                return keywords

            print("[AUTO_LOAD] No existing JSON files found")
            self.update_status_bar("No cached files found", is_loading=True)

        except Exception as e:
            print(f"[AUTO_LOAD] JSON loading failed: {e}")
            self.update_status_bar("Cache loading failed", is_loading=True)

        # Final fallback: empty list
        print("[AUTO_LOAD] All loading methods failed, starting with empty keyword list")
        print("[AUTO_LOAD] Users can manually refresh from CFG files using File > Refresh menu")
        self.update_status_bar("No keywords loaded - use File > Refresh", is_loading=False)
        return []

    def auto_refresh_cfg_keywords(self):
        """Automatically refresh keywords from CFG files in the background."""
        print("[AUTO_REFRESH] Starting background CFG refresh...")

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
                    print(f"[AUTO_REFRESH] Found {len(keywords)} new keywords (current: {len(self.keywords)})")
                    self.keywords = keywords
                    self.save_keywords_as_json(self._convert_cfg_to_editor_format(keywords))
                    self.update_category_list()
                    self.update_keyword_list()

                    # Show notification if significant number of new keywords
                    if len(keywords) > len(self.keywords) + 10:
                        print(f"[AUTO_REFRESH] Notifying user of {len(keywords)} keywords available")
                        # Could add a notification here if needed
                else:
                    print(f"[AUTO_REFRESH] No new keywords found (current: {len(self.keywords)})")
            else:
                print(f"[AUTO_REFRESH] Dynamic CFG loader not available")

        except Exception as e:
            print(f"[AUTO_REFRESH] Background refresh failed: {e}")

    def start_auto_refresh_timer(self):
        """Start automatic background refresh timer for CFG keywords."""
        try:
            from PySide2.QtCore import QTimer
            self.auto_refresh_timer = QTimer(self)
            self.auto_refresh_timer.timeout.connect(self._check_cfg_updates)
            # Check every 5 minutes (300,000 milliseconds)
            self.auto_refresh_timer.start(300000)
            print("[AUTO_REFRESH] Started automatic background refresh timer (5-minute intervals)")
        except Exception as e:
            print(f"[AUTO_REFRESH] Could not start timer: {e}")

    def _check_cfg_updates(self):
        """Check for CFG updates in the background (called by timer)."""
        print("[AUTO_REFRESH] Checking for CFG updates...")
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
                    print(f"[AUTO_REFRESH] Found {len(keywords)} new keywords (current: {len(self.keywords)})")
                    self.keywords = keywords
                    self.save_keywords_as_json(self._convert_cfg_to_editor_format(keywords))
                    self.update_category_list()
                    self.update_keyword_list()

                    # Show notification if significant number of new keywords
                    if len(keywords) > len(self.keywords) + 10:
                        print(f"[AUTO_REFRESH] Notifying user of {len(keywords)} keywords available")
                        # Could add a notification here if needed
                else:
                    print(f"[AUTO_REFRESH] No new keywords found (current: {len(self.keywords)})")
            else:
                print(f"[AUTO_REFRESH] Dynamic CFG loader not available")

        except Exception as e:
            print(f"[AUTO_REFRESH] Background refresh failed: {e}")

    def update_status_bar(self, message, is_loading=False):
        """Update the status bar with current loading status."""
        if hasattr(self, 'status_bar'):
            if is_loading:
                self.status_bar.setText(f"🔄 {message}")
                self.status_bar.setStyleSheet("padding: 5px; background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 3px; color: #856404;")
            else:
                self.status_bar.setText(f"✅ {message}")
                self.status_bar.setStyleSheet("padding: 5px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 3px; color: #155724;")

    def load_settings(self):
        """Load user settings from file."""
        try:
            settings_file = os.path.join(os.path.dirname(__file__), 'json', 'openradioss_keyword_editor_settings.json')
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    self.template_mode = settings.get('template_mode', 'full')
        except Exception as e:
            print(f"[WARNING] Could not load settings: {e}")
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
            print(f"[WARNING] Could not save settings: {e}")

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

        # Get the keyword data stored in the item's UserRole
        self.current_keyword = item.data(QtCore.Qt.UserRole)
        if not self.current_keyword:
            return

        print(f"[DEBUG] Selected keyword: {self.current_keyword.get('name', 'Unknown')}")
        print(f"[DEBUG] Keyword data keys: {list(self.current_keyword.keys())}")
        print(f"[DEBUG] Has parameters: {'parameters' in self.current_keyword}")
        if 'parameters' in self.current_keyword:
            print(f"[DEBUG] Number of parameters: {len(self.current_keyword['parameters'])}")
            for i, param in enumerate(self.current_keyword['parameters'][:3]):  # Show first 3
                print(f"[DEBUG] Param {i+1}: {param}")

        # Get the documentation URL
        doc_url = self.current_keyword.get('documentation')
        if doc_url:
            self.show_web_view(doc_url)

        # Always show keyword details (parameters, etc.) regardless of documentation
        self.show_keyword_details()

    def load_keywords(self):
        """Load keywords using comprehensive format detection with dynamic CFG data priority."""
        try:
            # Try to load from dynamic CFG data first (highest priority)
            dynamic_json_path = os.path.join(os.path.dirname(__file__), 'dynamic_cfg_editor_keywords.json')
            if os.path.exists(dynamic_json_path):
                print(f"[INFO] Loading dynamic CFG keywords from: {dynamic_json_path}")
                with open(dynamic_json_path, 'r', encoding='utf-8') as f:
                    keywords = json.load(f)

                print(f"[INFO] Loaded {len(keywords)} keywords from dynamic CFG data")
                print(f"[INFO] Categories available: {len(set(kw.get('category', 'General') for kw in keywords))}")

                # Count by category for user information
                category_counts = {}
                for kw in keywords:
                    cat = kw.get('category', 'General')
                    category_counts[cat] = category_counts.get(cat, 0) + 1

                print(f"[INFO] Keywords by category: {category_counts}")
                return keywords

            # Fallback to comprehensive format detection
            json_path = os.path.join(os.path.dirname(__file__), 'json', 'comprehensive_hm_reader_keywords.json')
            if not os.path.exists(json_path):
                # Fall back to enhanced HM reader
                json_path = os.path.join(os.path.dirname(__file__), 'json', 'enhanced_hm_reader_keywords.json')
                if not os.path.exists(json_path):
                    print(f"[WARNING] Comprehensive keywords not found, trying basic format")
                    return self.load_keywords_from_cfg()

            with open(json_path, 'r', encoding='utf-8') as f:
                keywords = json.load(f)

            print(f"[INFO] Loaded {len(keywords)} keywords using comprehensive format detection from {json_path}")

            # Count by format type for user information
            format_counts = {}
            for kw in keywords:
                fmt_type = kw.get('type', 'UNKNOWN')
                format_counts[fmt_type] = format_counts.get(fmt_type, 0) + 1

            print(f"[INFO] Keywords by format: {format_counts}")
            return keywords

        except Exception as e:
            print(f"[ERROR] Error loading comprehensive keywords: {e}")
            print(f"[INFO] Attempting to load from CFG files as fallback")
            return self.load_keywords_from_cfg()

    def load_keywords_from_cfg(self):
        """Load keywords directly from CFG files as a fallback method."""
        try:
            cfg_root = os.path.join(os.path.dirname(__file__), 'CFG_Openradioss', 'radioss2025')
            if not os.path.exists(cfg_root):
                print(f"[ERROR] CFG directory not found at {cfg_root}")
                return []

            print(f"[INFO] Loading keywords directly from CFG files at {cfg_root}")

            # Import the generation script functionality
            import sys
            sys.path.append(os.path.dirname(__file__))

            # Create a simple parser for CFG files
            keywords = self.parse_cfg_files(cfg_root)

            print(f"[INFO] Loaded {len(keywords)} keywords directly from CFG files")
            return keywords

        except Exception as e:
            print(f"[ERROR] Error loading keywords from CFG files: {e}")
            return []

    def parse_cfg_files(self, cfg_root):
        """Parse CFG files to extract keyword information."""
        import re

        keywords = []
        categories = set()

        # Walk through all subdirectories
        for root, dirs, files in os.walk(cfg_root):
            for file in files:
                if file.endswith('.cfg'):
                    cfg_path = os.path.join(root, file)
                    file_keywords = self.parse_single_cfg_file(cfg_path)
                    keywords.extend(file_keywords)

                    if file_keywords:
                        print(f"[DEBUG] Parsed {len(file_keywords)} keywords from {cfg_path}")

        # Remove duplicates while preserving the first occurrence
        unique_keywords = {}
        for kw in keywords:
            name = kw.get('name', '').strip()
            # Only add if we haven't seen this exact name before
            if name and name not in unique_keywords:
                unique_keywords[name] = kw
                # Update categories as we go
                categories.add(kw.get('category', 'General'))

        # Convert to list and sort case-insensitively
        keywords_list = sorted(unique_keywords.values(), 
                             key=lambda x: x.get('name', '').lower())

        print(f"[INFO] Total unique keywords from CFG: {len(keywords_list)} in {len(categories)} categories")

        # Save as JSON for faster loading next time
        self.save_keywords_as_json(keywords_list)

        return keywords_list

    def parse_single_cfg_file(self, cfg_path):
        """Parse a single CFG file to extract keyword information."""
        import re

        keywords = []

        try:
            with open(cfg_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Extract category from path
            category = "General"
            path_parts = cfg_path.split(os.sep)
            for part in path_parts:
                part_upper = part.upper()
                if part_upper in ['MAT', 'PROP', 'LOADS', 'CARDS', 'INTER', 'FAIL', 'DAMP', 'SENSOR', 'TABLE', 'OUTPUTBLOCK']:
                    category = part_upper
                    break

            # Look for keyword definitions using regex patterns
            # Updated pattern to properly handle leading special characters and trailing semicolons
            keyword_pattern = r'KEYWORD\s*=\s*([^\s,;=]+(?:\s*[^\s,;=]+)*)[\s;]*'
            title_pattern = r'TITLE\s*=\s*"([^"]*)"'
            user_names_pattern = r'USER_NAMES\s*=\s*\(([^)]*)\)'
            desc_pattern = r'DESCRIPTION\s*=\s*"([^"]*)"'

            # Find all matches
            keyword_matches = re.findall(keyword_pattern, content, re.MULTILINE)
            title_matches = re.findall(title_pattern, content, re.MULTILINE)
            user_names_matches = re.findall(user_names_pattern, content, re.DOTALL)
            desc_matches = re.findall(desc_pattern, content, re.DOTALL)

            # Process each keyword found
            for i, keyword_name in enumerate(keyword_matches):
                # Clean up the keyword name (remove any surrounding quotes and whitespace)
                original_name = keyword_name
                keyword_name = keyword_name.strip('\"\'').strip()
                
                # Get the display name (preserve all characters, just clean up)
                display_name = keyword_name
                
                # Debug output
                print(f"[DEBUG] Processing keyword {i+1}:")
                print(f"  Original match: {original_name!r}")
                print(f"  After cleanup: {keyword_name!r}")
                print(f"  Display name: {display_name!r}")
                
                keyword_info = {
                    'name': keyword_name,  # Original name with all special characters
                    'display_name': display_name,  # Use the full name for display
                    'category': category,
                    'title': title_matches[i] if i < len(title_matches) else '',
                    'description': desc_matches[i] if i < len(desc_matches) else '',
                    'source_file': os.path.basename(cfg_path),
                    'parameters': []  # Add default empty parameters
                }

                # Process USER_NAMES if available
                if i < len(user_names_matches):
                    user_names_str = user_names_matches[i]
                    # Clean up the user names (remove quotes, spaces)
                    user_names = [name.strip().strip('"').strip("'") for name in user_names_str.split(',') if name.strip()]
                    if user_names:
                        keyword_info['user_names'] = user_names

                # Add default parameters based on keyword type
                keyword_info['parameters'] = self.get_default_parameters(keyword_name)

                keywords.append(keyword_info)

        except Exception as e:
            print(f"[ERROR] Error parsing {cfg_path}: {e}")

        return keywords

    def get_default_parameters(self, keyword_name):
        """Get default parameters based on keyword name."""
        parameters = []

        # Material keywords
        if 'MAT' in keyword_name:
            parameters = [
                {
                    'name': 'Material ID',
                    'description': 'Material identifier',
                    'field_0': 'mid',
                    'field_1': 'ro',
                    'field_2': 'e',
                    'field_3': 'nu',
                    'field_4': 'sigy'
                },
                {
                    'name': 'Density',
                    'description': 'Material density (kg/m³)',
                    'field_0': 'ro'
                },
                {
                    'name': 'Young Modulus',
                    'description': 'Young modulus (Pa)',
                    'field_0': 'e'
                },
                {
                    'name': 'Poisson Ratio',
                    'description': 'Poisson ratio',
                    'field_0': 'nu'
                }
            ]

        # Node keywords
        elif 'NODE' in keyword_name:
            parameters = [
                {
                    'name': 'Node ID',
                    'description': 'Node identifier',
                    'field_0': 'nid'
                },
                {
                    'name': 'Coordinates',
                    'description': 'Node coordinates (x, y, z)',
                    'field_0': 'x',
                    'field_1': 'y',
                    'field_2': 'z'
                }
            ]

        # Element keywords
        elif 'ELEMENT' in keyword_name or 'ELEM' in keyword_name:
            parameters = [
                {
                    'name': 'Element ID',
                    'description': 'Element identifier',
                    'field_0': 'eid'
                },
                {
                    'name': 'Part ID',
                    'description': 'Part identifier',
                    'field_0': 'pid'
                },
                {
                    'name': 'Node Connectivity',
                    'description': 'Element connectivity',
                    'field_0': 'n1',
                    'field_1': 'n2',
                    'field_2': 'n3',
                    'field_3': 'n4'
                }
            ]

        # Part keywords
        elif 'PART' in keyword_name:
            parameters = [
                {
                    'name': 'Part ID',
                    'description': 'Part identifier',
                    'field_0': 'pid'
                },
                {
                    'name': 'Section ID',
                    'description': 'Section identifier',
                    'field_0': 'secid'
                },
                {
                    'name': 'Material ID',
                    'description': 'Material identifier',
                    'field_0': 'mid'
                }
            ]

        # Boundary condition keywords
        elif any(word in keyword_name.upper() for word in ['BCS', 'BOUNDARY', 'BC', 'CONSTRAINT']):
            parameters = [
                {
                    'name': 'Node Set ID',
                    'description': 'Node set identifier',
                    'field_0': 'nsid'
                },
                {
                    'name': 'DOF',
                    'description': 'Degrees of freedom (1-6 for x,y,z,rx,ry,rz)',
                    'field_0': 'dof'
                }
            ]

        # Load keywords
        elif any(word in keyword_name.upper() for word in ['LOAD', 'FORCE', 'PRESSURE', 'GRAVITY']):
            parameters = [
                {
                    'name': 'Load Set ID',
                    'description': 'Load set identifier',
                    'field_0': 'lsid'
                },
                {
                    'name': 'Load Type',
                    'description': 'Type of load (force, pressure, etc.)',
                    'field_0': 'ltype'
                }
            ]

        return parameters

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

            print(f"[INFO] Saved {len(keywords)} keywords in comprehensive format with format detection")

        except Exception as e:
            print(f"[WARNING] Could not save keywords to JSON: {e}")

    def refresh_keywords_from_cfg(self):
        """Refresh keywords using dynamic CFG file loading (no hardcoded data)."""
        print("[INFO] Refreshing keywords using dynamic CFG file loading...")

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
            print(f"[ERROR] Dynamic CFG refresh failed: {e}")

    def _convert_cfg_to_editor_format(self, cfg_keywords):
        """Convert CFG keywords to editor-compatible format."""
        editor_keywords = []

        for kw in cfg_keywords:
            # Preserve the original name exactly as it appears in the CFG file
            name = kw.get('name', '')
            # Use the display_name if provided, otherwise use the original name
            display_name = kw.get('display_name', name)
            
            editor_kw = {
                'name': name,  # Original name with all special characters
                'display_name': display_name,  # Use the provided or original name for display
                'category': kw.get('category', 'General'),
                'title': kw.get('title', ''),
                'description': kw.get('description', ''),
                'source_file': kw.get('source_file', ''),
                'parameters': kw.get('parameters', []),
                'type': kw.get('type', 'LS_DYNA'),
                'format_tags': kw.get('format_tags', []),
                'solver_compatibility': kw.get('solver_compatibility', []),
                'parameter_count': kw.get('parameter_count', 0),
                'validation_rules': kw.get('validation_rules', 0),
                'data_types': kw.get('data_types', []),
                'sections': kw.get('sections', [])
            }

            # Add format cards if available
            if 'format_cards' in kw:
                editor_kw['format_cards'] = kw['format_cards']

            # Add LS-DYNA syntax if available
            if 'ls_dyna_syntax' in kw:
                editor_kw['ls_dyna_syntax'] = kw['ls_dyna_syntax']

            # If user_names exist, copy them over
            if 'user_names' in kw:
                editor_kw['user_names'] = kw['user_names']

            editor_keywords.append(editor_kw)

        return editor_keywords

    def _clean_description(self, description):
        """Clean up the keyword description."""
        if not description:
            return "No description available."

        # Remove any copyright notices
        if '©' in description:
            description = description.split('©')[0].strip()

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
            print("[DEBUG] update_keyword_list: No keywords available")
            return

        current_category = self.category_combo.currentText()
        print(f"[DEBUG] update_keyword_list: Updating for category: {current_category}")
        print(f"[DEBUG] Total keywords: {len(self.keywords)}")
        
        # Debug: Print first few keywords
        print("[DEBUG] First 5 keywords:")
        for i, kw in enumerate(self.keywords[:5]):
            print(f"  {i+1}. Name: {kw.get('name', 'N/A')!r}")
            print(f"     Display: {kw.get('display_name', 'N/A')!r}")
            print(f"     Category: {kw.get('category', 'N/A')}")
        
        self.keywords_list.clear()
        added_count = 0

        for kw in self.keywords:
            if current_category == "All Categories" or kw.get('category') == current_category:
                # Use display_name if available, otherwise fall back to name
                display_name = kw.get('display_name', kw.get('name', 'Unnamed'))
                
                # Debug output for first 5 items
                if added_count < 5:
                    print(f"[DEBUG] Adding item {added_count+1}:")
                    print(f"  Name: {kw.get('name', 'N/A')!r}")
                    print(f"  Display name: {display_name!r}")
                    print(f"  Category: {kw.get('category', 'N/A')}")
                
                item = QListWidgetItem(display_name)
                item.setData(QtCore.Qt.UserRole, kw)  # Store the full keyword data
                self.keywords_list.addItem(item)
                added_count += 1
                
                if added_count == 5:  # Only show first 5 for brevity
                    print("[DEBUG] ... and more items ...")

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

        # Add status bar for CFG loading status
        self.status_bar = QtWidgets.QLabel("🔄 Loading keywords from CFG files...")
        self.status_bar.setStyleSheet("padding: 5px; background-color: #e8f4f8; border: 1px solid #b3d9ff; border-radius: 3px;")
        self.status_bar.setMinimumHeight(25)
        main_layout.addWidget(self.status_bar)

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

        # Add dialog buttons
        button_box = QDialogButtonBox()
        self.close_button = button_box.addButton("Close and Save Cache", QDialogButtonBox.AcceptRole)
        self.close_button.clicked.connect(self.close_and_save)
        
        # Add a cancel button for consistency
        cancel_button = button_box.addButton(QDialogButtonBox.Cancel)
        cancel_button.clicked.connect(self.reject)

        # Create a horizontal layout for the action buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        # Add buttons to the layout
        self.generate_button = QtWidgets.QPushButton("Generate Keyword")
        self.generate_button.clicked.connect(self.generate_keyword)
        button_layout.addWidget(self.generate_button)
        
        # Add spacer
        button_layout.addSpacing(10)
        
        # Cache management button
        self.cache_button = QtWidgets.QPushButton("Add to Cache")
        self.cache_button.clicked.connect(self.cache_keyword)
        self.cache_button.setEnabled(False)  # Initially disabled
        button_layout.addWidget(self.cache_button)
        
        # Add spacer
        button_layout.addSpacing(10)
        
        self.update_file_button = QtWidgets.QPushButton("Update .k File")
        self.update_file_button.clicked.connect(self.update_k_file)
        button_layout.addWidget(self.update_file_button)
        
        # Add stretch to push buttons to the left
        button_layout.addStretch()
        
        # Add the button layout to the main layout
        main_layout.addLayout(button_layout)
        
        # Add standard OK/Cancel buttons to the button box
        button_box.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        main_layout.addWidget(button_box)

    def show_welcome_message(self):
        """Display welcome message in the details panel."""
        keywords_count = len(self.keywords) if self.keywords else 0
        loading_status = "✅ Keywords loaded from CFG files" if keywords_count > 0 else "⚠️  No keywords loaded yet"

        welcome_html = f"""
        <div style="text-align: center; padding: 20px;">
            <h1>Welcome to OpenRadioss Keyword Editor</h1>
            <p style="font-size: 14px; color: #666; margin-top: 20px;">
                This tool helps you create and manage OpenRadioss input files for your simulations.
            </p>
            <div style="margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 5px; text-align: left;">
                <h3>🎯 Automatic CFG Loading Status:</h3>
                <p><strong>{loading_status}</strong></p>
                <p>📊 <strong>{keywords_count}</strong> keywords available in {len(set(kw.get('category', 'General') for kw in self.keywords)) if self.keywords else 0} categories</p>
                <p>🔄 Keywords are automatically loaded from CFG files on startup</p>
                <p>📁 File &gt; Refresh from Dynamic CFG Files (manual refresh available)</p>
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

        # Update status bar to reflect current keyword count
        keywords_count = len(self.keywords) if self.keywords else 0
        if keywords_count > 0:
            categories_count = len(set(kw.get('category', 'General') for kw in self.keywords))
            self.update_status_bar(f"Ready with {keywords_count} keywords in {categories_count} categories", is_loading=False)
        else:
            self.update_status_bar("Ready - no keywords loaded (use File > Refresh)", is_loading=False)

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
        """Cache the currently generated keyword and save to disk."""
        print("[DEBUG] cache_keyword called")
        
        if not hasattr(self, 'generated_tab') or not self.generated_tab.toPlainText().strip():
            QMessageBox.warning(self, "No Generated Keyword",
                            "Please generate a keyword first before caching it.")
            return

        # Get the generated keyword text
        keyword_text = self.generated_tab.toPlainText().strip()
        print(f"[DEBUG] Caching keyword text: {keyword_text[:100]}...")

        if not keyword_text or keyword_text == "# No keyword selected":
            QMessageBox.warning(self, "Invalid Keyword",
                            "The generated keyword is empty or invalid.")
            return

        # Add to cache with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        keyword_name = self.current_keyword.get('name', 'Unknown') if self.current_keyword else 'Unknown'
        cache_entry = {
            'text': keyword_text,
            'timestamp': timestamp,
            'keyword_name': keyword_name
        }
        print(f"[DEBUG] Created cache entry for: {keyword_name}")

        # Add to in-memory cache
        self.keyword_cache.append(cache_entry)
        print(f"[DEBUG] Added to cache. Total items: {len(self.keyword_cache)}")
        
        # Save to disk
        if self.save_cache_to_disk():
            print("[DEBUG] Successfully saved cache to disk")
            QMessageBox.information(self, "Keyword Cached",
                                f"Keyword '{keyword_name}' has been added to the cache and saved to disk.\n\nLocation: {self.CACHE_FILE}")
        else:
            print("[ERROR] Failed to save cache to disk")
            QMessageBox.warning(self, "Cache Warning",
                            f"Keyword '{keyword_name}' was added to the in-memory cache but could not be saved to disk.\n\nCheck console for details.")
            
        # Update the UI
        self.update_cache_display()
        
        # Enable cache and save buttons
        self.cache_button.setEnabled(True)
        if hasattr(self, 'save_cache_button'):
            self.save_cache_button.setEnabled(True)

        # Open cache viewer window
        self.open_cache_viewer()

    def update_cache_display(self):
        """Update the cached keywords display."""
        if not hasattr(self, 'cache_tab'):
            return

        if not self.keyword_cache:
            self.cache_tab.setPlainText("No keywords cached yet.\n\nGenerate a keyword and click 'Add to Cache' to start building your OpenRadioss input file.")
            self.tab_widget.setTabText(3, "Cached Keywords (0)")
            # Disable save button when cache is empty
            if hasattr(self, 'save_cache_button'):
                self.save_cache_button.setEnabled(False)
            return
            
        # Enable save button when we have cached items
        if hasattr(self, 'save_cache_button'):
            self.save_cache_button.setEnabled(True)

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

    def open_cache_viewer(self):
        """Open the cache viewer window."""
        if not hasattr(self, 'cache_viewer') or self.cache_viewer is None:
            self.cache_viewer = CacheViewerWindow(self.keyword_cache, self)
        self.cache_viewer.show()
        self.cache_viewer.raise_()
        self.cache_viewer.activateWindow()

    def show_keyword_details(self):
        """Show details of the selected keyword with enhanced documentation."""
        if not self.current_keyword:
            return
            
        # Clear previous details
        self.details_text.clear()
        self.parameters_table.setRowCount(0)
        
        # Get keyword details
        name = self.current_keyword.get('name', '')
        category = self.current_keyword.get('category', 'Uncategorized')
        description = self.current_keyword.get('description', 'No description available.')
        doc_url = self.current_keyword.get('documentation', '')
        
        # Find matching JSON keyword for additional details
        json_kw = next((k for k in self.json_keywords if k.get('name') == name), None)
        
        # Format and display details with enhanced styling
        html = """
        <html>
        <head>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 10px; 
                    color: #333;
                }
                h2 { 
                    color: #2c3e50; 
                    margin-bottom: 10px;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 5px;
                }
                h3 { 
                    color: #3498db; 
                    margin-top: 15px;
                }
                .section {
                    margin-bottom: 15px;
                    padding: 10px;
                    background-color: #f9f9f9;
                    border-radius: 5px;
                    border-left: 4px solid #3498db;
                }
                .doc-link {
                    display: inline-block;
                    margin-top: 5px;
                    padding: 5px 10px;
                    background-color: #3498db;
                    color: white !important;
                    text-decoration: none;
                    border-radius: 3px;
                    font-weight: bold;
                }
                .doc-link:hover {
                    background-color: #2980b9;
                }
                .category {
                    display: inline-block;
                    background-color: #e8f4fc;
                    color: #2980b9;
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-size: 0.9em;
                    margin-bottom: 10px;
                }
            </style>
        </head>
        <body>
        """
        
        # Add main keyword info
        html += f"""
        <div class="section">
            <h2>{name}</h2>
            <div class="category">{category}</div>
            <p>{description}</p>
        """
        
        # Add documentation link if available
        if doc_url:
            html += f"""
            <a href="{doc_url}" class="doc-link" target="_blank">
                View Full Documentation
            </a>
            """
        
        html += "</div>"  # Close section
        
        # Add parameters section if available
        if 'parameters' in self.current_keyword and self.current_keyword['parameters']:
            html += """
            <div class="section">
                <h3>Parameters</h3>
                <table width="100%" cellspacing="0" cellpadding="5">
                    <tr style="background-color: #f0f0f0; font-weight: bold;">
                        <th>Name</th>
                        <th>Type</th>
                        <th>Default</th>
                        <th>Description</th>
                    </tr>
            """
            
            # Add parameter rows
            for i, (param_name, param_data) in enumerate(self.current_keyword['parameters'].items()):
                row_bg = '#ffffff' if i % 2 == 0 else '#f9f9f9'
                html += f"""
                <tr style="background-color: {row_bg};">
                    <td><b>{param_name}</b></td>
                    <td>{param_data.get('type', 'any')}</td>
                    <td>{param_data.get('default', '')}</td>
                    <td>{param_data.get('description', '')}</td>
                </tr>
                """
            
            html += "</table></div>"
        
        # Add examples section if available in JSON
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
        
        # Close HTML
        html += """
        </body>
        </html>
        """
        
        self.details_text.setHtml(html)

    def auto_load_from_cfg(self):
        """Automatically load keywords from CFG files and filter against JSON documentation."""
        try:
            print("[AUTO_LOAD] Attempting to load keywords from CFG files...")
            
            # Load from CFG files
            cfg_keywords = self.load_keywords_from_cfg()
            
            if not cfg_keywords:
                print("[AUTO_LOAD] No keywords found in CFG files, trying cache...")
                # Try loading from JSON cache if available
                try:
                    if os.path.exists(self.CACHE_FILE):
                        with open(self.CACHE_FILE, 'r') as f:
                            cfg_keywords = json.load(f)
                            print(f"[AUTO_LOAD] Loaded {len(cfg_keywords)} keywords from cache")
                except Exception as e:
                    print(f"[AUTO_LOAD] Error loading from cache: {str(e)}")
            
            if not cfg_keywords:
                print("[AUTO_LOAD] No keywords found in cache, using empty list")
                return []
                
            # Filter CFG keywords against JSON documentation
            filtered_keywords = []
            json_keyword_names = {kw['name'] for kw in self.json_keywords}
            
            for kw in cfg_keywords:
                kw_name = kw.get('name', '')
                if kw_name in json_keyword_names:
                    # Find matching JSON keyword to get documentation
                    json_kw = next((jk for jk in self.json_keywords if jk['name'] == kw_name), None)
                    if json_kw:
                        # Merge CFG data with JSON documentation
                        kw.update({
                            'description': json_kw.get('description', kw.get('description', '')),
                            'documentation': json_kw.get('documentation', ''),
                            'category': json_kw.get('category', 'Uncategorized')
                        })
                        filtered_keywords.append(kw)
            
            print(f"[AUTO_LOAD] Filtered to {len(filtered_keywords)} keywords with documentation")
            return filtered_keywords
            
        except Exception as e:
            print(f"[AUTO_LOAD] Error during auto-load: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

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
                print(f"Saved {len(self.keyword_cache)} keywords to cache at {self.CACHE_FILE}")
            except Exception as e:
                print(f"Error saving keyword cache: {e}")
            
        # Save settings and close any open dialogs
        try:
            # Save settings
            self.save_settings()
            
            # Close any open dialogs
            if hasattr(self, 'cache_viewer') and self.cache_viewer:
                self.cache_viewer.close()
                
        except Exception as e:
            print(f"Error in closeEvent: {e}")
        finally:
            # Always accept the close event
            event.accept()
