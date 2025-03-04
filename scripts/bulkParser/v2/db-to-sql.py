#!/usr/bin/env python3
"""
DB to SQL Converter
Exports SQLite database files to SQL statements for importing into any SQL database

Usage:
    python db_to_sql.py <input_directory> [options]

Arguments:
    input_directory        Directory containing SQLite database (.db) files to convert

Options:
    --output FILE          Output SQL file path (default: export.sql in input directory)
    --format FORMAT        SQL dialect: 'mysql', 'postgresql', 'sqlite', 'mssql' (default: mysql)
    --tables TABLES        Comma-separated list of tables to extract (default: all)
    --batch-size N         Number of rows to process in each batch (default: 1000)
    --skip-blobs           Skip binary blob fields to reduce output size
    --schema-only          Only include schema (CREATE TABLE statements), not data
    --data-only            Only include data (INSERT statements), not schema
    --transaction          Wrap output in transaction statements (BEGIN/COMMIT)
    --drop-tables          Include DROP TABLE statements before CREATE TABLE
    --no-create-index      Skip creation of indexes
"""

import os
import sys
import json
import sqlite3
import argparse
import base64
import re
import gc
import logging
from datetime import datetime
from io import StringIO

def setup_logging():
    """Set up basic logging"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"db_to_sql_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('db_to_sql')

def escape_value(value, dialect):
    """Escape a value for SQL based on the dialect"""
    if value is None:
        return "NULL"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, bytes):
        # Handle binary data based on dialect
        if dialect == 'mysql':
            # Convert to hex for MySQL
            return "X'" + value.hex() + "'"
        elif dialect == 'postgresql':
            # Use bytea escape format
            return "E'\\\\x" + value.hex() + "'"
        elif dialect == 'mssql':
            # Convert to 0x format for SQL Server
            return "0x" + value.hex()
        else:  # SQLite and others
            return "X'" + value.hex() + "'"
    else:
        # Escape string values
        escaped = str(value).replace("'", "''")
        if dialect == 'postgresql':
            # PostgreSQL allows additional escape sequences
            escaped = escaped.replace("\\", "\\\\")
        return f"'{escaped}'"

def get_column_definition(column, dialect):
    """Convert SQLite column definition to the target dialect"""
    # SQLite returns column info as (cid, name, type, notnull, default_value, pk)
    if len(column) > 5:  # Handle both 5-tuple and 6-tuple formats
        _, name, type_name, notnull, default_value, pk = column
    else:
        name, type_name, notnull, default_value, pk = column
    
    # Normalize type name to uppercase
    type_upper = type_name.upper() if type_name else "TEXT"
    
    # Map SQLite types to target dialect types
    if dialect == 'mysql':
        if 'INT' in type_upper:
            sql_type = type_upper
        elif 'CHAR' in type_upper or 'TEXT' in type_upper or 'CLOB' in type_upper:
            if 'VARCHAR' in type_upper:
                sql_type = type_upper
            else:
                sql_type = "TEXT"
        elif 'BLOB' in type_upper:
            sql_type = "BLOB"
        elif 'REAL' in type_upper or 'FLOA' in type_upper or 'DOUB' in type_upper:
            sql_type = "DOUBLE"
        else:
            sql_type = "TEXT"
    elif dialect == 'postgresql':
        if 'INT' in type_upper:
            sql_type = "INTEGER"
        elif 'CHAR' in type_upper or 'TEXT' in type_upper or 'CLOB' in type_upper:
            sql_type = "TEXT"
        elif 'BLOB' in type_upper:
            sql_type = "BYTEA"
        elif 'REAL' in type_upper or 'FLOA' in type_upper or 'DOUB' in type_upper:
            sql_type = "DOUBLE PRECISION"
        else:
            sql_type = "TEXT"
    elif dialect == 'mssql':
        if 'INT' in type_upper:
            sql_type = "INT"
        elif 'CHAR' in type_upper:
            length = re.search(r'\((\d+)\)', type_upper)
            if length:
                sql_type = f"VARCHAR({length.group(1)})"
            else:
                sql_type = "VARCHAR(255)"
        elif 'TEXT' in type_upper or 'CLOB' in type_upper:
            sql_type = "NVARCHAR(MAX)"
        elif 'BLOB' in type_upper:
            sql_type = "VARBINARY(MAX)"
        elif 'REAL' in type_upper or 'FLOA' in type_upper or 'DOUB' in type_upper:
            sql_type = "FLOAT"
        else:
            sql_type = "NVARCHAR(255)"
    else:  # SQLite and others
        sql_type = type_name
    
    # Add constraints
    column_def = f"`{name}` {sql_type}"
    if pk:
        if dialect == 'postgresql':
            column_def += " PRIMARY KEY"
        else:
            column_def += " PRIMARY KEY"
    if notnull:
        column_def += " NOT NULL"
    if default_value is not None:
        column_def += f" DEFAULT {default_value}"
    
    return column_def

def get_create_table_statement(table_name, columns, dialect, drop_table=False):
    """Generate CREATE TABLE statement for the given dialect"""
    create_sql = []
    
    # Add DROP TABLE statement if requested
    if drop_table:
        if dialect == 'postgresql':
            create_sql.append(f"DROP TABLE IF EXISTS \"{table_name}\" CASCADE;")
        elif dialect == 'mysql':
            create_sql.append(f"DROP TABLE IF EXISTS `{table_name}`;")
        elif dialect == 'mssql':
            create_sql.append(f"IF OBJECT_ID(N'[{table_name}]', N'U') IS NOT NULL DROP TABLE [{table_name}];")
        else:
            create_sql.append(f"DROP TABLE IF EXISTS `{table_name}`;")
    
    # Create table statement preamble
    if dialect == 'postgresql':
        create_sql.append(f"CREATE TABLE \"{table_name}\" (")
    elif dialect == 'mysql':
        create_sql.append(f"CREATE TABLE `{table_name}` (")
    elif dialect == 'mssql':
        create_sql.append(f"CREATE TABLE [{table_name}] (")
    else:
        create_sql.append(f"CREATE TABLE `{table_name}` (")
    
    # Add column definitions
    column_defs = []
    primary_keys = []
    
    for column in columns:
        # Extract name and pk based on whether it's a 5-tuple or 6-tuple
        if len(column) > 5:
            # Handle SQLite's 6-tuple format: (cid, name, type, notnull, default_value, pk)
            _, name, _, _, _, pk = column
        else:
            # Handle 5-tuple format: (name, type, notnull, default_value, pk)
            name, _, _, _, pk = column
            
        if pk:
            primary_keys.append(name)
        column_defs.append(f"  {get_column_definition(column, dialect)}")
    
    # Special handling for composite primary keys
    if len(primary_keys) > 1:
        pk_names = ", ".join([f"`{pk}`" for pk in primary_keys])
        column_defs.append(f"  PRIMARY KEY ({pk_names})")
    
    create_sql.append(",\n".join(column_defs))
    create_sql.append(");")
    
    return "\n".join(create_sql)

def get_create_index_statements(table_name, indexes, dialect):
    """Generate CREATE INDEX statements for the given dialect"""
    index_sql = []
    
    for index_name, columns, unique in indexes:
        if unique:
            if dialect == 'postgresql':
                index_sql.append(f"CREATE UNIQUE INDEX \"{index_name}\" ON \"{table_name}\" ({', '.join(columns)});")
            elif dialect == 'mysql':
                index_sql.append(f"CREATE UNIQUE INDEX `{index_name}` ON `{table_name}` ({', '.join(columns)});")
            elif dialect == 'mssql':
                index_sql.append(f"CREATE UNIQUE INDEX [{index_name}] ON [{table_name}] ({', '.join(columns)});")
            else:
                index_sql.append(f"CREATE UNIQUE INDEX `{index_name}` ON `{table_name}` ({', '.join(columns)});")
        else:
            if dialect == 'postgresql':
                index_sql.append(f"CREATE INDEX \"{index_name}\" ON \"{table_name}\" ({', '.join(columns)});")
            elif dialect == 'mysql':
                index_sql.append(f"CREATE INDEX `{index_name}` ON `{table_name}` ({', '.join(columns)});")
            elif dialect == 'mssql':
                index_sql.append(f"CREATE INDEX [{index_name}] ON [{table_name}] ({', '.join(columns)});")
            else:
                index_sql.append(f"CREATE INDEX `{index_name}` ON `{table_name}` ({', '.join(columns)});")
    
    return index_sql

def get_insert_statement(table_name, columns, values, dialect, batch_size=1000):
    """Generate INSERT statements for the given dialect"""
    insert_sql = []
    
    # Prepare column names
    if dialect == 'postgresql':
        column_list = ", ".join([f"\"{col}\"" for col in columns])
    elif dialect == 'mysql':
        column_list = ", ".join([f"`{col}`" for col in columns])
    elif dialect == 'mssql':
        column_list = ", ".join([f"[{col}]" for col in columns])
    else:
        column_list = ", ".join([f"`{col}`" for col in columns])
    
    # Split values into batches
    for i in range(0, len(values), batch_size):
        batch = values[i:i+batch_size]
        
        if dialect == 'postgresql':
            insert_sql.append(f"INSERT INTO \"{table_name}\" ({column_list}) VALUES")
        elif dialect == 'mysql':
            insert_sql.append(f"INSERT INTO `{table_name}` ({column_list}) VALUES")
        elif dialect == 'mssql':
            insert_sql.append(f"INSERT INTO [{table_name}] ({column_list}) VALUES")
        else:
            insert_sql.append(f"INSERT INTO `{table_name}` ({column_list}) VALUES")
        
        value_strings = []
        for row in batch:
            escaped_values = [escape_value(val, dialect) for val in row]
            value_strings.append(f"({', '.join(escaped_values)})")
        
        if dialect == 'postgresql' or dialect == 'mysql':
            insert_sql.append(",\n".join(value_strings) + ";")
        elif dialect == 'mssql':
            # SQL Server has a limit on the number of rows per batch insert
            # Split into multiple statements if needed
            for j in range(0, len(value_strings), 1000):
                sub_batch = value_strings[j:j+1000]
                if j > 0:
                    if dialect == 'postgresql':
                        insert_sql.append(f"INSERT INTO \"{table_name}\" ({column_list}) VALUES")
                    elif dialect == 'mysql':
                        insert_sql.append(f"INSERT INTO `{table_name}` ({column_list}) VALUES")
                    elif dialect == 'mssql':
                        insert_sql.append(f"INSERT INTO [{table_name}] ({column_list}) VALUES")
                    else:
                        insert_sql.append(f"INSERT INTO `{table_name}` ({column_list}) VALUES")
                insert_sql.append(",\n".join(sub_batch) + ";")
        else:
            insert_sql.append(",\n".join(value_strings) + ";")
    
    return insert_sql

def list_tables(db_path):
    """List all tables in a SQLite database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except sqlite3.Error as e:
        logging.error(f"Error listing tables in {db_path}: {e}")
        return []

