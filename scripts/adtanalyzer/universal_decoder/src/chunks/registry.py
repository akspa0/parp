"""
Chunk decoder registry and management
"""

from typing import Dict, Type, Optional
from enum import Enum, auto
from .common.base_decoder import ChunkDecoder
from .common.basic_chunks import (
    MVERDecoder,
    MCVTDecoder,
    MCNRDecoder,
    MCLYDecoder,
    MTEXDecoder
)
from .common.map_chunks import (
    MPHDDecoder,
    MAINDecoder,
    MDDFDecoder,
    MODFDecoder,
    MMDXDecoder,
    MMIDDecoder,
    MWMODecoder,
    MWIDDecoder
)
from .common.terrain_chunks import (
    MCNKDecoder,
    MCVTDecoder,
    MCNRDecoder,
    MCLYDecoder,
    MCALDecoder,
    MCSHDecoder,
    MCLQDecoder,
    MCCVDecoder
)
from .alpha.map_chunks import (
    AlphaMPHDDecoder,
    AlphaMAINDecoder,
    AlphaMDNMDecoder,
    AlphaMONMDecoder,
    AlphaMAOCDecoder,
    AlphaMAOFDecoder
)
from .alpha.terrain_chunks import (
    AlphaMCNKDecoder,
    AlphaMCLYDecoder,
    AlphaMCLQDecoder
)

class ChunkFormat(Enum):
    """Supported chunk formats"""
    COMMON = auto()
    ALPHA = auto()
    RETAIL = auto()

class ChunkRegistry:
    """
    Registry for chunk decoders
    Handles format-specific overrides and decoder management
    """
    
    def __init__(self):
        # Dictionary of dictionaries:
        # format -> chunk_name -> decoder_class
        self._decoders: Dict[ChunkFormat, Dict[bytes, Type[ChunkDecoder]]] = {
            ChunkFormat.COMMON: {},
            ChunkFormat.ALPHA: {},
            ChunkFormat.RETAIL: {}
        }
        
        # Register common chunks
        self.register_common_chunks()
        
        # Register format-specific chunks
        self.register_alpha_chunks()
        self.register_retail_chunks()

    def register_decoder(self, 
                        decoder_class: Type[ChunkDecoder], 
                        chunk_format: ChunkFormat = ChunkFormat.COMMON):
        """
        Register a chunk decoder for a specific format
        
        Args:
            decoder_class: The decoder class to register
            chunk_format: The format this decoder is for
        """
        decoder = decoder_class()
        self._decoders[chunk_format][decoder.name] = decoder_class

    def register_common_chunks(self):
        """Register all common chunk decoders"""
        common_decoders = [
            # Basic chunks
            MVERDecoder,
            MCVTDecoder,
            MCNRDecoder,
            MCLYDecoder,
            MTEXDecoder,
            
            # Map chunks - these will be overridden for Alpha format
            MPHDDecoder,
            MAINDecoder,
            MDDFDecoder,
            MODFDecoder,
            
            # Retail model chunks
            MMDXDecoder,
            MMIDDecoder,
            MWMODecoder,
            MWIDDecoder,
            
            # Terrain chunks - these will be overridden for Alpha format
            MCNKDecoder,
            MCVTDecoder,
            MCNRDecoder,
            MCLYDecoder,
            MCALDecoder,
            MCSHDecoder,
            MCLQDecoder,
            MCCVDecoder
        ]
        
        for decoder_class in common_decoders:
            self.register_decoder(decoder_class)

    def register_alpha_chunks(self):
        """Register Alpha format specific chunks"""
        alpha_decoders = [
            # Alpha-specific overrides for map chunks
            AlphaMPHDDecoder,  # Override common MPHD
            AlphaMAINDecoder,  # Override common MAIN
            
            # Alpha-only map chunks
            AlphaMDNMDecoder,  # M2 model names (Alpha)
            AlphaMONMDecoder,  # WMO model names (Alpha)
            AlphaMAOCDecoder,  # Model coordinates
            AlphaMAOFDecoder,  # Model flags
            
            # Alpha-specific overrides for terrain chunks
            AlphaMCNKDecoder,  # Override common MCNK
            AlphaMCLYDecoder,  # Override common MCLY
            AlphaMCLQDecoder   # Override common MCLQ
        ]
        
        for decoder_class in alpha_decoders:
            self.register_decoder(decoder_class, ChunkFormat.ALPHA)

    def register_retail_chunks(self):
        """Register Retail format specific chunks"""
        # Currently using common chunks for Retail
        # Add Retail-specific overrides here if needed
        pass

    def get_decoder(self, 
                   chunk_name: bytes, 
                   preferred_format: ChunkFormat = ChunkFormat.RETAIL) -> Optional[ChunkDecoder]:
        """
        Get a decoder for the specified chunk name
        
        Args:
            chunk_name: Name of the chunk to decode
            preferred_format: Preferred format to use (for format-specific overrides)
            
        Returns:
            ChunkDecoder instance or None if no decoder found
        """
        # Check format-specific decoder first
        if chunk_name in self._decoders[preferred_format]:
            return self._decoders[preferred_format][chunk_name]()
            
        # Fall back to common decoder
        if chunk_name in self._decoders[ChunkFormat.COMMON]:
            return self._decoders[ChunkFormat.COMMON][chunk_name]()
            
        return None

    def supports_chunk(self, chunk_name: bytes, chunk_format: ChunkFormat) -> bool:
        """Check if a decoder exists for the given chunk name and format"""
        return (chunk_name in self._decoders[chunk_format] or 
                chunk_name in self._decoders[ChunkFormat.COMMON])

    def list_supported_chunks(self, chunk_format: ChunkFormat) -> Dict[bytes, str]:
        """
        List all supported chunks for a given format
        
        Returns:
            Dictionary mapping chunk names to decoder class names
        """
        chunks = {}
        
        # Add common chunks
        for name, decoder_class in self._decoders[ChunkFormat.COMMON].items():
            chunks[name] = decoder_class.__name__
            
        # Add/override format-specific chunks
        if chunk_format != ChunkFormat.COMMON:
            for name, decoder_class in self._decoders[chunk_format].items():
                chunks[name] = decoder_class.__name__
                
        return chunks

    def get_format_for_chunk(self, chunk_name: bytes) -> Optional[ChunkFormat]:
        """Determine which format a chunk belongs to"""
        if chunk_name in self._decoders[ChunkFormat.ALPHA]:
            return ChunkFormat.ALPHA
        elif chunk_name in self._decoders[ChunkFormat.RETAIL]:
            return ChunkFormat.RETAIL
        elif chunk_name in self._decoders[ChunkFormat.COMMON]:
            return ChunkFormat.COMMON
        return None

# Global registry instance
chunk_registry = ChunkRegistry()