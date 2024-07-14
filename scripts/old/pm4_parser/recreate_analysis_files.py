import sqlite3
import json
import logging
import argparse
import os

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

def ensure_folder_exists(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

def fetch_data(db_path, output_dir):
    ensure_folder_exists(output_dir)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Fetch all distinct file names
        cursor.execute("SELECT DISTINCT file_name FROM chunks")
        files = cursor.fetchall()
        
        for (file_name,) in files:
            # Fetch initial analysis data
            cursor.execute("SELECT chunk_id, chunk_data FROM chunks WHERE file_name = ?", (file_name,))
            chunks = cursor.fetchall()
            
            # Recreate initial analysis file
            initial_analysis = [{"id": chunk_id, "data": json.loads(chunk_data)} for chunk_id, chunk_data in chunks]
            initial_output = os.path.join(output_dir, file_name.replace('.pm4', '_initial_analysis.json').replace('.adt', '_initial_analysis.json'))
            ensure_folder_exists(os.path.dirname(initial_output))
            with open(initial_output, 'w', encoding='utf-8') as f:
                json.dump(initial_analysis, f, indent=4)
            logging.info(f"Recreated initial analysis for {file_name} at {initial_output}")
            
            # Fetch detailed analysis data
            cursor.execute("SELECT chunk_id, chunk_data FROM parsed_chunks WHERE file_name = ?", (file_name,))
            parsed_chunks = cursor.fetchall()
            
            detailed_analysis = {}
            for chunk_id, chunk_data in parsed_chunks:
                if chunk_id not in detailed_analysis:
                    detailed_analysis[chunk_id] = []
                detailed_analysis[chunk_id].append(json.loads(chunk_data))
            
            detailed_output = initial_output.replace('_initial_analysis', '_detailed_analysis')
            with open(detailed_output, 'w', encoding='utf-8') as f:
                json.dump(detailed_analysis, f, indent=4)
            logging.info(f"Recreated detailed analysis for {file_name} at {detailed_output}")
        
    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Recreate analysis files from SQLite database.")
    parser.add_argument("db_path", type=str, help="Path to the SQLite database file.")
    parser.add_argument("output_dir", type=str, help="Path to the output directory.")
    args = parser.parse_args()

    fetch_data(args.db_path, args.output_dir)

if __name__ == "__main__":
    main()
