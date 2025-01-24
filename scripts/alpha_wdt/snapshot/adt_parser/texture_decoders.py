#!/usr/bin/env python3
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Iterator
import struct
import logging
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class TextureFlag:
    """Texture flags from MTXF chunk"""
    texture_id: int
    flags: int

    @property
    def is_terrain(self) -> bool:
        return bool(self.flags & 0x1)
        
    @property
    def is_hole(self) -> bool:
        return bool(self.flags & 0x2)
        
    @property
    def is_water(self) -> bool:
        return bool(self.flags & 0x4)
        
    @property
    def has_alpha(self) -> bool:
        return bool(self.flags & 0x8)
        
    @property
    def is_animated(self) -> bool:
        return bool(self.flags & 0x10)

@dataclass
class TextureLayer:
    """MCLY texture layer information"""
    texture_id: int
    flags: int
    offset_mcal: int
    effect_id: int
    blend_mode: int

    @property
    def is_compressed(self) -> bool:
        return bool(self.flags & 0x200)

    @property
    def has_alpha_map(self) -> bool:
        return self.offset_mcal != 0

    @classmethod
    def from_bytes(cls, data: bytes) -> 'TextureLayer':
        if len(data) < 16:
            raise ValueError("Texture layer data too short")
        texture_id, flags, offset_mcal, effect_id = struct.unpack('<4I', data[:16])
        blend_mode = (flags >> 24) & 0x7
        return cls(texture_id, flags, offset_mcal, effect_id, blend_mode)

@dataclass
class TextureDefinition:
    """Complete texture definition combining MTEX and MTXF data"""
    filename: str
    flags: TextureFlag
    texture_id: int
    layers: List[TextureLayer]

    @property
    def base_name(self) -> str:
        """Get base filename without path"""
        return Path(self.filename).name

    @property
    def extension(self) -> str:
        """Get file extension"""
        return Path(self.filename).suffix

    @property
    def is_tileable(self) -> bool:
        """Check if texture is marked as tileable"""
        return "tileset" in self.filename.lower()

class TextureDecoder:
    """Decoder for texture-related chunks (MTEX, MTXF, MCLY)"""
    
    @staticmethod
    def decode_mtex(data: bytes) -> List[str]:
        """Decode MTEX chunk containing null-terminated texture filenames"""
        try:
            textures = []
            current = bytearray()
            
            for byte in data:
                if byte == 0:  # Null terminator
                    if current:  # Only add if we have characters
                        textures.append(current.decode('utf-8'))
                        current = bytearray()
                else:
                    current.append(byte)
            
            # Add final texture if it doesn't end with null
            if current:
                textures.append(current.decode('utf-8'))
                
            return textures
            
        except Exception as e:
            logger.error(f"Error decoding MTEX chunk: {e}")
            return []

    @staticmethod
    def decode_mtxf(data: bytes) -> List[TextureFlag]:
        """Decode MTXF chunk containing texture flags"""
        try:
            flags = []
            # Each entry is 8 bytes (2 integers)
            for i in range(0, len(data), 8):
                if i + 8 <= len(data):
                    texture_id, flag_value = struct.unpack('<II', data[i:i+8])
                    flags.append(TextureFlag(texture_id=texture_id, flags=flag_value))
            return flags
        except Exception as e:
            logger.error(f"Error decoding MTXF chunk: {e}")
            return []

    @staticmethod
    def decode_mcly(data: bytes) -> List[TextureLayer]:
        """Decode MCLY chunk containing layer information"""
        try:
            layers = []
            # Each layer entry is 16 bytes
            for i in range(0, len(data), 16):
                if i + 16 <= len(data):
                    layer = TextureLayer.from_bytes(data[i:i+16])
                    layers.append(layer)
            return layers
        except Exception as e:
            logger.error(f"Error decoding MCLY chunk: {e}")
            return []

