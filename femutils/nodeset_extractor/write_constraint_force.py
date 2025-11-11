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

__title__ = "FreeCAD FEM calculix constraint force"
__author__ = "Bernd Hahnebach"
__url__ = "https://www.freecad.org"


def get_analysis_types():
    return ["buckling", "static", "thermomech"]


def get_sets_name():
    return "constraints_force_node_loads"


def get_before_write_meshdata_constraint():
    return "*CLOAD\n"


def get_after_write_meshdata_constraint():
    return ""


def extract_nodes_from_references(references, mesh_obj, log_prefix=""):
    """Extract node IDs from geometry references using the mesh object.
    
    Args:
        references: List of (object, element_list) tuples from constraint.References
        mesh_obj: The FEM mesh object
        log_prefix: Optional prefix for log messages
        
    Returns:
        set: Set of node IDs that correspond to the geometry references
    """
    if not references:
        print(f"{log_prefix}[WARNING] No references provided")
        return set()
        
    if not hasattr(mesh_obj, 'FemMesh'):
        print(f"{log_prefix}[ERROR] Mesh object has no FemMesh attribute")
        return set()
        
    fem_mesh = mesh_obj.FemMesh
    node_ids = set()
    
    for ref_idx, (part_obj, elem_list) in enumerate(references):
        print(f"{log_prefix}[DEBUG] Processing reference {ref_idx}: {part_obj.Name if hasattr(part_obj, 'Name') else part_obj}, elements: {elem_list}")
        
        if not hasattr(part_obj, 'Shape'):
            print(f"{log_prefix}[WARNING] Reference object has no Shape attribute")
            continue
            
        # Get the part object that defines the constraint
        part_shape = part_obj.Shape
        
        # If no specific elements are provided, use the whole shape
        if not elem_list:
            print(f"{log_prefix}[DEBUG] No elements specified, using entire shape")
            element_nodes = extract_nodes_from_geometry(part_shape, mesh_obj, log_prefix=log_prefix)
            node_ids.update(element_nodes)
            continue
            
        # Process each element in the reference
        for elem in elem_list:
            try:
                # Get the sub-element (face, edge, or vertex)
                element = part_shape.getElement(elem)
                
                # Extract nodes from this element with proper tolerance checking
                element_nodes = extract_nodes_from_geometry(element, mesh_obj, log_prefix=f"{log_prefix}[{elem}] ")
                node_ids.update(element_nodes)
                
            except Exception as e:
                print(f"{log_prefix}[ERROR] Error processing element {elem}: {str(e)}")
                print(f"{log_prefix}[DEBUG] {traceback.format_exc()}")
                
                # Fallback to the old method if the new one fails
                try:
                    print(f"{log_prefix}[DEBUG] Falling back to legacy node extraction for {elem}")
                    element = part_shape.getElement(elem)
                    element_nodes = set()
                    
                    # Bounding box check first for performance
                    bbox = element.BoundBox
                    bbox.enlarge(1e-6)  # Small tolerance for floating point inaccuracies
                    
                    for node_id, node in fem_mesh.Nodes.items():
                        if bbox.isInside(Vector(node)):
                            if element.distToShape(Part.Vertex(node))[0] < 1e-6:
                                element_nodes.add(node_id)
                    
                    node_ids.update(element_nodes)
                    print(f"{log_prefix}[DEBUG] Legacy method found {len(element_nodes)} nodes for {elem}")
                    
                except Exception as e2:
                    print(f"{log_prefix}[ERROR] Legacy method also failed for {elem}: {str(e2)}")
    
    print(f"{log_prefix}[DEBUG] Found {len(node_ids)} total nodes from references")
    return node_ids

def extract_nodesets(analysis, mesh_obj):
    """Extract force constraint nodesets from the analysis.
    
    Args:
        analysis: The FreeCAD FEM analysis object
        mesh_obj: The FEM mesh object
        
    Returns:
        dict: Dictionary with nodeset name as key and node IDs as value
    """
    nodesets = {}
    
    # Find all force constraints in the analysis
    force_constraints = [obj for obj in analysis.Group 
                       if hasattr(obj, 'TypeId') and 
                       obj.TypeId == 'Fem::ConstraintForce']
    
    for constraint in force_constraints:
        nodeset_name = f"force_{constraint.Name}"
        
        # Get nodes from the constraint references
        if hasattr(constraint, 'References') and constraint.References:
            node_ids = extract_nodes_from_references(constraint.References, mesh_obj, log_prefix=f"[ForceConstraint {constraint.Name}] ")
            if node_ids:
                nodesets[nodeset_name] = ",".join(map(str, sorted(node_ids)))
    
    return nodesets


def write_meshdata_constraint(f, femobj, force_obj, ORwriter):
    """Write constraint data for force constraints.
    
    Args:
        f: File object to write to
        femobj: The FEM object containing the constraint data
        force_obj: The force constraint object
        ORwriter: The OpenRadioss writer instance
    """
    # floats read from ccx should use {:.13G}, see comment in writer module
    direction_vec = femobj["Object"].DirectionVector
    dir_zero_tol = 1e-15  # TODO: should this be more generally for more values?
    # be careful with raising the tolerance, a big load would have an impact
    # but compared to the real direction the impact would be small again
    for ref_shape in femobj["NodeLoadTable"]:
        f.write(f"** {ref_shape[0]}\n")
        for n in sorted(ref_shape[1]):
            node_load = ref_shape[1][n]
            # the loads in ref_shape[1][n] are without unit
            if abs(direction_vec.x) > dir_zero_tol:
                v1 = f"{(direction_vec.x * node_load).Value:.13G}"
                f.write(f"{n},1,{v1}\n")
            if abs(direction_vec.y) > dir_zero_tol:
                v2 = f"{(direction_vec.y * node_load).Value:.13G}"
                f.write(f"{n},2,{v2}\n")
            if abs(direction_vec.z) > dir_zero_tol:
                v3 = f"{(direction_vec.z * node_load).Value:.13G}"
                f.write(f"{n},3,{v3}\n")
        f.write("\n")
    f.write("\n")
