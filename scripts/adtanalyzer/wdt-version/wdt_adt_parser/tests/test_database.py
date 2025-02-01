"""
Tests for database functionality
"""
import unittest
import tempfile
from pathlib import Path
import sqlite3

from ..database.manager import DatabaseManager
from ..database.schema import DatabaseSchema

class TestDatabase(unittest.TestCase):
    """Test database functionality"""
    
    def setUp(self):
        """Set up test database"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = DatabaseManager(self.db_path)
    
    def tearDown(self):
        """Clean up test database"""
        if self.db:
            self.db.close()
        if self.db_path.exists():
            self.db_path.unlink()
    
    def test_schema_creation(self):
        """Test database schema creation"""
        # Verify all tables exist
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        expected_tables = {
            'wdt_files',
            'chunk_offsets',
            'adt_offsets',
            'map_tiles',
            'tile_mcnk',
            'tile_layers',
            'wdt_textures',
            'm2_models',
            'wmo_models',
            'm2_placements',
            'height_map_info',
            'liquid_data',
            'wmo_placements'
        }
        
        self.assertEqual(tables, expected_tables)
    
    def test_wdt_record_insertion(self):
        """Test WDT record insertion"""
        wdt_id = self.db.insert_wdt_record(
            filename="test.wdt",
            map_name="TestMap",
            version=18,
            flags=0x1,
            is_wmo_based=False,
            chunk_order="MVER,MPHD,MAIN",
            original_format="alpha"
        )
        
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM wdt_files WHERE id = ?", (wdt_id,))
        record = cursor.fetchone()
        
        self.assertIsNotNone(record)
        self.assertEqual(record[1], "test.wdt")  # filename
        self.assertEqual(record[2], "TestMap")   # map_name
        self.assertEqual(record[3], 18)          # version
        self.assertEqual(record[4], 0x1)         # flags
        self.assertEqual(record[5], 0)           # is_wmo_based
        self.assertEqual(record[6], "MVER,MPHD,MAIN")  # chunk_order
        self.assertEqual(record[7], "alpha")     # original_format
    
    def test_model_and_placement(self):
        """Test model and placement insertion"""
        # Insert WDT record first
        wdt_id = self.db.insert_wdt_record(
            filename="test.wdt",
            map_name="TestMap",
            version=18,
            flags=0x1
        )
        
        # Insert M2 model
        model_id = self.db.insert_m2_model(
            wdt_id=wdt_id,
            tile_x=0,
            tile_y=0,
            model_path="test_model.m2",
            format_type="alpha"
        )
        
        # Insert M2 placement
        placement_id = self.db.insert_m2_placement(
            wdt_id=wdt_id,
            tile_x=0,
            tile_y=0,
            model_id=model_id,
            unique_id=1,
            position=(1.0, 2.0, 3.0),
            rotation=(0.0, 0.0, 0.0),
            scale=1.0,
            flags=0
        )
        
        cursor = self.db.conn.cursor()
        
        # Verify model
        cursor.execute("SELECT * FROM m2_models WHERE id = ?", (model_id,))
        model = cursor.fetchone()
        self.assertIsNotNone(model)
        self.assertEqual(model[4], "test_model.m2")  # model_path
        
        # Verify placement
        cursor.execute("SELECT * FROM m2_placements WHERE id = ?", (placement_id,))
        placement = cursor.fetchone()
        self.assertIsNotNone(placement)
        self.assertEqual(placement[6], 1.0)  # position_x
        self.assertEqual(placement[7], 2.0)  # position_y
        self.assertEqual(placement[8], 3.0)  # position_z
    
    def test_texture_and_layer(self):
        """Test texture and layer insertion"""
        # Insert WDT record
        wdt_id = self.db.insert_wdt_record(
            filename="test.wdt",
            map_name="TestMap",
            version=18,
            flags=0x1
        )
        
        # Insert MCNK record
        mcnk_id = self.db.insert_tile_mcnk(
            wdt_id=wdt_id,
            tile_x=0,
            tile_y=0,
            mcnk_data={
                'flags': 0,
                'n_layers': 1,
                'n_doodad_refs': 0,
                'mcvt_offset': 0,
                'mcnr_offset': 0,
                'mcly_offset': 0,
                'mcrf_offset': 0,
                'mcal_offset': 0,
                'mcsh_offset': 0,
                'mclq_offset': 0,
                'area_id': 0,
                'holes': 0
            }
        )
        
        # Insert texture
        texture_id = self.db.insert_texture(
            wdt_id=wdt_id,
            tile_x=0,
            tile_y=0,
            texture_path="test_texture.blp",
            layer_index=0,
            blend_mode=1,
            has_alpha=1
        )
        
        # Insert layer
        layer_id = self.db.insert_tile_layer(
            tile_mcnk_id=mcnk_id,
            layer_index=0,
            texture_id=texture_id,
            flags=0,
            effect_id=0
        )
        
        cursor = self.db.conn.cursor()
        
        # Verify texture
        cursor.execute("SELECT * FROM wdt_textures WHERE id = ?", (texture_id,))
        texture = cursor.fetchone()
        self.assertIsNotNone(texture)
        self.assertEqual(texture[4], "test_texture.blp")  # texture_path
        
        # Verify layer
        cursor.execute("SELECT * FROM tile_layers WHERE id = ?", (layer_id,))
        layer = cursor.fetchone()
        self.assertIsNotNone(layer)
        self.assertEqual(layer[1], mcnk_id)     # tile_mcnk_id
        self.assertEqual(layer[3], texture_id)  # texture_id

if __name__ == '__main__':
    unittest.main()