def get_table_schema(db_path, table_name):
    """Get the schema for a specific table"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        # Get index information
        cursor.execute(f"PRAGMA index_list({table_name})")
        index_list = cursor.fetchall()
        
        indexes = []
        for idx_info in index_list:
            index_name = idx_info[1]
            unique = idx_info[2]
            
            # Get columns for this index
            cursor.execute(f"PRAGMA index_info({index_name})")
            index_columns = cursor.fetchall()
            columns_list = [col[2] for col in index_columns]
            
            indexes.append((index_name, columns_list, unique))
        
        conn.close()
        
        return {'columns': columns, 'indexes': indexes}
    except sqlite3.Error as e:
        logging.error(f"Error getting schema for table {table_name} in {db_path}: {e}")
        return {'columns': [], 'indexes': []}

def get_table_data_generator(db_path, table_name, batch_size=1000, skip_blobs=False):
    """Generator that yields batches of table data"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Get total row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = cursor.fetchone()[0]
        
        if total_rows == 0:
            yield columns, []
            return
        
        # Process in batches
        offset = 0
        while offset < total_rows:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
            batch = cursor.fetchall()
            
            if skip_blobs:
                # Replace BLOBs with NULL to reduce output size
                processed_batch = []
                for row in batch:
                    processed_row = []
                    for value in row:
                        if isinstance(value, bytes) and len(value) > 100:  # Only skip large blobs
                            processed_row.append(None)
                        else:
                            processed_row.append(value)
                    processed_batch.append(tuple(processed_row))
                yield columns, processed_batch
            else:
                yield columns, batch
            
            offset += batch_size
            
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Error getting data from table {table_name} in {db_path}: {e}")
        yield columns, []

