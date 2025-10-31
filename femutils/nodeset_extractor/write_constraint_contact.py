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

__title__ = "FreeCAD FEM calculix constraint contact"
__author__ = "Bernd Hahnebach"
__url__ = "https://www.freecad.org"


def get_analysis_types():
    return "all"  # write for all analysis types


def get_sets_name():
    return "constraints_contact_surface_sets"


def get_constraint_title():
    return "Contact Constraints"


def get_before_write_meshdata_constraint():
    return ""


def get_after_write_meshdata_constraint():
    return ""


def get_before_write_constraint():
    return ""


def get_after_write_constraint():
    return ""


def extract_nodesets(analysis, mesh_obj):
    """Extract contact constraint nodesets from the analysis.
    
    Args:
        analysis: The FreeCAD FEM analysis object
        mesh_obj: The FEM mesh object
        
    Returns:
        dict: Dictionary with nodeset name as key and node IDs as value
    """
    nodesets = {}
    
    # Find all contact constraints in the analysis
    contact_constraints = [obj for obj in analysis.Group 
                         if hasattr(obj, 'TypeId') and 
                         obj.TypeId == 'Fem::ConstraintContact']
    
    for constraint in contact_constraints:
        # Create nodesets for both master and slave surfaces
        master_nodeset = f"contact_{constraint.Name}_master"
        slave_nodeset = f"contact_{constraint.Name}_slave"
        
        # Get nodes from the master references
        if hasattr(constraint, 'References') and constraint.References:
            master_node_ids = []
            for (obj, elem) in constraint.References:
                if hasattr(obj, 'getNodeByEdge'):
                    # Get nodes from edges/faces/vertices
                    for e in elem:
                        if 'Edge' in e:
                            master_node_ids.extend(obj.getNodeByEdge(e))
                        elif 'Face' in e:
                            master_node_ids.extend(obj.getNodeByFace(e))
                        elif 'Vertex' in e:
                            master_node_ids.append(obj.getNodeByVertex(e))
            
            if master_node_ids:
                nodesets[master_nodeset] = ",".join(map(str, sorted(set(master_node_ids))))
        
        # Get nodes from the slave references if they exist
        if hasattr(constraint, 'SlaveRef'):
            slave_node_ids = []
            for (obj, elem) in constraint.SlaveRef:
                if hasattr(obj, 'getNodeByEdge'):
                    # Get nodes from edges/faces/vertices
                    for e in elem:
                        if 'Edge' in e:
                            slave_node_ids.extend(obj.getNodeByEdge(e))
                        elif 'Face' in e:
                            slave_node_ids.extend(obj.getNodeByFace(e))
                        elif 'Vertex' in e:
                            slave_node_ids.append(obj.getNodeByVertex(e))
            
            if slave_node_ids:
                nodesets[slave_nodeset] = ",".join(map(str, sorted(set(slave_node_ids))))
    
    return nodesets


def write_meshdata_constraint(f, femobj, contact_obj, ORwriter):
    # slave DEP
    f.write(f"*SURFACE, NAME=DEP{contact_obj.Name}\n")
    for i in femobj["ContactSlaveFaces"]:
        f.write(f"{i[0]},S{i[1]}\n")
    # master IND
    f.write(f"*SURFACE, NAME=IND{contact_obj.Name}\n")
    for i in femobj["ContactMasterFaces"]:
        f.write(f"{i[0]},S{i[1]}\n")


def write_constraint(f, femobj, contact_obj, ORwriter):

    # floats read from ccx should use {:.13G}, see comment in writer module
    adjust = ""
    if contact_obj.Adjust.Value > 0:
        adjust = ", ADJUST={:.13G}".format(contact_obj.Adjust.getValueAs("mm").Value)

    f.write(
        "*CONTACT PAIR, INTERACTION=INT{}, TYPE=SURFACE TO SURFACE{}\n".format(
            contact_obj.Name, adjust
        )
    )
    ind_surf = "IND" + contact_obj.Name
    dep_surf = "DEP" + contact_obj.Name
    f.write(f"{dep_surf}, {ind_surf}\n")
    f.write(f"*SURFACE INTERACTION, NAME=INT{contact_obj.Name}\n")
    f.write("*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR\n")
    slope = contact_obj.Slope.getValueAs("MPa/mm").Value
    f.write(f"{slope:.13G}\n")
    if contact_obj.Friction:
        f.write("*FRICTION\n")
        friction = contact_obj.FrictionCoefficient
        stick = contact_obj.StickSlope.getValueAs("MPa/mm").Value
        f.write(f"{friction:.13G}, {stick:.13G}\n")
