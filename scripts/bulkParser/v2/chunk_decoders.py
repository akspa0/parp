"""
ADT Chunk Decoders
Contains decoder classes for all chunk types in ADT files
"""

import struct
import logging

logger = logging.getLogger("parser")

class ChunkDecoder:
    """Base class for chunk decoders"""
    @staticmethod
    def decode(data):
        return {"raw_data": data}, None

class MCVTDecoder(ChunkDecoder):
    """Decoder for MCVT chunk - Heightmap information"""
    
    @staticmethod
    def decode(data):
        """Decode MCVT data - 145 height vertices"""
        if len(data) >= 145 * 4:
            # Each height is a 4-byte float, total of 9x9 + 8x8 = 145 vertices
            heights = list(struct.unpack('<' + 'f' * 145, data[:145*4]))
            return {"heights": heights}, None
        return {"heights": []}, "Invalid MCVT data length"

class MCNRDecoder(ChunkDecoder):
    """Decoder for MCNR chunk - Normal map information"""
    
    @staticmethod
    def decode(data):
        """Decode MCNR data - 145 normal vectors + 13 bytes of padding"""
        if len(data) >= 145 * 3:
            normals = []
            # Each normal is 3 signed bytes, scaled from -127..127 to -1..1
            for i in range(145):
                nx, ny, nz = struct.unpack('<bbb', data[i*3:i*3+3])
                normals.append((nx/127.0, ny/127.0, nz/127.0))
            
            # Extract padding if present (13 bytes)
            padding = None
            if len(data) >= (145 * 3) + 13:
                padding = data[(145 * 3):(145 * 3) + 13]
            
            return {"normals": normals, "padding": padding}, None
        return {"normals": []}, "Invalid MCNR data length"

class MCLYDecoder(ChunkDecoder):
    """Decoder for MCLY chunk - Texture layer information"""
    
    @staticmethod
    def decode(data):
        """Decode MCLY data - Texture layers, 16 bytes per layer"""
        layers = []
        layer_count = len(data) // 16  # Each layer is 16 bytes
        
        for i in range(layer_count):
            layer_data = data[i*16:(i+1)*16]
            texture_id, flags = struct.unpack('<II', layer_data[:8])
            offset_mcal, effect_id = struct.unpack('<II', layer_data[8:16])
            
            # Extract specific flags
            animation_rotation = (flags & 0x7)  # 3 bits, each tick is 45°
            animation_speed = ((flags >> 3) & 0x7)  # 3 bits
            animation_enabled = bool(flags & 0x40)  # 1 bit
            overbright = bool(flags & 0x80)  # 1 bit
            use_alpha_map = bool(flags & 0x100)  # 1 bit
            alpha_map_compressed = bool(flags & 0x200)  # 1 bit
            use_cube_map_reflection = bool(flags & 0x400)  # 1 bit
            
            layers.append({
                'textureId': texture_id,
                'flags': flags,
                'flagDetails': {
                    'animation_rotation': animation_rotation,
                    'animation_speed': animation_speed,
                    'animation_enabled': animation_enabled,
                    'overbright': overbright,
                    'use_alpha_map': use_alpha_map,
                    'alpha_map_compressed': alpha_map_compressed,
                    'use_cube_map_reflection': use_cube_map_reflection
                },
                'offsetInMCAL': offset_mcal,
                'effectId': effect_id
            })
        
        return {"layers": layers}, None

class MCALDecoder(ChunkDecoder):
    """Decoder for MCAL chunk - Alpha map data"""
    
    @staticmethod
    def decode(data, mcly_flags=None):
        """
        Decode MCAL data - Alpha maps for additional texture layers
        
        The format depends on flags in the MCLY chunk:
        - If MCLY flag 0x200 is set, the alpha map is compressed
        - The size also depends on WDT flags
        """
        compressed = False
        
        # If we have mcly_flags, check if the alpha map is compressed
        if mcly_flags and any(layer['flagDetails']['alpha_map_compressed'] for layer in mcly_flags):
            compressed = True
        
        # For simplicity in this implementation, we'll store the raw data
        # and metadata about its format
        return {
            "alpha_map": data,
            "mode": {
                "compressed": compressed,
                "size": len(data)
            }
        }, None

