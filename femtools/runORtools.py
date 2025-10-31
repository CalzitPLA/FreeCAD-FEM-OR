# ***************************************************************************
# *   Copyright (c) 2015 Przemo Firszt <przemo@firszt.eu>                   *
# *   Copyright (c) 2016 Bernd Hahnebach <bernd@bimstatik.org>              *
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

__title__ = "FemToolsCcx"
__author__ = "Przemo Firszt, Bernd Hahnebach"
__url__ = "https://www.freecad.org"

## \addtogroup FEM
#  @{

import os
import sys
import subprocess
import time

# Import femtools modules
from femtools import femutils
from femtools import membertools

# Import Qt modules
from PySide import QtCore

# Import FreeCAD only when needed to avoid startup issues
def _import_freecad():
    try:
        import FreeCAD
        return FreeCAD
    except ImportError:
        # This shouldn't happen in FreeCAD, but handle gracefully
        raise ImportError("FreeCAD not available")

def _import_gui():
    FreeCAD = _import_freecad()
    if FreeCAD.GuiUp:
        from PySide import QtGui
        import FemGui
        return QtGui, FemGui
    return None, None


class FemToolsOR(QtCore.QRunnable, QtCore.QObject):
    """

    Attributes
    ----------
    analysis : Fem::FemAnalysis
        FEM group analysis object
        has to be present, will be set in __init__
    solver : Fem::FemSolverObjectPython
        FEM solver object
        has to be present, will be set in __init__
    base_name : str
        name of .inp/.frd file (without extension)
        It is used to construct .inp file path that is passed to CalculiX ccx
    ccx_binary : str
    working_dir : str
    results_present : bool
        indicating if there are calculation results ready for us
    members : class femtools/membertools/AnalysisMember
        contains references to all analysis member except solvers and mesh
        Updated with update_objects
    """

    finished = QtCore.Signal(int)

    def __init__(self, analysis=None, solver=None, test_mode=False):
        """The constructor

        Parameters
        ----------
        analysis : Fem::FemAnalysis, optional
            analysis group as a container for all  objects needed for the analysis
        solver : Fem::FemSolverObjectPython, optional
            solver object to be used for this solve
        test_mode : bool, optional
            mainly used in unit tests
        """

        QtCore.QRunnable.__init__(self)
        QtCore.QObject.__init__(self)

        FreeCAD = _import_freecad()
        QtGui, FemGui = _import_gui()

        self.ccx_binary_present = False
        self.analysis = None
        self.solver = None

        # TODO if something will go wrong in __init__ do not continue,
        # but do not raise a exception, break in a smarter way

        if analysis:
            self.analysis = analysis
            if solver:
                # analysis and solver given
                self.solver = solver
            else:
                # analysis given, search for the solver
                self.find_solver()
                if not self.solver:
                    raise Exception("FEM: No solver found!")
        else:
            if solver:
                # solver given, search for the analysis
                self.solver = solver
                self.find_solver_analysis()
                if not self.analysis:
                    raise Exception(
                        "FEM: The solver was given as parameter, "
                        "but no analysis for this solver was found!"
                    )
            else:
                # neither analysis nor solver given, search both
                self.find_analysis()

        # Set default values
        self.base_name = ""
        self.inp_file_name = ""
        self.working_dir = ""
        self.mesh = None
        self.member = None
        self.results_present = False

        # Initialize FemToolsOR specific attributes
        self.ccx_binary = ""
        self.ccx_binary_present = False
        self.result_object = None
        self.test_mode = test_mode

        if self.analysis and self.solver:
            self.working_dir = ""
            self.ccx_binary = ""
            self.base_name = ""
            self.results_present = False
            if test_mode:
                self.test_mode = True
                self.ccx_binary_present = True
            else:
                self.test_mode = False
                self.ccx_binary_present = False
        else:
            raise Exception(
                "FEM: Something went wrong, the exception should have been raised earlier!"
            )

    def purge_results(self):
        """Remove all result objects and result meshes from an analysis group"""
        from femresult.resulttools import purge_results as pr

        pr(self.analysis)

    def reset_mesh_purge_results_checked(self):
        """Reset mesh color, deformation and removes all result objects
        if preferences to keep them is not set.
        """
        FreeCAD = _import_freecad()

        self.fem_prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/General")
        keep_results_on_rerun = self.fem_prefs.GetBool("KeepResultsOnReRun", False)
        if not keep_results_on_rerun:
            self.purge_results()

    def reset_all(self):
        """Reset mesh color, deformation and removes all result objects"""
        self.purge_results()

    def _get_several_member(self, obj_type):
        return membertools.get_several_member(self.analysis, obj_type)

    def find_analysis(self):
        FreeCAD = _import_freecad()
        QtGui, FemGui = _import_gui()

        if FreeCAD.GuiUp:
            self.analysis = FemGui.getActiveAnalysis()
        if self.analysis:
            return
        found_analysis = False
        # search in the active document
        for m in FreeCAD.activeDocument().Objects:
            if femutils.is_of_type(m, "Fem::FemAnalysis"):
                if not found_analysis:
                    self.analysis = m
                    found_analysis = True
                else:
                    self.analysis = None  # more than one analysis
        if self.analysis:
            if FreeCAD.GuiUp:
                FemGui.setActiveAnalysis(self.analysis)

    def find_solver_analysis(self):
        """get the analysis group the solver belongs to"""
        FreeCAD = _import_freecad()
        QtGui, FemGui = _import_gui()

        if self.solver.getParentGroup():
            obj = self.solver.getParentGroup()
            if femutils.is_of_type(obj, "Fem::FemAnalysis"):
                self.analysis = obj
                if FreeCAD.GuiUp:
                    FemGui.setActiveAnalysis(self.analysis)

    def find_solver(self):
        FreeCAD = _import_freecad()

        found_solver_for_use = False
        for m in self.analysis.Group:
            if femutils.is_of_type(m, "Fem::SolverOpenRadioss"):
                # we are going to explicitly check for the ccx tools solver type only,
                # thus it is possible to have lots of framework solvers inside the analysis anyway
                # for some methods no solver is needed (purge_results) --> solver could be none
                # analysis has one solver and no solver was set --> use the one solver
                # analysis has more than one solver and no solver was set --> use solver none
                # analysis has no solver --> use solver none
                if not found_solver_for_use:
                    # no solver was found before
                    self.solver = m
                    found_solver_for_use = True
                else:
                    # another solver was found --> We have more than one solver
                    # we do not know which one to use, so we use none !
                    self.solver = None
                    FreeCAD.Console.PrintLog(
                        "FEM: More than one solver in the analysis "
                        "and no solver given to analyze. "
                        "No solver is set!\n"
                    )

    def update_objects(self):
        FreeCAD.Console.PrintMessage("=== FemToolsOR.update_objects() starting ===\n")
        ## @var mesh
        #  mesh for the analysis
        self.mesh = None
        FreeCAD.Console.PrintMessage(f"  - Getting mesh for analysis: {self.analysis.Label if self.analysis else 'None'}\n")
        mesh, message = membertools.get_mesh_to_solve(self.analysis)
        if mesh is not None:
            self.mesh = mesh
            FreeCAD.Console.PrintMessage(f"  - Mesh found: {mesh.Label}\n")
        else:
            # the prerequisites will run anyway and they will print a message box anyway
            # thus do not print one here, but print a console warning
            FreeCAD.Console.PrintWarning(f"{message} The prerequisite check will fail.\n")

        ## @var members
        # members of the analysis. All except the solver and the mesh
        FreeCAD.Console.PrintMessage("  - Getting analysis members...\n")
        self.member = membertools.AnalysisMember(self.analysis)
        FreeCAD.Console.PrintMessage(f"  - Members found: {len(self.member.members)} objects\n")
        FreeCAD.Console.PrintMessage("=== FemToolsOR.update_objects() completed ===\n")

    def check_prerequisites(self):
        FreeCAD.Console.PrintMessage("=== FemToolsOR.check_prerequisites() starting ===\n")
        FreeCAD.Console.PrintMessage("\n")  # because of time print in separate line
        FreeCAD.Console.PrintMessage("Check prerequisites...\n")
        message = ""
        # analysis
        FreeCAD.Console.PrintMessage(f"  - Checking analysis: {self.analysis.Label if self.analysis else 'None'}\n")
        if not self.analysis:
            message += "No active Analysis\n"
        # solver
        FreeCAD.Console.PrintMessage(f"  - Checking solver: {self.solver.Label if self.solver else 'None'}\n")
        if not self.solver:
            message += "No solver object defined in the analysis\n"
        if not self.working_dir:
            message += "Working directory not set\n"
        if not os.path.isdir(self.working_dir):
            message += f"Working directory '{self.working_dir}' doesn't exist."
        from femtools.checksanalysis import check_member_for_solver_calculix

        FreeCAD.Console.PrintMessage("  - Running member checks...\n")
        message += check_member_for_solver_calculix(
            self.analysis, self.solver, self.mesh, self.member
        )
        FreeCAD.Console.PrintMessage(f"  - Prerequisites check result: {message if message else 'All checks passed'}\n")
        FreeCAD.Console.PrintMessage("=== FemToolsOR.check_prerequisites() completed ===\n")
        return message

    def set_base_name(self, base_name=None):
        """
        Set base_name

        Parameters
        ----------
        base_name : str, optional
            base_name base name of .k/.out file (without extension).
            It is used to construct .k file path that is passed to OpenRadioss
        """
        if base_name is None:
            self.base_name = ""
        else:
            self.base_name = base_name
        # Update k file name
        self.set_k_file_name()

    def set_k_file_name(self, k_file_name=None):
        """
        Set k file name. Normally k file name is set by write_k_file.
        That name is also used to determine location and name of out result file.

        Parameters
        ----------
        k_file_name : str, optional
            input file name path
        """
        if k_file_name is not None:
            self.inp_file_name = k_file_name
        else:
            self.inp_file_name = os.path.join(self.working_dir, (self.base_name + ".k"))

    def setup_working_dir(self, param_working_dir=None, create=False):
        """Set working dir for solver execution.

        Parameters
        ----------
        param_working_dir :  str, optional
            directory to be used for writing
        create : bool, optional
            Should the working directory be created if it does not exist
        """
        FreeCAD = _import_freecad()

        self.working_dir = ""
        # try to use given working dir or overwrite with solver working dir
        fem_general_prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/General")
        if param_working_dir is not None:
            self.working_dir = param_working_dir
            if femutils.check_working_dir(self.working_dir) is not True:
                if create is True:
                    FreeCAD.Console.PrintMessage(
                        f"Dir given as parameter '{self.working_dir}' doesn't exist.\n"
                    )
                else:
                    FreeCAD.Console.PrintError(
                        "Dir given as parameter '{}' doesn't exist "
                        "and create parameter is set to False.\n".format(self.working_dir)
                    )
                    self.working_dir = femutils.get_pref_working_dir(self.solver)
                    FreeCAD.Console.PrintMessage(
                        f"Dir '{self.working_dir}' will be used instead.\n"
                    )
        elif fem_general_prefs.GetBool("OverwriteSolverWorkingDirectory", True) is False:
            self.working_dir = self.solver.WorkingDir
            if femutils.check_working_dir(self.working_dir) is not True:
                if self.working_dir == "":
                    FreeCAD.Console.PrintError(
                        "Working Dir is set to be used from solver object "
                        "but Dir from solver object '{}' is empty.\n".format(self.working_dir)
                    )
                else:
                    FreeCAD.Console.PrintError(
                        f"Dir from solver object '{self.working_dir}' doesn't exist.\n"
                    )
                self.working_dir = femutils.get_pref_working_dir(self.solver)
                FreeCAD.Console.PrintMessage(f"Dir '{self.working_dir}' will be used instead.\n")
        else:
            self.working_dir = femutils.get_pref_working_dir(self.solver)

        # check working_dir exist, if not use a tmp dir and inform the user
        if femutils.check_working_dir(self.working_dir) is not True:
            FreeCAD.Console.PrintError(
                f"Dir '{self.working_dir}' doesn't exist or cannot be created.\n"
            )
            self.working_dir = femutils.get_temp_dir(self.solver)
            FreeCAD.Console.PrintMessage(f"Dir '{self.working_dir}' will be used instead.\n")

        # Update inp file name
        self.set_k_file_name()

    def write_k_file(self):
        FreeCAD = _import_freecad()
        FreeCAD.Console.PrintMessage("=== FemToolsOR.write_k_file() starting ===\n")

        # Write input file
        from femsolver.OpenRadioss import writer as iw

        self.OR_file_name = ""
        FreeCAD.Console.PrintMessage(f"  - Working directory: {self.working_dir}\n")
        FreeCAD.Console.PrintMessage(f"  - Base name: {self.base_name}\n")

        try:
            # Create a minimal member object for the writer
            member = membertools.AnalysisMember(self.analysis)

            # TODO: Enable OpenRadioss writer when ready
            # OR_writer = iw.FemInputWriterCcx(
            #     self.analysis,
            #     self.solver,
            #     self.mesh,
            #     member,
            #     self.working_dir,
            #     [],  # Empty material/geometry sets
            # )
            # self.OR_file_name = OR_writer.write_solver_input()
            # FreeCAD.Console.PrintMessage(f"  - Input file written: {self.OR_file_name}\n")

            # For now, copy the test file to the working directory
            # Use the filename that was set by the solver (don't override it)
            # self.OR_file_name = os.path.join(self.working_dir, "fem_export.k")  # ← REMOVE THIS LINE
            # self.inp_file_name = self.OR_file_name  # Keep them consistent

            # Use the filename that was already set by the solver
            if not self.OR_file_name:
                self.OR_file_name = os.path.join(self.working_dir, "fem_export.k")
                self.inp_file_name = self.OR_file_name

            # Debug: Show what filename we're using
            FreeCAD.Console.PrintMessage(f"  - Target filename: {self.OR_file_name}\n")
            FreeCAD.Console.PrintMessage(f"  - Working directory: {self.working_dir}\n")

            # Copy the test file to the working directory
            test_k_file = "/home/nemo/Dokumente/Sandbox/Fem_upgraded/zug_test3_RS.k"
            import shutil
            if os.path.exists(test_k_file):
                shutil.copy2(test_k_file, self.OR_file_name)
                FreeCAD.Console.PrintMessage(f"  - Using test file: {test_k_file}\n")
                FreeCAD.Console.PrintMessage(f"  - Copied to working directory: {self.OR_file_name}\n")

                # Verify the file was actually created
                if os.path.exists(self.OR_file_name):
                    file_size = os.path.getsize(self.OR_file_name)
                    FreeCAD.Console.PrintMessage(f"  - File successfully created: {self.OR_file_name} ({file_size} bytes)\n")
                else:
                    FreeCAD.Console.PrintError(f"  - ERROR: File was not created at: {self.OR_file_name}\n")
            else:
                FreeCAD.Console.PrintError(f"  - Test file not found: {test_k_file}\n")
                # Create a minimal K-file as fallback
                with open(self.OR_file_name, 'w') as f:
                    f.write("* Test K-file generated by OpenRadioss solver\n")
                    f.write("$ Generated at: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                FreeCAD.Console.PrintMessage(f"  - Created minimal K-file: {self.OR_file_name}\n")

                # Verify fallback file was created
                if os.path.exists(self.OR_file_name):
                    file_size = os.path.getsize(self.OR_file_name)
                    FreeCAD.Console.PrintMessage(f"  - Fallback file successfully created: {self.OR_file_name} ({file_size} bytes)\n")
                else:
                    FreeCAD.Console.PrintError(f"  - ERROR: Fallback file was not created at: {self.OR_file_name}\n")

        except Exception as e:
            FreeCAD.Console.PrintError(
                f"Unexpected error when writing OpenRadioss k file: {str(e)}\n"
            )
            import traceback
            FreeCAD.Console.PrintError(f"Traceback: {traceback.format_exc()}\n")
            raise

        FreeCAD.Console.PrintMessage("=== FemToolsOR.write_k_file() completed ===\n")

    def setup_OR(self, OR_binary=None, OR_binary_sig="OpenRadioss"):
        FreeCAD = _import_freecad()
        QtGui, FemGui = _import_gui()

        """Set Calculix binary path and validate its execution.

        Parameters
        ----------
        OR_binary : str, optional
            It defaults to `None`. The path to the `ccx` binary. If it is `None`,
            the path is guessed.
        OR_binary_sig : str, optional
            Defaults to 'OpenRadioss'. Expected output from `ccx` when run empty.

        """
        error_title = "No or wrong OpenRadioss binary"
        error_message = ""
        from platform import system

        FreeCAD.Console.PrintMessage(f"  - OR_binary parameter: {OR_binary}\n")
        FreeCAD.Console.PrintMessage(f"  - Platform: {system()}\n")

        # Check for explicitly provided binary
        if OR_binary and os.path.isfile(OR_binary):
            FreeCAD.Console.PrintMessage(f"  - Using provided binary: {OR_binary}\n")
            self.OR_binary = OR_binary
            self.OR_binary_present = True
            FreeCAD.Console.PrintMessage("=== FemToolsOR.setup_OR() completed ===\n")
            return

        # Try to get binary from FreeCAD settings
        from femsolver.settings import get_binary

        binary_path = get_binary("OpenRadioss")
        FreeCAD.Console.PrintMessage(f"  - Binary path from settings: {binary_path}\n")

        if binary_path and os.path.isfile(binary_path):
            FreeCAD.Console.PrintMessage(f"  - Using settings binary: {binary_path}\n")
            self.OR_binary = binary_path
            self.OR_binary_present = True
            FreeCAD.Console.PrintMessage("=== FemToolsOR.setup_OR() completed ===\n")
            return

        # Try standard locations as fallback
        if system() == "Windows":
            default_path = os.path.join(FreeCAD.getHomePath(), "OpenRadioss_linux64", "OpenRadioss", "exec", "engine_linux64_gf")
        else:
            default_path = "/opt/OpenRadioss/exec/engine_linux64_gf"

        FreeCAD.Console.PrintMessage(f"  - Checking default path: {default_path}\n")
        if os.path.isfile(default_path):
            FreeCAD.Console.PrintMessage(f"  - Found binary at default path: {default_path}\n")
            self.OR_binary = default_path
            self.OR_binary_present = True

            # Save to settings for future use
            from femsolver.settings import _SolverDlg
            param_group = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/OpenRadioss")
            param_group.SetString("openRadiossEngineBinaryPath", default_path)
            param_group.SetBool("UseStandardOpenRadiossEngineLocation", False)

            FreeCAD.Console.PrintMessage("=== FemToolsOR.setup_OR() completed ===\n")
            return

        # Binary not found
        self.OR_binary_present = False
        error_message = (
            "OpenRadioss binary not found. Please set the path in "
            "Edit → Preferences → FEM → OpenRadioss"
        )
        FreeCAD.Console.PrintError(f"{error_title}: {error_message}\n")
        if FreeCAD.GuiUp:
            QtWidgets.QMessageBox.critical(None, error_title, error_message)
        raise RuntimeError(error_message)

    def start_OR(self):
        import multiprocessing

        self.OR_stdout = ""
        self.OR_stderr = ""
        ont_backup = os.environ.get("OMP_NUM_THREADS")
        self.ccx_prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/Ccx")
        # If number of CPU's specified
        num_cpu_pref = self.ccx_prefs.GetInt("AnalysisNumCPUs", 1)
        if not ont_backup:
            ont_backup = str(num_cpu_pref)
        if num_cpu_pref > 1:
            # If user picked a number use that instead
            os.environ["OMP_NUM_THREADS"] = str(num_cpu_pref)
        else:
            os.environ["OMP_NUM_THREADS"] = str(multiprocessing.cpu_count())

        # Set OpenRadioss specific environment variables
        or_base_dir = "/home/nemo/Dokumente/Software/OpenRadioss_linux64"
        os.environ["OPENRADIOSS_PATH"] = or_base_dir
        os.environ["RAD_CFG_PATH"] = f"{or_base_dir}/OpenRadioss/hm_cfg_files"
        os.environ["RAD_H3D_PATH"] = f"{or_base_dir}/OpenRadioss/extlib/h3d/lib/linux64"
        os.environ["LD_LIBRARY_PATH"] = f"{or_base_dir}/OpenRadioss/extlib/hm_reader/linux64:{or_base_dir}/OpenRadioss/extlib/h3d/lib/linux64:{os.environ.get('LD_LIBRARY_PATH', '')}"

        # change cwd because ccx may crash if directory has no write permission
        # there is also a limit of the length of file names so jump to the document directory
        cwd = QtCore.QDir.currentPath()
        f = QtCore.QFileInfo(self.inp_file_name)
        QtCore.QDir.setCurrent(f.path())
        p = subprocess.Popen(
            [self.OR_binary, "-i ", f.baseName()],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            env=os.environ.copy(),  # Pass the modified environment to subprocess
        )
        self.OR_stdout, self.OR_stderr = p.communicate()
        self.OR_stdout = self.OR_stdout.decode()
        self.OR_stderr = self.OR_stderr.decode()
        # Restore original environment
        if ont_backup:
            os.environ["OMP_NUM_THREADS"] = ont_backup
        else:
            os.environ.pop("OMP_NUM_THREADS", None)
        QtCore.QDir.setCurrent(cwd)
        return p.returncode

    def get_OR_version(self):
        self.setup_OR()
        import re
        from platform import system

        OR_stdout = None
        OR_stderr = None

        # Set up environment for version check
        or_base_dir = "/home/nemo/Dokumente/Software/OpenRadioss_linux64"
        os.environ["OPENRADIOSS_PATH"] = or_base_dir
        os.environ["RAD_CFG_PATH"] = f"{or_base_dir}/OpenRadioss/hm_cfg_files"
        os.environ["RAD_H3D_PATH"] = f"{or_base_dir}/OpenRadioss/extlib/h3d/lib/linux64"
        os.environ["LD_LIBRARY_PATH"] = f"{or_base_dir}/OpenRadioss/extlib/hm_reader/linux64:{or_base_dir}/OpenRadioss/extlib/h3d/lib/linux64:{os.environ.get('LD_LIBRARY_PATH', '')}"

        # Now extract the version number
        p = subprocess.Popen(
            [self.OR_binary, "-v"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            startupinfo=femutils.startProgramInfo(""),
            env=os.environ.copy(),  # Pass the modified environment
        )
        OR_stdout, OR_stderr = p.communicate()
        OR_stdout = OR_stdout.decode()
        m = re.search(r"(\d+).(\d+)", OR_stdout)
        return (int(m.group(1)), int(m.group(2)))

    def OR_run(self):
        FreeCAD = _import_freecad()
        QtGui, FemGui = _import_gui()

        ret_code = None
        FreeCAD.Console.PrintMessage("\n")  # because of time print in separate line
        FreeCAD.Console.PrintMessage("OpenRadioss solver run...\n")
        if self.test_mode:
            FreeCAD.Console.PrintError("OpenRadioss can not be run if test_mode is True.\n")
            return
        self.setup_OR()
        if self.OR_binary_present is False:
            error_message = (
                "FEM: OpenRadioss binary engine_linux64_gf '{}' not found. "
                "Please set the OpenRadioss binary engine_linux64_gf path in FEM preferences tab OpenRadioss.\n".format(
                    self.OR_binary
                )
            )
            if FreeCAD.GuiUp:
                QtGui.QMessageBox.critical(None, "No OpenRadioss binary engine_linux64_gf", error_message)
            return
        progress_bar = FreeCAD.Base.ProgressIndicator()
        progress_bar.start("Everything seems fine. OpenRadioss engine_linux64_gf will be executed ...", 0)
        ret_code = self.start_OR()
        self.finished.emit(ret_code)
        progress_bar.stop()
        if ret_code or self.OR_stderr:
            if ret_code == 201 and self.solver.AnalysisType == "check":
                FreeCAD.Console.PrintMessage(
                    "It seems we run into NOANALYSIS problem, "
                    "thus workaround for wrong exit code for *NOANALYSIS check "
                    "and set ret_code to 0.\n"
                )
                # https://forum.freecad.org/viewtopic.php?f=18&t=31303&start=10#p260743
                ret_code = 0
            else:
                FreeCAD.Console.PrintError(f"OpenRadioss failed with exit code {ret_code}\n")
                FreeCAD.Console.PrintMessage("--------start of stderr-------\n")
                FreeCAD.Console.PrintMessage(self.OR_stderr)
                FreeCAD.Console.PrintMessage("--------end of stderr---------\n")
                FreeCAD.Console.PrintMessage("--------start of stdout-------\n")
                FreeCAD.Console.PrintMessage(self.OR_stdout)
                FreeCAD.Console.PrintMessage("\n--------end of stdout---------\n")
                FreeCAD.Console.PrintMessage("--------start problems---------\n")
                self.has_no_material_assigned()
                self.has_nonpositive_jacobians()
                FreeCAD.Console.PrintMessage("\n--------end problems---------\n")
        else:
            # remove highlighted nodes, if any
            if FreeCAD.GuiUp:
                self.mesh.ViewObject.HighlightedNodes = []

            FreeCAD.Console.PrintMessage("OpenRadioss finished without error.\n")

            # Load results and launch ParaView if successful
            self.load_results()
            if self.results_present and self.should_launch_paraview():
                FreeCAD.Console.PrintMessage("Results loaded successfully. Launching ParaView...\n")
                self.launch_paraview()
            elif self.results_present:
                FreeCAD.Console.PrintMessage("Results loaded successfully. ParaView launch disabled by user preference.\n")
                # Generate bash command for manual ParaView launch
                self._generate_paraview_command()
        return ret_code

    def run(self):
        FreeCAD = _import_freecad()
        QtGui, FemGui = _import_gui()

        self.update_objects()
        self.setup_working_dir()
        message = self.check_prerequisites()
        if message:
            text = "OpenRadioss can not be started due to missing prerequisites:\n"
            error_app = f"{text}{message}"
            error_gui = f"{text}\n{message}"
            FreeCAD.Console.PrintError(error_app)
            if FreeCAD.GuiUp:
                QtGui.QMessageBox.critical(None, "Missing prerequisite", error_gui)
            return False
        else:
            self.write_k_file()
            if self.inp_file_name == "":
                error_message = "Error on writing OpenRadioss k file.\n"
                FreeCAD.Console.PrintError(error_message)
                if FreeCAD.GuiUp:
                    QtGui.QMessageBox.critical(None, "Error", error_message)
                return False
            else:
                FreeCAD.Console.PrintLog("Writing OpenRadioss k file completed.\n")
                ret_code = self.OR_run()
                if ret_code is None:
                    error_message = "OpenRadioss has not been run. The OpenRadioss binary search returned: {}.\n".format(
                        self.OR_binary_present
                    )
                    FreeCAD.Console.PrintError(error_message)
                    if FreeCAD.GuiUp:
                        QtGui.QMessageBox.critical(None, "Error", error_message)
                    return False
                if ret_code != 0:
                    error_message = f"OpenRadioss finished with error {ret_code}.\n"
                    FreeCAD.Console.PrintError(error_message)
                    if FreeCAD.GuiUp:
                        QtGui.QMessageBox.critical(None, "Error", error_message)
                    return False
                else:
                    FreeCAD.Console.PrintLog("Try to read result files\n")
                    self.load_results()

                    # Launch ParaView if results were loaded successfully and user preference is enabled
                    if self.results_present and self.should_launch_paraview():
                        FreeCAD.Console.PrintMessage("Results loaded successfully. Launching ParaView...\n")
                        self.launch_paraview()
                    elif self.results_present:
                        FreeCAD.Console.PrintMessage("Results loaded successfully. ParaView launch disabled by user preference.\n")
                        # Generate bash command for manual ParaView launch
                        self._generate_paraview_command()
                    else:
                        FreeCAD.Console.PrintMessage("No results loaded or ParaView launch disabled.\n")
        return True
    
    def has_no_material_assigned(self):
        FreeCAD = _import_freecad()

        if " *ERROR in calinput: no material was assigned" in self.OR_stdout:
            without_material_elements = []
            without_material_elemnodes = []
            for line in self.OR_stdout.splitlines():
                if "to element" in line:
                    # print(line)
                    # print(line.split())
                    non_mat_ele = int(line.split()[2])
                    # print(non_mat_ele)
                    if non_mat_ele not in without_material_elements:
                        without_material_elements.append(non_mat_ele)
            for e in without_material_elements:
                for n in self.mesh.FemMesh.getElementNodes(e):
                    without_material_elemnodes.append(n)
            without_material_elements = sorted(without_material_elements)
            without_material_elemnodes = sorted(without_material_elemnodes)
            command_for_withoutmatnodes = "without_material_elemnodes = {}".format(
                without_material_elemnodes
            )
            command_to_highlight = (
                "Gui.ActiveDocument.{}.HighlightedNodes = without_material_elemnodes".format(
                    self.mesh.Name
                )
            )
            # some output for the user
            FreeCAD.Console.PrintError(
                "\n\nOpenRadioss returned an error due to elements without materials.\n"
            )
            FreeCAD.Console.PrintMessage(
                f"without_material_elements = {without_material_elements}\n"
            )
            FreeCAD.Console.PrintMessage(command_for_withoutmatnodes + "\n")
            if FreeCAD.GuiUp:
                import FreeCADGui

                # with this the list without_material_elemnodes
                # will be available for further user interaction
                FreeCADGui.doCommand(command_for_withoutmatnodes)
                FreeCAD.Console.PrintMessage("\n")
                FreeCADGui.doCommand(command_to_highlight)
            FreeCAD.Console.PrintMessage(
                "\nFollowing some commands to copy. "
                "They will highlight the elements without materials "
                "or to reset the highlighted nodes:\n"
            )
            FreeCAD.Console.PrintMessage(command_to_highlight + "\n")
            # command to reset the Highlighted Nodes
            FreeCAD.Console.PrintMessage(
                f"Gui.ActiveDocument.{self.mesh.Name}.HighlightedNodes = []\n\n"
            )
            return True
        else:
            return False

    def has_nonpositive_jacobians(self):
        if "*ERROR in e_c3d: nonpositive jacobian" in self.OR_stdout:
            nonpositive_jacobian_elements = []
            nonpositive_jacobian_elenodes = []
            for line in self.OR_stdout.splitlines():
                if "determinant in element" in line:
                    # print(line)
                    # print(line.split())
                    non_posjac_ele = int(line.split()[3])
                    # print(non_posjac_ele)
                    if non_posjac_ele not in nonpositive_jacobian_elements:
                        nonpositive_jacobian_elements.append(non_posjac_ele)
            for e in nonpositive_jacobian_elements:
                for n in self.mesh.FemMesh.getElementNodes(e):
                    nonpositive_jacobian_elenodes.append(n)
            nonpositive_jacobian_elements = sorted(nonpositive_jacobian_elements)
            nonpositive_jacobian_elenodes = sorted(nonpositive_jacobian_elenodes)
            command_for_nonposjacnodes = "nonpositive_jacobian_elenodes = {}".format(
                nonpositive_jacobian_elenodes
            )
            command_to_highlight = (
                "Gui.ActiveDocument.{}.HighlightedNodes = nonpositive_jacobian_elenodes".format(
                    self.mesh.Name
                )
            )
            # some output for the user
            FreeCAD.Console.PrintError(
                "\n\nOpenRadioss returned an error due to nonpositive jacobian elements.\n"
            )
            FreeCAD.Console.PrintMessage(
                f"nonpositive_jacobian_elements = {nonpositive_jacobian_elements}\n"
            )
            FreeCAD.Console.PrintMessage(command_for_nonposjacnodes + "\n")
            if FreeCAD.GuiUp:
                import FreeCADGui

                # with this the list nonpositive_jacobian_elenodes
                # will be available for further user interaction
                FreeCADGui.doCommand(command_for_nonposjacnodes)
                FreeCAD.Console.PrintMessage("\n")
                FreeCADGui.doCommand(command_to_highlight)
            FreeCAD.Console.PrintMessage(
                "\nFollowing some commands to copy. "
                "They highlight the nonpositive jacobians "
                "or to reset the highlighted nodes:\n"
            )
            FreeCAD.Console.PrintMessage(command_to_highlight + "\n")
            # command to reset the Highlighted Nodes
            FreeCAD.Console.PrintMessage(
                f"Gui.ActiveDocument.{self.mesh.Name}.HighlightedNodes = []\n\n"
            )
            return True
        else:
            return False

    def load_results(self):
        FreeCAD = _import_freecad()

        FreeCAD.Console.PrintMessage("\n")  # because of time print in separate line
        FreeCAD.Console.PrintMessage("OpenRadioss read results...\n")
        self.results_present = False
        self.load_results_ORfrd()
        self.load_results_ORdat()
        self.analysis.Document.recompute()

    def load_results_ORfrd(self):
        """Load results of OpenRadioss calculations from .frd file."""
        FreeCAD = _import_freecad()

        import feminout.importCcxFrdResults as importCcxFrdResults

        frd_result_file = os.path.splitext(self.inp_file_name)[0] + ".frd"
        if os.path.isfile(frd_result_file):
            importCcxFrdResults.importFrd(
                frd_result_file, self.analysis, "OR_", self.solver.AnalysisType
            )
            for m in self.analysis.Group:
                if m.isDerivedFrom("Fem::FemResultObject"):
                    self.results_present = True
                    break
            else:
                if self.solver.AnalysisType == "check":
                    for m in self.analysis.Group:
                        if m.isDerivedFrom("Fem::FemMeshObjectPython"):
                            # we have no result object but a mesh object
                            # this happens in NOANALYSIS mode
                            break
                else:
                    FreeCAD.Console.PrintError("FEM: No result object in active Analysis.\n")
        else:
            FreeCAD.Console.PrintError(f"FEM: No frd result file found at {frd_result_file}\n")

    def load_results_ORdat(self):
        """Load results of OpenRadioss calculations from .dat file."""
        FreeCAD = _import_freecad()

        import feminout.importORDatResults as importORDatResults

        dat_result_file = os.path.splitext(self.inp_file_name)[0] + ".dat"
        mode_frequencies = None
        dat_content = None

        if os.path.isfile(dat_result_file):
            mode_frequencies = importORDatResults.import_dat(dat_result_file, self.analysis)

            dat_file = open(dat_result_file)
            dat_content = dat_file.read()
            dat_file.close()
        else:
            FreeCAD.Console.PrintError(f"FEM: No dat result file found at {dat_result_file}\n")

        if mode_frequencies:
            # print(mode_frequencies)
            for m in self.analysis.Group:
                if m.isDerivedFrom("Fem::FemResultObject") and m.Eigenmode > 0:
                    for mf in mode_frequencies:
                        if m.Eigenmode == mf["eigenmode"]:
                            m.EigenmodeFrequency = mf["frequency"]

        if dat_content:
            # print(dat_content)
            dat_text_obj = self.analysis.Document.addObject("App::TextDocument", "OR_dat_file")
            dat_text_obj.Text = dat_content
            dat_text_obj.setPropertyStatus("Text", "ReadOnly")  # set property editor readonly
            if FreeCAD.GuiUp:
                dat_text_obj.ViewObject.ReadOnly = True  # set editor view readonly
            self.analysis.addObject(dat_text_obj)

    def launch_paraview(self):
        """Launch ParaView to visualize OpenRadioss results."""
        FreeCAD = _import_freecad()

        try:
            # Check if ParaView is available in the system PATH
            import subprocess
            import shutil

            # Look for ParaView executable
            paraview_exe = None

            # Try common ParaView executable names and locations
            possible_executables = [
                "paraview",
                "ParaView",
                "/usr/bin/paraview",
                "/usr/local/bin/paraview",
                "/opt/paraview/bin/paraview",
                "/Applications/ParaView.app/Contents/bin/paraview",  # macOS
                "C:\\Program Files\\ParaView\\bin\\paraview.exe",  # Windows
                "C:\\Program Files (x86)\\ParaView\\bin\\paraview.exe",  # Windows 32-bit
            ]

            for exe in possible_executables:
                if shutil.which(exe) or (exe.endswith('.exe') and os.path.exists(exe)):
                    paraview_exe = exe
                    break

            if not paraview_exe:
                FreeCAD.Console.PrintWarning("ParaView executable not found in system PATH. Please install ParaView or add it to your PATH.\n")
                return False

            # Check if we have result files to visualize
            result_files = []
            base_name = os.path.splitext(self.inp_file_name)[0]

            # Look for common OpenRadioss result files
            result_extensions = ['.frd', '.dat', '.h3d', '.t01', '.t02', '.t03', '.t04']
            for ext in result_extensions:
                result_file = base_name + ext
                if os.path.exists(result_file):
                    result_files.append(result_file)

            if not result_files:
                FreeCAD.Console.PrintWarning("No OpenRadioss result files found for ParaView visualization.\n")
                return False

            # Launch ParaView with the result files
            FreeCAD.Console.PrintMessage(f"Launching ParaView with {len(result_files)} result files...\n")

            # Build command to open ParaView with result files
            cmd = [paraview_exe] + result_files

            # Launch ParaView in background
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            FreeCAD.Console.PrintMessage(f"ParaView launched with files: {', '.join(result_files)}\n")
            return True

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error launching ParaView: {str(e)}\n")
            return False

    def should_launch_paraview(self):
        """Check if ParaView should be launched based on user preferences."""
        FreeCAD = _import_freecad()

        try:
            # Check user preferences for ParaView integration using settings module
            from femsolver.settings import get_launch_paraview
            launch_paraview = get_launch_paraview("OpenRadioss")

            # Also check solver-specific setting
            if hasattr(self.solver, 'LaunchParaView'):
                launch_paraview = self.solver.LaunchParaView

            return launch_paraview if launch_paraview is not None else True

        except Exception:
            # Default to True if preference doesn't exist
            return True

    def _generate_paraview_command(self):
        """Generate bash command for manual ParaView launch."""
        FreeCAD = _import_freecad()

        try:
            # Generate bash command for users to copy and paste
            base_name = os.path.splitext(self.inp_file_name)[0]
            working_dir = os.path.dirname(self.inp_file_name)

            # Build command to find and launch ParaView
            command = f'''#!/bin/bash
# OpenRadioss ParaView Launcher Command
# Copy and paste this command in terminal from: {working_dir}

cd "{working_dir}"
PARAVIEW=$(command -v paraview || command -v ParaView || echo "paraview")
if command -v "$PARAVIEW" >/dev/null 2>&1; then
    echo "Found ParaView: $PARAVIEW"
    FILES=("{base_name}.frd" "{base_name}.dat" "{base_name}.h3d")
    FOUND_FILES=()
    for file in "${{FILES[@]}}"; do
        [ -f "$file" ] && FOUND_FILES+=("$file")
    done
    if [ ${{#FOUND_FILES[@]}} -gt 0 ]; then
        echo "Found result files: ${{FOUND_FILES[*]}}"
        "$PARAVIEW" "${{FOUND_FILES[@]}}" &
        echo "ParaView launched with ${{#FOUND_FILES[@]}} result files"
    else
        echo "No result files found"
    fi
else
    echo "ParaView not found in PATH"
fi
'''

            FreeCAD.Console.PrintMessage("\n" + "="*60 + "\n")
            FreeCAD.Console.PrintMessage("📋 COPY AND PASTE THIS BASH COMMAND:\n")
            FreeCAD.Console.PrintMessage("="*60 + "\n")
            FreeCAD.Console.PrintMessage(command)
            FreeCAD.Console.PrintMessage("="*60 + "\n")
            FreeCAD.Console.PrintMessage("💡 Instructions:\n")
            FreeCAD.Console.PrintMessage("   1. Copy the command above\n")
            FreeCAD.Console.PrintMessage("   2. Paste it in a terminal\n")
            FreeCAD.Console.PrintMessage("   3. Run it to launch ParaView with results\n")
            FreeCAD.Console.PrintMessage("="*60 + "\n")

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error generating ParaView command: {str(e)}\n")


class ORTools(FemToolsOR):

    def __init__(self, solver=None):
        FemToolsOR.__init__(self, None, solver)

    def launch_paraview_with_results(self):
        """Manually launch ParaView with current analysis results."""
        FreeCAD = _import_freecad()

        if not self.analysis:
            FreeCAD.Console.PrintError("No analysis available.\n")
            return False

        if not self.inp_file_name:
            FreeCAD.Console.PrintError("No input file available.\n")
            return False

        FreeCAD.Console.PrintMessage("Manually launching ParaView with analysis results...\n")

        # Check if results are already loaded
        if hasattr(self, 'results_present') and self.results_present:
            return self.launch_paraview()
        else:
            # Try to load results first
            self.load_results()
            if self.results_present:
                return self.launch_paraview()
            else:
                FreeCAD.Console.PrintWarning("No results available to visualize in ParaView.\n")
                return False


##  @}
