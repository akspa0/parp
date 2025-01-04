# WoW ADT File Analyzer

This project provides tools for analyzing World of Warcraft ADT (terrain) files. It processes ADT files in two stages:
1. Initial extraction and chunking of ADT files
2. Conversion of extracted data into SQLite databases for analysis

## Requirements

- Python 3.8 or higher
- Dependencies listed in `requirements.txt`

Install dependencies with:
```bash
pip install -r requirements.txt

Scripts
adt_processor.py

Primary script for processing ADT files. It performs two passes:

    Initial pass: Extracts raw chunk data from ADT files
    Detailed pass: Decodes chunk data using known formats

Usage:

python bulk_adt_analyzer.py --known-files community-listfile.csv /path/to/adt/files/

Output structure:

output_files/
    MapName1/
        initial_analysis/
            file1.json
            file2.json
        decoded_data/
            file1.json
            file2.json
    MapName2/
        ...

json_to_sqlite.py

Converts processed JSON files into SQLite databases for easier analysis. Creates separate databases for each map directory.

Usage:

python json_to_sqlite.py output_files --output-dir databases

Output structure:

databases/
    MapName1/
        adt_data_MapName1_20231215_123456.db
        adt_export_20231215_123456.log
    MapName2/
        adt_data_MapName2_20231215_123456.db
        adt_export_20231215_123456.log

Database Schema
adt_files table

    id (PRIMARY KEY)
    filename
    map_name
    x_coord
    y_coord
    processed_timestamp

chunks table

    id (PRIMARY KEY)
    adt_id (FOREIGN KEY)
    magic
    size
    chunk_index
    raw_data
    decoded_data
    chunk_status
    status_message

Example Queries

Get chunk status distribution:

SELECT magic, chunk_status, COUNT(*) as count
FROM chunks
GROUP BY magic, chunk_status
ORDER BY magic, count DESC;

Find problematic chunks:

SELECT af.filename, c.magic, c.chunk_status, c.status_message
FROM chunks c
JOIN adt_files af ON c.adt_id = af.id
WHERE c.chunk_status NOT IN ('decoded', 'empty')
ORDER BY af.filename, c.chunk_index;

Chunk Status Types

    decoded: Successfully decoded chunk
    empty: Empty chunk (normal for some chunk types)
    error: Error during decoding
    unhandled: No decoder available for chunk type

Logging

Both scripts generate detailed logs:

    adt_processor.log: General processing log
    adt_export_TIMESTAMP.log: Database export logs (per map)

Notes

    Timestamps are used in filenames to prevent overwriting previous runs
    Each map gets its own database file for easier management
    Empty chunks are normal for some chunk types
    Some chunk types may be unhandled if no decoder is available

Known Issues

    MCIN/NICM chunks require exactly 24 bytes for decoding
    Some chunk types may not have implemented decoders
    Large files may require significant memory during processing

Contributing

Feel free to contribute by:

    Adding new chunk decoders
    Improving existing decoders
    Adding new analysis queries
    Reporting bugs or issues


And here's the `requirements.txt`:

pathlib>=1.0.1
argparse>=1.4.0


Note: The actual requirements are minimal since the scripts mainly use Python standard library modules. The only external dependencies are `pathlib` (which is actually part of the standard library in Python 3.x but listed for completeness) and `argparse` (also part of standard library but listed for explicit documentation).

Optional dependencies for development:

For development

pylint>=2.17.0
black>=23.0.0
pytest>=7.0.0