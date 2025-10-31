"""
FEM Task Panels for FreeCAD

This package contains task panels for various FEM tools and solvers.
"""

from .task_solver_openradioss import _TaskPanel as OpenRadiossTaskPanel
from .task_nodeset_extractor import _TaskPanel as NodesetExtractorTaskPanel

__all__ = ['OpenRadiossTaskPanel', 'NodesetExtractorTaskPanel']