# LIT Parser Tool

This tool parses World of Warcraft `.lit` files and stores the extracted data into a SQLite database. The tool performs both initial and detailed analyses of the `.lit` files, storing all relevant data in a single database with multiple tables.

## Features

- Parses `.lit` files from World of Warcraft.
- Extracts both initial metadata and detailed light data.
- Stores parsed data into a SQLite database.
- Handles version-specific parsing logic.
- Supports additional analysis and storage of light data parameters.

## Requirements

- Python 3.6 or higher
- SQLite3

## Installation

1. Clone the repository or download the `combined_lit_parser.py` script.
2. Ensure you have the required Python version and SQLite3 installed on your system.

## Usage

### Command Line Interface

```bash
python combined_lit_parser.py /path/to/input_folder /path/to/output_folder
```

- `/path/to/input_folder`: Directory containing the `.lit` files to be parsed.
- `/path/to/output_folder`: Directory where the SQLite database will be saved.

### Example

```bash
python combined_lit_parser.py ./wow100_input ./wow100_output
```

### Database Schema

The SQLite database will contain the following tables:

- `lights_data`: Stores metadata and light data extracted from the `.lit` files.
  - `id`: Primary key.
  - `file_name`: Name of the `.lit` file.
  - `folder_name`: Name of the folder containing the `.lit` file.
  - `version`: Version of the `.lit` file.
  - `has_count`: Indicates if the file has a count field.
  - `count`: Number of lights in the file.
  - `m_chunk_x`, `m_chunk_y`: Chunk coordinates.
  - `m_chunkRadius`: Chunk radius.
  - `m_lightLocation_x`, `m_lightLocation_y`, `m_lightLocation_z`: Light location coordinates.
  - `m_lightRadius`: Light radius.
  - `m_lightDropoff`: Light dropoff.
  - `m_lightName`: Name of the light.

- `raw_files`: Stores the original `.lit` files as BLOBs.
  - `id`: Primary key.
  - `file_name`: Name of the `.lit` file.
  - `folder_name`: Name of the folder containing the `.lit` file.
  - `file_content`: Binary content of the `.lit` file.

- `additional_light_data`: Stores detailed light data parameters.
  - `id`: Primary key.
  - `file_name`: Name of the `.lit` file.
  - `folder_name`: Name of the folder containing the `.lit` file.
  - `light_index`: Index of the light entry.
  - `highlight_counts`: Highlight counts.
  - `highlight_markers`: Highlight markers.
  - `fog_end`: Fog end values.
  - `fog_start_scaler`: Fog start scaler values.
  - `highlight_sky`: Highlight sky value.
  - `sky_data`: Sky data values.
  - `cloud_mask`: Cloud mask value.
  - `param_data`: Additional parameter data.

## Contributing

If you would like to contribute to the development of this tool, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Commit your changes and push the branch to your forked repository.
4. Open a pull request with a detailed description of your changes.

## Acknowledgments

This tool was developed with the help of the World of Warcraft development community and the documentation provided at [wowdev.wiki](https://wowdev.wiki/LIT)
And extra help from schlumpf (010 Template).
