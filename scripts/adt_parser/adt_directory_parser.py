#!/usr/bin/env python3
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import argparse

from adt_reader import ADTFile

@dataclass
class ADTSummary:
    """Summary data for an ADT file"""
    filename: str
    version: int
    flags: int
    texture_count: int
    m2_count: int
    wmo_count: int
    m2_placements: int
    wmo_placements: int
    has_liquid: bool
    textures: List[str]
    m2_models: List[str]
    wmo_models: List[str]

class ADTDirectoryParser:
    """Parse directory of ADT files and generate summary"""
    def __init__(self, input_dir: str, output_file: str, log_file: str):
        self.input_dir = Path(input_dir)
        self.output_file = Path(output_file)
        
        # Set up logging with Unicode support
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def process_adt(self, adt_path: Path) -> Optional[ADTSummary]:
        """Process single ADT file and return summary"""
        try:
            self.logger.info(f"Processing {adt_path}")
            adt = ADTFile(str(adt_path))
            
            # Get texture information
            textures = []
            mtex = adt.chunks.get('MTEX')
            if mtex:
                textures = [name for name in mtex.filenames]
            
            # Get M2 information
            m2_models = []
            mmdx = adt.chunks.get('MMDX')
            if mmdx:
                m2_models = [name for name in mmdx.filenames]
            
            # Get WMO information
            wmo_models = []
            mwmo = adt.chunks.get('MWMO')
            if mwmo:
                wmo_models = [name for name in mwmo.filenames]
            
            # Check for liquid
            has_liquid = 'MH2O' in adt.chunks or 'MCLQ' in adt.chunks
            
            # Create summary
            summary = ADTSummary(
                filename=adt_path.name,
                version=adt.version,
                flags=int(adt.mhdr_flags),
                texture_count=len(textures),
                m2_count=len(m2_models),
                wmo_count=len(wmo_models),
                m2_placements=len(adt.chunks['MDDF'].placements) if 'MDDF' in adt.chunks else 0,
                wmo_placements=len(adt.chunks['MODF'].placements) if 'MODF' in adt.chunks else 0,
                has_liquid=has_liquid,
                textures=textures,
                m2_models=m2_models,
                wmo_models=wmo_models
            )
            
            self.logger.info(f"Successfully processed {adt_path.name}")
            self.logger.debug(f"Found {summary.texture_count} textures, "
                            f"{summary.m2_placements} M2 placements, "
                            f"{summary.wmo_placements} WMO placements")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error processing {adt_path}: {str(e)}")
            return None

    def process_directory(self) -> List[ADTSummary]:
        """Process all ADT files in directory"""
        summaries = []
        adt_files = list(self.input_dir.glob('**/*.adt'))
        
        self.logger.info(f"Found {len(adt_files)} ADT files to process")
        
        for adt_path in adt_files:
            summary = self.process_adt(adt_path)
            if summary:
                summaries.append(summary)
        
        return summaries

    def generate_report(self, summaries: List[ADTSummary]):
        """Generate JSON report from summaries"""
        try:
            # Convert summaries to dict for JSON serialization
            report_data = {
                "generated_at": datetime.now().isoformat(),
                "input_directory": str(self.input_dir),
                "file_count": len(summaries),
                "summaries": [asdict(summary) for summary in summaries]
            }
            
            # Write JSON with proper Unicode handling
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Report generated: {self.output_file}")
            
        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")

    def generate_statistics(self, summaries: List[ADTSummary]):
        """Generate and log statistical information"""
        if not summaries:
            self.logger.warning("No data to generate statistics")
            return
            
        total_m2 = sum(s.m2_placements for s in summaries)
        total_wmo = sum(s.wmo_placements for s in summaries)
        liquid_count = sum(1 for s in summaries if s.has_liquid)
        
        # Collect unique models/textures
        unique_textures = set()
        unique_m2 = set()
        unique_wmo = set()
        
        for summary in summaries:
            unique_textures.update(summary.textures)
            unique_m2.update(summary.m2_models)
            unique_wmo.update(summary.wmo_models)
        
        # Log statistics
        self.logger.info("\nMap Statistics:")
        self.logger.info(f"Total ADT files processed: {len(summaries)}")
        self.logger.info(f"Total M2 placements: {total_m2}")
        self.logger.info(f"Total WMO placements: {total_wmo}")
        self.logger.info(f"ADTs with liquid: {liquid_count}")
        self.logger.info(f"Unique textures: {len(unique_textures)}")
        self.logger.info(f"Unique M2 models: {len(unique_m2)}")
        self.logger.info(f"Unique WMO models: {len(unique_wmo)}")

def main():
    parser = argparse.ArgumentParser(description='Process directory of ADT files')
    parser.add_argument('input_dir', help='Input directory containing ADT files')
    parser.add_argument('--output', '-o', default='adt_report.json',
                        help='Output JSON report file (default: adt_report.json)')
    parser.add_argument('--log', '-l', default='adt_processing.log',
                        help='Log file (default: adt_processing.log)')
    
    args = parser.parse_args()
    
    processor = ADTDirectoryParser(args.input_dir, args.output, args.log)
    summaries = processor.process_directory()
    processor.generate_report(summaries)
    processor.generate_statistics(summaries)

if __name__ == "__main__":
    main()
