# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Nodeset Extractor GUI

Provides the command and task panel for the nodeset extractor functionality.
"""

import os
import time
import FreeCAD as App
import FreeCADGui as Gui
from PySide6 import QtCore, QtGui, QtWidgets
from femutils.nodeset_extractor.writer import extract_nodesets


class ProgressDialog(QtWidgets.QProgressDialog):
    """Progress dialog for the nodeset extraction process"""
    
    def __init__(self, parent=None):
        super().__init__("Extracting nodesets...", "Cancel", 0, 100, parent)
        self.setWindowTitle("Nodeset Extractor")
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setMinimumDuration(500)  # Show after 500ms if not finished
        self.setAutoReset(False)
        self.setAutoClose(True)
        self.setValue(0)
        
    def update_progress(self, current, total, message):
        """Update the progress dialog"""
        if total > 0:
            progress = int((current / total) * 100)
            self.setValue(min(progress, 100))
        self.setLabelText(message)
        QtWidgets.QApplication.processEvents()
        
        # Check if user clicked cancel
        return not self.wasCanceled()


class NodesetExtractorTaskPanel:
    """Task panel for the nodeset extractor"""
    
    def __init__(self):
        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle("Nodeset Extractor")
        self.progress_dialog = None
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface"""
        layout = QtWidgets.QVBoxLayout(self.form)
        
        # Add options group
        options_group = QtWidgets.QGroupBox("Options")
        options_layout = QtWidgets.QVBoxLayout()
        
        # Add create text object checkbox
        self.create_text_cb = QtWidgets.QCheckBox("Create text object in document")
        self.create_text_cb.setChecked(True)
        options_layout.addWidget(self.create_text_cb)
        
        # Add tolerance spinbox
        tol_layout = QtWidgets.QHBoxLayout()
        tol_layout.addWidget(QtWidgets.QLabel("Tolerance:"))
        self.tolerance_sb = QtWidgets.QDoubleSpinBox()
        self.tolerance_sb.setRange(1e-9, 1.0)
        self.tolerance_sb.setValue(1e-6)
        self.tolerance_sb.setSingleStep(1e-6)
        self.tolerance_sb.setDecimals(9)
        self.tolerance_sb.setSuffix(" mm")
        tol_layout.addWidget(self.tolerance_sb)
        options_layout.addLayout(tol_layout)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Add extract button
        self.extract_btn = QtWidgets.QPushButton("Extract Nodesets")
        self.extract_btn.clicked.connect(self.extract_nodesets)
        layout.addWidget(self.extract_btn)
        
        # Add results area
        results_group = QtWidgets.QGroupBox("Results")
        results_layout = QtWidgets.QVBoxLayout()
        
        self.result_text = QtWidgets.QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(200)
        results_layout.addWidget(self.result_text)
        
        # Add export button
        self.export_btn = QtWidgets.QPushButton("Export to File...")
        self.export_btn.clicked.connect(self.export_nodesets)
        self.export_btn.setEnabled(False)
        results_layout.addWidget(self.export_btn)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Store the last export directory
        self.last_export_dir = None
    
    def log_message(self, message):
        """Add a message to the log"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.result_text.append(f"[{timestamp}] {message}")
        self.result_text.verticalScrollBar().setValue(
            self.result_text.verticalScrollBar().maximum())
        QtWidgets.QApplication.processEvents()
    
    def progress_callback(self, current, total, message):
        """Handle progress updates"""
        if self.progress_dialog:
            return self.progress_dialog.update_progress(current, total, message)
        return True
    
    def extract_nodesets(self):
        """Extract nodesets from the active analysis"""
        try:
            import FemGui
            
            # Reset UI state
            self.result_text.clear()
            self.export_btn.setEnabled(False)
            self.log_message("Starting nodeset extraction...")
            
            # Get the active analysis
            analysis = FemGui.getActiveAnalysis()
            if not analysis:
                self.log_message("Error: No active FEM analysis found")
                App.Console.PrintError("No active FEM analysis found\n")
                return
            
            # Create and show progress dialog
            self.progress_dialog = ProgressDialog(self.form)
            
            try:
                # Debug: Print analysis object info
                App.Console.PrintMessage(f"Analysis object: {analysis}\n")
                App.Console.PrintMessage(f"Analysis Group contents: {analysis.Group}\n")
                
                # Get the mesh object from analysis
                mesh_obj = None
                for obj in analysis.Group:
                    obj_type = getattr(obj, 'TypeId', 'N/A')
                    App.Console.PrintMessage(f"Checking object: {obj}, Type: {obj_type}\n")
                    
                    # Check for different possible mesh types
                    if hasattr(obj, 'TypeId') and (
                        obj_type == 'Fem::FemMeshObject' or 
                        obj_type == 'Fem::FEMMeshGmsh' or
                        obj_type == 'Fem::FemMeshGmsh'  # For backward compatibility
                    ):
                        mesh_obj = obj
                        App.Console.PrintMessage(f"Found mesh object ({obj_type}): {mesh_obj}\n")
                        break
                
                if not mesh_obj:
                    # Try alternative method to find mesh using isDerivedFrom
                    App.Console.PrintMessage("Trying alternative method to find mesh...\n")
                    for obj in analysis.Group:
                        if hasattr(obj, 'isDerivedFrom') and (
                            obj.isDerivedFrom('Fem::FemMeshObject') or
                            obj.isDerivedFrom('Fem::FEMMeshGmsh') or
                            obj.isDerivedFrom('Fem::FemMeshGmsh')
                        ):
                            mesh_obj = obj
                            App.Console.PrintMessage(f"Found mesh object (alternative method, TypeId: {getattr(obj, 'TypeId', 'N/A')}): {mesh_obj}\n")
                            break
                
                if not mesh_obj:
                    raise ValueError("No FEM mesh found in the analysis. Check if the analysis contains a mesh object.")
                
                # Extract nodesets
                result = extract_nodesets(
                    analysis,
                    mesh_obj,
                    create_text_object=self.create_text_cb.isChecked(),
                    progress_callback=self.progress_callback
                )
                
                # Display results
                self.result_text.clear()
                self.result_text.append(result)
                self.log_message("Nodesets extracted successfully")
                self.export_btn.setEnabled(True)
                
            except Exception as e:
                error_msg = f"Error extracting nodesets: {str(e)}"
                self.log_message(error_msg)
                App.Console.PrintError(f"{error_msg}\n")
                
            finally:
                self.progress_dialog.reset()
                self.progress_dialog = None
                
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.log_message(error_msg)
            App.Console.PrintError(f"{error_msg}\n")
    
    def export_nodesets(self):
        """Export the nodeset data to a file"""
        try:
            # Get the text to export
            text = self.result_text.toPlainText()
            if not text.strip():
                self.log_message("No nodeset data to export")
                return
            
            # Get save file name
            default_dir = self.last_export_dir or os.path.expanduser("~")
            default_file = os.path.join(default_dir, "nodesets.txt")
            
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.form,
                "Export Nodesets",
                default_file,
                "Text Files (*.txt);;All Files (*)"
            )
            
            if file_path:
                # Ensure the file has an extension
                if not file_path.lower().endswith('.txt'):
                    file_path += '.txt'
                
                # Save the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                # Update last export directory
                self.last_export_dir = os.path.dirname(file_path)
                
                self.log_message(f"Nodesets exported to: {file_path}")
                
        except Exception as e:
            error_msg = f"Error exporting nodesets: {str(e)}"
            self.log_message(error_msg)
            App.Console.PrintError(f"{error_msg}\n")


class NodesetExtractorCommand:
    """Command to show the nodeset extractor task panel"""
    
    def GetResources(self):
        return {
            'Pixmap': 'FEM_ConstraintFixed',
            'MenuText': 'Extract Nodesets',
            'ToolTip': 'Extract nodesets from FEM constraints',
            'Accel': 'N, S'
        }

    def IsActive(self):
        """Command is active when there's an active document"""
        return bool(App.ActiveDocument)

    def Activated(self):
        """Execute the command"""
        try:
            # Check if the panel is already open
            mw = Gui.getMainWindow()
            dock = mw.findChild(QtWidgets.QDockWidget, "NodesetExtractorPanel")
            
            if dock:
                # Toggle visibility if already open
                dock.setVisible(not dock.isVisible())
                if dock.isVisible():
                    dock.raise_()
            else:
                # Create a new dock widget
                panel = NodesetExtractorTaskPanel()
                dock = QtWidgets.QDockWidget("Nodeset Extractor", mw)
                dock.setObjectName("NodesetExtractorPanel")
                dock.setWidget(panel.form)
                mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
                
                # Add close event to clean up
                def on_close(event):
                    # Save window state
                    settings = QtCore.QSettings("FreeCAD", "FemUpgraded")
                    settings.setValue("NodesetExtractor/geometry", dock.saveGeometry())
                    # Only save state if the widget supports it
                    if hasattr(panel, 'saveState'):
                        settings.setValue("NodesetExtractor/state", panel.saveState())
                    event.accept()
                
                dock.closeEvent = on_close
                
                # Restore window state if available
                settings = QtCore.QSettings("FreeCAD", "FemUpgraded")
                if settings.contains("NodesetExtractor/geometry"):
                    dock.restoreGeometry(settings.value("NodesetExtractor/geometry"))
                if settings.contains("NodesetExtractor/state"):
                    dock.restoreState(settings.value("NodesetExtractor/state"))
            
        except Exception as e:
            App.Console.PrintError(f"Error showing nodeset extractor panel: {str(e)}\n")
