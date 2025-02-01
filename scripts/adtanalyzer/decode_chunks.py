#!/usr/bin/env python3
import struct
import logging
import math

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
    """
    Enhanced MCNR (Normals) decoder with comprehensive parsing
    
    Handles normal vectors with specific decoding rules:
    - X, Z, Y order (not typical X, Y, Z)
    - Normalized values where 127 = 1.0, -127 = -1.0
    - Potential padding/additional data
    """
    try:
        # Check for standard normal data (145 * 3 = 435 bytes for 64x65 grid)
        # Plus potential 13 bytes of padding
        if len(data) < 435:
            logging.warning(f"Insufficient MCNR data. Expected at least 435 bytes, got {len(data)} bytes")
            return {
                'error': 'Insufficient normal data',
                'raw_data': data.hex(),
                'data_length': len(data)
            }
        
        # Prepare to store normals
        normals = []
        
        # Parse the first 435 bytes (145 * 3) as normal vectors
        for i in range(0, 435, 3):
            try:
                # Unpack in X, Z, Y order
                x, z, y = struct.unpack('<3B', data[i:i+3])
                
                # Convert to normalized float values
                # Normalize X and Y
                x_norm = (x - 127) / 127.0
                y_norm = (y - 127) / 127.0
                
                # Recalculate Z to ensure unit vector
                # Z = sqrt(1 - X² - Y²), ensuring Z is non-negative
                z_norm = max(0, math.sqrt(max(0, 1 - x_norm**2 - y_norm**2)))
                
                normals.append({
                    'x': x_norm,
                    'y': y_norm,
                    'z': z_norm,
                    'original_bytes': {
                        'x': x,
                        'y': y,
                        'z': z
                    }
                })
            except struct.error:
                logging.warning(f"Failed to unpack normal at index {i}")
                break
        
        # Check for padding/additional data
        padding = None
        if len(data) >= 448:
            # Known padding pattern from the notes
            known_padding = data[435:448]
            padding = {
                'bytes': list(known_padding),
                'hex': known_padding.hex()
            }
        
        # Prepare result dictionary
        result = {
            'normals': normals,
            'total_normals': len(normals),
            'expected_normals': 145,
            'raw_data': data.hex(),
            'data_length': len(data)
        }
        
        # Add padding if present
        if padding:
            result['padding'] = padding
        
        return result
    
    except Exception as e:
        logging.error(f"Critical error decoding MCNR: {e}")
        return {
            'error': str(e),
            'raw_data': data.hex(),
            'data_length': len(data)
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

def decode_MCAL(data, compressed=False):
    """Decode alpha maps"""
    if not compressed:
        # Uncompressed 4096 byte (64x64) alpha map
        return {
            'alpha_map': list(data),
            'raw_data': data.hex()
        }
    
    # Compressed alpha map parsing
    alpha_map = []
    pos = 0
    
    while len(alpha_map) < 4096 and pos < len(data):
        control_byte = data[pos]
        is_fill_mode = bool(control_byte & 0x80)
        count = control_byte & 0x7F
        pos += 1
        
        if is_fill_mode:
            value = data[pos]
            pos += 1
            alpha_map.extend([value] * count)
        else:
            alpha_map.extend(data[pos:pos+count])
            pos += count
    
    return {
        'alpha_map': alpha_map,
        'raw_data': data.hex(),
        'compressed': compressed
    }

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
    """Decode doodad placement definitions"""
    entries = []
    entry_format = '<3I3f2H'
    entry_size = struct.calcsize(entry_format)
    
    for i in range(0, len(data), entry_size):
        entry = struct.unpack_from(entry_format, data, i)
        entries.append({
            'nameId': entry[0],
            'uniqueId': entry[1],
            'position': {
                'x': entry[2],
                'y': entry[3],
                'z': entry[4]
            },
            'rotation': {
                'x': entry[5],
                'y': entry[6],
                'z': entry[7]
            },
            'scale': entry[8],
            'flags': entry[9]
        })
    
    return {'entries': entries}, len(data)

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

# Combine decoders into a dictionary
decoders = {
    'MCNK': decode_MCNK,
    'MCVT': decode_MCVT,
    'MCNR': decode_MCNR,
    'MCLY': decode_MCLY,
    'MCAL': decode_MCAL,
    'MCSH': decode_MCSH,
    'MCLQ': decode_MCLQ,
    'MCCV': decode_MCCV,
    'MTEX': decode_MTEX,
    'MDDF': decode_MDDF,
}


# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
