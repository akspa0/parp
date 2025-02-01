#!/usr/bin/env python3
"""
Convert WoW terrain data to 3D models (OBJ/GLTF)
"""
import os
import json
import argparse
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

@dataclass
class TextureLayer:
    """Represents a terrain texture layer with alpha map"""
    alpha_map: List[float]
import logging

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False

def setup_logging(debug: bool = False) -> logging.Logger:
    """Set up logging"""
    logger = logging.getLogger('terrain_to_3d')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(console_handler)
    
    return logger

def create_heightmap_mesh(heights: List[float], normals: List[List[float]],
                         holes: int = 0, holes_high_res: int = 0,
                         texture_layers: Optional[List[TextureLayer]] = None,
                         liquid_heights: Optional[List[float]] = None,
                         scale: float = 1.0, logger: logging.Logger = None) -> Tuple[List[List[float]], List[List[int]], List[List[float]]]:
    """Create mesh data from heightmap with additional terrain features
    
    Args:
        heights: List of vertex heights
        normals: List of vertex normal vectors
        holes: Low-resolution hole mask
        holes_high_res: High-resolution hole mask
        texture_layers: List of texture layers with alpha maps
        liquid_heights: List of liquid height values
        scale: Scale factor for coordinates
        logger: Optional logger for debug output
    """
    vertices = []
    faces = []
    vertex_normals = []
    
    # WoW uses 9x17 or 17x9 grid for terrain chunks
    if len(heights) == 145:  # 145 = (8*9 + 9*8 + 9*9)
        width = 9
        height = 17
    else:
        raise ValueError(f"Unexpected number of vertices: {len(heights)}")
    
    # Create vertices
    chunk_width = 33.33333  # yards
    
    # Helper function to check if vertex is in a hole
    def is_hole(x: int, z: int) -> bool:
        # Convert vertex position to hole grid cell (8x8)
        cell_x = int(x * 8 / width)
        cell_z = int(z * 8 / height)
        cell_idx = cell_z * 8 + cell_x
        
        # Check both low and high resolution hole masks
        return bool(holes & (1 << cell_idx)) or bool(holes_high_res & (1 << cell_idx))
    
    for z in range(height):
        for x in range(width):
            idx = z * width + x
            if idx >= len(heights):
                break
                
            # Skip vertices in holes
            if is_hole(x, z):
                continue
                
            # Get terrain height
            y = heights[idx] * scale
            
            # Check for liquid height
            if liquid_heights and idx < len(liquid_heights) and liquid_heights[idx] > y:
                y = liquid_heights[idx] * scale
            
            # Convert to WoW's coordinate system
            vertices.append([
                x * (chunk_width/width) * scale,   # X: east/west
                y,                                 # Y: up/down
                z * (chunk_width/height) * scale   # Z: north/south
            ])
            vertex_normals.append(normals[idx])
            
            if logger and texture_layers:
                logger.debug(f"Vertex {idx}: pos=({x},{y},{z}), layers={len(texture_layers)}")
    
    # Create vertex index lookup
    vertex_indices = {}  # Maps (x,z) to vertex index
    for i, v in enumerate(vertices):
        x = int(v[0] / (chunk_width/width) / scale)
        z = int(v[2] / (chunk_width/height) / scale)
        vertex_indices[(x, z)] = i

    # Create faces (triangles), skipping holes
    for z in range(height - 1):
        for x in range(width - 1):
            # Get vertices for this quad
            quad_vertices = []
            for dx, dz in [(0,0), (1,0), (0,1), (1,1)]:  # Clockwise order
                pos = (x+dx, z+dz)
                if pos in vertex_indices and not is_hole(pos[0], pos[1]):
                    quad_vertices.append(vertex_indices[pos])
                else:
                    quad_vertices.append(None)
            
            # Create triangles if we have all vertices
            if None not in quad_vertices[:3]:  # First triangle
                faces.append([quad_vertices[0], quad_vertices[1], quad_vertices[2]])
            if None not in quad_vertices[1:]:  # Second triangle
                faces.append([quad_vertices[1], quad_vertices[3], quad_vertices[2]])
    
    # Log mesh statistics
    if logger:
        logger.debug(f"  Created mesh with {len(vertices)} vertices and {len(faces)} faces")
    
    return vertices, faces, vertex_normals

