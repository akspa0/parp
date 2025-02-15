"""ADT file parser."""
from typing import Dict, Any, Optional, BinaryIO, List
import logging
import struct
from pathlib import Path

from ..chunks.base import BaseChunk, ChunkParsingError
from ..chunks.mver.parser import MverChunk
from ..chunks.mhdr.parser import MhdrChunk
from ..chunks.mcin.parser import McinChunk
from ..chunks.mtex.parser import MtexChunk
from ..chunks.mmdx.parser import MmdxChunk
from ..chunks.mmid.parser import MmidChunk
from ..chunks.mwmo.parser import MwmoChunk
from ..chunks.mwid.parser import MwidChunk
from ..chunks.mddf.parser import MddfChunk
from ..chunks.modf.parser import ModfChunk
from ..chunks.mcnk.parser import McnkChunk
from .constants import ChunkProcessingPhase

logger = logging.getLogger(__name__)

def read_c_string_list(data: bytes) -> List[str]:
    """Read a list of null-terminated strings."""
    strings = data.split(b'\0')
    return [s.decode('utf-8', 'replace') for s in strings if s]

def load_name_list(base_block: bytes, offsets: List[int]) -> List[str]:
    """Load a list of names from a data block using offsets."""
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

class AdtFileParser:
    """Main parser for ADT files."""
    
    def __init__(self):
        self.chunks: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.reverse_names = False
        
    def _read_chunk_header(self, data: bytes, offset: int) -> Optional[Dict[str, Any]]:
        """Read a chunk header, handling name orientation."""
        try:
            if offset + 8 > len(data):
                return None
                
            chunk_name = data[offset:offset+4]
            if self.reverse_names:
                chunk_name = chunk_name[::-1]
                
            chunk_size = struct.unpack('<I', data[offset+4:offset+8])[0]
            
            return {
                'name': chunk_name,
                'size': chunk_size,
                'offset': offset
            }
        except Exception as e:
            self.errors.append(f"Failed to read chunk header at offset {offset}: {e}")
            return None
    
    def _detect_name_orientation(self, data: bytes) -> bool:
        """Detect whether chunk names need to be reversed."""
        # Try first chunk both ways
        normal_name = data[0:4]
        reversed_name = normal_name[::-1]
        
        # MVER should be first chunk
        if normal_name == b'MVER':
            return False
        elif reversed_name == b'MVER':
            return True
            
        # If we can't determine from MVER, look for other known chunks
        known_chunks = [b'MHDR', b'MCIN', b'MTEX']
        reversed_known = [name[::-1] for name in known_chunks]
        
        # Check first 3 chunks
        offset = 0
        for _ in range(3):
            if offset + 8 > len(data):
                break
                
            chunk_name = data[offset:offset+4]
            chunk_size = struct.unpack('<I', data[offset+4:offset+8])[0]
            
            if chunk_name in known_chunks:
                return False
            elif chunk_name in reversed_known:
                return True
                
            offset += 8 + chunk_size
        
        # Default to normal orientation if we can't determine
        logger.warning("Could not definitively determine chunk name orientation")
        return False
    
    def _process_phase(self, 
                      data: bytes,
                      phase: ChunkProcessingPhase,
                      offset: int = 0) -> int:
        """Process chunks for a specific phase, returns next offset."""
        size = len(data)
        while offset < size:
            header = self._read_chunk_header(data, offset)
            if not header:
                break
                
            chunk_name = header['name']
            chunk_size = header['size']
            
            # Validate chunk size
            if offset + 8 + chunk_size > size:
                logger.error(f"Chunk {chunk_name} extends beyond file size. Corrupt file?")
                break
                
            chunk_data = data[offset+8:offset+8+chunk_size]
            
            try:
                if phase == ChunkProcessingPhase.INITIAL:
                    if chunk_name == b'MVER':
                        chunk = MverChunk(header=None, data=chunk_data)
                        self.chunks['version'] = chunk.parse()
                    elif chunk_name == b'MHDR':
                        chunk = MhdrChunk(header=None, data=chunk_data)
                        self.chunks['header'] = chunk.parse()
                    else:
                        break  # End of initial phase
                        
                elif phase == ChunkProcessingPhase.INDICES:
                    if chunk_name == b'MCIN':
                        chunk = McinChunk(header=None, data=chunk_data)
                        self.chunks['chunk_indices'] = chunk.parse()
                    else:
                        break
                        
                elif phase == ChunkProcessingPhase.REFERENCES:
                    if chunk_name == b'MTEX':
                        self.chunks['textures'] = read_c_string_list(chunk_data)
                    elif chunk_name == b'MMDX':
                        self.chunks['mmdx_block'] = chunk_data
                    elif chunk_name == b'MMID':
                        chunk = MmidChunk(header=None, data=chunk_data)
                        self.chunks['m2_indices'] = chunk.parse()
                    elif chunk_name == b'MWMO':
                        self.chunks['mwmo_block'] = chunk_data
                    elif chunk_name == b'MWID':
                        chunk = MwidChunk(header=None, data=chunk_data)
                        self.chunks['wmo_indices'] = chunk.parse()
                    else:
                        break
                        
                elif phase == ChunkProcessingPhase.PLACEMENTS:
                    if chunk_name == b'MDDF':
                        chunk = MddfChunk(header=None, data=chunk_data)
                        result = chunk.parse()
                        self.chunks['m2_placements'] = result['entries']
                    elif chunk_name == b'MODF':
                        chunk = ModfChunk(header=None, data=chunk_data)
                        result = chunk.parse()
                        self.chunks['wmo_placements'] = result['entries']
                    else:
                        break
                        
                elif phase == ChunkProcessingPhase.TERRAIN:
                    if chunk_name == b'MCNK':
                        # Add to list of MCNK chunks
                        if 'terrain_chunks' not in self.chunks:
                            self.chunks['terrain_chunks'] = []
                            
                        chunk = McnkChunk(header=None, data=chunk_data)
                        self.chunks['terrain_chunks'].append(chunk.parse())
                        
            except Exception as e:
                error_msg = f"Failed to parse {chunk_name} chunk: {e}"
                logger.error(error_msg)
                self.errors.append(error_msg)
            
            offset += 8 + chunk_size
        
        return offset
    
    def _process_model_references(self):
        """Process and validate model references."""
        try:
            # Process M2 model names
            if 'mmdx_block' in self.chunks and 'm2_indices' in self.chunks:
                mmdx_block = self.chunks['mmdx_block']
                mmid_offsets = self.chunks['m2_indices']['offsets']
                m2_names = load_name_list(mmdx_block, mmid_offsets)
                self.chunks['m2_models'] = m2_names
            
            # Process WMO names
            if 'mwmo_block' in self.chunks and 'wmo_indices' in self.chunks:
                mwmo_block = self.chunks['mwmo_block']
                mwid_offsets = self.chunks['wmo_indices']['offsets']
                wmo_names = load_name_list(mwmo_block, mwid_offsets)
                self.chunks['wmo_models'] = wmo_names
            
            # Add model names to placements
            if 'm2_models' in self.chunks and 'm2_placements' in self.chunks:
                m2_names = self.chunks['m2_models']
                for m in self.chunks['m2_placements']:
                    if 'error' in m:
                        continue
                    name_id = m.get('nameId', -1)
                    if isinstance(name_id, int) and 0 <= name_id < len(m2_names):
                        m['model_name'] = m2_names[name_id]
                    else:
                        m['model_name'] = ""
            
            # Add WMO names to placements
            if 'wmo_models' in self.chunks and 'wmo_placements' in self.chunks:
                wmo_names = self.chunks['wmo_models']
                for w in self.chunks['wmo_placements']:
                    if 'error' in w:
                        continue
                    name_id = w.get('nameId', -1)
                    if isinstance(name_id, int) and 0 <= name_id < len(wmo_names):
                        w['wmo_name'] = wmo_names[name_id]
                    else:
                        w['wmo_name'] = ""
                
        except Exception as e:
            error_msg = f"Failed to process model references: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
    
    def _prepare_for_json(self, data: Any) -> Any:
        """Convert data to JSON-serializable format."""
        if isinstance(data, bytes):
            return data.hex()  # Convert bytes to hex string
        elif isinstance(data, dict):
            return {k: self._prepare_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._prepare_for_json(item) for item in data]
        elif isinstance(data, tuple):
            return [self._prepare_for_json(item) for item in data]
        return data
    
    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse an ADT file and return structured data."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Detect chunk name orientation
            self.reverse_names = self._detect_name_orientation(data)
            logger.debug(f"Using {'reversed' if self.reverse_names else 'normal'} chunk names")
            
            # Process each phase
            offset = 0
            for phase in ChunkProcessingPhase:
                offset = self._process_phase(data, phase, offset)
            
            # Process model references
            self._process_model_references()
            
            # Clean up temporary data
            if 'mmdx_block' in self.chunks:
                del self.chunks['mmdx_block']
            if 'mwmo_block' in self.chunks:
                del self.chunks['mwmo_block']
            
            # Convert data to JSON-serializable format
            json_chunks = self._prepare_for_json(self.chunks)
            
            return {
                'file_path': str(file_path),
                'chunks': json_chunks,
                'errors': self.errors
            }
            
        except Exception as e:
            error_msg = f"Failed to parse file {file_path}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return {
                'file_path': str(file_path),
                'errors': self.errors
            }
