# mcnk_processor.py
import struct
from typing import List, Tuple
from adt_core import ADTOffsets

class MCNKProcessor:
    def __init__(self, file_handle):
        self.file = file_handle
        self.positions = []
        self.chunks_reversed = None

    def find_chunks(self):
        # Check MCIN header
        self.file.seek(0)
        header = self.file.read(4)
        self.chunks_reversed = is_chunk_name_reversed(header)
        
        # MCIN offset is always at 0x54
        self.file.seek(0x54)
        mcin_offset = struct.unpack('<I', self.file.read(4))[0]
        self.file.seek(mcin_offset + 8)  # Skip MCIN header
        
        for _ in range(256):
            offset = struct.unpack('<I', self.file.read(4))[0]
            size = struct.unpack('<I', self.file.read(4))[0]
            self.file.seek(8, 1)  # Skip temp1, temp2
            self.positions.append((offset, size))

    def process_chunks(self, offset_data: ADTOffsets):
        # Get initial coordinates for offset calculation
        self.file.seek(self.positions[0][0] + 0x68 + 8)
        old_y = struct.unpack('<f', self.file.read(4))[0]
        old_x = struct.unpack('<f', self.file.read(4))[0]

        y = (1600.0 * (32 - offset_data.y)) / 3.0
        x = (1600.0 * (32 - offset_data.x)) / 3.0

        offset_data.xf = old_x - x
        offset_data.zf = old_y - y

        # Process each MCNK
        for i, (offset, _) in enumerate(self.positions):
            self.file.seek(offset + 0x68 + 8)
            y_pos = (1600.0 * (32 - offset_data.y)) / 3.0 - 100.0 * (i // 16) / 3.0
            x_pos = (1600.0 * (32 - offset_data.x)) / 3.0 - 100.0 * (i % 16) / 3.0
            
            self.file.write(struct.pack('<f', y_pos))
            self.file.write(struct.pack('<f', x_pos))
            
            self.file.seek(offset + 0x68 + 8 + 8)
            height = struct.unpack('<f', self.file.read(4))[0]
            height += offset_data.z_offset
            
            self.file.seek(offset + 0x68 + 8 + 8)
            self.file.write(struct.pack('<f', height))