# FreeCAD FEM Workbench

[![License: LGPL v2+](https://img.shields.io/badge/License-LGPL%20v2+-blue.svg)](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html)
[![FreeCAD Version](https://img.shields.io/badge/FreeCAD-0.20%2B-brightgreen)](https://www.freecad.org/)

## Overview

The FreeCAD FEM Workbench provides a complete Finite Element Analysis (FEA) workflow within FreeCAD. This document covers the key components and their integration:

- **Keyword Editor**: For editing solver-specific input files
- **Nodeset Extractor**: For creating and managing node sets from geometry
- **Solver Integration**: For executing and monitoring analyses

## Installation

1. Clone this repository into your FreeCAD Mod directory:
   ```bash
   git clone https://github.com/yourusername/Fem_upgraded.git /path/to/FreeCAD/Mod/Fem_upgraded
   ```
2. Restart FreeCAD
3. Select the FEM workbench from the workbench selector

## Features

### Keyword Editor
- Edit solver input files with syntax highlighting
- Support for multiple solvers (CalculiX, OpenRadioss, etc.)
- Template-based configuration
- Validation of input parameters

### Nodeset Extractor
- Automatic node set creation from geometry
- Support for various constraint types:
  - Force constraints
  - Displacement constraints
  - Temperature constraints
  - Pressure loads
- Visualization of node sets
- Export/import capabilities

### Solver Integration
- Seamless execution of analyses
- Progress monitoring
- Error handling and logging
- Support for multiple solvers

## Quick Start

### 1. Model Setup
1. Create or import your geometry in FreeCAD
2. Switch to the FEM workbench
3. Create a new analysis

### 2. Define Materials and Constraints
1. Add material properties
2. Apply boundary conditions
3. Define loads and constraints

### 3. Extract Node Sets
1. Select the geometry for your node sets
2. Use the Nodeset Extractor to create node sets
3. Verify the node sets in the 3D view

### 4. Configure Solver
1. Open the Keyword Editor
2. Configure solver parameters
3. Save the input file

### 5. Run Analysis
1. Execute the solver
2. Monitor progress in the console
3. View and analyze results

## Example Usage

```python
import FreeCAD
from femutils.nodeset_extractor import extract_nodesets

# Get the active document
doc = FreeCAD.ActiveDocument

# Extract nodesets from analysis
analysis = doc.Analysis
mesh_obj = doc.Mesh
nodesets = extract_nodesets(analysis, mesh_obj)

# Print extracted nodesets
for name, nodes in nodesets.items():
    print(f"{name}: {nodes}")
```

## Documentation

For detailed documentation, see the [Documentation](docs/fem_workbench_documentation.pdf).

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This work is licensed under the [LGPLv2.1+ License](LICENSE).

## Support

For support, please open an issue on our [GitHub repository](https://github.com/yourusername/Fem_upgraded/issues).

## Acknowledgments

- The FreeCAD development team
- All contributors to the FEM workbench
- The open-source community for their support and contributions
