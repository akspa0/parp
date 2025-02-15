from dataclasses import dataclass
from typing import Dict

@dataclass
class MclyEntry:
    """MCLY (Texture Layer) entry.
    
    Each entry is 16 bytes and contains information about a texture layer.
    """
    texture_id: int  # Index into MTEX array
    flags: int      # Layer flags
    mcal_offset: int  # Offset into MCAL chunk for alpha map
    effect_id: int  # Special effects ID

    def to_dict(self) -> Dict:
        """Convert entry to dictionary."""
        return {
            'texture_id': self.texture_id,
            'flags': self.flags,
            'mcal_offset': self.mcal_offset,
            'effect_id': self.effect_id
        }