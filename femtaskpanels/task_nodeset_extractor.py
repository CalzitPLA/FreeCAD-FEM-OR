# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Nodeset Extractor Task Panel

Task panel for extracting nodesets from FEM constraints.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets


from femutils.nodeset_extractor import process_analysis


class _TaskPanel:
    """Task panel for the nodeset extractor"""
    
    def __init__(self):
        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle("Nodeset Extractor")
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface"""
        layout = QtWidgets.QVBoxLayout(self.form)
        
        # Add extract button
        self.extract_btn = QtWidgets.QPushButton("Extract Nodesets")
        self.extract_btn.clicked.connect(self.extract_nodesets)
        layout.addWidget(self.extract_btn)
        
        # Add results area
        self.result_text = QtWidgets.QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        
        # Add stretch to push content to the top
        layout.addStretch()
        
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
    
    def accept(self):
        """Called when the task panel is accepted"""
        Gui.Control.closeDialog()
        return True
        
    def reject(self):
        """Called when the task panel is rejected"""
        Gui.Control.closeDialog()
        return True
    
    def getStandardButtons(self):
        """Define standard buttons for the task panel"""
        return int(QtGui.QDialogButtonBox.Close)
    
    def clicked(self, button):
        """Handle button clicks"""
        if button == QtGui.QDialogButtonBox.Close:
            Gui.Control.closeDialog()
            return True
        return False
