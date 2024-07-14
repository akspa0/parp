import sqlite3
import json
import argparse

def main(db_path, output_file):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Step 1: Extract _0x0c values from the KLSM chunk
    query_klsm = """
    SELECT chunk_data 
    FROM parsed_chunks 
    WHERE chunk_id = 'KLSM'
    """
    cursor.execute(query_klsm)
    rows_klsm = cursor.fetchall()

    # Print the number of rows fetched
    print(f"Number of KLSM chunks fetched: {len(rows_klsm)}")

    # Open the output file
    with open(output_file, 'w') as file:
        # Write each chunk's data to the file
        for i, row in enumerate(rows_klsm):
            chunk_data = row[0]
            chunk_data_json = json.loads(chunk_data)
            file.write(f"KLSM Chunk {i+1}:\n")
            file.write(json.dumps(chunk_data_json, indent=4))
            file.write('\n\n')

    print(f"Data written to {output_file}")

    # Close the database connection
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract and save KLSM chunks to a text file.")
    parser.add_argument("db_path", type=str, help="Path to the SQLite database file.")
    parser.add_argument("output_file", type=str, help="Path to the output text file.")
    args = parser.parse_args()

    main(args.db_path, args.output_file)
