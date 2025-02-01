#!/usr/bin/env python3
import logging
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from collections import defaultdict
import argparse
from dataclasses import dataclass, field
import traceback

# Import our specialized decoders
from adt_reader import ADTFile
from texture_decoders import TextureManager
from placement_decoders import MDDFChunk, MODFChunk
from liquid_decoders import LiquidManager
from misc_root_decoders import MFBOChunk, MTXFChunk
from mcnk_base_decoder import MCNKChunk

@dataclass
class ADTStats:
    """Statistics for a single ADT file"""
    texture_count: int = 0
    model_count: int = 0
    wmo_count: int = 0
    doodad_placements: int = 0
    wmo_placements: int = 0
    mcnk_count: int = 0
    has_liquid: bool = False
    has_flight_bounds: bool = False
    unique_textures: Set[str] = field(default_factory=set)
    unique_models: Set[str] = field(default_factory=set)
    unique_wmos: Set[str] = field(default_factory=set)
    terrain_layers: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    liquid_types: Dict[int, int] = field(default_factory=lambda: defaultdict(int))

@dataclass
class ProcessingResult:
    """Result of processing a single ADT file"""
    filename: str
    stats: Optional[ADTStats] = None
    chunk_data: Optional[Dict] = None
    error: Optional[str] = None
    warning_count: int = 0
    processing_time: float = 0.0

