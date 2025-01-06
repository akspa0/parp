#!/usr/bin/env python3
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, BinaryIO
from datetime import datetime
from dataclasses import dataclass, asdict, field
import argparse
import struct
from collections import defaultdict
import sqlite3

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
    liquid_type: int = 0
    liquid_height: float = 0.0
    liquid_flags: int = 0
    liquid_data: Optional[bytes] = None

@dataclass
class ModelPlacement:
    id: int
    unique_id: int
    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float]
    scale: float
    flags: int

@dataclass
class WMOPlacement:
    id: int
    unique_id: int
    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float]
    extent_min: Tuple[float, float, float]
    extent_max: Tuple[float, float, float]
    flags: int
    doodad_set: int
    name_set: int
    unknown: int

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
        'MH2O': '_decode_mh2o'
    }

    def __init__(self, filename: str):
        self.filename = filename
        self.chunks = {}
        self.mcnk_grid = [[None for x in range(16)] for y in range(16)]

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

    def _decode_mtex(self, data: bytes) -> Dict:
        pos = 0
        filenames = []
        while pos < len(data):
            if data[pos] == 0:
                pos += 1
                continue
            end = data.find(b'\0', pos)
            if end == -1:
                break
            filenames.append(data[pos:end].decode('utf-8'))
            pos = end + 1
        return {'filenames': filenames}

    def _decode_mmdx(self, data: bytes) -> Dict:
        return self._decode_mtex(data)  # Same format as MTEX

    def _decode_mmid(self, data: bytes) -> Dict:
        return {'offsets': list(struct.unpack(f'<{len(data)//4}I', data))}

    def _decode_mwmo(self, data: bytes) -> Dict:
        return self._decode_mtex(data)  # Same format as MTEX

    def _decode_mwid(self, data: bytes) -> Dict:
        return self._decode_mmid(data)  # Same format as MMID

    def _decode_mddf(self, data: bytes) -> Dict:
        placements = []
        for i in range(0, len(data), 36):
            chunk = data[i:i+36]
            placement = ModelPlacement(
                id=struct.unpack_from('<I', chunk, 0)[0],
                unique_id=struct.unpack_from('<I', chunk, 4)[0],
                position=struct.unpack_from('<3f', chunk, 8),
                rotation=struct.unpack_from('<3f', chunk, 20),
                scale=struct.unpack_from('<f', chunk, 32)[0],
                flags=struct.unpack_from('<H', chunk, 34)[0]
            )
            placements.append(asdict(placement))
        return {'placements': placements}

    def _decode_modf(self, data: bytes) -> Dict:
        placements = []
        for i in range(0, len(data), 64):
            chunk = data[i:i+64]
            placement = WMOPlacement(
                id=struct.unpack_from('<I', chunk, 0)[0],
                unique_id=struct.unpack_from('<I', chunk, 4)[0],
                position=struct.unpack_from('<3f', chunk, 8),
                rotation=struct.unpack_from('<3f', chunk, 20),
                extent_min=struct.unpack_from('<3f', chunk, 32),
                extent_max=struct.unpack_from('<3f', chunk, 44),
                flags=struct.unpack_from('<H', chunk, 56)[0],
                doodad_set=struct.unpack_from('<H', chunk, 58)[0],
                name_set=struct.unpack_from('<H', chunk, 60)[0],
                unknown=struct.unpack_from('<H', chunk, 62)[0]
            )
            placements.append(asdict(placement))
        return {'placements': placements}

    def _decode_mcnk(self, data: bytes, index: int = 0) -> Dict:
        header_size = 128
        header = data[:header_size]
        
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
        position = struct.unpack_from('<3f', header, 84)

        chunk = MCNKChunk(
            flags=flags,
            ix=ix,
            iy=iy,
            n_layers=n_layers,
            n_doodad_refs=n_doodad_refs,
            n_object_refs=n_mapobj_refs,
            holes=holes,
            layer_ex=layer_tex_flags,
            height_min=0,
            height_max=0,
            position=position,
            area_id=area_id,
            n_ground_effects=0,
            prediction_type=0,
            prediction_id=0
        )

        if offset_mcvt:
            chunk.height_map = list(struct.unpack('<145f', data[offset_mcvt:offset_mcvt+580]))

        if offset_mcnr:
            chunk.normals = [
                tuple(x/127.0 for x in struct.unpack_from('<3b', data, offset_mcnr+i))
                for i in range(0, 435, 3)
            ]

        return asdict(chunk)

    def _decode_mh2o(self, data: bytes) -> Dict:
        if len(data) < 8:
            return {'chunks': []}
            
        chunks = []
        for i in range(256):
            offset = i * 8
            info = {
                'offset': struct.unpack_from('<I', data, offset)[0],
                'layer_count': struct.unpack_from('<I', data, offset + 4)[0],
                'layers': []
            }
            if info['offset'] and info['layer_count']:
                pos = info['offset']
                for j in range(info['layer_count']):
                    if pos + 20 <= len(data):
                        layer = {
                            'type': struct.unpack_from('<H', data, pos)[0],
                            'flags': struct.unpack_from('<H', data, pos + 2)[0],
                            'height_levels': struct.unpack_from('<2f', data, pos + 4),
                            'offset_mask': struct.unpack_from('<I', data, pos + 12)[0],
                            'offset_data': struct.unpack_from('<I', data, pos + 16)[0]
                        }
                        info['layers'].append(layer)
                    pos += 20
            chunks.append(info)
        return {'chunks': chunks}

    def decode_file(self) -> Dict:
        with open(self.filename, 'rb') as f:
            data = f.read()
            
        pos = 0
        mcnk_index = 0
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
                    self.chunks[chunk_name] = decoder(chunk_data)
            else:
                self.chunks[chunk_name] = {'raw_size': chunk_size}
                
            pos += 8 + chunk_size
            
        return self.chunks

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
            
            output_json = self.output_dir / f"{adt_path.stem}.json"
            
            result = {
                'filename': adt_path.name,
                'file_size': os.path.getsize(adt_path),
                'chunks': data,
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
