# ***************************************************************************
# *   Copyright (c) 2021 Bernd Hahnebach <bernd@bimstatik.org>              *
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

__title__ = "FreeCAD FEM calculix write inpfile step equation"
__author__ = "Bernd Hahnebach"
__url__ = "https://www.freecad.org"


import FreeCAD


def write_step_equation(f, ORwriter):

    f.write("\n{}\n".format(59 * "*"))
    f.write("** At least one step is needed to run an CalculiX analysis of FreeCAD\n")

    # build STEP line
    step = "*STEP"
    if ORwriter.solver_obj.GeometricalNonlinearity == "nonlinear":
        if ORwriter.analysis_type == "static" or ORwriter.analysis_type == "thermomech":
            # https://www.comsol.com/blogs/what-is-geometric-nonlinearity
            step += ", NLGEOM"
        elif ORwriter.analysis_type == "frequency":
            FreeCAD.Console.PrintMessage(
                "Analysis type frequency and geometrical nonlinear "
                "analysis are not allowed together, linear is used instead!\n"
            )
    if ORwriter.solver_obj.IterationsMaximum:
        if ORwriter.analysis_type == "thermomech" or ORwriter.analysis_type == "static":
            step += f", INC={ORwriter.solver_obj.IterationsMaximum}"
        elif ORwriter.analysis_type == "frequency" or ORwriter.analysis_type == "buckling":
            # parameter is for thermomechanical analysis only, see ccx manual *STEP
            pass
    # write STEP line
    f.write(step + "\n")

    # CONTROLS line
    # all analysis types, ... really in frequency too?!?
    if ORwriter.solver_obj.IterationsControlParameterTimeUse:
        f.write("*CONTROLS, PARAMETERS=TIME INCREMENTATION\n")
        f.write(ORwriter.solver_obj.IterationsControlParameterIter + "\n")
        f.write(ORwriter.solver_obj.IterationsControlParameterCutb + "\n")

    # ANALYSIS type line
    # analysis line --> analysis type
    if ORwriter.analysis_type == "static":
        analysis_type = "*STATIC"
    elif ORwriter.analysis_type == "frequency":
        analysis_type = "*FREQUENCY"
    elif ORwriter.analysis_type == "thermomech":
        if ORwriter.solver_obj.ThermoMechType == "coupled":
            analysis_type = "*COUPLED TEMPERATURE-DISPLACEMENT"
        elif ORwriter.solver_obj.ThermoMechType == "uncoupled":
            analysis_type = "*UNCOUPLED TEMPERATURE-DISPLACEMENT"
        elif ORwriter.solver_obj.ThermoMechType == "pure heat transfer":
            analysis_type = "*HEAT TRANSFER"
    elif ORwriter.analysis_type == "check":
        analysis_type = "*NO ANALYSIS"
    elif ORwriter.analysis_type == "buckling":
        analysis_type = "*BUCKLE"
    # analysis line --> solver type
    # https://forum.freecad.org/viewtopic.php?f=18&t=43178
    if ORwriter.solver_obj.MatrixSolverType == "default":
        pass
    elif ORwriter.solver_obj.MatrixSolverType == "pastix":
        analysis_type += ", SOLVER=PASTIX"
    elif ORwriter.solver_obj.MatrixSolverType == "pardiso":
        analysis_type += ", SOLVER=PARDISO"
    elif ORwriter.solver_obj.MatrixSolverType == "spooles":
        analysis_type += ", SOLVER=SPOOLES"
    elif ORwriter.solver_obj.MatrixSolverType == "iterativescaling":
        analysis_type += ", SOLVER=ITERATIVE SCALING"
    elif ORwriter.solver_obj.MatrixSolverType == "iterativecholesky":
        analysis_type += ", SOLVER=ITERATIVE CHOLESKY"
    # analysis line --> user defined incrementations --> parameter DIRECT
    # --> completely switch off ccx automatic incrementation
    if ORwriter.solver_obj.IterationsUserDefinedIncrementations:
        if ORwriter.analysis_type == "static":
            analysis_type += ", DIRECT"
        elif ORwriter.analysis_type == "thermomech":
            analysis_type += ", DIRECT"
        elif ORwriter.analysis_type == "frequency":
            FreeCAD.Console.PrintMessage(
                "Analysis type frequency and IterationsUserDefinedIncrementations "
                "are not allowed together, it is ignored\n"
            )
    # analysis line --> steadystate --> thermomech only
    if ORwriter.solver_obj.ThermoMechSteadyState:
        # bernd: I do not know if STEADY STATE is allowed with DIRECT
        # but since time steps are 1.0 it makes no sense IMHO
        if ORwriter.analysis_type == "thermomech":
            analysis_type += ", STEADY STATE"
            # Set time to 1 and ignore user inputs for steady state
            ORwriter.solver_obj.TimeInitialStep = 1.0
            ORwriter.solver_obj.TimeEnd = 1.0
        elif (
            ORwriter.analysis_type == "static"
            or ORwriter.analysis_type == "frequency"
            or ORwriter.analysis_type == "buckling"
        ):
            pass  # not supported for static and frequency!

    # ANALYSIS parameter line
    analysis_parameter = ""
    if ORwriter.analysis_type == "static" or ORwriter.analysis_type == "check":
        if (
            ORwriter.solver_obj.IterationsUserDefinedIncrementations is True
            or ORwriter.solver_obj.IterationsUserDefinedTimeStepLength is True
        ):
            analysis_parameter = "{},{},{},{}".format(
                ORwriter.solver_obj.TimeInitialStep,
                ORwriter.solver_obj.TimeEnd,
                ORwriter.solver_obj.TimeMinimumStep,
                ORwriter.solver_obj.TimeMaximumStep,
            )
    elif ORwriter.analysis_type == "frequency":
        if (
            ORwriter.solver_obj.EigenmodeLowLimit == 0.0
            and ORwriter.solver_obj.EigenmodeHighLimit == 0.0
        ):
            analysis_parameter = f"{ORwriter.solver_obj.EigenmodesCount}\n"
        else:
            analysis_parameter = "{},{},{}\n".format(
                ORwriter.solver_obj.EigenmodesCount,
                ORwriter.solver_obj.EigenmodeLowLimit,
                ORwriter.solver_obj.EigenmodeHighLimit,
            )
    elif ORwriter.analysis_type == "thermomech":
        # OvG: 1.0 increment, total time 1 for steady state will cut back automatically
        analysis_parameter = "{},{},{},{}".format(
            ORwriter.solver_obj.TimeInitialStep,
            ORwriter.solver_obj.TimeEnd,
            ORwriter.solver_obj.TimeMinimumStep,
            ORwriter.solver_obj.TimeMaximumStep,
        )
    elif ORwriter.analysis_type == "buckling":
        analysis_parameter = f"{ORwriter.solver_obj.BucklingFactors}\n"

    # write analysis type line, analysis parameter line
    f.write(analysis_type + "\n")
    f.write(analysis_parameter + "\n")


def write_step_end(f, ORwriter):
    f.write("\n{}\n".format(59 * "*"))
    f.write("*END STEP\n")
