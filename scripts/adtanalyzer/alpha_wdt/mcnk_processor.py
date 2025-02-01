import sqlite3
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
from pathlib import Path
from chunk_handler import WDTFile, ChunkRef
from mcnk_parser import process_mcnk_data

class MCNKProcessor:
    """Multi-threaded MCNK data processor"""
    
    def __init__(self, db_path: str, max_workers: int = 4):
        self.db_path = db_path
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
    
    def _process_tile(self, args: Tuple) -> Dict:
        """
        Process a single tile's MCNK data.
        Returns a dict with processing results.
        """
        wdt_file, wdt_id, tile, x, y, is_alpha = args
        
        # Create a new database connection for this thread with larger timeout
        conn = sqlite3.connect(self.db_path, timeout=60)
        conn.execute("PRAGMA journal_mode=WAL")  # Use Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Reduce synchronous mode for better performance
        
        try:
            # Create chunk reference
            chunk_ref = ChunkRef(
                offset=tile['offset'],
                size=tile['size'],
                magic='MCNK',
                header_offset=tile['offset']
            )
            
            # Start transaction for batch operations
            with conn:
                # Process MCNK data
                mcnk_id = process_mcnk_data(
                    conn=conn,
                    wdt_id=wdt_id,
                    tile_x=x,
                    tile_y=y,
                    wdt_file=wdt_file,
                    chunk_ref=chunk_ref,
                    is_alpha=is_alpha
                )
                
                result = {
                    'success': mcnk_id is not None,
                    'tile_x': x,
                    'tile_y': y,
                    'mcnk_id': mcnk_id
                }
            
        except Exception as e:
            self.logger.error(f"Error processing tile ({x}, {y}): {e}")
            result = {
                'success': False,
                'tile_x': x,
                'tile_y': y,
                'error': str(e)
            }
        
        finally:
            conn.close()
        
        return result
    
    def process_tiles(self, wdt_file: WDTFile, wdt_id: int, tiles: List[Dict], is_alpha: bool) -> Dict:
        """
        Process multiple tiles in parallel.
        Returns statistics about the processing.
        """
        stats = {
            'total': len(tiles),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        # Prepare arguments for each tile
        tile_args = [
            (wdt_file, wdt_id, tile, tile['coordinates']['x'], tile['coordinates']['y'], is_alpha)
            for tile in tiles
        ]
        
        # Process tiles in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_tile = {
                executor.submit(self._process_tile, args): args
                for args in tile_args
            }
            
            # Process results as they complete
            for future in as_completed(future_to_tile):
                args = future_to_tile[future]
                try:
                    result = future.result()
                    if result['success']:
                        stats['successful'] += 1
                        self.logger.info(
                            f"Successfully processed tile ({result['tile_x']}, {result['tile_y']})"
                        )
                    else:
                        stats['failed'] += 1
                        error_msg = f"Failed to process tile ({result['tile_x']}, {result['tile_y']})"
                        if 'error' in result:
                            error_msg += f": {result['error']}"
                        stats['errors'].append(error_msg)
                        self.logger.error(error_msg)
                except Exception as e:
                    stats['failed'] += 1
                    error_msg = f"Error processing tile ({args[3]}, {args[4]}): {e}"
                    stats['errors'].append(error_msg)
                    self.logger.error(error_msg)
        
        return stats

def process_wdt_tiles(
    wdt_file: WDTFile,
    wdt_id: int,
    tiles: List[Dict],
    db_path: str,
    is_alpha: bool,
    max_workers: int = 4
) -> Dict:
    """
    Process WDT tiles using multiple threads.
    
    Args:
        wdt_file: WDTFile instance
        wdt_id: WDT file ID in database
        tiles: List of tile data dictionaries
        db_path: Path to SQLite database
        is_alpha: Whether processing Alpha format
        max_workers: Maximum number of worker threads
    
    Returns:
        Dictionary containing processing statistics
    """
    processor = MCNKProcessor(db_path, max_workers)
    return processor.process_tiles(wdt_file, wdt_id, tiles, is_alpha)