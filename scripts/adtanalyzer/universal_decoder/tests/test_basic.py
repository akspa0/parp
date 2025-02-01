"""
Basic tests for the universal WoW map file decoder
"""

import os
import sys
import json
import struct
import pytest
import sqlite3
from pathlib import Path
from typing import Tuple

# Add the parent directory to sys.path to allow direct imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.format_detector import FormatDetector, FileFormat, FileType
from src.base.chunk_parser import ChunkParsingError
from src.formats.alpha.wdt_parser import AlphaWDTParser
from src.formats.alpha.adt_parser import AlphaADTParser
from src.formats.retail.wdt_parser import RetailWDTParser
from src.formats.retail.adt_parser import RetailADTParser
from src.database.operations import DatabaseOperations
from src.output.json_handler import JSONOutputHandler

# Test data paths relative to the test file location
TEST_DATA_DIR = Path(__file__).parent / "test_data"
ALPHA_WDT = TEST_DATA_DIR / "alpha" / "test.wdt"
ALPHA_ADT = TEST_DATA_DIR / "alpha" / "test_30_30.adt"
RETAIL_WDT = TEST_DATA_DIR / "retail" / "test.wdt"
RETAIL_ADT = TEST_DATA_DIR / "retail" / "test_30_30.adt"

@pytest.fixture
def db_ops(tmp_path):
    """Create a temporary database operations instance"""
    db_path = tmp_path / "test.db"
    ops = DatabaseOperations(str(db_path))
    yield ops
    ops.close()

def create_test_chunk(name: bytes, data: bytes, reversed: bool = False) -> bytes:
    """Create a test chunk with the given name and data"""
    chunk_name = name[::-1] if reversed else name
    size = len(data)
    return chunk_name + size.to_bytes(4, 'little') + data

def create_mcnk_chunk(flags: int, x: int, y: int, area_id: int) -> bytes:
    """Create an MCNK chunk with header and subchunks"""
    # Create header
    header = struct.pack('<IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII',
        flags,      # Flags
        x,          # Index X
        y,          # Index Y
        8,          # Layers
        0,          # Doodad refs
        area_id,    # Area ID
        0,          # Holes
        0x1000,     # Low quality texture file offset
        0x2000,     # Height map offset
        0x3000,     # Normal map offset
        0x4000,     # Shadow map offset
        0x5000,     # Layer offset
        0x6000,     # Reference offset
        0,          # Detail file offset
        0,          # Detail layers
        0,          # First light ref
        0,          # Light refs count
        0,          # Flags2
        0,          # Surface shader ID
        0,          # Fog indices
        0,          # Liquid type
        0,          # Max limit
        x * 100,    # Position X
        y * 100,    # Position Y
        0,          # Position Z
        0,          # Map object ref
        0,          # Holes high-res
        0,          # Predtex layer count
        0,          # Noeffect layer count
        0,          # Render flags
        0,          # Root node
        0,          # Node count
        0,          # Reserved1
        0,          # Reserved2
        0,          # Reserved3
        0           # Reserved4
    ) + b'\x00' * 8  # Padding to reach 136 bytes

    # Create MCVT subchunk
    mcvt_data = struct.pack('<145f', *([0.0] * 145))  # Height map data
    mcvt_chunk = create_test_chunk(b'MCVT', mcvt_data)

    # Combine header and subchunks
    return create_test_chunk(b'MCNK', header + mcvt_chunk)

