#!/usr/bin/env python3
"""
Clean up the Fem_upgraded workbench by removing unnecessary files.
This script will keep only the essential files for the workbench to function.
"""

import os
import shutil
from pathlib import Path

# Base directory
base_dir = Path(__file__).parent.absolute()

# Essential files and directories to keep
ESSENTIAL_FILES = [
    'Init.py',
    'InitGui.py',
    'ObjectsFem.py',
    'Resources',
    'femcommands',
    'femexamples',
    'femguiobjects',
    'femguiutils',
    'feminout',
    'femmesh',
    'femobjects',
    'femresult',
    'femsolver',
    'femtools',
    'femviewprovider',
    'gui',
    'README_OpenRadioss_Keyword_Editor.md',
    'README_OpenRadioss_Macro.md',
    'templates.json',
    'openradioss_paraview_launcher.sh',
    'openradioss_test.FCMacro',
    'or_test.sh',
    'paraview_oneliner.sh',
    'run_openradioss_starter.py',
    'openradioss_debug_command.py',
    'coding_conventions.md',
    'openradioss_cfg_analysis.md',
    'openradioss_cfg_workflow.md',
    'PARAVIEW_INTEGRATION_README.md',
    'ENHANCED_FORMAT_DETECTION.md',
    'HM_READER_INTEGRATION.md',
    'BACKUP_HISTORY_README.md',
]

# File extensions to keep (in addition to essential files)
KEEP_EXTENSIONS = {
    '.md',  # Markdown files
    '.json',  # JSON configuration
    '.sh',  # Shell scripts
    '.FCMacro',  # FreeCAD macros
    '.k',  # Radioss input files
}

def is_essential(path):
    """Check if a path is in the essential files list."""
    rel_path = str(Path(path).relative_to(base_dir))
    
    # Check if it's in the essential files list
    if rel_path in ESSENTIAL_FILES:
        return True
        
    # Check if it's in an essential directory
    for essential_dir in ESSENTIAL_FILES:
        if rel_path.startswith(essential_dir + os.sep):
            return True
            
    # Check file extension
    if Path(path).suffix.lower() in KEEP_EXTENSIONS:
        return True
        
    return False

def cleanup():
    """Clean up the workbench directory."""
    print("Starting cleanup of Fem_upgraded workbench...")
    
    # Create a list of all files and directories
    all_items = []
    for root, dirs, files in os.walk(base_dir, topdown=False):
        # Add files
        for name in files:
            all_items.append(Path(root) / name)
        # Add directories
        for name in dirs:
            all_items.append(Path(root) / name)
    
    # Process items to remove
    removed_count = 0
    for item in all_items:
        try:
            # Skip the cleanup script itself
            if item.name == 'cleanup_workbench.py':
                continue
                
            # Skip if it's an essential file or directory
            if is_essential(item):
                continue
                
            # Handle files and directories
            if item.is_file() or item.is_symlink():
                print(f"Removing file: {item}")
                item.unlink()
                removed_count += 1
            elif item.is_dir():
                # Check if directory is empty
                if not any(item.iterdir()):
                    print(f"Removing empty directory: {item}")
                    item.rmdir()
                    removed_count += 1
                else:
                    print(f"Skipping non-empty directory: {item}")
                    
        except Exception as e:
            print(f"Error processing {item}: {e}")
    
    print(f"\nCleanup complete. Removed {removed_count} items.")
    print("The workbench should now be cleaned up with only essential files remaining.")

if __name__ == "__main__":
    # Ask for confirmation
    confirm = input("This will remove non-essential files from the Fem_upgraded workbench. Continue? (y/N): ")
    if confirm.lower() == 'y':
        cleanup()
    else:
        print("Cleanup cancelled.")
