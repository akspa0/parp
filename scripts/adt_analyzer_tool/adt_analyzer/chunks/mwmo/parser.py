# adt_analyzer/chunks/mwmo/parser.py
from typing import Dict, Any, List
import logging
from ..base import BaseChunk, ChunkParsingError

logger = logging.getLogger(__name__)

class MwmoChunk(BaseChunk):
    """MWMO (WMO Definitions) parser.
    
    Contains a series of null-terminated strings for WMO model filenames.
    Used in conjunction with MWID chunk which provides offsets into this data.
    Similar to MMDX but for World Map Objects instead of M2 models.
    """
    
    def _extract_wmo_names(self, data: bytes) -> List[Dict[str, Any]]:
        """Extract WMO names and their positions in the data block."""
        wmos = []
        current_offset = 0
        current_name = bytearray()
        
        for byte in data:
            if byte == 0:  # Null terminator
                if current_name:
                    try:
                        name = current_name.decode('utf-8')
                        wmos.append({
                            'name': name,
                            'offset': current_offset,
                            'length': len(current_name)
                        })
                        current_name = bytearray()
                    except UnicodeDecodeError as e:
                        logger.warning(
                            f"Failed to decode WMO name at offset {current_offset}: {e}"
                        )
                        current_name = bytearray()
                current_offset += 1  # Include null terminator
            else:
                current_name.append(byte)
                current_offset += 1
        
        # Handle any remaining data
        if current_name:
            try:
                name = current_name.decode('utf-8')
                wmos.append({
                    'name': name,
                    'offset': current_offset - len(current_name),
                    'length': len(current_name)
                })
            except UnicodeDecodeError as e:
                logger.warning(f"Failed to decode final WMO name: {e}")
        
        return wmos
    
    def parse(self) -> Dict[str, Any]:
        """Parse MWMO chunk data."""
        try:
            wmos = self._extract_wmo_names(self.data)
            
            # Basic validation
            for wmo in wmos:
                name = wmo['name']
                if not name.lower().endswith('.wmo'):
                    logger.warning(f"Unusual WMO extension: {name}")
                if wmo['offset'] + wmo['length'] > len(self.data):
                    logger.error(f"WMO entry extends beyond chunk data: {name}")
                
                # Additional WMO-specific validation
                if '\\' in name:  # WMOs typically use forward slashes
                    fixed_name = name.replace('\\', '/')
                    logger.warning(f"Converting backslashes to forward slashes: {name} -> {fixed_name}")
                    wmo['name'] = fixed_name
            
            return {
                'wmos': wmos,
                'count': len(wmos),
                'data_size': len(self.data)
            }
            
        except Exception as e:
            raise ChunkParsingError(f"Failed to parse MWMO data: {e}")
