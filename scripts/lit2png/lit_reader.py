import struct
import os
import math
import logging

MAX_COORD = 17066

logger = logging.getLogger()

def is_valid_light(position, color):
    return any(coord != 0 for coord in position) or any(c != 0 for c in color)

def is_valid_name(name):
    return re.match(r'^[\w\s\-\.,]+$', name) is not None

def has_valid_coordinates(position):
    return all(len(str(abs(coord)).split('.')[-1]) <= 12 for coord in position)

def read_lit_file(file_path, max_lights, track_empty_named_lights=True):
    bad_lights = []
    try:
        with open(file_path, 'rb') as file:
            header = file.read(4)
            version = struct.unpack('B', header[0:1])[0]
            logger.debug(f"Version: {version}")
            
            if version == 2:
                file_format = 'old'
                header_size = 4  # Old format has a 4-byte header
                file.seek(0)  # Reset to start
            else:
                file_format = 'new'
                header_size = 8
            
            entry_size = 60 if file_format == 'old' else 64
            
            if file_format == 'new':
                file.seek(0)
                header = file.read(header_size)
                version = struct.unpack('B', header[0:1])[0]
                reported_light_count = struct.unpack('I', header[4:8])[0]
            else:
                file.seek(0)
                header = file.read(header_size)
                version = struct.unpack('B', header[0:1])[0]
                reported_light_count = -1
            
            file_size = os.path.getsize(file_path)
            actual_light_count = min((file_size - header_size) // entry_size, max_lights)
            
            logger.debug(f"File format: {file_format}")
            logger.debug(f"Reported Light Count: {reported_light_count}")
            logger.debug(f"Calculated Actual Light Count: {actual_light_count}")
            
            lights = []
            unnamed_light_count = 0
            for i in range(actual_light_count):
                light_data = file.read(entry_size)
                try:
                    if file_format == 'new':
                        chunk = struct.unpack('2i', light_data[0:8])
                        chunk_radius = struct.unpack('i', light_data[8:12])[0]
                        position = struct.unpack('3f', light_data[12:24])
                        light_radius = struct.unpack('f', light_data[24:28])[0] / 36
                        light_dropoff = struct.unpack('f', light_data[28:32])[0] / 36
                        light_name = light_data[32:64].decode('utf-8', 'ignore').replace('\x00', '-').strip('-')
                        color = struct.unpack('4B', light_data[32:36])
                    else:
                        chunk = struct.unpack('2i', light_data[0:8])
                        chunk_radius = struct.unpack('i', light_data[8:12])[0]
                        position = struct.unpack('3f', light_data[12:24])
                        light_radius = struct.unpack('f', light_data[24:28])[0] / 36
                        light_dropoff = struct.unpack('f', light_data[28:32])[0] / 36
                        light_name = light_data[32:60].decode('utf-8', 'ignore').replace('\x00', '-').strip('-')
                        color = (255, 255, 255, 255)  # Default white color for old format without explicit color

                    if any(math.isnan(coord) for coord in position):
                        logger.debug(f"Converting NaN values to 0 in file {file_path} at light {len(lights)}")
                        position = [0 if math.isnan(coord) else coord for coord in position]
                    
                    if abs(position[0]) > MAX_COORD or abs(position[1]) > MAX_COORD:
                        position = [coord / 2 for coord in position]

                    if light_name == "Global Light" or (is_valid_light(position, color) and has_valid_coordinates(position)):
                        lights.append({
                            "chunk": chunk,
                            "chunk_radius": chunk_radius,
                            "position": {
                                "x": position[0] / 36,
                                "y": position[2] / 36,  # Swap y and z
                                "z": position[1] / 36  # Swap z and y
                            },
                            "light_radius": light_radius,
                            "light_dropoff": light_dropoff,
                            "light_name": light_name,
                            "color": color
                        })
                    else:
                        unnamed_light_count += 1
                        bad_lights.append({
                            "chunk": chunk,
                            "chunk_radius": chunk_radius,
                            "position": position,
                            "light_radius": light_radius,
                            "light_dropoff": light_dropoff,
                            "light_name": light_name,
                            "color": color
                        })
                except struct.error as e:
                    logger.error(f"Struct error reading light {i}: {e}")
                    bad_lights.append({
                        "raw_data": light_data.hex()
                    })
            
            return {
                "version": version,
                "light_count": actual_light_count,
                "lights": lights,
                "unnamed_light_count": unnamed_light_count,
                "bad_lights": bad_lights
            }
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None
