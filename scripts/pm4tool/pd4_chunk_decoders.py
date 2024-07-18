# pd4_chunk_decoders.py

import logging
import struct
from common_helpers import (
    decode_uint8,
    decode_uint16,
    decode_int16,
    decode_uint32,
    decode_float,
    decode_cstring,
    decode_C3Vector,
    decode_C3Vector_i,
    decode_RGBA
)
from chunk_decoders import (
    decode_MVER_chunk,
    decode_MCRC_chunk,
    decode_MSHD_chunk,
    decode_MSPV_chunk,
    decode_MSPI_chunk,
    decode_MSCN_chunk,
    decode_MSLK_chunk,
    decode_MSVT_chunk,
    decode_MSVI_chunk,
    decode_MSUR_chunk,
    decode_IVSM_chunk,
    decode_LRPM_chunk,
    decode_RRPM_chunk,
    decode_KLSM_chunk,
    decode_HBDM_chunk,
    decode_IBDM_chunk,
    decode_FBDM_chunk,
    decode_SODM_chunk,
    decode_FSDM_chunk
)
from adt_chunk_decoders import (
    decode_MHDR,
    decode_MCIN,
    decode_MTXF,
    decode_MMDX,
    decode_MMID,
    decode_MWMO,
    decode_MWID,
    decode_MDDF,
    decode_MODF,
    decode_MFBO,
    decode_MH2O,
    decode_MCNK,
    decode_MCVT,
    decode_MCLY,
    decode_MCRF,
    decode_MCAL,
    decode_MCSH,
    decode_MCCV,
    decode_MCLQ,
    decode_MCSE,
    decode_MCLV
)

# Function to reverse chunk IDs
def reverse_chunk_id(chunk_id):
    return chunk_id[::-1]

# Additional PD4 specific decoders
def decode_PD4SPEC_chunk(data, offset=0):
    decoded = {}
    # Implement specific decoding logic here
    logging.debug(f"PD4SPEC Chunk: {decoded}")
    return decoded, offset

# Dictionary to map PD4 chunk IDs to decoder functions
pd4_chunk_decoders = {
    'MVER': decode_MVER_chunk,
    'MHDR': decode_MHDR,
    'MCIN': decode_MCIN,
    'MTXF': decode_MTXF,
    'MMDX': decode_MMDX,
    'MMID': decode_MMID,
    'MWMO': decode_MWMO,
    'MWID': decode_MWID,
    'MDDF': decode_MDDF,
    'MODF': decode_MODF,
    'MFBO': decode_MFBO,
    'MH2O': decode_MH2O,
    'MCNK': decode_MCNK,
    'MCVT': decode_MCVT,
    'MCLY': decode_MCLY,
    'MCRF': decode_MCRF,
    'MCAL': decode_MCAL,
    'MCSH': decode_MCSH,
    'MCCV': decode_MCCV,
    'MCLQ': decode_MCLQ,
    'MCSE': decode_MCSE,
    'MCLV': decode_MCLV,
    'REVM': decode_MVER_chunk,
    'CRCM': decode_MCRC_chunk,
    'DHSM': decode_MSHD_chunk,
    'VPSM': decode_MSPV_chunk,
    'IPSM': decode_MSPI_chunk,
    'NCSM': decode_MSCN_chunk,
    'KLSM': decode_KLSM_chunk,
    'TVSM': decode_MSVT_chunk,
    'IVSM': decode_IVSM_chunk,
    'RUSM': decode_MSUR_chunk,
    'LRPM': decode_LRPM_chunk,
    'RRPM': decode_RRPM_chunk,
    'HBDM': decode_HBDM_chunk,
    'IBDM': decode_IBDM_chunk,
    'FBDM': decode_FBDM_chunk,
    'SODM': decode_SODM_chunk,
    'FSDM': decode_FSDM_chunk,
    'PD4SPEC': decode_PD4SPEC_chunk,
    # Add additional PD4 specific decoders here...
}

# Function to categorize and parse PD4 chunks
def parse_pd4(file_path):
    with open(file_path, 'rb') as file:
        data = file.read()
    
    offset = 0
    parsed_data = []

    while offset < len(data):
        chunk_id = data[offset:offset + 4].decode('utf-8')
        chunk_size = int.from_bytes(data[offset+4:offset+8], byteorder='little')
        chunk_data = data[offset+8:offset+8 + chunk_size]
        offset += 8 + chunk_size

        decoder = pd4_chunk_decoders.get(chunk_id) or pd4_chunk_decoders.get(reverse_chunk_id(chunk_id))
        if decoder:
            decoded_data, _ = decoder(chunk_data, 0)
            parsed_data.append({
                'id': chunk_id,
                'size': chunk_size,
                'data': decoded_data
            })
        else:
            logging.warning(f"No decoder found for chunk ID {chunk_id}")

    return parsed_data
