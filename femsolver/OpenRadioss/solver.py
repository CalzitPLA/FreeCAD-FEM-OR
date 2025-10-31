# ***************************************************************************
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

__title__ = "FreeCAD FEM solver object OpenRadioss"
__author__ = "Bernd Hahnebach"
__url__ = "https://www.freecad.org"

## @package SolverOpenRadioss
#  \ingroup FEM

import glob
import os

import FreeCAD

from . import tasks
from .. import run
from .. import solverbase
from femtools import femutils

if FreeCAD.GuiUp:
    import FemGui

ANALYSIS_TYPES = ["static", "frequency", "thermomech", "check", "buckling"]


def create(doc, name="SolverCalculiX"):
    return femutils.createObject(doc, name, Proxy, ViewProxy)


class _BaseSolverOpenRadioss:

    def on_restore_of_document(self, obj):
        temp_analysis_type = obj.AnalysisType
        obj.AnalysisType = ANALYSIS_TYPES
        if temp_analysis_type in ANALYSIS_TYPES:
            obj.AnalysisType = temp_analysis_type
        else:
            FreeCAD.Console.PrintWarning(
                f"Analysis type {temp_analysis_type} not found. Standard is used.\n"
            )
            obj.AnalysisType = ANALYSIS_TYPES[0]

        self.add_attributes(obj)

    def add_attributes(self, obj):
        if not hasattr(obj, "AnalysisType"):
            obj.addProperty(
                "App::PropertyEnumeration", "AnalysisType", "Fem", "Type of the analysis"
            )
            obj.AnalysisType = ANALYSIS_TYPES
            obj.AnalysisType = ANALYSIS_TYPES[0]

        if not hasattr(obj, "GeometricalNonlinearity"):
            choices_geom_nonlinear = ["linear", "nonlinear"]
            obj.addProperty(
                "App::PropertyEnumeration",
                "GeometricalNonlinearity",
                "Fem",
                "Set geometrical nonlinearity",
            )
            obj.GeometricalNonlinearity = choices_geom_nonlinear
            obj.GeometricalNonlinearity = choices_geom_nonlinear[0]

        if not hasattr(obj, "MaterialNonlinearity"):
            choices_material_nonlinear = ["linear", "nonlinear"]
            obj.addProperty(
                "App::PropertyEnumeration",
                "MaterialNonlinearity",
                "Fem",
                "Set material nonlinearity",
            )
            obj.MaterialNonlinearity = choices_material_nonlinear
            obj.MaterialNonlinearity = choices_material_nonlinear[0]

        if not hasattr(obj, "EigenmodesCount"):
            obj.addProperty(
                "App::PropertyIntegerConstraint",
                "EigenmodesCount",
                "Fem",
                "Number of modes for frequency calculations",
            )
            obj.EigenmodesCount = (10, 1, 100, 1)

        if not hasattr(obj, "EigenmodeLowLimit"):
            obj.addProperty(
                "App::PropertyFloatConstraint",
                "EigenmodeLowLimit",
                "Fem",
                "Low frequency limit for eigenmode calculations",
            )
            obj.EigenmodeLowLimit = (0.0, 0.0, 1000000.0, 10000.0)

        if not hasattr(obj, "EigenmodeHighLimit"):
            obj.addProperty(
                "App::PropertyFloatConstraint",
                "EigenmodeHighLimit",
                "Fem",
                "High frequency limit for eigenmode calculations",
            )
            obj.EigenmodeHighLimit = (1000000.0, 0.0, 1000000.0, 10000.0)

        if not hasattr(obj, "IterationsMaximum"):
            help_string_IterationsMaximum = (
                "Maximum Number of iterations in each time step before stopping jobs"
            )
            obj.addProperty(
                "App::PropertyIntegerConstraint",
                "IterationsMaximum",
                "Fem",
                help_string_IterationsMaximum,
            )
            obj.IterationsMaximum = 2000

        if hasattr(obj, "IterationsThermoMechMaximum"):
            obj.IterationsMaximum = obj.IterationsThermoMechMaximum
            obj.removeProperty("IterationsThermoMechMaximum")

        if not hasattr(obj, "BucklingFactors"):
            obj.addProperty(
                "App::PropertyIntegerConstraint",
                "BucklingFactors",
                "Fem",
                "Calculates the lowest buckling modes to the corresponding buckling factors",
            )
            obj.BucklingFactors = 1

        if not hasattr(obj, "TimeInitialStep"):
            obj.addProperty(
                "App::PropertyFloatConstraint", "TimeInitialStep", "Fem", "Initial time steps"
            )
            obj.TimeInitialStep = 0.01

        if not hasattr(obj, "TimeEnd"):
            obj.addProperty("App::PropertyFloatConstraint", "TimeEnd", "Fem", "End time analysis")
            obj.TimeEnd = 1.0

        if not hasattr(obj, "TimeMinimumStep"):
            obj.addProperty(
                "App::PropertyFloatConstraint", "TimeMinimumStep", "Fem", "Minimum time step"
            )
            obj.TimeMinimumStep = 0.00001

        if not hasattr(obj, "TimeMaximumStep"):
            obj.addProperty(
                "App::PropertyFloatConstraint", "TimeMaximumStep", "Fem", "Maximum time step"
            )
            obj.TimeMaximumStep = 1.0

        if not hasattr(obj, "ThermoMechSteadyState"):
            obj.addProperty(
                "App::PropertyBool",
                "ThermoMechSteadyState",
                "Fem",
                "Choose between steady state thermo mech or transient thermo mech analysis",
            )
            obj.ThermoMechSteadyState = True

        if not hasattr(obj, "IterationsControlParameterTimeUse"):
            obj.addProperty(
                "App::PropertyBool",
                "IterationsControlParameterTimeUse",
                "Fem",
                "Use the user defined time incrementation control parameter",
            )
            obj.IterationsControlParameterTimeUse = False

        if not hasattr(obj, "SplitInputWriter"):
            obj.addProperty(
                "App::PropertyBool", "SplitInputWriter", "Fem", "Split writing of ccx input file"
            )
            obj.SplitInputWriter = False

        if not hasattr(obj, "IterationsControlParameterIter"):
            control_parameter_iterations = (
                "{I_0},{I_R},{I_P},{I_C},{I_L},{I_G},{I_S},{I_A},{I_J},{I_T}".format(
                    I_0=4,
                    I_R=8,
                    I_P=9,
                    I_C=200,  # ccx default = 16
                    I_L=10,
                    I_G=400,  # ccx default = 4
                    I_S="",
                    I_A=200,  # ccx default = 5
                    I_J="",
                    I_T="",
                )
            )
            obj.addProperty(
                "App::PropertyString",
                "IterationsControlParameterIter",
                "Fem",
                "User defined time incrementation iterations control parameter",
            )
            obj.IterationsControlParameterIter = control_parameter_iterations

        if not hasattr(obj, "IterationsControlParameterCutb"):
            control_parameter_cutback = "{D_f},{D_C},{D_B},{D_A},{D_S},{D_H},{D_D},{W_G}".format(
                D_f=0.25,
                D_C=0.5,
                D_B=0.75,
                D_A=0.85,
                D_S="",
                D_H="",
                D_D=1.5,
                W_G="",
            )
            obj.addProperty(
                "App::PropertyString",
                "IterationsControlParameterCutb",
                "Fem",
                "User defined time incrementation cutbacks control parameter",
            )
            obj.IterationsControlParameterCutb = control_parameter_cutback

        if not hasattr(obj, "IterationsUserDefinedIncrementations"):
            stringIterationsUserDefinedIncrementations = (
                "Set to True to switch off the ccx automatic incrementation completely "
                "(ccx parameter DIRECT). Use with care. Analysis may not converge!"
            )
            obj.addProperty(
                "App::PropertyBool",
                "IterationsUserDefinedIncrementations",
                "Fem",
                stringIterationsUserDefinedIncrementations,
            )
            obj.IterationsUserDefinedIncrementations = False

        if not hasattr(obj, "IterationsUserDefinedTimeStepLength"):
            help_string_IterationsUserDefinedTimeStepLength = (
                "Set to True to use the user defined time steps. "
                "They are set with TimeInitialStep, TimeEnd, TimeMinimum and TimeMaximum"
            )
            obj.addProperty(
                "App::PropertyBool",
                "IterationsUserDefinedTimeStepLength",
                "Fem",
                help_string_IterationsUserDefinedTimeStepLength,
            )
            obj.IterationsUserDefinedTimeStepLength = False

        if not hasattr(obj, "MatrixSolverType"):
            known_ccx_solver_types = [
                "default",
                "pastix",
                "pardiso",
                "spooles",
                "iterativescaling",
                "iterativecholesky",
            ]
            obj.addProperty(
                "App::PropertyEnumeration", "MatrixSolverType", "Fem", "Type of solver to use"
            )
            obj.MatrixSolverType = known_ccx_solver_types
            obj.MatrixSolverType = known_ccx_solver_types[0]

        if not hasattr(obj, "BeamShellResultOutput3D"):
            obj.addProperty(
                "App::PropertyBool",
                "BeamShellResultOutput3D",
                "Fem",
                "Output 3D results for 1D and 2D analysis ",
            )
            obj.BeamShellResultOutput3D = True

        if not hasattr(obj, "BeamReducedIntegration"):
            obj.addProperty(
                "App::PropertyBool",
                "BeamReducedIntegration",
                "Fem",
                "Set to True to use beam elements with reduced integration",
            )
            obj.BeamReducedIntegration = True

        if not hasattr(obj, "OutputFrequency"):
            obj.addProperty(
                "App::PropertyIntegerConstraint",
                "OutputFrequency",
                "Fem",
                "Set the output frequency in increments",
            )
            obj.OutputFrequency = 1

        if not hasattr(obj, "ModelSpace"):
            model_space_types = ["3D", "plane stress", "plane strain", "axisymmetric"]
            obj.addProperty("App::PropertyEnumeration", "ModelSpace", "Fem", "Type of model space")
            obj.ModelSpace = model_space_types

        if not hasattr(obj, "ThermoMechType"):
            thermomech_types = ["coupled", "uncoupled", "pure heat transfer"]
            obj.addProperty(
                "App::PropertyEnumeration",
                "ThermoMechType",
                "Fem",
                "Type of thermomechanical analysis",
            )
            obj.ThermoMechType = thermomech_types

    def write_input(self, k_file):
        """Write the OpenRadioss input file"""
        # self is the Proxy instance, and we need to call the FemToolsOR
        from femtools.runORtools import FemToolsOR

        # Create FemToolsOR instance for this solver
        femtools = FemToolsOR(solver=self)

        # Set up working directory and write k file
        femtools.setup_working_dir()
        femtools.write_k_file()

        # Copy the file to the requested location if different
        import shutil
        if femtools.OR_file_name != k_file:
            shutil.copy2(femtools.OR_file_name, k_file)

        return k_file


