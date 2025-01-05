# ADT File Decoder Tool

A comprehensive decoder for World of Warcraft ADT (terrain) files. This tool extracts and documents all terrain data including textures, models, heightmaps, and liquid data.

## Required Files

1. `adt_decoder.py` - The main decoder script
2. Input directory containing .adt files (typically named like `MapName_XX_YY.adt`)

### Optional Output Locations
- Output JSON file (default: `adt_report.json`)
- Log file (default: `adt_processing.log`)

## Script Structure

The decoder is organized into several key components:

### 1. Data Classes
- `TerrainLayer` - Handles texture and terrain layer information
- `MCNKChunk` - Represents map chunks with terrain data
- `ModelPlacement` - Handles M2 model placement data
- `WMOPlacement` - Handles WMO (World Map Object) placement data

### 2. Main Decoder Classes
- `ADTDecoder` - Core class that handles individual ADT file decoding
- `ADTDirectoryParser` - Manages batch processing of ADT files

### 3. Chunk Types Decoded
- `MVER` - Version information
- `MHDR` - Header data and flags
- `MCIN` - Chunk index
- `MTEX` - Texture filenames
- `MMDX` - M2 model filenames
- `MMID` - Model indices
- `MWMO` - WMO filenames
- `MWID` - WMO indices
- `MDDF` - Model placements
- `MODF` - WMO placements
- `MCNK` - Map chunks (terrain data)
- `MH2O` - Liquid/water data

## Usage

```bash
python adt_decoder.py <input_directory> [options]

Options:
  --output, -o  Output JSON file (default: adt_report.json)
  --log, -l     Log file (default: adt_processing.log)
  --debug, -d   Enable debug logging
```

## Output

The tool generates:
1. A detailed JSON report containing:
   - File metadata
   - Chunk data
   - Asset references
   - Terrain information
   - Model placements
   - Texture references

2. Statistical analysis including:
   - Chunk type counts
   - Unique textures used
   - Model references
   - WMO usage

## Example

```bash
python adt_decoder.py /path/to/adt/files --output map_data.json --log processing.log
```

## File Format Overview

ADT files contain multiple chunks that describe terrain:
- Terrain height and texture data
- Model and object placements
- Liquid (water) information
- Texture references
- Lighting and shadow data

Each chunk is identified by a 4-character code (e.g., 'MVER', 'MHDR') and contains specific data structures.
```
