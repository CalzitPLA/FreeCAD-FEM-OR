
# OpenRadioss CFG Processing Workflow

## 1. Environment Setup
export OPENRADIOSS_PATH=/path/to/openradioss
export RAD_CFG_PATH=$OPENRADIOSS_PATH/hm_cfg_files
export LD_LIBRARY_PATH=$OPENRADIOSS_PATH/extlib/hm_reader/linux64/:$LD_LIBRARY_PATH

## 2. Starter Input Processing
1. Starter reads .k file (Radioss input)
2. Calls HM reader library functions
3. HM reader parses .cfg files from RAD_CFG_PATH
4. Builds internal database of keyword definitions
5. Starter queries database to validate and process keywords

## 3. Key HM Reader Functions
- HM_OPTION_COUNT() - Count occurrences of keywords
- HM_OPTION_START() - Begin reading keyword section  
- HM_OPTION_READ_KEY() - Read keyword headers and IDs
- HM_GET_INTV() - Get integer values
- HM_GET_FLOATV() - Get float values
- HM_GET_STRING() - Get string values

## 4. CFG File Structure
ATTRIBUTES: Parameter definitions with types and descriptions
GUI: Display and validation rules  
FORMAT: Exact syntax and card layout
SKEYWORDS_IDENTIFIER: Internal mapping

