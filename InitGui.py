# ***************************************************************************
# *   Copyright (c) 2009 Juergen Riegel <juergen.riegel@web.de>             *
# *   Copyright (c) 2020 Bernd Hahnebach <bernd@bimstatik.org>              *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

"""FEM module Gui init script

Gathering all the information to start FreeCAD.
This is the second one of three init scripts.
The third one runs when the gui is up.

The script is executed using exec().
This happens inside srd/Gui/FreeCADGuiInit.py
All imports made there are available here too.
Thus no need to import them here.
But the import code line is used anyway to get flake8 quired.
Since they are cached they will not be imported twice.
"""

__title__ = "FEM module Gui init script"
__author__ = "Juergen Riegel, Bernd Hahnebach"
__url__ = "https://www.freecad.org"

# imports to get flake8 quired
import sys
import FreeCAD
import FreeCADGui
from FreeCADGui import Workbench

# needed imports
from femguiutils.migrate_gui import FemMigrateGui


# migrate old FEM Gui objects
sys.meta_path.append(FemMigrateGui())


# add FEM Gui unit tests
FreeCAD.__unit_test__ += ["TestFemGui"]


class FEMORWorkbench(Workbench):
    """FEMOR - Finite Element Modeling and Analysis workbench"""

    def __init__(self):
        self.__class__.Icon = FreeCAD.getResourceDir() + "Mod/Fem/Resources/icons/FemWorkbench.svg"
        self.__class__.MenuText = "FEMOR"
        self.__class__.ToolTip = "FEMOR - Finite Element Modeling and Analysis"

    def Initialize(self):
        # Load modules
        import Fem
        import FemGui
        import femcommands.commands
        from femcommands.open_cache_viewer import OpenCacheViewer
        from femutils.nodeset_extractor import _import_gui

        # Register the commands
        FreeCADGui.addCommand('FEM_OpenCacheViewer', OpenCacheViewer())
        
        # Get the command class using the import function to avoid circular imports
        NodesetExtractorCommand = _import_gui()
        if NodesetExtractorCommand is not None:
            FreeCADGui.addCommand('FEM_NodesetExtractor', NodesetExtractorCommand())

        FreeCADGui.addPreferencePage(":/ui/DlgSettingsNetgen.ui", "FEM")
        FreeCADGui.addPreferencePage("/home/nemo/Dokumente/Sandbox/Fem_upgraded/Resources/ui/DlgSettingsFem.ui", "FEM_upgraded")

        # Define the menu directly
        self.appendMenu("Solve", ["FEM_SolverOpenRadioss", "FEM_FemKeywordEditor", "FEM_OpenRadiossGui", "FEM_UpdateKFile", "FEM_SolverControl"])
        self.appendMenu("FEM", ["FEM_Analysis", "FEM_MaterialSolid", "FEM_MeshGmshFromShape", "FEM_MeshNetgenFromShape", "FEM_SolverCalculiX", "FEM_ConstraintFixed", "FEM_ConstraintPressure", "FEM_ConstraintForce", "FEM_ConstraintTemperature", "FEM_MaterialFluid", "FEM_SolverElmer", "FEM_ResultsPurge", "FEM_OpenCacheViewer", "FEM_NodesetExtractor"])  # Added FEM_NodesetExtractor to menu

        # Define the toolbar directly
        self.appendToolbar("Solve", ["FEM_SolverOpenRadioss", "FEM_FemKeywordEditor"])
        self.appendToolbar("FEM", ["FEM_Analysis", "FEM_MaterialSolid", "FEM_MeshGmshFromShape", "FEM_SolverCalculiX", "FEM_OpenCacheViewer", "FEM_NodesetExtractor"])  # Added to main FEM toolbar
        self.appendToolbar("Mesh", ["FEM_MeshGmshFromShape", "FEM_MeshNetgenFromShape", "FEM_MeshGroup", "FEM_MeshBoundaryLayer"])
        self.appendToolbar("Constraints", ["FEM_ConstraintFixed", "FEM_ConstraintPressure", "FEM_ConstraintForce", "FEM_ConstraintTemperature", "FEM_ConstraintSelfWeight", "FEM_NodesetExtractor"])  # Also added to Constraints toolbar
        self.appendToolbar("Materials", ["FEM_MaterialSolid", "FEM_MaterialFluid", "FEM_MaterialReinforced", "FEM_MaterialEditor"])
        self.appendToolbar("Solvers", ["FEM_SolverCalculiX", "FEM_SolverElmer", "FEM_SolverControl", "FEM_SolverOpenRadioss"])
        self.appendToolbar("Results", ["FEM_ResultShow", "FEM_ResultsPurge", "FEM_PostFilterContours", "FEM_PostFilterWarp"])

        # dummy usage to get flake8 and lgtm quiet
        False if Fem.__name__ else True
        False if FemGui.__name__ else True
        False if femcommands.commands.__name__ else True

    def GetClassName(self):
        return "Gui::PythonWorkbench"


FreeCADGui.addWorkbench(FEMORWorkbench())

# Add nodeset extractor command
try:
    from femutils.nodeset_extractor.gui import NodesetExtractorCommand
    from femutils.nodeset_extractor import extract_nodesets, process_analysis
    
    # Register the command
    Gui.addCommand('FEM_NodesetExtractor', NodesetExtractorCommand())
    
    # Add to FEM workbench's toolbar
    def add_nodeset_extractor_to_fem():
        """Add nodeset extractor to FEM workbench"""
        try:
            mw = Gui.getMainWindow()
            if mw:
                # Add to FEM workbench's toolbar
                fem_toolbar = mw.findChild(QtGui.QToolBar, "FEM")
                if fem_toolbar:
                    fem_toolbar.addAction('FEM_NodesetExtractor')
                
                # Add a toggle button to the FEM_ToggleTools toolbar
                toggle_toolbar = mw.findChild(QtGui.QToolBar, "FEM_ToggleTools")
                if not toggle_toolbar:
                    toggle_toolbar = QtGui.QToolBar("Toggle Tools", mw)
                    toggle_toolbar.setObjectName("FEM_ToggleTools")
                    mw.addToolBar(QtCore.Qt.TopToolBarArea, toggle_toolbar)
                
                # Add the toggle button
                action = QtGui.QAction(mw)
                action.setCheckable(True)
                action.setIcon(Gui.getIcon("FEM_ConstraintFixed"))
                action.setText("Toggle Nodeset Extractor")
                action.setToolTip("Show/Hide Nodeset Extractor Panel")
                action.toggled.connect(lambda checked: Gui.runCommand('FEM_NodesetExtractor') if checked else None)
                toggle_toolbar.addAction(action)
                
                return True
            return False
        except Exception as e:
            App.Console.PrintError(f"Error adding nodeset extractor to FEM workbench: {str(e)}\n")
            return False
    
    # Add the command after a short delay to ensure GUI is fully loaded
    QtCore.QTimer.singleShot(1000, add_nodeset_extractor_to_fem)
    
except Exception as e:
    App.Console.PrintError(f"Error initializing nodeset extractor: {str(e)}\n")