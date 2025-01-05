#!/usr/bin/env python3
import os
import sys
import json
import logging
from datetime import datetime

def setup_logging(log_dir='logs'):
    """
    Set up logging to both file and console
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Generate a unique log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"json_analyzer_{timestamp}.log")
    
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

def print_json_structure(data, logger, indent=0):
    """
    Recursively log the structure of a JSON object for debugging
    """
    indent_str = "  " * indent
    if isinstance(data, dict):
        logger.info(f"{indent_str}Dictionary with keys:")
        for key, value in data.items():
            logger.info(f"{indent_str}  {key}:")
            print_json_structure(value, logger, indent + 1)
    elif isinstance(data, list):
        logger.info(f"{indent_str}List with {len(data)} items:")
        for i, item in enumerate(data[:5]):  # Limit to first 5 items
            logger.info(f"{indent_str}  Item {i}:")
            print_json_structure(item, logger, indent + 1)
        if len(data) > 5:
            logger.info(f"{indent_str}  ... and {len(data) - 5} more items")
    else:
        logger.info(f"{indent_str}Value: {data}")

def extract_heights_and_normals(json_path, logger):
    """
    Carefully extract heights and normals from the JSON file
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    logger.info(f"\n--- Analyzing {json_path} ---")
    
    # Log overall structure
    logger.info("JSON File Structure:")
    print_json_structure(data, logger)
    
    # Attempt to extract heights and normals
    heights = []
    normals = []
    
    # If data is a list (entire parsed file), iterate through it
    if isinstance(data, list):
        for item in data:
            mcnk_chunks = item.get('chunks', {}).get('MCNK', [])
            for mcnk in mcnk_chunks:
                sub_chunks = mcnk.get('sub_chunks', {})
                
                # Extract heights from MCVT
                mcvt = sub_chunks.get('MCVT', {})
                if mcvt and 'heights' in mcvt:
                    heights.extend(mcvt['heights'])
                    logger.info(f"Found {len(mcvt['heights'])} heights in MCVT")
                
                # Extract normals from MCNR
                mcnr = sub_chunks.get('MCNR', {})
                if mcnr and 'normals' in mcnr:
                    normals.extend(mcnr['normals'])
                    logger.info(f"Found {len(mcnr['normals'])} normals in MCNR")
    
    # If data is a dictionary
    elif isinstance(data, dict):
        mcnk_chunks = data.get('chunks', {}).get('MCNK', [])
        for mcnk in mcnk_chunks:
            sub_chunks = mcnk.get('sub_chunks', {})
            
            # Extract heights from MCVT
            mcvt = sub_chunks.get('MCVT', {})
            if mcvt and 'heights' in mcvt:
                heights.extend(mcvt['heights'])
                logger.info(f"Found {len(mcvt['heights'])} heights in MCVT")
            
            # Extract normals from MCNR
            mcnr = sub_chunks.get('MCNR', {})
            if mcnr and 'normals' in mcnr:
                normals.extend(mcnr['normals'])
                logger.info(f"Found {len(mcnr['normals'])} normals in MCNR")
    
    logger.info(f"Total heights extracted: {len(heights)}")
    logger.info(f"Total normals extracted: {len(normals)}")
    
    return heights, normals

def main(input_dir):
    """
    Analyze JSON files in the input directory
    """
    # Set up logging
    log_filename = setup_logging()
    logger = logging.getLogger()

    logger.info(f"Analyzing JSON files in directory: {input_dir}")

    for filename in os.listdir(input_dir):
        if filename.endswith('.json'):
            json_path = os.path.join(input_dir, filename)
            try:
                heights, normals = extract_heights_and_normals(json_path, logger)
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}", exc_info=True)

    logger.info("JSON analysis complete.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python json_analyzer.py <input_json_directory>")
        sys.exit(1)

    main(sys.argv[1])
