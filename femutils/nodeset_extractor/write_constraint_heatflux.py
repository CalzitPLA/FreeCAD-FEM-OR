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

__title__ = "FreeCAD FEM calculix constraint heatflux"
__author__ = "Bernd Hahnebach"
__url__ = "https://www.freecad.org"


def get_analysis_types():
    return ["thermomech"]


def get_sets_name():
    return "constraints_heatflux_element_face_heatflux"


def get_before_write_meshdata_constraint():
    return ""


def get_after_write_meshdata_constraint():
    return ""


def extract_nodesets(analysis, mesh_obj):
    """Extract heat flux constraint nodesets from the analysis.
    
    Args:
        analysis: The FreeCAD FEM analysis object
        mesh_obj: The FEM mesh object
        
    Returns:
        dict: Dictionary with nodeset name as key and node IDs as value
    """
    nodesets = {}
    
    # Find all heat flux constraints in the analysis
    heatflux_constraints = [obj for obj in analysis.Group 
                          if hasattr(obj, 'TypeId') and 
                          obj.TypeId == 'Fem::ConstraintHeatflux']
    
    for constraint in heatflux_constraints:
        nodeset_name = f"heatflux_{constraint.Name}"
        
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
                            # For heat flux constraints, we typically want the face nodes
                            node_ids.extend(obj.getNodeByFace(e))
                        elif 'Vertex' in e:
                            node_ids.append(obj.getNodeByVertex(e))
            
            if node_ids:
                nodesets[nodeset_name] = ",".join(map(str, sorted(set(node_ids))))
    
    return nodesets


def write_meshdata_constraint(f, femobj, heatflux_obj, ORwriter):
    """Write constraint data for heat flux constraints.
    
    Args:
        f: File object to write to
        femobj: The FEM object containing the constraint data
        heatflux_obj: The heat flux constraint object
        ORwriter: The OpenRadioss writer instance
    """
    # floats read from ccx should use {:.13G}, see comment in writer module

    if heatflux_obj.ConstraintType == "Convection":
        heatflux_key_word = "FILM"
        heatflux_facetype = "F"
        # SvdW: add factor to force heatflux to units system of t/mm/s/K
        heatflux_values = "{:.13G},{:.13G}".format(
            heatflux_obj.AmbientTemp, heatflux_obj.FilmCoef * 0.001
        )

    elif heatflux_obj.ConstraintType == "Radiation":
        heatflux_key_word = "RADIATE"
        heatflux_facetype = "R"
        heatflux_values = "{:.13G},{:.13G}".format(
            heatflux_obj.AmbientTemp, heatflux_obj.Emissivity
        )

    elif heatflux_obj.ConstraintType == "DFlux":
        heatflux_key_word = "DFLUX"
        heatflux_facetype = "S"
        heatflux_values = f"{heatflux_obj.DFlux * 0.001:.13G}"

    f.write(f"*{heatflux_key_word}\n")
    for ref_shape in femobj["HeatFluxFaceTable"]:
        elem_string = ref_shape[0]
        face_table = ref_shape[1]
        f.write(f"** Heat flux on face {elem_string}\n")
        for i in face_table:
            # OvG: Only write out the VolumeIDs linked to a particular face
            f.write(f"{i[0]},{heatflux_facetype}{i[1]},{heatflux_values}\n")