def get_create_statements(db_path, dialect, drop_tables=False, no_create_index=False, tables_to_extract=None):
    """Generate all CREATE TABLE statements for a database"""
    logger = logging.getLogger('db_to_sql')
    
    db_name = os.path.basename(db_path)
    statements = []
    
    # Add comment with database info
    statements.append(f"-- Schema for database: {db_name}")
    statements.append(f"-- Generated: {datetime.now().isoformat()}")
    statements.append("")
    
    # Get list of tables
    all_tables = list_tables(db_path)
    
    # Determine which tables to process
    if tables_to_extract:
        tables = [t for t in all_tables if t in tables_to_extract]
    else:
        tables = all_tables
    
    for table_name in tables:
        schema = get_table_schema(db_path, table_name)
        
        if not schema['columns']:
            logger.warning(f"No schema found for table {table_name} in {db_name}")
            continue
        
        # Generate CREATE TABLE statement
        statements.append(f"-- Table: {table_name}")
        create_stmt = get_create_table_statement(table_name, schema['columns'], dialect, drop_tables)
        statements.append(create_stmt)
        statements.append("")
        
        # Generate CREATE INDEX statements
        if not no_create_index and schema['indexes']:
            statements.append(f"-- Indexes for table: {table_name}")
            index_stmts = get_create_index_statements(table_name, schema['indexes'], dialect)
            statements.extend(index_stmts)
            statements.append("")
    
    return statements

