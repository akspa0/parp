# modf_processor.py
import struct
from adt_core import ADTOffsets

class MODFProcessor:
    def __init__(self, file_handle):
        self.file = file_handle
        self.offset = 0
        self.chunks_reversed = None

    def find_chunk(self):
        self.file.seek(0)
        header = self.file.read(4)
        self.chunks_reversed = is_chunk_name_reversed(header)
        
        # MODF offset is at 0x34
        self.file.seek(0x34)
        self.offset = struct.unpack('<I', self.file.read(4))[0]

    def process_chunk(self, offset_data: ADTOffsets):
        if not self.offset:
            return

        self.file.seek(0x14 + 0x04 + self.offset)
        num_wmos = struct.unpack('<I', self.file.read(4))[0] // 64

        for i in range(num_wmos):
            base_pos = 0x14 + 0x04 + self.offset + 0x08 + 4 + i * 64

            # Update main position
            self.file.seek(base_pos)
            pos = list(struct.unpack('<fff', self.file.read(12)))
            pos[0] += offset_data.xf + offset_data.wdt_x_offset
            pos[1] += offset_data.z_offset + offset_data.wdt_z_offset
            pos[2] += offset_data.zf + offset_data.wdt_y_offset
            
            self.file.seek(base_pos)
            self.file.write(struct.pack('<fff', *pos))

            # Update bounds
            for offset in [24, 36]:
                self.file.seek(base_pos + offset)
                bounds = list(struct.unpack('<fff', self.file.read(12)))
                bounds[0] += offset_data.xf + offset_data.wdt_x_offset
                bounds[1] += offset_data.z_offset + offset_data.wdt_z_offset
                bounds[2] += offset_data.zf + offset_data.wdt_y_offset
                
                self.file.seek(base_pos + offset)
                self.file.write(struct.pack('<fff', *bounds))