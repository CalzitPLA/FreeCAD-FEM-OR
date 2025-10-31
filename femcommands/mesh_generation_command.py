"""
Command for FEM mesh generation in OpenRadioss workbench using FemMeshShapeObject functionality
"""

import FreeCAD
import FreeCADGui as Gui
from ..post_processing import MeshGenerationCommand

# Create the command instance
mesh_generation_cmd = MeshGenerationCommand()

class MeshGenerationWorkbenchCommand:
    """Workbench command wrapper for mesh generation"""

    def GetResources(self):
        return mesh_generation_cmd.GetResources()

    def IsActive(self):
        return mesh_generation_cmd.IsActive()

    def Activated(self):
        mesh_generation_cmd.Activated()

# Register the command with FreeCAD
# Note: Command registration is handled by the workbench in __init__.py
# if hasattr(FreeCAD, 'GuiUp') and FreeCAD.GuiUp:
#     Gui.addCommand('ORfe_FEMMeshGeneration', MeshGenerationWorkbenchCommand())
