# ***************************************************************************
# *   Copyright (c) 2017 Markus Hovorka <m.hovorka@live.de>                 *
# *   Copyright (c) 2017 Bernd Hahnebach <bernd@bimstatik.org>              *
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

__title__ = "FreeCAD FEM solver OpenRadioss tasks"
__author__ = "Markus Hovorka, Bernd Hahnebach"
__url__ = "https://www.freecad.org"

## \addtogroup FEM
#  @{

import os
import os.path
import subprocess

import FreeCAD

from . import writer
from .. import run
from .. import settings
from feminout import importCcxDatResults
from feminout import importCcxFrdResults
from femmesh import meshsetsgetter
from femtools import femutils
from femtools import membertools


_inputFileName = None


class Check(run.Check):

    def run(self):
        self.pushStatus("Checking analysis member...\n")
        self.check_mesh_exists()

        # workaround use Calculix ccxtools pre checks
        from femtools.checksanalysis import check_member_for_solver_calculix

        message = check_member_for_solver_calculix(
            self.analysis,
            self.solver,
            membertools.get_mesh_to_solve(self.analysis)[0],
            membertools.AnalysisMember(self.analysis),
        )
        if message:
            text = "OpenRadioss can not be started...\n"
            self.report.error(f"{text}{message}")
            self.fail()
            return


class Prepare(run.Prepare):

    def run(self):
        global _inputFileName
        self.pushStatus("Preparing input...\n")

        # get mesh set data
        # TODO evaluate if it makes sense to add new task
        # between check and prepare to the solver frame work
        mesh_obj = membertools.get_mesh_to_solve(self.analysis)[0]  # pre check done already
        meshdatagetter = meshsetsgetter.MeshSetsGetter(
            self.analysis,
            self.solver,
            mesh_obj,
            membertools.AnalysisMember(self.analysis),
        )
        meshdatagetter.get_mesh_sets()

        # write solver input
        w = writer.FemInputWriterCcx(
            self.analysis,
            self.solver,
            mesh_obj,
            meshdatagetter.member,
            self.directory,
            meshdatagetter.mat_geo_sets,
        )
        path = w.write_solver_input()
        # report to user if task succeeded
        if path != "" and os.path.isfile(path):
            self.pushStatus("Writing solver input completed.")
        else:
            self.pushStatus("Writing solver input failed.")
            self.fail()
        _inputFileName = os.path.splitext(os.path.basename(path))[0]


class Solve(run.Solve):

    def run(self):
        self.pushStatus("Executing solver...\n")

        # get solver binary
        self.pushStatus("Get solver binary...\n")
        binary = settings.get_binary("OpenRadioss")
        if binary is None:
            self.pushStatus("Error: The OpenRadioss binary has not been found!")
            self.fail()
            return

        # run solver
        self._process = subprocess.Popen(
            [binary, "-i", _inputFileName],
            cwd=self.directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.signalAbort.add(self._process.terminate)
        # output = self._observeSolver(self._process)
        self._process.communicate()
        self.signalAbort.remove(self._process.terminate)
        # if not self.aborted:
        #     self._updateOutput(output)
        # del output   # get flake8 quiet


class Results(run.Results):

    def run(self):
        prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/General")
        if not prefs.GetBool("KeepResultsOnReRun", False):
            self.purge_results()
        self.load_results()

    def purge_results(self):
        self.pushStatus("Purge existing results...\n")
        # TODO dat file will not be removed
        # TODO implement a generic purge method
        # TODO results from other solvers will be removed too
        # the user should decide if purge should only
        # delete this solver results or results from all solvers
        for m in membertools.get_member(self.analysis, "Fem::FemResultObject"):
            if m.Mesh and femutils.is_of_type(m.Mesh, "Fem::MeshResult"):
                self.analysis.Document.removeObject(m.Mesh.Name)
            self.analysis.Document.removeObject(m.Name)
        self.analysis.Document.recompute()

    def load_results(self):
        self.pushStatus("Import new results...\n")
        self.load_ccxfrd_results()
        self.load_ccxdat_results()

    def load_ccxfrd_results(self):
        frd_result_file = os.path.join(self.directory, _inputFileName + ".frd")
        if os.path.isfile(frd_result_file):
            result_name_prefix = "OpenRadioss_" + self.solver.AnalysisType + "_"
            importCcxFrdResults.importFrd(frd_result_file, self.analysis, result_name_prefix)
        else:
            # TODO: use solver framework status message system
            FreeCAD.Console.PrintError(f"FEM: No results found at {frd_result_file}!\n")
            self.fail()

    def load_ccxdat_results(self):
        dat_result_file = os.path.join(self.directory, _inputFileName + ".dat")
        FreeCAD.Console.PrintMessage(f"DEBUG: Checking for DAT file at {dat_result_file}\n")
        if os.path.isfile(dat_result_file):
            FreeCAD.Console.PrintMessage("DEBUG: Importing DAT results\n")
            mode_frequencies = importCcxDatResults.import_dat(dat_result_file, self.analysis)
            FreeCAD.Console.PrintMessage(f"DEBUG: Found {len(mode_frequencies)} mode frequencies\n")
        else:
            # TODO: use solver framework status message system
            FreeCAD.Console.PrintError(f"FEM: No results found at {dat_result_file}!\n")
            self.fail()
        if mode_frequencies:
            FreeCAD.Console.PrintMessage(f"DEBUG: Processing {len(mode_frequencies)} eigenmodes\n")
            for m in membertools.get_member(self.analysis, "Fem::FemResultObject"):
                if m.Eigenmode > 0:
                    for mf in mode_frequencies:
                        if m.Eigenmode == mf["eigenmode"]:
                            m.EigenmodeFrequency = mf["frequency"]
                            FreeCAD.Console.PrintMessage(f"DEBUG: Set frequency for mode {m.Eigenmode}\n")


class _TaskPanel:
    """TaskPanel for the OpenRadioss solver."""
    
    def __init__(self, obj):
        self.obj = obj
        self.form = FreeCADGui.PySideUic.loadUi(
            os.path.join(os.path.dirname(__file__), "TaskPanel.ui")
        )
        self._setupConnections()
        
    def _setupConnections(self):
        """Setup signal/slot connections for the UI."""
        self.form.pb_edit.clicked.connect(self.edit)
        self.form.pb_reset.clicked.connect(self.reset)
        
    def setupUi(self):
        """Initialize the UI with current values."""
        self.form.sb_eigenmodes.setValue(self.obj.Eigenmodes)
        self.form.sb_cycles.setValue(self.obj.IterationsMaximum)
        self.form.dsb_time_step.setValue(self.obj.TimeStep)
        self.form.dsb_time_end.setValue(self.obj.TimeEnd)
        
    def edit(self):
        """Handle edit button click."""
        self.obj.Eigenmodes = self.form.sb_eigenmodes.value()
        self.obj.IterationsMaximum = self.form.sb_cycles.value()
        self.obj.TimeStep = self.form.dsb_time_step.value()
        self.obj.TimeEnd = self.form.dsb_time_end.value()
        FreeCADGui.ActiveDocument.resetEdit()
        
    def reset(self):
        """Reset to default values."""
        self.form.sb_eigenmodes.setValue(10)
        self.form.sb_cycles.setValue(1000)
        self.form.dsb_time_step.setValue(1.0)
        self.form.dsb_time_end.setValue(1.0)
    
    @staticmethod
    def unsetEdit():
        """Clean up when editing is finished."""
        FreeCADGui.Control.closeDialog()
        FreeCAD.ActiveDocument.recompute()

##  @}
