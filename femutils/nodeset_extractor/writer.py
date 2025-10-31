# ***************************************************************************
# *   Copyright (c) 2015 Przemo Firszt <przemo@firszt.eu>                   *
# *   Copyright (c) 2015 Bernd Hahnebach <bernd@bimstatik.org>              *
# *   Copyright (c) 2023 Your Name <your.email@example.com>                  *
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

"""
Writer module for FEM analysis export to various solver formats.

This module provides writers for different FEM solver formats, including:
- CalculiX (.inp)
- OpenRadioss (.rad)
- Generic nodeset export (.txt)
"""

__title__ = "FreeCAD FEM solver writer"
__author__ = "Przemo Firszt, Bernd Hahnebach, Your Name"
__url__ = "https://www.freecad.org"

## \addtogroup FEM
#  @{

import os
import time
from os.path import join, splitext
import importlib
import io
from contextlib import redirect_stdout

import FreeCAD
from FreeCAD import Units
from PySide import QtCore, QtGui, QtWidgets

# Import constraint writers
from . import write_constraint_centrif as con_centrif
from . import write_constraint_bodyheatsource as con_bodyheatsource
from . import write_constraint_contact as con_contact
from . import write_constraint_displacement as con_displacement
from . import write_constraint_fixed as con_fixed
from . import write_constraint_fluidsection as con_fluidsection
from . import write_constraint_force as con_force
from . import write_constraint_heatflux as con_heatflux
from . import write_constraint_initialtemperature as con_itemp
from . import write_constraint_planerotation as con_planerotation
from . import write_constraint_pressure as con_pressure
from . import write_constraint_rigidbody as con_rigidbody
from . import write_constraint_rigidbody_step as con_rigidbody_step
from . import write_constraint_sectionprint as con_sectionprint
from . import write_constraint_selfweight as con_selfweight
from . import write_constraint_temperature as con_temperature
from . import write_constraint_tie as con_tie
from . import write_constraint_transform as con_transform
from . import write_femelement_geometry
from . import write_femelement_material
from . import write_femelement_matgeosets
from . import write_footer
from . import write_mesh
from . import write_step_equation
from . import write_step_output
from . import writerbase
from femtools import constants


# Interesting forum topic: https://forum.freecad.org/viewtopic.php?&t=48451
# TODO somehow set units at beginning and every time a value is retrieved use this identifier
# this would lead to support of unit system, force might be retrieved in base writer!


# the following text will be at the end of the main calculix input file
units_information = """***********************************************************
**  About units:
**  See ccx manual, ccx does not know about any unit.
**  Golden rule: The user must make sure that the numbers they provide have consistent units.
**  The user is the FreeCAD calculix writer module ;-)
**
**  The unit system which is used at Guido Dhondt's company: mm, N, s, K
**  Since Length and Mass are connected by Force, if Length is mm the Mass is in t to get N
**  The following units are used to write to inp file:
**
**  Length: mm (this includes the mesh geometry)
**  Mass: t
**  TimeSpan: s
**  Temperature: K
**
**  This leads to:
**  Force: N
**  Pressure: N/mm^2 == MPa (Young's Modulus has unit Pressure)
**  Density: t/mm^3
**  Gravity: mm/s^2
**  Thermal conductivity: t*mm/K/s^3 == as W/m/K == kW/mm/K
**  Specific Heat: mm^2/s^2/K = J/kg/K == kJ/t/K
"""


# TODO
# {0:.13G} or {:.13G} should be used on all places writing floating points to ccx
# All floating points fields read from ccx are F20.0 FORTRAN input fields.
# see in dload.f in ccx's source
# https://forum.freecad.org/viewtopic.php?f=18&p=516518#p516433
# https://forum.freecad.org/viewtopic.php?f=18&t=22759&#p176578
# example "{:.13G}".format(math.sqrt(2.)*-1e100) and count chars
# a property type is best checked in FreeCAD objects definition
# see femobjects package for Python objects or in objects App