def get_insert_statements(db_path, dialect, batch_size=1000, skip_blobs=False, tables_to_extract=None):
    """Generate all INSERT statements for a database"""
    logger = logging.getLogger('db_to_sql')
    
    db_name = os.path.basename(db_path)
    statements = []
    
    # Add comment with database info
    statements.append(f"-- Data for database: {db_name}")
    statements.append(f"-- Generated: {datetime.now().isoformat()}")
    statements.append("")
    
    # Get list of tables
    all_tables = list_tables(db_path)
    
    # Determine which tables to process
    if tables_to_extract:
        tables = [t for t in all_tables if t in tables_to_extract]
    else:
        tables = all_tables
    
    for table_name in tables:
        logger.info(f"Generating INSERT statements for table {table_name} in {db_name}")
        
        # Add comment for this table
        statements.append(f"-- Data for table: {table_name}")
        statements.append("")
        
        # Process data in batches
        batch_num = 0
        for columns, batch in get_table_data_generator(db_path, table_name, batch_size, skip_blobs):
            if not batch:
                if batch_num == 0:
                    logger.info(f"No data found for table {table_name}")
                continue
            
            logger.info(f"Processing batch {batch_num+1} ({len(batch)} rows) for table {table_name}")
            
            # Generate INSERT statements for this batch
            insert_stmts = get_insert_statement(table_name, columns, batch, dialect, batch_size)
            statements.extend(insert_stmts)
            statements.append("")
            
            batch_num += 1
            
            # Force garbage collection
            gc.collect()
    
    return statements