def combine_meshes(vertices_list: List[List[List[float]]],
                  faces_list: List[List[List[int]]],
                  normals_list: List[List[List[float]]],
                  chunk_positions: List[Tuple[int, int]],
                  chunk_size: Tuple[int, int] = (9, 17),
                  chunk_spacing: float = 33.33333) -> Tuple[List[List[float]], List[List[int]], List[List[float]]]:
    """Combine multiple chunk meshes into a single mesh.
    
    WoW's coordinate system:
    - Each ADT tile is 533.33333 yards wide
    - Each chunk is 33.33333 yards wide
    - 16x16 chunks per tile
    - Right-handed coordinate system with Y up
    """
    combined_vertices = []
    combined_faces = []
    combined_normals = []
    vertex_offset = 0
    
    # Sort chunks by position to ensure consistent ordering
    chunks = list(zip(chunk_positions, vertices_list, faces_list, normals_list))
    chunks.sort(key=lambda x: (x[0][1], x[0][0]))  # Sort by y then x
    
    for (chunk_x, chunk_y), vertices, faces, normals in chunks:
        # Offset vertices based on chunk position
        offset_vertices = []
        for v in vertices:
            offset_vertices.append([
                # Convert to WoW's coordinate system:
                # - Each chunk is 33.33333 yards wide
                # - 16x16 chunks per tile
                # - Origin is at tile corner
                v[0] + (chunk_x * chunk_spacing),  # X: east/west
                v[1],                              # Y: up/down (height)
                v[2] + (chunk_y * chunk_spacing)   # Z: north/south
            ])
        
        # Offset face indices
        offset_faces = [[f + vertex_offset for f in face] for face in faces]
        
        # Add to combined mesh
        combined_vertices.extend(offset_vertices)
        combined_faces.extend(offset_faces)
        combined_normals.extend(normals)
        
        vertex_offset += len(vertices)
    
    return combined_vertices, combined_faces, combined_normals

def save_obj(vertices: List[List[float]], faces: List[List[int]], 
             normals: List[List[float]], output_path: Path):
    """Save mesh as OBJ file"""
    with open(output_path, 'w') as f:
        # Write vertices
        for v in vertices:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")
        
        # Write vertex normals
        for n in normals:
            f.write(f"vn {n[0]} {n[1]} {n[2]}\n")
        
        # Write faces (1-based indexing in OBJ)
        for face in faces:
            # Include both vertex and normal indices
            f.write(f"f {face[0]+1}//{face[0]+1} {face[1]+1}//{face[1]+1} {face[2]+1}//{face[2]+1}\n")

def save_gltf(vertices: List[List[float]], faces: List[List[int]], 
              normals: List[List[float]], output_path: Path):
    """Save mesh as GLTF file using trimesh"""
    if not HAS_TRIMESH:
        raise ImportError("trimesh is required for GLTF export. Install with: pip install trimesh")
    
    # Create trimesh mesh
    mesh = trimesh.Trimesh(
        vertices=np.array(vertices),
        faces=np.array(faces),
        vertex_normals=np.array(normals)
    )
    
    # Export as GLTF
    mesh.export(str(output_path))

