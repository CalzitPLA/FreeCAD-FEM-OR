"""Radioss Keyword Editor GUI for FreeCAD"""

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
        else:
            print("[WARNING] No documentation URL to open")



class KeywordEditorDialog(QtGui.QDialog):
    """Main dialog for the Radioss Keyword Editor."""
    
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle("Radioss Keyword Editor")
        self.setMinimumSize(1000, 700)
        
        # Initialize state
        self.editing = False
        self.keywords = []
        self.current_keyword = None
        self.param_inputs = {}  # Store parameter input widgets
        self.keyword_cache = []  # Cache for generated keywords
        
        # Template configuration
        self.template_mode = "full"  # "full", "basic", "minimal"
        
        # Load keywords from JSON file
        self.keywords = self.load_keywords() or []
        
        # Initialize UI components
        self.setup_ui()
        
        # Show welcome message
        self.show_welcome_message()
        
        # Populate templates tab
        self.populate_templates_tab()
        
        # Populate initial data
        self.update_category_list()
        self.update_keyword_list()

    def load_settings(self):
        """Load user settings from file."""
        try:
            settings_file = os.path.join(os.path.dirname(__file__), '..', 'keyword_editor_settings.json')
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
            settings_file = os.path.join(os.path.dirname(__file__), '..', 'keyword_editor_settings.json')
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
        """Load keywords from the enhanced JSON file with parameters."""
        try:
            # Try to load from the enhanced JSON file first (with parameters)
            json_path = os.path.join(os.path.dirname(__file__), '..', 'keywords_with_parameters.json')
            if not os.path.exists(json_path):
                # Fall back to the cleaned JSON file
                json_path = os.path.join(os.path.dirname(__file__), '..', 'keywords_clean.json')
                if not os.path.exists(json_path):
                    print(f"Error: Keywords files not found")
                    return []

            with open(json_path, 'r', encoding='utf-8') as f:
                keywords = json.load(f)

            print(f"Loaded {len(keywords)} keywords from {json_path}")
            return keywords

        except Exception as e:
            print(f"Error loading keywords: {e}")
            return []
    
    def _clean_description(self, description):
        """Clean up the keyword description."""
        if not description:
            return "No description available."
            
        # Remove LS-DYNA Input Interface Keyword prefix
        if 'LS-DYNA Input Interface Keyword' in description:
            description = description.split('LS-DYNA Input Interface Keyword', 1)[-1].strip()
            
        # Remove any copyright notices
        if '©' in description:
            description = description.split('©')[0].strip()
            
        return description
    
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
            return
            
        current_category = self.category_combo.currentText()
        self.keywords_list.clear()
        
        for kw in self.keywords:
            if current_category == "All Categories" or kw.get('category') == current_category:
                item = QListWidgetItem(kw.get('name', 'Unnamed'))
                item.setData(QtCore.Qt.UserRole, kw)  # Store the full keyword data
                self.keywords_list.addItem(item)
        
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
        """Show a specific help section and scroll to the LS-DYNA Input section.
        
        Args:
            section_name: Name of the section to show (e.g., 'search_help', 'tutorials')
            scroll_lines: Number of lines to scroll down (default: None, uses preset values)
        """
        base_url = "https://2021.help.altair.com/2021/hwsolvers/rad/topics/solvers/rad"
        
        # Define scroll positions for each section to align LS-DYNA Input at the top
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
            "search_help": "search_help_lsdyna_r.htm",
            "whats_new": "whats_new_lsdyna_r.htm",
            "overview": "overview_lsdyna_r.htm",
            "tutorials": "tutorials_lsdyna_r.htm",
            "user_guide": "user_guide_lsdyna_r.htm",
            "reference_guide": "reference_guide_lsdyna_r.htm",
            "example_guide": "example_guide_lsdyna_r.htm",
            "verification": "verification_problems_lsdyna_r.htm",
            "faq": "faq_lsdyna_r.htm",
            "theory": "theory_manual_lsdyna_r.htm",
            "subroutines": "user_subroutines_lsdyna_r.htm",
            "starter": "starter_input_lsdyna_r.htm",
            "engine": "engine_input_lsdyna_r.htm",
            "index": "index_lsdyna_r.htm"
        }
        
        if section_name in section_map:
            url = f"{base_url}/{section_map[section_name]}"
            # Use preset scroll position if not specified
            scroll_pos = scroll_lines if scroll_lines is not None else section_scrolls.get(section_name, 1000)
            # Add a small delay to ensure the page is loaded before scrolling
            self.show_web_view(url, section="ls-dyna-input-beta", scroll_lines=scroll_pos)
    
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

        # Add Help menu
        help_menu = menubar.addMenu("&Help")

        # Add Template menu
        template_menu = menubar.addMenu("&Templates")

        # Add Examples menu
        examples_menu = menubar.addMenu("&Examples")

        # Add help actions
        search_help_action = help_menu.addAction("Search Help")
        search_help_action.triggered.connect(lambda: self.show_help_section("search_help"))

        tutorials_action = help_menu.addAction("Tutorials")
        tutorials_action.triggered.connect(lambda: self.show_help_section("tutorials"))

        reference_action = help_menu.addAction("Reference Guide")
        reference_action.triggered.connect(lambda: self.show_help_section("reference_guide"))

        # Add template actions
        minimal_template_action = template_menu.addAction("Minimal Template")
        minimal_template_action.triggered.connect(lambda: self.load_minimal_template())

        simulation_template_action = template_menu.addAction("Simulation Template")
        simulation_template_action.triggered.connect(lambda: self.load_simulation_template())

        basic_template_action = template_menu.addAction("Basic Template")
        basic_template_action.triggered.connect(lambda: self.load_basic_template())

        structural_template_action = template_menu.addAction("Structural Template")
        structural_template_action.triggered.connect(lambda: self.load_structural_template())

        thermal_template_action = template_menu.addAction("Transient Thermal")
        thermal_template_action.triggered.connect(lambda: self.load_thermal_template())

        template_menu.addSeparator()

        # Add analysis-specific template actions
        linear_static_action = template_menu.addAction("Linear Static Analysis")
        linear_static_action.triggered.connect(lambda: self.load_linear_static_template())

        modal_analysis_action = template_menu.addAction("Modal Analysis")
        modal_analysis_action.triggered.connect(lambda: self.load_modal_analysis_template())

        steady_thermal_action = template_menu.addAction("Steady-State Thermal")
        steady_thermal_action.triggered.connect(lambda: self.load_steady_state_thermal_template())

        basic_contact_action = template_menu.addAction("Basic Contact")
        basic_contact_action.triggered.connect(lambda: self.load_basic_contact_template())

        template_menu.addSeparator()

        # Add solver differentiation actions
        implicit_action = template_menu.addAction("Implicit Analysis")
        implicit_action.triggered.connect(lambda: self.load_implicit_template())

        explicit_action = template_menu.addAction("Explicit Analysis")
        explicit_action.triggered.connect(lambda: self.load_explicit_template())

        # Add template mode configuration action
        template_mode_action = template_menu.addAction("Template Mode")
        template_mode_action.triggered.connect(self.configure_template_mode)

        # Add example actions
        latest_examples_action = examples_menu.addAction("Latest Examples")
        latest_examples_action.triggered.connect(lambda: self.show_examples_section("latest"))

        introductory_action = examples_menu.addAction("Introductory Examples")
        introductory_action.triggered.connect(lambda: self.show_examples_section("introductory"))

        implicit_action = examples_menu.addAction("Implicit Examples")
        implicit_action.triggered.connect(lambda: self.show_examples_section("implicit"))

        openradioss_action = examples_menu.addAction("OpenRadioss Examples")
        openradioss_action.triggered.connect(lambda: self.show_examples_section("openradioss"))

        # Create main splitter for the content
        self.main_splitter = QSplitter(QtCore.Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)

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

        # Remove the duplicate tab creation that was causing two "Cached Keywords" tabs
        # The first tab creation is kept, the second one (if it exists) is removed

        # Add the tab widget to the right panel's layout
        self.right_layout.addWidget(self.tab_widget)

        # Add right panel to splitter
        self.main_splitter.addWidget(self.right_panel)

        # Set initial sizes
        self.main_splitter.setSizes([200, 600])

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

        button_box.addButton(self.cache_button, QDialogButtonBox.ActionRole)
        
        # Add View Cache button
        self.view_cache_button = QtWidgets.QPushButton("View Cache")
        self.view_cache_button.clicked.connect(self.open_cache_viewer)
        self.view_cache_button.setToolTip("Open the keyword cache viewer")
        button_box.addButton(self.view_cache_button, QDialogButtonBox.ActionRole)

        self.update_file_button = QtWidgets.QPushButton("Update .k File")
        self.update_file_button.clicked.connect(self.update_k_file)
        button_box.addButton(self.update_file_button, QDialogButtonBox.ActionRole)

        main_layout.addWidget(button_box)

    def show_welcome_message(self):
        """Display welcome message in the details panel."""
        welcome_html = """
        <div style="text-align: center; padding: 20px;">
            <h1>Welcome to Radioss Keyword Editor</h1>
            <p style="font-size: 14px; color: #666; margin-top: 20px;">
                This tool helps you manage and edit Radioss keywords for your simulations.
            </p>
            <div style="margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 5px; text-align: left;">
                <h3>Getting Started:</h3>
                <ul>
                    <li>Browse keywords using the list on the left</li>
                    <li>Filter by category using the dropdown menu</li>
                    <li>Select a keyword to view its documentation</li>
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
            self.cache_tab.setPlainText("No keywords cached yet.\n\nGenerate a keyword and click 'Add to Cache' to start building your .k file.")
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
                if obj.Label.startswith("LS-DYNA_k_File"):
                    k_text_object = obj
                    break

            # Create new object if none exists
            if k_text_object is None:
                k_text_object = doc.addObject("App::TextDocument", "LS-DYNA_k_File")
                k_text_object.Label = f"LS-DYNA_k_File_{len(self.keyword_cache)}_keywords"

            # Update the text content
            k_text_object.Text = k_file_content

            # Update the cache tab display
            self.update_cache_display()

            QMessageBox.information(self, "Document Updated",
                                  f"LS-DYNA .k file content updated in document object:\n'{k_text_object.Label}'\n\n"
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
        default_filename = f"updated_model_{len(self.keyword_cache)}_keywords.k"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save .k File to Disk",
            os.path.join(os.path.expanduser("~"), "Documents", default_filename),
            "LS-DYNA files (*.k);;All files (*.*)"
        )

        if not filepath:
            return  # User cancelled

        try:
            with open(filepath, 'w') as f:
                f.write(k_file_content)

            QMessageBox.information(self, "File Saved",
                                  f".k file saved successfully:\n{filepath}")

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
        """Generate complete .k file content from cached keywords."""
        if not self.keyword_cache:
            return "*KEYWORD\n*END"

        # Start with header
        content = "*KEYWORD\n"
        content += "$ Updated LS-DYNA Model with Cached Keywords\n"
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
        """Open or show the cache viewer window."""
        from femcommands.open_cache_viewer import _cache_viewer_instances
        
        # Get or create the cache viewer instance for this document
        doc_name = self.document.Name if hasattr(self, 'document') and self.document else 'global'
        
        if doc_name in _cache_viewer_instances:
            # Existing instance found, just show it
            self.cache_viewer = _cache_viewer_instances[doc_name]
        else:
            # Create new instance
            self.cache_viewer = CacheViewerWindow(self.keyword_cache, self)
            
        # Show and activate the window
        self.cache_viewer.show()
        self.cache_viewer.raise_()
        self.cache_viewer.activateWindow()
        
        # Update the cache from the parent editor if needed
        if hasattr(self, 'keyword_cache'):
            self.cache_viewer.keyword_cache = self.keyword_cache
            self.cache_viewer.update_display()

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
        for field_name in self.param_inputs:
            value = self.param_inputs[field_name].text().strip()
            print(f"[DEBUG] Field '{field_name}' = '{value}'")
            if value:  # Only include non-empty values
                param_values[field_name] = value

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
            # Group parameters in logical groups (typically 8 values per line for LS-DYNA)
            param_items = list(param_values.items())
            
            # Add comment line with variable names
            param_names = [f"{name}" for name, value in param_items]
            lines.append("$# " + " ".join(param_names))
            
            for i in range(0, len(param_items), 8):
                line_params = param_items[i:i+8]
                line_values = [f"{value}" for name, value in line_params]
                lines.append("        " + ", ".join(line_values))

        # Add closing line if there are parameters
        if param_values:
            lines.append("")

        return "\n".join(lines)

    def populate_templates_tab(self):
        """Populate the templates tab with available templates."""
        if not hasattr(self, 'templates_tab'):
            print("[WARNING] Templates tab not initialized")
            return

        templates = self.load_templates()
        if not templates:
            self.templates_tab.addItem("No templates available")
            return

        # Clear existing items
        self.templates_tab.clear()

        # Add template items
        for template_id, template_data in templates.items():
            item = QListWidgetItem(template_data.get('name', template_id))
            item.setData(QtCore.Qt.UserRole, {
                'id': template_id,
                'data': template_data
            })
            self.templates_tab.addItem(item)

        print(f"[INFO] Populated templates tab with {len(templates)} templates")

    def load_template(self, item):
        """Load a template into the keyword cache."""
        if not item:
            return

        template_info = item.data(QtCore.Qt.UserRole)
        if not template_info or 'data' not in template_info:
            QMessageBox.warning(self, "Template Error",
                              "Invalid template data.")
            return

        template_data = template_info['data']
        template_keywords = template_data.get('keywords', [])

        if not template_keywords:
            QMessageBox.warning(self, "Template Error",
                              "Template contains no keywords.")
            return

        # Clear existing cache
        self.keyword_cache = []

        # Add template keywords to cache
        for kw_data in template_keywords:
            keyword_text = self._generate_keyword_text_from_template(kw_data)
            if keyword_text:
                cache_entry = {
                    'text': keyword_text,
                    'timestamp': datetime.datetime.now().strftime("%H:%M:%S"),
                    'keyword_name': kw_data.get('name', 'Unknown')
                }
                self.keyword_cache.append(cache_entry)

        # Update cache display
        self.update_cache_display()

        QMessageBox.information(self, "Template Loaded",
                              f"Template '{template_data.get('name', 'Unknown')}' has been loaded.\n"
                              f"{len(template_keywords)} keywords added to cache.")

    def _generate_keyword_text_from_template(self, kw_data):
        """Generate keyword text from template data."""
        keyword_name = kw_data.get('name', '')
        if not keyword_name:
            return ""

        # Start with the keyword header
        lines = [f"{keyword_name}"]

        # Add parameters if any
        parameters = kw_data.get('parameters', [])
        if parameters:
            for param in parameters:
                # Build parameter string from field values
                param_parts = []
                for i in range(8):  # field_0 through field_7
                    field_name = f'field_{i}'
                    if field_name in param and param[field_name]:
                        param_parts.append(f"{param[field_name]}")

                if param_parts:
                    lines.append("        " + ", ".join(param_parts))

        # Add closing line if there are parameters
        if parameters:
            lines.append("")

    def show_examples_section(self, section):
        """Show examples section in web view or open browser."""
        base_url = "https://www.dynaexamples.com"

        section_urls = {
            "latest": "/latest-examples",
            "introductory": "/introduction",
            "implicit": "/implicit",
            "thermal": "/thermal",
            "structural": "/implicit",
            "fluid": "/icfd",
            "ale": "/ale-s-ale",
            "em": "/em",
            "cese": "/cese",
            "openradioss": "/Example+LS-DYNA+Format+Models"
        }

        if section in section_urls:
            url = base_url + section_urls[section]
            try:
                # Try to use web browser to open the URL
                import webbrowser
                webbrowser.open(url)
                QMessageBox.information(self, "Examples Opened",
                                      f"Opening LS-DYNA Examples section:\n{url}\n\n"
                                      "The examples page will open in your default web browser.")
            except Exception as e:
                QMessageBox.warning(self, "Browser Error",
                                  f"Could not open web browser:\n{str(e)}\n\n"
                                  f"Please visit manually: {url}")

    def load_minimal_template(self):
        """Load a minimal LS-DYNA template with just essentials."""
        minimal_keywords = [
            {"name": "*KEYWORD", "parameters": []},
            {"name": "*CONTROL_TERMINATION", "parameters": [
                {"name": "ENDTIM", "field_0": "1.0", "description": "Termination time"}
            ]},
            {"name": "*CONTROL_TIMESTEP", "parameters": [
                {"name": "DTINIT", "field_0": "0.001", "description": "Initial time step"}
            ]},
            {"name": "*END", "parameters": []}
        ]

        self.load_keywords_from_list(minimal_keywords, "Minimal Template")

    def load_simulation_template(self):
        """Load a general simulation template."""
        simulation_keywords = [
            {"name": "*KEYWORD", "parameters": []},
            {"name": "*CONTROL_TERMINATION", "parameters": [
                {"name": "ENDTIM", "field_0": "1.0", "description": "Termination time"}
            ]},
            {"name": "*CONTROL_TIMESTEP", "parameters": [
                {"name": "DTINIT", "field_0": "0.001", "description": "Initial time step"}
            ]},
            {"name": "*DATABASE_BINARY_D3PLOT", "parameters": [
                {"name": "DT", "field_0": "0.01", "description": "Output interval"}
            ]},
            {"name": "*END", "parameters": []}
        ]

        self.load_keywords_from_list(simulation_keywords, "Simulation Template")

    def load_basic_template(self):
        """Load a basic LS-DYNA template."""
        basic_keywords = [
            {"name": "*KEYWORD", "parameters": []},
            {"name": "*CONTROL_TERMINATION", "parameters": [
                {"name": "ENDTIM", "field_0": "1.0", "description": "Termination time"},
                {"name": "ENDCYC", "field_0": "0", "description": "Termination cycle (0 for time-based)"}
            ]},
            {"name": "*CONTROL_TIMESTEP", "parameters": [
                {"name": "DTINIT", "field_0": "0.001", "description": "Initial time step size"}
            ]},
            {"name": "*DATABASE_BINARY_D3PLOT", "parameters": [
                {"name": "DT", "field_0": "0.01", "description": "Time interval for output"}
            ]},
            {"name": "*END", "parameters": []}
        ]

        self.load_keywords_from_list(basic_keywords, "Basic Template")

    def load_structural_template(self):
        """Load a structural analysis template."""
        structural_keywords = [
            {"name": "*KEYWORD", "parameters": []},
            {"name": "*CONTROL_TERMINATION", "parameters": [
                {"name": "ENDTIM", "field_0": "1.0", "description": "Termination time"}
            ]},
            {"name": "*PART", "parameters": [
                {"name": "PID", "field_0": "1", "description": "Part ID"},
                {"name": "SECID", "field_0": "1", "description": "Section ID"},
                {"name": "MID", "field_0": "1", "description": "Material ID"}
            ]},
            {"name": "*SECTION_SHELL", "parameters": [
                {"name": "SECID", "field_0": "1", "description": "Section ID"},
                {"name": "ELFORM", "field_0": "2", "description": "Element formulation"},
                {"name": "SHRF", "field_0": "0.833", "description": "Shear factor"}
            ]},
            {"name": "*MAT_ELASTIC", "parameters": [
                {"name": "MID", "field_0": "1", "description": "Material ID"},
                {"name": "RO", "field_0": "7800", "description": "Density"},
                {"name": "E", "field_0": "200000", "description": "Young's modulus"},
                {"name": "NU", "field_0": "0.3", "description": "Poisson's ratio"}
            ]},
            {"name": "*END", "parameters": []}
        ]

        self.load_keywords_from_list(structural_keywords, "Structural Template")

    def load_thermal_template(self):
        """Load a thermal analysis template."""
        thermal_keywords = [
            {"name": "*KEYWORD", "parameters": []},
            {"name": "*CONTROL_THERMAL_SOLVER", "parameters": [
                {"name": "TSLIMT", "field_0": "1", "description": "Thermal solver type"}
            ]},
            {"name": "*CONTROL_THERMAL_TIMESTEP", "parameters": [
                {"name": "DT", "field_0": "0.001", "description": "Time step"}
            ]},
            {"name": "*MAT_THERMAL_ISOTROPIC", "parameters": [
                {"name": "MID", "field_0": "1", "description": "Material ID"},
                {"name": "RO", "field_0": "7800", "description": "Density"},
                {"name": "CP", "field_0": "460", "description": "Specific heat"},
                {"name": "K", "field_0": "50", "description": "Thermal conductivity"}
            ]},
            {"name": "*BOUNDARY_THERMAL", "parameters": [
                {"name": "PID", "field_0": "1", "description": "Part ID"},
                {"name": "TYPE", "field_0": "1", "description": "Boundary type"}
            ]},
            {"name": "*END", "parameters": []}
        ]

    def load_linear_static_template(self):
        """Load a linear static analysis template."""
        linear_static_keywords = [
            {"name": "*KEYWORD", "parameters": []},
            {"name": "*CONTROL_TERMINATION", "parameters": [
                {"name": "ENDTIM", "field_0": "1.0", "description": "Termination time"}
            ]},
            {"name": "*CONTROL_IMPLICIT_GENERAL", "parameters": [
                {"name": "IMFLAG", "field_0": "1", "description": "Implicit flag (1=linear, 2=nonlinear)"}
            ]},
            {"name": "*CONTROL_IMPLICIT_SOLUTION", "parameters": [
                {"name": "NSOLVR", "field_0": "1", "description": "Linear solver type"}
            ]},
            {"name": "*CONTROL_IMPLICIT_TERMINATION", "parameters": [
                {"name": "ENDTIM", "field_0": "1.0", "description": "Termination time"}
            ]},
            {"name": "*PART", "parameters": [
                {"name": "PID", "field_0": "1", "description": "Part ID"},
                {"name": "SECID", "field_0": "1", "description": "Section ID"},
                {"name": "MID", "field_0": "1", "description": "Material ID"}
            ]},
            {"name": "*SECTION_SHELL", "parameters": [
                {"name": "SECID", "field_0": "1", "description": "Section ID"},
                {"name": "ELFORM", "field_0": "2", "description": "Element formulation"},
                {"name": "SHRF", "field_0": "0.833", "description": "Shear factor"}
            ]},
            {"name": "*MAT_ELASTIC", "parameters": [
                {"name": "MID", "field_0": "1", "description": "Material ID"},
                {"name": "RO", "field_0": "7800", "description": "Density"},
                {"name": "E", "field_0": "200000", "description": "Young's modulus"},
                {"name": "NU", "field_0": "0.3", "description": "Poisson's ratio"}
            ]},
            {"name": "*BOUNDARY_SPC_NODE", "parameters": [
                {"name": "NID", "field_0": "1", "description": "Node ID"},
                {"name": "CID", "field_0": "0", "description": "Coordinate system ID"},
                {"name": "DOF", "field_0": "123456", "description": "Degrees of freedom"}
            ]},
            {"name": "*LOAD_NODE_POINT", "parameters": [
                {"name": "NID", "field_0": "2", "description": "Node ID"},
                {"name": "DOF", "field_0": "2", "description": "Direction"},
                {"name": "LCID", "field_0": "1", "description": "Load curve ID"}
            ]},
            {"name": "*DEFINE_CURVE", "parameters": [
                {"name": "LCID", "field_0": "1", "description": "Load curve ID"},
                {"name": "SIDR", "field_0": "0", "description": "Scale factor"},
                {"name": "SFA", "field_0": "1.0", "description": "Scale factor A"},
                {"name": "SFO", "field_0": "0.0", "description": "Offset"}
            ]},
            {"name": "*END", "parameters": []}
        ]

        self.load_keywords_from_list(linear_static_keywords, "Linear Static Template")

    def load_modal_analysis_template(self):
        """Load a modal analysis template."""
        modal_keywords = [
            {"name": "*KEYWORD", "parameters": []},
            {"name": "*CONTROL_IMPLICIT_EIGENVALUE", "parameters": [
                {"name": "NEIG", "field_0": "10", "description": "Number of eigenvalues"},
                {"name": "METHOD", "field_0": "1", "description": "Solution method"}
            ]},
            {"name": "*CONTROL_TERMINATION", "parameters": [
                {"name": "ENDTIM", "field_0": "1.0", "description": "Termination time"}
            ]},
            {"name": "*PART", "parameters": [
                {"name": "PID", "field_0": "1", "description": "Part ID"},
                {"name": "SECID", "field_0": "1", "description": "Section ID"},
                {"name": "MID", "field_0": "1", "description": "Material ID"}
            ]},
            {"name": "*SECTION_SHELL", "parameters": [
                {"name": "SECID", "field_0": "1", "description": "Section ID"},
                {"name": "ELFORM", "field_0": "2", "description": "Element formulation"},
                {"name": "SHRF", "field_0": "0.833", "description": "Shear factor"}
            ]},
            {"name": "*MAT_ELASTIC", "parameters": [
                {"name": "MID", "field_0": "1", "description": "Material ID"},
                {"name": "RO", "field_0": "7800", "description": "Density"},
                {"name": "E", "field_0": "200000", "description": "Young's modulus"},
                {"name": "NU", "field_0": "0.3", "description": "Poisson's ratio"}
            ]},
            {"name": "*BOUNDARY_SPC_NODE", "parameters": [
                {"name": "NID", "field_0": "1", "description": "Node ID"},
                {"name": "CID", "field_0": "0", "description": "Coordinate system ID"},
                {"name": "DOF", "field_0": "123456", "description": "Degrees of freedom"}
            ]},
            {"name": "*END", "parameters": []}
        ]

        self.load_keywords_from_list(modal_keywords, "Modal Analysis Template")

    def load_steady_state_thermal_template(self):
        """Load a steady-state thermal analysis template."""
        thermal_keywords = [
            {"name": "*KEYWORD", "parameters": []},
            {"name": "*CONTROL_THERMAL_SOLVER", "parameters": [
                {"name": "TSLIMT", "field_0": "1", "description": "Thermal solver type (1=steady-state)"}
            ]},
            {"name": "*CONTROL_THERMAL_TIMESTEP", "parameters": [
                {"name": "DT", "field_0": "0.001", "description": "Time step"},
                {"name": "TSSFAC", "field_0": "0.9", "description": "Time step safety factor"}
            ]},
            {"name": "*CONTROL_TERMINATION", "parameters": [
                {"name": "ENDTIM", "field_0": "1000.0", "description": "Termination time (steady-state convergence)"}
            ]},
            {"name": "*PART", "parameters": [
                {"name": "PID", "field_0": "1", "description": "Part ID"},
                {"name": "SECID", "field_0": "1", "description": "Section ID"},
                {"name": "MID", "field_0": "1", "description": "Material ID"}
            ]},
            {"name": "*SECTION_SOLID", "parameters": [
                {"name": "SECID", "field_0": "1", "description": "Section ID"},
                {"name": "ELFORM", "field_0": "1", "description": "Element formulation"}
            ]},
            {"name": "*MAT_THERMAL_ISOTROPIC", "parameters": [
                {"name": "MID", "field_0": "1", "description": "Material ID"},
                {"name": "RO", "field_0": "7800", "description": "Density"},
                {"name": "CP", "field_0": "460", "description": "Specific heat"},
                {"name": "K", "field_0": "50", "description": "Thermal conductivity"}
            ]},
            {"name": "*BOUNDARY_THERMAL", "parameters": [
                {"name": "PID", "field_0": "1", "description": "Part ID"},
                {"name": "TYPE", "field_0": "1", "description": "Boundary type (1=temperature)"}
            ]},
            {"name": "*LOAD_THERMAL_BODY", "parameters": [
                {"name": "PID", "field_0": "1", "description": "Part ID"},
                {"name": "LCID", "field_0": "1", "description": "Load curve ID"}
            ]},
            {"name": "*DEFINE_CURVE", "parameters": [
                {"name": "LCID", "field_0": "1", "description": "Load curve ID"},
                {"name": "SIDR", "field_0": "0", "description": "Scale factor"},
                {"name": "SFA", "field_0": "100.0", "description": "Heat generation rate"}
            ]},
            {"name": "*END", "parameters": []}
        ]

        self.load_keywords_from_list(thermal_keywords, "Steady-State Thermal Template")

    def load_basic_contact_template(self):
        """Load a basic contact analysis template."""
        contact_keywords = [
            {"name": "*KEYWORD", "parameters": []},
            {"name": "*CONTROL_TERMINATION", "parameters": [
                {"name": "ENDTIM", "field_0": "1.0", "description": "Termination time"}
            ]},
            {"name": "*CONTROL_CONTACT", "parameters": [
                {"name": "SLSFAC", "field_0": "0.1", "description": "Scale factor for sliding"},
                {"name": "RWGAPS", "field_0": "1", "description": "Rigid wall gap stiffness"}
            ]},
            {"name": "*PART", "parameters": [
                {"name": "PID", "field_0": "1", "description": "Part 1 ID"},
                {"name": "SECID", "field_0": "1", "description": "Section 1 ID"},
                {"name": "MID", "field_0": "1", "description": "Material 1 ID"}
            ]},
            {"name": "*PART", "parameters": [
                {"name": "PID", "field_0": "2", "description": "Part 2 ID"},
                {"name": "SECID", "field_0": "2", "description": "Section 2 ID"},
                {"name": "MID", "field_0": "1", "description": "Material 2 ID"}
            ]},
            {"name": "*SECTION_SHELL", "parameters": [
                {"name": "SECID", "field_0": "1", "description": "Section 1 ID"},
                {"name": "ELFORM", "field_0": "2", "description": "Element formulation"}
            ]},
            {"name": "*SECTION_SHELL", "parameters": [
                {"name": "SECID", "field_0": "2", "description": "Section 2 ID"},
                {"name": "ELFORM", "field_0": "2", "description": "Element formulation"}
            ]},
            {"name": "*MAT_ELASTIC", "parameters": [
                {"name": "MID", "field_0": "1", "description": "Material ID"},
                {"name": "RO", "field_0": "7800", "description": "Density"},
                {"name": "E", "field_0": "200000", "description": "Young's modulus"},
                {"name": "NU", "field_0": "0.3", "description": "Poisson's ratio"}
            ]},
            {"name": "*CONTACT_AUTOMATIC_SURFACE_TO_SURFACE", "parameters": [
                {"name": "SSID", "field_0": "1", "description": "Slave surface ID"},
                {"name": "MSID", "field_0": "1", "description": "Master surface ID"}
            ]},
            {"name": "*SET_SEGMENT", "parameters": [
                {"name": "SID", "field_0": "1", "description": "Segment set ID"},
                {"name": "DA", "field_0": "1", "description": "Delete flag"}
            ]},
            {"name": "*BOUNDARY_SPC_NODE", "parameters": [
                {"name": "NID", "field_0": "1", "description": "Node ID"},
                {"name": "CID", "field_0": "0", "description": "Coordinate system ID"},
                {"name": "DOF", "field_0": "123456", "description": "Degrees of freedom"}
            ]},
            {"name": "*LOAD_NODE_POINT", "parameters": [
                {"name": "NID", "field_0": "2", "description": "Node ID"},
                {"name": "DOF", "field_0": "2", "description": "Direction"},
                {"name": "LCID", "field_0": "1", "description": "Load curve ID"}
            ]},
            {"name": "*DEFINE_CURVE", "parameters": [
                {"name": "LCID", "field_0": "1", "description": "Load curve ID"},
                {"name": "SIDR", "field_0": "0", "description": "Scale factor"},
                {"name": "SFA", "field_0": "1.0", "description": "Scale factor"}
            ]},
            {"name": "*END", "parameters": []}
        ]

        self.load_keywords_from_list(contact_keywords, "Basic Contact Template")

    def load_implicit_template(self):
        """Load an implicit analysis template."""
        implicit_keywords = [
            {"name": "*KEYWORD", "parameters": []},
            {"name": "*CONTROL_IMPLICIT_GENERAL", "parameters": [
                {"name": "IMFLAG", "field_0": "2", "description": "Implicit flag (2=nonlinear)"}
            ]},
            {"name": "*CONTROL_IMPLICIT_SOLUTION", "parameters": [
                {"name": "NSOLVR", "field_0": "12", "description": "Nonlinear solver (BCSLIB)"}
            ]},
            {"name": "*CONTROL_IMPLICIT_TERMINATION", "parameters": [
                {"name": "ENDTIM", "field_0": "1.0", "description": "Termination time"}
            ]},
            {"name": "*CONTROL_TERMINATION", "parameters": [
                {"name": "ENDTIM", "field_0": "1.0", "description": "Termination time"}
            ]},
            {"name": "*PART", "parameters": [
                {"name": "PID", "field_0": "1", "description": "Part ID"},
                {"name": "SECID", "field_0": "1", "description": "Section ID"},
                {"name": "MID", "field_0": "1", "description": "Material ID"}
            ]},
            {"name": "*SECTION_SHELL", "parameters": [
                {"name": "SECID", "field_0": "1", "description": "Section ID"},
                {"name": "ELFORM", "field_0": "2", "description": "Element formulation"},
                {"name": "SHRF", "field_0": "0.833", "description": "Shear factor"}
            ]},
            {"name": "*MAT_ELASTIC", "parameters": [
                {"name": "MID", "field_0": "1", "description": "Material ID"},
                {"name": "RO", "field_0": "7800", "description": "Density"},
                {"name": "E", "field_0": "200000", "description": "Young's modulus"},
                {"name": "NU", "field_0": "0.3", "description": "Poisson's ratio"}
            ]},
            {"name": "*MAT_PLASTIC_KINEMATIC", "parameters": [
                {"name": "MID", "field_0": "2", "description": "Material ID"},
                {"name": "RO", "field_0": "7800", "description": "Density"},
                {"name": "E", "field_0": "200000", "description": "Young's modulus"},
                {"name": "NU", "field_0": "0.3", "description": "Poisson's ratio"},
                {"name": "SIGY", "field_0": "250", "description": "Yield stress"}
            ]},
            {"name": "*BOUNDARY_SPC_NODE", "parameters": [
                {"name": "NID", "field_0": "1", "description": "Node ID"},
                {"name": "CID", "field_0": "0", "description": "Coordinate system ID"},
                {"name": "DOF", "field_0": "123456", "description": "Degrees of freedom"}
            ]},
            {"name": "*LOAD_NODE_POINT", "parameters": [
                {"name": "NID", "field_0": "2", "description": "Node ID"},
                {"name": "DOF", "field_0": "2", "description": "Direction"},
                {"name": "LCID", "field_0": "1", "description": "Load curve ID"}
            ]},
            {"name": "*DEFINE_CURVE", "parameters": [
                {"name": "LCID", "field_0": "1", "description": "Load curve ID"},
                {"name": "SIDR", "field_0": "0", "description": "Scale factor"},
                {"name": "SFA", "field_0": "1.0", "description": "Scale factor"}
            ]},
            {"name": "*END", "parameters": []}
        ]

        self.load_keywords_from_list(implicit_keywords, "Implicit Analysis Template")

    def load_explicit_template(self):
        """Load an explicit analysis template."""
        explicit_keywords = [
            {"name": "*KEYWORD", "parameters": []},
            {"name": "*CONTROL_TERMINATION", "parameters": [
                {"name": "ENDTIM", "field_0": "0.1", "description": "Termination time"}
            ]},
            {"name": "*CONTROL_TIMESTEP", "parameters": [
                {"name": "DTINIT", "field_0": "0.001", "description": "Initial time step"},
                {"name": "TSSFAC", "field_0": "0.9", "description": "Time step safety factor"}
            ]},
            {"name": "*CONTROL_HOURGLASS", "parameters": [
                {"name": "IHQ", "field_0": "4", "description": "Hourglass control type"}
            ]},
            {"name": "*CONTROL_CONTACT", "parameters": [
                {"name": "SLSFAC", "field_0": "0.1", "description": "Scale factor for sliding"}
            ]},
            {"name": "*CONTROL_ENERGY", "parameters": [
                {"name": "HGEN", "field_0": "2", "description": "Hourglass energy computation"}
            ]},
            {"name": "*DATABASE_BINARY_D3PLOT", "parameters": [
                {"name": "DT", "field_0": "0.01", "description": "Output interval"}
            ]},
            {"name": "*DATABASE_HISTORY_NODE", "parameters": [
                {"name": "ID", "field_0": "1", "description": "Node ID"},
                {"name": "DT", "field_0": "0.001", "description": "Output interval"}
            ]},
            {"name": "*PART", "parameters": [
                {"name": "PID", "field_0": "1", "description": "Part ID"},
                {"name": "SECID", "field_0": "1", "description": "Section ID"},
                {"name": "MID", "field_0": "1", "description": "Material ID"}
            ]},
            {"name": "*SECTION_SHELL", "parameters": [
                {"name": "SECID", "field_0": "1", "description": "Section ID"},
                {"name": "ELFORM", "field_0": "2", "description": "Element formulation"},
                {"name": "SHRF", "field_0": "0.833", "description": "Shear factor"}
            ]},
            {"name": "*MAT_PLASTIC_KINEMATIC", "parameters": [
                {"name": "MID", "field_0": "1", "description": "Material ID"},
                {"name": "RO", "field_0": "7800", "description": "Density"},
                {"name": "E", "field_0": "200000", "description": "Young's modulus"},
                {"name": "NU", "field_0": "0.3", "description": "Poisson's ratio"},
                {"name": "SIGY", "field_0": "250", "description": "Yield stress"}
            ]},
            {"name": "*BOUNDARY_SPC_NODE", "parameters": [
                {"name": "NID", "field_0": "1", "description": "Node ID"},
                {"name": "CID", "field_0": "0", "description": "Coordinate system ID"},
                {"name": "DOF", "field_0": "123456", "description": "Degrees of freedom"}
            ]},
            {"name": "*LOAD_NODE_POINT", "parameters": [
                {"name": "NID", "field_0": "2", "description": "Node ID"},
                {"name": "DOF", "field_0": "2", "description": "Direction"},
                {"name": "LCID", "field_0": "1", "description": "Load curve ID"}
            ]},
            {"name": "*DEFINE_CURVE", "parameters": [
                {"name": "LCID", "field_0": "1", "description": "Load curve ID"},
                {"name": "SIDR", "field_0": "0", "description": "Scale factor"},
                {"name": "SFA", "field_0": "1.0", "description": "Scale factor"}
            ]},
            {"name": "*END", "parameters": []}
        ]

        self.load_keywords_from_list(explicit_keywords, "Explicit Analysis Template")

    def load_keywords_from_list(self, keywords_list, template_name):
        """Load keywords from a list into the cache."""
        # Clear existing cache
        self.keyword_cache = []

        # Add keywords to cache
        for kw_data in keywords_list:
            keyword_text = self._generate_keyword_text_from_data(kw_data)
            if keyword_text:
                import datetime
                cache_entry = {
                    'text': keyword_text,
                    'timestamp': datetime.datetime.now().strftime("%H:%M:%S"),
                    'keyword_name': kw_data['name']
                }
                self.keyword_cache.append(cache_entry)

        # Update cache display
        self.update_cache_display()

        QMessageBox.information(self, "Template Loaded",
                              f"Template '{template_name}' has been loaded.\n"
                              f"{len(keywords_list)} keywords added to cache.")

    def _generate_keyword_text_from_data(self, kw_data):
        """Generate keyword text from keyword data dictionary."""
        keyword_name = kw_data.get('name', '')
        if not keyword_name:
            return ""

        # Start with the keyword header
        lines = [f"{keyword_name}"]

        # Add parameters if any
        parameters = kw_data.get('parameters', [])
        if parameters:
            for param in parameters:
                # Build parameter string from field values
                param_parts = []
                for i in range(8):  # field_0 through field_7
                    field_name = f'field_{i}'
                    if field_name in param and param[field_name]:
                        param_parts.append(f"{param[field_name]}")

                if param_parts:
                    lines.append("        " + ", ".join(param_parts))

        # Add closing line if there are parameters
        if parameters:
            lines.append("")

        return "\n".join(lines)


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
            self.keyword_cache = cache_data

    def setup_ui(self):
        """Set up the user interface."""
        layout = QtGui.QVBoxLayout(self)

        # Title and info
        title_label = QtGui.QLabel("LS-DYNA Keyword Cache")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)

        info_label = QtGui.QLabel(f"Total cached keywords: {len(self.keyword_cache)}")
        info_label.setStyleSheet("font-size: 12px; color: #666; margin: 5px;")
        layout.addWidget(info_label)

        # Create splitter for main content
        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)

        # Cache list widget
        self.cache_list = QtGui.QListWidget()
        self.cache_list.setMaximumHeight(200)
        self.cache_list.itemDoubleClicked.connect(self.show_keyword_details)
        splitter.addWidget(self.cache_list)

        # Keyword content viewer
        self.content_text = QtGui.QTextEdit()
        self.content_text.setReadOnly(True)
        splitter.addWidget(self.content_text)

        layout.addWidget(splitter)

        # Buttons
        button_layout = QtGui.QHBoxLayout()

        self.refresh_button = QtGui.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.update_display)
        button_layout.addWidget(self.refresh_button)

        self.remove_button = QtGui.QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_selected)
        button_layout.addWidget(self.remove_button)

        self.clear_all_button = QtGui.QPushButton("Clear All")
        self.clear_all_button.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_all_button)

        button_layout.addStretch()

        self.generate_k_button = QtGui.QPushButton("Generate .k File")
        self.generate_k_button.clicked.connect(self.generate_k_file)
        button_layout.addWidget(self.generate_k_button)

        self.close_button = QtGui.QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def update_display(self):
        """Update the cache display."""
        self.cache_list.clear()

        if not self.keyword_cache:
            self.content_text.setPlainText("No keywords cached yet.\n\nGenerate a keyword and click 'Add to Cache' to start building your .k file.")
            return

        for i, entry in enumerate(self.keyword_cache, 1):
            item_text = f"{i}. {entry['keyword_name']} ({entry['timestamp']})"
            item = QtGui.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, entry)
            self.cache_list.addItem(item)

        # Update info label
        info_label = self.findChild(QtGui.QLabel)
        if info_label:
            info_label.setText(f"Total cached keywords: {len(self.keyword_cache)}")

        # Show first item details
        if self.cache_list.count() > 0:
            self.cache_list.setCurrentRow(0)
            self.show_keyword_details(self.cache_list.item(0))

    def show_keyword_details(self, item):
        """Show details of the selected cached keyword."""
        if not item:
            return

        entry = item.data(QtCore.Qt.UserRole)
        if not entry:
            return

        # Show keyword content
        content = f"Keyword: {entry['keyword_name']}\n"
        content += f"Timestamp: {entry['timestamp']}\n"
        content += "=" * 50 + "\n\n"
        content += entry['text']

        self.content_text.setPlainText(content)

    def remove_selected(self):
        """Remove the selected cached keyword."""
        current_row = self.cache_list.currentRow()
        if current_row < 0:
            QtGui.QMessageBox.warning(self, "No Selection",
                                    "Please select a keyword to remove.")
            return

        reply = QtGui.QMessageBox.question(
            self, "Remove Keyword",
            "Are you sure you want to remove this keyword from the cache?",
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
        )

        if reply == QtGui.QMessageBox.Yes:
            # Remove from cache
            if 0 <= current_row < len(self.keyword_cache):
                removed_entry = self.keyword_cache.pop(current_row)

                # Update parent editor's cache
                if self.parent_editor:
                    self.parent_editor.keyword_cache = self.keyword_cache
                    self.parent_editor.update_cache_display()

                self.update_display()

                QtGui.QMessageBox.information(
                    self, "Keyword Removed",
                    f"Removed keyword '{removed_entry['keyword_name']}' from cache."
                )

    def clear_all(self):
        """Clear all cached keywords."""
        if not self.keyword_cache:
            QtGui.QMessageBox.information(self, "Cache Empty",
                                        "No keywords in cache to clear.")
            return

        reply = QtGui.QMessageBox.question(
            self, "Clear All Keywords",
            f"Are you sure you want to clear all {len(self.keyword_cache)} cached keywords?",
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No
        )

        if reply == QtGui.QMessageBox.Yes:
            self.keyword_cache.clear()

            # Update parent editor's cache
            if self.parent_editor:
                self.parent_editor.keyword_cache = self.keyword_cache
                self.parent_editor.update_cache_display()

            self.update_display()

            QtGui.QMessageBox.information(self, "Cache Cleared",
                                        "All cached keywords have been removed.")

    def generate_k_file(self):
        """Generate .k file from current cache."""
        if not self.keyword_cache:
            QtGui.QMessageBox.warning(self, "No Keywords",
                                    "No keywords in cache to generate file from.")
            return

        # Use the parent editor's method to generate the file
        if self.parent_editor and hasattr(self.parent_editor, 'update_k_file'):
            self.parent_editor.update_k_file()