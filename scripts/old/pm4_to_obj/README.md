# PM4 File Parser

This project contains scripts to parse and decode chunks in PM4 files. It performs an initial analysis to extract raw data from the chunks and a detailed analysis to decode and interpret the chunk data.

## Structure

The project includes the following files:
- `initial_analysis.py`: Performs the initial analysis of the PM4 file and extracts raw chunk data into a JSON file.
- `detailed_analysis.py`: Decodes the raw chunk data from the initial analysis and outputs detailed information into a JSON file.
- `chunk_decoders.py`: Contains functions to decode specific chunk types.
- `README.md`: Provides an overview of the project and usage instructions.

## Setup

Ensure you have Python 3.x installed on your system. Install the required dependencies using `pip`:

```sh
pip install structlog
```

## Usage

### Initial Analysis

The initial analysis script reads a PM4 file, extracts raw chunk data, and saves it to a JSON file.

```sh
python initial_analysis.py <path/to/pm4_file> <output_directory>
```

#### Example

```sh
python initial_analysis.py /path/to/development_00_00.pm4 /path/to/output
```

This command will create a JSON file named `development_00_00.pm4_initial_analysis.json` in the specified output directory.

### Detailed Analysis

The detailed analysis script reads the JSON file from the initial analysis, decodes the chunk data, and saves detailed information to a JSON file.

```sh
python detailed_analysis.py <path/to/initial_analysis_json> <output_directory>
```

#### Example

```sh
python detailed_analysis.py /path/to/output/development_00_00.pm4_initial_analysis.json /path/to/detailed_output
```

This command will create a JSON file named `development_00_00.pm4_detailed_parsing.json` in the specified output directory.

## Chunk Decoders

The `chunk_decoders.py` file contains functions to decode specific chunk types. The decoders currently implemented include:

- `MVER`: Version information
- `MCRC`: CRC information
- `MSHD`: Header information
- `MSPV`: Vertices
- `MSPI`: Indices
- `MSCN`: Normals
- `MSLK`: Links
- `MSVT`: Vertices with tangents
- `MSVI`: Indices for vertices
- `MSUR`: Surfaces
- `LRPM`: Position data
- `RRPM`: Position data in a different format
- `HBDM`: Destructible building headers
- `IBDM`: Destructible building indices
- `FBDM`: Destructible building filenames
- `SODM`: Miscellaneous data
- `FSDM`: Miscellaneous data

## Contributing

Contributions to this project are welcome. If you have improvements or new decoders to add, please submit a pull request.

## License

This project is licensed under the MIT License.

## Contact

For questions or support, please contact Akspa on discord (see root README.md for invite link).
