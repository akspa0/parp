import sqlite3
import sys
import logging
from datetime import datetime

def gather_statistics(db_path: str) -> None:
    """Gather statistics from WDT analysis database"""
    log_filename = f"wdt_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        filename=log_filename,
        filemode='w',
        format='%(asctime)s [%(levelname)s] %(message)s',
        level=logging.INFO
    )

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Get WDT files info
        cursor.execute('''
            SELECT id, map_name, original_format, 
                   (SELECT COUNT(*) FROM map_tiles WHERE wdt_id = w.id) as tile_count
            FROM wdt_files w
        ''')
        wdt_files = cursor.fetchall()

        for wdt_id, map_name, format_type, tile_count in wdt_files:
            print(f"\nStatistics for {map_name} ({format_type}):")
            print("=" * 50)
            print(f"Active Tiles: {tile_count}")

            # Count models and placements
            cursor.execute('''
                SELECT COUNT(DISTINCT model_path) as unique_models,
                       COUNT(DISTINCT p.id) as placements
                FROM m2_models m
                LEFT JOIN m2_placements p ON m.id = p.model_id
                WHERE m.wdt_id = ?
            ''', (wdt_id,))
            m2_stats = cursor.fetchone()

            cursor.execute('''
                SELECT COUNT(DISTINCT model_path) as unique_models,
                       COUNT(DISTINCT p.id) as placements
                FROM wmo_models m
                LEFT JOIN wmo_placements p ON m.id = p.model_id
                WHERE m.wdt_id = ?
            ''', (wdt_id,))
            wmo_stats = cursor.fetchone()

            # Count textures and layers
            cursor.execute('''
                SELECT COUNT(DISTINCT texture_path) as unique_textures,
                       COUNT(*) as total_textures
                FROM wdt_textures
                WHERE wdt_id = ?
            ''', (wdt_id,))
            texture_stats = cursor.fetchone()

            cursor.execute('''
                SELECT COUNT(*) as layer_count
                FROM tile_layers tl
                JOIN tile_mcnk tm ON tl.tile_mcnk_id = tm.id
                WHERE tm.wdt_id = ?
            ''', (wdt_id,))
            layer_count = cursor.fetchone()[0]

            # Count height maps and liquid data
            cursor.execute('''
                SELECT COUNT(*) as height_maps,
                       (SELECT COUNT(*) FROM liquid_data ld 
                        JOIN tile_mcnk tm2 ON ld.tile_mcnk_id = tm2.id 
                        WHERE tm2.wdt_id = ?) as liquid_chunks
                FROM height_map_info hm
                JOIN tile_mcnk tm ON hm.tile_mcnk_id = tm.id
                WHERE tm.wdt_id = ?
            ''', (wdt_id, wdt_id))
            terrain_stats = cursor.fetchone()

            print("\nAsset Counts:")
            print(f"  M2 Models: {m2_stats[0]} unique models with {m2_stats[1]} placements")
            print(f"  WMO Models: {wmo_stats[0]} unique models with {wmo_stats[1]} placements")
            print(f"  Textures: {texture_stats[0]} unique, {texture_stats[1]} total")
            print(f"  Texture Layers: {layer_count}")
            print("\nTerrain Data:")
            print(f"  Height Maps: {terrain_stats[0]}")
            print(f"  Liquid Chunks: {terrain_stats[1]}")

            # Log detailed per-tile information
            logging.info(f"\nDetailed tile information for {map_name}:")
            cursor.execute('''
                SELECT t.tile_x, t.tile_y,
                       COUNT(DISTINCT tex.texture_path) as textures,
                       COUNT(DISTINCT tl.id) as layers,
                       CASE WHEN hm.id IS NOT NULL THEN 1 ELSE 0 END as has_height_map,
                       CASE WHEN ld.id IS NOT NULL THEN 1 ELSE 0 END as has_liquid
                FROM map_tiles t
                LEFT JOIN tile_mcnk tm ON t.wdt_id = tm.wdt_id 
                    AND t.tile_x = tm.tile_x AND t.tile_y = tm.tile_y
                LEFT JOIN wdt_textures tex ON t.wdt_id = tex.wdt_id 
                    AND t.tile_x = tex.tile_x AND t.tile_y = tex.tile_y
                LEFT JOIN tile_layers tl ON tm.id = tl.tile_mcnk_id
                LEFT JOIN height_map_info hm ON tm.id = hm.tile_mcnk_id
                LEFT JOIN liquid_data ld ON tm.id = ld.tile_mcnk_id
                WHERE t.wdt_id = ?
                GROUP BY t.tile_x, t.tile_y
            ''', (wdt_id,))
            
            for row in cursor.fetchall():
                logging.info(
                    f"Tile ({row[0]}, {row[1]}): "
                    f"{row[2]} textures, {row[3]} layers, "
                    f"{'has' if row[4] else 'no'} height map, "
                    f"{'has' if row[5] else 'no'} liquid data"
                )

    finally:
        conn.close()

    print(f"\nDetailed statistics written to: {log_filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python wdt_stats.py <database_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    gather_statistics(db_path)