#!/usr/bin/env python3
import struct
import logging
import math
from typing import Dict, Any, List, Tuple
from decode_binary_structures import ADTStructures


def decode_MTEX(data: bytes) -> Dict[str, List[str]]:
    textures = data.decode('utf-8').split('\x00')[:-1]
    return {'textures': textures}

def decode_MHDR(data: bytes) -> Dict[str, Any]:
    """Decode ADT header chunk"""
    try:
        # MHDR is 64 bytes total
        # First 4 bytes are flags
        # Next 8 uint32 values are offsets
        # Remaining bytes are unused
        if len(data) < 64:
            raise ValueError(f"MHDR data too short: {len(data)} bytes")

        flags = int.from_bytes(data[0:4], "little")
        offsets = struct.unpack('<8I', data[4:36])  # 8 uint32 values

        return {
            'flags': flags,
            'mcin_offset': offsets[0],  # Chunk index
            'mtex_offset': offsets[1],  # Texture names
            'mmdx_offset': offsets[2],  # Model filenames
            'mmid_offset': offsets[3],  # Map object file IDs
            'mwmo_offset': offsets[4],  # WMO filenames
            'mwid_offset': offsets[5],  # WMO file IDs
            'mddf_offset': offsets[6],  # Doodad placement info
            'modf_offset': offsets[7],  # WMO placement info
            'raw_data': data.hex()
        }
    except Exception as e:
        logging.error(f"Error decoding MHDR: {e}")
        return {
            "error": str(e),
            "raw_data": data.hex()
        }


def decode_MCIN(data: bytes) -> Dict[str, Any]:
    """Decode cell index chunk"""
    return ADTStructures.decode_mcin(data)

def decode_MMDX(data: bytes) -> Dict[str, List[str]]:
    strings = read_c_string_list(data)
    return {'filenames': strings}

def decode_MMID(data: bytes) -> Dict[str, List[int]]:
    count = len(data) // 4
    ids = list(struct.unpack(f'{count}I', data))
    return {'ids': ids}

def decode_MWMO(data: bytes) -> Dict[str, List[str]]:
    strings = read_c_string_list(data)
    return {'filenames': strings}

def decode_MWID(data: bytes) -> Dict[str, List[int]]:
    count = len(data) // 4
    ids = list(struct.unpack(f'{count}I', data))
    return {'ids': ids}

def decode_MDDF(data: bytes) -> Dict[str, Any]:
    """Decode M2 placement information"""
    return ADTStructures.decode_mddf(data)

def decode_MODF(data: bytes) -> Dict[str, Any]:
    """Decode WMO placement information"""
    return ADTStructures.decode_modf(data)

def decode_MCSE(data: bytes) -> Dict[str, Any]:
    """Decode sound emitters"""
    return ADTStructures.decode_mcse(data)

def decode_MCRF(data: bytes) -> Dict[str, List[int]]:
    """Decode MCAL reference list"""
    return ADTStructures.decode_mcrf(data)

def decode_MVER(data: bytes) -> Dict[str, Any]:
    """Decode version chunk"""
    try:
        if len(data) != 4:
            raise ValueError(f"MVER data length must be 4 bytes, got {len(data)}")
        version = int.from_bytes(data, "little")
        return {
            "version": version,
            "raw_data": data.hex()
        }
    except Exception as e:
        logging.error(f"Error decoding MVER: {e}")
        return {
            "error": str(e),
            "raw_data": data.hex()
        }

def read_c_string(data: bytes, offset: int = 0) -> Tuple[str, int]:
    """Read null-terminated string from bytes"""
    end = offset
    while end < len(data) and data[end] != 0:
        end += 1
    string = data[offset:end].decode('utf-8')
    return string, end + 1

def read_c_string_list(data: bytes) -> List[str]:
    """Read multiple null-terminated strings until end of data"""
    strings = []
    offset = 0
    while offset < len(data):
        string, new_offset = read_c_string(data, offset)
        if string:
            strings.append(string)
        offset = new_offset
    return strings

# Combine decoders into a dictionary
decoders = {
    # Version and header chunks
    'MVER': decode_MVER,
    'REVM': decode_MVER,
    'RDHM': decode_MHDR,
    'MHDR': decode_MHDR,
    
    # Index chunks
    'MCIN': decode_MCIN,
    'NICM': decode_MCIN,
    
    # Asset reference chunks
    'MTEX': decode_MTEX,  # Texture filenames
    'MMDX': decode_MMDX,  # M2 model filenames
    'MMID': decode_MMID,  # M2 model instance IDs
    'MWMO': decode_MWMO,  # WMO filenames
    'MWID': decode_MWID,  # WMO instance IDs
    
    # Placement chunks
    'MDDF': decode_MDDF,  # M2 model placements
    'MODF': decode_MODF,  # WMO placements
    
    # Sound chunks
    'MCSE': decode_MCSE,  # Sound emitters
    
    # Reference chunks
    'MCRF': decode_MCRF,  # MCAL references
    
    # MCNK subchunks (these are handled by MCNKChunk class)
    'MCVT': None,  # Height vertices
    'MCNR': None,  # Normals
    'MCLY': None,  # Material layers
    'MCAL': None,  # Alpha maps
    'MCSH': None,  # Shadows
    'MCCV': None,  # Vertex colors
    'MCLV': None   # Light values
}

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