class ADTDirectoryParser:
    """Advanced ADT directory parser using specialized decoders"""
    
    def __init__(self, input_dir: str, output_file: str, log_file: str, debug: bool = False):
        self.input_dir = Path(input_dir)
        self.output_file = Path(output_file)
        
        # Setup logging
        self._setup_logging(log_file, debug)
        
        # Statistics tracking
        self.total_stats = ADTStats()
        self.processed_files: List[ProcessingResult] = []
        self.texture_usage: Dict[str, int] = defaultdict(int)
        self.model_usage: Dict[str, int] = defaultdict(int)
        self.wmo_usage: Dict[str, int] = defaultdict(int)
        
        # Error tracking
        self.error_count = 0
        self.warning_count = 0
    def _setup_logging(self, log_file: str, debug: bool) -> None:
        """Setup logging configuration"""
        level = logging.DEBUG if debug else logging.INFO
        format_str = '%(asctime)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=level,
            format=format_str,
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _process_textures(self, adt: ADTFile, stats: ADTStats) -> None:
        """Process texture information"""
        if 'MTEX' in adt.chunks:
            mtex = adt.chunks['MTEX']
            stats.texture_count = len(mtex.filenames)
            stats.unique_textures.update(mtex.filenames)
            
            # Track texture usage
            for tex in mtex.filenames:
                self.texture_usage[tex] += 1

    def _process_models(self, adt: ADTFile, stats: ADTStats) -> None:
        """Process M2 and WMO model information"""
        # Process M2 models
        if 'MMDX' in adt.chunks:
            mmdx = adt.chunks['MMDX']
            stats.model_count = len(mmdx.filenames)
            stats.unique_models.update(mmdx.filenames)
            
            for model in mmdx.filenames:
                self.model_usage[model] += 1

        # Process WMOs
        if 'MWMO' in adt.chunks:
            mwmo = adt.chunks['MWMO']
            stats.wmo_count = len(mwmo.filenames)
            stats.unique_wmos.update(mwmo.filenames)
            
            for wmo in mwmo.filenames:
                self.wmo_usage[wmo] += 1

    def _process_placements(self, adt: ADTFile, stats: ADTStats) -> None:
        """Process model and WMO placements"""
        if 'MDDF' in adt.chunks:
            mddf = adt.chunks['MDDF']
            stats.doodad_placements = len(mddf.doodads)
            
        if 'MODF' in adt.chunks:
            modf = adt.chunks['MODF']
            stats.wmo_placements = len(modf.map_objects)

    def _process_terrain(self, adt: ADTFile, stats: ADTStats) -> None:
        """Process terrain chunks and layers"""
        stats.mcnk_count = len(adt.mcnks)
        
        for mcnk in adt.mcnks:
            # Process terrain layers
            mcly = mcnk.get_subchunk('MCLY')
            if mcly:
                for layer in mcly.layers:
                    stats.terrain_layers[layer.texture_id] += 1

    def _process_liquid(self, adt: ADTFile, stats: ADTStats) -> None:
        """Process liquid data"""
        if 'MH2O' in adt.chunks:  # Modern liquid
            mh2o = adt.chunks['MH2O']
            stats.has_liquid = any(chunk.chunks for chunk in mh2o.chunks)
            
            # Track liquid types
            for chunk in mh2o.chunks:
                for instance in chunk.chunks:
                    stats.liquid_types[instance.liquid_type] += 1
                    
        elif 'MCLQ' in adt.chunks:  # Legacy liquid
            mclq = adt.chunks['MCLQ']
            stats.has_liquid = True
            stats.liquid_types[mclq.liquid_type] += 1

    def _serialize_chunk_data(self, adt: ADTFile) -> Dict:
        """Serialize all chunk data to JSON-compatible format"""
        chunk_data = {
            "version": adt.version,
            "mhdr_flags": int(adt.mhdr_flags),
            "chunks": {}
        }

        # MTEX (Textures)
        if 'MTEX' in adt.chunks:
            chunk_data["chunks"]["MTEX"] = {
                "filenames": adt.chunks['MTEX'].filenames
            }

        # MMDX/MMID (M2 Models)
        if 'MMDX' in adt.chunks:
            chunk_data["chunks"]["MMDX"] = {
                "filenames": adt.chunks['MMDX'].filenames
            }
            if 'MMID' in adt.chunks:
                chunk_data["chunks"]["MMID"] = {
                    "offsets": adt.chunks['MMID'].offsets,
                    "name_map": adt.chunks['MMID'].name_map
                }

        # MWMO/MWID (WMOs)
        if 'MWMO' in adt.chunks:
            chunk_data["chunks"]["MWMO"] = {
                "filenames": adt.chunks['MWMO'].filenames
            }
            if 'MWID' in adt.chunks:
                chunk_data["chunks"]["MWID"] = {
                    "offsets": adt.chunks['MWID'].offsets,
                    "name_map": adt.chunks['MWID'].name_map
                }

        # MDDF (Doodad Placements)
        if 'MDDF' in adt.chunks:
            chunk_data["chunks"]["MDDF"] = {
                "doodads": [
                    {
                        "name_id": d.name_id,
                        "unique_id": d.unique_id,
                        "position": {"x": d.position.x, "y": d.position.y, "z": d.position.z},
                        "rotation": {"x": d.rotation.x, "y": d.rotation.y, "z": d.rotation.z},
                        "scale": d.scale,
                        "flags": int(d.flags)
                    }
                    for d in adt.chunks['MDDF'].doodads
                ]
            }

        # MODF (WMO Placements)
        if 'MODF' in adt.chunks:
            chunk_data["chunks"]["MODF"] = {
                "objects": [
                    {
                        "name_id": o.name_id,
                        "unique_id": o.unique_id,
                        "position": {"x": o.position.x, "y": o.position.y, "z": o.position.z},
                        "rotation": {"x": o.rotation.x, "y": o.rotation.y, "z": o.rotation.z},
                        "extents": {
                            "min": {"x": o.extents.min.x, "y": o.extents.min.y, "z": o.extents.min.z},
                            "max": {"x": o.extents.max.x, "y": o.extents.max.y, "z": o.extents.max.z}
                        },
                        "flags": int(o.flags),
                        "doodad_set": o.doodad_set,
                        "name_set": o.name_set,
                        "scale": o.scale
                    }
                    for o in adt.chunks['MODF'].map_objects
                ]
            }

        # MCNK chunks
        chunk_data["chunks"]["MCNK"] = []
        for mcnk in adt.mcnks:
            mcnk_data = {
                "header": {
                    "flags": int(mcnk.header.flags),
                    "idx_x": mcnk.header.idx_x,
                    "idx_y": mcnk.header.idx_y,
                    "n_layers": mcnk.header.n_layers,
                    "area_id": mcnk.header.area_id,
                    "position": mcnk.header.position
                },
                "subchunks": {}
            }

            # Height map
            height_map = mcnk.get_height_map()
            if height_map:
                mcnk_data["subchunks"]["height_map"] = list(height_map)

            # Layer info
            layers = mcnk.get_layer_info()
            if layers:
                mcnk_data["subchunks"]["layers"] = layers

            # Alpha maps
            alpha_map = mcnk.get_alpha_map()
            if alpha_map:
                mcnk_data["subchunks"]["alpha_map"] = list(alpha_map)

            # Shadow map
            shadow_map = mcnk.get_shadow_map()
            if shadow_map:
                mcnk_data["subchunks"]["shadow_map"] = list(shadow_map)

            chunk_data["chunks"]["MCNK"].append(mcnk_data)

        # MH2O (Modern Liquid)
        if 'MH2O' in adt.chunks:
            chunk_data["chunks"]["MH2O"] = {
                "chunks": [
                    {
                        "instances": [
                            {
                                "liquid_type": instance.liquid_type,
                                "height_levels": {
                                    "min": instance.min_height_level,
                                    "max": instance.max_height_level
                                },
                                "geometry": {
                                    "x_offset": instance.x_offset,
                                    "y_offset": instance.y_offset,
                                    "width": instance.width,
                                    "height": instance.height
                                },
                                "vertex_format": instance.vertex_format,
                                "has_vertex_data": instance.vertex_data is not None
                            }
                            for instance in chunk.chunks
                        ]
                    }
                    for chunk in adt.chunks['MH2O'].chunks
                ]
            }

        # MFBO (Flight Bounds)
        if 'MFBO' in adt.chunks:
            chunk_data["chunks"]["MFBO"] = {
                "flight_boxes": [
                    {
                        "min": {"x": box.min_x, "y": box.min_y, "z": box.min_z},
                        "max": {"x": box.max_x, "y": box.max_y, "z": box.max_z}
                    }
                    for box in adt.chunks['MFBO'].flight_boxes
                ]
            }

        return chunk_data
    def process_file(self, adt_path: Path) -> ProcessingResult:
        """Process a single ADT file"""
        start_time = datetime.now()
        stats = ADTStats()
        warnings = 0
        
        try:
            self.logger.info(f"Processing {adt_path}")
            adt = ADTFile(str(adt_path))
            
            # Process statistics
            self._process_textures(adt, stats)
            self._process_models(adt, stats)
            self._process_placements(adt, stats)
            self._process_terrain(adt, stats)
            self._process_liquid(adt, stats)
            
            # Check for flight bounds
            stats.has_flight_bounds = 'MFBO' in adt.chunks
            
            # Serialize all chunk data
            chunk_data = self._serialize_chunk_data(adt)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            return ProcessingResult(
                filename=adt_path.name,
                stats=stats,
                chunk_data=chunk_data,
                warning_count=warnings,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error processing {adt_path}: {str(e)}")
            self.logger.debug(traceback.format_exc())
            
            processing_time = (datetime.now() - start_time).total_seconds()
            return ProcessingResult(
                filename=adt_path.name,
                error=str(e),
                warning_count=warnings,
                processing_time=processing_time
            )

    def process_directory(self) -> None:
        """Process all ADT files in directory sequentially"""
        adt_files = sorted(self.input_dir.glob('**/*.adt'))
        total_files = len(adt_files)
        
        self.logger.info(f"Found {total_files} ADT files to process")
        
        for index, adt_path in enumerate(adt_files, 1):
            self.logger.info(f"Processing file {index}/{total_files}: {adt_path.name}")
            result = self.process_file(adt_path)
            self.processed_files.append(result)
            
            # Update global statistics if processing was successful
            if result.stats:
                self._update_global_stats(result.stats)
            
            # Log progress
            if index % 10 == 0:
                self._log_progress(index, total_files)

    def _update_global_stats(self, stats: ADTStats) -> None:
        """Update global statistics with data from a single file"""
        self.total_stats.texture_count += stats.texture_count
        self.total_stats.model_count += stats.model_count
        self.total_stats.wmo_count += stats.wmo_count
        self.total_stats.doodad_placements += stats.doodad_placements
        self.total_stats.wmo_placements += stats.wmo_placements
        self.total_stats.mcnk_count += stats.mcnk_count
        
        self.total_stats.unique_textures.update(stats.unique_textures)
        self.total_stats.unique_models.update(stats.unique_models)
        self.total_stats.unique_wmos.update(stats.unique_wmos)
        
        # Update layer counts
        for tex_id, count in stats.terrain_layers.items():
            self.total_stats.terrain_layers[tex_id] += count
            
        # Update liquid type counts
        for liquid_type, count in stats.liquid_types.items():
            self.total_stats.liquid_types[liquid_type] += count

    def generate_report(self) -> None:
        """Generate detailed processing report"""
        report = {
            "summary": {
                "generated_at": datetime.now().isoformat(),
                "input_directory": str(self.input_dir),
                "total_files_processed": len(self.processed_files),
                "successful_files": sum(1 for r in self.processed_files if r.stats),
                "failed_files": sum(1 for r in self.processed_files if r.error),
                "total_warnings": sum(r.warning_count for r in self.processed_files),
                "total_errors": self.error_count,
                "total_processing_time": sum(r.processing_time for r in self.processed_files)
            },
            "global_statistics": {
                "unique_textures": len(self.total_stats.unique_textures),
                "unique_models": len(self.total_stats.unique_models),
                "unique_wmos": len(self.total_stats.unique_wmos),
                "total_doodad_placements": self.total_stats.doodad_placements,
                "total_wmo_placements": self.total_stats.wmo_placements,
                "total_mcnk_chunks": self.total_stats.mcnk_count,
                "files_with_liquid": sum(1 for r in self.processed_files 
                                       if r.stats and r.stats.has_liquid),
                "files_with_flight_bounds": sum(1 for r in self.processed_files 
                                              if r.stats and r.stats.has_flight_bounds)
            },
            "asset_usage": {
                "most_used_textures": self._get_top_usage(self.texture_usage, 20),
                "most_used_models": self._get_top_usage(self.model_usage, 20),
                "most_used_wmos": self._get_top_usage(self.wmo_usage, 20)
            },
            "terrain_analysis": {
                "layer_distribution": dict(self.total_stats.terrain_layers),
                "liquid_types": dict(self.total_stats.liquid_types)
            },
            "files": [
                {
                    "filename": result.filename,
                    "processing_time": result.processing_time,
                    "warnings": result.warning_count,
                    "error": result.error if result.error else None,
                    "stats": {
                        "textures": len(result.stats.unique_textures),
                        "models": len(result.stats.unique_models),
                        "wmos": len(result.stats.unique_wmos),
                        "doodad_placements": result.stats.doodad_placements,
                        "wmo_placements": result.stats.wmo_placements,
                        "mcnk_count": result.stats.mcnk_count,
                        "has_liquid": result.stats.has_liquid,
                        "has_flight_bounds": result.stats.has_flight_bounds
                    } if result.stats else None,
                    "chunk_data": result.chunk_data
                }
                for result in self.processed_files
            ]
        }

        # Write report to file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Report generated: {self.output_file}")

    def _get_top_usage(self, usage_dict: Dict[str, int], limit: int) -> List[Dict]:
        """Get top used assets with their counts"""
        return [
            {"name": name, "count": count}
            for name, count in sorted(
                usage_dict.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:limit]
        ]

    def _log_progress(self, current: int, total: int) -> None:
        """Log processing progress"""
        percentage = (current / total) * 100
        self.logger.info(f"Progress: {current}/{total} files ({percentage:.1f}%)")

def main():
    parser = argparse.ArgumentParser(description='Process directory of ADT files')
    parser.add_argument('input_dir', help='Input directory containing ADT files')
    parser.add_argument('--output', '-o', default='adt_report.json',
                      help='Output JSON report file (default: adt_report.json)')
    parser.add_argument('--log', '-l', default='adt_processing.log',
                      help='Log file (default: adt_processing.log)')
    parser.add_argument('--debug', '-d', action='store_true',
                      help='Enable debug logging')
    
    args = parser.parse_args()
    
    processor = ADTDirectoryParser(
        input_dir=args.input_dir,
        output_file=args.output,
        log_file=args.log,
        debug=args.debug
    )
    
    try:
        processor.process_directory()
        processor.generate_report()
    except Exception as e:
        processor.logger.error(f"Fatal error: {str(e)}")
        processor.logger.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
