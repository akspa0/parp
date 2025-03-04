"""
Utility functions for the ADT Analyzer
Handles file operations, path normalization, logging setup, etc.
"""

import os
import re
import logging
import struct
from collections import defaultdict

def setup_logging(log_dir, timestamp, log_level="INFO"):
    """Set up logging for the ADT analyzer"""
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging for the parser
    parser_log_filename = os.path.join(log_dir, f"adt_parser_{timestamp}.log")
    
    # Set up the root logger
    logging.basicConfig(
        filename=parser_log_filename,
        filemode='w',
        format='%(asctime)s [%(levelname)s] %(message)s',
        level=getattr(logging, log_level)
    )
    logger = logging.getLogger("parser")
    
    # Add console handler
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    console.setLevel(getattr(logging, log_level))
    logger.addHandler(console)
    
    # Configure logging for missing files
    missing_log_filename = os.path.join(log_dir, f"missing_files_{timestamp}.log")
    missing_logger = logging.getLogger('missing_files')
    missing_file_handler = logging.FileHandler(missing_log_filename, mode='w')
    missing_file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    missing_logger.addHandler(missing_file_handler)
    missing_logger.setLevel(logging.INFO)
    
    return {"parser": logger, "missing": missing_logger}

def read_c_string_list(data):
    """Read a null-terminated string list from binary data"""
    strings = data.split(b'\0')
    return [s.decode('utf-8', 'replace') for s in strings if s]

def load_name_list(base_block, offsets):
    """Load a list of names from a block of data using offsets"""
    names = []
    for off in offsets:
        if off >= len(base_block):
            names.append("<invalid offset>")
            continue
        end = base_block.find(b'\0', off)
        if end == -1:
            name = base_block[off:].decode('utf-8', 'replace')
        else:
            name = base_block[off:end].decode('utf-8', 'replace')
        names.append(name)
    return names

def try_parse_chunks(data, reverse_names=False):
    """Try to parse a chunk list to determine chunk name orientation"""
    pos = 0
    size = len(data)
    chunks = []
    while pos + 8 <= size:
        chunk_name_raw = data[pos:pos+4]
        chunk_name = chunk_name_raw[::-1] if reverse_names else chunk_name_raw
        if pos+8 > size:
            break
        chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
        if pos+8+chunk_size > size:
            break
        chunk_data = data[pos+8:pos+8+chunk_size]
        chunks.append((chunk_name, chunk_data))
        pos += 8 + chunk_size
        if len(chunks) > 10:
            break
    return chunks

def detect_chunk_name_reversal(data):
    """Detect if chunk names need to be reversed"""
    normal_chunks = try_parse_chunks(data, reverse_names=False)
    reversed_chunks = try_parse_chunks(data, reverse_names=True)

    # Common chunks to check for
    known_chunks = [b'MVER', b'MHDR', b'MCIN', b'MTEX', b'MMDX', b'MMID', b'MWMO', b'MWID', b'MDDF', b'MODF']
    
    normal_known = any(c[0] in known_chunks for c in normal_chunks)
    reversed_known = any(c[0] in known_chunks for c in reversed_chunks)

    if normal_known and not reversed_known:
        return False
    elif reversed_known and not normal_known:
        return True
    else:
        return False  # Default to normal

def normalize_filename(fname):
    """Normalize a filename for comparison"""
    # Skip invalid or empty filenames immediately
    if not fname or fname == "<invalid offset>":
        return ""

    fname_norm = fname.lower().replace('\\', '/')
    # Remove leading ./ or /
    fname_norm = fname_norm.lstrip('./').lstrip('/')
    # Collapse multiple slashes
    fname_norm = re.sub('/+', '/', fname_norm)
    return fname_norm

def check_file_in_listfile(fname, known_good_files):
    """Check if a file exists in the listfile"""
    fname_norm = normalize_filename(fname)
    if fname_norm == "":
        # Empty or invalid offset
        return True  # Treat as found so we don't log it as missing
    
    # Always convert .mdx to .m2 before checking
    if fname_norm.endswith('.mdx'):
        fname_norm = fname_norm[:-4] + '.m2'
    
    return fname_norm in known_good_files

def repair_file_path(bad_path, known_good_files):
    """Attempt to repair a bad file path by finding a known-good alternative"""
    bad_norm = normalize_filename(bad_path)
    if not bad_norm:
        return None

    # Try direct match first
    if bad_norm in known_good_files:
        return bad_norm

    # Try to find similar paths
    for good_path in known_good_files:
        if good_path.endswith(bad_norm.split('/')[-1]):
            return good_path

    return None

def generate_patch_file(directory, repairs, timestamp):
    """Generate a patch file with path corrections"""
    patch_path = os.path.join(directory, f"path_patch_{timestamp}.txt")
    with open(patch_path, 'w') as f:
        for bad_path, good_path in repairs.items():
            f.write(f"{bad_path} -> {good_path}\n")
    return patch_path

def write_uid_file(directory, max_uid):
    """Write the maximum uniqueId to a file"""
    ini_path = os.path.join(directory, 'uid.ini')
    with open(ini_path, 'w') as f:
        f.write(f"max_unique_id={max_uid}\n")

def group_adt_files(directory):
    """
    Group related ADT files for split-ADT processing.
    Returns a dictionary where keys are base filenames and values are lists of related files.
    """
    adt_groups = defaultdict(list)
    
    # Define patterns for split-ADT files
    base_pattern = re.compile(r'^(.+?)(\d+)_(\d+)\.adt$', re.IGNORECASE)
    tex_pattern = re.compile(r'^(.+?)(\d+)_(\d+)_tex(\d+)\.adt$', re.IGNORECASE)
    obj_pattern = re.compile(r'^(.+?)(\d+)_(\d+)_obj(\d+)\.adt$', re.IGNORECASE)
    lod_pattern = re.compile(r'^(.+?)(\d+)_(\d+)_lod\.adt$', re.IGNORECASE)
    
    # Get all ADT files in the directory
    all_files = [f for f in os.listdir(directory) if f.lower().endswith('.adt')]
    
    # Group files by their base coordinates
    for filename in all_files:
        filepath = os.path.join(directory, filename)
        base_match = base_pattern.match(filename)
        tex_match = tex_pattern.match(filename)
        obj_match = obj_pattern.match(filename)
        lod_match = lod_pattern.match(filename)
        
        if base_match:
            prefix, x, y = base_match.groups()
            key = f"{prefix}{x}_{y}"
            adt_groups[key].append(filepath)
        elif tex_match:
            prefix, x, y, lod = tex_match.groups()
            key = f"{prefix}{x}_{y}"
            adt_groups[key].append(filepath)
        elif obj_match:
            prefix, x, y, lod = obj_match.groups()
            key = f"{prefix}{x}_{y}"
            adt_groups[key].append(filepath)
        elif lod_match:
            prefix, x, y = lod_match.groups()
            key = f"{prefix}{x}_{y}"
            adt_groups[key].append(filepath)
    
    # Sort files within each group to ensure consistent processing order
    for key in adt_groups:
        adt_groups[key].sort()
    
    return adt_groups
