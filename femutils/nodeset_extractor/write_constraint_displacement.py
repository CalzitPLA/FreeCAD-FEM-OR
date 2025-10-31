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

__title__ = "FreeCAD FEM calculix constraint displacement"
__author__ = "Bernd Hahnebach"
__url__ = "https://www.freecad.org"

import FreeCAD


def get_analysis_types():
    return "all"  # write for all analysis types


def get_sets_name():
    return "constraints_displacement_node_sets"


def get_constraint_title():
    return "Displacement constraint applied"


def get_before_write_meshdata_constraint():
    return ""


def get_after_write_meshdata_constraint():
    return ""


def get_before_write_constraint():
    return ""


def get_after_write_constraint():
    return "\n"


def write_meshdata_constraint(f, femobj, disp_obj, ORwriter):
    f.write(f"*NSET,NSET={disp_obj.Name}\n")
    for n in femobj["Nodes"]:
        f.write(f"{n},\n")


def extract_nodesets(analysis, mesh_obj):
    """Extract displacement constraint nodesets from the analysis.
    
    Args:
        analysis: The FreeCAD FEM analysis object
        mesh_obj: The FEM mesh object
        
    Returns:
        dict: Dictionary with nodeset name as key and node IDs as value
    """
    nodesets = {}
    
    # Find all displacement constraints in the analysis
    disp_constraints = [obj for obj in analysis.Group 
                       if hasattr(obj, 'TypeId') and obj.TypeId == 'Fem::ConstraintDisplacement']
    
    for constraint in disp_constraints:
        nodeset_name = f"disp_{constraint.Name}"
        
        # Get nodes from the constraint references
        if hasattr(constraint, 'References') and constraint.References:
            node_ids = []
            for (obj, elem) in constraint.References:
                if hasattr(obj, 'getNodeByEdge'):
                    # Get nodes from edges/faces/vertices
                    for e in elem:
                        if 'Edge' in e:
                            node_ids.extend(obj.getNodeByEdge(e))
                        elif 'Face' in e:
                            node_ids.extend(obj.getNodeByFace(e))
                        elif 'Vertex' in e:
                            node_ids.append(obj.getNodeByVertex(e))
            
            if node_ids:
                nodesets[nodeset_name] = ",".join(map(str, sorted(set(node_ids))))
    
    return nodesets


def write_constraint(f, femobj, disp_obj, ORwriter):
    # For OpenRadioss, we'll write the displacement constraint as a /BCS/PRESCRIBED_VELOCITY card
    # Format: $BCS/PRESCRIBED_VELOCITY/constraint_name
    
    # Only write the constraint if it has fixed displacements
    has_fixed_disp = not (disp_obj.xFree and disp_obj.yFree and disp_obj.zFree)
    has_fixed_rot = ORwriter.member.geos_beamsection or ORwriter.member.geos_shellthickness
    has_fixed_rot = has_fixed_rot and not (disp_obj.rotxFree and disp_obj.rotyFree and disp_obj.rotzFree)
    
    if not (has_fixed_disp or has_fixed_rot):
        return  # Skip if no fixed displacements or rotations
    
    # Write the constraint header
    f.write(f"$BCS/PRESCRIBED_VELOCITY/{disp_obj.Name}\n")
    
    # Write fixed translations
    if has_fixed_disp:
        # Format: /BCS/PRESCRIBED_VELOCITY/constraint_name
        #         NODE_ID, DOF, VELOCITY, FUNCTION_ID
        disp_values = []
        if not disp_obj.xFree:
            disp_values.append(FreeCAD.Units.Quantity(disp_obj.xDisplacement.getValueAs("mm")))
        if not disp_obj.yFree:
            disp_values.append(FreeCAD.Units.Quantity(disp_obj.yDisplacement.getValueAs("mm")))
        if not disp_obj.zFree:
            disp_values.append(FreeCAD.Units.Quantity(disp_obj.zDisplacement.getValueAs("mm")))
        
        # Write the nodeset reference and displacement values
        f.write(f"{disp_obj.Name},0,0,0\n")  # 0,0,0 for fixed displacement
        f.write(" ".join(str(float(v)) for v in disp_values) + "\n")
    
    # Write fixed rotations if applicable
    if has_fixed_rot:
        rot_values = []
        if not disp_obj.rotxFree:
            rot_values.append(FreeCAD.Units.Quantity(disp_obj.xRotation.getValueAs("deg")))
        if not disp_obj.rotyFree:
            rot_values.append(FreeCAD.Units.Quantity(disp_obj.yRotation.getValueAs("deg")))
        if not disp_obj.rotzFree:
            rot_values.append(FreeCAD.Units.Quantity(disp_obj.zRotation.getValueAs("deg")))
        
        if rot_values:
            f.write(f"{disp_obj.Name}_ROT,0,0,0\n")  # 0,0,0 for fixed rotation
            f.write(" ".join(str(float(v)) for v in rot_values) + "\n")
    
    # Add a blank line after the constraint
    f.write("\n")
