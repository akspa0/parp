# Universal WDT/ADT Parser Specification

## Overview
A modular system for parsing both Alpha and Retail format WDT/ADT files, with clear separation of concerns and format-specific handling.

## Core Components

### 1. Format Detection Module
- Location: `format_detector.py`
- Purpose: Detect file format (Alpha vs Retail) based on chunk signatures
- Key features:
  * Fast signature scanning
  * Format-specific chunk patterns (MDNM/MONM for Alpha, MMDX/MWMO for Retail)
  * Version detection from MVER chunk

### 2. Base Parser Classes
- Location: `base/`
  * `chunk_parser.py` - Abstract base class for chunk parsing
  * `wdt_parser.py` - Base WDT file parser
  * `adt_parser.py` - Base ADT file parser
- Common functionality:
  * Memory mapping
  * Chunk navigation
  * Error handling
  * Database integration

### 3. Format-Specific Implementations
- Location: `formats/`
  * `alpha/`
    - `wdt_parser.py` - Alpha WDT implementation
    - `adt_parser.py` - Alpha ADT implementation
    - `chunk_decoders.py` - Alpha-specific chunk decoders
  * `retail/`
    - `wdt_parser.py` - Retail WDT implementation
    - `adt_parser.py` - Retail ADT implementation
    - `chunk_decoders.py` - Retail-specific chunk decoders

### 4. Shared Chunk Definitions
- Location: `chunks/`
  * `common.py` - Shared chunk structures (MVER, etc.)
  * `alpha_chunks.py` - Alpha format chunk definitions
  * `retail_chunks.py` - Retail format chunk definitions

### 5. Database Layer
- Location: `database/`
  * `models.py` - Database models/schemas
  * `operations.py` - Database operations
  * `migrations/` - Schema migrations

### 6. Utilities
- Location: `utils/`
  * `memory_mapping.py` - Memory mapping utilities
  * `visualization.py` - Grid visualization tools
  * `logging.py` - Enhanced logging functionality

## Key Features

### Format Detection
```python
class FormatDetector:
    def detect_format(self, file_path: str) -> FileFormat:
        # Scan for format-specific signatures
        # Return FileFormat.ALPHA or FileFormat.RETAIL
```

### Universal Parser Interface
```python
class UniversalWDTParser:
    def __init__(self, file_path: str):
        self.format = FormatDetector().detect_format(file_path)
        self.parser = self._create_parser()

    def _create_parser(self):
        if self.format == FileFormat.ALPHA:
            return AlphaWDTParser(self.file_path)
        return RetailWDTParser(self.file_path)
```

### Chunk Processing
```python
class ChunkProcessor:
    def process_chunk(self, chunk_name: str, data: bytes) -> dict:
        decoder = self._get_decoder(chunk_name)
        return decoder.decode(data)
```

## Implementation Strategy

1. **Phase 1: Core Infrastructure**
   - Base classes and interfaces
   - Format detection
   - Memory mapping
   - Database schema

2. **Phase 2: Alpha Format**
   - Port current Alpha format handling
   - Implement Alpha-specific decoders
   - Testing with Alpha files

3. **Phase 3: Retail Format**
   - Implement Retail format handling
   - Port improved MCLY/MCAL handling
   - Testing with Retail files

4. **Phase 4: Integration**
   - Universal parser interface
   - Format-specific optimizations
   - Comprehensive testing

## Key Improvements

1. **MCLY/MCAL Handling**
   - Combine current analyze_wdt.py's accurate MCLY/MCAL parsing with other_utils' comprehensive chunk handling
   - Enhanced error detection and recovery
   - Better compression handling

2. **Memory Efficiency**
   - Streaming chunk processing
   - Selective memory mapping
   - Batch database operations

3. **Error Handling**
   - Detailed error reporting
   - Graceful degradation
   - Recovery mechanisms

4. **Extensibility**
   - Plugin system for new formats
   - Custom chunk handlers
   - Format-specific optimizations

## Usage Example
```python
from wdt_parser import UniversalWDTParser

parser = UniversalWDTParser("map.wdt")
result = parser.parse()

# Format-specific operations are handled internally
for tile in result.tiles:
    print(f"Tile at ({tile.x}, {tile.y})")
    if tile.has_adt:
        adt_data = parser.parse_adt(tile)
```
References:

https://github.com/ModernWoWTools/Warcraft.NET
https://github.com/ModernWoWTools/MapUpconverter/
https://gitlab.com/prophecy-rp/noggit-red/-/tree/master/src/noggit
Alpha format WDT files: https://wowdev.wiki/Alpha
Common ADT/WDT chunks, similar between both formats: https://wowdev.wiki/ADT/v18
Retail format WDT files: https://wowdev.wiki/WDT