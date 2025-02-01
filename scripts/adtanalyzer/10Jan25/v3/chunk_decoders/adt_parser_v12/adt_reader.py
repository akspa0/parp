#!/usr/bin/env python3
from dataclasses import dataclass
from typing import Dict, List, Optional, BinaryIO
import struct
from enum import IntFlag
import os

from mcnk_base_decoder import MCNKChunk
from liquid_decoders import MH2OChunk, MCLQLiquid  # Pre-Cata liquid
from placement_decoders import MDDFChunk, MODFChunk
from name_reference_decoders import (
    MTEXChunk, MMDXChunk, MMIDChunk,
    MWMOChunk, MWIDChunk
)
from misc_root_decoders import MFBOChunk, MTXFChunk

class MHDRFlags(IntFlag):
    """ADT Header flags"""
    mhdr_MFBO = 0x1            # Contains a flight box
    mhdr_northrend = 0x2       # Is set for some northrend ones
    mhdr_use_global_map_obj = 0x4  # Uses global map objects
    mhdr_use_tex_flags = 0x8   # Uses MTXF chunk
    mhdr_use_height_map = 0x10 # Uses MHID chunk for heightmap info
    mhdr_unk_40 = 0x40        # Legion+
    mhdr_unk_80 = 0x80        # Legion+

@dataclass
class ChunkHeader:
    """Generic chunk header"""
    magic: str
    size: int
    offset: int

@dataclass
class MCINEntry:
    """MCNK information entry"""
    offset: int
    size: int
    flags: int
    async_id: int
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'MCINEntry':
        offset, size, flags, async_id = struct.unpack('<4I', data)
        return cls(offset, size, flags, async_id)

class ADTFile:
    """Main ADT file reader"""
    def __init__(self, filename: str):
        self.filename = filename
        self.version = self._detect_version()
        
        # Root chunks
        self.mhdr_flags: MHDRFlags = MHDRFlags(0)
        self.mcin_entries: List[MCINEntry] = []
        self.chunks: Dict[str, object] = {}
        
        # MCNK chunks
        self.mcnks: List[MCNKChunk] = []
        
        # Parse the file
        self._parse_file()  # Changed to match the method name below

    def _detect_version(self) -> int:
        """Detect ADT version from filename or content"""
        # Simple version detection based on filename
        if '_obj0' in self.filename or '_obj1' in self.filename:
            return 8  # Cataclysm+
        return 0  # Pre-Cata

def _read_chunk_header(self, f: BinaryIO) -> Optional[ChunkHeader]:
    """Read next chunk header"""
    try:
        header_data = f.read(8)
        if len(header_data) < 8:
            return None
            
        # Reverse the magic bytes to handle REVM -> MVER etc.
        magic = header_data[:4][::-1].decode('ascii')
        size = struct.unpack('<I', header_data[4:8])[0]
        offset = f.tell()
        return ChunkHeader(magic, size, offset)
    except Exception as e:
        print(f"Error reading chunk header at position {f.tell()}: {e}")
        return None

