# Universal WoW Map File Decoder

A unified tool for decoding both World of Warcraft ADT (terrain) and WDT (world definition) files, supporting both Alpha and Retail formats.

## Features

- **Format Detection**: Automatically detects and handles both Alpha and Retail formats
- **Unified Processing**: Single interface for both ADT and WDT files
- **Memory Efficient**: Streams data in chunks to handle large files
- **Data Validation**: Validates against known-good listfiles
- **Comprehensive Output**: Stores detailed information in SQLite database
- **Progress Tracking**: Real-time progress reporting and logging
- **Error Recovery**: Graceful handling of corrupted or incomplete files

## Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd universal_decoder
```

2. Run the decoder:
```bash
# Process a single file
python decode.py path/to/file.wdt -o output_directory

# Process a directory recursively
python decode.py path/to/directory -o output_directory -r

# With listfile validation
python decode.py path/to/file.wdt -o output_directory -l path/to/listfile.csv
```

## Output

The tool creates:
- A SQLite database (map_data.db) containing all parsed data
- Detailed logs in the output directory
- Progress information in the console

## Database Schema

The parsed data is stored in several tables:

- `files`: Basic file information and metadata
- `map_tiles`: WDT tile references
- `mcnk_data`: Terrain chunk information
- `textures`: Texture definitions and properties
- `m2_models`: M2 model references
- `wmo_models`: WMO model references
- `m2_placements`: M2 model placement data
- `wmo_placements`: WMO model placement data

## Command Line Options

```
usage: decode.py [-h] [-o OUTPUT_DIR] [-l LISTFILE] [-r] input

Universal WoW Map File Decoder - Handles both WDT and ADT files

positional arguments:
  input                 File or directory to process

optional arguments:
  -h, --help           show this help message and exit
  -o OUTPUT_DIR        Output directory (default: output)
  -l LISTFILE          Path to listfile for validation
  -r, --recursive      Process directories recursively
```

## File Format Support

### ADT Files (Terrain)

#### Alpha Format
- MDNM/MONM chunk structure
- Basic terrain data
- Model references
- Texture information

#### Retail Format
- MMDX/MWMO chunk structure
- Enhanced terrain data
- Advanced texture layers
- Extended model placement data

### WDT Files (World Definition)

#### Alpha Format
- Basic map structure
- Simple tile references
- Limited model support

#### Retail Format
- Advanced map structure
- Detailed tile information
- Extended model and texture support

## Error Handling

The tool provides detailed error reporting:
- Format detection errors
- Chunk parsing errors
- Database operation errors
- Missing file references

All errors are logged to both the console and log files in the output directory.

## Examples

1. Process a single WDT file:
```bash
python decode.py World/Maps/Azeroth/Azeroth.wdt -o parsed_data
```

2. Process all files in a directory:
```bash
python decode.py World/Maps/Azeroth -o parsed_data -r
```

3. Validate against a listfile:
```bash
python decode.py World/Maps/Azeroth/Azeroth.wdt -o parsed_data -l listfile.csv
```

## Development

### Project Structure
```
universal_decoder/
├── src/
│   ├── format_detector.py   # Format detection logic
│   ├── base/               # Base classes
│   ├── formats/            # Format-specific implementations
│   ├── chunks/             # Chunk definitions
│   ├── database/           # Database operations
│   └── utils/              # Utility functions
├── tests/                  # Test files
└── decode.py              # Main executable script
```

### Running Tests
```bash
pytest tests/
```

## References

- [WoWDev Wiki - ADT Format](https://wowdev.wiki/ADT)
- [WoWDev Wiki - WDT Format](https://wowdev.wiki/WDT)
- [Alpha Client Research](https://wowdev.wiki/Alpha)

## License

This project is licensed under the MIT License - see the LICENSE file for details.