class TextureManager:
    """Manages texture definitions and provides lookup capabilities"""
    
    def __init__(self):
        self.textures: Dict[int, TextureDefinition] = {}
        self.name_to_id: Dict[str, int] = {}
        self.layer_map: Dict[int, List[TextureLayer]] = defaultdict(list)

    def load_from_chunks(self, mtex_data: bytes, mtxf_data: Optional[bytes] = None, mcly_data: Optional[bytes] = None) -> None:
        """Load texture definitions from MTEX and optional MTXF/MCLY chunk data"""
        # Decode filenames
        filenames = TextureDecoder.decode_mtex(mtex_data)
        
        # Decode flags if available
        flags = TextureDecoder.decode_mtxf(mtxf_data) if mtxf_data else []
        flags_dict = {flag.texture_id: flag for flag in flags}
        
        # Decode layers if available
        layers = TextureDecoder.decode_mcly(mcly_data) if mcly_data else []
        
        # Create texture definitions
        for idx, filename in enumerate(filenames):
            texture_id = idx
            flag = flags_dict.get(texture_id, TextureFlag(texture_id=texture_id, flags=0))
            
            # Find layers that reference this texture
            texture_layers = [layer for layer in layers if layer.texture_id == texture_id]
            
            texture_def = TextureDefinition(
                filename=filename,
                flags=flag,
                texture_id=texture_id,
                layers=texture_layers
            )
            
            self.textures[texture_id] = texture_def
            self.name_to_id[filename] = texture_id
            
            # Store layer mapping
            if texture_layers:
                self.layer_map[texture_id].extend(texture_layers)

    def get_texture_by_id(self, texture_id: int) -> Optional[TextureDefinition]:
        """Get texture definition by ID"""
        return self.textures.get(texture_id)

    def get_texture_by_name(self, filename: str) -> Optional[TextureDefinition]:
        """Get texture definition by filename"""
        texture_id = self.name_to_id.get(filename)
        if texture_id is not None:
            return self.textures.get(texture_id)
        return None

    def get_all_textures(self) -> List[TextureDefinition]:
        """Get all texture definitions"""
        return list(self.textures.values())

    def get_textures_by_type(self, 
                            terrain: bool = False,
                            water: bool = False,
                            animated: bool = False,
                            with_alpha: bool = False) -> List[TextureDefinition]:
        """Get textures filtered by type"""
        result = []
        for texture in self.textures.values():
            if terrain and texture.flags.is_terrain:
                result.append(texture)
            elif water and texture.flags.is_water:
                result.append(texture)
            elif animated and texture.flags.is_animated:
                result.append(texture)
            elif with_alpha and texture.flags.has_alpha:
                result.append(texture)
        return result

    def get_layer_textures(self, chunk_id: int) -> List[TextureDefinition]:
        """Get textures used in specific chunk's layers"""
        layers = self.layer_map.get(chunk_id, [])
        return [self.textures[layer.texture_id] for layer in layers 
                if layer.texture_id in self.textures]

    def analyze_texture_usage(self) -> Dict[str, int]:
        """Analyze texture types and return counts"""
        stats = {
            'total': len(self.textures),
            'terrain': 0,
            'water': 0,
            'holes': 0,
            'animated': 0,
            'with_alpha': 0,
            'tileable': 0,
            'unique_paths': len(set(tex.filename for tex in self.textures.values())),
            'layers': sum(len(tex.layers) for tex in self.textures.values())
        }
        
        for texture in self.textures.values():
            if texture.flags.is_terrain:
                stats['terrain'] += 1
            if texture.flags.is_water:
                stats['water'] += 1
            if texture.flags.is_hole:
                stats['holes'] += 1
            if texture.flags.is_animated:
                stats['animated'] += 1
            if texture.flags.has_alpha:
                stats['with_alpha'] += 1
            if texture.is_tileable:
                stats['tileable'] += 1
                
        return stats

    def export_texture_list(self, output_path: Path) -> None:
        """Export list of texture references to file"""
        with open(output_path, 'w') as f:
            f.write("Texture References:\n")
            f.write("==================\n\n")
            
            for texture in sorted(self.textures.values(), key=lambda x: x.filename):
                f.write(f"ID: {texture.texture_id}\n")
                f.write(f"Filename: {texture.filename}\n")
                f.write(f"Flags: terrain={texture.flags.is_terrain}, "
                       f"water={texture.flags.is_water}, "
                       f"animated={texture.flags.is_animated}, "
                       f"alpha={texture.flags.has_alpha}\n")
                
                if texture.layers:
                    f.write("Layers:\n")
                    for layer in texture.layers:
                        f.write(f"  - Blend Mode: {layer.blend_mode}\n")
                        f.write(f"  - Has Alpha Map: {layer.has_alpha_map}\n")
                        f.write(f"  - Is Compressed: {layer.is_compressed}\n")
                
                f.write("\n")

def example_usage():
    # Example texture chunk data
    mtex_data = (
        b'tileset/terrain/path.blp\0'
        b'water/ocean.blp\0'
        b'tileset/rocks/stone.blp\0'
    )
    
    # Example flags data (terrain, water, terrain with alpha)
    mtxf_data = struct.pack('<IIIIII', 
        0, 0x1,    # First texture: terrain
        1, 0x4,    # Second texture: water
        2, 0x9     # Third texture: terrain with alpha
    )
    
    # Example layer data
    mcly_data = struct.pack('<IIII', 
        0,      # texture_id
        0x200,  # flags (compressed)
        64,     # alpha map offset
        0       # effect_id
    )
    
    # Create texture manager
    manager = TextureManager()
    manager.load_from_chunks(mtex_data, mtxf_data, mcly_data)
    
    # Demonstrate usage
    print("\nAll textures:")
    for texture in manager.get_all_textures():
        print(f"\nID: {texture.texture_id}")
        print(f"Name: {texture.filename}")
        print(f"Base Name: {texture.base_name}")
        print(f"Is Tileable: {texture.is_tileable}")
        print(f"Flags: Terrain={texture.flags.is_terrain}, "
              f"Water={texture.flags.is_water}, "
              f"Alpha={texture.flags.has_alpha}")
        
        if texture.layers:
            print("Layers:")
            for layer in texture.layers:
                print(f"  Blend Mode: {layer.blend_mode}")
                print(f"  Has Alpha Map: {layer.has_alpha_map}")
    
    # Get statistics
    stats = manager.analyze_texture_usage()
    print("\nTexture statistics:")
    for key, value in stats.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    example_usage()
