#!/usr/bin/env python3
import os
import sys
import json
import logging
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple, BinaryIO, Any
from datetime import datetime
from dataclasses import dataclass, asdict, field
import argparse
import struct
from collections import defaultdict
import traceback

def chunk_name_rev(name: str) -> str:
    return name[::-1]

@dataclass
class TerrainLayer:
    texture_id: int
    flags: int
    offset_mcal: int
    effect_id: int
    layer_height: float = 0.0
    alpha_map: Optional[bytes] = None

@dataclass
class MCNKChunk:
    flags: int
    ix: int
    iy: int
    n_layers: int
    n_doodad_refs: int
    n_object_refs: int
    holes: int
    layer_ex: int
    height_min: float
    height_max: float
    position: Tuple[float, float, float]
    area_id: int
    n_ground_effects: int
    prediction_type: int
    prediction_id: int
    height_map: List[float] = field(default_factory=list)
    normals: List[Tuple[float, float, float]] = field(default_factory=list)
    layers: List[TerrainLayer] = field(default_factory=list)
    doodad_refs: List[int] = field(default_factory=list)
    object_refs: List[int] = field(default_factory=list)
    shadow_map: Optional[bytes] = None
    alpha_maps: List[bytes] = field(default_factory=list)

@dataclass
class ModelPlacement:
    name_id: int
    unique_id: int
    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float]
    scale: float
    flags: int

@dataclass
class WMOPlacement:
    name_id: int
    unique_id: int
    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float]
    extent_min: Tuple[float, float, float]
    extent_max: Tuple[float, float, float]
    flags: int
    doodad_set: int
    name_set: int
    scale: int