class MCSHDecoder(ChunkDecoder):
    """Decoder for MCSH chunk - Shadow map data"""
    
    @staticmethod
    def decode(data):
        """
        Decode MCSH data - Shadow map stored as a 64x64 bit array
        Each bit represents a shadow state (0=no shadow, 1=shadow)
        """
        # For simplicity, just store the raw shadow map data
        return {"shadow_map": data}, None

class MCLQDecoder(ChunkDecoder):
    """Decoder for MCLQ chunk - Liquid data"""
    
    @staticmethod
    def decode(data):
        """
        Decode MCLQ data - Liquid information
        Format depends on the liquid type specified in the MCNK flags
        """
        # For simplicity, we'll store the raw data and extract any height information
        has_heights = False
        heights = []
        
        if len(data) >= 9*9*4:  # Check if it has at least 81 floats for heights
            heights = list(struct.unpack('<' + 'f' * 81, data[:81*4]))
            has_heights = True
        
        return {
            "raw_data": data,
            "has_heights": has_heights,
            "heights": heights
        }, None

class MCCVDecoder(ChunkDecoder):
    """Decoder for MCCV chunk - Vertex shading information"""
    
    @staticmethod
    def decode(data):
        """Decode MCCV data - 145 RGBA color values for vertices"""
        colors = []
        if len(data) >= 145 * 4:
            for i in range(145):
                b, g, r, a = struct.unpack('<BBBB', data[i*4:i*4+4])
                colors.append((r, g, b, a))
            return {"vertex_colors": colors}, None
        return {"vertex_colors": []}, "Invalid MCCV data length"

class MCLVDecoder(ChunkDecoder):
    """Decoder for MCLV chunk - Vertex lighting information (Cataclysm+)"""
    
    @staticmethod
    def decode(data):
        """Decode MCLV data - 145 RGBA lighting values for vertices"""
        lighting = []
        if len(data) >= 145 * 4:
            for i in range(145):
                b, g, r, a = struct.unpack('<BBBB', data[i*4:i*4+4])
                lighting.append((r, g, b, a))
            return {"vertex_lighting": lighting}, None
        return {"vertex_lighting": []}, "Invalid MCLV data length"

class MCRFDecoder(ChunkDecoder):
    """Decoder for MCRF chunk - Doodad and object references"""
    
    @staticmethod
    def decode(data, doodad_count=0, obj_count=0):
        """
        Decode MCRF data - References to doodads and objects
        
        Args:
            data: The chunk data
            doodad_count: Number of doodad references from MCNK header
            obj_count: Number of object references from MCNK header
        """
        model_refs = []
        obj_refs = []
        
        if not doodad_count and not obj_count:
            # If we don't have counts, assume all are model references
            # (We'll fix this later when proper counts are available)
            count = len(data) // 4
            for i in range(count):
                ref = struct.unpack('<I', data[i*4:(i+1)*4])[0]
                model_refs.append(ref)
        else:
            # Parse based on the provided counts
            pos = 0
            
            # Read doodad references
            for i in range(doodad_count):
                if pos + 4 <= len(data):
                    ref = struct.unpack('<I', data[pos:pos+4])[0]
                    model_refs.append(ref)
                    pos += 4
            
            # Read object references
            for i in range(obj_count):
                if pos + 4 <= len(data):
                    ref = struct.unpack('<I', data[pos:pos+4])[0]
                    obj_refs.append(ref)
                    pos += 4
        
        return {
            "model_references": model_refs,
            "object_references": obj_refs
        }, None

class MCRDDecoder(ChunkDecoder):
    """Decoder for MCRD chunk - Doodad references (Cataclysm+)"""
    
    @staticmethod
    def decode(data):
        """Decode MCRD data - References to doodads"""
        refs = []
        count = len(data) // 4
        for i in range(count):
            ref = struct.unpack('<I', data[i*4:(i+1)*4])[0]
            refs.append(ref)
        return {"doodad_references": refs}, None

