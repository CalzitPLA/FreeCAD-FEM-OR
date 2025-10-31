"""
Create Basic LS-DYNA .k File command for FreeCAD.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets
import os

class CreateBasicKFile:
    """Command to create a new basic LS-DYNA .k file object in FreeCAD."""

    def GetResources(self):
        """Return a dictionary with data that will be used by the button or menu item."""
        return {
            'Pixmap': ':/icons/document-new',
            'MenuText': 'Create Basic .k File',
            'ToolTip': 'Create a new basic LS-DYNA .k file object',
            'CmdType': 'ForEdit'
        }

    def Activated(self):
        """Run the command to create a new basic LS-DYNA .k file object."""
        try:
            # Create a new document if none exists
            if not App.ActiveDocument:
                doc = App.newDocument("LSDyna_Model")
                doc.Label = "LS-DYNA Model"
            else:
                doc = App.ActiveDocument

            # Create the LS-DYNA keyword text object
            k_file_obj = doc.addObject("App::TextDocument", "LSDynaKeywords")
            k_file_obj.Label = "LS-DYNA Keywords"

            # Set the text content
            k_file_obj.Text = self._generate_basic_k_file_content()

            # Set the view to show the text editor
            if Gui.ActiveDocument:
                Gui.ActiveDocument.activeView().viewIsometric()
                Gui.SendMsgToActiveView("ViewFit")

            # Refresh the view
            doc.recompute()

            # Set the active workbench to OpenRadioss
            Gui.activateWorkbench("OpenRadiossWorkbench")

            # Show success message
            QtWidgets.QMessageBox.information(
                None,
                "LS-DYNA Keywords Created",
                "LS-DYNA keywords text document created successfully in the active document.\n\n"
                "You can now:\n"
                "• View the content in the Property panel (Text property)\n"
                "• Edit the content by modifying the Text property\n"
                "• Export to .k file using the Export command\n"
                "• The content is stored in the .FCStd file"
            )

            return True

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                None,
                "Error creating LS-DYNA keywords",
                f"An error occurred while creating the LS-DYNA keywords:\n{str(e)}"
            )
            return False

    def _generate_basic_k_file_content(self):
        """Generate basic LS-DYNA .k file content."""
        content = """*KEYWORD
*TITLE
Basic LS-DYNA Model - Getting Started
$
$ This is a basic LS-DYNA input file template
$ Created by FreeCAD OpenRadioss Workbench
$
*CONTROL_TERMINATION
$  endtim    endcyc     dtmin       endeng     endmas
     1.0
$
*CONTROL_TIMESTEP
$  dtinit    scft     isdo     tsd0       dt2ms       dtmp       dt2ms
     0.0     0.0     0.0     0.0
$
*CONTROL_OUTPUT
$  npopt     neecho    nrefup     iaccu     opifs     iodc
     1         1         1         1
$
*DATABASE_BINARY_D3PLOT
$  dt/cycl  lcdt      ioopt
   0.01
$
*DATABASE_BINARY_D3THDT
$  dt/cycl  lcdt      ioopt
   0.01
$
*DATABASE_GLSTAT
$  dt/cycl  lcdt      ioopt
   0.01
$
*DATABASE_MATSUM
$  dt/cycl  lcdt      ioopt
   0.01
$
*DATABASE_NODOUT
$  dt/cycl  lcdt      ioopt
   0.01
$
*DATABASE_RWFORC
$  dt/cycl  lcdt      ioopt
   0.01
$
*DATABASE_SECFORC
$  dt/cycl  lcdt      ioopt
   0.01
$
*PART
$      pid     secid       mid     eosid      hgid      grav    adpopt
         1         1         1         0         0         0         0
$
*SECTION_SHELL
$     sid    elform      shrf       nip     propt   qr/irid     icomp    setyp
        1         2     1.000     3.000         0         0         0         0
$
*MAT_ELASTIC
$      mid        ro         e        pr         da         db         k
         1    7.8e-9     2.0e5      0.30
$
*NODE
$     nid               x               y               z      tc      rc
         1       0.000000       0.000000       0.000000       0       0
         2       1.000000       0.000000       0.000000       0       0
         3       1.000000       1.000000       0.000000       0       0
         4       0.000000       1.000000       0.000000       0       0
$
*ELEMENT_SHELL
$     eid     pid      n1      n2      n3      n4
         1       1       1       2       3       4
$
*END"""
        return content

    def IsActive(self):
        """Define whether the command is active or not (greyed out)."""
        # Always active as we can create a new .k file object anytime
        return True
