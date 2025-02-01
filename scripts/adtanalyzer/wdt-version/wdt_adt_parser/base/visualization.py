"""
Visualization utilities for WDT/ADT data.
"""
from typing import List, Optional
from datetime import datetime
import logging
from pathlib import Path

class GridVisualizer:
    """Handles visualization of map grid data"""
    
    def __init__(self):
        """Initialize the visualizer"""
        self.logger = logging.getLogger('GridVisualizer')
    
    def create_text_visualization(self, grid: List[List[int]], 
                                active_char: str = "#",
                                inactive_char: str = ".") -> str:
        """
        Create a text-based visualization of the map grid
        
        Args:
            grid: 2D list representing the map grid
            active_char: Character to use for active tiles
            inactive_char: Character to use for inactive tiles
            
        Returns:
            String containing the visualization
        """
        return "\n".join(
            "".join(active_char if cell == 1 else inactive_char for cell in row)
            for row in grid
        )
    
    def write_visualization(self, grid: List[List[int]], 
                          output_dir: Optional[Path] = None,
                          prefix: str = "adt_visualization",
                          active_char: str = "#",
                          inactive_char: str = ".") -> Path:
        """
        Write text-based visualization of the map grid to a file
        
        Args:
            grid: 2D list representing the map grid
            output_dir: Optional output directory, defaults to current directory
            prefix: Prefix for the output filename
            active_char: Character to use for active tiles
            inactive_char: Character to use for inactive tiles
            
        Returns:
            Path to the created visualization file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = output_dir or Path.cwd()
        filename = output_dir / f"{prefix}_{timestamp}.txt"
            
        visualization = self.create_text_visualization(
            grid, active_char, inactive_char
        )
        
        try:
            with open(filename, 'w') as vis_file:
                vis_file.write("Text-based visualization of the ADT grid:\n")
                vis_file.write(visualization + "\n")
                
            self.logger.info(f"Grid visualization saved to: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"Failed to write visualization: {e}")
            raise
    
    def create_html_visualization(self, grid: List[List[int]], 
                                active_color: str = "#4CAF50",
                                inactive_color: str = "#FFFFFF") -> str:
        """
        Create an HTML visualization of the map grid
        
        Args:
            grid: 2D list representing the map grid
            active_color: Color for active tiles
            inactive_color: Color for inactive tiles
            
        Returns:
            HTML string containing the visualization
        """
        cell_size = 10  # pixels
        
        cells = []
        for row in grid:
            cells.extend(
                f'<div style="width:{cell_size}px;height:{cell_size}px;'
                f'background-color:{active_color if cell == 1 else inactive_color};'
                f'float:left;"></div>'
                for cell in row
            )
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Map Grid Visualization</title>
            <style>
                .grid {{
                    width: {len(grid[0]) * cell_size}px;
                    height: {len(grid) * cell_size}px;
                    border: 1px solid #ccc;
                    overflow: hidden;
                }}
                .cell {{
                    width: {cell_size}px;
                    height: {cell_size}px;
                    float: left;
                    transition: background-color 0.3s;
                }}
                .cell:hover {{
                    filter: brightness(90%);
                }}
            </style>
        </head>
        <body>
            <div class="grid">
                {''.join(cells)}
            </div>
        </body>
        </html>
        """
    
    def write_html_visualization(self, grid: List[List[int]], 
                               output_dir: Optional[Path] = None,
                               prefix: str = "adt_visualization",
                               active_color: str = "#4CAF50",
                               inactive_color: str = "#FFFFFF") -> Path:
        """
        Write HTML visualization of the map grid to a file
        
        Args:
            grid: 2D list representing the map grid
            output_dir: Optional output directory, defaults to current directory
            prefix: Prefix for the output filename
            active_color: Color for active tiles
            inactive_color: Color for inactive tiles
            
        Returns:
            Path to the created visualization file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = output_dir or Path.cwd()
        filename = output_dir / f"{prefix}_{timestamp}.html"
            
        html = self.create_html_visualization(
            grid, active_color, inactive_color
        )
        
        try:
            with open(filename, 'w') as vis_file:
                vis_file.write(html)
                
            self.logger.info(f"HTML visualization saved to: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"Failed to write HTML visualization: {e}")
            raise

def create_visualizer() -> GridVisualizer:
    """Create a new grid visualizer instance"""
    return GridVisualizer()