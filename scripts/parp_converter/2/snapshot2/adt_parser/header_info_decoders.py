#!/usr/bin/env python3
from dataclasses import dataclass
from typing import List, Optional
import struct
from enum import IntFlag

class MHDRFlags(IntFlag):
    mhdr_MFBO = 0x1            # Contains a flight box
    mhdr_northrend = 0x2       # Is set for some northrend ones
    mhdr_use_global_map_obj = 0x4
    mhdr_use_tex_flags = 0x8   # Use MTXF chunk to define texture flags
    mhdr_use_height_map = 0x10 # Use MHID chunk to define heightmap info
    mhdr_unk_40 = 0x40        # Legion+
    mhdr_unk_80 = 0x80        # Legion+

@dataclass
class ChunkOffset:
    """Helper class for chunk offsets in MHDR"""
    offset: int
    size: int

    @classmethod
    def from_bytes(cls, data: bytes) -> 'ChunkOffset':
        offset, size = struct.unpack('<II', data)
        return cls(offset, size)

@dataclass
class MHDRData:
    """ADT Header data"""
    flags: MHDRFlags
    mcin: ChunkOffset  # Mandatory
    mtex: ChunkOffset  # Mandatory
    mmdx: ChunkOffset  # Mandatory
    mmid: ChunkOffset  # Mandatory
    mwmo: ChunkOffset  # Mandatory
    mwid: ChunkOffset  # Mandatory
    mddf: ChunkOffset  # Mandatory
    modf: ChunkOffset  # Mandatory
    mfbo: ChunkOffset  # Optional, if flags & mhdr_MFBO
    mh2o: ChunkOffset  # Optional
    mtxf: ChunkOffset  # Optional, if flags & mhdr_use_tex_flags
    mhid: ChunkOffset  # Optional, if flags & mhdr_use_height_map

class MHDRChunk:
    """ADT Header chunk parser"""
    def __init__(self, data: bytes):
        self.data = self._parse(data)

    def _parse(self, data: bytes) -> MHDRData:
        flags = MHDRFlags(struct.unpack('<I', data[0:4])[0])
        
        # Parse all chunk offsets
        return MHDRData(
            flags=flags,
            mcin=ChunkOffset.from_bytes(data[4:12]),
            mtex=ChunkOffset.from_bytes(data[12:20]),
            mmdx=ChunkOffset.from_bytes(data[20:28]),
            mmid=ChunkOffset.from_bytes(data[28:36]),
            mwmo=ChunkOffset.from_bytes(data[36:44]),
            mwid=ChunkOffset.from_bytes(data[44:52]),
            mddf=ChunkOffset.from_bytes(data[52:60]),
            modf=ChunkOffset.from_bytes(data[60:68]),
            mfbo=ChunkOffset.from_bytes(data[68:76]),
            mh2o=ChunkOffset.from_bytes(data[76:84]),
            mtxf=ChunkOffset.from_bytes(data[84:92]),
            mhid=ChunkOffset.from_bytes(data[92:100])
        )

@dataclass
class MCINEntry:
    """MCNK information entry"""
    offset: int          # Absolute position into ADT file
    size: int           # Size of MCNK chunk in bytes
    flags: int          # Runtime flags for this MCNK, not read from file
    async_id: int       # Runtime value for async loading

class MCINChunk:
    """MCNK offset/information chunk parser"""
    def __init__(self, data: bytes):
        self.entries: List[MCINEntry] = []
        self._parse(data)

    def _parse(self, data: bytes):
        # MCIN contains 256 entries (16x16 grid)
        entry_size = 16  # Each entry is 16 bytes
        num_entries = 256

        for i in range(num_entries):
            offset = i * entry_size
            entry_data = data[offset:offset + entry_size]
            offset, size, flags, async_id = struct.unpack('<IIII', entry_data)
            self.entries.append(MCINEntry(offset, size, flags, async_id))

@dataclass
class HeightMapInfo:
    """Height map information for an ADT cell"""
    offset: int
    height_count: int
    base_height: float
    height_range: float

class MHIDChunk:
    """Height map information chunk parser"""
    def __init__(self, data: bytes):
        self.height_maps: List[HeightMapInfo] = []
        self._parse(data)

    def _parse(self, data: bytes):
        # MHID contains 256 entries (16x16 grid)
        entry_size = 16  # Each entry is 16 bytes
        num_entries = 256

        for i in range(num_entries):
            offset = i * entry_size
            entry_data = data[offset:offset + entry_size]
            offset, height_count, base_height, height_range = struct.unpack('<IIff', entry_data)
            self.height_maps.append(HeightMapInfo(
                offset=offset,
                height_count=height_count,
                base_height=base_height,
                height_range=height_range
            ))

def example_usage():
    """Example usage of header and info chunks"""
    # Create example MHDR data
    mhdr_data = bytearray()
    # Flags (has flight box and uses height map)
    mhdr_data.extend(struct.pack('<I', int(MHDRFlags.mhdr_MFBO | MHDRFlags.mhdr_use_height_map)))
    
    # Add some example chunk offsets (12 chunks * 8 bytes each)
    for i in range(12):
        mhdr_data.extend(struct.pack('<II', i * 1000, 500))  # offset, size pairs
    
    # Create example MCIN data (256 entries * 16 bytes each)
    mcin_data = bytearray()
    for i in range(256):
        mcin_data.extend(struct.pack('<IIII', 
            i * 2000,      # offset
            1000,          # size
            0,             # flags
            0              # async_id
        ))
    
    # Create example MHID data (256 entries * 16 bytes each)
    mhid_data = bytearray()
    for i in range(256):
        mhid_data.extend(struct.pack('<IIff',
            i * 100,       # offset
            145,           # height_count (usually 145 heights per cell)
            0.0,           # base_height
            500.0          # height_range
        ))
    
    # Parse chunks
    mhdr_chunk = MHDRChunk(mhdr_data)
    mcin_chunk = MCINChunk(mcin_data)
    mhid_chunk = MHIDChunk(mhid_data)
    
    # Display results
    print("MHDR (Header) Information:")
    print(f"Flags: {mhdr_chunk.data.flags}")
    print("\nChunk Offsets:")
    print(f"  MCIN: offset={mhdr_chunk.data.mcin.offset}, size={mhdr_chunk.data.mcin.size}")
    print(f"  MTEX: offset={mhdr_chunk.data.mtex.offset}, size={mhdr_chunk.data.mtex.size}")
    print(f"  MMDX: offset={mhdr_chunk.data.mmdx.offset}, size={mhdr_chunk.data.mmdx.size}")
    # ... etc for other chunks
    
    print("\nMCIN (MCNK Info) Entries (showing first 5):")
    for i, entry in enumerate(mcin_chunk.entries[:5]):
        print(f"  Cell {i}:")
        print(f"    Offset: {entry.offset}")
        print(f"    Size: {entry.size}")
        print(f"    Flags: {entry.flags}")
        print(f"    Async ID: {entry.async_id}")
    
    print("\nMHID (Height Map Info) Entries (showing first 5):")
    for i, info in enumerate(mhid_chunk.height_maps[:5]):
        print(f"  Cell {i}:")
        print(f"    Offset: {info.offset}")
        print(f"    Height Count: {info.height_count}")
        print(f"    Base Height: {info.base_height}")
        print(f"    Height Range: {info.height_range}")

if __name__ == "__main__":
    example_usage()
