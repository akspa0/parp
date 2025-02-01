"""
JSON encoding for WoW terrain data structures.
Provides custom JSON encoder for serializing terrain data.
"""
import json
import dataclasses
from pathlib import Path
from typing import Any, Dict, List, Union

from ..models import (
    Vector3D, RGBA, CAaBox,
    MCNKFlags, WDTFlags,
    TerrainFile, ADTFile, WDTFile
)

class TerrainEncoder(json.JSONEncoder):
    """Custom JSON encoder for terrain data structures"""
    
    def default(self, obj: Any) -> Any:
        """
        Convert terrain data structures to JSON-serializable types
        
        Args:
            obj: Object to encode
            
        Returns:
            JSON-serializable representation
        """
        # Handle dataclasses
        if dataclasses.is_dataclass(obj):
            result = {}
            for field in dataclasses.fields(obj):
                value = getattr(obj, field.name)
                # Handle special types
                if isinstance(value, (Vector3D, RGBA, CAaBox)):
                    value = dataclasses.asdict(value)
                elif isinstance(value, (MCNKFlags, WDTFlags)):
                    value = value.value  # Get the raw integer value from the Flag enum
                elif isinstance(value, bytes):
                    value = value.hex()
                elif isinstance(value, dict):
                    # Convert tuple keys to strings for JSON
                    if any(isinstance(k, tuple) for k in value.keys()):
                        value = {
                            ','.join(str(x) for x in k) if isinstance(k, tuple) else str(k): v
                            for k, v in value.items()
                        }
                result[field.name] = value
            return result
            
        # Handle Path objects
        elif isinstance(obj, Path):
            return str(obj)
            
        # Handle bytes
        elif isinstance(obj, bytes):
            return obj.hex()
            
        # Handle other types
        return super().default(obj)

def encode_terrain_file(terrain_file: TerrainFile, indent: int = 2) -> str:
    """
    Encode terrain file to JSON string
    
    Args:
        terrain_file: Terrain file to encode
        indent: JSON indentation level
        
    Returns:
        JSON string representation
    """
    return json.dumps(terrain_file, cls=TerrainEncoder, indent=indent)

def save_terrain_file(terrain_file: TerrainFile, output_path: Path) -> None:
    """
    Save terrain file to JSON file
    
    Args:
        terrain_file: Terrain file to save
        output_path: Path to save JSON file
    """
    json_data = encode_terrain_file(terrain_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(json_data)