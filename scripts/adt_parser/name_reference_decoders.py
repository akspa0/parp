#!/usr/bin/env python3
from dataclasses import dataclass
from typing import List, Optional, Dict
import struct
from io import BytesIO

@dataclass
class NameOffsetPair:
    """Helper class for tracking filename positions"""
    offset: int  # Offset into filename string block
    name: str    # Filename string

class MTEXChunk:
    """Texture filename list"""
    def __init__(self, data: bytes):
        self.filenames: List[str] = []
        self._parse(data)

    def _parse(self, data: bytes):
        # MTEX is a contiguous block of null-terminated strings
        current_name = []
        for byte in data:
            if byte == 0:  # null terminator
                if current_name:  # avoid empty strings
                    self.filenames.append(bytes(current_name).decode('utf-8'))
                    current_name = []
            else:
                current_name.append(byte)
        # Handle last name if data doesn't end with null
        if current_name:
            self.filenames.append(bytes(current_name).decode('utf-8'))

    def get_filename(self, index: int) -> Optional[str]:
        """Get filename by index"""
        if 0 <= index < len(self.filenames):
            return self.filenames[index]
        return None

class MMDXChunk:
    """M2 model filename list"""
    def __init__(self, data: bytes):
        self.filenames: List[str] = []
        self._parse(data)

    def _parse(self, data: bytes):
        # MMDX is a contiguous block of null-terminated strings
        current_name = []
        for byte in data:
            if byte == 0:  # null terminator
                if current_name:  # avoid empty strings
                    self.filenames.append(bytes(current_name).decode('utf-8'))
                    current_name = []
            else:
                current_name.append(byte)
        # Handle last name if data doesn't end with null
        if current_name:
            self.filenames.append(bytes(current_name).decode('utf-8'))

    def get_filename(self, index: int) -> Optional[str]:
        """Get filename by index"""
        if 0 <= index < len(self.filenames):
            return self.filenames[index]
        return None

class MMIDChunk:
    """M2 filename offset list"""
    def __init__(self, data: bytes, mmdx_chunk: Optional[MMDXChunk] = None):
        self.offsets: List[int] = []
        self.name_map: Dict[int, str] = {}  # Maps offsets to names if MMDX provided
        self._parse(data)
        if mmdx_chunk:
            self._build_name_map(mmdx_chunk)

    def _parse(self, data: bytes):
        # MMID is a list of uint32 offsets into MMDX
        num_entries = len(data) // 4
        for i in range(num_entries):
            offset = struct.unpack('<I', data[i*4:(i+1)*4])[0]
            self.offsets.append(offset)

    def _build_name_map(self, mmdx_chunk: MMDXChunk):
        """Build mapping between offsets and actual filenames"""
        current_offset = 0
        for filename in mmdx_chunk.filenames:
            self.name_map[current_offset] = filename
            # +1 for null terminator
            current_offset += len(filename.encode('utf-8')) + 1

    def get_filename(self, offset: int) -> Optional[str]:
        """Get filename by offset"""
        return self.name_map.get(offset)

class MWMOChunk:
    """WMO filename list"""
    def __init__(self, data: bytes):
        self.filenames: List[str] = []
        self._parse(data)

    def _parse(self, data: bytes):
        # MWMO is a contiguous block of null-terminated strings
        current_name = []
        for byte in data:
            if byte == 0:  # null terminator
                if current_name:  # avoid empty strings
                    self.filenames.append(bytes(current_name).decode('utf-8'))
                    current_name = []
            else:
                current_name.append(byte)
        # Handle last name if data doesn't end with null
        if current_name:
            self.filenames.append(bytes(current_name).decode('utf-8'))

    def get_filename(self, index: int) -> Optional[str]:
        """Get filename by index"""
        if 0 <= index < len(self.filenames):
            return self.filenames[index]
        return None

class MWIDChunk:
    """WMO filename offset list"""
    def __init__(self, data: bytes, mwmo_chunk: Optional[MWMOChunk] = None):
        self.offsets: List[int] = []
        self.name_map: Dict[int, str] = {}  # Maps offsets to names if MWMO provided
        self._parse(data)
        if mwmo_chunk:
            self._build_name_map(mwmo_chunk)

    def _parse(self, data: bytes):
        # MWID is a list of uint32 offsets into MWMO
        num_entries = len(data) // 4
        for i in range(num_entries):
            offset = struct.unpack('<I', data[i*4:(i+1)*4])[0]
            self.offsets.append(offset)

    def _build_name_map(self, mwmo_chunk: MWMOChunk):
        """Build mapping between offsets and actual filenames"""
        current_offset = 0
        for filename in mwmo_chunk.filenames:
            self.name_map[current_offset] = filename
            # +1 for null terminator
            current_offset += len(filename.encode('utf-8')) + 1

    def get_filename(self, offset: int) -> Optional[str]:
        """Get filename by offset"""
        return self.name_map.get(offset)

def example_usage():
    """Example usage of name reference chunks"""
    # Create example MTEX data
    mtex_data = b"texture1.blp\0texture2.blp\0texture3.blp\0"
    mtex_chunk = MTEXChunk(mtex_data)
    
    # Create example MMDX/MMID pair
    mmdx_data = b"model1.m2\0model2.m2\0model3.m2\0"
    mmdx_chunk = MMDXChunk(mmdx_data)
    
    # Calculate correct offsets for MMID
    offset1 = 0                  # "model1.m2" starts at 0
    offset2 = len("model1.m2")+1 # "model2.m2" starts after "model1.m2\0"
    offset3 = offset2 + len("model2.m2")+1 # "model3.m2" starts after "model2.m2\0"
    
    mmid_data = struct.pack('<III', offset1, offset2, offset3)
    mmid_chunk = MMIDChunk(mmid_data, mmdx_chunk)
    
    # Create example MWMO/MWID pair
    mwmo_data = b"wmo1.wmo\0wmo2.wmo\0wmo3.wmo\0"
    mwmo_chunk = MWMOChunk(mwmo_data)
    
    # Calculate correct offsets for MWID
    offset1 = 0                # "wmo1.wmo" starts at 0
    offset2 = len("wmo1.wmo")+1 # "wmo2.wmo" starts after "wmo1.wmo\0"
    offset3 = offset2 + len("wmo2.wmo")+1 # "wmo3.wmo" starts after "wmo2.wmo\0"
    
    mwid_data = struct.pack('<III', offset1, offset2, offset3)
    mwid_chunk = MWIDChunk(mwid_data, mwmo_chunk)
    
    # Display results
    print("MTEX (Texture) filenames:")
    for i, name in enumerate(mtex_chunk.filenames):
        print(f"  [{i}] {name}")
    
    print("\nMMDX/MMID (M2) filenames and offsets:")
    for offset in mmid_chunk.offsets:
        name = mmid_chunk.get_filename(offset)
        print(f"  [{offset}] {name}")
    
    print("\nMWMO/MWID (WMO) filenames and offsets:")
    for offset in mwid_chunk.offsets:
        name = mwid_chunk.get_filename(offset)
        print(f"  [{offset}] {name}")

if __name__ == "__main__":
    example_usage()
