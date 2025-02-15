"""Database manager for ADT analyzer."""
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import logging

from .schema import ALL_TABLES

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database operations for ADT analyzer."""
    
    def __init__(self, db_path: Path):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def initialize(self) -> None:
        """Initialize database connection and create tables if needed."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # Enable foreign key support
            self.cursor.execute("PRAGMA foreign_keys = ON;")
            
            # Create tables
            for create_table_sql in ALL_TABLES:
                self.cursor.execute(create_table_sql)
                
            self.conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
            
    def store_adt_file(self, filename: str, data: Dict[str, Any]) -> None:
        """Store ADT file and its data in database.
        
        Args:
            filename: Name of the ADT file
            data: Dictionary containing ADT data
        """
        try:
            # Start transaction
            self.cursor.execute("BEGIN TRANSACTION")
            
            # Insert ADT file record
            self.cursor.execute(
                "INSERT INTO adt_files (filename, file_path) VALUES (?, ?)",
                (filename, data.get('file_path', ''))
            )
            adt_file_id = self.cursor.lastrowid
            
            # Store errors if any
            if errors := data.get('errors', []):
                self._store_errors(adt_file_id, errors)
            
            chunks = data.get('chunks', {})
            if not isinstance(chunks, dict):
                logger.warning(f"Unexpected chunks format for {filename}: {type(chunks)}")
                return
                
            # Store version info
            if version_data := chunks.get('version'):
                self._store_version(adt_file_id, version_data)
                
            # Store header info
            if header_data := chunks.get('header'):
                self._store_header(adt_file_id, header_data)
                
            # Store chunk indices
            if chunk_indices := chunks.get('chunk_indices'):
                self._store_chunk_indices(adt_file_id, chunk_indices)
                
            # Store textures
            if textures := chunks.get('textures'):
                self._store_textures(adt_file_id, textures)
                
            # Store M2 models
            if m2_models := chunks.get('m2_models'):
                self._store_m2_models(adt_file_id, m2_models)
                
            # Store WMO models
            if wmo_models := chunks.get('wmo_models'):
                self._store_wmo_models(adt_file_id, wmo_models)
                
            # Store M2 placements
            if m2_placements := chunks.get('m2_placements'):
                self._store_m2_placements(adt_file_id, m2_placements)
                
            # Store WMO placements
            if wmo_placements := chunks.get('wmo_placements'):
                self._store_wmo_placements(adt_file_id, wmo_placements)
                
            # Store terrain chunks
            if terrain_chunks := chunks.get('terrain_chunks', []):
                if isinstance(terrain_chunks, list):
                    self._store_terrain_chunks(adt_file_id, terrain_chunks)
                else:
                    logger.warning(f"Unexpected terrain_chunks format for {filename}: {type(terrain_chunks)}")
            
            # Commit transaction
            self.conn.commit()
            logger.info(f"Stored ADT file {filename} in database")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to store ADT file {filename}: {e}")
            raise
            
    def _store_errors(self, adt_file_id: int, errors: List[str]) -> None:
        """Store error messages for an ADT file."""
        self.cursor.executemany(
            "INSERT INTO errors (adt_file_id, error_message) VALUES (?, ?)",
            [(adt_file_id, str(error)) for error in errors]
        )
        
    def _store_version(self, adt_file_id: int, version_data: Dict[str, Any]) -> None:
        """Store version information."""
        if not isinstance(version_data, dict):
            logger.warning(f"Unexpected version data format: {type(version_data)}")
            return
            
        version = version_data.get('version')
        if version is not None:
            self.cursor.execute(
                "INSERT INTO versions (adt_file_id, version) VALUES (?, ?)",
                (adt_file_id, version)
            )
        
    def _store_header(self, adt_file_id: int, header_data: Dict[str, Any]) -> None:
        """Store header information and offsets."""
        if not isinstance(header_data, dict):
            logger.warning(f"Unexpected header data format: {type(header_data)}")
            return
            
        flags = header_data.get('flags', {})
        if not isinstance(flags, dict):
            logger.warning(f"Unexpected flags format: {type(flags)}")
            return
            
        self.cursor.execute(
            """INSERT INTO headers (
                adt_file_id, flags, has_mfbo, has_mh2o, has_mtxf,
                use_big_alpha, use_big_textures, use_mcsh
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                adt_file_id,
                flags.get('raw_value', 0),
                flags.get('has_mfbo', False),
                flags.get('has_mh2o', False),
                flags.get('has_mtxf', False),
                flags.get('use_big_alpha', False),
                flags.get('use_big_textures', False),
                flags.get('use_mcsh', False)
            )
        )
        header_id = self.cursor.lastrowid
        
        offsets = header_data.get('offsets', {})
        if not isinstance(offsets, dict):
            logger.warning(f"Unexpected offsets format: {type(offsets)}")
            return
            
        self.cursor.execute(
            """INSERT INTO header_offsets (
                header_id, mcin, mtex, mmdx, mmid, mwmo, mwid,
                mddf, modf, mfbo, mh2o, mtxf
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                header_id,
                offsets.get('mcin', 0),
                offsets.get('mtex', 0),
                offsets.get('mmdx', 0),
                offsets.get('mmid', 0),
                offsets.get('mwmo', 0),
                offsets.get('mwid', 0),
                offsets.get('mddf', 0),
                offsets.get('modf', 0),
                offsets.get('mfbo', 0),
                offsets.get('mh2o', 0),
                offsets.get('mtxf', 0)
            )
        )
        
    def _store_chunk_indices(self, adt_file_id: int, indices_data: Dict[str, Any]) -> None:
        """Store chunk indices information."""
        if not isinstance(indices_data, dict):
            logger.warning(f"Unexpected indices data format: {type(indices_data)}")
            return
            
        self.cursor.execute(
            """INSERT INTO chunk_indices (
                adt_file_id, count, valid_chunks
            ) VALUES (?, ?, ?)""",
            (
                adt_file_id,
                indices_data.get('count', 0),
                indices_data.get('valid_chunks', 0)
            )
        )
        indices_id = self.cursor.lastrowid
        
        # Store entries
        entries = indices_data.get('entries', [])
        if not isinstance(entries, list):
            logger.warning(f"Unexpected entries format: {type(entries)}")
            return
            
        for entry in entries:
            if not isinstance(entry, dict):
                continue
                
            try:
                self.cursor.execute(
                    """INSERT INTO chunk_index_entries (
                        chunk_indices_id, entry_index, offset, size,
                        flags, async_id, grid_x, grid_y
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        indices_id,
                        entry.get('index', 0),
                        entry.get('offset', 0),
                        entry.get('size', 0),
                        entry.get('flags', 0),
                        entry.get('async_id', 0),
                        entry.get('grid_position', [0, 0])[0],
                        entry.get('grid_position', [0, 0])[1]
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to store chunk index entry: {e}")
        
    def _store_textures(self, adt_file_id: int, textures_data: Dict[str, Any]) -> None:
        """Store texture information."""
        if not isinstance(textures_data, dict):
            logger.warning(f"Unexpected textures data format: {type(textures_data)}")
            return
            
        self.cursor.execute(
            "INSERT INTO textures (adt_file_id, count) VALUES (?, ?)",
            (adt_file_id, textures_data.get('count', 0))
        )
        textures_id = self.cursor.lastrowid
        
        # Store texture entries
        textures = textures_data.get('textures', [])
        if isinstance(textures, list):
            self.cursor.executemany(
                "INSERT INTO texture_entries (textures_id, texture_path) VALUES (?, ?)",
                [(textures_id, str(texture)) for texture in textures]
            )
        
    def _store_m2_models(self, adt_file_id: int, models_data: Dict[str, Any]) -> None:
        """Store M2 model information."""
        if not isinstance(models_data, dict):
            logger.warning(f"Unexpected M2 models data format: {type(models_data)}")
            return
            
        self.cursor.execute(
            """INSERT INTO m2_models (
                adt_file_id, count, data_size
            ) VALUES (?, ?, ?)""",
            (
                adt_file_id,
                models_data.get('count', 0),
                models_data.get('data_size', 0)
            )
        )
        models_id = self.cursor.lastrowid
        
        # Store model entries
        models = models_data.get('models', [])
        if not isinstance(models, list):
            logger.warning(f"Unexpected models format: {type(models)}")
            return
            
        for i, model in enumerate(models):
            if not isinstance(model, dict):
                continue
                
            try:
                self.cursor.execute(
                    """INSERT INTO m2_model_entries (
                        m2_models_id, model_index, offset, name
                    ) VALUES (?, ?, ?, ?)""",
                    (
                        models_id,
                        i,
                        model.get('offset', 0),
                        str(model.get('name', ''))
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to store M2 model entry: {e}")
        
    def _store_wmo_models(self, adt_file_id: int, models_data: Dict[str, Any]) -> None:
        """Store WMO model information."""
        if not isinstance(models_data, dict):
            logger.warning(f"Unexpected WMO models data format: {type(models_data)}")
            return
            
        self.cursor.execute(
            """INSERT INTO wmo_models (
                adt_file_id, count, data_size
            ) VALUES (?, ?, ?)""",
            (
                adt_file_id,
                models_data.get('count', 0),
                models_data.get('data_size', 0)
            )
        )
        models_id = self.cursor.lastrowid
        
        # Store model entries
        wmos = models_data.get('wmos', [])
        if not isinstance(wmos, list):
            logger.warning(f"Unexpected WMOs format: {type(wmos)}")
            return
            
        for i, wmo in enumerate(wmos):
            if not isinstance(wmo, dict):
                continue
                
            try:
                self.cursor.execute(
                    """INSERT INTO wmo_model_entries (
                        wmo_models_id, model_index, offset, name
                    ) VALUES (?, ?, ?, ?)""",
                    (
                        models_id,
                        i,
                        wmo.get('offset', 0),
                        str(wmo.get('name', ''))
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to store WMO model entry: {e}")
        
    def _store_m2_placements(self, adt_file_id: int, placement_data: Dict[str, Any]) -> None:
        """Store M2 model placement information."""
        if not isinstance(placement_data, dict):
            logger.warning(f"Unexpected M2 placement data format: {type(placement_data)}")
            return
            
        self.cursor.execute(
            """INSERT INTO m2_placements (
                adt_file_id, count, valid_entries
            ) VALUES (?, ?, ?)""",
            (
                adt_file_id,
                placement_data.get('count', 0),
                placement_data.get('valid_entries', 0)
            )
        )
        placements_id = self.cursor.lastrowid
        
        # Store placement entries
        entries = placement_data.get('entries', [])
        if not isinstance(entries, list):
            logger.warning(f"Unexpected entries format: {type(entries)}")
            return
            
        for entry in entries:
            if not isinstance(entry, dict):
                continue
                
            try:
                position = entry.get('position', {})
                rotation = entry.get('rotation', {})
                
                self.cursor.execute(
                    """INSERT INTO m2_placement_entries (
                        m2_placements_id, entry_index, mmid_entry, unique_id,
                        position_x, position_y, position_z,
                        rotation_x, rotation_y, rotation_z,
                        scale, flags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        placements_id,
                        entry.get('index', 0),
                        entry.get('mmid_entry', 0),
                        entry.get('unique_id', 0),
                        position.get('x', 0.0),
                        position.get('y', 0.0),
                        position.get('z', 0.0),
                        rotation.get('x', 0.0),
                        rotation.get('y', 0.0),
                        rotation.get('z', 0.0),
                        entry.get('scale', 1.0),
                        entry.get('flags', 0)
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to store M2 placement entry: {e}")
        
    def _store_wmo_placements(self, adt_file_id: int, placement_data: Dict[str, Any]) -> None:
        """Store WMO model placement information."""
        if not isinstance(placement_data, dict):
            logger.warning(f"Unexpected WMO placement data format: {type(placement_data)}")
            return
            
        self.cursor.execute(
            """INSERT INTO wmo_placements (
                adt_file_id, count, valid_entries
            ) VALUES (?, ?, ?)""",
            (
                adt_file_id,
                placement_data.get('count', 0),
                placement_data.get('valid_entries', 0)
            )
        )
        placements_id = self.cursor.lastrowid
        
        # Store placement entries
        entries = placement_data.get('entries', [])
        if not isinstance(entries, list):
            logger.warning(f"Unexpected entries format: {type(entries)}")
            return
            
        for entry in entries:
            if not isinstance(entry, dict):
                continue
                
            try:
                position = entry.get('position', {})
                rotation = entry.get('rotation', {})
                bounds = entry.get('bounds', {})
                bounds_min = bounds.get('min', {})
                bounds_max = bounds.get('max', {})
                
                self.cursor.execute(
                    """INSERT INTO wmo_placement_entries (
                        wmo_placements_id, entry_index, mwid_entry, unique_id,
                        position_x, position_y, position_z,
                        rotation_x, rotation_y, rotation_z,
                        bounds_min_x, bounds_min_y, bounds_min_z,
                        bounds_max_x, bounds_max_y, bounds_max_z,
                        flags, doodad_set, name_set, scale
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        placements_id,
                        entry.get('index', 0),
                        entry.get('mwid_entry', 0),
                        entry.get('unique_id', 0),
                        position.get('x', 0.0),
                        position.get('y', 0.0),
                        position.get('z', 0.0),
                        rotation.get('x', 0.0),
                        rotation.get('y', 0.0),
                        rotation.get('z', 0.0),
                        bounds_min.get('x', 0.0),
                        bounds_min.get('y', 0.0),
                        bounds_min.get('z', 0.0),
                        bounds_max.get('x', 0.0),
                        bounds_max.get('y', 0.0),
                        bounds_max.get('z', 0.0),
                        entry.get('flags', 0),
                        entry.get('doodad_set', 0),
                        entry.get('name_set', 0),
                        entry.get('scale', 1.0)
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to store WMO placement entry: {e}")
        
    def _store_terrain_chunks(self, adt_file_id: int, chunks: List[Dict[str, Any]]) -> None:
        """Store terrain chunk information."""
        if not isinstance(chunks, list):
            logger.warning(f"Unexpected terrain chunks format: {type(chunks)}")
            return
            
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
                
            try:
                # Store chunk header
                header = chunk.get('header', {})
                if not isinstance(header, dict):
                    continue
                    
                position = header.get('position', [0, 0])
                if not isinstance(position, list) or len(position) < 2:
                    position = [0, 0]
                    
                self.cursor.execute(
                    """INSERT INTO terrain_chunks (
                        adt_file_id, grid_x, grid_y, area_id,
                        flags, holes, liquid_level
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        adt_file_id,
                        position[0],
                        position[1],
                        header.get('area_id', 0),
                        header.get('flags', 0),
                        header.get('holes', 0),
                        header.get('liquid_level', 0.0)
                    )
                )
                chunk_id = self.cursor.lastrowid
                
                # Store heights
                heights = chunk.get('heights', [])
                if isinstance(heights, list):
                    self.cursor.executemany(
                        """INSERT INTO terrain_heights (
                            terrain_chunk_id, vertex_index, height
                        ) VALUES (?, ?, ?)""",
                        [(chunk_id, i, height) for i, height in enumerate(heights)]
                    )
                
                # Store normals
                normals = chunk.get('normals', [])
                if isinstance(normals, list):
                    normal_data = []
                    for i, normal in enumerate(normals):
                        if isinstance(normal, list) and len(normal) >= 3:
                            normal_data.append((chunk_id, i, normal[0], normal[1], normal[2]))
                            
                    if normal_data:
                        self.cursor.executemany(
                            """INSERT INTO terrain_normals (
                                terrain_chunk_id, normal_index, x, y, z
                            ) VALUES (?, ?, ?, ?, ?)""",
                            normal_data
                        )
                        
            except Exception as e:
                logger.warning(f"Failed to store terrain chunk: {e}")
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None