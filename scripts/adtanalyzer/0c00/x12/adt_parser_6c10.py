import os
import logging
from datetime import datetime
from pprint import pformat
from adt_chunk_decoders import parse_chunk, adt_chunk_decoders
from global_chunk_decoders import global_chunk_decoders
from mcnk_chunk_decoders import decode_mcnk_chunk

# Logging setup
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.basicConfig(
    filename=f"adt_parser_{timestamp}.log",
    filemode='w',
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Separate log for unknown chunks
unknown_chunks_log = f"unknown_chunks_{timestamp}.log"
unknown_logger = logging.getLogger("unknown_chunks")
unknown_handler = logging.FileHandler(unknown_chunks_log)
unknown_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
unknown_handler.setFormatter(unknown_formatter)
unknown_logger.addHandler(unknown_handler)
unknown_logger.setLevel(logging.INFO)

def parse_chunk(chunk_id, data, chunk_size=None):
    if chunk_id == "KNCM":
        # Decode KNCM header
        container = adt_chunk_decoders[chunk_id].parse(data)
        logger.info(f"Decoded KNCM chunk header: {container.header}")

        # Decode sub-chunks
        sub_chunks = {}
        pos = 0
        while pos < len(container.sub_chunks):
            subchunk_id = container.sub_chunks[pos:pos + 4].decode("utf-8", errors="replace")
            subchunk_size = int.from_bytes(container.sub_chunks[pos + 4:pos + 8], "little")
            subchunk_data = container.sub_chunks[pos + 8:pos + 8 + subchunk_size]
            pos += 8 + subchunk_size

            try:
                sub_chunks[subchunk_id] = parse_kncm_subchunk(subchunk_id, subchunk_data)
                logger.info(f"Decoded sub-chunk {subchunk_id}: {pformat(sub_chunks[subchunk_id])}")
            except ValueError:
                sub_chunks[subchunk_id] = {"raw_data": subchunk_data.hex()}
                logger.warning(f"No decoder for sub-chunk ID {subchunk_id}.")
                unknown_logger.info(f"Unknown sub-chunk {subchunk_id}: {subchunk_data.hex()}")
        return {"header": container.header, "sub_chunks": sub_chunks}

    elif chunk_id in global_chunk_decoders:
        decoder = global_chunk_decoders[chunk_id]
        logger.info(f"Decoding global chunk {chunk_id}")
        return decoder.parse(data)
    elif chunk_id in adt_chunk_decoders:
        decoder = adt_chunk_decoders[chunk_id]
        logger.info(f"Decoding ADT chunk {chunk_id}")
        return decoder.parse(data)
    else:
        raise ValueError(f"No decoder available for chunk ID {chunk_id}")

def parse_adt(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()

    pos = 0
    size = len(data)
    logger.info(f"Parsing ADT file: {file_path}")
    logger.debug(f"Available chunk decoders: {list(adt_chunk_decoders.keys()) + list(global_chunk_decoders.keys())}")

    while pos < size:
        if pos + 8 > size:
            logger.error(f"Reached end of file before reading chunk header at position {pos}.")
            break

        # Read chunk ID and size
        chunk_id = data[pos:pos + 4].decode('utf-8', errors='replace')  # Read as-is
        logger.debug(f"Parsing chunk ID: {chunk_id}")
        chunk_size = int.from_bytes(data[pos + 4:pos + 8], byteorder='little')

        if pos + 8 + chunk_size > size:
            logger.error(f"Chunk {chunk_id} at position {pos} exceeds file size. Corrupted file?")
            break

        chunk_data = data[pos + 8:pos + 8 + chunk_size]
        pos += 8 + chunk_size

        # Decode chunk
        try:
            logger.debug(f"Attempting to decode chunk ID: {chunk_id}")
            decoded_data = parse_chunk(chunk_id, chunk_data, chunk_size=chunk_size)
            logger.info(f"Decoded chunk {chunk_id}: {pformat(decoded_data)}")  # Pretty print decoded data
        except ValueError as e:
            logger.warning(f"No decoder found for chunk ID {chunk_id}. Logging raw data.")
            logger.info(f"Unknown chunk {chunk_id}: {chunk_data.hex()}")
            unknown_logger.info(f"Unknown chunk {chunk_id}: {chunk_data.hex()}")
        except Exception as e:
            logger.error(f"Error decoding chunk {chunk_id}: {e}")

    logger.info(f"Finished parsing {file_path}")

def main(directory):
    for file_name in os.listdir(directory):
        if file_name.lower().endswith(".adt"):
            file_path = os.path.join(directory, file_name)
            parse_adt(file_path)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python adt_parser.py <directory_of_adts>")
        sys.exit(1)

    directory = sys.argv[1]
    main(directory)
