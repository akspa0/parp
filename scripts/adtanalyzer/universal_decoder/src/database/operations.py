"""
Database operations for WoW map data
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple, Set
from pathlib import Path
from datetime import datetime
from .models import DatabaseManager

class DatabaseOperations:
    """High-level database operations"""
    
    def __init__(self, db_path: str):
        self.db = DatabaseManager(db_path)
        self.unique_ids: Set[int] = set()

    def insert_map(self, name: str, format_type: str, version: int, flags: int, chunk_order: str = '') -> int:
        """Insert map record and return its ID"""
        cursor = self.db.conn.execute(
            """
            INSERT INTO maps (name, format, version, flags, chunk_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, format_type, version, flags, chunk_order)
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def insert_map_tile(self, map_id: int, x: int, y: int, flags: int,
                       has_data: bool, adt_file: Optional[str] = None,
                       offset: Optional[int] = None, size: Optional[int] = None,
                       async_id: Optional[int] = None, version: int = 0,
                       header_flags: int = 0) -> int:
        """Insert map tile record and return its ID"""
        cursor = self.db.conn.execute(
            """
            INSERT INTO map_tiles (
                map_id, x, y, flags, has_data, adt_file,
                offset, size, async_id, version, header_flags
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (map_id, x, y, flags, has_data, adt_file,
             offset, size, async_id, version, header_flags)
        )
        self.db.conn.commit()
        return cursor.lastrowid

    def track_missing_file(self, map_id: int, file_path: str, reference_file: str) -> None:
        """Track missing file reference"""
        self.db.conn.execute(
            """
            INSERT OR IGNORE INTO missing_files (map_id, file_path, reference_file)
            VALUES (?, ?, ?)
            """,
            (map_id, file_path, reference_file)
        )
        self.db.conn.commit()

    def track_unique_id(self, unique_id: int) -> None:
        """Track unique ID for uid.ini generation"""
        self.unique_ids.add(unique_id)

    def write_uid_ini(self, directory: str) -> None:
        """Write uid.ini file with max unique ID"""
        if self.unique_ids:
            max_uid = max(self.unique_ids)
            ini_path = os.path.join(directory, 'uid.ini')
            with open(ini_path, 'w') as f:
                f.write(f"max_unique_id={max_uid}\n")

    def batch_insert_textures(self, map_id: int, textures: List[Dict[str, Any]]) -> Dict[str, int]:
        """Batch insert textures and return mapping of paths to IDs"""
        texture_ids = {}
        values = [(map_id, tex['path']) for tex in textures]
        
        self.db.conn.executemany(
            """
            INSERT OR IGNORE INTO textures (map_id, path)
            VALUES (?, ?)
            """,
            values
        )
        self.db.conn.commit()
        
        # Get all texture IDs
        cursor = self.db.conn.execute(
            "SELECT id, path FROM textures WHERE map_id = ?",
            (map_id,)
        )
        for row in cursor:
            texture_ids[row[1]] = row[0]
            
        return texture_ids

    def batch_insert_m2_models(self, map_id: int, models: List[str]) -> Dict[str, int]:
        """Batch insert M2 models and return mapping of paths to IDs"""
        model_ids = {}
        values = [(map_id, path) for path in models]
        
        self.db.conn.executemany(
            """
            INSERT OR IGNORE INTO models_m2 (map_id, path)
            VALUES (?, ?)
            """,
            values
        )
        self.db.conn.commit()
        
        # Get all model IDs
        cursor = self.db.conn.execute(
            "SELECT id, path FROM models_m2 WHERE map_id = ?",
            (map_id,)
        )
        for row in cursor:
            model_ids[row[1]] = row[0]
            
        return model_ids

    def batch_insert_wmo_models(self, map_id: int, models: List[str]) -> Dict[str, int]:
        """Batch insert WMO models and return mapping of paths to IDs"""
        model_ids = {}
        values = [(map_id, path) for path in models]
        
        self.db.conn.executemany(
            """
            INSERT OR IGNORE INTO models_wmo (map_id, path)
            VALUES (?, ?)
            """,
            values
        )
        self.db.conn.commit()
        
        # Get all model IDs
        cursor = self.db.conn.execute(
            "SELECT id, path FROM models_wmo WHERE map_id = ?",
            (map_id,)
        )
        for row in cursor:
            model_ids[row[1]] = row[0]
            
        return model_ids

    def batch_insert_m2_placements(self, map_id: int, placements: List[Dict[str, Any]], model_ids: Dict[str, int]) -> None:
        """Batch insert M2 model placements"""
        values = []
        for p in placements:
            if p['model_path'] not in model_ids:
                continue
            self.track_unique_id(p['unique_id'])
            values.append((
                map_id,
                model_ids[p['model_path']],
                p['unique_id'],
                p['position'][0], p['position'][1], p['position'][2],
                p['rotation'][0], p['rotation'][1], p['rotation'][2],
                p['scale'],
                p['flags']
            ))
        
        self.db.conn.executemany(
            """
            INSERT INTO model_placements_m2 (
                map_id, model_id, unique_id,
                pos_x, pos_y, pos_z,
                rot_x, rot_y, rot_z,
                scale, flags
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values
        )
        self.db.conn.commit()

    def batch_insert_wmo_placements(self, map_id: int, placements: List[Dict[str, Any]], model_ids: Dict[str, int]) -> None:
        """Batch insert WMO model placements"""
        values = []
        for p in placements:
            if p['model_path'] not in model_ids:
                continue
            self.track_unique_id(p['unique_id'])
            values.append((
                map_id,
                model_ids[p['model_path']],
                p['unique_id'],
                p['position'][0], p['position'][1], p['position'][2],
                p['rotation'][0], p['rotation'][1], p['rotation'][2],
                p['scale'],
                p['flags'],
                p.get('doodad_set'),
                p.get('name_set'),
                p.get('bounds', {}).get('min', {}).get('x'),
                p.get('bounds', {}).get('min', {}).get('y'),
                p.get('bounds', {}).get('min', {}).get('z'),
                p.get('bounds', {}).get('max', {}).get('x'),
                p.get('bounds', {}).get('max', {}).get('y'),
                p.get('bounds', {}).get('max', {}).get('z')
            ))
        
        self.db.conn.executemany(
            """
            INSERT INTO model_placements_wmo (
                map_id, model_id, unique_id,
                pos_x, pos_y, pos_z,
                rot_x, rot_y, rot_z,
                scale, flags, doodad_set, name_set,
                bounds_min_x, bounds_min_y, bounds_min_z,
                bounds_max_x, bounds_max_y, bounds_max_z
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values
        )
        self.db.conn.commit()

    def batch_insert_terrain_chunks(self, map_id: int, tile_id: int, chunks: List[Dict[str, Any]]) -> Dict[int, int]:
        """Batch insert terrain chunks and return mapping of indices to IDs"""
        chunk_ids = {}
        values = []
        for idx, chunk in enumerate(chunks):
            x = idx % 16
            y = idx // 16
            values.append((
                map_id,
                tile_id,
                x, y,
                chunk['flags'],
                chunk.get('area_id'),
                chunk.get('holes'),
                1 if chunk.get('has_mcvt', False) else 0,
                1 if chunk.get('has_mcnr', False) else 0,
                1 if chunk.get('has_mclq', False) else 0
            ))
        
        cursor = self.db.conn.executemany(
            """
            INSERT INTO terrain_chunks (
                map_id, tile_id, index_x, index_y,
                flags, area_id, holes,
                has_mcvt, has_mcnr, has_mclq
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values
        )
        self.db.conn.commit()
        
        # Get chunk IDs
        cursor = self.db.conn.execute(
            """
            SELECT id, index_x, index_y 
            FROM terrain_chunks 
            WHERE tile_id = ? 
            ORDER BY index_y, index_x
            """,
            (tile_id,)
        )
        for row in cursor:
            idx = row[2] * 16 + row[1]
            chunk_ids[idx] = row[0]
            
        return chunk_ids

    def batch_insert_terrain_heights(self, heights_data: List[Tuple[int, List[float]]]) -> None:
        """Batch insert terrain height values"""
        values = []
        for chunk_id, heights in heights_data:
            values.extend((chunk_id, i, height) for i, height in enumerate(heights))
        
        self.db.conn.executemany(
            """
            INSERT INTO terrain_heights (chunk_id, vertex_index, height)
            VALUES (?, ?, ?)
            """,
            values
        )
        self.db.conn.commit()

    def batch_insert_terrain_layers(self, layers_data: List[Tuple[int, int, int, Optional[int], int]]) -> None:
        """Batch insert terrain layer data"""
        self.db.conn.executemany(
            """
            INSERT INTO terrain_layers (chunk_id, texture_id, flags, effect_id, offset_in_mcal)
            VALUES (?, ?, ?, ?, ?)
            """,
            layers_data
        )
        self.db.conn.commit()

    def batch_insert_vertex_colors(self, colors_data: List[Tuple[int, int, int, int, int, int]]) -> None:
        """Batch insert vertex color data"""
        self.db.conn.executemany(
            """
            INSERT INTO terrain_vertex_colors (chunk_id, vertex_index, r, g, b, a)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            colors_data
        )
        self.db.conn.commit()

    def insert_alpha_map(self, chunk_id: int, data: bytes, is_compressed: bool) -> None:
        """Insert alpha map data"""
        self.db.conn.execute(
            """
            INSERT INTO terrain_alpha_maps (chunk_id, data, is_compressed)
            VALUES (?, ?, ?)
            """,
            (chunk_id, data, is_compressed)
        )
        self.db.conn.commit()

    def process_wdt_data(self, file_path: str, format_type: str,
                        decoded_data: Dict[str, Any]) -> int:
        """Process decoded WDT data and store in database"""
        # Get map name from file path
        map_name = Path(file_path).stem
        
        # Get version and flags
        version = 0
        flags = 0
        chunk_order = ''
        if 'MVER' in decoded_data:
            version = decoded_data['MVER'][0]['version']
        if 'MPHD' in decoded_data:
            flags = decoded_data['MPHD'][0]['flags']
        if 'chunk_order' in decoded_data:
            chunk_order = ','.join(decoded_data['chunk_order'])
        
        # Insert map record
        map_id = self.insert_map(map_name, format_type, version, flags, chunk_order)
        
        # Process model files
        m2_models = []
        wmo_models = []
        
        # Alpha format model names
        if 'MDNM' in decoded_data:
            m2_models = decoded_data['MDNM'][0]['names']
        if 'MONM' in decoded_data:
            wmo_models = decoded_data['MONM'][0]['names']
        
        # Retail format model names
        if 'MMDX' in decoded_data:
            m2_models = decoded_data['MMDX'][0]['names']
        if 'MWMO' in decoded_data:
            wmo_models = decoded_data['MWMO'][0]['names']
        
        # Track missing files
        for model in m2_models:
            if not self._check_file_exists(model):
                self.track_missing_file(map_id, model, file_path)
        for model in wmo_models:
            if not self._check_file_exists(model):
                self.track_missing_file(map_id, model, file_path)
        
        # Batch insert models
        m2_model_ids = self.batch_insert_m2_models(map_id, m2_models)
        wmo_model_ids = self.batch_insert_wmo_models(map_id, wmo_models)
        
        # Process model placements
        if 'MDDF' in decoded_data:
            placements = []
            for entry in decoded_data['MDDF'][0]['entries']:
                model_path = m2_models[entry['nameId']] if entry['nameId'] < len(m2_models) else None
                if model_path:
                    placements.append({
                        'model_path': model_path,
                        'unique_id': entry['uniqueId'],
                        'position': (entry['position']['x'], entry['position']['y'], entry['position']['z']),
                        'rotation': (entry['rotation']['x'], entry['rotation']['y'], entry['rotation']['z']),
                        'scale': entry['scale'],
                        'flags': entry['flags']
                    })
            self.batch_insert_m2_placements(map_id, placements, m2_model_ids)
        
        if 'MODF' in decoded_data:
            placements = []
            for entry in decoded_data['MODF'][0]['entries']:
                model_path = wmo_models[entry['nameId']] if entry['nameId'] < len(wmo_models) else None
                if model_path:
                    placements.append({
                        'model_path': model_path,
                        'unique_id': entry['uniqueId'],
                        'position': (entry['position']['x'], entry['position']['y'], entry['position']['z']),
                        'rotation': (entry['rotation']['x'], entry['rotation']['y'], entry['rotation']['z']),
                        'scale': entry['scale'],
                        'flags': entry['flags'],
                        'doodad_set': entry.get('doodadSet'),
                        'name_set': entry.get('nameSet'),
                        'bounds': entry.get('bounds', {})
                    })
            self.batch_insert_wmo_placements(map_id, placements, wmo_model_ids)
        
        # Process map tiles
        if 'MAIN' in decoded_data:
            main_data = decoded_data['MAIN'][0]
            for y, row in enumerate(main_data['tiles']):
                for x, tile in enumerate(row):
                    tile_id = self.insert_map_tile(
                        map_id, x, y,
                        tile['flags'],
                        tile['has_data'],
                        tile.get('adt_file'),
                        tile.get('offset'),
                        tile.get('size'),
                        tile.get('async_id'),
                        tile.get('version', 0),
                        tile.get('header_flags', 0)
                    )
                    
                    # Process ADT data if available
                    adt_name = f"{map_name}_{x}_{y}.adt"
                    if 'adt_files' in decoded_data and adt_name in decoded_data['adt_files']:
                        self.process_adt_data(
                            map_id,
                            tile_id,
                            decoded_data['adt_files'][adt_name]
                        )
        
        return map_id

    def process_adt_data(self, map_id: int, tile_id: int,
                        decoded_data: Dict[str, Any]) -> None:
        """Process decoded ADT data and store in database"""
        # Process textures
        textures = []
        if 'MTEX' in decoded_data:
            textures = [{'path': path} for path in decoded_data['MTEX'][0]['textures']]
            # Track missing textures
            for tex in textures:
                if not self._check_file_exists(tex['path']):
                    self.track_missing_file(map_id, tex['path'], f"tile_{tile_id}")
                    
        texture_ids = self.batch_insert_textures(map_id, textures)
        
        # Process terrain chunks
        if 'MCNK' in decoded_data:
            # Batch insert chunks
            chunk_ids = self.batch_insert_terrain_chunks(map_id, tile_id, decoded_data['MCNK'])
            
            # Prepare batch data
            heights_data = []
            layers_data = []
            colors_data = []
            
            for chunk_idx, chunk in enumerate(decoded_data['MCNK']):
                chunk_id = chunk_ids[chunk_idx]
                
                # Heights (MCVT)
                if 'heights' in chunk:
                    heights_data.append((chunk_id, chunk['heights']))
                
                # Layers (MCLY)
                if 'layers' in chunk:
                    for layer in chunk['layers']:
                        texture_path = layer['texture_path']
                        if texture_path in texture_ids:
                            layers_data.append((
                                chunk_id,
                                texture_ids[texture_path],
                                layer['flags'],
                                layer.get('effect_id'),
                                layer.get('offset_in_mcal', 0)
                            ))
                
                # Vertex Colors (MCCV)
                if 'vertex_colors' in chunk:
                    for i, color in enumerate(chunk['vertex_colors']):
                        colors_data.append((
                            chunk_id, i,
                            color['r'], color['g'], color['b'], color['a']
                        ))
                
                # Alpha Maps (MCAL)
                if 'alpha_map' in chunk:
                    self.insert_alpha_map(
                        chunk_id,
                        chunk['alpha_map']['data'],
                        chunk['alpha_map'].get('is_compressed', False)
                    )
            
            # Batch insert all data
            if heights_data:
                self.batch_insert_terrain_heights(heights_data)
            if layers_data:
                self.batch_insert_terrain_layers(layers_data)
            if colors_data:
                self.batch_insert_vertex_colors(colors_data)

    def _check_file_exists(self, file_path: str) -> bool:
        """Check if a file exists in the game files"""
        # This would typically check against a listfile or game directory
        # For now, just return True to avoid false positives
        return True

    def close(self):
        """Close database connection"""
        self.db.close()