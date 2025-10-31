# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Core functionality for the nodeset extractor

This module provides the core functionality for extracting nodesets from FEM constraints.
"""

import FreeCAD as App
from . import nodeset_utils


def process_analysis(analysis, create_text_object=True, progress_callback=None):
    """Process an analysis and extract nodesets from constraints.
    
    Args:
        analysis: The FreeCAD FEM analysis object
        create_text_object: If True, creates a FreeCAD text document object
        progress_callback: Optional callback function for progress updates
        
    Returns:
        str: The nodeset data as a string
    """
    if progress_callback:
        progress_callback(0, 1, "Starting nodeset extraction...")
    
    # Get the mesh object from analysis
    mesh_obj = None
    for obj in analysis.Group:
        if hasattr(obj, 'Proxy') and hasattr(obj.Proxy, 'Type') and obj.Proxy.Type == 'Fem::FemMeshObject':
            mesh_obj = obj
            break
    
    if not mesh_obj:
        return "No FEM mesh found in the analysis."
    
    # Extract nodesets
    nodeset_data = nodeset_utils.extract_nodesets(analysis, mesh_obj)
    
    if progress_callback:
        progress_callback(1, 1, "Nodeset extraction complete")
    
    return nodeset_data