class FemInputWriter(writerbase.FemInputWriter):
    """Base class for FEM writers with common functionality."""
    
    def __init__(self, analysis_obj, solver_obj, mesh_obj, member, dir_name=None, mat_geo_sets=None):
        """Initialize the base FEM writer.
        
        Args:
            analysis_obj: The analysis object
            solver_obj: The solver object
            mesh_obj: The mesh object
            member: The member object
            dir_name: Output directory name
            mat_geo_sets: Material geometry sets
        """
        super().__init__(analysis_obj, solver_obj, mesh_obj, member, dir_name, mat_geo_sets)
        self.mesh_name = self.mesh_object.Name
        self.femmesh_file = ""  # the file the femmesh is in, no matter if one or split input file
        self.gravity = int(Units.Quantity(constants.gravity()).getValueAs("mm/s^2"))  # 9820 mm/s2
        self.units_information = units_information
        self.file_extension = ".dat"  # Default extension, override in subclasses
        self.file_name = join(self.dir_name, f"{self.mesh_name}{self.file_extension}")
    
    def get_supported_constraints(self):
        """Return a list of supported constraint types."""
        return [
            'fixed', 'displacement', 'force', 'pressure', 'temperature',
            'heatflux', 'selfweight', 'centrif', 'bodyheatsource',
            'initialtemperature', 'planerotation', 'contact', 'tie',
            'transform', 'rigidbody', 'rigidbody_step', 'sectionprint'
        ]
    
    def write_constraints_meshsets(self, f, constraints, writer_module):
        """Write mesh sets for constraints."""
        if not constraints:
            return
            
        if hasattr(writer_module, 'write_meshdata_constraint'):
            for femobj in constraints:
                try:
                    writer_module.write_meshdata_constraint(
                        f, femobj, femobj['Object'], self
                    )
                except Exception as e:
                    FreeCAD.Console.PrintError(
                        f"Error writing mesh data for {femobj['Object'].Name}: {str(e)}\n"
                    )
    
    def write_constraints_propdata(self, f, constraints, writer_module):
        """Write property data for constraints."""
        if not constraints:
            return
            
        if hasattr(writer_module, 'write_constraint'):
            for femobj in constraints:
                try:
                    writer_module.write_constraint(
                        f, femobj, femobj['Object'], self
                    )
                except Exception as e:
                    FreeCAD.Console.PrintError(
                        f"Error writing constraint {femobj['Object'].Name}: {str(e)}\n"
                    )
    
    def get_nodesets(self):
        """Extract nodesets from constraints and return as a string.
        
        Returns:
            str: The nodeset data as a formatted string, or empty string if no nodesets found
        """
        print(f"[NODESET] Starting nodeset extraction for mesh: {getattr(self, 'mesh_name', 'unknown')}")
        
        try:
            # Get the analysis and mesh objects
            analysis = getattr(self, 'analysis', None)
            mesh_obj = getattr(self, 'mesh_object', None)
            
            if not analysis or not mesh_obj:
                print("[NODESET] [ERROR] Missing analysis or mesh object")
                return ""
                
            # Extract nodesets
            return extract_nodesets(analysis, mesh_obj)
                
        except Exception as e:
            print(f"[NODESET] [ERROR] Failed to extract nodesets: {str(e)}")
            import traceback
            traceback.print_exc()
            return ""

