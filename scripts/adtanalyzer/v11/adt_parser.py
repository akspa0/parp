#!/usr/bin/env python3
"""
ADT File Parser for World of Warcraft Map Tiles

Parses ADT files and generates comprehensive JSON output.

Usage:
  python adt_parser.py <adt_directory>
"""

import os
import re
import sys
import struct
import logging
import json
from datetime import datetime

# Import decoders from decode_chunks
from decode_chunks import decoders

def setup_logging():
    """Configure logging for the script."""
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Generate a unique log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"adt_parser_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_filename, mode='w'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info(f"Logging initialized. Log file: {log_filename}")
    return log_filename

def reverse_chunk_id(chunk_id):
    """Reverse the chunk ID"""
    return chunk_id[::-1]

def extract_adt_coordinates(filename):
    """Extract X and Y coordinates from ADT filename."""
    match = re.match(r'(\d+)_(\d+)\.adt$', filename, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None

def parse_adt_file(filepath):
    """
    Parse a single ADT file and extract chunk information.
    
    Args:
        filepath (str): Path to the ADT file to parse
    
    Returns:
        dict: Parsed ADT file information
    """
    base_name = os.path.basename(filepath)
    folder_name = os.path.basename(os.path.dirname(filepath)).lower()
    x_coord, y_coord = extract_adt_coordinates(base_name)

    # Initialize ADT data structure
    adt_data = {
        "name": base_name,
        "folder": folder_name,
        "x_coord": x_coord,
        "y_coord": y_coord,
        "chunks": {}
    }

    try:
        with open(filepath, "rb") as f:
            data = f.read()

        offset = 0
        while offset < len(data):
            try:
                # Read chunk signature and size
                chunk_id = data[offset:offset + 4].decode('utf-8')
                chunk_size = struct.unpack('<I', data[offset + 4:offset + 8])[0]
                chunk_data = data[offset + 8:offset + 8 + chunk_size]
                
                # Reverse chunk ID for decoding
                chunk_id_reversed = reverse_chunk_id(chunk_id)
                
                # Try to decode the chunk
                if chunk_id_reversed in decoders:
                    try:
                        decoded_data, _ = decoders[chunk_id_reversed](chunk_data)
                        adt_data['chunks'].setdefault(chunk_id_reversed, []).append(decoded_data)
                        logging.info(f"Decoded chunk {chunk_id_reversed} successfully.")
                    except Exception as e:
                        logging.error(f"Error decoding chunk {chunk_id_reversed}: {e}")
                else:
                    logging.debug(f"No decoder found for chunk {chunk_id_reversed}")

            except Exception as e:
                logging.error(f"Error processing chunk at offset {offset}: {e}")
                break

            # Move to next chunk
            offset += 8 + chunk_size

        return adt_data

    except Exception as e:
        logging.error(f"Error parsing {filepath}: {e}")
        return None

def main(directory):
    """
    Main processing function to parse all ADT files in a directory.
    
    Args:
        directory (str): Path to directory containing ADT files
    """
    log_filename = setup_logging()
    logging.info(f"Starting ADT parsing in directory: {directory}")

    # Create output directory
    output_dir = "parsed_data"
    os.makedirs(output_dir, exist_ok=True)

    parsed_adts = []
    for filename in os.listdir(directory):
        if not filename.lower().endswith('.adt'):
            continue

        filepath = os.path.join(directory, filename)
        logging.info(f"Processing {filepath}")
        
        adt_data = parse_adt_file(filepath)
        if adt_data:
            parsed_adts.append(adt_data)
            
            # Save individual ADT parse results
            output_path = os.path.join(output_dir, f"{filename}_parsed.json")
            with open(output_path, 'w') as f:
                json.dump(adt_data, f, indent=2)

    # Write comprehensive output
    comprehensive_output_path = os.path.join(output_dir, 'all_adts_parsed.json')
    with open(comprehensive_output_path, 'w') as f:
        json.dump(parsed_adts, f, indent=2)

    logging.info(f"Parsed {len(parsed_adts)} ADT files.")
    logging.info(f"Full log available at {log_filename}")
    logging.info(f"Individual ADT outputs written to {output_dir}")
    logging.info(f"Comprehensive output written to {comprehensive_output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python adt_parser.py <directory_of_adts>")
        sys.exit(1)
    
    main(sys.argv[1])