def _parse_file(self):  # Changed to _parse_file to match init
    """Parse ADT file"""
    try:
        with open(self.filename, 'rb') as f:
            # Debug info
            file_size = os.path.getsize(self.filename)
            print(f"Reading file: {self.filename} (size: {file_size} bytes)")
            
            # Read MVER chunk
            mver_header = self._read_chunk_header(f)
            if not mver_header or mver_header.magic != 'MVER':
                raise ValueError(f"Expected MVER, got {mver_header.magic if mver_header else 'None'}")
            
            # Read version
            version = struct.unpack('<I', f.read(4))[0]
            print(f"ADT Version: {version}")

            # Read MHDR chunk
            mhdr_header = self._read_chunk_header(f)
            if not mhdr_header or mhdr_header.magic != 'MHDR':
                raise ValueError(f"Expected MHDR, got {mhdr_header.magic if mhdr_header else 'None'}")
            
            # Parse MHDR flags
            self.mhdr_flags = MHDRFlags(struct.unpack('<I', f.read(4))[0])
            print(f"MHDR flags: {self.mhdr_flags}")
            
            # Skip rest of MHDR
            f.seek(f.tell() + mhdr_header.size - 4)  # -4 because we read the flags
            
            # Parse remaining chunks
            while True:
                chunk_header = self._read_chunk_header(f)
                if not chunk_header:
                    break
                    
                print(f"Found chunk: {chunk_header.magic} (size: {chunk_header.size})")
                chunk_data = f.read(chunk_header.size)
                
                # Parse chunk based on magic
                if chunk_header.magic == 'MCIN':
                    self._parse_mcin(chunk_data)
                elif chunk_header.magic == 'MTEX':
                    self.chunks['MTEX'] = MTEXChunk(chunk_data)
                elif chunk_header.magic == 'MMDX':
                    self.chunks['MMDX'] = MMDXChunk(chunk_data)
                elif chunk_header.magic == 'MMID':
                    self.chunks['MMID'] = MMIDChunk(chunk_data, self.chunks.get('MMDX'))
                elif chunk_header.magic == 'MWMO':
                    self.chunks['MWMO'] = MWMOChunk(chunk_data)
                elif chunk_header.magic == 'MWID':
                    self.chunks['MWID'] = MWIDChunk(chunk_data, self.chunks.get('MWMO'))
                elif chunk_header.magic == 'MDDF':
                    self.chunks['MDDF'] = MDDFChunk(chunk_data)
                elif chunk_header.magic == 'MODF':
                    self.chunks['MODF'] = MODFChunk(chunk_data)
                elif chunk_header.magic == 'MFBO' and self.mhdr_flags & MHDRFlags.mhdr_MFBO:
                    self.chunks['MFBO'] = MFBOChunk(chunk_data)
                elif chunk_header.magic == 'MTXF' and self.mhdr_flags & MHDRFlags.mhdr_use_tex_flags:
                    self.chunks['MTXF'] = MTXFChunk(chunk_data)
                elif chunk_header.magic == 'MH2O' and self.version >= 8:
                    self.chunks['MH2O'] = MH2OChunk(chunk_data)
                elif chunk_header.magic == 'MCLQ' and self.version < 8:
                    self.chunks['MCLQ'] = MCLQLiquid(chunk_data)
                elif chunk_header.magic == 'MCNK':
                    mcnk = MCNKChunk(chunk_data)
                    self.mcnks.append(mcnk)
                
                # Ensure we're aligned to 4 bytes
                if chunk_header.size % 4 != 0:
                    padding = 4 - (chunk_header.size % 4)
                    f.seek(f.tell() + padding)
                    
    except FileNotFoundError:
        raise ValueError(f"ADT file not found: {self.filename}")
    except Exception as e:
        raise ValueError(f"Error parsing ADT file: {e}")

    def _parse_mcin(self, data: bytes):
        """Parse MCIN chunk data"""
        entry_size = 16
        num_entries = len(data) // entry_size
        
        for i in range(num_entries):
            offset = i * entry_size
            entry_data = data[offset:offset + entry_size]
            self.mcin_entries.append(MCINEntry.from_bytes(entry_data))

    def get_texture_name(self, index: int) -> Optional[str]:
        """Get texture filename by index"""
        mtex = self.chunks.get('MTEX')
        if mtex:
            return mtex.get_filename(index)
        return None

    def get_m2_name(self, index: int) -> Optional[str]:
        """Get M2 model filename by index"""
        mmdx = self.chunks.get('MMDX')
        if mmdx:
            return mmdx.get_filename(index)
        return None

    def get_wmo_name(self, index: int) -> Optional[str]:
        """Get WMO filename by index"""
        mwmo = self.chunks.get('MWMO')
        if mwmo:
            return mwmo.get_filename(index)
        return None

    def get_mcnk(self, x: int, y: int) -> Optional[MCNKChunk]:
        """Get MCNK chunk by grid position"""
        if 0 <= x < 16 and 0 <= y < 16:
            index = y * 16 + x
            if index < len(self.mcnks):
                return self.mcnks[index]
        return None

    def get_height(self, x: int, y: int) -> float:
        """Get terrain height at grid position"""
        mcnk_x = x // 8
        mcnk_y = y // 8
        local_x = x % 8
        local_y = y % 8
        
        mcnk = self.get_mcnk(mcnk_x, mcnk_y)
        if mcnk:
            heights, _ = mcnk.terrain
            if heights:
                return heights.get_height(local_x, local_y)
        return 0.0

    def get_liquid_height(self, x: int, y: int) -> Optional[float]:
        """Get liquid height at position"""
        if self.version >= 8:
            mh2o = self.chunks.get('MH2O')
            if mh2o:
                return mh2o.get_height(x, y)
        else:
            mclq = self.chunks.get('MCLQ')
            if mclq and isinstance(mclq, MCLQLiquid):
                return mclq.get_height(x, y)
        return None

def example_usage():
    """Example usage of ADT reader"""
    # Example ADT file path
    adt_path = "example.adt"
    
    try:
        adt = ADTFile(adt_path)
        
        print(f"ADT File: {adt.filename}")
        print(f"Version: {'Cataclysm+' if adt.version >= 8 else 'Pre-Cataclysm'}")
        print(f"Flags: {adt.mhdr_flags}")
        
        print("\nChunk Summary:")
        for chunk_name in adt.chunks:
            print(f"  {chunk_name} present")
        
        print(f"\nMCNK chunks: {len(adt.mcnks)}")
        
        # Example texture lookup
        print("\nTextures:")
        mtex = adt.chunks.get('MTEX')
        if mtex:
            for i, name in enumerate(mtex.filenames[:5]):
                print(f"  [{i}] {name}")
        
        # Example model placement
        print("\nM2 Placements:")
        mddf = adt.chunks.get('MDDF')
        if mddf:
            for i, placement in enumerate(mddf.placements[:5]):
                model_name = adt.get_m2_name(placement.name_id)
                print(f"  [{i}] {model_name} at ({placement.position.x}, {placement.position.y}, {placement.position.z})")
        
        # Example WMO placement
        print("\nWMO Placements:")
        modf = adt.chunks.get('MODF')
        if modf:
            for i, placement in enumerate(modf.placements[:5]):
                wmo_name = adt.get_wmo_name(placement.name_id)
                print(f"  [{i}] {wmo_name} at ({placement.position.x}, {placement.position.y}, {placement.position.z})")
        
        # Example terrain height lookup
        print("\nTerrain Heights (sample):")
        for y in range(0, 64, 32):
            for x in range(0, 64, 32):
                height = adt.get_height(x, y)
                print(f"  ({x}, {y}): {height:.2f}")
        
        # Example liquid height lookup
        print("\nLiquid Heights (sample):")
        for y in range(0, 64, 32):
            for x in range(0, 64, 32):
                height = adt.get_liquid_height(x, y)
                if height is not None:
                    print(f"  ({x}, {y}): {height:.2f}")

    except FileNotFoundError:
        print(f"Error: ADT file {adt_path} not found")
    except ValueError as e:
        print(f"Error parsing ADT file: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    example_usage()
