"""
Utility functions for nodeset extraction.
"""

import importlib
import os
import sys
import traceback
from pathlib import Path
import FreeCAD
import Part
from FreeCAD import Vector

# Try to import QtCore for potential GUI operations
try:
    from PySide6 import QtCore
except ImportError:
    QtCore = None
    print("[NODESET] [INFO] PySide6.QtCore not available, running in console mode")

# Dictionary mapping constraint types to their module names
CONSTRAINT_MODULES = {
    'Fem::ConstraintFixed': 'write_constraint_fixed',
    'Fem::ConstraintForce': 'write_constraint_force',
    'Fem::ConstraintPressure': 'write_constraint_pressure',
    'Fem::ConstraintContact': 'write_constraint_contact',
    'Fem::ConstraintTie': 'write_constraint_tie',
    'Fem::ConstraintHeatflux': 'write_constraint_heatflux',
    'Fem::ConstraintDisplacement': 'write_constraint_displacement',
    'Fem::ConstraintTemperature': 'write_constraint_temperature',
}

def log_message(level, message):
    #Log a message with the specified log level.
    log_msg = f"[NODESET] [{level}] {message}"
    print(log_msg)
    
    # If we have a console in FreeCAD, write to it
    try:
        import FreeCAD
        if hasattr(FreeCAD, 'Console'):
            if level == 'ERROR':
                FreeCAD.Console.PrintError(log_msg + '\n')
            elif level == 'WARNING':
                FreeCAD.Console.PrintWarning(log_msg + '\n')
            else:
                FreeCAD.Console.PrintLog(log_msg + '\n')
    except Exception:
        pass


def extract_nodes_from_geometry(geometry, mesh_obj, tolerance=1e-7, log_prefix=""):
    """Extract node IDs from geometry that are within tolerance of the mesh.
    
    Args:
        geometry: The geometry to extract nodes from (can be Face, Edge, Vertex, or Shape)
        mesh_obj: The FEM mesh object
        tolerance: Maximum allowed distance between geometry and mesh nodes
        log_prefix: Optional prefix for log messages
        
    Returns:
        set: Set of node IDs that correspond to the geometry within tolerance
    """
    if not hasattr(mesh_obj, 'FemMesh'):
        log_message('ERROR', f"{log_prefix}Mesh object has no FemMesh attribute")
        return set()
        
    fem_mesh = mesh_obj.FemMesh
    node_ids = set()
    
    # Create a bounding box check first for performance
    bbox = geometry.BoundBox
    bbox.enlarge(tolerance)
    
    # Find all nodes within the bounding box
    potential_nodes = []
    for node_id, node in fem_mesh.Nodes.items():
        if bbox.isInside(Vector(node)):
            potential_nodes.append((node_id, Vector(node)))
    
    # For vertices, edges, and faces, we need to check the exact distance
    if geometry.ShapeType == 'Vertex':
        # For vertices, just check distance to the point
        point = geometry.Point
        for node_id, node_pos in potential_nodes:
            if (node_pos - point).Length <= tolerance:
                node_ids.add(node_id)
        
    elif geometry.ShapeType in ['Edge', 'Face']:
        # For edges and faces, check distance to the geometry
        for node_id, node_pos in potential_nodes:
            dist = geometry.distToShape(Part.Vertex(node_pos))[0]
            if dist <= tolerance:
                node_ids.add(node_id)
                
    elif geometry.ShapeType in ['Solid', 'Compound', 'Shell']:
        # For solids and compounds, check distance to the shape
        for node_id, node_pos in potential_nodes:
            dist = geometry.distToShape(Part.Vertex(node_pos))[0]
            if dist <= tolerance:
                node_ids.add(node_id)
    
    log_message('DEBUG', f"{log_prefix}Found {len(node_ids)} nodes on {geometry.ShapeType} within {tolerance} tolerance")
    return node_ids

def extract_nodes_from_references(references, mesh_obj, log_prefix=""):
    #Extract node IDs from geometry references using the mesh object.
    
    #Args:
    #    references: #List of (object, element_list) tuples from constraint.References
    #    mesh_obj: #The FEM mesh object
    #    log_prefix: #Optional prefix for log messages
        
    #Returns:
    #    set: #Set of node IDs that correspond to the geometry references

    if not references:
        log_message('WARNING', f"{log_prefix}No references provided")
        return set()
        
    if not hasattr(mesh_obj, 'FemMesh'):
        log_message('ERROR', f"{log_prefix}Mesh object has no FemMesh attribute")
        return set()
        
    fem_mesh = mesh_obj.FemMesh
    node_ids = set()
    
    for ref_idx, (part_obj, elem_list) in enumerate(references):
        log_message('DEBUG', f"{log_prefix}Processing reference {ref_idx}: {part_obj.Name if hasattr(part_obj, 'Name') else part_obj}, elements: {elem_list}")
        
        if not hasattr(part_obj, 'Shape'):
            log_message('WARNING', f"{log_prefix}Reference object has no Shape attribute")
            continue
            
        # Get the part object that defines the constraint
        part_shape = part_obj.Shape
        
        # If no specific elements are provided, use the whole shape
        if not elem_list:
            log_message('DEBUG', f"{log_prefix}No elements specified, using entire shape")
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
                log_message('ERROR', f"{log_prefix}Error processing element {elem}: {str(e)}")
                log_message('DEBUG', f"{log_prefix}{traceback.format_exc()}")
                
                # Fallback to the old method if the new one fails
                try:
                    log_message('DEBUG', f"{log_prefix}Falling back to legacy node extraction for {elem}")
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
                    log_message('DEBUG', f"{log_prefix}Legacy method found {len(element_nodes)} nodes for {elem}")
                    
                except Exception as e2:
                    log_message('ERROR', f"{log_prefix}Legacy method also failed for {elem}: {str(e2)}")
    
    log_message('DEBUG', f"{log_prefix}Found {len(node_ids)} total nodes from references")
    return node_ids

