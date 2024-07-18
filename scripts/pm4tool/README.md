# PM4/ADT/WMO Parsing and 3D Model Generation

This project contains scripts for parsing PM4, ADT, and WMO files from World of Warcraft game data. It extracts and decodes chunk data, stores it in an SQLite database, and generates 3D models in OBJ format.

## Table of Contents

- [Overview](#overview)
- [Scripts](#scripts)
  - [pm4-tool_0x21.py](#pm4-tool_0x21py)
  - [common_helpers.py](#common_helperspy)
  - [adt_chunk_decoders.py](#adt_chunk_decoderspy)
  - [chunk_decoders.py](#chunk_decoderspy)
- [Usage](#usage)
- [3D Model Generation](#3d-model-generation)
- [Contributing](#contributing)
- [License](#license)

## Overview

This project aims to parse and decode data from PM4, ADT, and WMO files used in World of Warcraft. The decoded data is stored in an SQLite database and used to generate 3D models in OBJ format. The position data in the `LRPM` chunks is considered the origin point for each 3D model.

## Useful tools and links to reference material used in development of this tool:
https://wowdev.wiki/Alpha
https://wowdev.wiki/M2
https://wowdev.wiki/MDX
https://wowdev.wiki/WMO
https://wowdev.wiki/WDT
https://wowdev.wiki/ADT/v18
https://wowdev.wiki/WDL/v18
https://wowdev.wiki/WLQ
https://wowdev.wiki/Common_Types

https://wowdev.wiki/PD4
https://wowdev.wiki/PM4

## Converters and libraries ##
https://github.com/MaxtorCoder/MultiConverter/
https://github.com/wowdev/pywowlib (The basis of all our chunk decoders is based on pywowlib's implementation)

## MDX/MDL reference ##
https://www.hiveworkshop.com/threads/mdx-specifications.240487/
https://forum.wc3edit.net/viewtopic.php?t=10568

## Scripts

### pm4-tool_0x21.py


# PM4-Tool

The `pm4-tool` is a Python script designed to process PM4, PD4, and ADT files, decode their chunks, store the data in SQLite databases, and optionally export the data to JSON files for further analysis.

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [File Structure](#file-structure)
- [Logging](#logging)

## Requirements

- Python 3.6 or higher
- SQLite

## Installation

1. Clone the repository or download the script files.
2. Ensure you have Python installed. If not, download and install it from [python.org](https://www.python.org/downloads/).

## Usage

To use the `pm4-tool` script, run the following command in your terminal or command prompt:

```bash
python pm4-tool_0x21.py <input_path> <output_dir> [--output_json <output_json_dir>] [--export_json <export_json_dir>]
```

- `<input_path>`: Path to the input file or directory containing PM4, PD4, or ADT files.
- `<output_dir>`: Path to the output directory where SQLite databases will be stored.
- `--output_json <output_json_dir>`: (Optional) Directory to save JSON analysis files.
- `--export_json <export_json_dir>`: (Optional) Directory to export data from the database to JSON files.

### Example

```bash
python pm4-tool_0x21.py ./input ./output --output_json ./json_analysis --export_json ./json_export
```

This command will process all files in the `./input` directory, store the decoded data in the `./output` directory, save JSON analysis files in the `./json_analysis` directory, and export data from the SQLite database to JSON files in the `./json_export` directory.

## File Structure

### pm4-tool_0x21.py

The main script that processes PM4, PD4, and ADT files.

### chunk_decoders.py

Contains decoder functions for PM4 and PD4 chunk types.

### adt_chunk_decoders.py

Contains decoder functions for ADT chunk types.

### common_helpers.py

Contains helper functions used across the scripts.

## Logging

The script generates a log file with a timestamped filename (e.g., `processing_YYYYMMDD_HHMMSS.log`) in the current directory. The log file contains detailed information about the processing steps, including any errors or warnings encountered during the execution.

### common_helpers.py

Contains utility functions used across the project.

**Functions:**
- `ensure_folder_exists(folder)`: Ensures the specified folder exists.
- `decode_uint8(data, offset)`, `decode_uint16(data, offset)`, `decode_int16(data, offset)`, `decode_uint32(data, offset)`, `decode_float(data, offset)`, `decode_cstring(data, offset, length)`: Functions to decode various data types.
- `decode_C3Vector(data, offset)`, `decode_C3Vector_i(data, offset)`: Functions to decode 3D vector data.
- `decode_RGBA(data, offset)`: Function to decode RGBA color data.
- `read_chunks_from_data(data, offset=0)`: Reads chunks from raw data.
- `reverse_chunk_id(chunk_id)`: Reverses a chunk ID.

### adt_chunk_decoders.py

Contains decoding functions for ADT chunk types.

**Functions:**
- `decode_MVER(data, offset=0)`, `decode_MHDR(data, offset=0)`, `decode_MCIN(data, offset=0)`, `decode_MTXF(data, offset=0)`, `decode_MMDX(data, offset=0)`, `decode_MMID(data, offset=0)`, `decode_MWMO(data, offset=0)`, `decode_MWID(data, offset=0)`, `decode_MDDF(data, offset=0)`, `decode_MODF(data, offset=0)`, `decode_MFBO(data, offset=0)`, `decode_MH2O(data, offset=0)`, `decode_MCNK(data, offset=0)`, `decode_MCVT(data, offset=0)`, `decode_MCLY(data, offset=0)`, `decode_MCRF(data, offset=0)`, `decode_MCAL(data, offset=0)`, `decode_MCSH(data, offset=0)`, `decode_MCCV(data, offset=0)`, `decode_MCLQ(data, offset=0)`, `decode_MCSE(data, offset=0)`, `decode_MCLV(data, offset=0)`: Functions to decode various ADT chunk types.

**Global Variables:**
- `adt_chunk_decoders`: Dictionary mapping ADT chunk IDs to their respective decoding functions.

### chunk_decoders.py

Contains decoding functions for PM4 chunk types.

**Functions:**
- `decode_MVER_chunk(data)`, `decode_MCRC_chunk(data)`, `decode_MSHD_chunk(data)`, `decode_MSPV_chunk(data)`, `decode_MSPI_chunk(data)`, `decode_MSCN_chunk(data)`, `decode_MSLK_chunk(data)`, `decode_MSVT_chunk(data)`, `decode_MSVI_chunk(data)`, `decode_MSUR_chunk(data)`, `decode_LRPM_chunk(data)`, `decode_RRPM_chunk(data)`, `decode_KLSM_chunk(data)`, `decode_HBDM_chunk(data)`, `decode_IBDM_chunk(data)`, `decode_FBDM_chunk(data)`, `decode_SODM_chunk(data)`, `decode_FSDM_chunk(data)`: Functions to decode various PM4 chunk types.

**Global Variables:**
- `chunk_decoders`: Dictionary mapping PM4 chunk IDs to their respective decoding functions.

### wmo_parse.py

Analyzes WMO files and outputs parsed data to JSON.

**Functions:**
- `analyze_wmo_file(file_path, output_dir)`: Analyzes a WMO file and outputs parsed data to JSON.
- `main()`: Main function to handle command-line arguments and call `analyze_wmo_file`.

### wmo_chunk_decoders.py

Contains decoding functions for WMO chunk types.

**Functions:**
- `decode_chunk_REVM(data, offset)`, `decode_chunk_MVER(data, offset)`, `decode_chunk_MOGP(data, offset)`, `decode_chunk_MOPY(data, offset)`, `decode_chunk_MOVI(data, offset)`, `decode_chunk_MOLT(data, offset)`, `decode_chunk_MOSB(data, offset)`, `decode_chunk_MOCV(data, offset)`, `decode_chunk_MODD(data, offset)`, `decode_chunk_MODR(data, offset)`, `decode_chunk_MOTV(data, offset)`, `decode_chunk_MOVT(data, offset)`, `decode_chunk_MOIN(data, offset)`, `decode_unknown(data, offset)`: Functions to decode various WMO chunk types.

**Global Variables:**
- `chunk_decoders`: Dictionary mapping WMO chunk IDs to their respective decoding functions.

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Create a new Pull Request.