class Proxy(solverbase.Proxy, _BaseSolverOpenRadioss):
    """The Fem::FemSolver's Proxy python type, add solver specific properties"""

    Type = "Fem::SolverOpenRadioss"

    def __init__(self, obj):
        super().__init__(obj)
        obj.Proxy = self
        self.solver = obj  # Store reference to solver object
        self.add_attributes(obj)

    def onDocumentRestored(self, obj):
        self.on_restore_of_document(obj)

    def createMachine(self, obj, directory, testmode=False):
        return run.Machine(
            solver=obj,
            directory=directory,
            check=tasks.Check(),
            prepare=tasks.Prepare(),
            solve=tasks.Solve(),
            results=tasks.Results(),
            testmode=testmode,
        )

    def write_input(self, k_file):
        """Write the OpenRadioss input file"""
        # Try to import FemToolsOR with multiple fallback strategies
        FemToolsOR = None

        # Strategy 1: Try standard import
        try:
            from femtools.runORtools import FemToolsOR
            FreeCAD.Console.PrintMessage("Successfully imported FemToolsOR via standard import\n")
        except ImportError as e:
            FreeCAD.Console.PrintMessage(f"Standard import failed: {e}\n")

            # Strategy 2: Try to add the femtools path to sys.path
            try:
                import sys
                import os

                # Get the current file's directory
                current_dir = os.path.dirname(os.path.abspath(__file__))
                FreeCAD.Console.PrintMessage(f"Current file directory: {current_dir}\n")

                # Try to find femtools relative to current location
                femtools_paths = [
                    os.path.join(current_dir, '..', '..', '..', 'femtools'),  # femsolver/OpenRadioss/../femtools
                    '/home/nemo/Dokumente/Sandbox/Fem_upgraded/femtools',     # Absolute path
                    os.path.join(os.path.dirname(current_dir), 'femtools'),   # Sibling to femsolver
                ]

                for path in femtools_paths:
                    if os.path.exists(path):
                        if path not in sys.path:
                            sys.path.insert(0, path)
                            FreeCAD.Console.PrintMessage(f"Added to path: {path}\n")

                        try:
                            from runORtools import FemToolsOR
                            FreeCAD.Console.PrintMessage(f"Successfully imported FemToolsOR from {path}\n")
                            break
                        except ImportError:
                            continue
                else:
                    # If we still can't import, try importing the module object directly
                    try:
                        import runORtools
                        FemToolsOR = runORtools.FemToolsOR
                        FreeCAD.Console.PrintMessage("Successfully imported FemToolsOR as module attribute\n")
                    except ImportError:
                        raise ImportError("Cannot import FemToolsOR from femtools.runORtools - module not found in any expected location")

            except Exception as e:
                FreeCAD.Console.PrintError(f"All import strategies failed: {e}\n")
                raise ImportError("Cannot import FemToolsOR from femtools.runORtools")

        # Create FemToolsOR instance for this solver
        femtools = FemToolsOR(solver=self.solver)

        # Set up working directory and write k file
        femtools.setup_working_dir()

        # Debug: Show working directory and target file
        FreeCAD.Console.PrintMessage(f"Solver write_input: target k_file = {k_file}\n")
        FreeCAD.Console.PrintMessage(f"Solver write_input: femtools.working_dir = {femtools.working_dir}\n")
        FreeCAD.Console.PrintMessage(f"Solver write_input: femtools.OR_file_name before = {getattr(femtools, 'OR_file_name', 'Not set')}\n")

        # Instead of copying from a non-existent file, write directly to the target location
        # First, set the file name in femtools to point to our target
        femtools.OR_file_name = k_file
        femtools.inp_file_name = k_file

        FreeCAD.Console.PrintMessage(f"Solver write_input: femtools.OR_file_name after = {femtools.OR_file_name}\n")

        # Now write the file directly to the target location
        femtools.write_k_file()

        # Verify the file was actually created
        if os.path.exists(k_file):
            file_size = os.path.getsize(k_file)
            FreeCAD.Console.PrintMessage(f"Solver write_input: ✅ File successfully created at {k_file} ({file_size} bytes)\n")
        else:
            FreeCAD.Console.PrintError(f"Solver write_input: ❌ File was NOT created at {k_file}\n")

        return k_file

class ViewProxy(solverbase.ViewProxy):
    pass


"""
Should there be some equation object for OpenRadioss too?

Necessarily yes! The properties GeometricalNonlinearity,
MaterialNonlinearity, ThermoMechSteadyState might be moved
to the appropriate equation.

Furthermore the material Category should not be used in writer.
See common material object for more information. The equation
should used instead to get this information needed in writer.
"""
