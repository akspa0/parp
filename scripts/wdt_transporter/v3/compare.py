"""Compare WDT and ADT files to identify differences."""
import argparse
from pathlib import Path
import struct
from typing import Dict, List, Optional, Tuple

from chunks.base import Chunk


def read_chunks(path: Path) -> List[Tuple[str, int, bytes]]:
    """Read all chunks from a file.
    
    Returns a list of (letters, size, data) tuples.
    """
    chunks = []
    with open(path, 'rb') as f:
        while True:
            # Try to read chunk header
            header = f.read(8)
            if not header or len(header) < 8:
                break
            
            # Parse header
            letters = header[0:4].decode('ascii')
            size = struct.unpack('<I', header[4:8])[0]
            
            # Read chunk data including header
            f.seek(f.tell() - 8)  # Go back to start of chunk
            full_data = f.read(size + 8)  # Read header + data
            if len(full_data) < size + 8:
                break
            
            chunks.append((letters, size, full_data))
    
    return chunks


def analyze_mcnk(data1: bytes, data2: bytes) -> None:
    """Analyze differences between MCNK chunks."""
    print("\nMCNK analysis:")
    print(f"Raw data1 length: {len(data1)}")
    print(f"Raw data2 length: {len(data2)}")
    print(f"First 16 bytes of data1: {data1[:16].hex()}")
    print(f"First 16 bytes of data2: {data2[:16].hex()}")
    
    try:
        # Skip chunk headers (8 bytes)
        data1 = data1[8:]
        data2 = data2[8:]
        print(f"After header skip - data1 length: {len(data1)}")
        print(f"After header skip - data2 length: {len(data2)}")
        
        # Compare headers (128 bytes)
        if len(data1) >= 128 and len(data2) >= 128:
            print("Analyzing headers...")
        else:
            print("Data too short for header analysis")
    except Exception as e:
        print(f"Error in MCNK analysis: {e}")
        import traceback
        traceback.print_exc()
        header1 = data1[:128]
        header2 = data2[:128]
        
        # Compare each field
        fields = [
            ("flags", 0, 4),
            ("ix", 4, 8),
            ("iy", 8, 12),
            ("n_layers", 12, 16),
            ("n_doodad_refs", 16, 20),
            ("mcvt_offset", 20, 24),
            ("mcnr_offset", 24, 28),
            ("mcly_offset", 28, 32),
            ("mcrf_offset", 32, 36),
            ("mcal_offset", 36, 40),
            ("mcal_size", 40, 44),
            ("mcsh_offset", 44, 48),
            ("mcsh_size", 48, 52),
            ("area_id", 52, 56),
            ("n_mapobj_refs", 56, 60),
            ("holes", 60, 64),
            ("pred_tex", 64, 68),
            ("n_effect_doodad", 68, 72),
            ("mcse_offset", 72, 76),
            ("n_snd_emitters", 76, 80),
            ("mclq_offset", 80, 84),
            ("mclq_size", 84, 88),
            ("pos_y", 88, 92),
            ("pos_x", 92, 96),
            ("pos_z", 96, 100),
            ("mccv_offset", 100, 104),
            ("mclv_offset", 104, 108),
            ("unused", 108, 112),
        ]
        
        print("\nHeader fields:")
        print(f"{'Field':16} {'Value 1':>12} {'Value 2':>12} {'Match':>6}")
        print("-" * 50)
        
        for name, start, end in fields:
            val1 = struct.unpack('<I', header1[start:end])[0]
            val2 = struct.unpack('<I', header2[start:end])[0]
            match = "Yes" if val1 == val2 else "No"
            print(f"{name:16} {val1:12} {val2:12} {match:>6}")
    
    # Compare subchunk sizes
    print("\nSubchunk sizes:")
    subchunks = ["MCVT", "MCNR", "MCLY", "MCRF", "MCSH", "MCAL", "MCLQ"]
    pos1 = pos2 = 128  # Start after header
    
    for name in subchunks:
        # Try to read subchunk from first file
        if pos1 + 8 <= len(data1):
            letters1 = data1[pos1:pos1+4].decode('ascii')
            size1 = struct.unpack('<I', data1[pos1+4:pos1+8])[0] if letters1 == name else 0
        else:
            letters1 = ""
            size1 = 0
            
        # Try to read subchunk from second file
        if pos2 + 8 <= len(data2):
            letters2 = data2[pos2:pos2+4].decode('ascii')
            size2 = struct.unpack('<I', data2[pos2+4:pos2+8])[0] if letters2 == name else 0
        else:
            letters2 = ""
            size2 = 0
            
        print(f"{name:6} {size1:10} {size2:10} {'Yes' if size1 == size2 else 'No':>6}")
        
        # Update positions
        if letters1 == name:
            pos1 += 8 + size1
        if letters2 == name:
            pos2 += 8 + size2


