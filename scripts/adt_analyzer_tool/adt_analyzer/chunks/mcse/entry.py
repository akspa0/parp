from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass
class McseEntry:
    """MCSE (Sound Emitter) entry.
    
    Each entry is 28 bytes and defines a sound emitter in the map chunk.
    """
    sound_id: int       # Sound effect ID
    sound_type: int     # Type of sound
    position: Tuple[float, float, float]  # XYZ coordinates
    min_distance: float  # Minimum audible distance
    max_distance: float  # Maximum audible distance

    def to_dict(self) -> Dict:
        """Convert entry to dictionary."""
        return {
            'sound_id': self.sound_id,
            'sound_type': self.sound_type,
            'position': self.position,
            'min_distance': self.min_distance,
            'max_distance': self.max_distance
        }

    @classmethod
    def from_bytes(cls, data: bytes) -> 'McseEntry':
        """Create entry from bytes."""
        import struct
        sound_id, sound_type, pos_x, pos_y, pos_z, min_dist, max_dist = struct.unpack(
            '<2I3f2f', data
        )
        return cls(
            sound_id=sound_id,
            sound_type=sound_type,
            position=(pos_x, pos_y, pos_z),
            min_distance=min_dist,
            max_distance=max_dist
        )