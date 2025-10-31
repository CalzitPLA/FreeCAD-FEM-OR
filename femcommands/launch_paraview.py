"""
OpenRadioss ParaView launcher command for FreeCAD.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets


class LaunchParaView:
    """Command to launch ParaView with OpenRadioss results."""

    def GetResources(self):
        """Return a dictionary with data that will be used by the button or menu item."""
        return {
            'Pixmap': ':/icons/utilities-terminal',
            'MenuText': 'Launch ParaView',
            'ToolTip': 'Launch ParaView with OpenRadioss analysis results',
            'CmdType': 'ForEdit'
        }

    def Activated(self):
        """Run the command to launch ParaView."""
        try:
            # Find the active OpenRadioss solver
            solver = None
            analysis = None

            # Look for active analysis with OpenRadioss solver
            if App.ActiveDocument:
                for obj in App.ActiveDocument.Objects:
                    if obj.isDerivedFrom("Fem::FemAnalysis"):
                        analysis = obj
                        # Look for OpenRadioss solver in the analysis
                        for member in obj.Group:
                            if member.isDerivedFrom("Fem::SolverOpenRadioss"):
                                solver = member
                                break
                        if solver:
                            break

            if not solver:
                QtWidgets.QMessageBox.information(
                    None,
                    "No OpenRadioss Solver Found",
                    "No active OpenRadioss solver found.\n\n"
                    "Please open an analysis with an OpenRadioss solver."
                )
                return False

            # Import and use the OpenRadioss tools
            from femtools.runORtools import FemToolsOR

            # Create tools instance and launch ParaView
            tools = FemToolsOR(analysis=analysis, solver=solver)

            # Set up working directory and input file
            tools.setup_working_dir()
            tools.set_k_file_name()

            # Try to launch ParaView
            success = tools.launch_paraview_with_results()

            if success:
                QtWidgets.QMessageBox.information(
                    None,
                    "ParaView Launched",
                    "ParaView has been launched with the analysis results.\n\n"
                    "Check the console for details."
                )
            else:
                QtWidgets.QMessageBox.warning(
                    None,
                    "ParaView Launch Failed",
                    "Could not launch ParaView with the analysis results.\n\n"
                    "Check the console for error details."
                )

            return True

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                None,
                "Error Launching ParaView",
                f"An error occurred while launching ParaView:\n{str(e)}"
            )
            return False

    def IsActive(self):
        """Define whether the command is active or not (greyed out)."""
        # Check if there's an active analysis with OpenRadioss solver
        if App.ActiveDocument:
            for obj in App.ActiveDocument.Objects:
                if obj.isDerivedFrom("Fem::FemAnalysis"):
                    for member in obj.Group:
                        if member.isDerivedFrom("Fem::SolverOpenRadioss"):
                            return True
        return False


# Register the command
if App.GuiUp:
    Gui.addCommand('Fem_LaunchParaView', LaunchParaView())
