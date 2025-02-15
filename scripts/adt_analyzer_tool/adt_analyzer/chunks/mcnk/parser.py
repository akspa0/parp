"""MCNK (Map Chunk) parser."""
from typing import Dict, Any, Optional, Tuple
import struct
import logging
from ..base import BaseChunk, ChunkParsingError
from .header import McnkHeader, MCNKFlags

logger = logging.getLogger(__name__)

class McnkChunk(BaseChunk):
    """MCNK (Map Chunk) parser.
    
    Contains terrain information and references to models/textures.
    Structure:
    1. Header (128 bytes)
    2. Mandatory subchunks:
       - MCVT (heights) - always first after header
       - MCNR (normals) - always after MCVT
       - MCLY (texture layers) - at offset_mcly
    3. Optional subchunks based on flags:
       - MCRF (doodad refs) - if HAS_DOODAD_REFS
       - MCSH (shadows) - if HAS_MCSH
       - MCCV (vertex colors) - if HAS_MCCV
       - MCLV (lighting) - if HAS_MCLV
       - MCAL (alpha maps) - if offset_mcal present
    """
    
    HEADER_SIZE = 128
    
    def parse(self) -> Dict[str, Any]:
        """Parse MCNK chunk data."""
        if len(self.data) < self.HEADER_SIZE:
            raise ChunkParsingError(
                f"MCNK chunk too small: {len(self.data)} < {self.HEADER_SIZE}"
            )
        
        # Parse header
        header = McnkHeader.from_bytes(self.data[:self.HEADER_SIZE])
        result = {
            'header': {
                'flags': header.flags,
                'position': (header.idx_x, header.idx_y),
                'area_id': header.area_id,
                'holes': header.holes,
                'liquid_level': header.liquid_level
            },
            'errors': []  # Track subchunk errors
        }
        
        # Parse mandatory subchunks
        self._parse_mandatory_subchunks(header, result)
        
        # Parse optional subchunks
        self._parse_optional_subchunks(header, result)
        
        return result

    def _parse_mandatory_subchunks(self, header: McnkHeader, result: Dict[str, Any]):
        """Parse mandatory subchunks (MCVT, MCNR, MCLY)."""
        # Parse MCVT (heights) - always first after header
        mcvt_data = self._get_chunk_data(self.HEADER_SIZE)
        if mcvt_data:
            try:
                from ..mcvt import McvtChunk
                mcvt = McvtChunk(header=self.header, data=mcvt_data)
                mcvt_result = mcvt.parse()
                result['heights'] = mcvt_result['heights']
            except Exception as e:
                error_msg = f"Failed to parse MCVT chunk: {e}"
                logger.error(error_msg)
                result['errors'].append(error_msg)
                result['heights'] = [0.0] * 145  # Default heights
        
        # Parse MCNR (normals) - always after MCVT
        if mcvt_data:
            mcnr_offset = self.HEADER_SIZE + len(mcvt_data) + 8  # Add MCVT chunk header
        else:
            mcnr_offset = self.HEADER_SIZE + 580 + 8  # Default MCVT size
            
        mcnr_data = self._get_chunk_data(mcnr_offset)
        if mcnr_data:
            try:
                from ..mcnr import McnrChunk
                mcnr = McnrChunk(header=self.header, data=mcnr_data)
                mcnr_result = mcnr.parse()
                result['normals'] = mcnr_result['normals']
            except Exception as e:
                error_msg = f"Failed to parse MCNR chunk: {e}"
                logger.error(error_msg)
                result['errors'].append(error_msg)
                result['normals'] = [(0.0, 0.0, 1.0)] * 145  # Default normals
        
        # Parse MCLY (texture layers)
        if header.offset_mcly:
            mcly_data = self._get_chunk_data(header.offset_mcly)
            if mcly_data:
                try:
                    from ..mcly import MclyChunk
                    mcly = MclyChunk(header=self.header, data=mcly_data)
                    mcly_result = mcly.parse()
                    result['layers'] = mcly_result['layers']
                    if 'error' in mcly_result:
                        result['errors'].append(mcly_result['error'])
                except Exception as e:
                    error_msg = f"Failed to parse MCLY chunk: {e}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
                    result['layers'] = []  # Empty layer list

    def _parse_optional_subchunks(self, header: McnkHeader, result: Dict[str, Any]):
        """Parse optional subchunks based on flags."""
        # Parse MCRF (doodad references)
        if header.flags & MCNKFlags.HAS_DOODAD_REFS and header.offset_mcrf:
            mcrf_data = self._get_chunk_data(header.offset_mcrf)
            if mcrf_data:
                try:
                    from ..mcrf import McrfChunk
                    mcrf = McrfChunk(header=self.header, data=mcrf_data)
                    mcrf_result = mcrf.parse()
                    result['doodad_refs'] = mcrf_result['doodad_refs']
                except Exception as e:
                    error_msg = f"Failed to parse MCRF chunk: {e}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
        
        # Parse MCSH (shadows)
        if header.flags & MCNKFlags.HAS_MCSH and header.offset_mcsh:
            mcsh_data = self._get_chunk_data(header.offset_mcsh)
            if mcsh_data:
                try:
                    from ..mcsh import McshChunk
                    mcsh = McshChunk(header=self.header, data=mcsh_data)
                    mcsh_result = mcsh.parse()
                    result['shadow_map'] = mcsh_result['shadow_map']
                    result['dimensions'] = mcsh_result['dimensions']
                    if not mcsh_result.get('complete', True):
                        result['errors'].append("Incomplete shadow map")
                except Exception as e:
                    error_msg = f"Failed to parse MCSH chunk: {e}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
        
        # Parse MCCV (vertex colors)
        if header.flags & MCNKFlags.HAS_MCCV and header.offset_mccv:
            mccv_data = self._get_chunk_data(header.offset_mccv)
            if mccv_data:
                try:
                    from ..mccv import MccvChunk
                    mccv = MccvChunk(header=self.header, data=mccv_data)
                    mccv_result = mccv.parse()
                    result['vertex_colors'] = mccv_result['colors']
                except Exception as e:
                    error_msg = f"Failed to parse MCCV chunk: {e}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
        
        # Parse MCLV (lighting)
        if header.flags & MCNKFlags.HAS_MCLV and header.offset_mclv:
            mclv_data = self._get_chunk_data(header.offset_mclv)
            if mclv_data:
                try:
                    from ..mclv import MclvChunk
                    mclv = MclvChunk(header=self.header, data=mclv_data)
                    mclv_result = mclv.parse()
                    result['light_values'] = mclv_result['light_values']
                except Exception as e:
                    error_msg = f"Failed to parse MCLV chunk: {e}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
        
        # Parse MCAL (alpha maps)
        if header.offset_mcal:
            mcal_data = self._get_chunk_data(header.offset_mcal)
            if mcal_data:
                try:
                    from ..mcal import McalChunk
                    mcal = McalChunk(header=self.header, data=mcal_data)
                    mcal_result = mcal.parse()
                    result['alpha_maps'] = mcal_result['alpha_map_data']
                except Exception as e:
                    error_msg = f"Failed to parse MCAL chunk: {e}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)

    def _get_chunk_data(self, offset: int, size: Optional[int] = None) -> Optional[bytes]:
        """Get chunk data using stored offset and optional size."""
        if offset >= len(self.data):
            return None
        
        # Read chunk header
        if offset + 8 > len(self.data):
            return None
            
        chunk_name = self.data[offset:offset+4]
        chunk_size = struct.unpack('<I', self.data[offset+4:offset+8])[0]
        
        # Validate chunk size
        if size is not None and chunk_size != size:
            logger.warning(f"Chunk size mismatch at offset {offset}: {chunk_size} != {size}")
        
        # Get chunk data
        data_start = offset + 8
        data_end = data_start + chunk_size
        
        # Handle truncated chunks
        if data_end > len(self.data):
            logger.warning(f"Chunk at offset {offset} extends beyond file size. Truncating.")
            data_end = len(self.data)
            
        return self.data[data_start:data_end]
