import json
import logging
from pathlib import Path
from decode_chunks import decoders

class ADTProcessor:
    def __init__(self, known_files=None, output_dir="output_files"):
        self.logger = logging.getLogger("ADTProcessor")
        handler = logging.FileHandler("adt_processor.log")
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

        self.known_files = known_files or set()
        self.initial_analysis_dir = Path(output_dir) / "initial_analysis"
        self.decoded_data_dir = Path(output_dir) / "decoded_data"
        self.initial_analysis_dir.mkdir(parents=True, exist_ok=True)
        self.decoded_data_dir.mkdir(parents=True, exist_ok=True)

    def reverse_magic(self, magic):
        """Reverse the byte order of a chunk identifier."""
        return magic[::-1]

    def process_chunk(self, magic, chunk_data):
        """Process a single chunk using the appropriate decoder."""
        try:
            original_magic = magic
            reversed_magic = self.reverse_magic(magic)
            self.logger.debug(f"Processing chunk: original={original_magic}, reversed={reversed_magic}")

            if not chunk_data:
                self.logger.info(f"Empty chunk {original_magic} (this is normal for some chunks)")
                return {
                    "status": "empty",
                    "message": "Empty chunk (normal)",
                    "raw_data": ""
                }

            # Try both original and reversed magic
            decoder_magic = reversed_magic if reversed_magic in decoders else original_magic

            if decoder_magic in decoders:
                try:
                    self.logger.debug(f"Using decoder for chunk: {decoder_magic} (size: {len(chunk_data)})")
                    decoded_data = decoders[decoder_magic](chunk_data)
                    
                    if isinstance(decoded_data, tuple):
                        decoded_data = decoded_data[0]  # Some decoders return (data, bytes_processed)
                    
                    # Check for errors in decoded data
                    if isinstance(decoded_data, dict) and 'error' in decoded_data:
                        self.logger.error(f"Error in {decoder_magic} decoder: {decoded_data['error']}")
                        return decoded_data

                    return self._ensure_json_serializable(decoded_data)
                except Exception as e:
                    self.logger.error(f"Decoder error for {decoder_magic}: {e}")
                    return {
                        'error': str(e),
                        'raw_data': chunk_data.hex()
                    }
            else:
                self.logger.warning(f"No decoder found for chunk: {original_magic} or {reversed_magic}")
                return {
                    "status": "unhandled",
                    "message": "No specific decoder available",
                    "raw_data": chunk_data.hex()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to process chunk {magic}: {e}")
            return {
                'error': str(e),
                'raw_data': chunk_data.hex() if chunk_data else ""
            }

    def _ensure_json_serializable(self, data):
        """Ensure all data is JSON serializable"""
        if isinstance(data, bytes):
            return data.hex()
        elif isinstance(data, dict):
            return {
                k: self._ensure_json_serializable(v) 
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._ensure_json_serializable(item) for item in data]
        elif isinstance(data, (int, float, str, bool, type(None))):
            return data
        elif isinstance(data, tuple):  # Added tuple handling
            return list(self._ensure_json_serializable(item) for item in data)
        else:
            return str(data)  # Convert any other types to string

    def process_file_initial(self, filepath):
        """First pass: Parse raw data and save to initial_analysis."""
        try:
            self.logger.info(f"Processing {filepath.name} (Initial Pass)")
            with open(filepath, "rb") as f:
                data = f.read()

            chunks = []
            position = 0
            while position < len(data):
                magic = data[position:position+4].decode("ascii", errors="ignore")
                size = int.from_bytes(data[position+4:position+8], "little")
                chunk_data = data[position+8:position+8+size]
                position += 8 + size

                chunks.append({
                    "magic": magic,
                    "size": size,
                    "data": {"raw_data": chunk_data.hex()}
                })

            result = {"filename": filepath.name, "chunks": chunks}
            output_path = self.initial_analysis_dir / f"{filepath.stem}.json"
            with open(output_path, "w") as f:
                json.dump(result, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error processing file {filepath}: {e}")

    def process_file_detailed(self, initial_json_path):
        """Second pass: Decode raw_data into detailed data."""
        try:
            with open(initial_json_path, "r") as f:
                initial_json = json.load(f)

            self.logger.info(f"Processing {initial_json['filename']} (Detailed Pass)")
            
            for i, chunk in enumerate(initial_json.get("chunks", [])):
                try:
                    if "raw_data" in chunk["data"]:
                        raw_data = bytes.fromhex(chunk["data"]["raw_data"])
                        magic = chunk["magic"]
                        
                        self.logger.debug(f"Processing chunk {i+1}/{len(initial_json['chunks'])}: {magic}")
                        
                        decoded = self.process_chunk(magic, raw_data)
                        if decoded:
                            chunk["data"]["decoded"] = decoded
                        
                except Exception as e:
                    self.logger.error(f"Error processing chunk {i} in {initial_json['filename']}: {e}")
                    continue

            output_path = self.decoded_data_dir / f"{Path(initial_json['filename']).stem}.json"
            with open(output_path, "w") as f:
                json.dump(initial_json, f, indent=4)

        except Exception as e:
            self.logger.error(f"Error decoding file {initial_json_path}: {e}")

    def process_directory(self, directory_path):
        """Process all ADT files in the specified directory."""
        try:
            directory = Path(directory_path)
            if not directory.exists():
                self.logger.error(f"Directory does not exist: {directory_path}")
                return

            self.logger.info(f"Starting processing of directory: {directory_path}")
            
            # First Pass: Initial analysis
            adt_files = list(directory.glob("*.adt"))
            self.logger.info(f"Found {len(adt_files)} ADT files")
            
            for filepath in adt_files:
                try:
                    self.logger.info(f"Processing file (Initial Pass): {filepath.name}")
                    self.process_file_initial(filepath)
                except Exception as e:
                    self.logger.error(f"Error processing {filepath.name} (Initial Pass): {e}")
                    continue

            # Second Pass: Detailed decoding
            initial_json_files = list(self.initial_analysis_dir.glob("*.json"))
            self.logger.info(f"Processing {len(initial_json_files)} JSON files for detailed analysis")
            
            for filepath in initial_json_files:
                try:
                    self.logger.info(f"Processing file (Detailed Pass): {filepath.name}")
                    self.process_file_detailed(filepath)
                except Exception as e:
                    self.logger.error(f"Error processing {filepath.name} (Detailed Pass): {e}")
                    continue

            self.logger.info("Directory processing completed")
            
        except Exception as e:
            self.logger.error(f"Error processing directory {directory_path}: {e}")
            raise
