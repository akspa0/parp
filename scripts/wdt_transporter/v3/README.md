# WDT Converter v3

Simple Python script to convert WoW Alpha (0.5.3) WDT files to WotLK (3.3.5) format.

## Features

- Standalone script (no pip package)
- Raw chunk handling (preserves original chunk names)
- Separate files for each chunk type
- Based on gp implementation

## Usage

```bash
python convert.py input.wdt [-o output_dir] [--debug]
```

Arguments:
- `input.wdt`: Input Alpha WDT file
- `-o/--output-dir`: Output directory (default: input_dir/converted_YYYYMMDD_HHMMSS)
- `--debug`: Enable debug output

## Structure

- `chunks/base.py`: Base chunk handling
- `chunks/alpha/`: Alpha version chunks
  - `revm.py`: REVM (MVER) chunk
  - `dhpm.py`: DHPM (MPHD) chunk
  - `niam.py`: NIAM (MAIN) chunk
- `chunks/wotlk/`: WotLK version chunks
- `convert.py`: Main conversion script

## Development

1. Each chunk type is in its own file
2. Raw chunk names are used (e.g. 'REVM' not 'MVER')
3. Follows gp implementation patterns
4. Simple and focused functionality

## References

- `gp/wowfiles/`: Reference C++ implementation
- `gp/wowfiles/alpha/`: Alpha format definitions
- `gp/wowfiles/lichking/`: WotLK format definitions