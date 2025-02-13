# adt_process_dir.py
from typing import Dict, List, Tuple
import os
from adt_core import ADTCoordinates

def analyze_directory(directory: str) -> List[Tuple[str, ADTCoordinates]]:
    """Analyze directory and return list of (filename, coordinates) pairs"""
    results = []
    for filename in os.listdir(directory):
        if not filename.lower().endswith('.adt'):
            continue
        coords = ADTCoordinates.from_filename(filename)
        if coords:
            results.append((filename, coords))
    return results

def calculate_grid_offset(source_coords: List[Tuple[int, int]], 
                         target_coords: List[Tuple[int, int]]) -> Tuple[int, int]:
    """Calculate the offset between two coordinate grids"""
    if not source_coords or not target_coords:
        return (0, 0)
        
    source_min_x = min(x for x, _ in source_coords)
    source_min_y = min(y for _, y in source_coords)
    target_min_x = min(x for x, _ in target_coords)
    target_min_y = min(y for _, y in target_coords)
    
    return (target_min_x - source_min_x, target_min_y - source_min_y)

def generate_coordinate_mapping(source_dir: str, target_dir: str) -> Dict[str, ADTCoordinates]:
    """Generate coordinate mapping based on source and target directories"""
    source_files = analyze_directory(source_dir)
    target_files = analyze_directory(target_dir)
    
    source_coords = [(c.x, c.y) for _, c in source_files]
    target_coords = [(c.x, c.y) for _, c in target_files]
    
    x_offset, y_offset = calculate_grid_offset(source_coords, target_coords)
    
    return {
        filename: ADTCoordinates(coords.x + x_offset, coords.y + y_offset)
        for filename, coords in source_files
    }