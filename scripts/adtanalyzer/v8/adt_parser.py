# adt_parser.py

import os
import re
import sys
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from adt_format import *

@dataclass
class MCNKData:
    flags: Dict[str, int]
    indices: Tuple[int, int]
    layer_count: int
    doodad_refs: int
    map_object_refs: int
    holes: int
    texture_map: List[int]
    position: Vec3D
    area_id: int
    sound_emitters: int

@dataclass
class ADTData:
    adt_version: int
    flags: int
    textures: List[str]
    m2_models: List[str]
    wmo_models: List[str]
    mddf: List[Dict[str, Any]]
    modf: List[Dict[str, Any]]
    mcnk: List[MCNKData]
    mcin: List[Dict[str, int]]

class ADTParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = None
        self.chunks = {}
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._setup_logging()

    def _setup_logging(self):
        log_filename = f"adt_parser_{self.timestamp}.log"
        logging.basicConfig(
            filename=log_filename,
            filemode='w',
            format='%(asctime)s [%(levelname)s] %(message)s',
            level=logging.DEBUG
        )
        self.logger = logging.getLogger(__name__)

    def parse(self) -> Optional[ADTData]:
        try:
            with open(self.file_path, 'rb') as f:
                self.data = f.read()
        except Exception as e:
            self.logger.error(f"Failed to read file {self.file_path}: {e}")
            return None

        self._parse_chunks()
        return self._process_chunks()

    def _parse_chunks(self):
        offset = 0
        while offset < len(self.data):
            magic, size = read_chunk_header(self.data, offset)
            if not magic or not size:
                break

            chunk_data = self.data[offset:offset + 8 + size]
            self.chunks[magic] = chunk_data
            offset += 8 + size
            
            # Special handling for MCNK chunks
            if magic == b'MCNK':
                if b'MCNK_chunks' not in self.chunks:
                    self.chunks[b'MCNK_chunks'] = []
                self.chunks[b'MCNK_chunks'].append(chunk_data)

    def _process_chunks(self) -> ADTData:
        # Initialize with defaults
        flags = 0
        adt_version = 0
        textures = []
        m2_models = []
        wmo_models = []
        mddf_entries = []
        modf_entries = []
        mcnk_data = []
        mcin_entries = []

        # Parse version and flags
        if b'MVER' in self.chunks:
            try:
                mver = MVERChunk.parse(self.chunks[b'MVER'])
                adt_version = mver.version
            except Exception as e:
                self.logger.error(f"Failed to parse MVER chunk: {e}")

        if b'MHDR' in self.chunks:
            try:
                mhdr = MHDRChunk.parse(self.chunks[b'MHDR'])
                flags = mhdr.flags
            except Exception as e:
                self.logger.error(f"Failed to parse MHDR chunk: {e}")

        # Parse MCIN (cell information)
        if b'MCIN' in self.chunks:
            try:
                mcin = MCINChunk.parse(self.chunks[b'MCIN'])
                mcin_entries = [
                    {
                        'offset': entry.offset,
                        'size': entry.size,
                        'flags': entry.flags,
                        'async_id': entry.async_id
                    }
                    for entry in mcin.entries
                ]
            except Exception as e:
                self.logger.error(f"Failed to parse MCIN chunk: {e}")

        # Parse textures
        if b'MTEX' in self.chunks:
            try:
                mtex = MTEXChunk.parse(self.chunks[b'MTEX'])
                textures = mtex.textures
            except Exception as e:
                self.logger.error(f"Failed to parse MTEX chunk: {e}")

        # Parse M2 models
        if b'MMDX' in self.chunks and b'MMID' in self.chunks:
            try:
                mmdx = ModelListChunk.parse(self.chunks[b'MMDX'])
                mmid = OffsetListChunk.parse(self.chunks[b'MMID'])
                m2_models = parse_string_list_from_offsets(mmdx.data, mmid.offsets)
            except Exception as e:
                self.logger.error(f"Failed to parse M2 model list: {e}")

        # Parse WMO models
        if b'MWMO' in self.chunks and b'MWID' in self.chunks:
            try:
                mwmo = ModelListChunk.parse(self.chunks[b'MWMO'])
                mwid = OffsetListChunk.parse(self.chunks[b'MWID'])
                wmo_models = parse_string_list_from_offsets(mwmo.data, mwid.offsets)
            except Exception as e:
                self.logger.error(f"Failed to parse WMO model list: {e}")

        # Parse M2 placements
        if b'MDDF' in self.chunks:
            try:
                mddf = MDDFChunk.parse(self.chunks[b'MDDF'])
                for entry in mddf.entries:
                    mddf_entries.append({
                        'nameId': entry.nameId,
                        'uniqueId': entry.uniqueId,
                        'position': {
                            'x': entry.position.x,
                            'y': entry.position.y,
                            'z': entry.position.z
                        },
                        'rotation': {
                            'x': entry.rotation.x,
                            'y': entry.rotation.y,
                            'z': entry.rotation.z
                        },
                        'scale': entry.scale / 1024.0,
                        'flags': entry.flags,
                        'model_name': m2_models[entry.nameId] if entry.nameId < len(m2_models) else ""
                    })
            except Exception as e:
                self.logger.error(f"Failed to parse MDDF chunk: {e}")

        # Parse WMO placements
        if b'MODF' in self.chunks:
            try:
                modf = MODFChunk.parse(self.chunks[b'MODF'])
                for entry in modf.entries:
                    modf_entries.append({
                        'nameId': entry.nameId,
                        'uniqueId': entry.uniqueId,
                        'position': {
                            'x': entry.position.x,
                            'y': entry.position.y,
                            'z': entry.position.z
                        },
                        'rotation': {
                            'x': entry.rotation.x,
                            'y': entry.rotation.y,
                            'z': entry.rotation.z
                        },
                        'extents_lower': {
                            'x': entry.extents_lower.x,
                            'y': entry.extents_lower.y,
                            'z': entry.extents_lower.z
                        },
# Complete _process_chunks
        # Upper bounds of the extents
                        'extents_upper': {
                            'x': entry.extents_upper.x,
                            'y': entry.extents_upper.y,
                            'z': entry.extents_upper.z
                        },
                        'flags': entry.flags,
                        'doodadSet': entry.doodadSet,
                        'nameSet': entry.nameSet,
                        'scale': entry.scale / 1024.0,
                        'model_name': wmo_models[entry.nameId] if entry.nameId < len(wmo_models) else ""
                    })
            except Exception as e:
                self.logger.error(f"Failed to parse MODF chunk: {e}")

        # Parse MCNK chunks
        if b'MCNK_chunks' in self.chunks:
            for chunk in self.chunks[b'MCNK_chunks']:
                try:
                    mcnk = MCNKChunk.parse(chunk)
                    mcnk_data.append(
                        MCNKData(
                            flags=dict(mcnk.flags),
                            indices=(mcnk.ix, mcnk.iy),
                            layer_count=mcnk.layer_count,
                            doodad_refs=mcnk.doodad_refs,
                            map_object_refs=mcnk.map_object_refs,
                            holes=mcnk.holes,
                            texture_map=mcnk.low_quality_texture_map,
                            position=mcnk.position,
                            area_id=mcnk.area_id,
                            sound_emitters=mcnk.sound_emitters,
                        )
                    )
                except Exception as e:
                    self.logger.error(f"Failed to parse MCNK chunk: {e}")

        return ADTData(
            adt_version=adt_version,
            flags=flags,
            textures=textures,
            m2_models=m2_models,
            wmo_models=wmo_models,
            mddf=mddf_entries,
            modf=modf_entries,
            mcnk=mcnk_data,
            mcin=mcin_entries,
        )

def main():
    if len(sys.argv) < 3:
        print("Usage: python adt_parser.py <path_to_adt_file> <path_to_listfile>")
        sys.exit(1)

    adt_file_path = sys.argv[1]
    listfile_path = sys.argv[2]

    parser = ADTParser(adt_file_path)
    adt_data = parser.parse()

    if adt_data:
        output_file = f"{os.path.splitext(adt_file_path)[0]}_parsed.json"
        with open(output_file, 'w') as f:
            json.dump(asdict(adt_data), f, indent=4)
        print(f"Parsed data saved to {output_file}")

if __name__ == "__main__":
    main()