def extract_nodesets(analysis, mesh_obj, create_text_object=False, progress_callback=None):
    """Extract nodesets from analysis and return as a string.
    
    Args:
        analysis: The FreeCAD FEM analysis object
        mesh_obj: The FEM mesh object
        create_text_object: If True, creates a FreeCAD text document object (not used, kept for backward compatibility)
        progress_callback: Optional callback function for progress updates (not used, kept for backward compatibility)
        
    Returns:
        str: The nodeset data as a formatted string, or empty string if no nodesets found
    """
    print(f"[NODESET] Extracting nodesets for mesh: {mesh_obj.Name if mesh_obj else 'None'}")
    
    try:
        # Import all constraint writer modules
        from .write_constraint_fixed import extract_nodesets as extract_fixed_nodesets
        from .write_constraint_displacement import extract_nodesets as extract_displacement_nodesets
        from .write_constraint_planerotation import extract_nodesets as extract_planerotation_nodesets
        from .write_constraint_transform import extract_nodesets as extract_transform_nodesets
        from .write_constraint_temperature import extract_nodesets as extract_temperature_nodesets
        from .write_constraint_force import extract_nodesets as extract_force_nodesets
        from .write_constraint_pressure import extract_nodesets as extract_pressure_nodesets
        from .write_constraint_contact import extract_nodesets as extract_contact_nodesets
        from .write_constraint_tie import extract_nodesets as extract_tie_nodesets
        from .write_constraint_heatflux import extract_nodesets as extract_heatflux_nodesets
        
        # Initialize nodesets dictionary
        nodesets = {}
        
        # Extract nodesets from each constraint type
        extractors = [
            extract_fixed_nodesets,
            extract_displacement_nodesets,
            extract_planerotation_nodesets,
            extract_transform_nodesets,
            extract_temperature_nodesets,
            extract_force_nodesets,
            extract_pressure_nodesets,
            extract_contact_nodesets,
            extract_tie_nodesets,
            extract_heatflux_nodesets
        ]
        
        for extractor in extractors:
            try:
                nodesets.update(extractor(analysis, mesh_obj) or {})
            except Exception as e:
                print(f"[NODESET] [WARNING] Error extracting nodesets: {str(e)}")
        
        if not nodesets:
            print("[NODESET] [WARNING] No nodesets were extracted from constraints")
            return ""
            
        print(f"[NODESET] Extracted {len(nodesets)} nodesets")
        
        # Create output string
        output = []
        
        # Add header
        output.extend([
            f"# Nodeset definitions for {mesh_obj.Name if mesh_obj else 'unknown'}",
            "# Generated by FreeCAD FEM Nodeset Extractor",
            "# Format: nodeset_name node_id1, node_id2, ...",
            ""
        ])
        
        # Add nodesets
        for name, content in sorted(nodesets.items()):
            if content:
                node_count = len(str(content).split(',')) if content else 0
                print(f"[NODESET] Adding nodeset: {name} with {node_count} nodes")
                output.extend([f"# {name}", f"{content}", ""])
            else:
                print(f"[NODESET] [WARNING] Empty nodeset: {name}")
        
        return "\n".join(output)
        
    except ImportError as e:
        print(f"[NODESET] [ERROR] Failed to import required modules: {str(e)}")
        return ""
    except Exception as e:
        print(f"[NODESET] [ERROR] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return ""
        
    except ImportError as e:
        print(f"[NODESET] [ERROR] Failed to import required modules: {str(e)}")
        return False
    except IOError as e:
        print(f"[NODESET] [ERROR] Failed to write nodeset file: {str(e)}")
        return False
    except Exception as e:
        print(f"[NODESET] [ERROR] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


class FemInputWriterCcx(FemInputWriter):
    """Writer for CalculiX solver input files (.inp)."""
    
    def __init__(self, analysis_obj, solver_obj, mesh_obj, member, dir_name=None, mat_geo_sets=None):
        """Initialize the CalculiX writer."""
        super().__init__(analysis_obj, solver_obj, mesh_obj, member, dir_name, mat_geo_sets)
        self.file_extension = ".inp"
        self.file_name = join(self.dir_name, f"{self.mesh_name}{self.file_extension}")

    def write_solver_input(self):
        """Write the CalculiX solver input file."""
        time_start = time.process_time()
        FreeCAD.Console.PrintMessage("\n")  # because of time print in separate line
        FreeCAD.Console.PrintMessage("CalculiX solver input writing...\n")
        FreeCAD.Console.PrintMessage(f"Input file: {self.file_name}\n")

        if hasattr(self.solver_obj, 'SplitInputWriter') and self.solver_obj.SplitInputWriter is True:
            FreeCAD.Console.PrintMessage("Split input file.\n")
            self.split_inpfile = True
        else:
            FreeCAD.Console.PrintMessage("One monster input file.\n")
            self.split_inpfile = False

        try:
            # mesh
            inpfile = write_mesh.write_mesh(self)

            # element sets for materials and element geometry
            write_femelement_matgeosets.write_femelement_matgeosets(inpfile, self)

            # some fluidsection objs need special treatment, mat_geo_sets are needed for this
            if hasattr(con_fluidsection, 'handle_fluidsection_liquid_inlet_outlet'):
                inpfile = con_fluidsection.handle_fluidsection_liquid_inlet_outlet(inpfile, self)

            # element sets constraints
            self.write_constraints_meshsets(inpfile, getattr(self.member, 'cons_centrif', []), con_centrif)
            self.write_constraints_meshsets(
                inpfile, getattr(self.member, 'cons_bodyheatsource', []), con_bodyheatsource
            )

            # node sets
            self.write_constraints_meshsets(inpfile, getattr(self.member, 'cons_fixed', []), con_fixed)
            self.write_constraints_meshsets(inpfile, getattr(self.member, 'cons_rigidbody', []), con_rigidbody)
            self.write_constraints_meshsets(inpfile, getattr(self.member, 'cons_displacement', []), con_displacement)
            self.write_constraints_meshsets(inpfile, getattr(self.member, 'cons_planerotation', []), con_planerotation)
            self.write_constraints_meshsets(inpfile, getattr(self.member, 'cons_transform', []), con_transform)
            self.write_constraints_meshsets(inpfile, getattr(self.member, 'cons_temperature', []), con_temperature)

            # surface sets
            self.write_constraints_meshsets(inpfile, getattr(self.member, 'cons_contact', []), con_contact)
            self.write_constraints_meshsets(inpfile, getattr(self.member, 'cons_tie', []), con_tie)
            self.write_constraints_meshsets(inpfile, getattr(self.member, 'cons_sectionprint', []), con_sectionprint)

            # materials and fem element types
            write_femelement_material.write_femelement_material(inpfile, self)
            self.write_constraints_propdata(inpfile, getattr(self.member, 'cons_initialtemperature', []), con_itemp)
            write_femelement_geometry.write_femelement_geometry(inpfile, self)

            # constraints independent from steps
            self.write_constraints_propdata(inpfile, getattr(self.member, 'cons_planerotation', []), con_planerotation)
            self.write_constraints_propdata(inpfile, getattr(self.member, 'cons_contact', []), con_contact)
            self.write_constraints_propdata(inpfile, getattr(self.member, 'cons_tie', []), con_tie)
            self.write_constraints_propdata(inpfile, getattr(self.member, 'cons_transform', []), con_transform)
            self.write_constraints_propdata(inpfile, getattr(self.member, 'cons_rigidbody', []), con_rigidbody)

            # step equation
            write_step_equation.write_step_equation(inpfile, self)

            # constraints dependent from steps
            self.write_constraints_propdata(inpfile, getattr(self.member, 'cons_fixed', []), con_fixed)
            self.write_constraints_propdata(
                inpfile, getattr(self.member, 'cons_rigidbody_step', []), con_rigidbody_step
            )
            self.write_constraints_propdata(inpfile, getattr(self.member, 'cons_displacement', []), con_displacement)
            self.write_constraints_propdata(inpfile, getattr(self.member, 'cons_sectionprint', []), con_sectionprint)
            self.write_constraints_propdata(inpfile, getattr(self.member, 'cons_selfweight', []), con_selfweight)
            self.write_constraints_propdata(inpfile, getattr(self.member, 'cons_centrif', []), con_centrif)
            self.write_constraints_propdata(
                inpfile, getattr(self.member, 'cons_bodyheatsource', []), con_bodyheatsource
            )
            self.write_constraints_meshsets(inpfile, getattr(self.member, 'cons_force', []), con_force)
            self.write_constraints_meshsets(inpfile, getattr(self.member, 'cons_pressure', []), con_pressure)
            self.write_constraints_propdata(inpfile, getattr(self.member, 'cons_temperature', []), con_temperature)
            self.write_constraints_meshsets(inpfile, getattr(self.member, 'cons_heatflux', []), con_heatflux)
            
            if hasattr(con_fluidsection, 'write_constraints_fluidsection'):
                con_fluidsection.write_constraints_fluidsection(inpfile, self)

            # output and step end
            write_step_output.write_step_output(inpfile, self)
            write_step_equation.write_step_end(inpfile, self)

            # footer
            write_footer.write_footer(inpfile, self)

            # close file
            inpfile.close()

            writetime = round((time.process_time() - time_start), 3)
            FreeCAD.Console.PrintMessage(f"Writing time CalculiX input file: {writetime} seconds.\n")

            # Write nodesets if requested
            if hasattr(self.solver_obj, 'WriteNodesets') and self.solver_obj.WriteNodesets:
                nodeset_file = self.write_nodesets()
                if nodeset_file:
                    FreeCAD.Console.PrintMessage(f"Nodesets written to: {nodeset_file}\n")

            return self.file_name
            
        except Exception as e:
            import traceback
            FreeCAD.Console.PrintError(f"Error writing CalculiX input file: {str(e)}\n")
            FreeCAD.Console.PrintError(traceback.format_exc() + "\n")
            return ""


class FemInputWriterRadioss(FemInputWriter):
    """Writer for OpenRadioss solver input files (.rad)."""
    
    def __init__(self, analysis_obj, solver_obj, mesh_obj, member, dir_name=None, mat_geo_sets=None):
        """Initialize the OpenRadioss writer."""
        super().__init__(analysis_obj, solver_obj, mesh_obj, member, dir_name, mat_geo_sets)
        self.file_extension = ".rad"
        self.file_name = join(self.dir_name, f"{self.mesh_name}{self.file_extension}")
    
    def _update_keyword_file(self, analysis):
        """Update the .k file in the analysis directory with include statement."""
        try:
            import os
            import FreeCADGui as Gui
            
            # Get the document directory
            doc = analysis.Document
            doc_path = os.path.dirname(doc.FileName) if hasattr(doc, 'FileName') and doc.FileName else ''
            
            if not doc_path:
                FreeCAD.Console.PrintWarning("Document not saved, cannot find .k file\n")
                return
                
            # Look for .k files in the document directory
            k_files = [f for f in os.listdir(doc_path) if f.lower().endswith('.k')]
            
            if not k_files:
                FreeCAD.Console.PrintWarning(f"No .k file found in {doc_path}\n")
                return
                
            # Use the first .k file found
            k_file = os.path.join(doc_path, k_files[0])
            
            # Check if the include statement already exists
            with open(k_file, 'r') as f:
                content = f.read()
                
            if '*include discrete.mesh' in content:
                FreeCAD.Console.PrintMessage(f"Include statement already exists in {k_file}\n")
                return
                
            # Add the include statement at the end of the file
            with open(k_file, 'a') as f:
                f.write("\n*include discrete.mesh\n")
                
            FreeCAD.Console.PrintMessage(f"Added include statement to {k_file}\n")
            
        except Exception as e:
            FreeCAD.Console.PrintError(f"Error updating .k file: {str(e)}\n")
    
    def write_solver_input(self):
        """Write the OpenRadioss solver input file."""
        time_start = time.process_time()
        FreeCAD.Console.PrintMessage("\n")
        FreeCAD.Console.PrintMessage("OpenRadioss solver input writing...\n")
        FreeCAD.Console.PrintMessage(f"Output file: {self.file_name}\n")
        
        try:
            # Update the .k file with include statement
            if hasattr(self, 'analysis') and self.analysis:
                self._update_keyword_file(self.analysis)
                
            with open(self.file_name, 'w') as f:
                # Write header
                f.write("$$\n")
                f.write("$$ OpenRadioss Input File\n")
                f.write("$$ Generated by FreeCAD FEM\n")
                f.write(f"$$ Model: {self.mesh_name}\n")
                f.write(f"$$ Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("$$\n")
                
                
                # Write nodes
                self._write_nodes(f)
                
                # Write elements
                self._write_elements(f)
                
                # Write materials
                self._write_materials(f)
                
                # Write properties
                self._write_properties(f)
                
                # Write constraints
                self._write_constraints(f)
                
                # Write footer
                f.write("$$ End of OpenRadioss input file\n")
            
            writetime = round((time.process_time() - time_start), 3)
            FreeCAD.Console.PrintMessage(f"Writing time OpenRadioss input file: {writetime} seconds.\n")
            
            # Always write nodesets for Radioss
            nodeset_file = self.write_nodesets()
            if nodeset_file:
                FreeCAD.Console.PrintMessage(f"Nodesets written to: {nodeset_file}\n")
            
            return self.file_name
            
        except Exception as e:
            import traceback
            FreeCAD.Console.PrintError(f"Error writing OpenRadioss input file: {str(e)}\n")
            FreeCAD.Console.PrintError(traceback.format_exc() + "\n")
            return ""
    
    def _write_nodes(self, f):
        """Write node data to the file."""
        if not hasattr(self, 'mesh_object') or not hasattr(self.mesh_object, 'FemMesh'):
            return
            
        mesh = self.mesh_object.FemMesh
        f.write("$$\n$$ NODES\n$$\n")
        f.write("/NODE/\n")
        
        for node_id, node in mesh.Nodes.items():
            f.write(f"{node_id:10d}{node.x:16.9E}{node.y:16.9E}{node.z:16.9E}\n")
        
        f.write("\n")
    
    def _write_elements(self, f):
        """Write element data to the file."""
        if not hasattr(self, 'mesh_object') or not hasattr(self.mesh_object, 'FemMesh'):
            return
            
        mesh = self.mesh_object.FemMesh
        f.write("$$\n$$ ELEMENTS\n$$\n")
        
        # Group elements by type
        elements_by_type = {}
        for elem_id, elem in mesh.Faces.items():
            elem_type = len(elem)
            if elem_type not in elements_by_type:
                elements_by_type[elem_type] = []
            elements_by_type[elem_type].append((elem_id, elem))
        
        # Write elements by type
        for elem_type, elements in elements_by_type.items():
            if elem_type == 3:
                f.write("/ELEM/TRI3/\n")
            elif elem_type == 4:
                f.write("/ELEM/QUAD4/\n")
            else:
                f.write(f"$$ Unsupported element type with {elem_type} nodes\n")
                continue
            
            for elem_id, elem in elements:
                node_str = ' '.join(f"{n:10d}" for n in elem)
                f.write(f"{elem_id:10d}{node_str}\n")
            
            f.write("\n")
    
    def _write_materials(self, f):
        """Write material data to the file."""
        if not hasattr(self, 'member') or not hasattr(self.member, 'mats_linear'):
            return
            
        f.write("$$\n$$ MATERIALS\n$$\n")
        
        for i, mat in enumerate(self.member.mats_linear, 1):
            mat_obj = mat['Object']
            f.write(f"/MAT/LAW1/{i}\n")  # Using LAW1 for linear elastic
            f.write(f"{mat_obj.Label}\n")
            
            # Get material properties with defaults
            youngs_modulus = getattr(mat_obj, 'YoungsModulus', 210000.0)  # MPa
            poisson_ratio = getattr(mat_obj, 'PoissonRatio', 0.3)
            density = getattr(mat_obj, 'Density', 7.85e-9)  # t/mm^3
            
            f.write(f"{youngs_modulus:16.9E}{poisson_ratio:16.9E}{density:16.9E}\n\n")
    
    def _write_properties(self, f):
        """Write property data to the file."""
        if not hasattr(self, 'member') or not hasattr(self.member, 'geos_beamsection'):
            return
            
        f.write("$$\n$$ PROPERTIES\n$$\n")
        
        for i, geo in enumerate(self.member.geos_beamsection, 1):
            geo_obj = geo['Object']
            f.write(f"/PROP/TYPE{i}/\n")
            f.write(f"{geo_obj.Label}\n")
            
            # Get property values with defaults
            area = getattr(geo_obj, 'SectionArea', 100.0)  # mm^2
            iy = getattr(geo_obj, 'MomentOfInertiaY', 1000.0)  # mm^4
            iz = getattr(geo_obj, 'MomentOfInertiaZ', 1000.0)  # mm^4
            j = getattr(geo_obj, 'TorsionConstantJ', 500.0)  # mm^4
            
            f.write(f"{area:16.9E}{iy:16.9E}{iz:16.9E}{j:16.9E}\n\n")
    
    def _write_constraints(self, f):
        """Write constraint data to the file."""
        if not hasattr(self, 'member') or not hasattr(self.member, 'cons_fixed'):
            return
            
        f.write("$$\n$$ CONSTRAINTS\n$$\n")
        
        # Write fixed constraints
        for i, con in enumerate(self.member.cons_fixed, 1):
            con_obj = con['Object']
            f.write(f"$$ Fixed Constraint: {con_obj.Name}\n")
            f.write("/BC_DOF/\n")
            f.write(f"{i:10d}        0\n")
            
            # Get DOF constraints (1 = fixed, 0 = free)
            dof = [1, 1, 1, 1, 1, 1]  # TX, TY, TZ, RX, RY, RZ
            
            # Check if any DOFs are not fixed
            if hasattr(con_obj, 'xFix') and not con_obj.xFix:
                dof[0] = 0
            if hasattr(con_obj, 'yFix') and not con_obj.yFix:
                dof[1] = 0
            if hasattr(con_obj, 'zFix') and not con_obj.zFix:
                dof[2] = 0
                
            f.write(" ".join(str(d) for d in dof) + "\n\n")


def get_writer_for_solver(solver_type, analysis_obj, solver_obj, mesh_obj, member, dir_name=None, mat_geo_sets=None):
    """Factory function to get the appropriate writer for the given solver type.
    
    Args:
        solver_type: Type of solver ('CalculiX', 'Radioss', etc.)
        analysis_obj: The analysis object
        solver_obj: The solver object
        mesh_obj: The mesh object
        member: The member object
        dir_name: Output directory name
        mat_geo_sets: Material geometry sets
        
    Returns:
        FemInputWriter: An instance of the appropriate writer class
    """
    solver_type = str(solver_type).lower()
    
    if 'calculix' in solver_type:
        return FemInputWriterCcx(analysis_obj, solver_obj, mesh_obj, member, dir_name, mat_geo_sets)
    elif 'radioss' in solver_type:
        return FemInputWriterRadioss(analysis_obj, solver_obj, mesh_obj, member, dir_name, mat_geo_sets)
    else:
        # Default to CalculiX for backward compatibility
        FreeCAD.Console.PrintWarning(
            f"Unknown solver type: {solver_type}. Using CalculiX writer.\n"
        )
        return FemInputWriterCcx(analysis_obj, solver_obj, mesh_obj, member, dir_name, mat_geo_sets)


##  @}