class TestFormatDetection:
    """Test format detection functionality"""

    def test_detect_alpha_wdt(self):
        """Test detection of Alpha WDT files"""
        # Create test data with MDNM chunk
        test_data = create_test_chunk(b'MVER', struct.pack('<I', 17))  # Version 17 for alpha
        test_data += create_test_chunk(b'MDNM', b'test.m2\x00')
        
        # Write test data to a temporary file
        with open(ALPHA_WDT, 'wb') as f:
            f.write(test_data)
        
        detector = FormatDetector(ALPHA_WDT)
        file_type, format_type, reversed_chunks = detector.detect_format()
        
        assert file_type == FileType.WDT
        assert format_type == FileFormat.ALPHA
        assert not reversed_chunks

    def test_detect_retail_adt(self):
        """Test detection of Retail ADT files"""
        # Create test data with MMDX chunk
        test_data = create_test_chunk(b'MVER', struct.pack('<I', 18))  # Version 18 for retail
        test_data += create_test_chunk(b'MMDX', b'test.m2\x00')
        
        # Write test data to a temporary file
        with open(RETAIL_ADT, 'wb') as f:
            f.write(test_data)
        
        detector = FormatDetector(RETAIL_ADT)
        file_type, format_type, reversed_chunks = detector.detect_format()
        
        assert file_type == FileType.ADT
        assert format_type == FileFormat.RETAIL
        assert not reversed_chunks

class TestDatabaseOperations:
    """Test database operations"""

    def test_map_insertion(self, db_ops):
        """Test inserting map records"""
        map_id = db_ops.insert_map('test', 'RETAIL', 18, 0, 'MVER,MPHD,MAIN')
        assert map_id > 0
        
        cursor = db_ops.db.conn.execute("SELECT * FROM maps WHERE id = ?", (map_id,))
        result = cursor.fetchone()
        assert result['name'] == 'test'
        assert result['format'] == 'RETAIL'
        assert result['version'] == 18
        assert result['chunk_order'] == 'MVER,MPHD,MAIN'

    def test_map_tile_insertion(self, db_ops):
        """Test inserting map tile records"""
        map_id = db_ops.insert_map('test', 'RETAIL', 18, 0)
        tile_id = db_ops.insert_map_tile(
            map_id, 30, 30, 0, True,
            'test_30_30.adt', 0, 1000, 1, 18, 0x1
        )
        assert tile_id > 0
        
        cursor = db_ops.db.conn.execute("SELECT * FROM map_tiles WHERE id = ?", (tile_id,))
        result = cursor.fetchone()
        assert result['x'] == 30
        assert result['y'] == 30
        assert result['version'] == 18
        assert result['header_flags'] == 0x1

    def test_terrain_chunk_insertion(self, db_ops):
        """Test inserting terrain chunk records"""
        map_id = db_ops.insert_map('test', 'RETAIL', 18, 0)
        tile_id = db_ops.insert_map_tile(map_id, 30, 30, 0, True)
        
        chunks = [
            {
                'flags': 0x1,
                'area_id': 1,
                'holes': 0,
                'has_mcvt': True,
                'has_mcnr': True,
                'has_mclq': False
            }
        ]
        
        chunk_ids = db_ops.batch_insert_terrain_chunks(map_id, tile_id, chunks)
        assert len(chunk_ids) == 1
        
        cursor = db_ops.db.conn.execute("SELECT * FROM terrain_chunks WHERE id = ?", (chunk_ids[0],))
        result = cursor.fetchone()
        assert result['flags'] == 0x1
        assert result['has_mcvt'] == 1
        assert result['has_mcnr'] == 1
        assert result['has_mclq'] == 0

    def test_vertex_colors_insertion(self, db_ops):
        """Test inserting vertex color records"""
        map_id = db_ops.insert_map('test', 'RETAIL', 18, 0)
        tile_id = db_ops.insert_map_tile(map_id, 30, 30, 0, True)
        chunk_id = db_ops.batch_insert_terrain_chunks(map_id, tile_id, [{'flags': 0}])[0]
        
        colors_data = [
            (chunk_id, 0, 255, 128, 64, 255),
            (chunk_id, 1, 128, 255, 64, 255)
        ]
        
        db_ops.batch_insert_vertex_colors(colors_data)
        
        cursor = db_ops.db.conn.execute("SELECT * FROM terrain_vertex_colors WHERE chunk_id = ?", (chunk_id,))
        results = cursor.fetchall()
        assert len(results) == 2
        assert results[0]['r'] == 255
        assert results[1]['g'] == 255

    def test_alpha_map_insertion(self, db_ops):
        """Test inserting alpha map records"""
        map_id = db_ops.insert_map('test', 'RETAIL', 18, 0)
        tile_id = db_ops.insert_map_tile(map_id, 30, 30, 0, True)
        chunk_id = db_ops.batch_insert_terrain_chunks(map_id, tile_id, [{'flags': 0}])[0]
        
        test_data = bytes([0xFF] * 64)
        db_ops.insert_alpha_map(chunk_id, test_data, True)
        
        cursor = db_ops.db.conn.execute("SELECT * FROM terrain_alpha_maps WHERE chunk_id = ?", (chunk_id,))
        result = cursor.fetchone()
        assert result['is_compressed'] == 1
        assert result['data'] == test_data

    def test_wmo_placement_with_bounds(self, db_ops):
        """Test inserting WMO placements with bounds"""
        map_id = db_ops.insert_map('test', 'RETAIL', 18, 0)
        model_ids = db_ops.batch_insert_wmo_models(map_id, ['test.wmo'])
        
        placements = [{
            'model_path': 'test.wmo',
            'unique_id': 1,
            'position': (100.0, 200.0, 300.0),
            'rotation': (0.0, 0.0, 0.0),
            'scale': 1.0,
            'flags': 0,
            'doodad_set': 0,
            'name_set': 0,
            'bounds': {
                'min': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                'max': {'x': 10.0, 'y': 10.0, 'z': 10.0}
            }
        }]
        
        db_ops.batch_insert_wmo_placements(map_id, placements, model_ids)
        
        cursor = db_ops.db.conn.execute("SELECT * FROM model_placements_wmo")
        result = cursor.fetchone()
        assert result['bounds_min_x'] == 0.0
        assert result['bounds_max_x'] == 10.0

    def test_missing_file_tracking(self, db_ops):
        """Test missing file tracking"""
        map_id = db_ops.insert_map('test', 'RETAIL', 18, 0)
        db_ops.track_missing_file(map_id, 'missing.m2', 'test_30_30.adt')
        
        cursor = db_ops.db.conn.execute("SELECT * FROM missing_files WHERE map_id = ?", (map_id,))
        result = cursor.fetchone()
        assert result['file_path'] == 'missing.m2'
        assert result['reference_file'] == 'test_30_30.adt'

    def test_uid_tracking(self, db_ops, tmp_path):
        """Test unique ID tracking and uid.ini generation"""
        db_ops.track_unique_id(100)
        db_ops.track_unique_id(200)
        db_ops.write_uid_ini(str(tmp_path))
        
        uid_path = tmp_path / 'uid.ini'
        assert uid_path.exists()
        
        with open(uid_path) as f:
            content = f.read()
            assert 'max_unique_id=200' in content

