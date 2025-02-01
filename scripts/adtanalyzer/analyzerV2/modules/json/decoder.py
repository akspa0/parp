"""
JSON decoding for WoW terrain data structures.
Provides functions for deserializing JSON back into terrain data.
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from ..models import (
    Vector3D, RGBA, CAaBox,
    MCNKFlags, WDTFlags,
    TextureInfo, TextureLayer,
    ModelReference, ModelPlacement, WMOPlacement,
    MapTile, MCNKInfo,
    TerrainFile, ADTFile, WDTFile
)

def decode_vector3d(data: Dict) -> Vector3D:
    """Convert JSON data to Vector3D"""
    return Vector3D(
        x=float(data['x']),
        y=float(data['y']),
        z=float(data['z'])
    )

def decode_rgba(data: Dict) -> RGBA:
    """Convert JSON data to RGBA"""
    return RGBA(
        r=int(data['r']),
        g=int(data['g']),
        b=int(data['b']),
        a=int(data['a'])
    )

def decode_aabox(data: Dict) -> CAaBox:
    """Convert JSON data to CAaBox"""
    return CAaBox(
        min=decode_vector3d(data['min']),
        max=decode_vector3d(data['max'])
    )

def decode_texture_info(data: Dict) -> TextureInfo:
    """Convert JSON data to TextureInfo"""
    return TextureInfo(
        filename=data['filename'],
        flags=int(data.get('flags', 0)),
        effect_id=int(data.get('effect_id', 0)),
        layer_index=int(data.get('layer_index', 0)),
        blend_mode=int(data.get('blend_mode', 0)),
        is_compressed=bool(data.get('is_compressed', False))
    )

def decode_texture_layer(data: Dict) -> TextureLayer:
    """Convert JSON data to TextureLayer"""
    return TextureLayer(
        texture_id=int(data['texture_id']),
        flags=int(data['flags']),
        effect_id=int(data['effect_id']) if data.get('effect_id') is not None else None,
        layer_index=int(data.get('layer_index', 0)),
        blend_mode=int(data.get('blend_mode', 0)),
        is_compressed=bool(data.get('is_compressed', False)),
        alpha_map=data.get('alpha_map')
    )

def decode_model_reference(data: Dict) -> ModelReference:
    """Convert JSON data to ModelReference"""
    return ModelReference(
        path=data['path'],
        format_type=data.get('format_type', 'retail')
    )

def decode_model_placement(data: Dict, is_wmo: bool = False) -> Union[ModelPlacement, WMOPlacement]:
    """Convert JSON data to model placement"""
    base_data = {
        'name_id': int(data['name_id']),
        'unique_id': int(data['unique_id']),
        'position': decode_vector3d(data['position']),
        'rotation': decode_vector3d(data['rotation']),
        'scale': float(data['scale']),
        'flags': int(data['flags'])
    }
    
    if is_wmo:
        return WMOPlacement(
            **base_data,
            doodad_set=int(data['doodad_set']),
            name_set=int(data['name_set']),
            bounding_box=decode_aabox(data['bounding_box'])
        )
    return ModelPlacement(**base_data)

def decode_map_tile(data: Dict) -> MapTile:
    """Convert JSON data to MapTile"""
    return MapTile(
        x=int(data['x']),
        y=int(data['y']),
        offset=int(data.get('offset', 0)),
        size=int(data.get('size', 0)),
        flags=int(data.get('flags', 0)),
        async_id=int(data.get('async_id', 0))
    )

def decode_mcnk_info(data: Dict) -> MCNKInfo:
    """Convert JSON data to MCNKInfo"""
    return MCNKInfo(
        flags=MCNKFlags(int(data['flags'])),  # Convert JSON number back to Flag enum
        index_x=int(data['index_x']),
        index_y=int(data['index_y']),
        n_layers=int(data['n_layers']),
        n_doodad_refs=int(data['n_doodad_refs']),
        position=decode_vector3d(data['position']),
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
        holes_high_res=int(data['holes_high_res']),
        texture_layers=[decode_texture_layer(layer) for layer in data.get('texture_layers', [])],
        height_map=data.get('height_map'),
        normal_data=data.get('normal_data'),
        liquid_heights=data.get('liquid_heights'),
        liquid_flags=data.get('liquid_flags')
    )

def decode_adt_file(data: Dict) -> ADTFile:
    """Convert JSON data to ADTFile"""
    # Convert MCNK chunks (stored as string keys in JSON)
    mcnk_chunks = {}
    for key, value in data.get('mcnk_chunks', {}).items():
        x, y = map(int, key.strip('()').split(','))
        mcnk_chunks[(x, y)] = decode_mcnk_info(value)
        
    return ADTFile(
        path=data['path'],
        file_type='adt',
        format_type=data['format_type'],
        version=int(data['version']),
        flags=MCNKFlags(int(data['flags'])),  # Convert JSON number back to Flag enum
        map_name=data['map_name'],
        chunk_order=data['chunk_order'],
        textures=[decode_texture_info(tex) for tex in data.get('textures', [])],
        m2_models=data.get('m2_models', []),
        wmo_models=data.get('wmo_models', []),
        m2_placements=[decode_model_placement(p) for p in data.get('m2_placements', [])],
        wmo_placements=[decode_model_placement(p, True) for p in data.get('wmo_placements', [])],
        mcnk_chunks=mcnk_chunks,
        subchunks=data.get('subchunks', {})
    )

def decode_wdt_file(data: Dict) -> WDTFile:
    """Convert JSON data to WDTFile"""
    # Convert tiles (stored as string keys in JSON)
    tiles = {}
    for key, value in data.get('tiles', {}).items():
        x, y = map(int, key.strip('()').split(','))
        tiles[(x, y)] = decode_map_tile(value)
        
    return WDTFile(
        path=data['path'],
        file_type='wdt',
        format_type=data['format_type'],
        version=int(data['version']),
        flags=WDTFlags(int(data['flags'])),  # Convert JSON number back to Flag enum
        map_name=data['map_name'],
        chunk_order=data['chunk_order'],
        tiles=tiles,
        m2_models=[decode_model_reference(m) for m in data.get('m2_models', [])],
        wmo_models=[decode_model_reference(m) for m in data.get('wmo_models', [])],
        m2_placements=[decode_model_placement(p) for p in data.get('m2_placements', [])],
        wmo_placements=[decode_model_placement(p, True) for p in data.get('wmo_placements', [])],
        is_global_wmo=bool(data.get('is_global_wmo', False))
    )

def load_terrain_file(json_path: Path) -> TerrainFile:
    """
    Load terrain file from JSON
    
    Args:
        json_path: Path to JSON file
        
    Returns:
        Decoded terrain file
    """
    import json
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Determine file type
    file_type = data.get('file_type', '').lower()
    
    if file_type == 'adt':
        return decode_adt_file(data)
    elif file_type == 'wdt':
        return decode_wdt_file(data)
    else:
        raise ValueError(f"Unknown file type: {file_type}")