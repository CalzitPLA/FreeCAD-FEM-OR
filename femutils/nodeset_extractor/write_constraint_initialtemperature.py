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

__title__ = "FreeCAD FEM calculix constraint initialtemperature"
__author__ = "Bernd Hahnebach"
__url__ = "https://www.freecad.org"

from FreeCAD import Units


def get_analysis_types():
    return ["thermomech"]


def get_constraint_title():
    return "Initial temperature constraint"


def get_before_write_constraint():
    return ""


def get_after_write_constraint():
    return ""


def write_meshdata_constraint(f, femobj, inittemp_obj, ORwriter):
    # For OpenRadioss, we'll write a nodeset for the initial temperature
    # Format: $NODESET/constraint_name
    f.write(f"$NODESET/{inittemp_obj.Name}\n")
    
    # Write all nodes in the constraint
    if "Nodes" in femobj:
        # Write nodes in chunks of 10 for better readability
        nodes = femobj["Nodes"]
        for i in range(0, len(nodes), 10):
            chunk = nodes[i:i+10]
            f.write(" ".join(map(str, chunk)) + "\n")
    
    # Add a blank line after the nodeset
    f.write("\n")


def write_constraint(f, femobj, inittemp_obj, ORwriter):
    # For OpenRadioss, we'll write the initial temperature as a /INIT/TEMPERATURE card
    # Format: $INIT_TEMP/constraint_name
    temp_value = Units.Quantity(inittemp_obj.initialTemperature.getValueAs("K"))
    
    f.write(f"$INIT_TEMP/{inittemp_obj.Name}\n")
    f.write(f"{temp_value}\n\n")  # Add extra newline for separation


def extract_nodesets(analysis, mesh_obj):
    """Extract initial temperature nodesets from the analysis.
    
    Args:
        analysis: The FreeCAD FEM analysis object
        mesh_obj: The FEM mesh object
        
    Returns:
        dict: Dictionary with nodeset name as key and node IDs as value
    """
    nodesets = {}
    
    # Find all initial temperature constraints in the analysis
    temp_constraints = [obj for obj in analysis.Group 
                       if hasattr(obj, 'TypeId') and obj.TypeId == 'Fem::ConstraintInitialTemperature']
    
    for constraint in temp_constraints:
        nodeset_name = f"temp_init_{constraint.Name}"
        
        # Get all nodes from the mesh (since initial temp is typically applied to all nodes)
        if hasattr(mesh_obj, 'FemMesh'):
            node_ids = [node for node in mesh_obj.FemMesh.Nodes]
            if node_ids:
                nodesets[nodeset_name] = ",".join(map(str, sorted(node_ids)))
    
    return nodesets
