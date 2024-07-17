import sqlite3
import json
import logging
import argparse
from collections import defaultdict
import os

# Setup logging
log_file = 'analysis.log'
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s', handlers=[
    logging.FileHandler(log_file),
    logging.StreamHandler()
])

def ensure_folder_exists(folder_path):
    if folder_path and not os.path.exists(folder_path):
        os.makedirs(folder_path)

def fetch_data_from_db(db_path, chunk_ids):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    data = defaultdict(lambda: defaultdict(list))
    for chunk_id in chunk_ids:
        query = f"SELECT file_name, record_index, field_name, field_value, field_type FROM chunk_fields WHERE chunk_id='{chunk_id}'"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        for row in rows:
            file_name, record_index, field_name, field_value, field_type = row
            value = json.loads(field_value)
            data[chunk_id][field_name].append((record_index, value))
    
    conn.close()
    return data

def analyze_field_values(data):
    analysis = {}

    for chunk_id, fields in data.items():
        analysis[chunk_id] = {}
        for field_name, values in fields.items():
            value_list = [val[1] for val in values]
            analysis[chunk_id][field_name] = {
                "min": min(value_list),
                "max": max(value_list),
                "unique_values": len(set(value_list)),
                "sample_values": value_list[:10]  # Take a sample of first 10 values for reference
            }
    
    return analysis

def cross_reference(data):
    correlation = defaultdict(list)
    rrpm_data = defaultdict(dict)
    klsm_ids = {}

    # Collect RRPM data
    for field in ["list_item_0", "list_item_1", "list_item_2", "list_item_3", "list_item_4", "list_item_5"]:
        rrpm_data[field] = [val[1] for val in data['RRPM'][field]]

    # Collect KLSM unique IDs
    for field in ["_0x04", "_0x0c"]:
        klsm_ids[field] = [val[1] for val in data['KLSM'][field]]

    # Correlate KLSM and RRPM data
    correlations = defaultdict(list)
    for klsm_field, klsm_values in klsm_ids.items():
        for index, klsm_value in enumerate(klsm_values):
            for rrpm_field, rrpm_values in rrpm_data.items():
                if index < len(rrpm_values):
                    correlations[klsm_field].append((klsm_value, rrpm_values[index]))

    correlation_summary = {field: {"values": vals[:10], "unique_values": len(set(vals))} for field, vals in correlations.items()}
    return correlation_summary

def visualize_correlations(correlations, output_dir):
    import matplotlib.pyplot as plt
    ensure_folder_exists(output_dir)
    
    for field, data in correlations.items():
        values = data["values"]
        unique_values = data["unique_values"]

        x = [val[0] for val in values]
        y = [val[1] for val in values]

        plt.figure(figsize=(10, 6))
        plt.scatter(x, y, alpha=0.5)
        plt.title(f'Correlation between {field} and RRPM')
        plt.xlabel(f'{field} Values')
        plt.ylabel('RRPM Values')
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, f'{field}_correlation.png'))
        plt.close()

def save_analysis_results(analysis_results, output_file):
    output_dir = os.path.dirname(output_file)
    ensure_folder_exists(output_dir)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=4)
    logging.info(f"Saved analysis results to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Analyze data from chunk_data.db and export analysis results to JSON files.")
    parser.add_argument("db_path", type=str, help="Path to the SQLite database file (chunk_data.db).")
    parser.add_argument("output_file", type=str, help="Path to the output JSON file.")
    parser.add_argument("output_dir", type=str, help="Path to the output directory for visualizations.")
    args = parser.parse_args()

    # Define the chunks and fields we're interested in
    chunk_ids = ['KLSM', 'RRPM']

    # Fetch data from the database
    data = fetch_data_from_db(args.db_path, chunk_ids)

    # Analyze field values
    analysis_results = analyze_field_values(data)

    # Cross-reference data
    correlation_results = cross_reference(data)
    analysis_results["correlations"] = correlation_results

    # Visualize correlations
    visualize_correlations(correlation_results, args.output_dir)

    # Save analysis results
    save_analysis_results(analysis_results, args.output_file)

if __name__ == "__main__":
    main()
