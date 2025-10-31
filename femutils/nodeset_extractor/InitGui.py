# SPDX-License-Identifier: LGPL-2.1-or-later

import FreeCADGui as Gui

class NodesetExtractorWorkbench(Gui.Workbench):
    """Nodeset Extractor workbench"""
    MenuText = "Nodeset Extractor"
    ToolTip = "Extract nodesets from FEM constraints"
    Icon = "FEM_ConstraintFixed"  # Using an existing icon
    
    def Initialize(self):
        """Initialize the workbench"""
        from .gui import NodesetExtractorCommand
        self.cmd = NodesetExtractorCommand()
        
        # Add a toolbar
        self.toolbar = ["FEM_NodesetExtractor"]
        
        # Add a menu
        self.menu = ["FEM_NodesetExtractor"]
        
        # Register commands
        Gui.addCommand('FEM_NodesetExtractor', self.cmd)
        
    def GetClassName(self):
        return "Gui::PythonWorkbench"

# Add to the FEM workbench's toolbar
def add_to_fem_workbench():
    """Add the command to the FEM workbench"""
    try:
        from femcommands.manager import CommandManager
        
        class NodesetExtractorCommandWrapper:
            """Wrapper to make our command compatible with FEM workbench"""
            def __init__(self):
                from .gui import NodesetExtractorCommand
                self.cmd = NodesetExtractorCommand()
                self.resources = self.cmd.GetResources()
                
            def GetResources(self):
                return self.resources
                
            def IsActive(self):
                return self.cmd.IsActive()
                
            def Activated(self):
                return self.cmd.Activated()
        
        # Add to FEM workbench's command manager
        CommandManager.addCommand('FEM_NodesetExtractor', NodesetExtractorCommandWrapper())
        
        # Add to the FEM workbench's toolbar
        if hasattr(Gui, 'Snapper'):
            # For newer FreeCAD versions
            mw = Gui.getMainWindow()
            if mw:
                fem_toolbar = mw.findChild(QtGui.QToolBar, "FEM")
                if fem_toolbar:
                    fem_toolbar.addAction('FEM_NodesetExtractor')
        
        print("Nodeset Extractor added to FEM workbench")
        
    except Exception as e:
        print(f"Could not add to FEM workbench: {str(e)}")

# Add to FEM workbench when FreeCAD starts
if not hasattr(Gui, 'Workbench'):
    # For older FreeCAD versions
    Gui.addWorkbench(NodesetExtractorWorkbench())
else:
    # For newer FreeCAD versions
    add_to_fem_workbench()
