# ParaView Integration for OpenRadioss in FreeCAD

## Overview

This implementation adds comprehensive ParaView integration to the OpenRadioss solver in FreeCAD, allowing automatic visualization of analysis results after successful simulation completion.

## Features Implemented

### 1. Automatic ParaView Launch
- ParaView automatically launches after successful OpenRadioss analysis
- Smart detection of result files (.frd, .dat, .h3d, .t01, .t02, etc.)
- Cross-platform ParaView executable detection
- Non-blocking background launch

### 2. User Preferences
- Configurable via FreeCAD preferences: `FEM → OpenRadioss → Launch ParaView After Analysis`
- Solver-specific settings support
- Graceful fallback to default behavior

### 3. Manual Launch Command
- New command: `Launch ParaView` available in FreeCAD
- Allows on-demand visualization without re-running analysis
- Automatic result file detection and loading

### 4. Robust Error Handling
- Checks for ParaView availability before launch
- Handles missing result files gracefully
- Comprehensive logging for troubleshooting

## Files Modified

### `femtools/runORtools.py`
- Added `launch_paraview()` method for ParaView executable detection and launch
- Added `should_launch_paraview()` method for preference checking
- Modified `run()` and `OR_run()` methods to integrate ParaView launch
- Added `launch_paraview_with_results()` method for manual launch

### `femsolver/settings.py`
- Added `PARAVIEW_LAUNCH_PARAM` constant
- Added `get_launch_paraview()` method to _SolverDlg class
- Added `get_launch_paraview()` function for external access

### `femcommands/launch_paraview.py` (NEW)
- New FreeCAD command for manual ParaView launch
- Automatic detection of active OpenRadioss analysis
- User-friendly error messages and success notifications

## Usage

### Automatic Launch
1. Run OpenRadioss analysis in FreeCAD
2. Ensure `Launch ParaView After Analysis` is enabled in preferences
3. After successful completion, ParaView will automatically open with results

### Manual Launch
1. Open FreeCAD with completed OpenRadioss analysis
2. Use `Tools → Launch ParaView` command
3. ParaView will open with available result files

### Configuration
1. Go to `Edit → Preferences → FEM → OpenRadioss`
2. Check/uncheck `Launch ParaView After Analysis`
3. Optionally set custom ParaView executable path

## Supported Result Files

The integration automatically detects and loads:
- `.frd` - OpenRadioss result files
- `.dat` - Data files with analysis results
- `.h3d` - Hierarchical Data Format files
- `.t01`, `.t02`, `.t03`, `.t04` - Time step files
- Additional format support can be easily extended

## Technical Details

### ParaView Detection
The system searches for ParaView in the following order:
1. System PATH (paraview, ParaView commands)
2. Standard installation directories (/usr/bin, /usr/local/bin, /opt/paraview)
3. Platform-specific locations (macOS Applications, Windows Program Files)

### Integration Points
- Automatic launch after `self.load_results()` in successful analysis
- Preference checking via `femsolver.settings.get_launch_paraview()`
- Result file scanning in the working directory
- Non-blocking subprocess launch for smooth user experience

### Error Handling
- Graceful degradation if ParaView not found
- Warning messages for missing result files
- Console logging for debugging
- User-friendly dialog messages

## Benefits

1. **Streamlined Workflow**: Results automatically visualized without manual steps
2. **Cross-Platform**: Works on Linux, Windows, and macOS
3. **User Control**: Configurable via preferences and manual override
4. **Robust**: Handles missing software and files gracefully
5. **Extensible**: Easy to add support for additional result formats

## Console Output Examples

### Successful Launch:
```
OpenRadioss finished without error.
Results loaded successfully. Launching ParaView...
Launching ParaView with 2 result files...
ParaView launched with files: analysis.frd, analysis.dat
```

### ParaView Not Found:
```
OpenRadioss finished without error.
Results loaded successfully. ParaView launch disabled by user preference.
```

### Manual Launch:
```
Manually launching ParaView with analysis results...
ParaView launched with files: analysis.frd, analysis.dat
```

This implementation provides a seamless integration between FreeCAD's OpenRadioss solver and ParaView for result visualization, enhancing the user experience and workflow efficiency.
