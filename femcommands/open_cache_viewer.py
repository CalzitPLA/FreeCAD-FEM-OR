"""
Open LS-DYNA Cache Viewer command for FreeCAD.
"""

__all__ = ['OpenCacheViewer', 'CacheViewerWindow']

import os
import json
import copy
import traceback
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

# Import CommandManager from the local commands module
from .manager import CommandManager

# Import CacheViewerWindow from the current module
# The class is defined later in this file

# Initialize cache directory variables
CACHE_DIR = ""
CACHE_FILE = ""

def init_cache_paths():
    """Initialize the cache directory paths with fallbacks."""
    global CACHE_DIR, CACHE_FILE
    
    # Try different standard locations in order of preference
    possible_paths = [
        # Standard XDG cache directory
        os.path.join(os.path.expanduser('~/.cache'), 'FreeCAD', 'Fem_upgraded'),
        # Fallback to FreeCAD config directory
        os.path.join(App.getUserAppDataDir(), 'cache', 'Fem_upgraded'),
        # Final fallback to home directory
        os.path.join(os.path.expanduser('~'), '.FreeCAD', 'Fem_upgraded_cache')
    ]
    
    # Try each path until we find one that works
    for path in possible_paths:
        try:
            os.makedirs(path, exist_ok=True, mode=0o755)
            # Test if we can write to the directory
            test_file = os.path.join(path, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            # If we get here, the path is good
            CACHE_DIR = path
            CACHE_FILE = os.path.join(path, 'keyword_cache.json')
            print(f"Using cache directory: {CACHE_DIR}")
            return
            
        except (OSError, IOError) as e:
            print(f"Could not use cache directory {path}: {e}")
    
    # If all else fails, use a temporary directory
    import tempfile
    CACHE_DIR = os.path.join(tempfile.gettempdir(), 'freecad_fem_upgraded_cache')
    os.makedirs(CACHE_DIR, exist_ok=True, mode=0o777)
    CACHE_FILE = os.path.join(CACHE_DIR, 'keyword_cache.json')
    print(f"WARNING: Using temporary cache directory: {CACHE_DIR}")

# Initialize the cache paths
init_cache_paths()

def ensure_cache_dir():
    """Ensure the cache directory exists and is writable."""
    try:
        # Check if directory exists and is writable
        if os.path.exists(CACHE_DIR):
            test_file = os.path.join(CACHE_DIR, '.write_test')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                return True
            except (IOError, OSError):
                print(f"Warning: Cache directory {CACHE_DIR} is not writable")
        
        # If we get here, either directory doesn't exist or isn't writable
        os.makedirs(CACHE_DIR, exist_ok=True, mode=0o755)
        # Verify we can write to it
        test_file = os.path.join(CACHE_DIR, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print(f"Using cache directory: {CACHE_DIR}")
        return True
        
    except Exception as e:
        print(f"Error with cache directory {CACHE_DIR}: {e}")
        return False

def save_cache_to_disk(cache_data):
    """Save the cache data to disk."""
    try:
        # Print debug info about the cache data
        cache_size = len(cache_data) if cache_data else 0
        print(f"[CACHE] Saving {cache_size} items to disk...")
        
        # Ensure cache directory exists
        if not ensure_cache_dir():
            print(f"[CACHE] Error: Could not ensure cache directory exists at {CACHE_DIR}")
            return False
            
        # Write the cache file
        print(f"[CACHE] Writing cache to: {CACHE_FILE}")
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
            
        # Verify the file was written
        if os.path.exists(CACHE_FILE):
            file_size = os.path.getsize(CACHE_FILE)
            print(f"[CACHE] Successfully wrote {file_size} bytes to {CACHE_FILE}")
            if cache_size > 0:
                print(f"[CACHE] First item in cache: {str(cache_data[0])[:100]}...")
            return True
        else:
            print(f"[CACHE] Error: Cache file was not created at {CACHE_FILE}")
            return False
            
    except Exception as e:
        import traceback
        print(f"[CACHE] Error saving cache to disk: {e}")
        print("Traceback:")
        traceback.print_exc()
        return False

def load_cache_from_disk():
    """Load the cache data from disk."""
    if not os.path.exists(CACHE_FILE):
        print(f"No cache file found at {CACHE_FILE}")
        return []
    
    try:
        print(f"Loading cache from {CACHE_FILE}")
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
            if not isinstance(data, list):
                print(f"Warning: Cache file does not contain a list, got {type(data)}")
                return []
            print(f"Loaded {len(data)} items from cache")
            return data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from cache file {CACHE_FILE}: {e}")
        # Try to create a backup of the corrupted file
        try:
            import shutil
            backup_file = f"{CACHE_FILE}.corrupted.{int(time.time())}"
            shutil.copy2(CACHE_FILE, backup_file)
            print(f"Created backup of corrupted cache file at {backup_file}")
        except Exception as backup_err:
            print(f"Could not create backup of corrupted cache file: {backup_err}")
        return []
    except Exception as e:
        print(f"Error loading cache from disk: {e}")
        import traceback
        traceback.print_exc()
        return []

class OpenCacheViewer:
    """Command to open the LS-DYNA cache viewer window."""
    
    def __init__(self):
        self.menutext = "Open Cache Viewer"
        self.tooltip = "Open the LS-DYNA keyword cache viewer"
        self.pixmap = "document-open"
        self.is_active = "always"

    def GetResources(self):
        """Return a dictionary with data that will be used by the button or menu item."""
        return {
            'Pixmap': self.pixmap,
            'MenuText': self.menutext,
            'ToolTip': self.tooltip,
            'CmdType': 'ForEdit'
        }
        
    def IsActive(self):
        """Define whether the command is active or not (greyed out)."""
        return True

    def Activated(self):
        """Run the command to open the cache viewer."""
        try:
            print("\n=== OpenCacheViewer: Starting to open cache viewer ===")
            cache_data = []
            parent_editor = None
            source = "disk"  # Default source is disk

            # Debug: Get the active document and window
            active_doc = App.ActiveDocument
            print(f"Active document: {active_doc.Name if active_doc else 'None'}")
            
            # Get the main FreeCAD window
            mw = Gui.getMainWindow()
            print(f"Main window: {mw}")
            
            # Debug: Print all top-level widgets
            print("\nTop-level widgets:")
            for i, widget in enumerate(QtWidgets.QApplication.topLevelWidgets()):
                name = widget.objectName()
                title = widget.windowTitle()
                print(f"  {i}: {name} - {title} - {type(widget)}")

            # First try to get cache from an open keyword editor
            print("\nLooking for keyword editor...")
            for widget in QtWidgets.QApplication.topLevelWidgets():
                try:
                    widget_name = widget.objectName()
                    widget_title = widget.windowTitle()
                    
                    print(f"  Checking widget: {widget_name} - {widget_title}")
                    
                    # Check if this is the keyword editor
                    is_keyword_editor = (
                        'KeywordEditorDialog' in widget_name or 
                        'Radioss Keyword Editor' in widget_title or
                        (hasattr(widget, 'keyword_cache') and hasattr(widget, 'document'))
                    )
                    
                    if is_keyword_editor:
                        print("  Found keyword editor!")
                        if hasattr(widget, 'keyword_cache'):
                            cache_data = widget.keyword_cache
                            parent_editor = widget
                            source = "editor"
                            print(f"  Found {len(cache_data)} cached keywords from editor")
                            if hasattr(widget, 'document'):
                                print(f"  Editor document: {widget.document.Name if widget.document else 'None'}")
                            break
                        else:
                            print("  Widget has no keyword_cache attribute")
                except Exception as e:
                    print(f"  Error checking widget: {str(e)}")
            
            # If no editor found, try to load from disk
            if not cache_data:
                print("\nNo editor found with cache, loading from disk...")
                cache_data = load_cache_from_disk()
                print(f"  Loaded {len(cache_data)} keywords from disk")
            
            # Create or show the cache viewer window
            print("\nCreating/showing cache viewer...")
            
            # Check if we have a document-specific viewer to show
            doc_name = None
            if parent_editor and hasattr(parent_editor, 'document') and parent_editor.document:
                doc_name = parent_editor.document.Name
                print(f"  Document name: {doc_name}")
                if doc_name in _cache_viewer_instances:
                    viewer = _cache_viewer_instances[doc_name]
                    print(f"  Found existing viewer for document: {doc_name}")
                    
                    # Update the viewer's data
                    viewer.keyword_cache = cache_data
                    viewer.parent_editor = parent_editor
                    viewer.update_display()
                    
                    # Ensure the window is visible
                    if viewer.isHidden():
                        print("  Viewer was hidden, showing now")
                        viewer.show()
                    
                    # Bring to front
                    viewer.raise_()
                    viewer.activateWindow()
                    print("  Brought existing viewer to front")
                    return
            
            # If we get here, we need to create a new viewer
            print("  Creating new cache viewer window")
            try:
                viewer = CacheViewerWindow(cache_data, parent_editor, source)
                print("  CacheViewerWindow created successfully")
                
                # If we have a parent editor with a document, store it in our instances
                if doc_name:
                    _cache_viewer_instances[doc_name] = viewer
                    print(f"  Stored viewer for document: {doc_name}")
                
                # Show the window
                print("  Showing new viewer")
                viewer.show()
                viewer.raise_()
                viewer.activateWindow()
                print("  Viewer should be visible now")
                
            except Exception as e:
                print(f"ERROR creating CacheViewerWindow: {str(e)}\n{traceback.format_exc()}")
                raise
            
            print("\n=== OpenCacheViewer: Finished successfully ===\n")
            return True
            
        except Exception as e:
            error_msg = f"An error occurred while opening the cache viewer:\n{str(e)}\n\n{traceback.format_exc()}"
            print(f"\n!!! OpenCacheViewer ERROR: {error_msg}")
            QtWidgets.QMessageBox.critical(None, "Error Opening Cache Viewer", 
                "Failed to open the cache viewer. Please check the Python console for details.")
            return False

    def IsActive(self):
        """Define whether the command is active or not (greyed out)."""
        # Always active
        return True


# Global dictionary to store cache viewer instances per document
_cache_viewer_instances = {}

class CacheViewerWindow(QtWidgets.QDialog):
    """Window for viewing and managing cached LS-DYNA keywords."""
    
    # Class variable to track last update time for rate limiting
    _last_update_time = 0
    MIN_UPDATE_INTERVAL = 500  # milliseconds

    def __init__(self, keyword_cache=None, parent=None, source="editor"):
        super(CacheViewerWindow, self).__init__(parent)
        
        # Performance optimization flags
        self._update_pending = False
        self._is_updating = False
        self._cache_version = 0
        
        # Store reference to the analysis document if available
        self.analysis_doc = None
        if parent and hasattr(parent, 'document') and parent.document:
            self.analysis_doc = parent.document
        
        # Initialize cache
        self.keyword_cache = keyword_cache or []
        
        # Ensure each keyword has required fields
        self._initialize_cache_items()
        
        self.parent_editor = parent
        self.cache_source = source
        self.setWindowTitle("LS-DYNA Keyword Cache")
        self.setMinimumSize(800, 500)  # Slightly larger default size
        self.setModal(False)
        
        # Window flags for better behavior
        self.setWindowFlags(
            QtCore.Qt.Window | 
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.WindowMinMaxButtonsHint |
            QtCore.Qt.WindowCloseButtonHint
        )
        
        # Setup auto-update timer with a reasonable interval
        self.update_timer = QtCore.QTimer(self)
        self.update_timer.setSingleShot(True)  # Only trigger once per timeout
        self.update_timer.timeout.connect(self._on_update_timeout)
        
        # Use a separate timer for less frequent checks
        self.background_timer = QtCore.QTimer(self)
        self.background_timer.timeout.connect(self.check_for_updates)
        self.background_timer.start(2000)  # Check for updates every 2 seconds
        
        # Load analysis-specific cache if available
        self.load_analysis_cache()
        
        # Setup UI with optimizations
        self.setup_ui()
        
        # Initial update
        self.schedule_update()
        
        # Store instance reference
        if self.analysis_doc:
            _cache_viewer_instances[self.analysis_doc.Name] = self
    
    def _initialize_cache_items(self):
        """Initialize cache items with required fields."""
        for item in self.keyword_cache:
            if isinstance(item, dict):
                if 'active' not in item:
                    item['active'] = True
                if 'document_id' not in item and self.analysis_doc:
                    item['document_id'] = self.analysis_doc.Name

    def schedule_update(self, force=False):
        """Schedule an update with rate limiting."""
        current_time = QtCore.QTime.currentTime().msecsSinceStartOfDay()
        
        # If an update is already in progress, mark it as pending
        if self._is_updating:
            self._update_pending = True
            return
            
        # Check rate limiting
        time_since_last = current_time - self._last_update_time
        if not force and time_since_last < self.MIN_UPDATE_INTERVAL:
            # Schedule update for later
            if not self.update_timer.isActive():
                time_until_next = self.MIN_UPDATE_INTERVAL - time_since_last
                self.update_timer.start(time_until_next)
            self._update_pending = True
            return
            
        # Perform the update
        self._do_update()
    
    def _on_update_timeout(self):
        """Handle update timer timeout."""
        if self._update_pending:
            self._do_update()
    
    def _do_update(self):
        """Perform the actual update."""
        if self._is_updating:
            return
            
        self._is_updating = True
        self._update_pending = False
        self._last_update_time = QtCore.QTime.currentTime().msecsSinceStartOfDay()
        
        try:
            self.update_display()
        except Exception as e:
            print(f"Error during update: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._is_updating = False
            
            # If another update was requested while we were updating, do it now
            if self._update_pending:
                self._update_pending = False
                self.schedule_update()
                
    def load_analysis_cache(self):
        """Load analysis-specific cache if available."""
        if not self.analysis_doc:
            return
            
        cache_file = os.path.join(
            os.path.dirname(CACHE_FILE),
            f"{self.analysis_doc.Name}_cache.json"
        )
        
        if not os.path.exists(cache_file):
            return
            
        try:
            with open(cache_file, 'r') as f:
                doc_cache = json.load(f)
                
            if not isinstance(doc_cache, list):
                return
                
            # Update existing items or add new ones
            existing_names = {item.get('name') for item in self.keyword_cache if 'name' in item}
            
            for item in doc_cache:
                if not isinstance(item, dict):
                    continue
                    
                item_name = item.get('name')
                if item_name and item_name in existing_names:
                    # Update existing item
                    for i, existing in enumerate(self.keyword_cache):
                        if existing.get('name') == item_name:
                            self.keyword_cache[i].update(item)
                            break
                else:
                    # Add new item
                    self.keyword_cache.append(item)
                    
            self.schedule_update()
            
        except Exception as e:
            print(f"Error loading analysis cache: {e}")
            import traceback
            traceback.print_exc()

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Save any pending changes to analysis cache
            self.save_analysis_cache()
            
            # Save the main cache to disk
            if hasattr(self, 'keyword_cache') and self.keyword_cache:
                try:
                    # Ensure cache directory exists
                    if not os.path.exists(CACHE_DIR):
                        os.makedirs(CACHE_DIR, exist_ok=True)
                    
                    # Save the main cache
                    save_cache_to_disk(self.keyword_cache)
                    print(f"Saved {len(self.keyword_cache)} keywords to main cache at {CACHE_FILE}")
                    
                    # If we have an analysis document, also save a document-specific cache
                    if self.analysis_doc:
                        doc_cache = [
                            item for item in self.keyword_cache 
                            if isinstance(item, dict) and 
                            item.get('document_id') == self.analysis_doc.Name
                        ]
                        
                        if doc_cache:
                            cache_file = os.path.join(
                                CACHE_DIR,
                                f"{self.analysis_doc.Name}_cache.json"
                            )
                            with open(cache_file, 'w') as f:
                                json.dump(doc_cache, f, indent=2)
                            print(f"Saved {len(doc_cache)} keywords to document cache at {cache_file}")
                except Exception as e:
                    print(f"Error saving cache on close: {e}")
            
            # Stop timers
            self.update_timer.stop()
            self.background_timer.stop()
            
            # Clear the table
            if hasattr(self, 'cache_table'):
                self.cache_table.clearContents()
                self.cache_table.setRowCount(0)
            
            # Remove from instances dictionary
            if self.analysis_doc and self.analysis_doc.Name in _cache_viewer_instances:
                del _cache_viewer_instances[self.analysis_doc.Name]
            
            # Accept the close event
            event.accept()
            
        except Exception as e:
            print(f"Error in closeEvent: {e}")
            # Still allow the window to close
            event.accept()

    def setup_ui(self):
        """Set up the user interface with proper layout and controls."""
        try:
            print("CacheViewerWindow: Setting up UI...")
            
            # Set up the main layout
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(8)

            # Create a frame for the title bar
            title_bar = QtWidgets.QFrame()
            title_bar.setFrameShape(QtWidgets.QFrame.StyledPanel)
            title_bar.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                              stop:0 #f0f0f0, stop:1 #e0e0e0);
                    border: 1px solid #aaa;
                    border-radius: 4px;
                    padding: 2px;
                }
            """)
            
            # Title bar layout
            title_layout = QtWidgets.QHBoxLayout(title_bar)
            title_layout.setContentsMargins(8, 4, 8, 4)
            
            # Title label
            title_label = QtWidgets.QLabel("LS-DYNA Keyword Cache")
            title_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 12px;
                    color: #333;
                }
            """)
            
            # Close button
            close_btn = QtWidgets.QPushButton("✕")
            close_btn.setFixedSize(24, 24)
            close_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    font-weight: bold;
                    font-size: 14px;
                    background: transparent;
                    padding: 0;
                    margin: 0;
                }
                QPushButton:hover {
                    color: #f00;
                    background: rgba(255, 0, 0, 20);
                    border-radius: 12px;
                }
            """)
            close_btn.clicked.connect(self.close)
            
            # Add widgets to title bar
            title_layout.addWidget(title_label)
            title_layout.addStretch()
            title_layout.addWidget(close_btn)
            
            # Create a horizontal line
            line = QtWidgets.QFrame()
            line.setFrameShape(QtWidgets.QFrame.HLine)
            line.setFrameShadow(QtWidgets.QFrame.Sunken)
            line.setStyleSheet("color: #ccc;")
            
            # Info label
            self.info_label = QtWidgets.QLabel("No keywords in cache")
            self.info_label.setStyleSheet("""
                QLabel {
                    color: #666;
                    font-size: 11px;
                    padding: 2px 4px;
                    background: #f8f8f8;
                    border: 1px solid #e0e0e0;
                    border-radius: 3px;
                }
            """)
            
            # Create table widget for the cache list
            self.cache_table = QtWidgets.QTableWidget()
            self.cache_table.setColumnCount(3)  # Active, Name, Timestamp
            self.cache_table.setHorizontalHeaderLabels(['', 'Keyword', 'Last Modified'])
            self.cache_table.horizontalHeader().setStretchLastSection(True)
            self.cache_table.verticalHeader().setVisible(False)
            self.cache_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.cache_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            self.cache_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.cache_table.setAlternatingRowColors(True)
            
            # Set column properties
            self.cache_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # Active
            self.cache_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # Keyword
            self.cache_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)  # Timestamp
            
            # Connect signals
            self.cache_table.cellChanged.connect(self.on_cell_changed)
            self.cache_table.cellDoubleClicked.connect(self.on_item_double_clicked)
            
            # Buttons layout
            btn_layout = QtWidgets.QHBoxLayout()
            btn_layout.setSpacing(6)
            
            # Action buttons on the left
            left_btn_layout = QtWidgets.QHBoxLayout()
            
            self.refresh_btn = QtWidgets.QPushButton("🔄 Refresh")
            self.refresh_btn.setToolTip("Reload the cache")
            self.refresh_btn.clicked.connect(self.update_display)
            
            self.clear_btn = QtWidgets.QPushButton("🗑 Clear All")
            self.clear_btn.setToolTip("Clear all keywords from cache")
            self.clear_btn.clicked.connect(self.clear_all)
            
            left_btn_layout.addWidget(self.refresh_btn)
            left_btn_layout.addWidget(self.clear_btn)
            
            # Action buttons on the right
            right_btn_layout = QtWidgets.QHBoxLayout()
            
            self.generate_btn = QtWidgets.QPushButton("💾 Generate .k File")
            self.generate_btn.setToolTip("Generate LS-DYNA input file from selected keywords")
            self.generate_btn.clicked.connect(self.generate_k_file)
            
            self.close_btn = QtWidgets.QPushButton("✕ Close")
            self.close_btn.setToolTip("Close the cache viewer")
            self.close_btn.clicked.connect(self.close)
            
            right_btn_layout.addWidget(self.generate_btn)
            right_btn_layout.addWidget(self.close_btn)
            
            # Add button layouts to main button layout
            btn_layout.addLayout(left_btn_layout)
            btn_layout.addStretch()
            btn_layout.addLayout(right_btn_layout)
            
            # Add widgets to main layout
            layout.addWidget(title_bar)
            layout.addWidget(line)
            layout.addWidget(self.info_label)
            layout.addWidget(self.cache_table, 1)  # Add stretch factor to make table expand
            layout.addLayout(btn_layout)
            
            # Set window properties
            self.setWindowFlags(
                QtCore.Qt.Window |
                QtCore.Qt.WindowTitleHint |
                QtCore.Qt.WindowCloseButtonHint |
                QtCore.Qt.WindowStaysOnTopHint
            )
            
            # Set window title and icon
            self.setWindowTitle("LS-DYNA Keyword Cache")
            
            # Set minimum size
            self.setMinimumSize(700, 400)
            
            # Center the window on the screen
            self.center_on_screen()
            
            # Update the info label
            self.update_info_label()
            
        except Exception as e:
            print(f"Error setting up UI: {e}")
            import traceback
            traceback.print_exc()
    
    def center_on_screen(self):
        """Center the window on the screen."""
        try:
            # Get the primary screen
            screen = QtWidgets.QApplication.primaryScreen()
            if not screen:
                # Fallback to the first available screen
                screens = QtWidgets.QApplication.screens()
                if screens:
                    screen = screens[0]
                else:
                    # If no screens found, just return
                    return
            
            # Get the screen geometry
            screen_geometry = screen.availableGeometry()
            
            # Calculate center point
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            
            # Move the window to the center
            self.move(screen_geometry.left() + x, screen_geometry.top() + y)
            
        except Exception as e:
            print(f"Error centering window: {e}")
            # Fallback to default position
            self.move(100, 100)

    def closeEvent(self, event):
        """Handle window close event."""
        try:
            # Stop the update timer
            self.update_timer.stop()
            
            # Save the current cache state
            self.save_cache()
            
            # Save window position and size
            settings = QtCore.QSettings("FreeCAD", "FEM_CacheViewer")
            settings.setValue("geometry", self.saveGeometry())
                
            # Store the current cache version if it exists
            if hasattr(self, '_last_cache_version'):
                settings.setValue("cache_version", self._last_cache_version)
                
        except Exception as e:
            print(f"Error during close event: {e}")
            import traceback
            traceback.print_exc()
            
        # Don't actually close, just hide
        event.ignore()
        self.hide()

    def on_cell_changed(self, row, column):
        """Handle cell changes in the cache table."""
        if column == 0:  # Active checkbox column
            if row < 0 or row >= len(self.keyword_cache):
                return
                
            item = self.cache_table.item(row, column)
            if item:
                self.keyword_cache[row]['active'] = (item.checkState() == QtCore.Qt.Checked)
                self.save_cache()

    def on_item_double_clicked(self, row, column):
        """Handle double-click on a table item."""
        if row < 0 or row >= len(self.keyword_cache):
            return
            
        item = self.cache_table.item(row, 1)  # Get the name item
        if item:
            self.show_keyword_details(item)

    def check_for_updates(self):
        """Check for updates to the cache."""
        if self.cache_source == 'editor' and self.parent_editor and hasattr(self.parent_editor, 'keyword_cache'):
            if self.keyword_cache != self.parent_editor.keyword_cache:
                self.keyword_cache = self.parent_editor.keyword_cache
                self.update_display()
        elif self.cache_source == 'disk':
            disk_cache = load_cache_from_disk()
            if disk_cache != self.keyword_cache:
                self.keyword_cache = disk_cache
                self.update_display()

    def save_cache(self):
        """Save the current cache state."""
        if self.cache_source == 'editor' and self.parent_editor and hasattr(self.parent_editor, 'keyword_cache'):
            self.parent_editor.keyword_cache = self.keyword_cache
        elif self.cache_source == 'disk':
            save_cache_to_disk(self.keyword_cache)

    def update_info_label(self):
        """Update the information label with cache status."""
        active_count = sum(1 for item in self.keyword_cache if isinstance(item, dict) and item.get('active', True))
        total_count = len(self.keyword_cache)
        self.info_label.setText(f"Showing {active_count} of {total_count} keywords")

    def remove_selected(self):
        """Remove the selected cached keyword."""
        current_row = self.cache_table.currentRow()
        if current_row < 0 or current_row >= len(self.keyword_cache):
            QtWidgets.QMessageBox.warning(self, "No Selection",
                                        "Please select a valid keyword to remove.")
            return

        # Get the keyword name for the confirmation message
        keyword_name = self.keyword_cache[current_row].get('name', 'selected keyword')
        
        reply = QtWidgets.QMessageBox.question(
            self, 
            "Remove Keyword",
            f"Are you sure you want to remove '{keyword_name}' from the cache?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No  # Default to No for safety
        )

        if reply == QtWidgets.QMessageBox.Yes:
            # Remove from cache
            if 0 <= current_row < len(self.keyword_cache):
                removed_entry = self.keyword_cache.pop(current_row)
                self.save_cache()
                self.update_display()

    def clear_all(self):
        """Clear all cached keywords."""
        if not self.keyword_cache:
            return
            
        reply = QtWidgets.QMessageBox.question(
            self,
            "Clear All Keywords",
            "Are you sure you want to clear all cached keywords?\nThis action cannot be undone.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            self.keyword_cache = []
            self.update_display()
            self.save_cache()
            
    def generate_k_file(self):
        """Generate .k file from current cache."""
        if not self.keyword_cache:
            QtWidgets.QMessageBox.information(
                self, 
                "Empty Cache", 
                "The cache is empty. Nothing to generate.\nNo keywords in cache to generate .k file."
            )
            return

        # Use the parent editor's method to generate the file
        if self.parent_editor and hasattr(self.parent_editor, 'update_k_file'):
            self.parent_editor.update_k_file()

    def update_display(self):
        """Update the display with the current cache contents."""
        try:
            print("\n=== Updating cache display ===")
            print(f"Cache items: {len(self.keyword_cache)}")
            
            # Block signals to prevent cell change events during update
            self.cache_table.blockSignals(True)
            
            # Clear existing items
            self.cache_table.setRowCount(0)
            
            if not self.keyword_cache:
                print("No items in cache to display")
                return
                
            # Add items from cache
            for row, item in enumerate(self.keyword_cache):
                if not isinstance(item, dict):
                    print(f"Skipping non-dict item: {item}")
                    continue
                    
                print(f"Processing item {row}: {item}")
                
                # Get keyword name - handle different possible keys
                keyword_name = item.get('name') or item.get('keyword')
                if not keyword_name:
                    # If no name found, try to get the first value that looks like a name
                    for key, value in item.items():
                        if key not in ['active', 'timestamp', 'document_id'] and isinstance(value, str):
                            keyword_name = value
                            break
                    if not keyword_name:
                        keyword_name = f"Unnamed_{row}"
                
                # Add a new row
                self.cache_table.insertRow(row)
                
                # Active checkbox
                active_item = QtWidgets.QTableWidgetItem()
                active_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                active_item.setCheckState(
                    QtCore.Qt.Checked if item.get('active', True) else QtCore.Qt.Unchecked
                )
                self.cache_table.setItem(row, 0, active_item)
                
                # Keyword name
                name_item = QtWidgets.QTableWidgetItem(str(keyword_name))
                name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
                name_item.setData(QtCore.Qt.UserRole, item)  # Store full item data
                self.cache_table.setItem(row, 1, name_item)
                
                # Timestamp or additional info
                timestamp = item.get('timestamp', '')
                if not timestamp and 'time' in item:
                    timestamp = item['time']
                
                display_time = 'N/A'
                if timestamp:
                    try:
                        if isinstance(timestamp, str):
                            # Try parsing ISO format first
                            dt = QtCore.QDateTime.fromString(timestamp, QtCore.Qt.ISODate)
                            if not dt.isValid():
                                # Try other common formats if ISO fails
                                formats = [
                                    QtCore.Qt.ISODate,
                                    QtCore.Qt.TextDate,
                                    QtCore.Qt.ISODateWithMs,
                                    'yyyy-MM-dd HH:mm:ss.zzz',
                                    'yyyy-MM-dd HH:mm:ss',
                                    'MM/dd/yyyy HH:mm:ss',
                                    'dd.MM.yyyy HH:mm:ss'
                                ]
                                
                                for fmt in formats:
                                    dt = QtCore.QDateTime.fromString(timestamp, fmt)
                                    if dt.isValid():
                                        break
                            
                            if dt.isValid():
                                display_time = dt.toString('yyyy-MM-dd HH:mm:ss')
                            else:
                                display_time = str(timestamp)
                        elif isinstance(timestamp, (int, float)):
                            # Handle Unix timestamps
                            dt = QtCore.QDateTime.fromSecsSinceEpoch(int(timestamp))
                            if dt.isValid():
                                display_time = dt.toString('yyyy-MM-dd HH:mm:ss')
                            else:
                                display_time = str(timestamp)
                        else:
                            display_time = str(timestamp)
                    except Exception as e:
                        print(f"Error formatting timestamp {timestamp}: {e}")
                        display_time = str(timestamp)
                
                time_item = QtWidgets.QTableWidgetItem(display_time)
                time_item.setFlags(time_item.flags() & ~QtCore.Qt.ItemIsEditable)
                self.cache_table.setItem(row, 2, time_item)
                
                print(f"  Added row {row}: {keyword_name}")
                
            print(f"Display updated with {self.cache_table.rowCount()} rows")
            print("=== End of update ===\n")
            
            # Update the info label
            self.update_info_label()
            
        except Exception as e:
            print(f"Error updating display: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Re-enable signals
            self.cache_table.blockSignals(False)
    
    def IsActive(self):
        """Define whether the command is active or not (greyed out)."""
        # Always active as we can open the cache viewer anytime
        return True
