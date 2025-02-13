# chunk_utils.py
def reverse_chunk_name(chunk_name: bytes) -> bytes:
    return chunk_name[::-1]

def normalize_chunk_name(chunk_name: bytes, stored_reversed: bool = True) -> bytes:
    """Convert chunk name to standard form (e.g., MVER) regardless of storage format"""
    if stored_reversed:
        return reverse_chunk_name(chunk_name)
    return chunk_name

def is_chunk_name_reversed(chunk_name: bytes) -> bool:
    """Detect if chunk names in file are stored reversed"""
    standard_chunks = [b'MVER', b'MHDR', b'MCIN', b'MTEX']
    reversed_chunks = [reverse_chunk_name(name) for name in standard_chunks]
    
    # Check if chunk matches any standard forms
    if chunk_name in standard_chunks:
        return False
    if chunk_name in reversed_chunks:
        return True
        
    return True  # Default to reversed for safety