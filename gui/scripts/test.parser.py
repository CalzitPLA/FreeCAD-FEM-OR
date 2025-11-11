from parser_cfg import CfgParser
import json



# Initialize the parser
parser = CfgParser('/home/nemo/Dokumente/Sandbox/Fem_upgraded/gui/CFG_Openradioss/Keyword971/SETS/node.cfg')

# Print the parsed data as JSON
#print(parser.to_json())

#parse sections
attributes, defaults, format_data, header = parser.attributes, parser.defaults, parser.format_data, parser.header

# Get the parsed data as a dictionary
data = parser.to_dict()

# Save to a JSON file
with open('output.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Data successfully written to output.json")

print(header)