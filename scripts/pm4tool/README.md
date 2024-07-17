# PM4/ADT/WMO Parsing and 3D Model Generation

This project contains scripts for parsing PM4, ADT, and WMO files from World of Warcraft game data. It extracts and decodes chunk data, stores it in an SQLite database, and generates 3D models in OBJ format.

## Table of Contents

- [Overview](#overview)
- [Scripts](#scripts)
  - [pm4-tool_0x05a.py](#pm4-tool_0x05apy)
  - [common_helpers.py](#common_helperspy)
  - [adt_chunk_decoders.py](#adt_chunk_decoderspy)
  - [chunk_decoders.py](#chunk_decoderspy)
  - [wmo_parse.py](#wmo_parsepy)
  - [wmo_chunk_decoders.py](#wmo_chunk_decoderspy)
  - [generate_objs.py](#generate_objspy)
- [Usage](#usage)
- [3D Model Generation](#3d-model-generation)
- [Contributing](#contributing)
- [License](#license)

## Overview

This project aims to parse and decode data from PM4, ADT, and WMO files used in World of Warcraft. The decoded data is stored in an SQLite database and used to generate 3D models in OBJ format. The position data in the `LRPM` chunks is considered the origin point for each 3D model.

## Scripts

### pm4-tool_0x05a.py

This script processes PM4, PD4, and ADT files, stores decoded chunk data in an SQLite database, and optionally exports the data to JSON files.

**Functions:**
- `read_chunks(file_path)`: Reads chunks from the specified file.
- `create_database(db_path)`: Creates an SQLite database.
- `insert_chunk_field(cursor, file_name, chunk_id, record_index, field_name, field_value, field_type)`: Inserts chunk field data into the database.
- `decode_chunks(data, chunk_decoders)`: Decodes chunks using the provided decoders.
- `save_json(data, filepath)`: Saves data to a JSON file.
- `process_file(input_file, cursor, file_type, output_json)`: Processes an input file and stores the data in the database.
- `export_to_json(db_path, output_dir)`: Exports data from the database to JSON files.

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

### generate_objs.py

Generates 3D OBJ files from `LRPM` chunk data stored in the SQLite database.

**Functions:**
- `ensure_folder_exists(folder)`: Ensures the specified folder exists.
- `fetch_lrpm_data(cursor)`: Fetches `LRPM` chunk data from the database.
- `parse_field_value(field_value)`: Parses a JSON field value.
- `generate_obj(vertices, obj_path)`: Generates an OBJ file from the given vertices.
- `main(db_path, output_dir)`: Main function to fetch data, generate individual and combined OBJ files.

## Usage

1. **Process Files:**
   ```bash
   python pm4-tool_0x05a.py /path/to/input_file_or_directory /path/to/output_directory --output_json /path/to/json_output_directory --export_json /path/to/export_json_directory
   ```

2. **Analyze WMO Files:**
   ```bash
   python wmo_parse.py /path/to/input_wmo_file /path/to/output_directory
   ```

3. **Generate 3D OBJ Files:**
   ```bash
   python generate_objs.py /path/to/chunk_data.db /path/to/output_directory
   ```

## 3D Model Generation

- **Origin Point Notation:** The `position` data in the `LRPM` chunk represents the origin point for each 3D model.
- **Vertices:** Extracted from the `position` field in the `LRPM` chunk and converted into points in 3D space in the OBJ files.

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Create a new Pull Request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
