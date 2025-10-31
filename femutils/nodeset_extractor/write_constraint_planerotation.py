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

__title__ = "FreeCAD FEM calculix constraint planerotation"
__author__ = "Bernd Hahnebach"
__url__ = "https://www.freecad.org"


from femmesh import meshtools


def get_analysis_types():
    return "all"  # write for all analysis types


def get_sets_name():
    return "constraints_planerotation_node_sets"


def get_constraint_title():
    return "PlaneRotation Constraints"


def get_before_write_meshdata_constraint():
    return ""


def get_after_write_meshdata_constraint():
    return ""


def get_before_write_constraint():
    return ""


def get_after_write_constraint():
    return ""


def extract_nodesets(analysis, mesh_obj):
    """Extract planerotation constraint nodesets from the analysis.
    
    Args:
        analysis: The FreeCAD FEM analysis object
        mesh_obj: The FEM mesh object
        
    Returns:
        dict: Dictionary with nodeset name as key and node IDs as value
    """
    nodesets = {}
    
    # Find all planerotation constraints in the analysis
    planerotation_constraints = [obj for obj in analysis.Group 
                               if hasattr(obj, 'TypeId') and 
                               obj.TypeId == 'Fem::ConstraintPlaneRotation']
    
    for constraint in planerotation_constraints:
        nodeset_name = f"planerot_{constraint.Name}"
        
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
                # For planerotation constraints, we need to ensure we have enough nodes
                # to define a plane (at least 3 non-collinear nodes)
                if len(node_ids) >= 3:
                    # Get the actual node coordinates for planarity check
                    nodes_coords = []
                    for node_id in node_ids:
                        node = mesh_obj.FemMesh.Nodes[node_id]
                        nodes_coords.append((node_id, node.x, node.y, node.z))
                    
                    # Get three non-collinear nodes to define the plane
                    plane_nodes = meshtools.get_three_non_colinear_nodes(nodes_coords)
                    
                    # Add any additional nodes that weren't included in the plane definition
                    for node_id in node_ids:
                        if node_id not in plane_nodes:
                            plane_nodes.append(node_id)
                    
                    nodesets[nodeset_name] = ",".join(map(str, sorted(plane_nodes)))
    
    return nodesets


def write_meshdata_constraint(f, femobj, fric_obj, ORwriter):
    # write nodes to file
    if not hasattr(ORwriter, 'femnodes_mesh') or not ORwriter.femnodes_mesh:
        ORwriter.femnodes_mesh = ORwriter.femmesh.Nodes
    
    # Initialize constraint_conflict_nodes if it doesn't exist
    if not hasattr(ORwriter, 'constraint_conflict_nodes'):
        ORwriter.constraint_conflict_nodes = []
    
    # Code to extract nodes and coordinates on the PlaneRotation support face
    l_nodes = femobj["Nodes"]
    f.write(f"*NSET,NSET={fric_obj.Name}\n")
    
    nodes_coords = []
    for node in l_nodes:
        nodes_coords.append(
            (
                node,
                ORwriter.femnodes_mesh[node].x,
                ORwriter.femnodes_mesh[node].y,
                ORwriter.femnodes_mesh[node].z,
            )
        )
    
    # Get three non-collinear nodes to define the plane
    node_planerotation = meshtools.get_three_non_colinear_nodes(nodes_coords)
    
    # Add any additional nodes that weren't included in the plane definition
    for node in l_nodes:
        if node not in node_planerotation:
            node_planerotation.append(node)
    
    # Filter out nodes that are already used in other constraints
    MPC_nodes = []
    for node in node_planerotation:
        if node not in ORwriter.constraint_conflict_nodes:
            MPC_nodes.append(node)
    
    # Write the nodes to the file
    for node in MPC_nodes:
        f.write(f"{node},\n")
    
    # Add a blank line after the nodeset
    f.write("\n")


def write_constraint(f, femobj, fric_obj, ORwriter):

    # floats read from ccx should use {:.13G}, see comment in writer module

    f.write("*MPC\n")
    f.write(f"PLANE,{fric_obj.Name}\n")
