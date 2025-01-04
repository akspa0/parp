# decode_binary_structures.py
from typing import Dict, Any, List, Tuple
import struct
from dataclasses import dataclass

@dataclass
class ChunkHeader:
    magic: str
    size: int

    @classmethod
    def from_bytes(cls, data: bytes, offset: int = 0) -> 'ChunkHeader':
        magic = data[offset:offset+4].decode('ascii')
        size = struct.unpack('I', data[offset+4:offset+8])[0]
        return cls(magic, size)

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

class ADTStructures:
    @staticmethod
    def decode_mhdr(data: bytes) -> Dict[str, Any]:
        """Decode ADT header chunk"""
        values = struct.unpack('13I', data)
        flags = values[0]
        offsets = values[1:9]  # Take the next 8 values after flags
        return {
            'flags': flags,
            'mcin_offset': offsets[0],
            'mtex_offset': offsets[1],
            'mmdx_offset': offsets[2],
            'mmid_offset': offsets[3],
            'mwmo_offset': offsets[4],
            'mwid_offset': offsets[5],
            'mddf_offset': offsets[6],
            'modf_offset': offsets[7]
        }

    @staticmethod
    def decode_mcin(data: bytes) -> List[Dict[str, int]]:
        """Decode cell index chunk"""
        cells = []
        for i in range(256):
            offset = i * 24
            cell_data = struct.unpack('6I', data[offset:offset+24])
            cells.append({
                'offset': cell_data[0],
                'size': cell_data[1],
                'flags': cell_data[2],
                'async_id': cell_data[3],
                'layer_count': cell_data[4]
            })
        return cells

    @staticmethod
    def decode_mmdx(data: bytes) -> List[str]:
        """Decode M2 filename list"""
        return read_c_string_list(data)

    @staticmethod
    def decode_mmid(data: bytes) -> List[int]:
        """Decode M2 instance ID list"""
        count = len(data) // 4
        return list(struct.unpack(f'{count}I', data))

    @staticmethod
    def decode_mwid(data: bytes) -> List[int]:
        """Decode WMO instance ID list"""
        count = len(data) // 4
        return list(struct.unpack(f'{count}I', data))

    @staticmethod
    def decode_mcse(data: bytes) -> List[Dict[str, Any]]:
        """Decode sound emitters"""
        emitters = []
        emitter_size = 28
        num_emitters = len(data) // emitter_size
        
        for i in range(num_emitters):
            offset = i * emitter_size
            emitter_data = struct.unpack('3f4I', data[offset:offset+emitter_size])
            emitters.append({
                'position': (emitter_data[0], emitter_data[1], emitter_data[2]),
                'sound_id': emitter_data[3],
                'sound_name_ids': (emitter_data[4], emitter_data[5]),
                'flags': emitter_data[6]
            })
        
        return emitters

    @staticmethod
    def decode_mcrf(data: bytes) -> List[int]:
        """Decode MCAL reference list"""
        count = len(data) // 4
        return list(struct.unpack(f'{count}I', data))

# decode_binary_structures.py
# (Add these methods to the ADTStructures class)

    @staticmethod
    def decode_mddf(data: bytes) -> List[Dict[str, Any]]:
        """
        Decode M2 placement information
        Structure (36 bytes):
        uint32 name_id
        uint32 unique_id
        float[3] position
        float[3] rotation
        uint16 scale
        uint16 flags
        """
        placements = []
        entry_size = 36
        num_entries = len(data) // entry_size
        
        for i in range(num_entries):
            offset = i * entry_size
            values = struct.unpack('2I6fHH', data[offset:offset+entry_size])
            placements.append({
                'name_id': values[0],
                'unique_id': values[1],
                'position': (values[2], values[3], values[4]),
                'rotation': (values[5], values[6], values[7]),
                'scale': values[8],
                'flags': values[9]
            })
        
        return placements

    @staticmethod
    def decode_modf(data: bytes) -> List[Dict[str, Any]]:
        """
        Decode WMO placement information
        Structure (64 bytes):
        uint32 name_id
        uint32 unique_id
        float[3] position
        float[3] rotation
        float[3] bounds_min
        float[3] bounds_max
        uint16 flags
        uint16 doodad_set
        uint16 name_set
        uint16 unknown
        """
        placements = []
        entry_size = 64
        num_entries = len(data) // entry_size
        
        for i in range(num_entries):
            offset = i * entry_size
            values = struct.unpack('2I9f4H', data[offset:offset+entry_size])
            placements.append({
                'name_id': values[0],
                'unique_id': values[1],
                'position': (values[2], values[3], values[4]),
                'rotation': (values[5], values[6], values[7]),
                'bounds_min': (values[8], values[9], values[10]),
                'bounds_max': (values[11], values[12], values[13]),
                'flags': values[14],
                'doodad_set': values[15],
                'name_set': values[16],
                'unknown': values[17]
            })
        
        return placements

