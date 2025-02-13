# adt_validator.py
import struct
import logging
from typing import Dict, List, Tuple
from adt_core import MCNKInfo
from chunk_utils import is_chunk_name_reversed, normalize_chunk_name

class NoggitADTValidator:
   REQUIRED_CHUNKS = [b'MVER', b'MHDR', b'MCIN', b'MTEX']
   
   def __init__(self, filepath: str):
       self.filepath = filepath
       self.chunks: Dict[bytes, List[Tuple[int, bytes]]] = {}
       self.mcnk_info: List[MCNKInfo] = []
       self.errors: List[str] = []
       self.chunks_reversed = None
       self.logger = logging.getLogger('NoggitValidator')

   def validate(self) -> bool:
       try:
           with open(self.filepath, 'rb') as f:
               data = f.read()
           
           return all([
               self._parse_and_validate_chunks(data),
               self._validate_mver(),
               self._validate_mhdr(),
               self._validate_mcnk_structure(),
               self._validate_textures(),
               self._validate_model_placements()
           ])
       except Exception as e:
           self.errors.append(f"Critical error: {str(e)}")
           return False

   def _identify_chunk(self, chunk_name: bytes) -> bytes:
       if self.chunks_reversed is None:
           self.chunks_reversed = is_chunk_name_reversed(chunk_name)
       return normalize_chunk_name(chunk_name, self.chunks_reversed)

   def _parse_and_validate_chunks(self, data: bytes) -> bool:
       pos = 0
       while pos + 8 <= len(data):
           raw_chunk_name = data[pos:pos+4]
           chunk_name = self._identify_chunk(raw_chunk_name)
           chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
           
           if pos + 8 + chunk_size > len(data):
               self.errors.append(f"Chunk {chunk_name} extends beyond file size")
               return False
               
           chunk_data = data[pos+8:pos+8+chunk_size]
           
           if chunk_name not in self.chunks:
               self.chunks[chunk_name] = []
           self.chunks[chunk_name].append((pos, chunk_data))
           
           if chunk_name == b'MCNK':
               if not self._parse_mcnk_info(chunk_data, len(self.mcnk_info)):
                   return False
                   
           pos += 8 + chunk_size
       
       return True

   def _parse_mcnk_info(self, data: bytes, index: int) -> bool:
       if len(data) < 128:
           self.errors.append(f"MCNK {index} header too small")
           return False
           
       try:
           flags = struct.unpack('<I', data[0:4])[0]
           ix = struct.unpack('<I', data[4:8])[0]
           iy = struct.unpack('<I', data[8:12])[0]
           n_layers = struct.unpack('<I', data[12:16])[0]
           n_doodads = struct.unpack('<I', data[16:20])[0]
           layer_offset = struct.unpack('<I', data[20:24])[0]
           ref_offset = struct.unpack('<I', data[24:28])[0]
           alpha_offset = struct.unpack('<I', data[28:32])[0]
           shadow_offset = struct.unpack('<I', data[32:36])[0]
           height_offset = struct.unpack('<I', data[36:40])[0]
           holes = struct.unpack('<I', data[48:52])[0]
           
           self.mcnk_info.append(MCNKInfo(
               offset=0,
               size=len(data),
               flags=flags,
               ix=ix,
               iy=iy,
               n_layers=n_layers,
               n_doodads=n_doodads,
               holes=holes,
               layer_offset=layer_offset,
               ref_offset=ref_offset,
               alpha_offset=alpha_offset,
               shadow_offset=shadow_offset,
               height_offset=height_offset
           ))
           return True
           
       except struct.error:
           self.errors.append(f"Failed to parse MCNK {index} header")
           return False

   def _validate_mver(self) -> bool:
       if b'MVER' not in self.chunks or not self.chunks[b'MVER']:
           self.errors.append("Missing MVER chunk")
           return False
           
       version = struct.unpack('<I', self.chunks[b'MVER'][0][1])[0]
       if version != 18:
           self.errors.append(f"Unsupported ADT version: {version}")
           return False
           
       return True

   def _validate_mhdr(self) -> bool:
       if b'MHDR' not in self.chunks or not self.chunks[b'MHDR']:
           self.errors.append("Missing MHDR chunk")
           return False
           
       if len(self.chunks[b'MHDR'][0][1]) < 64:
           self.errors.append("MHDR chunk too small")
           return False
           
       return True

   def _validate_mcnk_structure(self) -> bool:
       if len(self.mcnk_info) != 256:
           self.errors.append(f"Expected 256 MCNK chunks, found {len(self.mcnk_info)}")
           return False
           
       positions = set()
       for info in self.mcnk_info:
           if not (0 <= info.ix < 16 and 0 <= info.iy < 16):
               self.errors.append(f"Invalid MCNK position: {info.ix}, {info.iy}")
               return False
           pos = (info.ix, info.iy)
           if pos in positions:
               self.errors.append(f"Duplicate MCNK position: {pos}")
               return False
           positions.add(pos)
           
       return True

   def _validate_textures(self) -> bool:
       if b'MTEX' not in self.chunks:
           self.errors.append("Missing MTEX chunk")
           return False
           
       mtex_data = self.chunks[b'MTEX'][0][1]
       textures = mtex_data.split(b'\0')
       
       for tex in textures:
           if tex and not tex.lower().endswith(b'.blp'):
               self.errors.append(f"Invalid texture format: {tex}")
               return False
               
       return True

   def _validate_model_placements(self) -> bool:
       valid = True
       if b'MDDF' in self.chunks and b'MMDX' in self.chunks:
           mddf_data = self.chunks[b'MDDF'][0][1]
           mddf_count = len(mddf_data) // 36
           
           for i in range(mddf_count):
               base = i * 36
               scale = struct.unpack('<H', mddf_data[base+32:base+34])[0] / 1024.0
               if scale < 0.01:
                   self.logger.warning(f"Low M2 scale at index {i}: {scale}")

       if b'MODF' in self.chunks and b'MWMO' in self.chunks:
           modf_data = self.chunks[b'MODF'][0][1]
           modf_count = len(modf_data) // 64
           
           for i in range(modf_count):
               base = i * 64
               scale = struct.unpack('<H', modf_data[base+62:base+64])[0] / 1024.0
               if scale < 0.01:
                   self.logger.warning(f"Low WMO scale at index {i}: {scale}")

       return valid

   def get_errors(self) -> List[str]:
       return self.errors