def import_constraint_module(module_name):
    #Dynamically import a constraint module.
    try:
        full_module_name = f'femutils.nodeset_extractor.{module_name}'
        log_message('DEBUG', f'Importing module: {full_module_name}')
        module = importlib.import_module(full_module_name)
        if hasattr(module, 'extract_nodesets'):
            log_message('DEBUG', f'Found extract_nodesets in {full_module_name}')
            return module.extract_nodesets
        else:
            log_message('WARNING', f'Module {full_module_name} has no extract_nodesets function')
    except ImportError as e:
        log_message('WARNING', f'Failed to import {module_name}: {str(e)}')
    except Exception as e:
        log_message('ERROR', f'Error importing {module_name}: {str(e)}')
        log_message('DEBUG', traceback.format_exc())
    return None

# Pre-import all constraint modules
CONSTRAINT_EXTRACTORS = {}
for const_type, module_name in CONSTRAINT_MODULES.items():
    extractor = import_constraint_module(module_name)
    if extractor:
        CONSTRAINT_EXTRACTORS[const_type] = extractor
        log_message('INFO', f'Loaded extractor for {const_type} from {module_name}')
    else:
        log_message('WARNING', f'No extractor available for {const_type} ({module_name})')

def extract_nodesets(analysis, mesh_obj, create_text_object=False, progress_callback=None):
    #Extract nodesets from analysis and return as a string.
    
    #This function uses constraint-specific extractors to get nodesets from all
    #constraints in the analysis.
    
    #Args:
    #    analysis: The FreeCAD FEM analysis object
    #    mesh_obj: The FEM mesh object
    #    create_text_object: If True, creates a FreeCAD text document object
    #    progress_callback: Optional callback function for progress updates
        
    #Returns:
    #    str: The nodeset data as a formatted string, or empty string if no nodesets found

    nodesets = {}
    
    if not hasattr(analysis, 'Group') or not analysis.Group:
        log_message('WARNING', 'Analysis has no group or is empty')
        return ""
    
    log_message('INFO', f'Found {len(analysis.Group)} objects in analysis group')
    
    # Process each constraint in the analysis
    for i, obj in enumerate(analysis.Group):
        if not hasattr(obj, 'TypeId'):
            log_message('DEBUG', f'Object {i} has no TypeId, skipping: {obj}')
            continue
            
        log_message('DEBUG', f'Processing object {i}: {obj.TypeId} - {obj.Name if hasattr(obj, 'Name') else 'Unnamed'}')
        
        # Use the appropriate extractor for this constraint type
        extractor = CONSTRAINT_EXTRACTORS.get(obj.TypeId)
        if extractor:
            try:
                log_message('DEBUG', f'Extracting nodesets for {obj.TypeId} - {obj.Name if hasattr(obj, 'Name') else 'Unnamed'}')
                constraint_nodesets = extractor(analysis, mesh_obj)
                if constraint_nodesets and isinstance(constraint_nodesets, dict):
                    log_message('INFO', f'Extracted {len(constraint_nodesets)} nodesets from {obj.TypeId} - {obj.Name if hasattr(obj, 'Name') else 'Unnamed'}')
                    nodesets.update(constraint_nodesets)
                else:
                    log_message('DEBUG', f'No nodesets extracted from {obj.TypeId} - {obj.Name if hasattr(obj, 'Name') else 'Unnamed'}')
            except Exception as e:
                log_message('ERROR', f'Error processing {obj.TypeId} - {obj.Name if hasattr(obj, 'Name') else 'Unnamed'}: {str(e)}')
                log_message('DEBUG', traceback.format_exc())
        else:
            log_message('DEBUG', f'No extractor available for {obj.TypeId}')
            
        # Update progress if callback is provided
        if progress_callback and hasattr(progress_callback, '__call__'):
            if not progress_callback(i + 1, len(analysis.Group), f'Processing {obj.TypeId}...'):
                log_message('INFO', 'Nodeset extraction cancelled by user')
                return ""
    
    if not nodesets:
        log_message('WARNING', 'No nodesets were extracted from constraints')
        return ""
    
    log_message('INFO', f'Extracted a total of {len(nodesets)} nodesets')
    
    # Format the nodesets as a string
    result = []
    for name, nodes in nodesets.items():
        result.append(f"$NODESET/{name}")
        # Write nodes in chunks of 10 for better readability
        for i in range(0, len(nodes), 10):
            chunk = nodes[i:i+10]
            result.append(" ".join(map(str, chunk)))
        result.append("")
    
    return "\n".join(result)