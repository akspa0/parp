# main_processor.py
from mcnk_processor import MCNKProcessor
from mddf_processor import MDDFProcessor
from modf_processor import MODFProcessor
from adt_core import ADTOffsets

class ChunkProcessor:
    def __init__(self, file_handle):
        self.file = file_handle
        self.chunks_reversed = None
        self.mcnk = MCNKProcessor(file_handle)
        self.mddf = MDDFProcessor(file_handle)
        self.modf = MODFProcessor(file_handle)

    def process_chunks(self, offset_data: ADTOffsets):
        self.file.seek(0)
        header = self.file.read(4)
        self.chunks_reversed = is_chunk_name_reversed(header)
        
        self.mcnk.find_chunks()
        self.mddf.find_chunk()
        self.modf.find_chunk()
        
        self.mcnk.process_chunks(offset_data)
        self.mddf.process_chunk(offset_data)
        self.modf.process_chunk(offset_data)