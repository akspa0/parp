# adt_analyzer/parser/file_parser.py
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

class AdtFileParser:
    """Main parser for ADT files.
    
    Handles:
    - Chunk order and dependencies
    - Name orientation detection
    - Data validation and linking
    """
    
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
        while offset < len(data):
            header = self._read_chunk_header(data, offset)
            if not header:
                break
                
            chunk_name = header['name']
            chunk_size = header['size']
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
                        chunk = MtexChunk(header=None, data=chunk_data)
                        self.chunks['textures'] = chunk.parse()
                    elif chunk_name == b'MMDX':
                        chunk = MmdxChunk(header=None, data=chunk_data)
                        self.chunks['m2_models'] = chunk.parse()
                    elif chunk_name == b'MMID':
                        chunk = MmidChunk(header=None, data=chunk_data)
                        self.chunks['m2_indices'] = chunk.parse()
                    elif chunk_name == b'MWMO':
                        chunk = MwmoChunk(header=None, data=chunk_data)
                        self.chunks['wmo_models'] = chunk.parse()
                    elif chunk_name == b'MWID':
                        chunk = MwidChunk(header=None, data=chunk_data)
                        self.chunks['wmo_indices'] = chunk.parse()
                    else:
                        break
                        
                elif phase == ChunkProcessingPhase.PLACEMENTS:
                    if chunk_name == b'MDDF':
                        chunk = MddfChunk(header=None, data=chunk_data)
                        self.chunks['m2_placements'] = chunk.parse()
                    elif chunk_name == b'MODF':
                        chunk = ModfChunk(header=None, data=chunk_data)
                        self.chunks['wmo_placements'] = chunk.parse()
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
            # Combine M2 model data
            if 'm2_models' in self.chunks and 'm2_indices' in self.chunks:
                m2_data = self.chunks['m2_models']
                index_data = self.chunks['m2_indices']
                
                models = []
                mmdx_models = {m['offset']: m['name'] for m in m2_data['models']}
                
                for entry in index_data['offsets']:
                    offset = entry['offset']
                    models.append({
                        'index': entry['index'],
                        'offset': offset,
                        'name': mmdx_models.get(offset, f"<invalid offset: {offset}>")
                    })
                    
                self.chunks['models'] = models
            
            # Combine WMO data
            if 'wmo_models' in self.chunks and 'wmo_indices' in self.chunks:
                wmo_data = self.chunks['wmo_models']
                index_data = self.chunks['wmo_indices']
                
                wmos = []
                mwmo_entries = {w['offset']: w['name'] for w in wmo_data['wmos']}
                
                for entry in index_data['offsets']:
                    offset = entry['offset']
                    wmos.append({
                        'index': entry['index'],
                        'offset': offset,
                        'name': mwmo_entries.get(offset, f"<invalid offset: {offset}>")
                    })
                    
                self.chunks['wmos'] = wmos
                
        except Exception as e:
            error_msg = f"Failed to process model references: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
    
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
            
            return {
                'file_path': str(file_path),
                'chunks': self.chunks,
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

if __name__ == "__main__":
    # Example usage
    parser = AdtFileParser()
    result = parser.parse_file(Path("test.adt"))
    
    if result['errors']:
        print("\nErrors encountered:")
        for error in result['errors']:
            print(f"- {error}")
    
    if 'version' in result['chunks']:
        print(f"\nADT Version: {result['chunks']['version']['version']}")
        
    if 'models' in result['chunks']:
        print("\nM2 Models:")
        for model in result['chunks']['models'][:5]:  # First 5 for brevity
            print(f"- {model['name']}")
            
    if 'terrain_chunks' in result['chunks']:
        print(f"\nTerrain Chunks: {len(result['chunks']['terrain_chunks'])}")
