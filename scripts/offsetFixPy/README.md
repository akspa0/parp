# Offset Fix Tool

This tool processes ADT files to fix offsets based on provided parameters. It is useful for adjusting coordinates within a game's map files.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Options](#options)
- [Examples](#examples)
- [License](#license)

## Installation

To use this tool, you need to have Python installed on your system. Additionally, you need to install the `construct` library, which can be done using pip:

```sh
pip install construct
```

## Usage

The tool can be run from the command line. The basic syntax is:

```sh
python offset_fix.py input_dir output_dir [options]
```

### Options

- `input_dir`: Path to the directory containing `.adt` files.
- `output_dir`: Path to the directory where processed files will be saved.
- `--x-offset`: X offset value (default: 0).
- `--y-offset`: Y offset value (default: 0).
- `--z-offset`: Z offset value (default: 0.0).
- `--wdt-x-offset`: WDT X offset value (default: 0.0).
- `--wdt-y-offset`: WDT Y offset value (default: 0.0).
- `--wdt-z-offset`: WDT Z offset value (default: 0.0).

### Examples

#### Basic Usage

Process all `.adt` files in the `input` directory and save the results in the `output` directory with default offsets:

```sh
python offset_fix.py input output
```

#### Custom Offsets

Process all `.adt` files with custom offsets:

```sh
python offset_fix.py input output --x-offset 10 --y-offset 15 --z-offset 5.0 --wdt-x-offset 2.0 --wdt-y-offset 3.0 --wdt-z-offset 4.0
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## How It Works

### Binary Structures

The script defines several binary structures using the `construct` library to parse and manipulate the ADT files:

- `MCIN`: Represents a chunk of data within the ADT file.
- `MCIN_Array`: An array of `MCIN` structures.
- `Offsets_Header`: Contains offsets for MDDF and MODF sections.
- `Coords`: Represents 3D coordinates.
- `MDDF_Header`: Header for the MDDF section.
- `MODF_Header`: Header for the MODF section.

### OffsetFixData Class

The `OffsetFixData` class holds the data necessary for offset fixing operations, including offsets and positions.

### Logging

The `setup_logging` function sets up logging to both a file and the console, with timestamps in the log file names.

### Processing Functions

- `process_zone_file`: Processes a single ADT file, applying the offset fixes.
- `process_directory`: Processes all `.adt` files in the specified input directory.

### Main Function

The `main` function parses command-line arguments, sets up the offset data, and processes the directory.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Support

If you encounter any issues or have questions, please open an issue on the GitHub repository.
