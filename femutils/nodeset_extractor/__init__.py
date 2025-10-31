# SPDX-License-Identifier: LGPL-2.1-or-later

"""
Nodeset Extractor for FreeCAD FEM

This module provides functionality to extract nodesets from FEM constraints.
"""

# Import the main functionality
from .core import process_analysis
from .nodeset_utils import extract_nodesets

# Import GUI components in a way that avoids circular imports
NodesetExtractorCommand = None
def _import_gui():
    global NodesetExtractorCommand
    if NodesetExtractorCommand is None:
        from .gui import NodesetExtractorCommand as Cmd
        NodesetExtractorCommand = Cmd
    return NodesetExtractorCommand

# Make the main functions available at package level
__all__ = ['extract_nodesets', 'process_analysis', 'NodesetExtractorCommand']