class MCRWDecoder(ChunkDecoder):
    """Decoder for MCRW chunk - WMO references (Cataclysm+)"""
    
    @staticmethod
    def decode(data):
        """Decode MCRW data - References to WMOs"""
        refs = []
        count = len(data) // 4
        for i in range(count):
            ref = struct.unpack('<I', data[i*4:(i+1)*4])[0]
            refs.append(ref)
        return {"wmo_references": refs}, None

class MCMTDecoder(ChunkDecoder):
    """Decoder for MCMT chunk - Material IDs (Cataclysm+)"""
    
    @staticmethod
    def decode(data):
        """Decode MCMT data - Material IDs"""
        materials = []
        count = len(data)  # Each ID is 1 byte
        for i in range(count):
            material_id = struct.unpack('<B', data[i:i+1])[0]
            materials.append(material_id)
        return {"material_ids": materials}, None

class MCDDDecoder(ChunkDecoder):
    """Decoder for MCDD chunk - Detail doodad settings (Cataclysm+)"""
    
    @staticmethod
    def decode(data):
        """Decode MCDD data - Detail doodad settings"""
        # The format is a bit array for 8x8 cells
        disable_data = data
        return {"disable_data": disable_data}, None

class MAMPDecoder(ChunkDecoder):
    """Decoder for MAMP chunk - Alpha map parameters (Cataclysm+)"""
    
    @staticmethod
    def decode(data):
        """Decode MAMP data - Alpha map parameters"""
        if len(data) >= 1:
            value = struct.unpack('<B', data[0:1])[0]
            return {"value": value}, None
        return {"value": 0}, "Invalid MAMP data length"

class MTEXDecoder(ChunkDecoder):
    """Decoder for MTEX chunk - Texture filenames"""
    
    @staticmethod
    def decode(data):
        """Decode MTEX data - Null-terminated texture filenames"""
        textures = []
        # Split by null terminators and decode each string
        offset = 0
        while offset < len(data):
            end = data.find(b'\0', offset)
            if end == -1:
                # No more null terminators, use the rest of the data
                if offset < len(data):
                    textures.append(data[offset:].decode('utf-8', 'replace'))
                break
            
            if end > offset:
                textures.append(data[offset:end].decode('utf-8', 'replace'))
            offset = end + 1
        
        return {"textures": textures}, None

class MDIDDecoder(ChunkDecoder):
    """Decoder for MDID chunk - Diffuse texture FileDataIDs"""
    
    @staticmethod
    def decode(data):
        """Decode MDID data - Array of FileDataIDs for diffuse textures"""
        diffuse_ids = []
        count = len(data) // 4
        for i in range(count):
            file_data_id = struct.unpack('<I', data[i*4:(i+1)*4])[0]
            diffuse_ids.append(file_data_id)
        return {"diffuse_texture_ids": diffuse_ids}, None

class MHIDDecoder(ChunkDecoder):
    """Decoder for MHID chunk - Height texture FileDataIDs"""
    
    @staticmethod
    def decode(data):
        """Decode MHID data - Array of FileDataIDs for height textures"""
        height_ids = []
        count = len(data) // 4
        for i in range(count):
            file_data_id = struct.unpack('<I', data[i*4:(i+1)*4])[0]
            height_ids.append(file_data_id)
        return {"height_texture_ids": height_ids}, None

class MTXFDecoder(ChunkDecoder):
    """Decoder for MTXF chunk - Texture flags (WotLK+)"""
    
    @staticmethod
    def decode(data):
        """Decode MTXF data - Texture flags"""
        flags = []
        count = len(data) // 4
        for i in range(count):
            flag = struct.unpack('<I', data[i*4:(i+1)*4])[0]
            # Decode specific flags
            disable_shading = bool(flag & 0x1)
            texture_scale = (flag >> 4) & 0xF  # 4 bits starting at bit 4
            
            flags.append({
                'raw_flag': flag,
                'disable_shading': disable_shading,
                'texture_scale': texture_scale
            })
        return {"texture_flags": flags}, None

