# OpenRadioss CFG File Processing Analysis

## CFG File Structure and Processing

Based on the review of OpenRadioss documentation and source structure, here's how CFG files are processed:

### 1. **Environment Setup**
```bash
export OPENRADIOSS_PATH=/path/to/openradioss
export RAD_CFG_PATH=$OPENRADIOSS_PATH/hm_cfg_files
export LD_LIBRARY_PATH=$OPENRADIOSS_PATH/extlib/hm_reader/linux64/:$LD_LIBRARY_PATH
```

The `RAD_CFG_PATH` points to the directory containing all `.cfg` files that define keyword syntax.

### 2. **HM Reader Library Processing**

OpenRadioss uses an external **HM Reader Library** (HyperMesh reader) that processes CFG files and builds an internal database. The workflow is:

1. **Starter/Engine Execution**: When OpenRadioss starter runs, it loads the HM reader library
2. **CFG File Scanning**: HM reader scans all `.cfg` files in `RAD_CFG_PATH` 
3. **Database Construction**: Creates an internal database of all keyword definitions
4. **Runtime Querying**: Starter queries this database to validate and process keywords from `.k` files

### 3. **Key HM Reader Functions**

From the documentation, the main functions are:

```fortran
! Count keywords
N = HM_OPTION_COUNT('/PART')

! Start reading section
CALL HM_OPTION_START('/PART')

! Read each occurrence
DO I = 1, N
    CALL HM_OPTION_READ_KEY('/PART', KEY1, KEY2, KEY3, KEY4, ID, UID, TITLE)
    
    ! Get parameter values
    CALL HM_GET_INTV('PID', PID)
    CALL HM_GET_FLOATV('RHO', RHO)
    CALL HM_GET_STRING('TITLE', TITLE)
ENDDO
```

### 4. **CFG File Structure Analysis**

From examining the actual CFG files, each keyword is defined with:

#### **ATTRIBUTES Section**
```cfg
ATTRIBUTES(COMMON) {
    PID     = VALUE(INT, "Part ID");
    RHO     = VALUE(FLOAT, "Density");
    E       = VALUE(FLOAT, "Young modulus");
    NU      = VALUE(FLOAT, "Poisson ratio");
}
```

#### **GUI Section**
```cfg
GUI(COMMON) {
    mandatory:
        SCALAR(PID) { DIMENSION="dimensionless"; }
        SCALAR(RHO) { DIMENSION="density"; }
    optional:
        SCALAR(E)   { DIMENSION="pressure"; }
        SCALAR(NU)  { DIMENSION="dimensionless"; }
}
```

#### **FORMAT Section**
```cfg
FORMAT(radioss2026) {
    HEADER("*PART/%s", TITLE);
    COMMENT("$      PID");
    CARD("%10d", PID);
    COMMENT("$      RHO         E        NU");
    CARD("%10lg%10lg%10lg", RHO, E, NU);
}
```

### 5. **Directory Organization**

The CFG files are organized by:
- **Version directories**: `radioss2026/`, `radioss2025/`, etc.
- **Category subdirectories**: `MAT/`, `PROP/`, `LOADS/`, `CARDS/`, etc.
- **Main hierarchy file**: `data_hierarchy.cfg` contains overall keyword structure

### 6. **Processing Workflow**

1. **Initialization**: HM reader loads and parses all CFG files
2. **Keyword Registration**: Each keyword definition is registered in internal database
3. **Validation**: Input files are validated against CFG definitions
4. **Data Extraction**: Parameter values are extracted according to CFG format specifications
5. **Unit Conversion**: Physical units are applied based on dimension specifications

### 7. **Integration with FreeCAD**

For the FreeCAD OpenRadioss Workbench, this means:

1. **CFG files provide authoritative syntax**: Use them as the source of truth for keyword definitions
2. **Parameter validation**: Validate user input against CFG specifications
3. **Format generation**: Generate proper `.k` file format based on CFG card definitions
4. **Version compatibility**: Support multiple OpenRadioss versions through different CFG directories

### 8. **Enhanced JSON Structure**

Based on this analysis, the updated JSON should include:

```json
{
  "name": "PART",
  "category": "Parts",
  "header": "*PART",
  "description": "Part definition",
  "parameters": [
    {
      "name": "PID",
      "type": "INT",
      "description": "Part ID",
      "dimension": "dimensionless",
      "required": true,
      "field_0": "pid"
    },
    {
      "name": "RHO",
      "type": "FLOAT", 
      "description": "Density",
      "dimension": "density",
      "required": true,
      "field_0": "rho"
    }
  ],
  "card_format": [
    {
      "type": "header",
      "format": "*PART/%s",
      "comment": "Part header with title"
    },
    {
      "type": "card",
      "format": "%10d",
      "comment": "$      PID",
      "line_number": 1
    }
  ],
  "ls_dyna_syntax": "*PART\n        PID",
  "openradioss_syntax": "*PART\n$      PID\n        PID"
}
```

This comprehensive understanding allows the FreeCAD workbench to provide accurate keyword definitions and proper `.k` file generation that matches OpenRadioss requirements.
