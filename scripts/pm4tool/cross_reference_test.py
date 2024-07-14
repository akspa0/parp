import sqlite3
import json
import argparse

def main(db_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Step 1: Extract _0x0c values from the MSLK chunk
    query_mslk = """
    SELECT chunk_data 
    FROM parsed_chunks 
    WHERE chunk_id = 'MSLK'
    """
    cursor.execute(query_mslk)
    rows_mslk = cursor.fetchall()

    unique_ids = []
    for row in rows_mslk:
        chunk_data = row[0]
        chunk_data_json = json.loads(chunk_data)
        if isinstance(chunk_data_json, dict) and '_0x0c' in chunk_data_json:
            unique_id = chunk_data_json['_0x0c']
            unique_ids.append(unique_id)
        elif isinstance(chunk_data_json, list):
            for item in chunk_data_json:
                if isinstance(item, dict) and '_0x0c' in item:
                    unique_id = item['_0x0c']
                    unique_ids.append(unique_id)

    print("Unique _0x0c values:")
    print(unique_ids)

    # Step 2: Identify and Extract Unknown Values from Other Chunks
    query_other_chunks = """
    SELECT chunk_id, chunk_data 
    FROM parsed_chunks 
    WHERE chunk_id != 'MSLK'
    """
    cursor.execute(query_other_chunks)
    rows_other_chunks = cursor.fetchall()

    unknown_values = {}
    for row in rows_other_chunks:
        chunk_id, chunk_data = row
        chunk_data_json = json.loads(chunk_data)
        if isinstance(chunk_data_json, dict):
            for key, value in chunk_data_json.items():
                if isinstance(value, int) and value in unique_ids:
                    if chunk_id not in unknown_values:
                        unknown_values[chunk_id] = []
                    unknown_values[chunk_id].append((key, value))
        elif isinstance(chunk_data_json, list):
            for item in chunk_data_json:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, int) and value in unique_ids:
                            if chunk_id not in unknown_values:
                                unknown_values[chunk_id] = []
                            unknown_values[chunk_id].append((key, value))

    print("Unknown values:")
    print(unknown_values)

    # Step 3: Cross-Reference _0x0c Values with Unknown Values
    cross_references = {}
    for chunk_id, values in unknown_values.items():
        for key, value in values:
            if value in unique_ids:
                if value not in cross_references:
                    cross_references[value] = []
                cross_references[value].append((chunk_id, key))

    # Close the database connection
    conn.close()

    # Display the cross-references
    print("Cross-references:")
    print(cross_references)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cross-reference _0x0c values with unknown values in other chunks.")
    parser.add_argument("db_path", type=str, help="Path to the SQLite database file.")
    args = parser.parse_args()

    main(args.db_path)
