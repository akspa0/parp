# adt_analyzer/chunks/modf/parser.py
from typing import Dict, Any, List
import logging
from ..base import BaseChunk, ChunkParsingError
from .entry import ModfEntry

logger = logging.getLogger(__name__)

class ModfChunk(BaseChunk):
    """MODF (WMO Placement) chunk parser.
    
    Contains information about WMO placement in the map.
    Each entry is 64 bytes.
    """
    
    ENTRY_SIZE = 64
    
    def parse(self) -> Dict[str, Any]:
        """Parse MODF chunk data."""
        if len(self.data) % self.ENTRY_SIZE != 0:
            raise ChunkParsingError(
                f"MODF chunk size {len(self.data)} not divisible by {self.ENTRY_SIZE}"
            )
        
        count = len(self.data) // self.ENTRY_SIZE
        entries = []
        
        for i in range(count):
            try:
                entry_data = self.data[i*self.ENTRY_SIZE:(i+1)*self.ENTRY_SIZE]
                entry = ModfEntry.from_bytes(entry_data)
                entries.append({
                    'index': i,
                    **entry.to_dict()
                })
                
            except Exception as e:
                logger.error(f"Failed to parse MODF entry {i}: {e}")
                entries.append({
                    'index': i,
                    'error': str(e)
                })
        
        return {
            'entries': entries,
            'count': count,
            'valid_entries': len([e for e in entries if 'error' not in e])
        }

# Example utility to combine model and placement data
def enrich_model_placement(
    mddf_data: Dict[str, Any],
    model_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Combine MDDF placement data with model names from MMDX/MMID."""
    enriched = []
    
    for entry in mddf_data['entries']:
        if 'error' in entry:
            enriched.append(entry)
            continue
            
        model_info = model_data[entry['mmid_entry']] if entry['mmid_entry'] < len(model_data) else None
        
        enriched.append({
            **entry,
            'model_name': model_info['name'] if model_info else '<invalid model reference>'
        })
    
    return enriched

# Similar function for WMO placements
def enrich_wmo_placement(
    modf_data: Dict[str, Any],
    wmo_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Combine MODF placement data with WMO names from MWMO/MWID."""
    enriched = []
    
    for entry in modf_data['entries']:
        if 'error' in entry:
            enriched.append(entry)
            continue
            
        wmo_info = wmo_data[entry['mwid_entry']] if entry['mwid_entry'] < len(wmo_data) else None
        
        enriched.append({
            **entry,
            'wmo_name': wmo_info['name'] if wmo_info else '<invalid WMO reference>'
        })
    
    return enriched
