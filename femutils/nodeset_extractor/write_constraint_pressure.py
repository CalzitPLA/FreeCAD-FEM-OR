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

__title__ = "FreeCAD FEM calculix constraint pressure"
__author__ = "Bernd Hahnebach"
__url__ = "https://www.freecad.org"

import FreeCAD


def get_analysis_types():
    return ["buckling", "static", "thermomech"]


def get_sets_name():
    return "constraints_pressure_element_face_loads"


def get_before_write_meshdata_constraint():
    return ""


def get_after_write_meshdata_constraint():
    return ""


def extract_nodesets(analysis, mesh_obj):
    """Extract pressure constraint nodesets from the analysis.
    
    Args:
        analysis: The FreeCAD FEM analysis object
        mesh_obj: The FEM mesh object
        
    Returns:
        dict: Dictionary with nodeset name as key and node IDs as value
    """
    nodesets = {}
    
    # Find all pressure constraints in the analysis
    pressure_constraints = [obj for obj in analysis.Group 
                          if hasattr(obj, 'TypeId') and 
                          obj.TypeId == 'Fem::ConstraintPressure']
    
    for constraint in pressure_constraints:
        nodeset_name = f"pressure_{constraint.Name}"
        
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
                            # For pressure constraints, we typically want the face nodes
                            node_ids.extend(obj.getNodeByFace(e))
                        elif 'Vertex' in e:
                            node_ids.append(obj.getNodeByVertex(e))
            
            if node_ids:
                nodesets[nodeset_name] = ",".join(map(str, sorted(set(node_ids))))
    
    return nodesets


def write_meshdata_constraint(f, femobj, prs_obj, ORwriter):
    """Write constraint data for pressure constraints.
    
    Args:
        f: File object to write to
        femobj: The FEM object containing the constraint data
        prs_obj: The pressure constraint object
        ORwriter: The OpenRadioss writer instance
    """
    # floats read from ccx should use {:.13G}, see comment in writer module

    rev = -1 if prs_obj.Reversed else 1
    # the pressure has to be output in MPa
    pressure_quantity = FreeCAD.Units.Quantity(prs_obj.Pressure.getValueAs("MPa"))
    press_rev = rev * pressure_quantity

    f.write("*DLOAD\n")
    for ref_shape in femobj["PressureFaces"]:
        # the loop is needed for compatibility reason
        # in deprecated method get_pressure_obj_faces_depreciated
        # the face ids where per ref_shape
        f.write("** " + ref_shape[0] + "\n")
        for face, fno in ref_shape[1]:
            if fno > 0:  # solid mesh face
                f.write(f"{face},P{fno},{press_rev}\n")
            # on shell mesh face: fno == 0
            # normal of element face == face normal
            elif fno == 0:
                f.write(f"{face},P,{press_rev}\n")
            # on shell mesh face: fno == -1
            # normal of element face opposite direction face normal
            elif fno == -1:
                f.write(f"{face},P,{-1 * press_rev}\n")