def process_json_file(json_path: Path, output_dir: Path, format: str = 'obj', 
                     logger: logging.Logger = None) -> bool:
    """Process a single JSON file to create 3D model for entire tile"""
    try:
        # Load JSON data
        with open(json_path) as f:
            data = json.load(f)
            
        logger.debug(f"Processing JSON file: {json_path}")
        logger.debug(f"File type: {data.get('file_type')}")
        logger.debug(f"Format type: {data.get('format_type')}")
        
        # Extract heightmap and normal data
        if 'mcnk_chunks' not in data:
            logger.error(f"No MCNK chunks found in {json_path}")
            return False
            
        chunk_count = len(data['mcnk_chunks'])
        logger.debug(f"Found {chunk_count} MCNK chunks")
        
        # Collect meshes for all chunks
        chunk_meshes = []
        chunk_positions = []
        
        for chunk_id, chunk_data in data['mcnk_chunks'].items():
            if not isinstance(chunk_data, dict):
                logger.warning(f"Invalid chunk data type for {chunk_id}: {type(chunk_data)}")
                continue
                
            # Log available fields in chunk data
            logger.debug(f"Chunk {chunk_id} fields: {list(chunk_data.keys())}")
            
            if 'height_map' not in chunk_data or 'normal_data' not in chunk_data:
                logger.warning(f"Missing height/normal data in chunk {chunk_id}")
                if 'height_map' in chunk_data:
                    logger.debug(f"  height_map type: {type(chunk_data['height_map'])}")
                if 'normal_data' in chunk_data:
                    logger.debug(f"  normal_data type: {type(chunk_data['normal_data'])}")
                continue
            
            # Get height and normal data
            try:
                heights = chunk_data['height_map']
                normal_data = chunk_data['normal_data']
                
                if not heights or not normal_data:
                    logger.warning(f"Empty height/normal data in chunk {chunk_id}")
                    continue
                    
                logger.debug(f"Chunk {chunk_id}:")
                logger.debug(f"  Height data length: {len(heights)}")
                logger.debug(f"  Normal data length: {len(normal_data)}")
                
                # Convert normal data to list of [x,y,z] lists
                # Each vertex has 3 components (x,y,z)
                normals = []
                if len(normal_data) == len(heights) * 3:
                    for i in range(len(heights)):
                        base_idx = i * 3
                        normals.append([
                            normal_data[base_idx],
                            normal_data[base_idx + 1],
                            normal_data[base_idx + 2]
                        ])
                    logger.debug(f"  Processed {len(normals)} normal vectors")
                else:
                    logger.warning(f"Normal data length {len(normal_data)} is not 3x height count {len(heights)}")
                    continue
                
                if len(heights) != len(normals):
                    logger.warning(f"Mismatched counts - heights: {len(heights)}, normals: {len(normals)}")
                    continue
                
                # Get additional terrain data
                holes = chunk_data.get('holes', 0)
                holes_high_res = chunk_data.get('holes_high_res', 0)
                texture_layers = chunk_data.get('texture_layers', [])
                liquid_heights = chunk_data.get('liquid_heights', [])
                
                # Create mesh data for this chunk
                vertices, faces, vertex_normals = create_heightmap_mesh(
                    heights,
                    normals,
                    holes=holes,
                    holes_high_res=holes_high_res,
                    texture_layers=texture_layers,
                    liquid_heights=liquid_heights,
                    scale=1.0,  # Use actual yard measurements from WoW
                    logger=logger
                )
                
                # Store mesh data and chunk position
                chunk_x, chunk_y = map(int, chunk_id.strip('()').split(','))
                chunk_meshes.append((vertices, faces, vertex_normals))
                chunk_positions.append((chunk_x, chunk_y))
                
            except (KeyError, IndexError, TypeError) as e:
                logger.error(f"Error processing chunk {chunk_id} data: {e}")
                continue
        
        if not chunk_meshes:
            logger.error("No valid chunks found to create mesh")
            return False
        
        # Combine all chunk meshes into a single tile mesh
        vertices_list, faces_list, normals_list = zip(*chunk_meshes)
        vertices, faces, normals = combine_meshes(
            vertices_list,
            faces_list,
            normals_list,
            chunk_positions
        )
        
        # Save combined mesh
        output_name = json_path.stem
        if format == 'obj':
            output_path = output_dir / f"{output_name}.obj"
            save_obj(vertices, faces, normals, output_path)
            logger.info(f"Created OBJ file: {output_path}")
            logger.debug(f"  Total vertices: {len(vertices)}")
            logger.debug(f"  Total faces: {len(faces)}")
            logger.debug(f"  Total normals: {len(normals)}")
        else:
            output_path = output_dir / f"{output_name}.gltf"
            save_gltf(vertices, faces, normals, output_path)
            logger.info(f"Created GLTF file: {output_path}")
            logger.debug(f"  Total vertices: {len(vertices)}")
            logger.debug(f"  Total faces: {len(faces)}")
            logger.debug(f"  Total normals: {len(normals)}")
        
        return True
        
    except Exception as e:
        if logger:
            logger.error(f"Error processing {json_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Convert WoW terrain data to 3D models')
    parser.add_argument('input', help='Input JSON file or directory')
    parser.add_argument('--format', choices=['obj', 'gltf'], default='obj',
                      help='Output format (default: obj)')
    parser.add_argument('--output', help='Output directory')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.debug)
    
    # Set up input/output paths
    input_path = Path(args.input)
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = input_path.parent / '3d_models'
    output_dir.mkdir(exist_ok=True)
    
    # Check format requirements
    if args.format == 'gltf' and not HAS_TRIMESH:
        logger.error("trimesh is required for GLTF export. Install with: pip install trimesh")
        return
    
    # Process files
    if input_path.is_file():
        if input_path.suffix == '.json':
            process_json_file(input_path, output_dir, args.format, logger)
        else:
            logger.error(f"Unsupported file type: {input_path}")
    else:
        # Process all JSON files in directory
        json_files = list(input_path.glob('**/*.json'))
        logger.info(f"Found {len(json_files)} JSON files")
        
        for json_file in json_files:
            process_json_file(json_file, output_dir, args.format, logger)
    
    logger.info("Processing complete")

if __name__ == '__main__':
    main()