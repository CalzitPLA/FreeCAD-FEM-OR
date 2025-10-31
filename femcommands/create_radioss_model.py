"""
Create Radioss Model command for FreeCAD.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets
import os

class CreateRadiossModel:
    """Command to create a new Radioss model."""
    
    def GetResources(self):
        """Return a dictionary with data that will be used by the button or menu item."""
        return {
            'Pixmap': ':/icons/document-new',
            'MenuText': 'Create Radioss Model',
            'ToolTip': 'Create a new Radioss model',
            'CmdType': 'ForEdit'
        }
    
    def Activated(self):
        """Run the command to create a new Radioss model."""
        try:
            # Create a new document
            doc = App.newDocument()
            doc.Label = "Radioss_Model"
            
            # Add Radioss specific properties to the document
            if not hasattr(doc, 'Radioss'):
                doc.addProperty("App::PropertyString", "Radioss", "Radioss",
                              "Radioss model properties").Radioss = "Radioss Model"
            
            # Add a model group to organize the Radioss entities
            model_group = doc.addObject("App::DocumentObjectGroup", "RadiossModel")
            model_group.Label = "Radioss Model"
            
            # Add default groups for different Radioss entities
            groups = [
                "Parts",
                "Materials",
                "Properties",
                "Sections",
                "Loads",
                "BCs",
                "Contacts",
                "Initial_Conditions"
            ]
            
            for group_name in groups:
                group = doc.addObject("App::DocumentObjectGroup", group_name)
                group.Label = group_name
                model_group.addObject(group)
            
            # Set the view to isometric
            if Gui.ActiveDocument:
                Gui.ActiveDocument.activeView().viewIsometric()
                Gui.SendMsgToActiveView("ViewFit")
            
            return True
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                None,
                "Error creating Radioss model",
                f"An error occurred while creating the Radioss model:\n{str(e)}"
            )
            return False
    
    def IsActive(self):
        """Define whether the command is active or not (greyed out)."""
        # Always active as we can create a new model anytime
        return True
