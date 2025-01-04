#!/usr/bin/env python3
import struct
import logging
import math
# decode_chunks.py
from typing import Dict, Any, List
from decode_binary_structures import ADTStructures

def decode_MTEX(data: bytes) -> List[str]:
    return ADTStructures.decode_mmdx(data)

def decode_MHDR(data: bytes) -> Dict[str, Any]:
    return ADTStructures.decode_mhdr(data)

def decode_MCIN(data: bytes) -> List[Dict[str, int]]:
    """
    Decode MCIN (Map Chunk Index) chunk
    Structure:
    4096 bytes total (256 entries * 16 bytes each)
    Each entry:
    uint32_t offset
    uint32_t size
    uint32_t flags
    uint32_t async_id
    """
    try:
        entries = []
        entry_size = 16  # 4 uint32s
        expected_entries = 256
        
        if len(data) < entry_size:
            raise ValueError(f"MCIN data too small: {len(data)} bytes, minimum {entry_size} required")

        # Calculate how many complete entries we can process
        num_entries = min(expected_entries, len(data) // entry_size)
        
        for i in range(num_entries):
            offset = i * entry_size
            if offset + entry_size > len(data):
                break
                
            entry_data = struct.unpack('<4I', data[offset:offset + entry_size])
            entries.append({
                'offset': entry_data[0],
                'size': entry_data[1],
                'flags': entry_data[2],
                'async_id': entry_data[3]
            })
        
        return {
            'entries': entries,
            'entry_count': len(entries),
            'expected_entries': expected_entries,
            'complete': len(entries) == expected_entries
        }
    except Exception as e:
        logging.error(f"Error decoding MCIN: {e}")
        return {
            'error': str(e),
            'raw_data': data.hex(),
            'data_length': len(data)
        }

def decode_MMDX(data: bytes) -> List[str]:
    return ADTStructures.decode_mmdx(data)

def decode_MMID(data: bytes) -> List[int]:
    return ADTStructures.decode_mmid(data)

def decode_MWMO(data: bytes) -> List[str]:
    return ADTStructures.decode_mmdx(data)

def decode_MWID(data: bytes) -> List[int]:
    return ADTStructures.decode_mwid(data)

def decode_MDDF(data: bytes) -> List[Dict[str, Any]]:
    return ADTStructures.decode_mddf(data)

def decode_MODF(data: bytes) -> List[Dict[str, Any]]:
    return ADTStructures.decode_modf(data)

def decode_MCSE(data: bytes) -> List[Dict[str, Any]]:
    return ADTStructures.decode_mcse(data)

def decode_MCRF(data: bytes) -> List[int]:
    return ADTStructures.decode_mcrf(data)

def decode_MCNK(data):
    """
    Comprehensive MCNK chunk decoder with enhanced error handling
    """
    try:
        # Check if data is sufficient for parsing
        if len(data) < 96:
            logging.error(f"MCNK data too small. Got {len(data)} bytes, expected at least 96.")
            return {
                'error': 'Insufficient data',
                'raw_data': data.hex()
            }, len(data)

        # Parsing header with safe unpacking
        header_data = list(struct.unpack("<16I", data[:64]))
        position_data = list(struct.unpack("<IIIIfffII", data[88:88+36]))

        # Decode flags bitwise
        flags = header_data[0]
        mcnk_flags = {
            "has_mcsh": bool(flags & 0x1),
            "impassable": bool(flags & 0x2),
            "liquid_river": bool(flags & 0x4),
            "liquid_ocean": bool(flags & 0x8),
            "liquid_magma": bool(flags & 0x10),
            "liquid_slime": bool(flags & 0x20),
            "has_mccv": bool(flags & 0x40),
            "unknown_0x80": bool(flags & 0x80),
            "do_not_fix_alpha_map": bool(flags & 0x8000),
            "high_res_holes": bool(flags & 0x10000)
        }

        # Safely create offsets dictionary with more robust handling
        offsets = {
            'MCVT': header_data[5] if len(header_data) > 5 else 0,
            'MCNR': header_data[6] if len(header_data) > 6 else 0,
            'MCLY': header_data[7] if len(header_data) > 7 else 0,
            'MCAL': header_data[8] if len(header_data) > 8 else 0,
            'MCSH': header_data[10] if len(header_data) > 10 else 0,
            'MCLQ': header_data[14] if len(header_data) > 14 else 0,
            'MCCV': header_data[15] if len(header_data) > 15 else 0,
        }

        # Safely create sizes dictionary with fallback
        sizes = {
            'MCVT': 145 * 4,  # Known vertex height size
            'MCNR': 448,       # Known normals size (435 + 13 padding)
            'MCLY': 16,        # Known layer entry size
            'MCAL': header_data[9] if len(header_data) > 9 else 0,
            'MCSH': header_data[11] if len(header_data) > 11 else 0,
            'MCLQ': header_data[15] if len(header_data) > 15 else 0,
        }

        # Sub-chunks storage
        sub_chunks = {}

        # Layer flags for MCAL decoding
        layer_flags = 0

        # Process each potential sub-chunk with more robust error handling
        for chunk_id, offset in offsets.items():
            if offset == 0:
                continue

            try:
                # Determine chunk size with fallback
                chunk_size = sizes.get(chunk_id, 0)

                # Robust size and offset checking
                if offset >= len(data):
                    logging.warning(f"Sub-chunk {chunk_id} offset {offset} exceeds data length {len(data)}")
                    continue

                # Calculate maximum possible size
                max_possible_size = len(data) - offset

                # Adjust chunk size if it would exceed data length
                if chunk_size == 0 or chunk_size > max_possible_size:
                    chunk_size = max(0, max_possible_size)
                    logging.warning(f"Adjusting {chunk_id} chunk size to {chunk_size} to prevent overflow")

                # Skip if no data
                if chunk_size == 0:
                    continue

                # Extract sub-chunk data
                sub_chunk_data = data[offset:offset + chunk_size]

                # Specific chunk decoding
                if chunk_id == 'MCLY':
                    # Decode layers first to get flags for MCAL
                    layer_result = decode_MCLY(sub_chunk_data)
                    sub_chunks[chunk_id] = layer_result
                    # Extract flags from first layer if exists
                    if layer_result.get('layers'):
                        layer_flags = layer_result['layers'][0].get('flags', 0)
                elif chunk_id == 'MCAL':
                    # Pass additional context for MCAL decoding
                    sub_chunks[chunk_id] = decode_MCAL(
                        sub_chunk_data, 
                        mcly_flags=layer_flags,
                        mcnk_flags=flags
                    )
                elif chunk_id == 'MCSH':
                    # Pass MCNK flags to MCSH decoder
                    sub_chunks[chunk_id] = decode_MCSH(sub_chunk_data, mcnk_flags=flags)
                elif chunk_id in decoders:
                    # Use specific decoders for other chunks
                    sub_chunks[chunk_id] = decoders[chunk_id](sub_chunk_data)
                else:
                    # Fallback for unknown chunks
                    sub_chunks[chunk_id] = {
                        'raw_data': sub_chunk_data.hex(),
                        'length': len(sub_chunk_data)
                    }

            except Exception as e:
                logging.error(f"Error processing sub-chunk {chunk_id}: {e}")
                sub_chunks[chunk_id] = {
                    'error': str(e),
                    'raw_data': sub_chunk_data.hex() if 'sub_chunk_data' in locals() else ''
                }

        # Safely create header dictionary
        header = {
            'flags': mcnk_flags,
            'index_x': header_data[1] if len(header_data) > 1 else None,
            'index_y': header_data[2] if len(header_data) > 2 else None,
            'num_layers': header_data[3] if len(header_data) > 3 else None,
            'num_doodad_refs': header_data[4] if len(header_data) > 4 else None,
            'area_id': header_data[13] if len(header_data) > 13 else None,
            'num_map_obj_refs': header_data[14] if len(header_data) > 14 else None,
            'holes': header_data[15] if len(header_data) > 15 else None,
            'position': {
                'x': position_data[5] if len(position_data) > 5 else None,
                'y': position_data[6] if len(position_data) > 6 else None,
                'z': position_data[4] if len(position_data) > 4 else None
            }
        }

        return {
            'header': header,
            'sub_chunks': sub_chunks
        }, len(data)

    except Exception as e:
        logging.error(f"Critical error decoding MCNK: {e}")
        return {
            'error': str(e),
            'raw_data': data.hex()
        }, len(data)

    except Exception as e:
        logging.error(f"Critical error decoding MCNK: {e}")
        return {
            'error': str(e),
            'raw_data': data.hex()
        }, len(data)

    except Exception as e:
        logging.error(f"Critical error decoding MCNK: {e}")
        return {
            'error': str(e),
            'raw_data': data.hex()
        }, len(data)
    
    except Exception as e:
        logging.error(f"Critical error decoding MCNK: {e}")
        return {
            'error': str(e),
            'raw_data': data.hex()
        }, len(data)

def decode_MCVT(data):
    """Decode vertex height map"""
    heights = struct.unpack(f'<{len(data)//4}f', data)
    return {
        'heights': list(heights),
        'raw_data': data.hex()
    }

def decode_MCNR(data):
    """Decode normals data (MCNR chunk)"""
    try:
        # Validate data length - MCNR should be 435 bytes + padding
        expected_size = 435
        if len(data) < expected_size:
            logging.error(f"MCNR data too small: {len(data)} bytes")
            return {
                'error': f'Insufficient data: {len(data)} bytes',
                'raw_data': data.hex()
            }

        normals = []
        entry_size = 3  # 3 bytes per component
        
        # Only process complete normal entries
        num_normals = min(145, len(data) // (entry_size * 3))
        
        for i in range(num_normals):
            base = i * entry_size * 3
            if base + (entry_size * 3) > len(data):
                break
                
            x_bytes = data[base:base+3]
            y_bytes = data[base+3:base+6]
            z_bytes = data[base+6:base+9]
            
            try:
                x = (int.from_bytes(x_bytes, byteorder='little', signed=True) / 127.0)
                y = (int.from_bytes(y_bytes, byteorder='little', signed=True) / 127.0)
                z = (int.from_bytes(z_bytes, byteorder='little', signed=True) / 127.0)
            except Exception as e:
                logging.error(f"Error converting normal components at index {i}: {e}")
                continue

            normals.append({
                'x': x,
                'y': y,
                'z': z
            })
        
        return {
            'normals': normals,
            'count': len(normals),
            'processed_bytes': len(data)
        }
        
    except Exception as e:
        logging.error(f"Error decoding MCNR: {e}")
        return {
            'error': str(e),
            'normals': [],
            'raw_data': data.hex()
        }

def decode_MCLY(data):
    """Decode texture layers"""
    layers = []
    layer_format = '<IB3xI'
    layer_size = struct.calcsize(layer_format)
    
    for i in range(0, len(data), layer_size):
        if i + layer_size > len(data):
            break
        
        texture_id, flags, offset_in_mcal = struct.unpack_from(layer_format, data, i)
        layers.append({
            'texture_id': texture_id,
            'flags': flags,  # Keep raw flags for MCAL
            'decoded_flags': {
                'animation_rotation': flags & 0x7,
                'animation_speed': (flags >> 3) & 0x7,
                'animation_enabled': bool(flags & 0x100),
                'overbright': bool(flags & 0x200),
                'use_alpha_map': bool(flags & 0x400),
                'alpha_map_compressed': bool(flags & 0x800),
                'use_cube_map_reflection': bool(flags & 0x1000)
            },
            'offset_in_mcal': offset_in_mcal
        })
    
    return {
        'layers': layers,
        'raw_data': data.hex()
    }

def decode_MCAL(data, mcly_flags=0, mphd_flags=0, mcnk_flags=0):
    """
    Decode Alpha Map (MCAL) chunk.

    Parameters:
        data (bytes): Raw MCAL data to decode.
        mcly_flags (int): Flags from MCLY chunk.
        mphd_flags (int): Flags from MPHD chunk.
        mcnk_flags (int): Flags from MCNK chunk.

    Returns:
        dict: Decoded MCAL data or error information.
    """
    try:
        is_compressed = bool(mcly_flags & 0x200)
        is_high_res = bool(mphd_flags & (0x4 | 0x80))
        do_not_fix_alpha_map = bool(mcnk_flags & 0x8000)

        result = {
            "is_compressed": is_compressed,
            "is_high_res": is_high_res,
            "do_not_fix_alpha_map": do_not_fix_alpha_map,
            "raw_size": len(data),
        }

        if not is_compressed:
            if is_high_res:
                if len(data) not in {4096, 2048}:
                    logging.warning(f"Unexpected high-res uncompressed MCAL size: {len(data)} bytes")
                    result["error"] = f"Unexpected high-res uncompressed size: {len(data)} bytes"
                    result["raw_data"] = data.hex()
                    return result

                # High-resolution uncompressed decoding
                result["decoded_alpha_map"] = [
                    data[i] for i in range(len(data))
                ]
                result["resolution"] = "high-res"
            else:
                if len(data) != 2048:
                    logging.warning(f"Unexpected low-res uncompressed MCAL size: {len(data)} bytes")
                    result["error"] = f"Unexpected low-res uncompressed size: {len(data)} bytes"
                    result["raw_data"] = data.hex()
                    return result

                # Low-resolution uncompressed decoding
                result["decoded_alpha_map"] = [
                    data[i] for i in range(len(data))
                ]
                result["resolution"] = "low-res"
        else:
            # Handle compressed MCAL data
            try:
                # Replace this with actual decompression logic if applicable
                decompressed_data = decompress_mcal(data)  # Example function
                result["decoded_alpha_map"] = decompressed_data
                result["resolution"] = "compressed"
            except Exception as e:
                logging.error(f"Error decompressing MCAL data: {e}")
                result["error"] = "Decompression failed"
                result["raw_data"] = data.hex()

        return result
    except Exception as e:
        logging.error(f"Error decoding MCAL: {e}")
        return {"error": str(e), "raw_data": data.hex()}

def decode_MCSH(data):
    """Decode shadow map"""
    return {
        'shadow_map': list(data),
        'raw_data': data.hex()
    }

def decode_MCLQ(data):
    """Decode liquid data"""
    # Basic liquid data parsing
    header_format = '<9f'
    header_size = struct.calcsize(header_format)
    heights = struct.unpack(header_format, data[:header_size])
    
    return {
        'heights': list(heights),
        'raw_data': data.hex()
    }

def decode_MCCV(data):
    """Decode vertex colors"""
    colors = []
    color_format = '<4B'
    color_size = struct.calcsize(color_format)
    
    for i in range(0, len(data), color_size):
        r, g, b, a = struct.unpack_from(color_format, data, i)
        colors.append({
            'r': r,
            'g': g,
            'b': b,
            'a': a
        })
    
    return {
        'vertex_colors': colors,
        'raw_data': data.hex()
    }

# Decoders for other chunks
def decode_MTEX(data):
    """Decode texture file paths"""
    textures = data.decode('utf-8').split('\x00')[:-1]
    return {'textures': textures}, len(data)

def decode_MDDF(data):
    """
    Decode doodad (M2 model) placement information (MDDF chunk)
    
    Structure (36 bytes total):
    uint32_t nameId       - references MMID chunk entry or file data id if mddf_entry_is_filedata_id flag is set
    uint32_t uniqueId     - should be unique across loaded ADTs
    C3Vector position     - relative to map corner (3 floats)
    C3Vector rotation     - in degrees (3 floats)
    uint16_t scale        - 1024 = 1.0f
    uint16_t flags        - MDDFFlags enum values
    """
    try:
        entries = []
        entry_format = '<2I6f2H'  # 2 uint32, 6 floats, 2 uint16
        entry_size = struct.calcsize(entry_format)
        
        # Flag definitions
        MDDF_FLAGS = {
            'mddf_biodome': 0x1,
            'mddf_shrubbery': 0x2,
            'mddf_unk_4': 0x4,
            'mddf_unk_8': 0x8,
            'mddf_unk_10': 0x10,
            'mddf_liquid_known': 0x20,
            'mddf_entry_is_filedata_id': 0x40,
            'mddf_unk_100': 0x100,
            'mddf_accept_proj_textures': 0x1000
        }
        
        for i in range(0, len(data), entry_size):
            if i + entry_size > len(data):
                break
                
            entry = struct.unpack_from(entry_format, data, i)
            
            # Decode flags
            flags = entry[9]
            decoded_flags = {name: bool(flags & value) for name, value in MDDF_FLAGS.items()}
            
            entries.append({
                'nameId': entry[0],  # References MMID chunk or file data id
                'uniqueId': entry[1],
                'position': {
                    'x': entry[2],  # Relative to map corner
                    'y': entry[3],
                    'z': entry[4]
                },
                'rotation': {
                    'x': entry[5],  # In degrees
                    'y': entry[6],
                    'z': entry[7]
                },
                'scale': entry[8] / 1024.0,  # Convert to float where 1024 = 1.0f
                'flags': flags,  # Raw flags value
                'decoded_flags': decoded_flags  # Human-readable flags
            })
        
        return {
            'entries': entries,
            'entry_count': len(entries),
            'bytes_per_entry': entry_size,
            'total_bytes': len(data)
        }, len(data)
    
    except Exception as e:
        logging.error(f"Error decoding MDDF: {e}")
        return {
            'error': str(e),
            'entries': [],
            'raw_data': data.hex()
        }, len(data)

def decode_MCAL(data, mcly_flags=0, mphd_flags=0, mcnk_flags=0):
    """
    Decode Alpha Map (MCAL) chunk with comprehensive support for different formats
    
    Args:
        data (bytes): Raw alpha map data
        mcly_flags (int): Texture layer flags from MCLY
        mphd_flags (int): Map header flags
        mcnk_flags (int): MCNK chunk flags
    
    Returns:
        dict: Decoded alpha map information
    """
    try:
        # Determine alpha map mode based on flags
        is_compressed = bool(mcly_flags & 0x200)
        is_high_res = bool(mphd_flags & (0x4 | 0x80))
        do_not_fix_alpha_map = bool(mcnk_flags & 0x8000)
        
        # Prepare output alpha map
        alpha_map = []
        
        if not is_compressed:
            # Uncompressed handling
            if is_high_res:
                # 4096 byte uncompressed (64x64)
                if len(data) == 4096:
                    alpha_map = list(data)
                else:
                    logging.warning(f"Unexpected uncompressed high-res MCAL size: {len(data)} bytes")
                    alpha_map = list(data)[:4096]
            else:
                # 2048 byte, 4-bit per pixel
                if len(data) == 2048:
                    alpha_map = []
                    for byte in data:
                        # Split byte into two 4-bit values
                        a = byte & 0x0F  # First 4 bits
                        b = (byte & 0xF0) >> 4  # Second 4 bits
                        
                        # Normalize 4-bit values
                        a = (a & 0x0F) | (a << 4)
                        b = (b & 0x0F) | (b << 4)
                        
                        alpha_map.extend([a, b])
                else:
                    logging.warning(f"Unexpected uncompressed low-res MCAL size: {len(data)} bytes")
                    alpha_map = []
        else:
            # Compressed handling (8-bit depth)
            offI = 0  # Input buffer offset
            offO = 0  # Output buffer offset
            
            while offO < 4096:
                if offI >= len(data):
                    logging.warning("Compressed alpha map data ended prematurely")
                    break
                
                # Read control byte
                control_byte = data[offI]
                fill = bool(control_byte & 0x80)
                count = control_byte & 0x7F
                offI += 1
                
                for k in range(count):
                    if offO >= 4096:
                        break
                    
                    if fill:
                        # Fill mode: repeat the same value
                        if offI >= len(data):
                            logging.warning("Not enough data for fill mode")
                            break
                        alpha_map.append(data[offI])
                    else:
                        # Copy mode: read different values
                        if offI >= len(data):
                            logging.warning("Not enough data for copy mode")
                            break
                        alpha_map.append(data[offI])
                        offI += 1
                    
                    offO += 1
                
                # Move input index for fill mode
                if fill:
                    offI += 1
        
        # Handle special case for do_not_fix_alpha_map
        if do_not_fix_alpha_map and len(alpha_map) == 4096:
            # Replicate last row and column
            fixed_alpha_map = []
            for y in range(64):
                row = []
                for x in range(64):
                    if x == 63:
                        row.append(alpha_map[y * 64 + 62])
                    elif y == 63:
                        row.append(alpha_map[62 * 64 + x])
                    else:
                        row.append(alpha_map[y * 64 + x])
                fixed_alpha_map.extend(row)
            alpha_map = fixed_alpha_map
        
        return {
            'alpha_map': alpha_map,
            'mode': {
                'compressed': is_compressed,
                'high_res': is_high_res,
                'do_not_fix_alpha_map': do_not_fix_alpha_map
            },
            'original_length': len(data),
            'decoded_length': len(alpha_map),
            'raw_data': data.hex()
        }
    
    except Exception as e:
        logging.error(f"Error decoding MCAL: {e}")
        return {
            'error': str(e),
            'raw_data': data.hex(),
            'original_length': len(data)
        }

def decode_MCSH(data, mcnk_flags=0):
    """
    Decode Shadow Map (MCSH) chunk with comprehensive handling
    
    Args:
        data (bytes): Raw shadow map data
        mcnk_flags (int): MCNK chunk flags
    
    Returns:
        dict: Decoded shadow map information
    """
    try:
        # Check if shadow map should be fixed
        do_not_fix_alpha_map = bool(mcnk_flags & 0x8000)
        
        # Prepare shadow map
        shadow_map = []
        
        # Unpack bit-packed shadow map (LSB first)
        for byte in data:
            # Unpack bits in LSB order
            shadow_bits = [
                bool(byte & (1 << j)) for j in range(8)
            ]
            shadow_map.extend(shadow_bits)
        
        # Handle special case similar to alpha map
        if do_not_fix_alpha_map and len(shadow_map) == 4096:
            # Replicate last row and column
            fixed_shadow_map = []
            for y in range(64):
                row = []
                for x in range(64):
                    if x == 63:
                        row.append(shadow_map[y * 64 + 62])
                    elif y == 63:
                        row.append(shadow_map[62 * 64 + x])
                    else:
                        row.append(shadow_map[y * 64 + x])
                fixed_shadow_map.extend(row)
            shadow_map = fixed_shadow_map
        
        return {
            'shadow_map': shadow_map,
            'mode': {
                'do_not_fix_shadow_map': do_not_fix_alpha_map
            },
            'original_length': len(data),
            'decoded_length': len(shadow_map),
            'raw_data': data.hex(),
            'description': 'Bit-packed shadow map (0=light, 1=shadow)'
        }
    
    except Exception as e:
        logging.error(f"Error decoding MCSH: {e}")
        return {
            'error': str(e),
            'raw_data': data.hex(),
            'original_length': len(data)
        }

def decode_generic(data):
    """
    Generic decoder for unhandled chunks.
    """
    return {"raw_data": data.hex(), "error": "No specific decoder available"}

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

# Combine decoders into a dictionary
decoders = {
    'MVER': decode_MVER,  # Add MVER decoder
    'REVM': decode_MVER,
    'RDHM': decode_MHDR,
    'MHDR': decode_MHDR,
    'MCIN': decode_MCIN,
    'NICM': decode_MCIN,  # Add NICM mapping to the same decoder
    'MTEX': decode_MTEX,
    'MMDX': decode_MMDX,
    'MMID': decode_MMID,
    'MWMO': decode_MWMO,
    'MWID': decode_MWID,
    'MDDF': decode_MDDF,
    'MODF': decode_MODF,
    'MCNK': decode_MCNK,
    'MCVT': decode_MCVT,
    'MCNR': decode_MCNR,
    'MCLY': decode_MCLY,
    'MCAL': decode_MCAL,
    'MCSH': decode_MCSH,
    'MCLQ': decode_MCLQ,
    'MCCV': decode_MCCV,
    "OtherMagic": decode_generic  # Placeholder
}



# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
