import sqlite3
import struct
import os
import logging
import argparse

logging.basicConfig(level=logging.DEBUG)

def connect_db(db_path, create=False):
    if create and not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path))
    return sqlite3.connect(db_path)

def initialize_tables(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lights_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            folder_name TEXT,
            version INTEGER,
            has_count INTEGER,
            count INTEGER,
            m_chunk_x INTEGER,
            m_chunk_y INTEGER,
            m_chunkRadius REAL,
            m_lightLocation_x REAL,
            m_lightLocation_y REAL,
            m_lightLocation_z REAL,
            m_lightRadius REAL,
            m_lightDropoff REAL,
            m_lightName TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            folder_name TEXT,
            file_content BLOB
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS highlight_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            light_id INTEGER,
            highlight_counts TEXT,
            highlight_markers TEXT,
            fog_end TEXT,
            fog_start_scaler TEXT,
            highlight_sky INTEGER,
            sky_data TEXT,
            cloud_mask INTEGER,
            param_data TEXT,
            FOREIGN KEY(light_id) REFERENCES lights_data(id)
        )
    ''')
    conn.commit()

def insert_lights_data(conn, data):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO lights_data (
            file_name, folder_name, version, has_count, count, m_chunk_x, m_chunk_y, m_chunkRadius,
            m_lightLocation_x, m_lightLocation_y, m_lightLocation_z, m_lightRadius, m_lightDropoff, m_lightName
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    light_id = cursor.lastrowid
    conn.commit()
    return light_id

def insert_raw_file(conn, file_name, folder_name, file_content):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO raw_files (
            file_name, folder_name, file_content
        ) VALUES (?, ?, ?)
    ''', (file_name, folder_name, file_content))
    conn.commit()

def parse_additional_lit_data(raw_data, version):
    additional_data = []
    offset = 0
    num_highlights = 0x12 if version != 3 else 0xE

    while offset < len(raw_data):
        try:
            light_index = len(additional_data)
            highlight_counts = struct.unpack(f'{num_highlights}i', raw_data[offset:offset + 4 * num_highlights])
            offset += 4 * num_highlights

            highlight_markers = []
            for _ in range(num_highlights):
                markers = []
                for _ in range(0x20):
                    time, color = struct.unpack('ii', raw_data[offset:offset + 8])
                    markers.append((time, color))
                    offset += 8
                highlight_markers.append(markers)

            fog_end = struct.unpack('32f', raw_data[offset:offset + 4 * 32])
            offset += 4 * 32

            fog_start_scaler = struct.unpack('32f', raw_data[offset:offset + 4 * 32])
            offset += 4 * 32

            highlight_sky = struct.unpack('i', raw_data[offset:offset + 4])[0]
            offset += 4

            sky_data = []
            for _ in range(4):
                sky_values = struct.unpack('32f', raw_data[offset:offset + 4 * 32])
                sky_data.append(sky_values)
                offset += 4 * 32

            cloud_mask = struct.unpack('i', raw_data[offset:offset + 4])[0]
            offset += 4

            if version >= 5:
                param_data = []
                for _ in range(4):
                    param_values = struct.unpack('10f', raw_data[offset:offset + 4 * 10])
                    param_data.append(param_values)
                    offset += 4 * 10
            else:
                param_data = [None] * 4  # Add default empty param_data for versions less than 5

            additional_data.append({
                'highlight_counts': highlight_counts,
                'highlight_markers': highlight_markers,
                'fog_end': fog_end,
                'fog_start_scaler': fog_start_scaler,
                'highlight_sky': highlight_sky,
                'sky_data': sky_data,
                'cloud_mask': cloud_mask,
                'param_data': param_data
            })
        except struct.error:
            break

    return additional_data

def insert_additional_data(conn, light_id, additional_data):
    cursor = conn.cursor()
    for data in additional_data:
        cursor.execute('''
            INSERT INTO highlight_data (
                light_id, highlight_counts, highlight_markers, fog_end, fog_start_scaler,
                highlight_sky, sky_data, cloud_mask, param_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            light_id, str(data['highlight_counts']), str(data['highlight_markers']),
            str(data['fog_end']), str(data['fog_start_scaler']), data['highlight_sky'],
            str(data['sky_data']), data['cloud_mask'], str(data['param_data'])
        ))
    conn.commit()

def process_lit_file(file_path, folder_name, conn):
    with open(file_path, 'rb') as f:
        content = f.read()
    
    file_name = os.path.basename(file_path)
    
    insert_raw_file(conn, file_name, folder_name, content)
    
    version_and_flags = struct.unpack('I', content[:4])[0]
    version = version_and_flags & ~0x80000000
    has_count = version_and_flags & 0x80000000

    offset = 4
    if has_count:
        count = struct.unpack('i', content[offset:offset + 4])[0]
        offset += 4
    else:
        count = 1
    
    for i in range(count):
        if version == 2:
            chunk_x, chunk_y, chunk_radius, loc_x, loc_z, loc_y, radius, dropoff, name = struct.unpack(
                '2i i 3f 2f 32s', content[offset:offset + 60])
            offset += 60
        else:
            chunk_x, chunk_y, chunk_radius, loc_x, loc_z, loc_y, radius, dropoff, name = struct.unpack(
                '2i i 3f 2f 32s', content[offset:offset + 64])
            offset += 64
        
        # Adjust values if not Global Light (-1,-1 chunk)
        if chunk_x != -1 and chunk_y != -1:
            if loc_x != 0: 
                loc_x = (17066.666 - (loc_x / 36))
            if loc_y != 0:    
                loc_y = (17066.666 - (loc_y / 36))
            if loc_z != 0:
                loc_z = loc_z / 36
        else:
            loc_x = loc_x / 36 
            loc_y = loc_y / 36 
            loc_z = loc_z / 36
        
        # Radius and Dropoff seem to be encoded in inches as well.
        radius /= 36
        dropoff /= 36
        name = name.decode('ascii', errors='ignore').strip('\x00')
        
        data = (file_name, folder_name, version, has_count, count, chunk_x, chunk_y, chunk_radius, loc_x, loc_y, loc_z, radius, dropoff, name)
        light_id = insert_lights_data(conn, data)
    
    additional_data = parse_additional_lit_data(content[offset:], version)
    insert_additional_data(conn, light_id, additional_data)

def main():
    parser = argparse.ArgumentParser(description="Parse LIT files and store in SQLite database.")
    parser.add_argument("input_folder", help="Input folder containing the LIT files.")
    parser.add_argument("output_folder", help="Output folder to store the SQLite database.")
    args = parser.parse_args()

    input_folder = args.input_folder
    output_db_path = os.path.join(args.output_folder, 'lights_data.db')

    conn = connect_db(output_db_path, create=True)
    initialize_tables(conn)

    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.endswith('.lit'):
                file_path = os.path.join(root, file)
                folder_name = os.path.relpath(root, input_folder)
                try:
                    process_lit_file(file_path, folder_name, conn)
                    logging.info(f"Processed {file_path} to {output_db_path}")
                except Exception as e:
                    logging.error(f"Error processing {file_path}: {e}")

    conn.close()

if __name__ == "__main__":
    main()
