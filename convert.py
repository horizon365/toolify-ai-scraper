from utils.data_utils import json_to_csv

# Convert existing JSON to CSV
json_file_path = 'toolify_ai_tools.json'
csv_file_path = 'toolify_ai_tools.csv'
json_to_csv(json_file_path, csv_file_path)

print(f"Successfully converted {json_file_path} to {csv_file_path}") 