class MTXPDecoder(ChunkDecoder):
    """Decoder for MTXP chunk - Texture parameters (MoP+)"""
    
    @staticmethod
    def decode(data):
        """Decode MTXP data - Texture parameters"""
        params = []
        entry_size = 16  # Each entry is 16 bytes
        count = len(data) // entry_size
        
        for i in range(count):
            entry_data = data[i*entry_size:(i+1)*entry_size]
            flags, height_scale, height_offset, padding = struct.unpack('<Iffi', entry_data)
            
            # Decode flags (same as MTXF)
            disable_shading = bool(flags & 0x1)
            texture_scale = (flags >> 4) & 0xF
            
            params.append({
                'flags': flags,
                'flag_details': {
                    'disable_shading': disable_shading,
                    'texture_scale': texture_scale
                },
                'height_scale': height_scale,
                'height_offset': height_offset,
                'padding': padding
            })
        
        return {"texture_params": params}, None

class MH2ODecoder(ChunkDecoder):
    """Decoder for MH2O chunk - Water data (WotLK+)"""
    
    @staticmethod
    def decode(data):
        """
        Decode MH2O data - Water information
        
        This is a complex chunk with multiple parts and a lot of indirection.
        For simplicity, we'll store the raw data and perform a basic analysis.
        """
        # First 256 entries are offsets (16x16 chunks, 8 bytes each)
        header_size = 256 * 8
        if len(data) < header_size:
            return {"error": "MH2O data too short"}, "MH2O data too short"
        
        headers = []
        for i in range(256):
            offset_pos = i * 8
            instance_offset, layer_count = struct.unpack('<II', data[offset_pos:offset_pos+8])
            headers.append({
                'offset_instances': instance_offset,
                'layer_count': layer_count
            })
        
        # For now, just store the raw data - this is a complex chunk
        # that requires special handling
        return {
            "headers": headers,
            "raw_data": data
        }, None

class MFBODecoder(ChunkDecoder):
    """Decoder for MFBO chunk - Bounding box for flying"""
    
    @staticmethod
    def decode(data):
        """Decode MFBO data - Flying bounding box"""
        if len(data) < 72:  # 2 planes * 9 shorts * 2 bytes
            return {"error": "MFBO data too short"}, "MFBO data too short"
        
        maximum_plane = []
        minimum_plane = []
        
        # First plane (maximum)
        for i in range(9):
            height = struct.unpack('<h', data[i*2:i*2+2])[0]
            maximum_plane.append(height)
        
        # Second plane (minimum)
        for i in range(9):
            height = struct.unpack('<h', data[36+i*2:36+i*2+2])[0]
            minimum_plane.append(height)
        
        return {
            "maximum_plane": maximum_plane,
            "minimum_plane": minimum_plane
        }, None

class MDDFDecoder(ChunkDecoder):
    """Decoder for MDDF chunk - M2 model placement information"""
    
    @staticmethod
    def decode(data):
        """Decode MDDF data - M2 model placements"""
        entries = []
        entry_size = 36  # Each MDDF entry is 36 bytes
        count = len(data) // entry_size
        
        for i in range(count):
            entry_data = data[i*entry_size:(i+1)*entry_size]
            nameId, uniqueId = struct.unpack('<II', entry_data[0:8])
            posx, posy, posz = struct.unpack('<fff', entry_data[8:20])
            rotx, roty, rotz = struct.unpack('<fff', entry_data[20:32])
            scale, flags = struct.unpack('<HH', entry_data[32:36])
            
            # Check if nameId is a FileDataID (Legion+)
            is_file_data_id = bool(flags & 0x40)  # mddf_entry_is_filedata_id = 0x40
            
            entries.append({
                'nameId': nameId,
                'uniqueId': uniqueId,
                'position': {'x': posx, 'y': posy, 'z': posz},
                'rotation': {'x': rotx, 'y': roty, 'z': rotz},
                'scale': scale,
                'flags': flags,
                'is_file_data_id': is_file_data_id  # Flag to indicate FileDataID usage
            })
        
        return {"entries": entries}, None

