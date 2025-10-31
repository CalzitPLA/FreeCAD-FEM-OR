# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Nodeset Extractor Panel for FreeCAD

Provides a dockable panel for the nodeset extractor functionality.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets
from .extract_nodesets import process_analysis

class NodesetExtractorPanel(QtWidgets.QDockWidget):
    """Dockable panel for the nodeset extractor"""
    
    def __init__(self, parent=None):
        super(NodesetExtractorPanel, self).__init__("Nodeset Extractor", parent)
        self.setObjectName("NodesetExtractorPanel")
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetClosable | 
                        QtWidgets.QDockWidget.DockWidgetMovable |
                        QtWidgets.QDockWidget.DockWidgetFloatable)
        self.setMinimumWidth(300)
        self.initUI()
        
    def initUI(self):
        # Create main widget
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        
        # Add extract button
        self.extract_btn = QtWidgets.QPushButton("Extract Nodesets")
        self.extract_btn.clicked.connect(self.extract_nodesets)
        layout.addWidget(self.extract_btn)
        
        # Add results area
        self.result_text = QtWidgets.QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        
        self.setWidget(widget)
        
    def extract_nodesets(self):
        """Extract nodesets from the active analysis"""
        try:
            import FemGui
            analysis = FemGui.getActiveAnalysis()
            if analysis:
                result = process_analysis(analysis, create_text_object=True)
                self.result_text.setText(result)
                App.Console.PrintMessage("Nodesets extracted successfully!\n")
            else:
                self.result_text.setText("No active FEM analysis found")
                App.Console.PrintError("No active FEM analysis found\n")
        except Exception as e:
            error_msg = f"Error extracting nodesets: {str(e)}"
            self.result_text.setText(error_msg)
            App.Console.PrintError(f"{error_msg}\n")
            
    def closeEvent(self, event):
        """Handle close event to uncheck the toggle button"""
        mw = Gui.getMainWindow()
        if mw:
            toolbar = mw.findChild(QtWidgets.QToolBar, "FEM_ToggleTools")
            if toolbar:
                for action in toolbar.actions():
                    if action.text() == "Toggle Nodeset Extractor":
                        action.setChecked(False)
                        break
        super(NodesetExtractorPanel, self).closeEvent(event)
