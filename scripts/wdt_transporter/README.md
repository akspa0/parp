# WDT Converter

Convert World of Warcraft Alpha (0.5.3) WDT/ADT files to version 3.3.5 format.

## Features

- Convert Alpha WDT files to retail format
- Convert embedded ADT data to version 3.3.5
- Fix coordinate offsets for proper placement
- Maintain compatibility with noggit-red
- Support for model and object placements
- Preserve texture and height data

## Requirements

- Python 3.7 or higher
- No additional dependencies required

## Usage

Simply run the script with a WDT file path:

```bash
python wdt_converter.py path/to/alpha.wdt
```

The script will:
1. Load the Alpha WDT file
2. Extract and convert ADT data
3. Apply coordinate fixes
4. Save converted ADTs in a new directory

Output files will be created in a directory named after the WDT file (e.g., `PVPZone01/PVPZone01_XX_YY.adt`).

## File Format Support

### Input Format (Alpha 0.5.3)
- WDT file containing embedded ADT data
- MPHD chunk with Alpha-specific header
- MAIN chunk with ADT offsets
- MDNM/MONM chunks for model/object names
- MCNK chunks with terrain data

### Output Format (3.3.5)
- Separate ADT files in retail format
- MVER chunk with version 18
- MHDR with proper chunk offsets
- MCIN for chunk indexing
- MCNK chunks with fixed coordinates
- MDDF/MODF with corrected placements

## Implementation Details

The script handles:
- Binary data parsing with struct module
- Chunk-based file format processing
- Coordinate system transformations
- Model/object placement fixes

Key classes:
- `WdtAlpha`: Handles Alpha WDT file parsing
- `AdtAlpha`: Processes embedded ADT data
- `AdtConverter`: Converts to version 3.3.5 format

## References

- [Alpha WDT Format](https://wowdev.wiki/Alpha)
- [ADT Format v18](https://wowdev.wiki/ADT/v18)
- [Common Types](https://wowdev.wiki/Common_Types)

## Debugging

The script includes detailed error messages and progress information. If you encounter issues:
1. Check the input file exists and is a valid Alpha WDT
2. Verify you have write permissions in the output directory
3. Look for specific error messages in the console output

## License

MIT License - See LICENSE file for details