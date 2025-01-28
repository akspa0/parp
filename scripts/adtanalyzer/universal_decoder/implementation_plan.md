# Universal WDT/ADT Decoder Implementation Plan

## Overview
This implementation merges the ADT analyzer (bulk_adt_analyzer_5.py) and WDT analyzer (alpha_wdt/analyze_wdt.py) into a unified tool that can handle both file formats while maintaining format-specific processing where needed.

## Directory Structure
```
universal_decoder/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Main entry point
│   ├── format_detector.py      # Format detection logic
│   ├── base/
│   │   ├── __init__.py
│   │   ├── chunk_parser.py     # Base chunk parsing
│   │   ├── wdt_parser.py       # Base WDT parsing
│   │   └── adt_parser.py       # Base ADT parsing
│   ├── formats/
│   │   ├── __init__.py
│   │   ├── alpha/
│   │   │   ├── __init__.py
│   │   │   ├── wdt_parser.py
│   │   │   ├── adt_parser.py
│   │   │   └── chunk_decoders.py
│   │   └── retail/
│   │       ├── __init__.py
│   │       ├── wdt_parser.py
│   │       ├── adt_parser.py
│   │       └── chunk_decoders.py
│   ├── chunks/
│   │   ├── __init__.py
│   │   ├── common.py          # Shared chunks (MVER etc)
│   │   ├── alpha_chunks.py    # Alpha-specific chunks
│   │   └── retail_chunks.py   # Retail-specific chunks
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py          # Database schemas
│   │   └── operations.py      # Database operations
│   └── utils/
│       ├── __init__.py
│       ├── memory_mapping.py
│       └── logging.py
└── tests/                     # Test files
    └── __init__.py
```

## Implementation Phases

### Phase 1: Core Infrastructure (1-2 days)
1. Set up project structure
2. Port common utilities from both analyzers
3. Implement format detection
4. Create base classes for chunk parsing
5. Set up unified database schema

### Phase 2: Format-Specific Implementation (2-3 days)
1. Port Alpha format handling from analyze_wdt.py
2. Port Retail format handling from bulk_adt_analyzer_5.py
3. Implement format-specific chunk decoders
4. Add format detection logic

### Phase 3: Database Layer (1-2 days)
1. Merge database schemas from both tools
2. Create unified database operations
3. Implement batch processing for better performance
4. Add migration support for schema updates

### Phase 4: Integration & Testing (2-3 days)
1. Create unified command-line interface
2. Add progress reporting and logging
3. Implement error handling and recovery
4. Add comprehensive testing
5. Create documentation

## Key Components

### Format Detection
```python
class FormatDetector:
    def detect_format(self, file_path: str) -> FileFormat:
        # Detect based on chunk signatures
        # MDNM/MONM for Alpha
        # MMDX/MWMO for Retail
```

### Universal Parser Interface
```python
class UniversalParser:
    def __init__(self, file_path: str):
        self.format = FormatDetector().detect_format(file_path)
        self.parser = self._create_parser()

    def parse_file(self):
        # Unified parsing interface
        # Delegates to format-specific parser
```

### Database Schema Updates
1. Combine tables from both analyzers
2. Add format tracking columns
3. Support for both Alpha and Retail specific fields
4. Maintain backwards compatibility

## Migration Strategy
1. Keep original tools functional
2. Create new unified tool in parallel
3. Validate against both original implementations
4. Provide database migration path

## Testing Strategy
1. Unit tests for each component
2. Integration tests for full parsing
3. Validation against original tools
4. Performance benchmarking

## Usage Example
```python
from universal_decoder import UniversalParser

# Parse WDT file
parser = UniversalParser("map.wdt")
wdt_data = parser.parse_file()

# Parse ADT file
parser = UniversalParser("map_32_32.adt")
adt_data = parser.parse_file()
```

## Improvements Over Original Tools
1. Unified interface for both formats
2. Better error handling and recovery
3. Improved performance through batch processing
4. More comprehensive logging
5. Format-specific optimizations
6. Better memory management
7. Progress reporting
8. Validation checks

## References
- Original ADT analyzer: bulk_adt_analyzer_5.py
- Original WDT analyzer: alpha_wdt/analyze_wdt.py
- Format specifications: v2_plan.md