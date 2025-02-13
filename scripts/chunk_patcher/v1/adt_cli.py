# adt_cli.py
import argparse
import sys
from adt_main import ADTProcessor
from adt_process_dir import generate_coordinate_mapping

def main():
    parser = argparse.ArgumentParser(description='Process ADT files')
    parser.add_argument('source_dir', help='Source directory containing ADT files')
    parser.add_argument('target_dir', help='Target coordinates reference directory')
    parser.add_argument('--output', help='Output directory for processed files')
    parser.add_argument('--preserve-backups', action='store_true', 
                       help='Keep backup files after successful processing')
    
    args = parser.parse_args()
    
    try:
        processor = ADTProcessor(args.source_dir, args.output)
        coordinates = generate_coordinate_mapping(args.source_dir, args.target_dir)
        
        success = True
        for filename, new_coords in coordinates.items():
            filepath = os.path.join(args.source_dir, filename)
            if not processor.process_file(filepath, new_coords):
                success = False
                
        return 0 if success else 1
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())