def generate_sql_file(db_files, output_path, dialect='mysql', tables_to_extract=None, batch_size=1000, 
                      skip_blobs=False, schema_only=False, data_only=False, transaction=False,
                      drop_tables=False, no_create_index=False):
    """Generate a SQL file from multiple SQLite databases"""
    logger = logging.getLogger('db_to_sql')
    
    # Create directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Generating SQL file: {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # Add header
        f.write("-- SQL export from SQLite databases\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Format: {dialect}\n")
        f.write("\n")
        
        if transaction:
            if dialect == 'mysql':
                f.write("START TRANSACTION;\n\n")
            elif dialect == 'postgresql':
                f.write("BEGIN;\n\n")
            elif dialect == 'mssql':
                f.write("BEGIN TRANSACTION;\n\n")
            else:
                f.write("BEGIN TRANSACTION;\n\n")
        
        # Process each database
        for db_path in db_files:
            db_name = os.path.basename(db_path)
            logger.info(f"Processing database: {db_name}")
            
            # Generate schema statements
            if not data_only:
                logger.info(f"Generating schema for {db_name}")
                schema_statements = get_create_statements(
                    db_path, dialect, drop_tables, no_create_index, tables_to_extract
                )
                for stmt in schema_statements:
                    f.write(stmt + "\n")
            
            # Generate data statements
            if not schema_only:
                logger.info(f"Generating data for {db_name}")
                data_statements = get_insert_statements(
                    db_path, dialect, batch_size, skip_blobs, tables_to_extract
                )
                for stmt in data_statements:
                    f.write(stmt + "\n")
            
            f.write("\n")
            
            # Force garbage collection
            gc.collect()
        
        if transaction:
            if dialect == 'mysql':
                f.write("COMMIT;\n")
            elif dialect == 'postgresql':
                f.write("COMMIT;\n")
            elif dialect == 'mssql':
                f.write("COMMIT TRANSACTION;\n")
            else:
                f.write("COMMIT;\n")
    
    logger.info(f"SQL file generated successfully: {output_path}")
    return True

def main():
    """Main entry point for the DB to SQL converter"""
    parser = argparse.ArgumentParser(description="Export SQLite database files to SQL statements")
    parser.add_argument("input_directory", help="Directory containing SQLite database (.db) files to convert")
    parser.add_argument("--output", help="Output SQL file path (default: export.sql in input directory)")
    parser.add_argument("--format", choices=["mysql", "postgresql", "sqlite", "mssql"], default="mysql", 
                        help="SQL dialect: 'mysql', 'postgresql', 'sqlite', 'mssql' (default: mysql)")
    parser.add_argument("--tables", help="Comma-separated list of tables to extract (default: all)")
    parser.add_argument("--batch-size", type=int, default=1000, 
                        help="Number of rows to process in each batch (default: 1000)")
    parser.add_argument("--skip-blobs", action="store_true", 
                        help="Skip binary blob fields to reduce output size")
    parser.add_argument("--schema-only", action="store_true",
                        help="Only include schema (CREATE TABLE statements), not data")
    parser.add_argument("--data-only", action="store_true",
                        help="Only include data (INSERT statements), not schema")
    parser.add_argument("--transaction", action="store_true",
                        help="Wrap output in transaction statements (BEGIN/COMMIT)")
    parser.add_argument("--drop-tables", action="store_true",
                        help="Include DROP TABLE statements before CREATE TABLE")
    parser.add_argument("--no-create-index", action="store_true",
                        help="Skip creation of indexes")
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging()
    
    # Check if input directory exists
    if not os.path.exists(args.input_directory):
        logger.error(f"Input directory {args.input_directory} does not exist")
        return 1
    
    # Set default output path if not specified
    if not args.output:
        args.output = os.path.join(args.input_directory, "export.sql")
    
    # Add .sql extension if not present
    if not args.output.lower().endswith('.sql'):
        args.output = args.output + '.sql'
        logger.info(f"Added .sql extension to output filename: {args.output}")
    
    # Find all .db files in the input directory
    db_files = []
    if os.path.isdir(args.input_directory):
        db_files = [os.path.join(args.input_directory, f) for f in os.listdir(args.input_directory) 
                    if f.endswith('.db')]
    elif os.path.isfile(args.input_directory) and args.input_directory.endswith('.db'):
        db_files = [args.input_directory]
    
    if not db_files:
        logger.error(f"No .db files found in {args.input_directory}")
        return 1
    
    logger.info(f"Found {len(db_files)} SQLite database files to process")
    
    # Parse tables list if provided
    tables_to_extract = None
    if args.tables:
        tables_to_extract = [t.strip() for t in args.tables.split(',')]
    
    # Generate SQL file
    success = generate_sql_file(
        db_files,
        args.output,
        args.format,
        tables_to_extract,
        args.batch_size,
        args.skip_blobs,
        args.schema_only,
        args.data_only,
        args.transaction,
        args.drop_tables,
        args.no_create_index
    )
    
    if success:
        logger.info("SQL export completed successfully")
        return 0
    else:
        logger.error("SQL export failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