class TestErrorHandling:
    """Test error handling"""

    def test_invalid_chunk_size(self):
        """Test handling of invalid chunk sizes"""
        with pytest.raises(ChunkParsingError):
            # Create invalid test data with bad chunk size
            test_data = create_test_chunk(b'MVER', b'\x00\x00\x00\x00')
            test_data += b'MMDX' + b'\xFF\xFF\xFF\xFF'  # Invalid size
            
            parser = RetailWDTParser(str(ALPHA_WDT))
            with parser:
                parser.parse()

    def test_missing_required_chunks(self):
        """Test handling of missing required chunks"""
        with pytest.raises(ChunkParsingError):
            # Create test data without required chunks
            test_data = create_test_chunk(b'MVER', b'\x00\x00\x00\x00')
            # Missing MAIN chunk
            
            parser = RetailWDTParser(str(ALPHA_WDT))
            with parser:
                parser.parse()

class TestDecoding:
    """Test actual file decoding and database output"""

    def test_alpha_wdt_decoding(self, tmp_path):
        """Test decoding of Alpha WDT file with verification of output"""
        # Create test WDT with multiple chunks
        test_data = (
            create_test_chunk(b'MVER', struct.pack('<I', 17)) +  # Version 17 for alpha
            create_test_chunk(b'MPHD', b'\x00' * 128) +  # 128-byte header for alpha
            create_test_chunk(b'MAIN', struct.pack('<II', 64, 64)) +  # 64x64 map size
            create_test_chunk(b'MDNM', b'World\\Model\\test.m2\x00') +  # Model filename
            create_test_chunk(b'MONM', b'World\\Model\\test.wmo\x00')   # WMO filename
        )
        
        wdt_path = ALPHA_WDT
        with open(wdt_path, 'wb') as f:
            f.write(test_data)
            
        # Create database
        db_path = tmp_path / "test_alpha.db"
        db_ops = DatabaseOperations(str(db_path))
        
        # Parse WDT file
        parser = AlphaWDTParser(str(wdt_path))
        with parser:
            result = parser.parse()
            
        # Save to database
        map_id = db_ops.insert_map(
            name=os.path.basename(wdt_path),
            format_type='ALPHA',
            version=17,
            flags=0
        )
        
        # Insert model references separately for M2 and WMO models
        m2_models = result.get('m2_models', [])
        wmo_models = result.get('wmo_models', [])
        m2_model_ids = db_ops.batch_insert_m2_models(map_id, m2_models)
        wmo_model_ids = db_ops.batch_insert_wmo_models(map_id, wmo_models)
            
        # Verify database content
        cursor = db_ops.db.conn.execute("SELECT * FROM maps")
        map_record = cursor.fetchone()
        assert map_record is not None
        assert map_record['format'] == 'ALPHA'
        assert map_record['version'] == 17
        
        # Check M2 model references
        cursor = db_ops.db.conn.execute("SELECT * FROM models_m2")
        m2_models = cursor.fetchall()
        assert len(m2_models) == 1
        assert m2_models[0]['path'] == 'World\\Model\\test.m2'

        # Check WMO model references
        cursor = db_ops.db.conn.execute("SELECT * FROM models_wmo")
        wmo_models = cursor.fetchall()
        assert len(wmo_models) == 1
        assert wmo_models[0]['path'] == 'World\\Model\\test.wmo'
        
        # Save to JSON
        json_handler = JSONOutputHandler(str(tmp_path))
        json_path = json_handler.write_wdt_data(
            file_path=str(wdt_path),
            format_type='ALPHA',
            data=result
        )
        
        # Verify JSON content
        with open(json_path) as f:
            json_data = json.load(f)
            assert json_data['metadata']['format'] == 'ALPHA'
            assert json_data['decoded_chunks']['m2_models'][0] == 'World\\Model\\test.m2'
            assert json_data['decoded_chunks']['wmo_models'][0] == 'World\\Model\\test.wmo'

    def test_retail_adt_decoding(self, tmp_path):
        """Test decoding of Retail ADT file with verification of output"""
        # Create test ADT with multiple chunks including terrain data
        # Create MCNK header
        mcnk_header = struct.pack('<IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII',
            0x1,        # Flags
            0,          # Index X
            0,          # Index Y
            8,          # Layers
            0,          # Doodad refs
            0x200,      # Area ID
            0,          # Holes
            0x1000,     # Low quality texture file offset
            0x2000,     # Height map offset
            0x3000,     # Normal map offset
            0x4000,     # Shadow map offset
            0x5000,     # Layer offset
            0x6000,     # Reference offset
            0,          # Detail file offset
            0,          # Detail layers
            0,          # First light ref
            0,          # Light refs count
            0,          # Flags2
            0,          # Surface shader ID
            0,          # Fog indices
            0,          # Liquid type
            0,          # Max limit
            0,          # Position X
            0,          # Position Y
            0,          # Position Z
            0,          # Map object ref
            0,          # Holes high-res
            0,          # Predtex layer count
            0,          # Noeffect layer count
            0,          # Render flags
            0,          # Root node
            0,          # Node count
            0,          # Reserved1
            0,          # Reserved2
            0,          # Reserved3
            0           # Reserved4
        ) + b'\x00' * 8  # Padding to reach 136 bytes

        # Create MCVT subchunk
        mcvt_data = struct.pack('<145f', *([0.0] * 145))  # Height map data
        mcvt_chunk = create_test_chunk(b'MCVT', mcvt_data)

        # Combine header and subchunks
        mcnk_data = mcnk_header + mcvt_chunk

        # Create complete test data
        test_data = (
            create_test_chunk(b'MVER', struct.pack('<I', 18)) +  # Version 18 for retail
            create_test_chunk(b'MHDR', struct.pack('<IIIIIIII', 0, 0, 0, 0, 0, 0, 0, 0)) +
            create_mcnk_chunk(0x1, 0, 0, 0x200)  # flags=0x1, x=0, y=0, area_id=0x200
=======
            create_test_chunk(b'MCNK',
                struct.pack('<IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII',
                    0x1,        # Flags
                    0,          # Index X
                    0,          # Index Y
                    8,          # Layers
                    0,          # Doodad refs
                    0x200,      # Area ID
                    0,          # Holes
                    0x1000,     # Low quality texture file offset
                    0x2000,     # Height map offset
                    0x3000,     # Normal map offset
                    0x4000,     # Shadow map offset
                    0x5000,     # Layer offset
                    0x6000,     # Reference offset
                    0,          # Detail file offset
                    0,          # Detail layers
                    0,          # First light ref
                    0,          # Light refs count
                    0,          # Flags2
                    0,          # Surface shader ID
                    0,          # Fog indices
                    0,          # Liquid type
                    0,          # Max limit
                    0,          # Position X
                    0,          # Position Y
                    0,          # Position Z
                    0,          # Map object ref
                    0,          # Holes high-res
                    0,          # Predtex layer count
                    0,          # Noeffect layer count
                    0,          # Render flags
                    0,          # Root node
                    0,          # Node count
                    0,          # Reserved1
                    0,          # Reserved2
                    0,          # Reserved3
                    0           # Reserved4
                ) + b'\x00' * 8    # Padding to reach 136 bytes
            ) +
            # Add MCVT subchunk
            create_test_chunk(b'MCVT', struct.pack('<145f', *([0.0] * 145)))  # Height map data
                    0x1,        # Flags
                    0,          # Index X
                    0,          # Index Y
                    8,          # Layers
                    0,          # Doodad refs
                    0x200,      # Area ID
                    0,          # Holes
                    0x1000,     # Low quality texture file offset
                    0x2000,     # Height map offset
                    0x3000,     # Normal map offset
                    0x4000,     # Shadow map offset
                    0x5000,     # Layer offset
                    0x6000,     # Reference offset
                    0,          # Detail file offset
                    0,          # Detail layers
                    0,          # First light ref
                    0,          # Light refs count
                    0,          # Flags2
                    0,          # Surface shader ID
                    0,          # Fog indices
                    0,          # Liquid type
                    0,          # Max limit
                    0,          # Position X
                    0,          # Position Y
                    0,          # Position Z
                    0,          # Map object ref
                    0,          # Holes high-res
                    0,          # Predtex layer count
                    0,          # Noeffect layer count
                    0,          # Render flags
                    0,          # Root node
                    0,          # Node count
                    0,          # Reserved1
                    0,          # Reserved2
                    0,          # Reserved3
                    0           # Reserved4
                ) + b'\x00' * 8    # Padding to reach 136 bytes
            )
        )
        
        adt_path = RETAIL_ADT
        with open(adt_path, 'wb') as f:
            f.write(test_data)
            
        # Create database
        db_path = tmp_path / "test_retail.db"
        db_ops = DatabaseOperations(str(db_path))
        
        # Parse ADT file
        parser = RetailADTParser(str(adt_path))
        with parser:
            result = parser.parse()
            
        # Save to database
        map_id = db_ops.insert_map(
            name=os.path.basename(adt_path),
            format_type='RETAIL',
            version=18,
            flags=0
        )
        
        # Insert map tile
        tile_id = db_ops.insert_map_tile(
            map_id=map_id,
            x=30,
            y=30,
            flags=0,
            has_data=True
        )
        
        # Insert terrain chunks from MCNK data
        chunks = [{
            'flags': 0x1,
            'area_id': 0x200,
            'holes': 0,
            'has_mcvt': True,
            'has_mcnr': True,
            'has_mclq': False
        }]
        chunk_ids = db_ops.batch_insert_terrain_chunks(map_id, tile_id, chunks)
            
        # Verify database content
        cursor = db_ops.db.conn.execute("SELECT * FROM maps")
        map_record = cursor.fetchone()
        assert map_record is not None
        assert map_record['format'] == 'RETAIL'
        assert map_record['version'] == 18
        
        # Check terrain chunks
        cursor = db_ops.db.conn.execute("SELECT * FROM terrain_chunks")
        chunk = cursor.fetchone()
        assert chunk is not None
        assert chunk['flags'] == 0x1
        assert chunk['area_id'] == 0x200
        
        # Save to JSON
        json_handler = JSONOutputHandler(str(tmp_path))
        json_path = json_handler.write_adt_data(
            file_path=str(adt_path),
            format_type='RETAIL',
            data=result
        )
        
        # Verify JSON content
        with open(json_path) as f:
            json_data = json.load(f)
            assert json_data['metadata']['format'] == 'RETAIL'
            mcnk_chunks = json_data['decoded_chunks'].get('MCNK', [])
            assert any(chunk.get('flags') == 0x1 for chunk in mcnk_chunks)

    def test_json_output(self, tmp_path):
        """Test JSON output format for decoded files"""
        # Create test ADT with terrain and model data
        test_data = (
            create_test_chunk(b'MVER', struct.pack('<I', 18)) +
            create_test_chunk(b'MMDX', b'World\\Model\\test.m2\x00') +
            create_mcnk_chunk(0x1, 30, 30, 0x200)  # flags=0x1, x=30, y=30, area_id=0x200
        )
        
        adt_path = RETAIL_ADT
        with open(adt_path, 'wb') as f:
            f.write(test_data)
            
        # Create output directory
        output_dir = tmp_path / "json_output"
        output_dir.mkdir()
        
        # Parse ADT file
        parser = RetailADTParser(str(adt_path))
        with parser:
            result = parser.parse()
            
            # Save to JSON using handler
            json_handler = JSONOutputHandler(str(output_dir))
            json_path = json_handler.write_adt_data(
                file_path=str(adt_path),
                format_type='RETAIL',
                data=result
            )
            
        # Verify JSON content
        with open(json_path) as f:
            data = json.loads(f.read())
            
        # Check high-level structure
        assert 'metadata' in data
        assert 'decoded_chunks' in data
        
        # Check specific content
        assert data['metadata']['format'] == 'RETAIL'
        
        # Check terrain chunk data
        terrain_chunks = data['decoded_chunks'].get('MCNK', [])
        assert len(terrain_chunks) == 1
        chunk = terrain_chunks[0]
        assert chunk['flags'] == 0x1
        assert chunk['area_id'] == 0x200
        assert chunk['position'] == {'x': 30, 'y': 30}
        
        # Check model references
        model_chunks = [c for c in data['chunks'] if c['name'] == 'MMDX']
        assert len(model_chunks) == 1
        assert 'World\\Model\\test.m2' in model_chunks[0]['data']

if __name__ == '__main__':
    pytest.main([__file__])