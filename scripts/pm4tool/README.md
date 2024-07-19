# PM4 Processing Tool

## Overview

This tool processes game data files (PM4, PD4, ADT, WMO), extracts chunk data, and stores the results in a SQLite database. Optionally, it can export the data to JSON format. The script is designed to handle multiple files simultaneously and can process entire directories of files.

## Features

- Supports PM4, PD4, ADT, and WMO file formats.
- Extracts and decodes chunk data.
- Stores extracted data in a SQLite database.
- Optionally exports data to JSON format.
- Handles multiple files using concurrent processing.

## Requirements

- Python 3.6+
- The following Python libraries:
  - `os`
  - `json`
  - `sqlite3`
  - `logging`
  - `argparse`
  - `datetime`
  - `collections`
  - `concurrent.futures`
  - `struct`

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/pm4-processing-tool.git
    cd pm4-processing-tool
    ```

2. Install the required Python packages (if not already installed):

    ```bash
    pip install -r requirements.txt
    ```

3. Ensure the following files are in the same directory as `pm4-tool_0x23.py`:
    - `pm4_chunk_decoders.py`
    - `adt_chunk_decoders.py`
    - `pd4_chunk_decoders.py`
    - `wmo_root_chunk_decoders.py`
    - `wmo_group_chunk_decoders.py`
    - `common_helpers.py`

## Usage

### Command Line Arguments

- `input_path`: Path to the input file or directory.
- `output_dir`: Path to the output directory.
- `--output_json`: (Optional) Directory to save JSON analysis files.
- `--export_json`: (Optional) Directory to export data from the database to JSON files.

### Running the Script

1. **Processing a Single File:**

    ```bash
    python pm4-tool_0x23.py path/to/input/file.pm4 path/to/output/dir
    ```

2. **Processing a Directory of Files:**

    ```bash
    python pm4-tool_0x23.py path/to/input/directory path/to/output/dir
    ```

3. **Processing and Exporting to JSON:**

    ```bash
    python pm4-tool_0x23.py path/to/input/file.pm4 path/to/output/dir --output_json path/to/json/output
    ```

4. **Exporting Data from Database to JSON:**

    ```bash
    python pm4-tool_0x23.py path/to/input/file.pm4 path/to/output/dir --export_json path/to/json/export
    ```

### Example

Processing a directory of files and exporting results to JSON:

```bash
python pm4-tool_0x23.py ./samples ./output --output_json ./json_output
```

## Modules and Functions

### pm4-tool_0x23.py

Main script for processing files.

- **Functions:**
  - `read_chunks(file_path)`
  - `create_database(db_path)`
  - `insert_chunk_field_batch(cursor, batch)`
  - `insert_initial_analysis(cursor, file_name, chunks)`
  - `decode_chunks(data, chunk_decoders)`
  - `parse_and_split_fields(data, record_index)`
  - `detect_data_type(data)`
  - `process_file(input_file, output_dir, output_json)`
  - `export_to_json(db_path, output_dir)`
  - `parse_adt(file_path)`
  - `parse_pd4(file_path)`
  - `parse_wmo_root(file_path)`
  - `parse_wmo_group(file_path)`
  - `main()`

### pm4_chunk_decoders.py

Contains decoders for different PM4 chunks.

### adt_chunk_decoders.py

Contains decoders and parsing functions for ADT chunks.

### pd4_chunk_decoders.py

Contains decoders and parsing functions for PD4 chunks.

### wmo_root_chunk_decoders.py

Contains decoders and parsing functions for WMO root chunks.

### wmo_group_chunk_decoders.py

Contains decoders and parsing functions for WMO group chunks.

### common_helpers.py

Helper functions for decoding various data types and utility functions.

- **Functions:**
  - `ensure_folder_exists(folder_path)`
  - `decode_uint8(data, offset)`
  - `decode_uint16(data, offset)`
  - `decode_int16(data, offset)`
  - `decode_uint32(data, offset)`
  - `decode_float(data, offset)`
  - `decode_cstring(data, offset, max_len)`
  - `decode_C3Vector(data, offset)`
  - `decode_C3Vector_i(data, offset)`
  - `decode_RGBA(data, offset)`
  - `save_json(data, filepath)`
  - `ensure_bytes(data)`
  - `convert_to_json(value)`
  - `analyze_data_type(value)`
  - `parse_and_split_fields(data, record_index)`
  - `detect_data_type(data)`
  - `read_chunks_from_data(data, offset=0)`
  - `reverse_chunk_id(chunk_id)`

## Logging

The script logs its progress and any errors encountered during processing. Logs are saved with a timestamped filename in the format `processing_YYYYMMDD_HHMMSS.log`.
