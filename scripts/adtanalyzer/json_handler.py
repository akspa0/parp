"""
JSON handling for terrain data.
Provides functions for saving and loading terrain data in JSON format.
"""
import os
import json
import dataclasses
from pathlib import Path
from typing import Any, Dict, List, Union
from datetime import datetime

from terrain_structures import (
    Vector3D, Quaternion, RGBA, CAaBox, MCNKFlags, WDTFlags,
    TextureInfo, ModelPlacement, WMOPlacement, MCNKInfo,
    MapTile, ModelReference, TerrainFile, ADTFile, WDTFile
)

class TerrainEncoder(json.JSONEncoder):
    """JSON encoder for terrain data structures"""
    
    def default(self, obj: Any) -> Any:
        if dataclasses.is_dataclass(obj):
            # Convert dataclass to dict
            result = {}
            for field in dataclasses.fields(obj):
                value = getattr(obj, field.name)
                # Handle special types
                if isinstance(value, (Vector3D, Quaternion, RGBA, CAaBox)):
                    value = dataclasses.asdict(value)
                elif isinstance(value, (MCNKFlags, WDTFlags)):
                    value = int(value)
                elif isinstance(value, bytes):
                    value = value.hex()
                elif isinstance(value, dict):
                    # Convert dict with tuple keys to string keys
                    value = {str(k): v for k, v in value.items()}
                result[field.name] = value
            return result
        # Handle other special types
        elif isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, bytes):
            return obj.hex()
        return super().default(obj)

def save_to_json(terrain_file: TerrainFile, output_dir: Path) -> Path:
    """
    Save terrain file data to JSON
    
    Args:
        terrain_file: Parsed terrain file data
        output_dir: Directory to save JSON files
        
    Returns:
        Path to saved JSON file
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename based on original file
    source_path = Path(terrain_file.path)
    json_path = output_dir / f"{source_path.stem}.json"
    
    # Convert to JSON
    json_data = json.dumps(terrain_file, cls=TerrainEncoder, indent=2)
    
    # Save to file
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(json_data)
        
    return json_path

def load_from_json(json_path: Path) -> TerrainFile:
    """
    Load terrain file data from JSON
    
    Args:
        json_path: Path to JSON file
        
    Returns:
        Parsed terrain file data
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Determine file type
    file_type = data.get('file_type', '')
    
    # Convert back to appropriate class
    if file_type == 'adt':
        return _json_to_adt(data)
    elif file_type == 'wdt':
        return _json_to_wdt(data)
    else:
        raise ValueError(f"Unknown file type: {file_type}")

def _json_to_vector3d(data: Dict) -> Vector3D:
    """Convert JSON data to Vector3D"""
    return Vector3D(
        x=float(data['x']),
        y=float(data['y']),
        z=float(data['z'])
    )

def _json_to_aabox(data: Dict) -> CAaBox:
    """Convert JSON data to CAaBox"""
    return CAaBox(
        min=_json_to_vector3d(data['min']),
        max=_json_to_vector3d(data['max'])
    )

def _json_to_model_placement(data: Dict, is_wmo: bool = False) -> Union[ModelPlacement, WMOPlacement]:
    """Convert JSON data to model placement"""
    base_data = {
        'name_id': int(data['name_id']),
        'unique_id': int(data['unique_id']),
        'position': _json_to_vector3d(data['position']),
        'rotation': _json_to_vector3d(data['rotation']),
        'scale': float(data['scale']),
        'flags': int(data['flags'])
    }
    
    if is_wmo:
        return WMOPlacement(
            **base_data,
            doodad_set=int(data['doodad_set']),
            name_set=int(data['name_set']),
            bounding_box=_json_to_aabox(data['bounding_box'])
        )
    return ModelPlacement(**base_data)

def _json_to_mcnk(data: Dict) -> MCNKInfo:
    """Convert JSON data to MCNKInfo"""
    return MCNKInfo(
        flags=MCNKFlags(data['flags']),
        index_x=int(data['index_x']),
        index_y=int(data['index_y']),
        n_layers=int(data['n_layers']),
        n_doodad_refs=int(data['n_doodad_refs']),
        position=_json_to_vector3d(data['position']),
        area_id=int(data['area_id']),
        holes=int(data['holes']),
        layer_flags=int(data['layer_flags']),
        render_flags=int(data['render_flags']),
        has_layer_height=bool(data['has_layer_height']),
        min_elevation=float(data['min_elevation']),
        max_elevation=float(data['max_elevation']),
        liquid_type=int(data['liquid_type']),
        predTex=int(data['predTex']),
        noEffectDoodad=int(data['noEffectDoodad']),
        holes_high_res=int(data['holes_high_res'])
    )

def _json_to_adt(data: Dict) -> ADTFile:
    """Convert JSON data to ADTFile"""
    # Convert MCNK chunks (stored as string keys in JSON)
    mcnk_chunks = {}
    for key, value in data.get('mcnk_chunks', {}).items():
        x, y = map(int, key.strip('()').split(','))
        mcnk_chunks[(x, y)] = _json_to_mcnk(value)
        
    return ADTFile(
        path=data['path'],
        file_type='adt',
        format_type=data['format_type'],
        version=int(data['version']),
        flags=MCNKFlags(data['flags']),
        map_name=data['map_name'],
        chunk_order=data['chunk_order'],
        textures=[TextureInfo(**tex) for tex in data.get('textures', [])],
        m2_models=data.get('m2_models', []),
        wmo_models=data.get('wmo_models', []),
        m2_placements=[_json_to_model_placement(p) for p in data.get('m2_placements', [])],
        wmo_placements=[_json_to_model_placement(p, True) for p in data.get('wmo_placements', [])],
        mcnk_chunks=mcnk_chunks,
        subchunks=data.get('subchunks', {})
    )

def _json_to_wdt(data: Dict) -> WDTFile:
    """Convert JSON data to WDTFile"""
    # Convert tiles (stored as string keys in JSON)
    tiles = {}
    for key, value in data.get('tiles', {}).items():
        x, y = map(int, key.strip('()').split(','))
        tiles[(x, y)] = MapTile(**value)
        
    return WDTFile(
        path=data['path'],
        file_type='wdt',
        format_type=data['format_type'],
        version=int(data['version']),
        flags=WDTFlags(data['flags']),
        map_name=data['map_name'],
        chunk_order=data['chunk_order'],
        tiles=tiles,
        m2_models=[ModelReference(**m) for m in data.get('m2_models', [])],
        wmo_models=[ModelReference(**m) for m in data.get('wmo_models', [])],
        m2_placements=[_json_to_model_placement(p) for p in data.get('m2_placements', [])],
        wmo_placements=[_json_to_model_placement(p, True) for p in data.get('wmo_placements', [])],
        is_global_wmo=bool(data.get('is_global_wmo', False))
    )