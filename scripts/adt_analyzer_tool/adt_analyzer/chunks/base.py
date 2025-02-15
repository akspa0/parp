"""Base chunk parser."""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ChunkParsingError(Exception):
    """Raised when chunk parsing fails."""
    pass

class BaseChunk:
    """Base class for chunk parsers."""
    
    def __init__(self, header: Optional[Dict[str, Any]], data: bytes):
        """Initialize chunk parser.
        
        Args:
            header: Optional chunk header info
            data: Raw chunk data (without header)
        """
        self.header = header
        self.data = data
    
    def parse(self) -> Dict[str, Any]:
        """Parse chunk data.
        
        Returns:
            Dictionary containing parsed data
        
        Raises:
            ChunkParsingError: If chunk data is invalid
        """
        raise NotImplementedError("Subclasses must implement parse()")
    
    def _validate_size(self, expected_size: int, allow_larger: bool = False) -> bool:
        """Validate chunk data size.
        
        Args:
            expected_size: Expected size in bytes
            allow_larger: If True, allow data to be larger than expected
        
        Returns:
            True if size is valid, False otherwise
        """
        actual_size = len(self.data)
        
        # Allow empty chunks
        if actual_size == 0:
            return True
            
        # Check if data is too small
        if actual_size < expected_size:
            logger.warning(f"Chunk data too small: {actual_size} < {expected_size}")
            return False
            
        # Check if data is too large
        if not allow_larger and actual_size > expected_size:
            logger.warning(f"Chunk data too large: {actual_size} > {expected_size}")
            return False
            
        return True
    
    def _validate_entry_size(self, entry_size: int) -> bool:
        """Validate chunk data size is multiple of entry size.
        
        Args:
            entry_size: Size of each entry in bytes
        
        Returns:
            True if size is valid, False otherwise
        """
        actual_size = len(self.data)
        
        # Allow empty chunks
        if actual_size == 0:
            return True
            
        # Check if size is multiple of entry size
        if actual_size % entry_size != 0:
            logger.warning(
                f"Chunk data size {actual_size} not divisible by entry size {entry_size}. "
                "Data may be truncated."
            )
            return False
            
        return True
    
    def _get_valid_data(self, entry_size: int) -> bytes:
        """Get chunk data truncated to valid size.
        
        Args:
            entry_size: Size of each entry in bytes
        
        Returns:
            Chunk data truncated to multiple of entry size
        """
        actual_size = len(self.data)
        
        # Handle empty chunks
        if actual_size == 0:
            return b''
            
        # Truncate to multiple of entry size
        valid_size = (actual_size // entry_size) * entry_size
        if valid_size < actual_size:
            logger.warning(
                f"Truncating chunk data from {actual_size} to {valid_size} bytes "
                f"to match entry size {entry_size}"
            )
            return self.data[:valid_size]
            
        return self.data
