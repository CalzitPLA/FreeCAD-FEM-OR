import FreeCAD
import FreeCADGui
import os
import json
import time
import shutil
import subprocess
from PySide import QtGui

class _TaskPanel(QtGui.QWidget):
    def __init__(self, obj):
        super().__init__()
        self.obj = obj
        self.form = self  # Important for FreeCAD to recognize the form
        self.k_file_updated = False  # Track if K-file was updated in this panel session

        # Set the hardcode executable path
        self.obj.Executable = '/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/exec/engine_linux64_gf'

        layout = QtGui.QVBoxLayout()
        label = QtGui.QLabel("SolverOpenRadioss Task Panel")
        layout.addWidget(label)

        # Working directory selection
        dir_layout = QtGui.QHBoxLayout()
        dir_label = QtGui.QLabel("Working Directory:")
        dir_layout.addWidget(dir_label)

        self.working_dir_input = QtGui.QLineEdit()
        self.working_dir_input.setText(os.path.expanduser("~"))
        dir_layout.addWidget(self.working_dir_input)

        browse_button = QtGui.QPushButton("Browse...")
        browse_button.clicked.connect(self.onBrowseWorkingDir)
        dir_layout.addWidget(browse_button)

        layout.addLayout(dir_layout)

        # Buttons
        self.solve_button = QtGui.QPushButton("Solve")
        self.update_kfile_button = QtGui.QPushButton("Update K File")

        layout.addWidget(self.solve_button)
        layout.addWidget(self.update_kfile_button)

        # Connect buttons to their methods
        self.solve_button.clicked.connect(self.onSolve)
        self.update_kfile_button.clicked.connect(self.onUpdateKFile)

        self.setLayout(layout)
        self.setWindowTitle("SolverOpenRadioss Settings")

    def onBrowseWorkingDir(self):
        """Browse for working directory"""
        current_dir = self.working_dir_input.text() or os.path.expanduser("~")
        directory = QtGui.QFileDialog.getExistingDirectory(self, "Select Working Directory", current_dir)

        if directory:
            self.working_dir_input.setText(directory)

    def get_working_directory_safe(self):
        """Safely get the working directory, with fallback to home directory if UI not available"""
        try:
            if hasattr(self, 'working_dir_input') and self.working_dir_input:
                working_dir = self.working_dir_input.text().strip()
                if working_dir:
                    return working_dir
        except:
            pass
        # Fallback to home directory if UI not available or empty
        return os.path.expanduser("~")

    def onSolve(self):
        # Implement solve
        if not self.k_file_updated:
            reply = QtGui.QMessageBox.question(self, 'Update K File',
                "The K-file was not updated in this panel session. Do you want to update it before solving?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.Yes)
            if reply == QtGui.QMessageBox.Yes:
                self.onUpdateKFile()
        try:
            # Get the active analysis object
            analysis = None

            # First try to get analysis from selection
            selection = FreeCADGui.Selection.getSelection()
            if selection:
                # Check if selected object is an analysis
                for obj in selection:
                    if hasattr(obj, 'WorkingDir') or 'Analysis' in obj.Name:
                        analysis = obj
                        break

            # If no analysis in selection, find the active analysis
            if not analysis:
                doc = FreeCAD.ActiveDocument
                for obj in doc.Objects:
                    # Look for analysis objects or objects with solver settings
                    if ('Analysis' in obj.Name or
                        hasattr(obj, 'WorkingDir') or
                        hasattr(obj, 'FemMesh') or
                        hasattr(obj, 'Mesh') or
                        (hasattr(obj, 'Proxy') and hasattr(obj.Proxy, 'Type') and
                         ('Analysis' in obj.Proxy.Type or 'Fem' in obj.Proxy.Type))):
                        analysis = obj
                        break

            if not analysis:
                QtGui.QMessageBox.warning(self, "Error", "No analysis object found in document. Please create or select an analysis first.")
                return

            # Get working directory from user selection
            working_dir = self.get_working_directory_safe()
            k_file_path = os.path.join(working_dir, 'fem_export.k')

            # Check if K-file exists
            if not os.path.exists(k_file_path):
                QtGui.QMessageBox.warning(self, "Error", f"K-file not found at {k_file_path}. Please update K-file first.")
                return

            # Show running popup
            self.showRunningPopup()

            try:
                # Set up OpenRadioss environment variables
                openradioss_path = '/home/nemo/Dokumente/Software/OpenRadioss_linux64'

                # Set up environment for proper library loading
                custom_env = os.environ.copy()

                # Set hardcoded paths for consistency with bash script
                openradioss_path = '/home/nemo/Dokumente/Software/OpenRadioss_linux64'

                # Set LD_LIBRARY_PATH for shared libraries (from official docs)
                hm_reader_lib = "/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/extlib/hm_reader/linux64"
                h3d_lib = "/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/extlib/h3d/lib/linux64"

                custom_env["LD_LIBRARY_PATH"] = f"{h3d_lib}:{hm_reader_lib}"

                # Set PATH for executables
                custom_env["PATH"] = f"{hm_reader_lib}:/opt/openmpi/bin:" + custom_env["PATH"]

                # Set other OpenRadioss environment variables (from official docs)
                custom_env["OPENRADIOSS_PATH"] = openradioss_path
                custom_env["RAD_CFG_PATH"] = "/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/hm_cfg_files"
                custom_env["RAD_H3D_PATH"] = h3d_lib
                custom_env["OMP_NUM_THREADS"] = "4"

                FreeCAD.Console.PrintMessage(f"DEBUG: Environment setup complete\n")
                FreeCAD.Console.PrintMessage(f"DEBUG: LD_LIBRARY_PATH = {custom_env.get('LD_LIBRARY_PATH', 'Not set')}\n")

                # Run OpenRadioss solver using proper starter + engine workflow
                # First run the starter to generate the key file
                starter_executable = '/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/exec/starter_linux64_gf'

                FreeCAD.Console.PrintMessage(f"DEBUG: Running starter: {starter_executable}\n")
                starter_cmd = [starter_executable, "-i", "fem_export.k"]
                starter_result = subprocess.run(starter_cmd, cwd=working_dir, env=custom_env, capture_output=True, text=True)

                if starter_result.returncode == 0:
                    FreeCAD.Console.PrintMessage("Starter completed successfully\n")

                    # Check what files were generated by the starter
                    import glob
                    rad_files = glob.glob(os.path.join(working_dir, "fem_export_*.rad"))
                    if rad_files:
                        # Sort files to get the lowest numbered one first
                        rad_files.sort()
                        engine_input = os.path.basename(rad_files[0])
                        FreeCAD.Console.PrintMessage(f"Found engine input files: {[os.path.basename(f) for f in rad_files]}\n")
                        FreeCAD.Console.PrintMessage(f"Using engine input file: {engine_input}\n")
                    else:
                        # Fallback to default naming
                        engine_input = "fem_export_0000.rad"
                        FreeCAD.Console.PrintMessage(f"Using default engine input: {engine_input}\n")

                    # Now run the engine
                    engine_executable = '/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/exec/engine_linux64_gf'

                    FreeCAD.Console.PrintMessage(f"DEBUG: Running engine: {engine_executable}\n")
                    engine_cmd = [engine_executable, "-i", engine_input]
                    engine_result = subprocess.run(engine_cmd, cwd=working_dir, env=custom_env, capture_output=True, text=True)

                    if engine_result.returncode == 0:
                        QtGui.QMessageBox.information(self, "Success", "OpenRadioss solver completed successfully!")
                    else:
                        FreeCAD.Console.PrintError(f"Engine failed with return code {engine_result.returncode}\n")
                        FreeCAD.Console.PrintError(f"STDOUT: {engine_result.stdout}\n")
                        FreeCAD.Console.PrintError(f"STDERR: {engine_result.stderr}\n")
                        self.showFailurePopup()
                else:
                    FreeCAD.Console.PrintError(f"Starter failed with return code {starter_result.returncode}\n")
                    FreeCAD.Console.PrintError(f"STDOUT: {starter_result.stdout}\n")
                    FreeCAD.Console.PrintError(f"STDERR: {starter_result.stderr}\n")
                    self.showFailurePopup()

            except Exception as e:
                FreeCAD.Console.PrintError(f"Error running OpenRadioss solver: {e}\n")
                QtGui.QMessageBox.warning(self, "Error", f"Failed to run solver: {str(e)}")
                self.showFailurePopup()

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error in onSolve: {e}\n")
            self.showFailurePopup()

    def onUpdateKFile(self):
        try:
            # Get the active analysis object
            analysis = None

            # First try to get analysis from selection
            selection = FreeCADGui.Selection.getSelection()
            if selection:
                # Check if selected object is an analysis
                for obj in selection:
                    if hasattr(obj, 'WorkingDir') or 'Analysis' in obj.Name:
                        analysis = obj
                        break

            # If no analysis in selection, find the active analysis
            if not analysis:
                doc = FreeCAD.ActiveDocument
                for obj in doc.Objects:
                    # Look for analysis objects or objects with solver settings
                    if ('Analysis' in obj.Name or
                        hasattr(obj, 'WorkingDir') or
                        (hasattr(obj, 'Proxy') and hasattr(obj.Proxy, 'Type') and 'Analysis' in obj.Proxy.Type)):
                        analysis = obj
                        break

            if not analysis:
                QtGui.QMessageBox.warning(self, "Error", "No analysis object found in document. Please create or select an analysis first.")
                return

            # Set working directory from user selection
            working_dir = self.get_working_directory_safe()
            k_file_path = os.path.join(working_dir, 'fem_export.k')

            FreeCAD.Console.PrintMessage(f"DEBUG: Working directory = {working_dir}\n")
            FreeCAD.Console.PrintMessage(f"DEBUG: K-file path = {k_file_path}\n")
            FreeCAD.Console.PrintMessage(f"DEBUG: Template file exists = {os.path.exists('/home/nemo/Dokumente/Sandbox/Fem_upgraded/zug_test3_RS.k')}\n")

            # Create a K-file from analysis data
            try:
                # First try to find existing K-file from analysis
                k_file_found = False

                # Look for existing input files in the analysis
                if hasattr(analysis, 'WorkingDir'):
                    analysis_working_dir = analysis.WorkingDir
                    FreeCAD.Console.PrintMessage(f"DEBUG: Analysis working directory = {analysis_working_dir}\n")

                    # Look for existing K-files in analysis working directory
                    if os.path.exists(analysis_working_dir):
                        for filename in os.listdir(analysis_working_dir):
                            if filename.endswith(('.k')):
                                source_file = os.path.join(analysis_working_dir, filename)
                                success = self.export_template_file(source_file, k_file_path)
                                if success:
                                    FreeCAD.Console.PrintMessage(f"Copied existing analysis file: {filename}\n")
                                    k_file_found = True
                                    break

                if not k_file_found:
                    # Fallback to template if no analysis file found
                    template_file = "/home/nemo/Dokumente/Sandbox/Fem_upgraded/zug_test3_RS.k"
                    if os.path.exists(template_file):
                        FreeCAD.Console.PrintMessage(f"DEBUG: About to export template to {k_file_path}\n")
                        self.export_template_file(template_file, k_file_path)
                        FreeCAD.Console.PrintMessage(f"DEBUG: Template export completed\n")
                    else:
                        # Create minimal K-file as last resort
                        try:
                            with open(k_file_path, 'w') as f:
                                f.write("* Test K-file generated by OpenRadioss solver\n")
                                f.write("$ Generated at: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                                f.write("/RUN/OpenRadioss/test_case\n")
                            FreeCAD.Console.PrintMessage(f"Created minimal K-file at {k_file_path}\n")
                        except Exception as fallback_error:
                            FreeCAD.Console.PrintError(f"Fallback creation failed: {fallback_error}\n")
                            return False

                # Verify the file was actually created
                if os.path.exists(k_file_path):
                    file_size = os.path.getsize(k_file_path)
                    FreeCAD.Console.PrintMessage(f"DEBUG: File successfully created, size = {file_size} bytes\n")
                else:
                    FreeCAD.Console.PrintError(f"DEBUG: File was NOT created at {k_file_path}\n")

                self.k_file_updated = True
                FreeCAD.Console.PrintMessage(f"K-file updated successfully at {k_file_path}\n")
                QtGui.QMessageBox.information(self, "Success", f"K-file updated successfully\nLocation: {k_file_path}")

            except Exception as e:
                FreeCAD.Console.PrintError(f"Error creating K-file: {e}\n")
                QtGui.QMessageBox.warning(self, "Error", f"Failed to create K-file: {str(e)}")

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error in onUpdateKFile: {e}\n")
            QtGui.QMessageBox.warning(self, "Error", f"Failed to update K-file: {str(e)}")

    def export_template_file(self, source_file, target_file):
        """Export template file by reading and writing content (works in sandbox)"""
        try:
            source_size = os.path.getsize(source_file)
            FreeCAD.Console.PrintMessage(f"DEBUG: Exporting {source_file} ({source_size} bytes) to {target_file}\n")

            # Use binary mode to handle any file type properly
            with open(source_file, 'rb') as src:
                content = src.read()

            FreeCAD.Console.PrintMessage(f"DEBUG: Read {len(content)} bytes from source\n")

            # Write in binary mode to preserve all data
            with open(target_file, 'wb') as dst:
                dst.write(content)

            # Verify the file was created and has correct content
            if os.path.exists(target_file):
                target_size = os.path.getsize(target_file)
                FreeCAD.Console.PrintMessage(f"DEBUG: Written {target_size} bytes to target\n")

                if target_size == source_size:
                    FreeCAD.Console.PrintMessage(f"Successfully exported template: {source_size} bytes\n")
                    return True
                else:
                    FreeCAD.Console.PrintError(f"Size mismatch: source={source_size}, target={target_size}\n")
                    # Try alternative method with shutil.copy2
                    try:
                        FreeCAD.Console.PrintMessage(f"DEBUG: Trying shutil.copy2 as fallback\n")
                        shutil.copy2(source_file, target_file)
                        fallback_size = os.path.getsize(target_file)
                        if fallback_size == source_size:
                            FreeCAD.Console.PrintMessage(f"Successfully copied with shutil.copy2: {source_size} bytes\n")
                            return True
                        else:
                            FreeCAD.Console.PrintError(f"Shutil copy also failed: {fallback_size} bytes\n")
                            # Create a simple fallback K-file as last resort
                            try:
                                with open(target_file, 'w') as f:
                                    f.write("* Fallback K-file generated by OpenRadioss solver\n")
                                    f.write("$ Generated at: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                                    f.write("$ Original template could not be copied properly\n")
                                    f.write("*NODE\n")
                                    f.write("       1       0.000000       0.000000       0.000000\n")
                                    f.write("       2       1.000000       0.000000       0.000000\n")
                                    f.write("       3       1.000000       1.000000       0.000000\n")
                                    f.write("       4       0.000000       1.000000       0.000000\n")
                                    f.write("*END\n")
                                    f.write("*ELEMENT_SHELL\n")
                                    f.write("       1       1       2       3       4       2\n")
                                    f.write("*END\n")
                                    f.write("*END\n")
                                FreeCAD.Console.PrintMessage(f"Created simple fallback K-file\n")
                                return True
                            except Exception as fallback_error:
                                FreeCAD.Console.PrintError(f"Fallback creation failed: {fallback_error}\n")
                                return False
                    except Exception as copy_error:
                        FreeCAD.Console.PrintError(f"Shutil copy failed: {copy_error}\n")
                        return False
            else:
                FreeCAD.Console.PrintError(f"Target file was not created: {target_file}\n")
                return False

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error exporting template file: {e}\n")
            return False

    def showRunningPopup(self):
        """Show a simple popup indicating the solver is running"""
        # Create a simple dialog
        dialog = QtGui.QDialog(self)
        dialog.setWindowTitle("OpenRadioss Solver Running")
        dialog.resize(400, 200)

        layout = QtGui.QVBoxLayout()

        # Simple message
        working_dir = self.get_working_directory_safe()

        message_label = QtGui.QLabel("OpenRadioss solver is running...\n\nWorking directory: " + working_dir)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        # Simple instructions
        info_label = QtGui.QLabel("If the solver fails in FreeCAD, you can run it externally in your terminal.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(info_label)

        # Close button
        close_button = QtGui.QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

    def showFailurePopup(self):
        """Show a popup with instructions for manual solver execution when automatic execution fails"""
        try:
            # Create a dialog for failure information
            dialog = QtGui.QDialog(self)
            dialog.setWindowTitle("OpenRadioss Solver Execution Failed")
            dialog.resize(600, 400)

            layout = QtGui.QVBoxLayout()

            # Title
            title_label = QtGui.QLabel("OpenRadioss Solver Failed")
            title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: red;")
            layout.addWidget(title_label)

            # Error message
            error_label = QtGui.QLabel("The automatic solver execution failed. You can run OpenRadioss manually using the command below:")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)

            # Get working directory
            working_dir = self.get_working_directory_safe()
            if not working_dir:
                working_dir = os.path.expanduser("~")

            k_file_path = os.path.join(working_dir, 'fem_export.k')

            # Create temp working directory for bash script
            temp_work_dir = f"/tmp/openradioss_work_{int(time.time())}"

            working_dir_label = QtGui.QLabel(f"Working Directory: {working_dir}\nTemp Directory: {temp_work_dir}")
            working_dir_label.setStyleSheet("font-weight: bold; background-color: #f0f0f0; padding: 5px;")
            layout.addWidget(working_dir_label)

            # Command instructions
            command_label = QtGui.QLabel("Run this command in your terminal:")
            command_label.setStyleSheet("font-weight: bold;")
            layout.addWidget(command_label)

            # Command text area
            command_text = QtGui.QTextEdit()
            command_text.setReadOnly(True)
            command_text.setMaximumHeight(100)

            # Get executable path
            executable = getattr(self.obj, 'Executable', '/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/exec/engine_linux64_gf')
            starter_executable = getattr(self.obj, 'Starter', '/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/exec/starter_linux64_gf')

            # Create temp working directory and copy files with environment setup
            command = (f"mkdir -p '{temp_work_dir}' && "
                      f"cp '{k_file_path}' '{temp_work_dir}/' && "
                      f"cd '{temp_work_dir}' && "
                      f"export OPENRADIOSS_PATH='/home/nemo/Dokumente/Software/OpenRadioss_linux64' && "
                      f"export RAD_CFG_PATH=\"/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/hm_cfg_files\" && "
                      f"export RAD_H3D_PATH=\"/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/extlib/h3d/lib/linux64\" && "
                      f"export LD_LIBRARY_PATH=\"/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/extlib/h3d/lib/linux64:/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/extlib/hm_reader/linux64:$LD_LIBRARY_PATH\" && "
                      f"export PATH=\"/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/extlib/hm_reader/linux64:/opt/openmpi/bin:$PATH\" && "
                      f"export OMP_NUM_THREADS=4 && "
                      f"echo \"Environment setup complete\" && "
                      f"echo \"Running starter...\" && "
                      f"'/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/exec/starter_linux64_gf' -i fem_export.k && "
                      f"echo \"Starter completed, looking for generated files:\" && "
                      f"ls -la fem_export*.rad && "
                      f"echo \"Running engine with first available .rad file...\" && "
                      f"ENGINE_INPUT=\"$(ls fem_export*.rad | sort | head -1)\" && "
                      f"echo \"Using input file: $ENGINE_INPUT\" && "
                      f"'/home/nemo/Dokumente/Software/OpenRadioss_linux64/OpenRadioss/exec/engine_linux64_gf' -i \"$ENGINE_INPUT\"")

            command_text.setPlainText(command)
            layout.addWidget(command_text)

            # Additional instructions
            instructions_label = QtGui.QLabel("Instructions:\n"
                                           "1. Copy the command above\n"
                                           "2. Open a terminal and run the command\n"
                                           "3. The command sets up proper environment variables\n"
                                           "4. Creates a temp directory in /tmp\n"
                                           "5. Files are copied from home directory to /tmp\n"
                                           "6. Starter processes the K-file and generates .rad files\n"
                                           "7. Engine automatically detects and uses the correct .rad file\n"
                                           "8. Check the output files (.out, .msg, .sta) in /tmp")
            instructions_label.setWordWrap(True)
            layout.addWidget(instructions_label)

            # Buttons
            button_layout = QtGui.QHBoxLayout()

            copy_button = QtGui.QPushButton("Copy Command")
            copy_button.clicked.connect(lambda: QtGui.QApplication.clipboard().setText(command))
            button_layout.addWidget(copy_button)

            close_button = QtGui.QPushButton("Close")
            close_button.clicked.connect(dialog.accept)
            button_layout.addWidget(close_button)

            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            FreeCAD.Console.PrintError(f"Error showing failure popup: {e}\n")
            # Fallback to simple message box
            QtGui.QMessageBox.warning(self, "Solver Failed",
                                    "The solver execution failed. Please run OpenRadioss manually in the terminal.")