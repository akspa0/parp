import os
import json
import logging
import argparse
from datetime import datetime
from wmo_chunk_decoders import extract_wmo_root_data, extract_wmo_group_data

def ensure_folder_exists(folder_path):
    if folder_path and not os.path.exists(folder_path):
        os.makedirs(folder_path)

def setup_logging():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"wmo_analysis_{timestamp}.log"
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s',
                        handlers=[logging.FileHandler(log_filename), logging.StreamHandler()])

def read_chunks(file_path):
    with open(file_path, "rb") as f:
        file_size = os.path.getsize(file_path)
        data = f.read()

    offset = 0
    chunks = []
    while offset < file_size:
        chunk_id = data[offset:offset+4]
        try:
            chunk_id_str = chunk_id.decode('utf-8')
        except UnicodeDecodeError:
            logging.error(f"Failed to decode chunk ID at offset {offset}. Skipping this chunk.")
            offset += 4
            continue
        
        chunk_size = int.from_bytes(data[offset+4:offset+8], byteorder='little')
        chunk_data = data[offset+8:offset+8+chunk_size]
        chunks.append({
            'id': chunk_id_str,
            'size': chunk_size,
            'data': chunk_data
        })
        logging.info(f"Read chunk: {chunk_id_str} (Size: {chunk_size})")
        offset += 8 + chunk_size

    return chunks

def save_extracted_data(data, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def main():
    parser = argparse.ArgumentParser(description="Extract data from WMO files.")
    parser.add_argument("input_dir", type=str, help="Path to the input directory containing WMO files.")
    parser.add_argument("output_dir", type=str, help="Path to the output directory to save extracted data.")
    args = parser.parse_args()

    setup_logging()
    ensure_folder_exists(args.output_dir)

    wmo_files = [os.path.join(args.input_dir, f) for f in os.listdir(args.input_dir) if f.endswith('.wmo')]

    for wmo_file in wmo_files:
        chunks = read_chunks(wmo_file)
        if '_000.wmo' in wmo_file or '_001.wmo' in wmo_file:
            data = extract_wmo_group_data(chunks)
        else:
            data = extract_wmo_root_data(chunks)
        
        output_file = os.path.join(args.output_dir, os.path.splitext(os.path.basename(wmo_file))[0] + "_data.json")
        save_extracted_data(data, output_file)
        logging.info(f"Saved extracted data to {output_file}")

if __name__ == "__main__":
    main()
