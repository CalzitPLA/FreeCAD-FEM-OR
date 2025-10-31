"""
Keyword Editor command for FreeCAD.
"""

import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

class KeywordEditorCommand:
    """Command to open the Keyword Editor dialog."""

    def GetResources(self):
        """Return a dictionary with data that will be used by the button or menu item."""
        return {
            'Pixmap': ':/icons/freecad',  # You can replace this with your own icon
            'MenuText': 'Keyword Editor',
            'ToolTip': 'Open the FEM Keyword Editor',
            'CmdType': 'ForEdit'
        }

    def Activated(self):
        """Run the command."""
        from ..gui.keyword_editor import KeywordEditorDialog

        # Create and show the dialog
        dialog = KeywordEditorDialog()
        dialog.show()

    def IsActive(self):
        """
        Define whether the command is active or not (greyed out).
        This function is called when the workbench is activated.

        Returns:
            bool: True if the command should be active, False otherwise.
        """
        # Only active when there's an active document
        return Gui.ActiveDocument is not None
