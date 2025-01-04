import argparse
import logging
from adt_processor import ADTProcessor

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process WoW ADT files into JSON.")
    parser.add_argument("input_dir", help="Directory containing ADT files")
    parser.add_argument("--output-dir", default="output_files", help="Directory to save output files.")
    parser.add_argument("--known-files", type=str, help="Path to known files list (optional)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    processor = ADTProcessor(known_files=args.known_files, output_dir=args.output_dir)
    processor.process_directory(args.input_dir)
