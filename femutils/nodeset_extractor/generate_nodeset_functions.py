"""
Helper script to generate extract_nodesets functions for all constraint writers.
Run this script to update all constraint writer files with the extract_nodesets function.
"""

import os
import re

# Template for the extract_nodesets function
template = """def extract_nodesets(analysis, mesh_obj):
    \"\"\"Extract {constraint_name} nodesets from the analysis.
    
    Args:
        analysis: The FreeCAD FEM analysis object
        mesh_obj: The FEM mesh object
        
    Returns:
        dict: Dictionary with nodeset name as key and node IDs as value
    \"\"\"
    nodesets = {{}}
    
    # Find all {constraint_name} constraints in the analysis
    constraints = [obj for obj in analysis.Group 
                  if hasattr(obj, 'TypeId') and 
                  obj.TypeId == '{constraint_type}']
    
    for constraint in constraints:
        nodeset_name = "{prefix}_{{}}".format(constraint.Name)
        
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
                nodesets[nodeset_name] = ",".join(map(str, sorted(set(node_ids))))
    
    return nodesets
"""

# Mapping of constraint types to their prefixes and full type names
constraint_types = {
    'write_constraint_bodyheatsource.py': {
        'prefix': 'bodyheatsource',
        'type': 'Fem::ConstraintBodyHeatSource'
    },
    'write_constraint_centrif.py': {
        'prefix': 'centrif',
        'type': 'Fem::ConstraintCentrif'
    },
    'write_constraint_contact.py': {
        'prefix': 'contact',
        'type': 'Fem::ConstraintContact'
    },
    'write_constraint_displacement.py': {
        'prefix': 'disp',
        'type': 'Fem::ConstraintDisplacement'
    },
    'write_constraint_fixed.py': {
        'prefix': 'fixed',
        'type': 'Fem::ConstraintFixed'
    },
    'write_constraint_fluidsection.py': {
        'prefix': 'fluidsection',
        'type': 'Fem::ConstraintFluidBoundary'
    },
    'write_constraint_force.py': {
        'prefix': 'force',
        'type': 'Fem::ConstraintForce'
    },
    'write_constraint_heatflux.py': {
        'prefix': 'heatflux',
        'type': 'Fem::ConstraintHeatflux'
    },
    'write_constraint_initialtemperature.py': {
        'prefix': 'initialtemp',
        'type': 'Fem::ConstraintInitialTemperature'
    },
    'write_constraint_planerotation.py': {
        'prefix': 'planerot',
        'type': 'Fem::ConstraintPlaneRotation'
    },
    'write_constraint_pressure.py': {
        'prefix': 'pressure',
        'type': 'Fem::ConstraintPressure'
    },
    'write_constraint_radioss.py': {
        'prefix': 'radioss',
        'type': 'Fem::ConstraintRadioss'
    },
    'write_constraint_rigidbody.py': {
        'prefix': 'rigidbody',
        'type': 'Fem::ConstraintRigidBody'
    },
    'write_constraint_rigidbody_step.py': {
        'prefix': 'rigidbody_step',
        'type': 'Fem::ConstraintRigidBodyStep'
    },
    'write_constraint_sectionprint.py': {
        'prefix': 'sectionprint',
        'type': 'Fem::ConstraintSectionPrint'
    },
    'write_constraint_selfweight.py': {
        'prefix': 'selfweight',
        'type': 'Fem::ConstraintSelfWeight'
    },
    'write_constraint_temperature.py': {
        'prefix': 'temp',
        'type': 'Fem::ConstraintTemperature'
    },
    'write_constraint_tie.py': {
        'prefix': 'tie',
        'type': 'Fem::ConstraintTie'
    },
    'write_constraint_transform.py': {
        'prefix': 'transform',
        'type': 'Fem::ConstraintTransform'
    }
}

def update_constraint_file(file_path, constraint_info):
    """Update a constraint file with the extract_nodesets function."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Skip if extract_nodesets already exists
    if 'def extract_nodesets(' in content:
        print(f"Skipping {file_path} - extract_nodesets already exists")
        return
    
    # Find the last function definition
    last_func_match = list(re.finditer(r'def \w+\s*\(', content))
    if not last_func_match:
        print(f"Warning: No functions found in {file_path}")
        return
    
    last_func_pos = last_func_match[-1].end()
    insert_pos = content.find('\n', content.find(')', last_func_pos)) + 1
    
    # Generate the function
    func = template.format(
        constraint_name=constraint_info['prefix'],
        constraint_type=constraint_info['type'],
        prefix=constraint_info['prefix']
    )
    
    # Insert the function
    new_content = content[:insert_pos] + '\n\n' + func + content[insert_pos:]
    
    # Write the updated content back to the file
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Updated {file_path}")

def main():
    """Main function to update all constraint files."""
    dir_path = os.path.dirname(os.path.abspath(__file__))
    
    for filename, constraint_info in constraint_types.items():
        file_path = os.path.join(dir_path, filename)
        if os.path.exists(file_path):
            update_constraint_file(file_path, constraint_info)
        else:
            print(f"Warning: File not found: {file_path}")

if __name__ == "__main__":
    main()
