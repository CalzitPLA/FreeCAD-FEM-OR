# OpenRadioss Backup History Feature

This feature tracks all backup operations performed by the OpenRadioss solver in FreeCAD.

## Features

- **Automatic Tracking**: All backup operations are automatically recorded
- **Local Storage**: Backup history is stored in the same directory as your K-files (`openradioss_backup_history.json`)
- **JSON Storage**: Backup history stored in easy-to-read JSON format
- **File Details**: Records original names, backup names, and file sizes
- **Timestamped**: Each backup entry includes a timestamp
- **History Limit**: Keeps only the last 50 backup operations to prevent file bloat

## JSON Structure

```json
{
  "backup_history": [
    {
      "timestamp": "20251022_170348",
      "working_directory": "/path/to/working/directory",
      "backup_directory": "/path/to/working/directory/fem_backup_20251022_170348",
      "files_backed_up": [
        {
          "original_name": "fem_export.k",
          "backup_name": "fem_export.k",
          "size_bytes": 12345
        },
        {
          "original_name": "fem_export_0001.rad",
          "backup_name": "fem_export_0001.rad",
          "size_bytes": 67890
        }
      ]
    }
  ]
}
```

## Usage

1. **View History**: Click the "Backup History" button in the OpenRadioss task panel
2. **Automatic Recording**: Backup history is automatically saved when:
   - Update K File button is clicked
   - Test Solver button is clicked
   - Solve button is clicked

## Backup Logic

- **Unique Names**: If files already exist in backup directory, unique names are created (e.g., `fem_export_1.k`, `fem_export_2.k`)
- **Complete Tracking**: Records all file types: `.k`, `.rad`, `.rst`, `.h5`, `.out`, `.msg`, `.sta`
- **Error Handling**: Gracefully handles file system errors and missing files
- **Project-Specific**: Each project has its own backup history file next to the K-files

## History Management

- **Location**: `openradioss_backup_history.json` (stored in your working directory next to K-files)
- **Rotation**: Automatically removes old entries (keeps last 50)
- **Persistent**: History survives FreeCAD restarts
- **Safe**: Creates backup directory if it doesn't exist
- **Per-Project**: Each project maintains its own history file

## Advanced Features

### **Smart Bash Script Integration**
The bash script (used when FreeCAD execution fails) now **automatically reads the backup history JSON** to find the correct location of your updated K-file:

```bash
# Reads openradioss_backup_history.json
# Finds the most recent backup entry  
# Uses the working_directory field as the source location
# Copies the correct K-file to /tmp for execution
```

This ensures the external script uses the **exact same location** where the backup history recorded your files, eliminating location inconsistencies.

### **Dynamic Path Construction**
The bash script now uses **dynamic path building** equivalent to Python's `os.path.join()`:

```bash
# Python equivalent: os.path.join(working_dir, 'fem_export.k')
# Bash equivalent: Dynamic construction using variables
HISTORY_FILE="${working_dir}/openradioss_backup_history.json"
```

This ensures consistent path handling between Python and bash environments.

### **Automatic JSON Creation**
The system now **automatically creates the backup history JSON file** if it doesn't exist:

- ✅ **On Update K File**: Creates JSON before saving backup history
- ✅ **On Test Solver**: Creates JSON before saving backup history
- ✅ **On Solve**: Creates JSON before saving backup history
- ✅ **On Keyword Editor Save**: Creates JSON and tracks the save operation

### **Automatic Location Detection**
The system now supports:
- **Primary**: Read from backup history JSON (most accurate)
- **Secondary**: Dynamic path construction using `os.path.join()` logic
- **Fallback**: Check current working directory
- **Final Fallback**: Use test file if no updated K-file found

## Troubleshooting

### **Location Mismatch Fixed**
Previously, there was a mismatch between:
- **Python backup functions**: Saved JSON in `analysis.WorkingDir`
- **Bash script**: Looked for JSON in current directory (`/tmp`)

**Fixed**: Bash script now looks for JSON in the same `working_dir` where Python saves it.

## Troubleshooting

### **Location Mismatch Fixed**
Previously, there was a mismatch between:
- **Python backup functions**: Saved JSON in `analysis.WorkingDir`
- **Bash script**: Looked for JSON in current directory (`/tmp`)

**Fixed**: Bash script now looks for JSON in the same `working_dir` where Python saves it.

## Troubleshooting

### **Location Mismatch Fixed**
Previously, there was a mismatch between:
- **Python backup functions**: Saved JSON in `analysis.WorkingDir`
- **Bash script**: Looked for JSON in current directory (`/tmp`)

**Fixed**: Bash script now looks for JSON in the same `working_dir` where Python saves it.

### **Directory Change Issue Fixed**
**Problem**: The bash script was changing to `/tmp` directory before finding the K-file, causing it to look in the wrong location.

**Solution**: The script now:
1. ✅ Looks for JSON in working directory first
2. ✅ Reads the correct K-file location from backup history  
3. ✅ Copies the K-file from the right location to `/tmp`
4. ✅ Only then changes to `/tmp` for execution

### **Enhanced Debugging Output**
The bash script now provides detailed output showing:
- ✅ Working directory from FreeCAD
- ✅ JSON file location being checked
- ✅ K-file locations being searched
- ✅ Clear success/failure messages with emoji indicators
- ✅ Helpful guidance when files aren't found

### **JSON Creation**
If you see "No backup history file found", run any backup operation (Update/Test/Solve) to create the JSON file in your working directory.

## Bash Script Flow

```bash
# 1. Look for JSON in working directory
HISTORY_FILE="${working_dir}/openradioss_backup_history.json"

# 2. If found, read most recent backup entry
# 3. Get K-file location from JSON data
# 4. Copy K-file to /tmp
# 5. Change to /tmp and execute OpenRadioss
```

## Complete Function List

The backup history system now includes all required functions:

- ✅ `get_backup_history_file()` - Get JSON file path
- ✅ `ensure_backup_history_exists()` - Create JSON if missing
- ✅ `save_backup_history()` - Save backup operations
- ✅ `get_backup_history()` - Read backup history
- ✅ `show_backup_history()` - Display history dialog
- ✅ `on_keyword_editor_save()` - Track editor saves
