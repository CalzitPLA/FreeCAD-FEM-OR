"""
Export Radioss/LS-DYNA Input command for FreeCAD.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets
import os

class ExportRadiossInput:
    """Command to export Radioss/LS-DYNA input files."""

    def GetResources(self):
        """Return a dictionary with data that will be used by the button or menu item."""
        return {
            'Pixmap': ':/icons/freecad',  # You can replace this with your own icon
            'MenuText': 'Export LS-DYNA .k File',
            'ToolTip': 'Export LS-DYNA text document to .k file',
            'CmdType': 'ForEdit'
        }

    def Activated(self):
        """Run the command to export LS-DYNA .k file."""
        try:
            # Check if there's an active document
            if not App.ActiveDocument:
                QtWidgets.QMessageBox.warning(
                    None,
                    "No Active Document",
                    "Please open or create a document first."
                )
                return False

            # Find LS-DYNA keywords objects in the document
            k_file_objects = []
            for obj in App.ActiveDocument.Objects:
                if (hasattr(obj, 'Text') and obj.Text and 
                    obj.TypeId == 'App::TextDocument'):
                    k_file_objects.append(obj)

            if not k_file_objects:
                QtWidgets.QMessageBox.information(
                    None,
                    "No LS-DYNA Keywords Found",
                    "No LS-DYNA keywords objects found in the active document.\n\n"
                    "Use 'Create Basic .k File' to create LS-DYNA keywords first."
                )
                return False

            # If multiple objects found, let user choose
            if len(k_file_objects) > 1:
                selected_obj = self._select_k_file_object(k_file_objects)
                if not selected_obj:
                    return False
            else:
                selected_obj = k_file_objects[0]

            # Ask user where to save the file
            default_filename = f"{App.ActiveDocument.Label}_lsdyna.k"
            filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
                None,
                "Export LS-DYNA .k File",
                os.path.join(os.path.expanduser("~"), "Documents", default_filename),
                "LS-DYNA files (*.k);;All files (*.*)"
            )

            if not filepath:
                return False  # User cancelled

            # Export the LS-DYNA content
            success = self._export_k_file(selected_obj, filepath)

            if success:
                QtWidgets.QMessageBox.information(
                    None,
                    "Export Successful",
                    f"LS-DYNA .k file exported successfully:\n{filepath}"
                )

                # Open the file if possible
                try:
                    import subprocess
                    subprocess.Popen([filepath], shell=True)
                except:
                    pass  # Silently ignore if we can't open the file

            return success

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                None,
                "Export Error",
                f"An error occurred while exporting:\n{str(e)}"
            )
            return False

    def _select_k_file_object(self, objects):
        """Let user select which LS-DYNA keywords object to export."""
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Select LS-DYNA Keywords Object")
        dialog.setMinimumWidth(300)

        layout = QtWidgets.QVBoxLayout()

        label = QtWidgets.QLabel("Multiple LS-DYNA keywords objects found. Please select which one to export:")
        layout.addWidget(label)

        combo = QtWidgets.QComboBox()
        for obj in objects:
            # Show object label and a preview of the content
            content_preview = obj.Text[:50] + "..." if len(obj.Text) > 50 else obj.Text
            combo.addItem(f"{obj.Label} - {content_preview}", obj)
        layout.addWidget(combo)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.setLayout(layout)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            return combo.itemData(combo.currentIndex())
        return None

    def _export_k_file(self, k_file_obj, filepath):
        """Export LS-DYNA text document to .k file."""
        try:
            # Get the text content
            content = k_file_obj.Text

            if not content:
                QtWidgets.QMessageBox.warning(
                    None,
                    "No Content",
                    "The selected LS-DYNA text document has no content to export."
                )
                return False

            # Write the file
            with open(filepath, 'w') as f:
                f.write(content)

            return True

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                None,
                "Export Error",
                f"Failed to export .k file:\n{str(e)}"
            )
            return False

    def IsActive(self):
        """Define whether the command is active or not (greyed out)."""
        # Only active when there's an active document
        return App.ActiveDocument is not None
