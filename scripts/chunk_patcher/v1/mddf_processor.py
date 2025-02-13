# mddf_processor.py
import struct
from adt_core import ADTOffsets

class MDDFProcessor:
    def __init__(self, file_handle):
        self.file = file_handle
        self.offset = 0
        self.chunks_reversed = None

    def find_chunk(self):
        self.file.seek(0)
        header = self.file.read(4)
        self.chunks_reversed = is_chunk_name_reversed(header)
        
        # MDDF offset is at 0x30
        self.file.seek(0x30)
        self.offset = struct.unpack('<I', self.file.read(4))[0]

    def process_chunk(self, offset_data: ADTOffsets):
        if not self.offset:
            return

        self.file.seek(0x14 + 0x04 + self.offset)
        num_doodads = struct.unpack('<I', self.file.read(4))[0] // 36

        self.file.seek(8, 1)
        for _ in range(num_doodads):
            pos = list(struct.unpack('<fff', self.file.read(12)))
            pos[0] += offset_data.xf
            pos[2] += offset_data.zf
            
            self.file.seek(-12, 1)
            self.file.write(struct.pack('<fff', *pos))
            self.file.seek(24, 1)