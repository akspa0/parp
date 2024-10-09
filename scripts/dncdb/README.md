# Dnc.db Parser

This tool parses the `Dnc.db` file and generates an HTML output with the parsed data and colors. The `Dnc.db` file specifies the day-night cycle and contains information about outdoor lighting with respect to the day-night cycle.

## Features

- Parses the `Dnc.db` file and extracts relevant data fields.
- Generates an HTML file with the parsed data displayed in a table.
- Displays colors for different light types based on the parsed data.

## Requirements

- Python 3.x
- `argparse` module (included in the Python standard library)

## Usage

1. Clone the repository or download the script.
2. Run the script with the input `Dnc.db` file and the desired output HTML file as arguments.

```sh
python plot_dnc.py path/to/Dnc.db path/to/output.html
```

### Example

```sh
python plot_dnc.py ./dnc.db dnc_output.html
```

This will parse the `dnc.db` file and generate an HTML file named `dnc_output.html` in the current directory.

## Script Details

### `parse_dnc_db(file_path)`

Parses the `Dnc.db` file and extracts the data fields.

- **Parameters**: `file_path` (str) - Path to the input `Dnc.db` file.
- **Returns**: List of dictionaries containing the parsed data.

### `generate_html(parsed_data, output_file)`

Generates an HTML file with the parsed data displayed in a table.

- **Parameters**:
  - `parsed_data` (list) - List of dictionaries containing the parsed data.
  - `output_file` (str) - Path to the output HTML file.

### `main()`

Main function to handle command-line arguments and run the parsing and HTML generation.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Acknowledgements

- Thanks to the [wowdev.wiki](https://wowdev.wiki/Dnc.db) documentation.
