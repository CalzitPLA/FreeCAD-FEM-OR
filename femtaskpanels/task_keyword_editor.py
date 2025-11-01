import os
import json
from PySide import QtGui, QtCore
from PySide.QtCore import Qt

class KeywordEditorPanel(QtGui.QWidget):
    """Panel for editing LS-DYNA/OpenRadioss keywords with live configuration."""
    
    def __init__(self):
        super().__init__()
        self.keywords = []
        self.current_keyword = None
        self.keyword_widgets = []
        
        self.setup_ui()
        self.load_keywords()
        
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("LS-DYNA/OpenRadioss Keyword Editor")
        self.setMinimumSize(1000, 700)
        
        # Main layout
        main_layout = QtGui.QHBoxLayout()
        
        # Left panel - Keyword list
        left_panel = QtGui.QWidget()
        left_layout = QtGui.QVBoxLayout()
        
        # Search box
        self.search_box = QtGui.QLineEdit()
        self.search_box.setPlaceholderText("Search keywords...")
        self.search_box.textChanged.connect(self.filter_keywords)
        left_layout.addWidget(self.search_box)
        
        # Category filter
        self.category_combo = QtGui.QComboBox()
        self.category_combo.addItem("All Categories")
        self.category_combo.currentIndexChanged.connect(self.filter_keywords)
        left_layout.addWidget(self.category_combo)
        
        # Keyword list
        self.keyword_list = QtGui.QListWidget()
        self.keyword_list.itemClicked.connect(self.on_keyword_selected)
        left_layout.addWidget(self.keyword_list)
        
        left_panel.setLayout(left_layout)
        
        # Right panel - Keyword editor
        right_panel = QtGui.QWidget()
        right_layout = QtGui.QVBoxLayout()
        
        # Keyword header
        self.keyword_header = QtGui.QLabel("Select a keyword to edit")
        self.keyword_header.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(self.keyword_header)
        
        # Documentation link
        self.doc_link = QtGui.QLabel()
        self.doc_link.setOpenExternalLinks(True)
        right_layout.addWidget(self.doc_link)
        
        # Description
        self.description_label = QtGui.QLabel()
        self.description_label.setWordWrap(True)
        right_layout.addWidget(self.description_label)
        
        # Scroll area for parameters
        scroll = QtGui.QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Container widget for parameters
        self.param_container = QtGui.QWidget()
        self.param_layout = QtGui.QFormLayout()
        self.param_container.setLayout(self.param_layout)
        
        scroll.setWidget(self.param_container)
        right_layout.addWidget(scroll)
        
        # Buttons
        button_layout = QtGui.QHBoxLayout()
        self.apply_button = QtGui.QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_changes)
        self.cancel_button = QtGui.QPushButton("Close")
        self.cancel_button.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        right_layout.addLayout(button_layout)
        
        right_panel.setLayout(right_layout)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)
        
        self.setLayout(main_layout)
    
    def load_keywords(self):
        """Load and filter keywords that exist in both CFD config and JSON files."""
        try:
            # Load keywords from the clean file
            keywords_path = os.path.join(
                os.path.dirname(__file__), 
                "..", "gui", "json", "keywords_clean.json"
            )
            with open(keywords_path, 'r') as f:
                all_keywords = json.load(f)
            
            # Load syntax configurations
            syntax_path = os.path.join(
                os.path.dirname(__file__), 
                "..", "gui", "json", "ls_dyna_syntax_user_friendly.json"
            )
            with open(syntax_path, 'r') as f:
                self.syntax_data = json.load(f)
            
            # Get list of valid CFD keywords from syntax data
            valid_cfd_keywords = set()
            if 'ls_dyna_syntax' in self.syntax_data and 'examples' in self.syntax_data['ls_dyna_syntax']:
                for example_name, example_data in self.syntax_data['ls_dyna_syntax']['examples'].items():
                    if 'keyword' in example_data:
                        valid_cfd_keywords.add(example_data['keyword'])
            
            # Filter keywords to only include those in both sources
            self.keywords = []
            for kw in all_keywords:
                kw_name = kw.get('name', '')
                # Check if keyword exists in CFD configuration
                if kw_name in valid_cfd_keywords:
                    # Also verify it has a valid configuration
                    if self.get_keyword_config(kw_name) is not None:
                        self.keywords.append(kw)
            
            # Update UI with filtered keywords
            self.update_keyword_list()
            
            # Extract and set categories from filtered keywords
            categories = set()
            for kw in self.keywords:
                if 'category' in kw:
                    categories.add(kw['category'])
            
            # Clear existing items and add new ones
            self.category_combo.clear()
            self.category_combo.addItem("All Categories")
            self.category_combo.addItems(sorted(categories))
            
        except Exception as e:
            QtGui.QMessageBox.critical(self, "Error", f"Failed to load keyword data: {str(e)}")
    
    def update_keyword_list(self, filter_text="", category=""):
        """Update the keyword list based on filter and category."""
        self.keyword_list.clear()
        
        for kw in self.keywords:
            name = kw.get('name', '')
            kw_category = kw.get('category', '')
            
            # Apply filters
            if filter_text.lower() not in name.lower():
                continue
                
            if category and category != "All Categories" and kw_category != category:
                continue
            
            item = QtGui.QListWidgetItem(name)
            item.setData(Qt.UserRole, kw)
            self.keyword_list.addItem(item)
    
    def filter_keywords(self):
        """Filter keywords based on search text and category."""
        filter_text = self.search_box.text()
        category = self.category_combo.currentText()
        self.update_keyword_list(filter_text, category)
    
    def on_keyword_selected(self, item):
        """Handle selection of a keyword from the list."""
        kw = item.data(Qt.UserRole)
        self.current_keyword = kw
        
        # Update header and documentation
        self.keyword_header.setText(kw.get('name', 'Unknown Keyword'))
        
        # Set documentation link if available
        doc_url = kw.get('documentation', '')
        if doc_url:
            self.doc_link.setText(f'<a href="{doc_url}">Documentation</a>')
        else:
            self.doc_link.setText('No documentation available')
        
        # Set description
        self.description_label.setText(kw.get('description', 'No description available.'))
        
        # Clear previous parameter widgets
        self.clear_parameter_widgets()
        
        # Load and display parameters
        self.load_keyword_parameters(kw)
    
    def clear_parameter_widgets(self):
        """Remove all parameter widgets from the layout."""
        for i in reversed(range(self.param_layout.count())):
            item = self.param_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Handle nested layouts if any
                for j in reversed(range(item.layout().count())):
                    widget = item.layout().itemAt(j).widget()
                    if widget:
                        widget.deleteLater()
                item.layout().deleteLater()
        
        # Clear the layout
        while self.param_layout.rowCount() > 0:
            self.param_layout.removeRow(0)
        
        self.keyword_widgets = []
    
    def get_keyword_config(self, keyword_name):
        """Get the configuration for a specific keyword from the syntax data."""
        if not hasattr(self, 'syntax_data') or 'ls_dyna_syntax' not in self.syntax_data:
            return None
            
        # Try exact match first
        for example_name, example_data in self.syntax_data['ls_dyna_syntax'].get('examples', {}).items():
            if 'keyword' in example_data and example_data['keyword'] == keyword_name:
                return example_data
        
        # Try partial match for base names (e.g., MAT_001)
        if '_' in keyword_name:
            base_name = keyword_name.split('_')[0] + '_'
            for example_name, example_data in self.syntax_data['ls_dyna_syntax'].get('examples', {}).items():
                if 'keyword' in example_data and example_data['keyword'].startswith(base_name):
                    return example_data
        
        return None

    def load_keyword_parameters(self, keyword):
        """Load and display parameters for the selected keyword."""
        keyword_name = keyword.get('name', '')
        
        # Get the configuration for this keyword
        syntax_config = self.get_keyword_config(keyword_name)
        
        if not syntax_config:
            QtGui.QMessageBox.warning(self, "Configuration Not Found", 
                                   f"No configuration found for keyword: {keyword_name}")
            return
        
        if syntax_config:
            # Add parameters from the syntax configuration
            if 'parameters' in syntax_config:
                for param_name, param_data in syntax_config['parameters'].items():
                    self.add_parameter_widget(param_name, param_data)
        else:
            # Fallback: Add a message if no configuration found
            label = QtGui.QLabel("No configuration available for this keyword.")
            self.param_layout.addRow(label)
    
    def add_parameter_widget(self, name, param_data):
        """Add a widget for a parameter."""
        param_type = param_data.get('type', 'text')
        default = param_data.get('default', '')
        description = param_data.get('description', '')
        
        # Create label with description as tooltip
        label = QtGui.QLabel(name)
        if description:
            label.setToolTip(description)
        
        # Create appropriate input widget based on parameter type
        if param_type == 'boolean':
            widget = QtGui.QCheckBox()
            widget.setChecked(bool(default))
        elif 'options' in param_data:
            # Dropdown for options
            widget = QtGui.QComboBox()
            for option in param_data['options']:
                widget.addItem(str(option), option)
            
            # Set default value if it exists in options
            if default is not None and str(default) in [widget.itemText(i) for i in range(widget.count())]:
                widget.setCurrentText(str(default))
        else:
            # Default to line edit
            widget = QtGui.QLineEdit(str(default) if default is not None else '')
        
        # Store widget reference
        self.keyword_widgets.append((name, widget, param_data))
        
        # Add to layout
        self.param_layout.addRow(label, widget)
    
    def apply_changes(self):
        """Apply the changes made in the editor."""
        if not self.current_keyword:
            return
        
        # Collect parameter values
        params = {}
        for name, widget, param_data in self.keyword_widgets:
            if isinstance(widget, QtGui.QCheckBox):
                params[name] = widget.isChecked()
            elif isinstance(widget, QtGui.QComboBox):
                params[name] = widget.currentData()
            else:
                params[name] = widget.text()
        
        # Here you would typically save the changes or apply them to your model
        print(f"Applied changes to {self.current_keyword['name']}:", params)
        
        # Show success message
        QtGui.QMessageBox.information(self, "Success", f"Updated {self.current_keyword['name']} with new parameters.")
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Add any cleanup code here if needed
        event.accept()


def show_keyword_editor():
    """Show the keyword editor dialog."""
    dialog = KeywordEditorPanel()
    dialog.show()
    return dialog