class ADTDecoder:
    CHUNK_DECODERS = {
        'MVER': '_decode_mver',
        'MHDR': '_decode_mhdr',
        'MCIN': '_decode_mcin',
        'MTEX': '_decode_mtex',
        'MMDX': '_decode_mmdx',
        'MMID': '_decode_mmid',
        'MWMO': '_decode_mwmo',
        'MWID': '_decode_mwid',
        'MDDF': '_decode_mddf',
        'MODF': '_decode_modf',
        'MCNK': '_decode_mcnk',
        'MH2O': '_decode_mh2o',
        'MFBO': '_decode_mfbo',
        'MTXF': '_decode_mtxf'
    }

    def __init__(self, filename: str):
        from .name_reference_decoders import MTEXChunk, MMDXChunk, MMIDChunk, MWMOChunk, MWIDChunk
        from .texture_decoders import TextureManager
        
        self.filename = filename
        self.chunks = {}
        self.texture_manager = TextureManager()
        
        # Store name reference chunks for linking
        self.mtex_chunk = None
        self.mmdx_chunk = None
        self.mwmo_chunk = None

    def _decode_mtex(self, data: bytes) -> Dict:
        """Decode texture filename list"""
        from .texture_decoders import TextureDecoder
        filenames = TextureDecoder.decode_mtex(data)
        # Store for texture manager
        self.mtex_data = data
        return {'filenames': filenames}

    def _decode_mtxf(self, data: bytes) -> Dict:
        """Decode texture flags chunk"""
        from .texture_decoders import TextureDecoder, TextureFlag
        flags = TextureDecoder.decode_mtxf(data)
        # Store for texture manager
        self.mtxf_data = data
        return {
            'texture_flags': [
                {
                    'texture_id': flag.texture_id,
                    'flags': {
                        'value': flag.flags,
                        'is_terrain': flag.is_terrain,
                        'is_hole': flag.is_hole,
                        'is_water': flag.is_water,
                        'has_alpha': flag.has_alpha,
                        'is_animated': flag.is_animated
                    }
                }
                for flag in flags
            ]
        }

    def _decode_mmdx(self, data: bytes) -> Dict:
        """Decode M2 model filename list"""
        from .name_reference_decoders import MMDXChunk
        self.mmdx_chunk = MMDXChunk(data)
        return {'filenames': self.mmdx_chunk.filenames}

    def _decode_mmid(self, data: bytes) -> Dict:
        """Decode M2 filename offset list"""
        from .name_reference_decoders import MMIDChunk
        if self.mmdx_chunk:
            mmid = MMIDChunk(data, self.mmdx_chunk)
            return {
                'offsets': mmid.offsets,
                'filenames': [mmid.get_filename(offset) for offset in mmid.offsets]
            }
        return {'offsets': list(struct.unpack(f'<{len(data)//4}I', data))}

    def _decode_mwmo(self, data: bytes) -> Dict:
        """Decode WMO filename list"""
        from .name_reference_decoders import MWMOChunk
        self.mwmo_chunk = MWMOChunk(data)
        return {'filenames': self.mwmo_chunk.filenames}

    def _decode_mwid(self, data: bytes) -> Dict:
        """Decode WMO filename offset list"""
        from .name_reference_decoders import MWIDChunk
        if self.mwmo_chunk:
            mwid = MWIDChunk(data, self.mwmo_chunk)
            return {
                'offsets': mwid.offsets,
                'filenames': [mwid.get_filename(offset) for offset in mwid.offsets]
            }
        return {'offsets': list(struct.unpack(f'<{len(data)//4}I', data))}

    def _decode_mfbo(self, data: bytes) -> Dict:
        """Decode flight bounds chunk"""
        from .misc_root_decoders import MFBOChunk
        mfbo = MFBOChunk(data)
        return {
            'flight_boxes': [
                {
                    'min': {'x': box.min_x, 'y': box.min_y, 'z': box.min_z},
                    'max': {'x': box.max_x, 'y': box.max_y, 'z': box.max_z}
                }
                for box in mfbo.flight_boxes
            ]
        }



    def _decode_mver(self, data: bytes) -> Dict:
        return {'version': struct.unpack('<I', data)[0]}

    def _decode_mhdr(self, data: bytes) -> Dict:
        flags = struct.unpack('<I', data[:4])[0]
        return {
            'flags': flags,
            'mfbo': bool(flags & 0x1),
            'northrend': bool(flags & 0x2),
            'has_mccv': bool(flags & 0x4),
            'has_big_alpha': bool(flags & 0x8),
            'has_vertex_shadows': bool(flags & 0x10),
            'has_terrain_normal': bool(flags & 0x20),
            'has_vertex_lighting': bool(flags & 0x40),
            'offsets': struct.unpack('<8I', data[4:36])
        }

    def _decode_mcin(self, data: bytes) -> Dict:
        indexes = []
        for i in range(256):
            offset = i * 16
            indexes.append({
                'offset': struct.unpack_from('<I', data, offset)[0],
                'size': struct.unpack_from('<I', data, offset + 4)[0],
                'flags': struct.unpack_from('<I', data, offset + 8)[0],
                'async_id': struct.unpack_from('<I', data, offset + 12)[0]
            })
        return {'chunk_indices': indexes}

    def _decode_mddf(self, data: bytes) -> Dict:
        """Decode M2/Doodad placement chunk"""
        from .placement_decoders import MDDFChunk, MDDFFlags
        mddf = MDDFChunk(data)
        return {
            'placements': [
                {
                    'name_id': doodad.name_id,
                    'unique_id': doodad.unique_id,
                    'position': {
                        'x': doodad.position.x,
                        'y': doodad.position.y,
                        'z': doodad.position.z
                    },
                    'rotation': {
                        'x': doodad.rotation.x,
                        'y': doodad.rotation.y,
                        'z': doodad.rotation.z
                    },
                    'scale': doodad.scale,
                    'flags': {
                        'value': int(doodad.flags),
                        'biodome': bool(doodad.flags & MDDFFlags.BIODOME),
                        'shrubbery': bool(doodad.flags & MDDFFlags.SHRUBBERY),
                        'liquid_known': bool(doodad.flags & MDDFFlags.LIQUID_KNOWN),
                        'entry_is_filedata_id': bool(doodad.flags & MDDFFlags.ENTRY_IS_FILEDATA_ID),
                        'accept_proj_textures': bool(doodad.flags & MDDFFlags.ACCEPT_PROJ_TEXTURES)
                    }
                }
                for doodad in mddf.doodads
            ]
        }

    def _decode_modf(self, data: bytes) -> Dict:
        """Decode WMO placement chunk"""
        from .placement_decoders import MODFChunk, MODFFlags
        modf = MODFChunk(data)
        return {
            'placements': [
                {
                    'name_id': obj.name_id,
                    'unique_id': obj.unique_id,
                    'position': {
                        'x': obj.position.x,
                        'y': obj.position.y,
                        'z': obj.position.z
                    },
                    'rotation': {
                        'x': obj.rotation.x,
                        'y': obj.rotation.y,
                        'z': obj.rotation.z
                    },
                    'extents': {
                        'min': {
                            'x': obj.extents.min.x,
                            'y': obj.extents.min.y,
                            'z': obj.extents.min.z
                        },
                        'max': {
                            'x': obj.extents.max.x,
                            'y': obj.extents.max.y,
                            'z': obj.extents.max.z
                        }
                    },
                    'flags': {
                        'value': int(obj.flags),
                        'destroyable': bool(obj.flags & MODFFlags.DESTROYABLE),
                        'use_lod': bool(obj.flags & MODFFlags.USE_LOD),
                        'has_scale': bool(obj.flags & MODFFlags.HAS_SCALE),
                        'entry_is_filedata_id': bool(obj.flags & MODFFlags.ENTRY_IS_FILEDATA_ID),
                        'use_sets_from_mwds': bool(obj.flags & MODFFlags.USE_SETS_FROM_MWDS)
                    },
                    'doodad_set': obj.doodad_set,
                    'name_set': obj.name_set,
                    'scale': obj.scale
                }
                for obj in modf.map_objects
            ]
        }

    def _ensure_json_serializable(self, data: Any) -> Any:
        """Ensure data is JSON serializable, encoding binary data in base64"""
        if isinstance(data, bytes):
            return base64.b64encode(data).decode('utf-8')
        elif isinstance(data, dict):
            return {k: self._ensure_json_serializable(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._ensure_json_serializable(item) for item in data]
        elif isinstance(data, tuple):
            return list(self._ensure_json_serializable(item) for item in data)
        elif isinstance(data, (int, float, str, bool, type(None))):
            return data
        else:
            return str(data)

    def _decode_mcnk(self, data: bytes, index: int = 0) -> Dict:
        try:
            from .mcnk_subchunk_decoders import (
                MCLYChunk, MCALChunk, MCCVChunk, MCSEChunk,
                MCBBChunk, MCRFChunk, MCSHChunk
            )
            
            header_size = 128
            header = data[:header_size]
            
            # Parse header
            flags = struct.unpack_from('<I', header, 0)[0]
            ix = struct.unpack_from('<I', header, 4)[0]
            iy = struct.unpack_from('<I', header, 8)[0]
            n_layers = struct.unpack_from('<I', header, 12)[0]
            n_doodad_refs = struct.unpack_from('<I', header, 16)[0]
            offset_mcvt = struct.unpack_from('<I', header, 20)[0]
            offset_mcnr = struct.unpack_from('<I', header, 24)[0]
            offset_mcly = struct.unpack_from('<I', header, 28)[0]
            offset_mcrf = struct.unpack_from('<I', header, 32)[0]
            offset_mcal = struct.unpack_from('<I', header, 36)[0]
            size_mcal = struct.unpack_from('<I', header, 40)[0]
            offset_mcsh = struct.unpack_from('<I', header, 44)[0]
            size_mcsh = struct.unpack_from('<I', header, 48)[0]
            area_id = struct.unpack_from('<I', header, 52)[0]
            n_mapobj_refs = struct.unpack_from('<I', header, 56)[0]
            holes = struct.unpack_from('<I', header, 60)[0]
            layer_tex_flags = struct.unpack_from('<H', header, 64)[0]
            layer_tex_id = struct.unpack_from('<H', header, 66)[0]
            offset_mcse = struct.unpack_from('<I', header, 68)[0]
            n_sound_emitters = struct.unpack_from('<I', header, 72)[0]
            offset_mclq = struct.unpack_from('<I', header, 76)[0]
            size_liquid = struct.unpack_from('<I', header, 80)[0]
            position = struct.unpack_from('<3f', header, 84)
            offset_mccv = struct.unpack_from('<I', header, 96)[0]
            offset_mcbb = struct.unpack_from('<I', header, 108)[0]

            result = {
                'header': {
                    'flags': flags,
                    'ix': ix,
                    'iy': iy,
                    'n_layers': n_layers,
                    'n_doodad_refs': n_doodad_refs,
                    'n_object_refs': n_mapobj_refs,
                    'holes': holes,
                    'layer_tex_flags': layer_tex_flags,
                    'layer_tex_id': layer_tex_id,
                    'area_id': area_id,
                    'position': position,
                    'n_sound_emitters': n_sound_emitters
                },
                'subchunks': {}
            }

            # Decode height map
            if offset_mcvt and offset_mcvt + 580 <= len(data):  # 145 floats * 4 bytes
                try:
                    result['subchunks']['MCVT'] = {
                        'heights': list(struct.unpack('<145f', data[offset_mcvt:offset_mcvt+580]))
                    }
                except struct.error:
                    logging.warning(f"Invalid MCVT data size in chunk {index}")

            # Decode normals
            if offset_mcnr and offset_mcnr + 435 <= len(data):  # 145 vertices * 3 bytes
                try:
                    result['subchunks']['MCNR'] = {
                        'normals': [
                            tuple(x/127.0 for x in struct.unpack_from('<3b', data, offset_mcnr+i))
                            for i in range(0, 435, 3)
                        ]
                    }
                except struct.error:
                    logging.warning(f"Invalid MCNR data size in chunk {index}")

            # Decode texture layers
            if offset_mcly and n_layers > 0 and offset_mcly + (n_layers * 16) <= len(data):
                try:
                    mcly_data = data[offset_mcly:offset_mcly + (n_layers * 16)]
                    mcly_chunks = MCLYChunk.read(mcly_data)
                    
                    # Store layer info
                    result['subchunks']['MCLY'] = []
                    for mcly in mcly_chunks:
                        layer = {
                            'texture_id': mcly.textureId,
                            'flags': mcly.flags,
                            'offset_mcal': mcly.offsetInMCAL,
                            'effect_id': mcly.effectId
                        }
                        result['subchunks']['MCLY'].append(layer)

                    # Decode alpha maps if available
                    if offset_mcal and size_mcal > 0 and offset_mcal + size_mcal <= len(data):
                        try:
                            mcal_data = data[offset_mcal:offset_mcal + size_mcal]
                            alpha_maps = MCALChunk.read(mcal_data, mcly_chunks)
                            
                            # Store alpha maps
                            result['subchunks']['MCAL'] = {}
                            for texture_id, alpha_map in alpha_maps.items():
                                result['subchunks']['MCAL'][texture_id] = {
                                    'alpha_map': alpha_map.alpha_map
                                }
                        except struct.error:
                            logging.warning(f"Invalid MCAL data size in chunk {index}")
                except struct.error:
                    logging.warning(f"Invalid MCLY data size in chunk {index}")

            # Decode vertex colors
            if offset_mccv and offset_mccv + (145 * 4) <= len(data):  # 145 vertices * 4 bytes (RGBA)
                try:
                    mccv_data = data[offset_mccv:offset_mccv + (145 * 4)]
                    mccv = MCCVChunk.read(mccv_data)
                    result['subchunks']['MCCV'] = {
                        'vertex_colors': mccv.vertex_colors
                    }
                except struct.error:
                    logging.warning(f"Invalid MCCV data size in chunk {index}")

            # Decode sound emitters
            if offset_mcse and n_sound_emitters > 0 and offset_mcse + (n_sound_emitters * 28) <= len(data):
                try:
                    mcse_data = data[offset_mcse:offset_mcse + (n_sound_emitters * 28)]
                    mcse = MCSEChunk.read(mcse_data)
                    result['subchunks']['MCSE'] = {
                        'entries': mcse.entries
                    }
                except struct.error:
                    logging.warning(f"Invalid MCSE data size in chunk {index}")

            # Decode bounding box
            if offset_mcbb and offset_mcbb + 24 <= len(data):  # Ensure we have enough data
                mcbb_data = data[offset_mcbb:offset_mcbb + 24]  # 6 floats * 4 bytes
                try:
                    mcbb = MCBBChunk.read(mcbb_data)
                    result['subchunks']['MCBB'] = asdict(mcbb)
                except struct.error:
                    logging.warning(f"Invalid MCBB data size in chunk {index}")

            # Store basic liquid info without detailed parsing
            if offset_mclq and size_liquid > 0:
                result['subchunks']['MCLQ'] = {
                    'offset': offset_mclq,
                    'size': size_liquid,
                    'flags': flags & 0x1C  # Mask for liquid type flags (0x4 | 0x8 | 0x10)
                }

            # Decode doodad references
            if offset_mcrf and n_doodad_refs > 0 and offset_mcrf + (n_doodad_refs * 4) <= len(data):
                try:
                    mcrf_data = data[offset_mcrf:offset_mcrf + (n_doodad_refs * 4)]
                    mcrf = MCRFChunk.read(mcrf_data)
                    result['subchunks']['MCRF'] = {
                        'entries': mcrf.entries
                    }
                except struct.error:
                    logging.warning(f"Invalid MCRF data size in chunk {index}")

            # Decode shadow map
            if offset_mcsh and size_mcsh > 0 and offset_mcsh + size_mcsh <= len(data):
                try:
                    mcsh_data = data[offset_mcsh:offset_mcsh + size_mcsh]
                    mcsh = MCSHChunk.read(mcsh_data)
                    result['subchunks']['MCSH'] = {
                        'shadow_map': mcsh.shadow_map
                    }
                except struct.error:
                    logging.warning(f"Invalid MCSH data size in chunk {index}")

            return result

        except Exception as e:
            error_msg = f"Error decoding MCNK chunk {index}: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            return {'error': error_msg}

    def decode_file(self) -> Dict:
        """Decode ADT file in two passes"""
        with open(self.filename, 'rb') as f:
            data = f.read()
            
        pos = 0
        mcnk_index = 0
        mtex_filenames = []  # Store MTEX filenames for second pass
        
        # First pass: Decode all chunks
        while pos < len(data):
            if pos + 8 > len(data):
                break
                
            chunk_name = chunk_name_rev(data[pos:pos+4].decode('ascii'))
            chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
            
            if chunk_size > len(data) - (pos + 8):
                break
                
            chunk_data = data[pos+8:pos+8+chunk_size]
            
            if chunk_name in self.CHUNK_DECODERS:
                decoder = getattr(self, self.CHUNK_DECODERS[chunk_name])
                if chunk_name == 'MCNK':
                    self.chunks[f'MCNK_{mcnk_index}'] = decoder(chunk_data, mcnk_index)
                    mcnk_index += 1
                else:
                    decoded = decoder(chunk_data)
                    self.chunks[chunk_name] = decoded
                    # Store MTEX filenames for later use
                    if chunk_name == 'MTEX':
                        mtex_filenames = decoded['filenames']
            else:
                self.chunks[chunk_name] = {'raw_size': chunk_size}
                
            pos += 8 + chunk_size
            
        # Second pass: Process textures and link to layers
        if hasattr(self, 'mtex_data'):
            # Initialize texture manager with all available data
            if hasattr(self, 'mtxf_data'):
                self.texture_manager.load_from_chunks(self.mtex_data, self.mtxf_data)
            else:
                self.texture_manager.load_from_chunks(self.mtex_data)

            # Link textures to layers and add texture info
            for i in range(mcnk_index):
                mcnk_key = f'MCNK_{i}'
                if mcnk_key in self.chunks:
                    mcnk_data = self.chunks[mcnk_key]
                    if 'subchunks' in mcnk_data and 'MCLY' in mcnk_data['subchunks']:
                        for layer in mcnk_data['subchunks']['MCLY']:
                            texture = self.texture_manager.get_texture_by_id(layer['texture_id'])
                            if texture:
                                layer['texture_info'] = {
                                    'filename': texture.filename,
                                    'base_name': texture.base_name,
                                    'is_tileable': texture.is_tileable,
                                    'flags': {
                                        'is_terrain': texture.flags.is_terrain,
                                        'is_hole': texture.flags.is_hole,
                                        'is_water': texture.flags.is_water,
                                        'has_alpha': texture.flags.has_alpha,
                                        'is_animated': texture.flags.is_animated
                                    }
                                }

            # Add texture statistics
            stats = self.texture_manager.analyze_texture_usage()
            self.chunks['texture_stats'] = {
                'total_textures': stats['total'],
                'terrain_textures': stats['terrain'],
                'water_textures': stats['water'],
                'holes': stats['holes'],
                'animated_textures': stats['animated'],
                'alpha_textures': stats['with_alpha'],
                'tileable_textures': stats['tileable'],
                'unique_paths': stats['unique_paths'],
                'total_layers': stats['layers']
            }

        return self.chunks

    def _decode_mh2o(self, data: bytes) -> Dict:
        """Decode modern liquid chunk (MH2O)"""
        from .liquid_decoders import MH2OChunk
        
        mh2o = MH2OChunk(data)
        result = {'chunks': []}
        
        for x, y, instances in mh2o.chunks:
            chunk_info = {
                'position': {'x': x, 'y': y},
                'size': len(instances)
            }
            result['chunks'].append(chunk_info)
        
        return result

class ADTDirectoryParser:
    def __init__(self, input_dir: str, output_dir: str, log_file: str, debug: bool = False):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def process_file(self, adt_path: Path) -> Dict:
        try:
            self.logger.info(f"Processing {adt_path}")
            decoder = ADTDecoder(str(adt_path))
            data = decoder.decode_file()
            
            # Ensure all data is JSON serializable
            json_safe_data = decoder._ensure_json_serializable(data)
            
            output_json = self.output_dir / f"{adt_path.stem}.json"
            
            result = {
                'filename': adt_path.name,
                'file_size': os.path.getsize(adt_path),
                'chunks': json_safe_data,
                'processed_at': datetime.now().isoformat()
            }
            
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Generated JSON: {output_json}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing {adt_path}: {str(e)}")
            return {
                'filename': adt_path.name,
                'error': str(e)
            }

    def process_directory(self) -> List[Dict]:
        results = []
        adt_files = list(self.input_dir.glob('**/*.adt'))
        
        self.logger.info(f"Found {len(adt_files)} ADT files to process")
        
        for adt_path in adt_files:
            result = self.process_file(adt_path)
            results.append(result)
            
        return results

    def generate_statistics(self, results: List[Dict]):
        if not results:
            self.logger.warning("No results to analyze")
            return
            
def main():
    parser = argparse.ArgumentParser(description='Process directory of ADT files')
    parser.add_argument('input_dir', help='Input directory containing ADT files')
    parser.add_argument('--output', '-o', default='adt_output',
                      help='Output directory for JSON files (default: adt_output)')
    parser.add_argument('--log', '-l', default='adt_processing.log',
                      help='Log file (default: adt_processing.log)')
    parser.add_argument('--debug', '-d', action='store_true',
                      help='Enable debug logging')
    
    args = parser.parse_args()
    
    processor = ADTDirectoryParser(args.input_dir, args.output, args.log, args.debug)
    results = processor.process_directory()
    processor.generate_statistics(results)

if __name__ == '__main__':
    main()
