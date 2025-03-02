using System;
using System.Collections.Generic;
using System.Numerics;
using System.Text;

namespace ModernWoWTools.ADTMeta.Analysis.Models
{
    /// <summary>
    /// Represents a terrain chunk (MCNK) in an ADT file.
    /// </summary>
    public class TerrainChunk
    {
        /// <summary>
        /// Gets or sets the position of the chunk in the ADT grid (x, y).
        /// </summary>
        public Vector2 Position { get; set; }

        /// <summary>
        /// Gets or sets the area ID of the chunk.
        /// </summary>
        public int AreaId { get; set; }

        /// <summary>
        /// Gets or sets the flags for the chunk.
        /// </summary>
        public uint Flags { get; set; }

        /// <summary>
        /// Gets or sets the holes in the chunk.
        /// </summary>
        public uint Holes { get; set; }

        /// <summary>
        /// Gets or sets the liquid level of the chunk.
        /// </summary>
        public float LiquidLevel { get; set; }

        /// <summary>
        /// Gets or sets the position of the chunk in the world.
        /// </summary>
        public Vector3 WorldPosition { get; set; }

        /// <summary>
        /// Gets or sets the normal vectors for the chunk.
        /// </summary>
        public List<Vector3> Normals { get; set; } = new List<Vector3>();

        /// <summary>
        /// Gets or sets the height values for the chunk.
        /// </summary>
        public List<float> Heights { get; set; } = new List<float>();

        /// <summary>
        /// Gets or sets the texture layers for the chunk.
        /// </summary>
        public List<TextureLayer> TextureLayers { get; set; } = new List<TextureLayer>();

        /// <summary>
        /// Gets or sets the vertex colors for the chunk.
        /// </summary>
        public List<Vector3> VertexColors { get; set; } = new List<Vector3>();

        /// <summary>
        /// Gets or sets the shadow map for the chunk.
        /// </summary>
        public byte[] ShadowMap { get; set; } = Array.Empty<byte>();

        /// <summary>
        /// Gets or sets the alpha maps for the chunk.
        /// </summary>
        public List<byte[]> AlphaMaps { get; set; } = new List<byte[]>();

        /// <summary>
        /// Gets or sets the doodad references for the chunk.
        /// </summary>
        public List<int> DoodadRefs { get; set; } = new List<int>();

        /// <summary>
        /// Gets a human-readable representation of the chunk's heightmap data.
        /// </summary>
        /// <returns>A string containing the heightmap data.</returns>
        public string GetHeightmapString()
        {
            var sb = new StringBuilder();
            sb.AppendLine($"Heightmap for chunk at ({Position.X}, {Position.Y}):");
            
            // Heights are stored in a 9x9 grid (9 vertices per side)
            for (int y = 0; y < 9; y++)
            {
                for (int x = 0; x < 9; x++)
                {
                    sb.Append($"{Heights[y * 9 + x]:F2} ");
                }
                sb.AppendLine();
            }
            return sb.ToString();
        }
    }

    /// <summary>
    /// Represents a texture layer in a terrain chunk.
    /// </summary>
    public class TextureLayer
    {
        /// <summary>
        /// Gets or sets the texture ID for the layer.
        /// </summary>
        public int TextureId { get; set; }

        /// <summary>
        /// Gets or sets the flags for the layer.
        /// </summary>
        public uint Flags { get; set; }

        /// <summary>
        /// Gets or sets the effect ID for the layer.
        /// </summary>
        public int EffectId { get; set; }

        /// <summary>
        /// Gets or sets the alpha map offset for the layer.
        /// </summary>
        public int AlphaMapOffset { get; set; }

        /// <summary>
        /// Gets or sets the alpha map size for the layer.
        /// </summary>
        public int AlphaMapSize { get; set; }

        /// <summary>
        /// Gets or sets the alpha map data for the layer.
        /// </summary>
        public byte[] AlphaMap { get; set; } = Array.Empty<byte>();

        /// <summary>
        /// Gets or sets the texture name for the layer.
        /// </summary>
        public string TextureName { get; set; } = string.Empty;

        /// <summary>
        /// Gets a human-readable representation of the texture layer's alpha map.
        /// </summary>
        /// <returns>A string containing the alpha map data.</returns>
        public string GetAlphaMapString()
        {
            if (AlphaMap == null || AlphaMap.Length == 0)
                return "No alpha map data available.";

            var sb = new StringBuilder();
            sb.AppendLine($"Alpha map for texture {TextureId} ({TextureName}):");
            
            // Alpha maps are typically 64x64 (4096 bytes) or 128x128 (16384 bytes)
            int size = (int)Math.Sqrt(AlphaMap.Length);
            
            // If the size is not a perfect square, just output the raw bytes
            if (size * size != AlphaMap.Length)
            {
                sb.AppendLine($"Alpha map size: {AlphaMap.Length} bytes (non-square)");
                return sb.ToString();
            }
            
            // Output a simplified representation (every 8th pixel)
            sb.AppendLine($"Alpha map size: {size}x{size}");
            sb.AppendLine("Simplified representation (every 8th pixel):");
            
            for (int y = 0; y < size; y += 8)
            {
                for (int x = 0; x < size; x += 8)
                {
                    int index = y * size + x;
                    if (index < AlphaMap.Length)
                    {
                        // Convert alpha value (0-255) to a character representation
                        char alphaChar = GetAlphaChar(AlphaMap[index]);
                        sb.Append(alphaChar);
                    }
                }
                sb.AppendLine();
            }
            
            return sb.ToString();
        }
        
        private char GetAlphaChar(byte alpha)
        {
            // Convert alpha value (0-255) to a character representation
            // ' ' (space) for 0, '#' for 255, and various characters in between
            return " .:-=+*#%@"[Math.Min(alpha * 10 / 256, 9)];
        }
    }
}