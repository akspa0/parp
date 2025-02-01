import sqlite3

def get_table_names(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    return [table[0] for table in tables]

def get_table_data(db_path, table_name):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    conn.close()
    return rows

def create_diff_db(diff_db_path):
    conn = sqlite3.connect(diff_db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS changes (table_name TEXT, action TEXT, data TEXT)")
    conn.commit()
    conn.close()

def log_change(diff_db_path, table_name, action, row):
    conn = sqlite3.connect(diff_db_path)
    cursor = conn.cursor()
    data = ', '.join([f"'{str(val)}'" for val in row])
    cursor.execute("INSERT INTO changes (table_name, action, data) VALUES (?, ?, ?)", (table_name, action, data))
    conn.commit()
    conn.close()

def compare_dbs(db1_path, db2_path, diff_db_path):
    tables1 = set(get_table_names(db1_path))
    tables2 = set(get_table_names(db2_path))

    # Find common tables
    common_tables = tables1.intersection(tables2)

    create_diff_db(diff_db_path)

    for table in common_tables:
        data1 = get_table_data(db1_path, table)
        data2 = get_table_data(db2_path, table)

        # Create sets of tuples for comparison
        tuple_data1 = [tuple(row) for row in data1]
        tuple_data2 = [tuple(row) for row in data2]

        # Compare records
        diff1 = set(tuple_data1).difference(set(tuple_data2))
        diff2 = set(tuple_data2).difference(set(tuple_data1))

        # Log unique differences with indicators
        for row in diff1:
            log_change(diff_db_path, table, '+', row)

        for row in diff2:
            log_change(diff_db_path, table, '-', row)

# Example usage
compare_dbs('PVPZone01_053_1_25_25-00.db', 'PVPZone01_055_1_25_25-00.db', 'differences.db')
