import argparse
import logging
from chunk_decoders.adt_parser_v12.adt_directory_parser import ADTDirectoryParser

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process WoW ADT files into JSON.")
    parser.add_argument("input_dir", help="Directory containing ADT files")
    parser.add_argument("--output-dir", default="output_files", help="Directory to save output files")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    try:
        # Single pass processing with full decoding
        parser = ADTDirectoryParser(
            args.input_dir,
            args.output_dir,
            "adt_processor.log",
            args.debug
        )
        results = parser.process_directory()
        parser.generate_statistics(results)
        
    except Exception as e:
        logging.error(f"Processing failed: {e}")
        raise