class MODFDecoder(ChunkDecoder):
    """Decoder for MODF chunk - WMO model placement information"""
    
    @staticmethod
    def decode(data):
        """Decode MODF data - WMO model placements"""
        entries = []
        entry_size = 64  # Each MODF entry is 64 bytes
        count = len(data) // entry_size
        
        for i in range(count):
            entry_data = data[i*64:(i+1)*64]
            nameId, uniqueId = struct.unpack('<II', entry_data[0:8])
            posx, posy, posz = struct.unpack('<fff', entry_data[8:20])
            rotx, roty, rotz = struct.unpack('<fff', entry_data[20:32])
            lx, ly, lz = struct.unpack('<fff', entry_data[32:44])
            ux, uy, uz = struct.unpack('<fff', entry_data[44:56])
            flags, doodadSet, nameSet, scale = struct.unpack('<HHHH', entry_data[56:64])
            
            # Check if nameId is a FileDataID (Legion+)
            is_file_data_id = bool(flags & 0x8)  # modf_entry_is_filedata_id = 0x8
            
            entries.append({
                'nameId': nameId,
                'uniqueId': uniqueId,
                'position': {'x': posx, 'y': posy, 'z': posz},
                'rotation': {'x': rotx, 'y': roty, 'z': rotz},
                'extents_lower': {'x': lx, 'y': ly, 'z': lz},
                'extents_upper': {'x': ux, 'y': uy, 'z': uz},
                'flags': flags,
                'doodadSet': doodadSet,
                'nameSet': nameSet,
                'scale': scale,
                'is_file_data_id': is_file_data_id  # Flag to indicate FileDataID usage
            })
        
        return {"entries": entries}, None

class MVERDecoder(ChunkDecoder):
    """Decoder for MVER chunk - Version information"""
    
    @staticmethod
    def decode(data):
        """Decode MVER data - Version number"""
        if len(data) >= 4:
            version = struct.unpack('<I', data[0:4])[0]
            return {"version": version}, None
        return {"version": 0}, "Invalid MVER data length"

class MCNKSubChunkHelper:
    """Helper class for extracting sub-chunks from MCNK data"""
    
    @staticmethod
    def extract_sub_chunks(data, mcnk_offset=0):
        """
        Extract all sub-chunks from MCNK data
        
        Args:
            data: The full MCNK chunk data
            mcnk_offset: Offset to the start of the MCNK chunk in the file
        
        Returns:
            Dictionary of sub-chunks indexed by signature
        """
        sub_chunks = {}
        pos = 128  # Start after header
        
        while pos + 8 <= len(data):
            sub_chunk_name = data[pos:pos+4]
            if pos + 8 > len(data):
                break
            
            sub_chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
            if pos + 8 + sub_chunk_size > len(data):
                break
            
            sub_chunk_data = data[pos+8:pos+8+sub_chunk_size]
            
            # Store the sub-chunk
            if sub_chunk_name not in sub_chunks:
                sub_chunks[sub_chunk_name] = []
            
            sub_chunks[sub_chunk_name].append({
                'offset': pos + mcnk_offset,  # Absolute offset in file
                'data': sub_chunk_data
            })
            
            pos += 8 + sub_chunk_size
        
        return sub_chunks

