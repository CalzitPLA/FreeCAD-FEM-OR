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

__title__ = "FreeCAD FEM calculix constraint fixed"
__author__ = "Bernd Hahnebach"
__url__ = "https://www.freecad.org"


def get_analysis_types():
    return "all"  # write for all analysis types


def get_sets_name():
    return "constraints_fixed_node_sets"


def get_constraint_title():
    return "Fixed Constraints"


def get_before_write_meshdata_constraint():
    return ""


def get_after_write_meshdata_constraint():
    return ""


def get_before_write_constraint():
    return ""


def get_after_write_constraint():
    return ""


def write_meshdata_constraint(f, femobj, fix_obj, ORwriter):
    # For OpenRadioss, we'll write a simple nodeset for all nodes in the constraint
    # Format: $NODESET/constraint_name
    f.write(f"$NODESET/{fix_obj.Name}\n")
    
    # Write all nodes in the constraint
    if "Nodes" in femobj:
        # Write nodes in chunks of 10 for better readability
        nodes = femobj["Nodes"]
        for i in range(0, len(nodes), 10):
            chunk = nodes[i:i+10]
            f.write(" ".join(map(str, chunk)) + "\n")
    
    # Add a blank line after the nodeset
    f.write("\n")


def extract_nodesets(analysis, mesh_obj):
    """Extract fixed constraint nodesets from the analysis.
    
    Args:
        analysis: The FreeCAD FEM analysis object
        mesh_obj: The FEM mesh object
        
    Returns:
        dict: Dictionary with nodeset name as key and node IDs as value
    """
    from .nodeset_utils import extract_nodes_from_references, log_message
    
    nodesets = {}
    constraint_type = 'Fem::ConstraintFixed'
    nodeset_prefix = 'fixed_'
    
    # Find all fixed constraints in the analysis
    constraints = [obj for obj in analysis.Group if hasattr(obj, 'TypeId') and obj.TypeId == constraint_type]
    log_message('DEBUG', f'Found {len(constraints)} {constraint_type} constraints')
    
    for constraint in constraints:
        nodeset_name = f"{nodeset_prefix}{constraint.Name}"
        log_message('DEBUG', f'Processing constraint: {constraint.Name} ({constraint.TypeId})')
        
        if not hasattr(constraint, 'References') or not constraint.References:
            log_message('WARNING', f'Constraint {constraint.Name} has no references')
            continue
            
        # Extract nodes using the utility function
        node_ids = extract_nodes_from_references(
            constraint.References,
            mesh_obj,
            log_prefix=f'[{constraint_type}] {constraint.Name} - '
        )
        
        if node_ids:
            # Convert node IDs to a sorted comma-separated string
            nodesets[nodeset_name] = ",".join(map(str, sorted(node_ids)))
            log_message('DEBUG', f'Extracted {len(node_ids)} nodes for {nodeset_name}')
        else:
            log_message('WARNING', f'No nodes found for constraint {constraint.Name}')
    
    return nodesets


def write_constraint(f, femobj, fix_obj, ORwriter):
    # floats read from ccx should use {:.13G}, see comment in writer module

    if ORwriter.femmesh.Volumes and (
        len(ORwriter.member.geos_shellthickness) > 0 or len(ORwriter.member.geos_beamsection) > 0
    ):
        if len(femobj["NodesSolid"]) > 0:
            f.write("*BOUNDARY\n")
            f.write(fix_obj.Name + "Solid" + ",1\n")
            f.write(fix_obj.Name + "Solid" + ",2\n")
            f.write(fix_obj.Name + "Solid" + ",3\n")
            f.write("\n")
        if len(femobj["NodesFaceEdge"]) > 0:
            f.write("*BOUNDARY\n")
            f.write(fix_obj.Name + "FaceEdge" + ",1\n")
            f.write(fix_obj.Name + "FaceEdge" + ",2\n")
            f.write(fix_obj.Name + "FaceEdge" + ",3\n")
            f.write(fix_obj.Name + "FaceEdge" + ",4\n")
            f.write(fix_obj.Name + "FaceEdge" + ",5\n")
            f.write(fix_obj.Name + "FaceEdge" + ",6\n")
            f.write("\n")
    else:
        f.write("*BOUNDARY\n")
        f.write(fix_obj.Name + ",1\n")
        f.write(fix_obj.Name + ",2\n")
        f.write(fix_obj.Name + ",3\n")
        if ORwriter.member.geos_beamsection or ORwriter.member.geos_shellthickness:
            f.write(fix_obj.Name + ",4\n")
            f.write(fix_obj.Name + ",5\n")
            f.write(fix_obj.Name + ",6\n")
        f.write("\n")