def analyze_mhdr(data1: bytes, data2: bytes) -> None:
    """Analyze differences between MHDR chunks."""
    print("\nMHDR analysis:")
    print(f"Raw data1 length: {len(data1)}")
    print(f"Raw data2 length: {len(data2)}")
    print(f"First 16 bytes of data1: {data1[:16].hex()}")
    print(f"First 16 bytes of data2: {data2[:16].hex()}")
    
    try:
        # Skip chunk headers (8 bytes)
        data1 = data1[8:]
        data2 = data2[8:]
        print(f"After header skip - data1 length: {len(data1)}")
        print(f"After header skip - data2 length: {len(data2)}")
        
        if len(data1) >= 64 and len(data2) >= 64:
            print("Analyzing offsets...")
        else:
            print("Data too short for offset analysis")
    except Exception as e:
        print(f"Error in MHDR analysis: {e}")
        import traceback
        traceback.print_exc()
        fields = [
            ("flags", 0, 4),
            ("mcin_offset", 4, 8),
            ("mtex_offset", 8, 12),
            ("mmdx_offset", 12, 16),
            ("mmid_offset", 16, 20),
            ("mwmo_offset", 20, 24),
            ("mwid_offset", 24, 28),
            ("mddf_offset", 28, 32),
            ("modf_offset", 32, 36),
            ("mfbo_offset", 36, 40),
            ("mh2o_offset", 40, 44),
            ("mtxf_offset", 44, 48),
        ]
        
        print("\nOffset fields:")
        print(f"{'Field':12} {'Value 1':>12} {'Value 2':>12} {'Match':>6}")
        print("-" * 46)
        
        for name, start, end in fields:
            val1 = struct.unpack('<I', data1[start:end])[0]
            val2 = struct.unpack('<I', data2[start:end])[0]
            match = "Yes" if val1 == val2 else "No"
            print(f"{name:12} {val1:12} {val2:12} {match:>6}")


def compare_files(path1: Path, path2: Path) -> None:
    """Compare two WDT/ADT files and print differences."""
    print(f"\nComparing files:")
    print(f"1: {path1}")
    print(f"2: {path2}")
    
    # Read chunks from both files
    chunks1 = read_chunks(path1)
    chunks2 = read_chunks(path2)
    
    # Convert to dictionaries for easier comparison
    chunks1_dict = {letters: (size, data) for letters, size, data in chunks1}
    chunks2_dict = {letters: (size, data) for letters, size, data in chunks2}
    
    # Find all unique chunk letters
    all_letters = sorted(set(chunks1_dict.keys()) | set(chunks2_dict.keys()))
    
    # Compare chunks
    print("\nChunk comparison:")
    print(f"{'Chunk':6} {'Size 1':>10} {'Size 2':>10} {'Match':>6}")
    print("-" * 35)
    
    for letters in all_letters:
        chunk1 = chunks1_dict.get(letters)
        chunk2 = chunks2_dict.get(letters)
        
        if chunk1 and chunk2:
            size1, data1 = chunk1
            size2, data2 = chunk2
            match = "Yes" if data1 == data2 else "No"
            print(f"{letters:6} {size1:10} {size2:10} {match:>6}")
            
            # Analyze specific chunks in detail
            raw_name = data1[:4].decode('ascii')
            print(f"\nChecking {letters}... (raw: {raw_name})")
            
            # MCNK chunk
            if raw_name == 'KNCM':
                print(f"Found MCNK chunk (match: {match})")
                if not match:
                    print(f"Analyzing MCNK chunk... (data1: {len(data1)} bytes, data2: {len(data2)} bytes)")
                    print(f"First 16 bytes of data1: {data1[:16].hex()}")
                    print(f"First 16 bytes of data2: {data2[:16].hex()}")
                    try:
                        analyze_mcnk(data1, data2)
                    except Exception as e:
                        print(f"Error analyzing MCNK: {e}")
                        import traceback
                        traceback.print_exc()
            
            # MHDR chunk
            elif raw_name == 'RDHM':
                print(f"Found MHDR chunk (match: {match})")
                if not match:
                    print(f"Analyzing MHDR chunk... (data1: {len(data1)} bytes, data2: {len(data2)} bytes)")
                    print(f"First 16 bytes of data1: {data1[:16].hex()}")
                    print(f"First 16 bytes of data2: {data2[:16].hex()}")
                    try:
                        analyze_mhdr(data1, data2)
                    except Exception as e:
                        print(f"Error analyzing MHDR: {e}")
                        import traceback
                        traceback.print_exc()
        elif chunk1:
            size1, _ = chunk1
            print(f"{letters:6} {size1:10} {'---':>10} {'N/A':>6}")
        else:
            size2, _ = chunk2
            print(f"{letters:6} {'---':>10} {size2:10} {'N/A':>6}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Compare WDT/ADT files to identify differences'
    )
    parser.add_argument(
        'file1',
        type=Path,
        help='First file to compare'
    )
    parser.add_argument(
        'file2',
        type=Path,
        help='Second file to compare'
    )
    args = parser.parse_args()
    
    # Validate files
    if not args.file1.exists():
        print(f"Error: File not found: {args.file1}")
        return 1
    if not args.file2.exists():
        print(f"Error: File not found: {args.file2}")
        return 1
    
    try:
        compare_files(args.file1, args.file2)
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())