class MCNKDecoder(ChunkDecoder):
    """Enhanced decoder for MCNK chunk and all its sub-chunks"""
    
    # Map of sub-chunk signatures to decoder functions
    SUB_CHUNK_DECODERS = {
        b'MCVT': MCVTDecoder.decode,
        b'MCNR': MCNRDecoder.decode,
        b'MCLY': MCLYDecoder.decode,
        b'MCAL': MCALDecoder.decode,
        b'MCSH': MCSHDecoder.decode,
        b'MCLQ': MCLQDecoder.decode,
        b'MCCV': MCCVDecoder.decode,
        b'MCLV': MCLVDecoder.decode,
        b'MCRF': MCRFDecoder.decode,
        b'MCRD': MCRDDecoder.decode,
        b'MCRW': MCRWDecoder.decode,
        b'MCMT': MCMTDecoder.decode,
        b'MCDD': MCDDDecoder.decode,
    }
    
    @staticmethod
    def decode(data, chunk_offset=0):
        """
        Decode MCNK data - Terrain chunk with sub-chunks
        
        Args:
            data: The chunk data
            chunk_offset: Offset to the start of the chunk in the file
        
        Returns:
            Dictionary with header info and sub-chunks
        """
        # Parse MCNK header (128 bytes)
        if len(data) < 128:
            return {"error": "MCNK data too short"}, "MCNK data too short"
        
        # Extract header fields
        flags_value = struct.unpack('<I', data[0:4])[0]
        flags = {
            'has_mcsh': bool(flags_value & 0x01),
            'impass': bool(flags_value & 0x02),
            'lq_river': bool(flags_value & 0x04),
            'lq_ocean': bool(flags_value & 0x08),
            'lq_magma': bool(flags_value & 0x10),
            'lq_slime': bool(flags_value & 0x20),
            'has_mccv': bool(flags_value & 0x40),
            'unknown_0x80': bool(flags_value & 0x80),
            'do_not_fix_alpha_map': bool(flags_value & 0x8000),
            'high_res_holes': bool(flags_value & 0x10000),
        }
        
        index_x = struct.unpack('<I', data[4:8])[0]
        index_y = struct.unpack('<I', data[8:12])[0]
        n_layers = struct.unpack('<I', data[12:16])[0]
        n_doodad_refs = struct.unpack('<I', data[16:20])[0]
        
        # Get offsets depending on version (pre-5.3 vs post-5.3)
        if flags['high_res_holes']:
            # Post-5.3 format with holes_high_res at 0x14
            holes_high_res = struct.unpack('<Q', data[20:28])[0]
            ofs_layer = struct.unpack('<I', data[28:32])[0]
            ofs_height = 0
            ofs_normal = 0
        else:
            # Pre-5.3 format with ofsHeight and ofsNormal
            ofs_height = struct.unpack('<I', data[20:24])[0]
            ofs_normal = struct.unpack('<I', data[24:28])[0]
            ofs_layer = struct.unpack('<I', data[28:32])[0]
            holes_high_res = 0
        
        ofs_refs = struct.unpack('<I', data[32:36])[0]
        ofs_alpha = struct.unpack('<I', data[36:40])[0]
        size_alpha = struct.unpack('<I', data[40:44])[0]
        ofs_shadow = struct.unpack('<I', data[44:48])[0]
        size_shadow = struct.unpack('<I', data[48:52])[0]
        areaid = struct.unpack('<I', data[52:56])[0]
        n_map_obj_refs = struct.unpack('<I', data[56:60])[0]
        holes_low_res = struct.unpack('<H', data[60:62])[0]
        unknown_but_used = struct.unpack('<H', data[62:64])[0]
        
        # Skip ReallyLowQualityTextureingMap and noEffectDoodad for now
        # These occupy 0x50 to 0x58 (64-88)
        
        ofs_snd_emitters = struct.unpack('<I', data[88:92])[0]
        n_snd_emitters = struct.unpack('<I', data[92:96])[0]
        ofs_liquid = struct.unpack('<I', data[96:100])[0]
        size_liquid = struct.unpack('<I', data[100:104])[0]
        
        # Position vector
        pos_x, pos_y, pos_z = struct.unpack('<fff', data[104:116])
        
        # Additional fields for newer versions
        ofs_mccv = 0
        ofs_mclv = 0
        if len(data) >= 120:
            ofs_mccv = struct.unpack('<I', data[116:120])[0]
        if len(data) >= 124:
            ofs_mclv = struct.unpack('<I', data[120:124])[0]
        
        # Extract sub-chunks
        sub_chunks = MCNKSubChunkHelper.extract_sub_chunks(data, chunk_offset)
        
        # Decode each sub-chunk
        decoded_sub_chunks = {}
        for sub_chunk_name, sub_chunk_list in sub_chunks.items():
            sub_chunk_name_str = sub_chunk_name.decode('utf-8', 'replace')
            
            if sub_chunk_name in MCNKDecoder.SUB_CHUNK_DECODERS:
                decoder = MCNKDecoder.SUB_CHUNK_DECODERS[sub_chunk_name]
                
                # Special case for MCRF which needs doodad and object counts
                if sub_chunk_name == b'MCRF':
                    for sub_chunk in sub_chunk_list:
                        decoded_data, _ = decoder(sub_chunk['data'], n_doodad_refs, n_map_obj_refs)
                        decoded_sub_chunks[sub_chunk_name_str] = decoded_data
                # Special case for MCAL which needs MCLY flags
                elif sub_chunk_name == b'MCAL' and b'MCLY' in sub_chunks:
                    mcly_data, _ = MCLYDecoder.decode(sub_chunks[b'MCLY'][0]['data'])
                    for sub_chunk in sub_chunk_list:
                        decoded_data, _ = decoder(sub_chunk['data'], mcly_data.get('layers'))
                        decoded_sub_chunks[sub_chunk_name_str] = decoded_data
                else:
                    for sub_chunk in sub_chunk_list:
                        decoded_data, _ = decoder(sub_chunk['data'])
                        decoded_sub_chunks[sub_chunk_name_str] = decoded_data
            else:
                # Just store raw data for unknown sub-chunks
                for sub_chunk in sub_chunk_list:
                    decoded_sub_chunks[sub_chunk_name_str] = {
                        'raw_data': sub_chunk['data']
                    }
        
        header = {
            'flags': flags,
            'flags_raw': flags_value,
            'index_x': index_x,
            'index_y': index_y,
            'n_layers': n_layers,
            'n_doodad_refs': n_doodad_refs,
            'holes_high_res': holes_high_res if flags['high_res_holes'] else None,
            'ofs_height': ofs_height if not flags['high_res_holes'] else None,
            'ofs_normal': ofs_normal if not flags['high_res_holes'] else None,
            'ofs_layer': ofs_layer,
            'ofs_refs': ofs_refs,
            'ofs_alpha': ofs_alpha,
            'size_alpha': size_alpha,
            'ofs_shadow': ofs_shadow,
            'size_shadow': size_shadow,
            'areaid': areaid,
            'n_map_obj_refs': n_map_obj_refs,
            'holes_low_res': holes_low_res,
            'unknown_but_used': unknown_but_used,
            'ofs_snd_emitters': ofs_snd_emitters,
            'n_snd_emitters': n_snd_emitters,
            'ofs_liquid': ofs_liquid,
            'size_liquid': size_liquid,
            'position': {'x': pos_x, 'y': pos_y, 'z': pos_z},
            'ofs_mccv': ofs_mccv,
            'ofs_mclv': ofs_mclv
        }
        
        return {
            'header': header,
            'sub_chunks': decoded_sub_chunks
        }, None

# Pre-compile common chunk decoders
CHUNK_DECODERS = {
    b'MCNK': MCNKDecoder.decode,
    b'MVER': MVERDecoder.decode,
    b'MAMP': MAMPDecoder.decode,
    b'MTXF': MTXFDecoder.decode,
    b'MTXP': MTXPDecoder.decode,
    b'MH2O': MH2ODecoder.decode,
    b'MCMT': MCMTDecoder.decode,
    b'MTEX': MTEXDecoder.decode,
    b'MDDF': MDDFDecoder.decode,
    b'MODF': MODFDecoder.decode,
    b'MDID': MDIDDecoder.decode,
    b'MHID': MHIDDecoder.decode,
    b'MFBO': MFBODecoder.decode,
}
