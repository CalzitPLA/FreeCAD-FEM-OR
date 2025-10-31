#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FreeCAD FEM Preferences Dialog Implementation

This module implements the preferences dialog for the FEM workbench,
handling UI events and connecting them to the settings system.
"""

import os
import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui

class FemSettingsDialog:
    """FEM Settings Dialog Implementation"""

    def __init__(self, parent=None):
        self.parent = parent
        self.dialog = None

    def show(self):
        """Show the FEM settings dialog"""
        # Load the UI file
        ui_path = os.path.join(
            FreeCAD.getResourceDir(),
            "Mod", "Fem", "Resources", "ui", "DlgSettingsFem.ui"
        )

        if not os.path.exists(ui_path):
            # Try alternative path for development
            ui_path = "/home/nemo/Dokumente/Sandbox/Fem_upgraded/Resources/ui/DlgSettingsFem.ui"

        if not os.path.exists(ui_path):
            FreeCAD.Console.PrintError(f"FEM settings UI file not found: {ui_path}\n")
            return

        # Load UI
        self.dialog = FreeCADGui.PySideUic.loadUi(ui_path)

        # Connect signals
        self.connect_signals()

        # Load current settings
        self.load_settings()

        # Show dialog
        self.dialog.show()

    def connect_signals(self):
        """Connect UI signals to handler methods"""
        if self.dialog:
            # OpenRadioss Engine browse button
            engine_browse = self.dialog.findChild(QtGui.QPushButton, "BrowseEngineBinary")
            if engine_browse:
                engine_browse.clicked.connect(self.browse_engine_binary)

            # OpenRadioss Starter browse button
            starter_browse = self.dialog.findChild(QtGui.QPushButton, "BrowseStarterBinary")
            if starter_browse:
                starter_browse.clicked.connect(self.browse_starter_binary)

            # OpenRadioss Anim-to-VTK browse button
            vtk_browse = self.dialog.findChild(QtGui.QPushButton, "BrowseAnimToVTKBinary")
            if vtk_browse:
                vtk_browse.clicked.connect(self.browse_anim_vtk_binary)

            # CalculiX CCX browse button
            ccx_browse = self.dialog.findChild(QtGui.QPushButton, "BrowseCcxBinary")
            if ccx_browse:
                ccx_browse.clicked.connect(self.browse_ccx_binary)

            # Elmer Solver browse button
            elmer_browse = self.dialog.findChild(QtGui.QPushButton, "BrowseElmerBinary")
            if elmer_browse:
                elmer_browse.clicked.connect(self.browse_elmer_binary)

            # Elmer Grid browse button
            grid_browse = self.dialog.findChild(QtGui.QPushButton, "BrowseGridBinary")
            if grid_browse:
                grid_browse.clicked.connect(self.browse_grid_binary)

    def load_settings(self):
        """Load current settings into UI elements"""
        if not self.dialog:
            return

        try:
            # Load OpenRadioss settings
            self.load_openradioss_settings()

            # Load CalculiX settings
            self.load_calculix_settings()

            # Load Elmer settings
            self.load_elmer_settings()

            # Load general settings
            self.load_general_settings()

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error loading FEM settings: {e}\n")

    def save_settings(self):
        """Save settings from UI elements"""
        if not self.dialog:
            return

        try:
            # Save OpenRadioss settings
            self.save_openradioss_settings()

            # Save CalculiX settings
            self.save_calculix_settings()

            # Save Elmer settings
            self.save_elmer_settings()

            # Save general settings
            self.save_general_settings()

            FreeCAD.Console.PrintMessage("FEM settings saved successfully\n")

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error saving FEM settings: {e}\n")

    def browse_engine_binary(self):
        """Browse for OpenRadioss engine binary"""
        current_path = self.get_ui_value("OpenRadiossEngineBinaryPath")
        new_path = self.file_dialog("Select OpenRadioss Engine", current_path, "Executables (*.exe *linux64_gf)")

        if new_path:
            self.set_ui_value("OpenRadiossEngineBinaryPath", new_path)
            # Uncheck standard location
            self.set_ui_checked("UseStandardOpenRadiossEngineLocation", False)

    def browse_starter_binary(self):
        """Browse for OpenRadioss starter binary"""
        current_path = self.get_ui_value("OpenRadiossStarterBinaryPath")
        new_path = self.file_dialog("Select OpenRadioss Starter", current_path, "Executables (*.exe *linux64_gf)")

        if new_path:
            self.set_ui_value("OpenRadiossStarterBinaryPath", new_path)
            # Uncheck standard location
            self.set_ui_checked("UseStandardOpenRadiossStarterLocation", False)

    def browse_anim_vtk_binary(self):
        """Browse for OpenRadioss Anim-to-VTK converter"""
        current_path = self.get_ui_value("OpenRadiossAnimToVTKBinaryPath")
        new_path = self.file_dialog("Select OpenRadioss Anim-to-VTK Converter", current_path, "Executables (*anim_to_vtk*)")

        if new_path:
            self.set_ui_value("OpenRadiossAnimToVTKBinaryPath", new_path)
            # Uncheck standard location
            self.set_ui_checked("UseStandardOpenRadiossAnimToVTKLocation", False)

    def browse_ccx_binary(self):
        """Browse for CalculiX CCX binary"""
        current_path = self.get_ui_value("CcxBinaryPath")
        new_path = self.file_dialog("Select CalculiX CCX", current_path, "Executables (*ccx*)")

        if new_path:
            self.set_ui_value("CcxBinaryPath", new_path)
            # Uncheck standard location
            self.set_ui_checked("UseStandardCcxLocation", False)

    def browse_elmer_binary(self):
        """Browse for ElmerSolver binary"""
        current_path = self.get_ui_value("ElmerBinaryPath")
        new_path = self.file_dialog("Select ElmerSolver", current_path, "Executables (*ElmerSolver*)")

        if new_path:
            self.set_ui_value("ElmerBinaryPath", new_path)
            # Uncheck standard location
            self.set_ui_checked("UseStandardElmerLocation", False)

    def browse_grid_binary(self):
        """Browse for ElmerGrid binary"""
        current_path = self.get_ui_value("GridBinaryPath")
        new_path = self.file_dialog("Select ElmerGrid", current_path, "Executables (*ElmerGrid*)")

        if new_path:
            self.set_ui_value("GridBinaryPath", new_path)
            # Uncheck standard location
            self.set_ui_checked("UseStandardGridLocation", False)

    def file_dialog(self, title, current_path, filter_str):
        """Show file selection dialog"""
        if not self.dialog:
            return None

        # Get the main window as parent
        main_window = FreeCADGui.getMainWindow()

        # Create file dialog
        dialog = QtGui.QFileDialog(main_window, title, os.path.dirname(current_path) if current_path else "")
        dialog.setFileMode(QtGui.QFileDialog.ExistingFile)
        dialog.setNameFilter(filter_str)

        if dialog.exec_():
            selected_files = dialog.selectedFiles()
            if selected_files:
                return selected_files[0]

        return None

    def get_ui_value(self, widget_name):
        """Get value from UI element"""
        if not self.dialog:
            return ""

        widget = self.dialog.findChild(QtGui.QLineEdit, widget_name)
        if widget:
            return widget.text()
        return ""

    def set_ui_value(self, widget_name, value):
        """Set value in UI element"""
        if not self.dialog:
            return

        widget = self.dialog.findChild(QtGui.QLineEdit, widget_name)
        if widget:
            widget.setText(value)

    def set_ui_checked(self, widget_name, checked):
        """Set checkbox state in UI element"""
        if not self.dialog:
            return

        widget = self.dialog.findChild(QtGui.QCheckBox, widget_name)
        if widget:
            widget.setChecked(checked)

    def get_ui_checked(self, widget_name):
        """Get checkbox state from UI element"""
        if not self.dialog:
            return False

        widget = self.dialog.findChild(QtGui.QCheckBox, widget_name)
        if widget:
            return widget.isChecked()
        return False

    def load_openradioss_settings(self):
        """Load OpenRadioss settings into UI"""
        from femsolver.settings import get_binary

        # Get current binary paths
        engine_path = get_binary("OpenRadioss") or "/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/exec/engine_linux64_gf"
        starter_path = get_binary("OpenRadiossStarter") or "/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/exec/starter_linux64_gf"
        vtk_path = get_binary("OpenRadiossAnimToVTK") or "/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/exec/anim_to_vtk"

        # Set UI values
        self.set_ui_value("OpenRadiossEngineBinaryPath", engine_path)
        self.set_ui_value("OpenRadiossStarterBinaryPath", starter_path)
        self.set_ui_value("OpenRadiossAnimToVTKBinaryPath", vtk_path)

    def save_openradioss_settings(self):
        """Save OpenRadioss settings from UI"""
        # Get values from UI
        engine_path = self.get_ui_value("OpenRadiossEngineBinaryPath")
        starter_path = self.get_ui_value("OpenRadiossStarterBinaryPath")
        vtk_path = self.get_ui_value("OpenRadiossAnimToVTKBinaryPath")

        # Save to FreeCAD parameters
        prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/OpenRadioss")

        if engine_path:
            prefs.SetString("openRadiossEngineBinaryPath", engine_path)
        if starter_path:
            prefs.SetString("openRadiossStarterBinaryPath", starter_path)
        if vtk_path:
            prefs.SetString("openRadiossAnimToVTKBinaryPath", vtk_path)

        # Set standard location flags
        prefs.SetBool("UseStandardOpenRadiossEngineLocation", self.get_ui_checked("UseStandardOpenRadiossEngineLocation"))
        prefs.SetBool("UseStandardOpenRadiossStarterLocation", self.get_ui_checked("UseStandardOpenRadiossStarterLocation"))
        prefs.SetBool("UseStandardOpenRadiossAnimToVTKLocation", self.get_ui_checked("UseStandardOpenRadiossAnimToVTKLocation"))

    def load_calculix_settings(self):
        """Load CalculiX settings into UI"""
        from femsolver.settings import get_binary

        # Get current binary path
        ccx_path = get_binary("Calculix") or "ccx"

        # Set UI values
        self.set_ui_value("CcxBinaryPath", ccx_path)

        # Load CPU settings
        prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/Ccx")
        cpu_count = prefs.GetInt("AnalysisNumCPUs", 1)

        cpu_spinbox = self.dialog.findChild(QtGui.QSpinBox, "AnalysisNumCPUs")
        if cpu_spinbox:
            cpu_spinbox.setValue(cpu_count)

    def save_calculix_settings(self):
        """Save CalculiX settings from UI"""
        # Get values from UI
        ccx_path = self.get_ui_value("CcxBinaryPath")
        cpu_count = 1

        cpu_spinbox = self.dialog.findChild(QtGui.QSpinBox, "AnalysisNumCPUs")
        if cpu_spinbox:
            cpu_count = cpu_spinbox.value()

        # Save to FreeCAD parameters
        prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/Ccx")

        if ccx_path:
            prefs.SetString("ccxBinaryPath", ccx_path)
        prefs.SetInt("AnalysisNumCPUs", cpu_count)

        prefs.SetBool("UseStandardCcxLocation", self.get_ui_checked("UseStandardCcxLocation"))

    def load_elmer_settings(self):
        """Load Elmer settings into UI"""
        from femsolver.settings import get_binary

        # Get current binary paths
        elmer_path = get_binary("ElmerSolver") or "ElmerSolver"
        grid_path = get_binary("ElmerGrid") or "ElmerGrid"

        # Set UI values
        self.set_ui_value("ElmerBinaryPath", elmer_path)
        self.set_ui_value("GridBinaryPath", grid_path)

    def save_elmer_settings(self):
        """Save Elmer settings from UI"""
        # Get values from UI
        elmer_path = self.get_ui_value("ElmerBinaryPath")
        grid_path = self.get_ui_value("GridBinaryPath")

        # Save to FreeCAD parameters (using Ccx group as Elmer uses similar structure)
        prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/Ccx")

        if elmer_path:
            prefs.SetString("elmerBinaryPath", elmer_path)
        if grid_path:
            prefs.SetString("gridBinaryPath", grid_path)

        prefs.SetBool("UseStandardElmerLocation", self.get_ui_checked("UseStandardElmerLocation"))
        prefs.SetBool("UseStandardGridLocation", self.get_ui_checked("UseStandardGridLocation"))

    def load_general_settings(self):
        """Load general FEM settings into UI"""
        # Load working directory settings
        prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/General")

        # Working directory setting
        working_dir_setting = prefs.GetInt("WorkingDirectory", 0)  # 0 = temporary, 1 = beside, 2 = custom

        combo_box = self.dialog.findChild(QtGui.QComboBox, "WorkingDirectory")
        if combo_box:
            if working_dir_setting < combo_box.count():
                combo_box.setCurrentIndex(working_dir_setting)

        # Custom directory path
        custom_path = prefs.GetString("CustomDirectoryPath", "")
        self.set_ui_value("CustomDirectoryPath", custom_path)

        # Other settings
        overwrite_solver_wd = prefs.GetBool("OverwriteSolverWorkingDirectory", True)
        keep_results = prefs.GetBool("KeepResultsOnReRun", False)
        write_comments = prefs.GetBool("WriteCommentsToInputFile", True)

        self.set_ui_checked("OverwriteSolverWorkingDirectory", overwrite_solver_wd)
        self.set_ui_checked("KeepResultsOnReRun", keep_results)
        self.set_ui_checked("WriteCommentsToInputFile", write_comments)

        # Default solver
        default_solver_idx = prefs.GetInt("DefaultSolver", 0)
        solver_combo = self.dialog.findChild(QtGui.QComboBox, "DefaultSolver")
        if solver_combo and default_solver_idx < solver_combo.count():
            solver_combo.setCurrentIndex(default_solver_idx)

    def save_general_settings(self):
        """Save general FEM settings from UI"""
        prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/General")

        # Working directory setting
        combo_box = self.dialog.findChild(QtGui.QComboBox, "WorkingDirectory")
        if combo_box:
            working_dir_setting = combo_box.currentIndex()
            prefs.SetInt("WorkingDirectory", working_dir_setting)

        # Custom directory path
        custom_path = self.get_ui_value("CustomDirectoryPath")
        prefs.SetString("CustomDirectoryPath", custom_path)

        # Other settings
        prefs.SetBool("OverwriteSolverWorkingDirectory", self.get_ui_checked("OverwriteSolverWorkingDirectory"))
        prefs.SetBool("KeepResultsOnReRun", self.get_ui_checked("KeepResultsOnReRun"))
        prefs.SetBool("WriteCommentsToInputFile", self.get_ui_checked("WriteCommentsToInputFile"))

        # Default solver
        solver_combo = self.dialog.findChild(QtGui.QComboBox, "DefaultSolver")
        if solver_combo:
            default_solver_idx = solver_combo.currentIndex()
            prefs.SetInt("DefaultSolver", default_solver_idx)

# Global instance
_fem_settings_dialog = None

def show_fem_settings():
    """Show FEM settings dialog"""
    global _fem_settings_dialog
    if _fem_settings_dialog is None:
        _fem_settings_dialog = FemSettingsDialog()
    _fem_settings_dialog.show()

# Add to FreeCAD command system
if FreeCAD.GuiUp:
    FreeCADGui.addCommand('Fem_Settings', show_fem_settings)
