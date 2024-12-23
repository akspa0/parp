### Main Script: analyze_wdt.py
import os
import struct
import logging
from datetime import datetime
from chunk_definitions import parse_mver, parse_mphd, parse_main, parse_mdnm, parse_monm, parse_mcnk, parse_mhdr, parse_mcin, parse_mtex, parse_mddf, parse_modf, text_based_visualization

def parse_wdt(filepath):
    """
    Parses a WDT file and extracts its chunk data for logging purposes.
    """
    with open(filepath, 'rb') as f:
        data = f.read()

    pos = 0
    size = len(data)
    chunks = []

    logging.info(f"Starting WDT file analysis: {filepath}")

    while pos + 8 <= size:
        # Read chunk name and reverse it for Alpha files
        chunk_name = data[pos:pos+4][::-1].decode('ascii', 'ignore')
        chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
        if pos + 8 + chunk_size > size:
            logging.warning(f"Chunk {chunk_name} extends beyond file size. Skipping.")
            break

        chunk_data = data[pos+8:pos+8+chunk_size]
        chunks.append((chunk_name, chunk_size, chunk_data))
        logging.info(f"Found chunk: {chunk_name} with size {chunk_size}")
        pos += 8 + chunk_size

    logging.info("Finished WDT file analysis.")
    return chunks

def analyze_chunk(chunk_name, chunk_data):
    """
    Analyzes a chunk based on its name and logs details.
    """
    try:
        if chunk_name == 'MVER':
            parse_mver(chunk_data)
        elif chunk_name == 'MPHD':
            parse_mphd(chunk_data)
        elif chunk_name == 'MAIN':
            parse_main(chunk_data)
        elif chunk_name == 'MDNM':
            parse_mdnm(chunk_data)
        elif chunk_name == 'MONM':
            parse_monm(chunk_data)
        elif chunk_name == 'MHDR':
            parse_mhdr(chunk_data)
        elif chunk_name == 'MCIN':
            parse_mcin(chunk_data)
        elif chunk_name == 'MTEX':
            parse_mtex(chunk_data)
        elif chunk_name == 'MDDF':
            parse_mddf(chunk_data)
        elif chunk_name == 'MODF':
            parse_modf(chunk_data)
        elif chunk_name == 'MCNK':
            parse_mcnk(chunk_data)
        else:
            logging.warning(f"Unrecognized chunk: {chunk_name}")
    except Exception as e:
        logging.error(f"Error analyzing chunk {chunk_name}: {e}")

def write_visualization_to_file(grid):
    """
    Writes the text-based visualization of the grid to a separate timestamped log file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    vis_filename = f"adt_visualization_{timestamp}.log"
    visualization = "\n".join(
        "".join("#" if cell == 1 else "." for cell in row)
        for row in grid
    )
    with open(vis_filename, 'w') as vis_file:
        vis_file.write("Text-based visualization of the ADT grid:\n")
        vis_file.write(visualization + "\n")
    logging.info(f"Text-based visualization saved to {vis_filename}")

def main(filepath):
    """
    Main function to analyze a WDT file and log its contents.
    """
    log_filename = f"wdt_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        filename=log_filename,
        filemode='w',
        format='%(asctime)s [%(levelname)s] %(message)s',
        level=logging.INFO
    )

    logging.info("Starting WDT analysis script.")

    chunks = parse_wdt(filepath)

    # Initialize grid for visualization
    grid = [[0] * 64 for _ in range(64)]

    for chunk_name, chunk_size, chunk_data in chunks:
        if chunk_name == 'MAIN':
            parse_main(chunk_data)
            # Populate grid for visualization
            entry_size = 16  # Total size of SMAreaInfo entry
            entry_count = len(chunk_data) // entry_size
            for i in range(entry_count):
                entry_data = chunk_data[i * entry_size:(i + 1) * entry_size]
                offset, size, flags = struct.unpack('<III', entry_data[:12])
                x = i % 64
                y = i // 64
                grid[y][x] = 1 if offset > 0 else 0

        analyze_chunk(chunk_name, chunk_data)

    # Write visualization to separate log file
    write_visualization_to_file(grid)

    logging.info(f"WDT analysis completed. Log file: {log_filename}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python analyze_wdt.py <path_to_wdt_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.isfile(filepath):
        print(f"Error: File {filepath} not found.")
        sys.exit(1)

    main(filepath)
