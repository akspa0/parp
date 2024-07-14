import sqlite3
import json
import logging
import os
import argparse
from collections import defaultdict
import matplotlib.pyplot as plt

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

def analyze_mspi_mslk_relationship(db_path, output_file):
    # Check if the database file exists
    if not os.path.exists(db_path):
        logging.error(f"Database file does not exist: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
    except sqlite3.OperationalError as e:
        logging.error(f"Unable to open database file: {db_path}. Error: {e}")
        return
    
    # Fetch MSLK data
    cursor.execute("SELECT record_index, field_name, field_value FROM chunk_fields WHERE chunk_id = 'KLSM' OR chunk_id = 'MSLK'")
    mslk_data = cursor.fetchall()
    
    # Fetch MSPI data
    cursor.execute("SELECT record_index, field_name, field_value FROM chunk_fields WHERE chunk_id = 'IPSM' OR chunk_id = 'MSPI'")
    mspi_data = cursor.fetchall()

    mslk_records = defaultdict(dict)
    for record in mslk_data:
        record_index, field_name, field_value = record
        mslk_records[record_index][field_name] = json.loads(field_value)

    mspi_records = defaultdict(dict)
    for record in mspi_data:
        record_index, field_name, field_value = record
        mspi_records[record_index][field_name] = json.loads(field_value)

    cross_reference_results = []

    for mslk_index, mslk_record in mslk_records.items():
        mspi_first_index = mslk_record.get("MSPI_first_index")
        mspi_index_count = mslk_record.get("MSPI_index_count")

        if mspi_first_index is not None and mspi_index_count is not None:
            for i in range(mspi_first_index, mspi_first_index + mspi_index_count):
                if i in mspi_records:
                    cross_reference_results.append({
                        "mslk_index": mslk_index,
                        "mslk_record": mslk_record,
                        "mspi_index": i,
                        "mspi_record": mspi_records[i]
                    })

    # Pattern analysis
    pattern_analysis = {
        "total_cross_references": len(cross_reference_results),
        "mslk_field_patterns": analyze_field_patterns(mslk_records),
        "mspi_field_patterns": analyze_field_patterns(mspi_records)
    }

    # Visualization
    visualize_data(pattern_analysis["mslk_field_patterns"], 'mslk')
    visualize_data(pattern_analysis["mspi_field_patterns"], 'mspi')

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "cross_references": cross_reference_results,
            "pattern_analysis": pattern_analysis
        }, f, indent=4)

    logging.info(f"Cross-reference results and pattern analysis written to {output_file}")

def analyze_field_patterns(records):
    field_patterns = defaultdict(lambda: defaultdict(int))
    for record_index, fields in records.items():
        for field_name, field_value in fields.items():
            field_patterns[field_name][str(field_value)] += 1
    return field_patterns

def visualize_data(field_patterns, chunk_type):
    for field, values in field_patterns.items():
        plt.figure(figsize=(10, 6))
        plt.bar(values.keys(), values.values(), color='blue')
        plt.xlabel('Values')
        plt.ylabel('Frequency')
        plt.title(f'Field {field} Distribution in {chunk_type.upper()} Chunks')
        plt.xticks(rotation=90)
        plt.tight_layout()
        plt.savefig(f'{chunk_type}_{field}_distribution.png')
        plt.close()

def main():
    parser = argparse.ArgumentParser(description="Analyze MSPI and MSLK chunk relationships and patterns.")
    parser.add_argument("db_path", type=str, help="Path to the input SQLite database file.")
    parser.add_argument("output_file", type=str, help="Path to the output JSON file.")
    args = parser.parse_args()

    analyze_mspi_mslk_relationship(args.db_path, args.output_file)

if __name__ == "__main__":
    main()
