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
        
        # Initialize cache paths
        from femcommands.open_cache_viewer import CACHE_FILE, CACHE_DIR
        self.CACHE_FILE = CACHE_FILE
        self.CACHE_DIR = CACHE_DIR

        # Template configuration
        self.template_mode = "full"  # "full", "basic", "minimal"

        # Load settings first
        self.load_settings()

        # Auto-load keywords from CFG files on startup
        print("[AUTO_LOAD] Starting automatic CFG keyword loading...")
        self.keywords = self.auto_load_from_cfg() or []

        # Initialize UI components
        self.setup_ui()

        # Show welcome message
        self.show_welcome_message()

        # Populate initial data
        self.update_category_list()
        self.update_keyword_list()

        print(f"[AUTO_LOAD] Initialization complete with {len(self.keywords)} keywords loaded")

        # Update status bar with final loading status
        keywords_count = len(self.keywords)
        if keywords_count > 0:
            categories_count = len(set(kw.get('category', 'General') for kw in self.keywords))
            self.update_status_bar(f"Ready with {keywords_count} keywords in {categories_count} categories", is_loading=False)
        else:
            self.update_status_bar("Ready - no keywords loaded (use File > Refresh)", is_loading=False)

        # Start automatic background refresh timer (check every 5 minutes)
        self.start_auto_refresh_timer()

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
            json_path = os.path.join(os.path.dirname(__file__), 'comprehensive_hm_reader_keywords.json')
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    keywords = json.load(f)
                print(f"[AUTO_LOAD] SUCCESS: Loaded {len(keywords)} keywords from comprehensive JSON")
                self.update_status_bar(f"Loaded {len(keywords)} keywords from cache", is_loading=False)
                return keywords

            # Try enhanced format
            json_path = os.path.join(os.path.dirname(__file__), 'enhanced_hm_reader_keywords.json')
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
            settings_file = os.path.join(os.path.dirname(__file__), '..', 'openradioss_keyword_editor_settings.json')
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
            settings_file = os.path.join(os.path.dirname(__file__), '..', 'openradioss_keyword_editor_settings.json')
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
            json_path = os.path.join(os.path.dirname(__file__), 'comprehensive_hm_reader_keywords.json')
            if not os.path.exists(json_path):
                # Fall back to enhanced HM reader
                json_path = os.path.join(os.path.dirname(__file__), 'enhanced_hm_reader_keywords.json')
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

            # Save detailed version with parameters
            detailed_file = os.path.join(os.path.dirname(__file__), 'openradioss_keywords_with_parameters.json')
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

        self.params_tab.clear()
        parameters = kw.get('parameters', [])

        print(f"[DEBUG] Parameters found: {len(parameters)}")
        if parameters:
            print(f"[DEBUG] First parameter: {parameters[0]}")

        if not parameters:
            print("[DEBUG] No parameters found, setting row count to 0")
            self.params_tab.setRowCount(0)
            return

        self.params_tab.setRowCount(len(parameters))
        self.params_tab.setColumnCount(3)  # Parameter, Value input, Description
        self.params_tab.setHorizontalHeaderLabels(["Parameter", "Value", "Description"])

        # Store parameter input widgets for later retrieval
        self.param_inputs = {}

        for row, param in enumerate(parameters):
            print(f"[DEBUG] Processing parameter {row+1}: {param}")

            # Add parameter name (read-only)
            name_item = QTableWidgetItem(param.get('name', ''))
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.params_tab.setItem(row, 0, name_item)

            # Create input widgets for all non-empty fields
            field_inputs = {}
            for i in range(8):  # field_0 through field_7
                field_name = param.get(f'field_{i}', '')
                if field_name:  # Only create input for non-empty fields
                    value_input = QLineEdit()
                    value_input.setText("")  # Start empty
                    field_inputs[field_name] = value_input
                    self.param_inputs[field_name] = value_input

            # For now, put the first field input in the table cell
            # TODO: This needs to be redesigned to show multiple inputs per parameter
            if field_inputs:
                first_field = next(iter(field_inputs.values()))
                self.params_tab.setCellWidget(row, 1, first_field)

            # Add description (read-only)
            desc_item = QTableWidgetItem(param.get('description', ''))
            desc_item.setFlags(desc_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.params_tab.setItem(row, 2, desc_item)

        # Resize columns
        self.params_tab.resizeColumnsToContents()
        self.params_tab.setColumnWidth(1, 150)  # Value column width
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

    def save_cache_to_disk(self):
        """Save the current keyword cache to disk as JSON."""
        try:
            # Ensure cache directory exists and is writable
            cache_dir = os.path.expanduser('~/.cache/FreeCAD/Fem_upgraded')
            os.makedirs(cache_dir, exist_ok=True, mode=0o755)
            
            if not os.access(cache_dir, os.W_OK):
                error_msg = f"Cache directory is not writable: {cache_dir}"
                print(f"[CACHE_ERROR] {error_msg}")
                return False
            
            # Set cache file path
            cache_file = os.path.join(cache_dir, 'openradioss_keyword_cache.json')
            temp_file = f"{cache_file}.tmp"
            
            print(f"[CACHE_DEBUG] Saving cache to: {cache_file}")
            print(f"[CACHE_DEBUG] Number of items to save: {len(self.keyword_cache)}")
            
            try:
                # Write to temporary file first
                with open(temp_file, 'w') as f:
                    json.dump(self.keyword_cache, f, indent=2, ensure_ascii=False)
                
                # Atomic rename for safety
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                os.rename(temp_file, cache_file)
                
                # Verify the file was written
                if os.path.exists(cache_file):
                    file_size = os.path.getsize(cache_file)
                    print(f"[CACHE_DEBUG] Successfully wrote {file_size} bytes to {cache_file}")
                    # Update the instance variables for consistency
                    self.CACHE_DIR = cache_dir
                    self.CACHE_FILE = cache_file
                    return True
                
                print(f"[CACHE_ERROR] Cache file was not created at {cache_file}")
                return False
                
            except Exception as e:
                error_msg = f"Error writing to cache file {cache_file}: {str(e)}"
                print(f"[CACHE_ERROR] {error_msg}")
                # Clean up temp file if it exists
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return False
                
        except Exception as e:
            import traceback
            error_msg = f"Error saving cache: {str(e)}"
            print(f"[CACHE_ERROR] {error_msg}")
            print(traceback.format_exc())
            return False
            
    def save_cache_to_json(self, file_path=None):
        """Save the current keyword cache to a JSON file.
        
        Args:
            file_path (str, optional): Path to save the JSON file. 
                If None, will save to ~/.cache/FreeCAD/Fem_upgraded/openradioss_keyword_cache.json
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        if not self.keyword_cache:
            QMessageBox.warning(self, "Empty Cache", "The cache is empty. Nothing to save.")
            return False
            
        # If no file path provided, use default cache location
        if not file_path:
            # Create cache directory if it doesn't exist
            cache_dir = os.path.expanduser('~/.cache/FreeCAD/Fem_upgraded')
            os.makedirs(cache_dir, exist_ok=True, mode=0o755)
            file_path = os.path.join(cache_dir, 'openradioss_keyword_cache.json')
                
        try:
            # Write to file with pretty-printed JSON
            with open(file_path, 'w') as f:
                json.dump(self.keyword_cache, f, indent=2, ensure_ascii=False)
            
            # Update the message to show the saved location
            QMessageBox.information(
                self,
                "Cache Saved",
                f"Successfully saved {len(self.keyword_cache)} keywords to:\n{file_path}"
            )
            
            # Also update the instance variables for consistency
            self.CACHE_FILE = file_path
            self.CACHE_DIR = os.path.dirname(file_path)
            
            return True
                
            QMessageBox.information(
                self,
                "Cache Saved",
                f"Successfully saved {len(self.keyword_cache)} keywords to:\n{file_path}"
            )
            return True
            
        except Exception as e:
            error_msg = f"Error saving cache to text file: {str(e)}"
            print(f"[ERROR] {error_msg}")
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save cache to text file:\n{error_msg}"
            )
            return False
            print("Traceback:")
            traceback.print_exc()
            return False

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
