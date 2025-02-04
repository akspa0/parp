"""Compare converted ADT files with retail reference."""
import argparse
from pathlib import Path
import struct
from typing import Dict, List, Set, Tuple

from chunks.base import Chunk


def read_chunks(path: Path) -> Dict[str, List[Chunk]]:
    """Read all chunks from file, grouped by type."""
    chunks: Dict[str, List[Chunk]] = {}
    
    with open(path, 'rb') as f:
        while True:
            chunk = Chunk.read(f)
            if not chunk:
                break
            if chunk.letters not in chunks:
                chunks[chunk.letters] = []
            chunks[chunk.letters].append(chunk)
            
    return chunks


def compare_adts(converted_path: Path, retail_path: Path) -> Tuple[bool, str]:
    """Compare converted ADT with retail reference.
    
    Returns:
    - bool: True if files match
    - str: Description of differences
    """
    converted = read_chunks(converted_path)
    retail = read_chunks(retail_path)
    
    # Compare chunk types
    converted_types = set(converted.keys())
    retail_types = set(retail.keys())
    
    missing = retail_types - converted_types
    extra = converted_types - retail_types
    
    if missing:
        return False, f"Missing chunks: {', '.join(missing)}"
    if extra:
        # Print details about extra MCRF chunks
        if 'FRCM' in extra:
            print("\nExtra MCRF chunks found:")
            for i, chunk in enumerate(converted['FRCM']):
                print(f"MCRF[{i}] size: {chunk.size}")
                print(f"MCRF[{i}] data: {chunk.data.hex()}")
        return False, f"Extra chunks: {', '.join(extra)}"
        
    # Compare chunk counts
    for chunk_type in retail_types:
        if len(converted[chunk_type]) != len(retail[chunk_type]):
            return False, f"Wrong number of {chunk_type} chunks: {len(converted[chunk_type])} vs {len(retail[chunk_type])}"
            
    # Compare chunk sizes and data
    for chunk_type in retail_types:
        for i, (conv, ret) in enumerate(zip(converted[chunk_type], retail[chunk_type])):
            if conv.size != ret.size:
                # Add debug output for MCNK chunks
                if chunk_type == 'KNCM':
                    print(f"\nConverted MCNK[{i}] details:")
                    print(f"Size: {conv.size}")
                    print(f"Header: {conv.data[:128].hex()}")
                    print(f"\nRetail MCNK[{i}] details:")
                    print(f"Size: {ret.size}")
                    print(f"Header: {ret.data[:128].hex()}")
                return False, f"{chunk_type}[{i}] wrong size: {conv.size} vs {ret.size}"
            if conv.data != ret.data:
                # Add debug output for data mismatches
                if chunk_type == 'RDHM':
                    print(f"\nMHDR data mismatch:")
                    print(f"Converted MHDR data: {conv.data.hex()}")
                    print(f"Retail MHDR data: {ret.data.hex()}")
                    # Parse and compare offsets
                    conv_offsets = struct.unpack('<16I', conv.data)
                    ret_offsets = struct.unpack('<16I', ret.data)
                    print("\nMHDR offsets:")
                    fields = ['flags', 'mcin', 'mtex', 'mmdx', 'mmid', 'mwmo', 'mwid', 'mddf', 
                            'modf', 'mfbo', 'mh2o', 'mtxf', 'unused1', 'unused2', 'unused3', 'unused4']
                    for field, conv_val, ret_val in zip(fields, conv_offsets, ret_offsets):
                        if conv_val != ret_val:
                            print(f"{field}: {conv_val} vs {ret_val}")
                elif chunk_type == 'NICM':
                    print(f"\nMCIN data mismatch:")
                    # Parse and compare entries
                    for j in range(256):
                        conv_entry = conv.data[j*16:(j+1)*16]
                        ret_entry = ret.data[j*16:(j+1)*16]
                        if conv_entry != ret_entry:
                            conv_offset, conv_size, conv_flags, conv_layer = struct.unpack('<4I', conv_entry)
                            ret_offset, ret_size, ret_flags, ret_layer = struct.unpack('<4I', ret_entry)
                            print(f"Entry {j}:")
                            print(f"  Offset: {conv_offset} vs {ret_offset}")
                            print(f"  Size: {conv_size} vs {ret_size}")
                            print(f"  Flags: {conv_flags} vs {ret_flags}")
                            print(f"  Layer: {conv_layer} vs {ret_layer}")
                elif chunk_type == 'KNCM':
                    print(f"\nMCNK[{i}] data mismatch:")
                    # Find first differing byte
                    for j, (c, r) in enumerate(zip(conv.data, ret.data)):
                        if c != r:
                            print(f"First difference at offset {j}: {c:02x} vs {r:02x}")
                            break
                return False, f"{chunk_type}[{i}] data mismatch"
                
    return True, "Files match"


def main():
    parser = argparse.ArgumentParser(description='Compare converted ADT with retail reference')
    parser.add_argument('converted', type=Path, help='Converted ADT file')
    parser.add_argument('retail', type=Path, help='Retail reference ADT file')
    args = parser.parse_args()
    
    match, details = compare_adts(args.converted, args.retail)
    print(f"Comparing {args.converted.name}...")
    print(details)
    return 0 if match else 1


if __name__ == '__main__':
    exit(main())