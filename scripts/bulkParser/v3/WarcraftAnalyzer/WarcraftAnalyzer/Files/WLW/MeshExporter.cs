using System;
using System.IO;
using System.Collections.Generic;
using System.Numerics;

namespace WarcraftAnalyzer.Files.WLW
{
    /// <summary>
    /// Handles exporting liquid meshes to OBJ format.
    /// </summary>
    public class MeshExporter
    {
        /// <summary>
        /// Mapping of liquid types to textures and colors.
        /// </summary>
        public static readonly Dictionary<ushort, (string texture, Vector4 color)> LiquidTypeInfo = new()
        {
            [0] = ("WaterBlue_1.png", new Vector4(0.2f, 0.5f, 0.8f, 0.8f)), // Still
            [1] = ("Blue_1.png", new Vector4(0.1f, 0.3f, 0.7f, 0.8f)),      // Ocean
            [2] = ("Grey_1.png", new Vector4(0.5f, 0.5f, 0.5f, 0.8f)),      // Unknown
            [4] = ("WaterBlue_1.png", new Vector4(0.3f, 0.6f, 0.9f, 0.8f)), // River
            [6] = ("Red_1.png", new Vector4(0.8f, 0.2f, 0.1f, 0.8f)),       // Magma
            [8] = ("WaterBlue_1.png", new Vector4(0.3f, 0.6f, 0.9f, 0.8f))  // Fast flowing
        };

        /// <summary>
        /// Exports a WLW file to OBJ format.
        /// </summary>
        /// <param name="wlw">The WLW file to export.</param>
        /// <param name="outputPath">The output path for the OBJ file.</param>
        public static void ExportToObj(WLWFile wlw, string outputPath)
        {
            var liquidType = (ushort)(wlw.LiquidType & 0xFFFF);
            var liquidInfo = LiquidTypeInfo.ContainsKey(liquidType) ? LiquidTypeInfo[liquidType] : LiquidTypeInfo[2];

            // Write MTL file
            var mtlPath = Path.ChangeExtension(outputPath, ".mtl");
            File.WriteAllText(mtlPath, $@"newmtl liquid
Ka {liquidInfo.color.X:F3} {liquidInfo.color.Y:F3} {liquidInfo.color.Z:F3}
Kd {liquidInfo.color.X:F3} {liquidInfo.color.Y:F3} {liquidInfo.color.Z:F3}
Ks 0.500 0.500 0.500
d {liquidInfo.color.W:F3}
Ns 50.0
illum 2
map_Kd {liquidInfo.texture}
");

            // Write OBJ file
            using var writer = new StreamWriter(outputPath);
            writer.WriteLine($"mtllib {Path.GetFileName(mtlPath)}");
            writer.WriteLine("usemtl liquid");

            // Write vertices
            var vertexOffset = 1; // OBJ indices are 1-based
            foreach (var block in wlw.Blocks)
            {
                foreach (var vertex in block.Vertices)
                {
                    writer.WriteLine($"v {vertex.X:F6} {vertex.Y:F6} {vertex.Z:F6}");
                }

                // Create triangles from the 4x4 grid
                for (int i = 0; i < 3; i++)
                {
                    for (int j = 0; j < 3; j++)
                    {
                        var v1 = i * 4 + j;
                        var v2 = i * 4 + (j + 1);
                        var v3 = (i + 1) * 4 + (j + 1);
                        var v4 = (i + 1) * 4 + j;

                        // Write two triangles for each quad
                        writer.WriteLine($"f {v1 + vertexOffset} {v2 + vertexOffset} {v3 + vertexOffset}");
                        writer.WriteLine($"f {v1 + vertexOffset} {v3 + vertexOffset} {v4 + vertexOffset}");
                    }
                }

                vertexOffset += block.Vertices.Length;
            }
        }
    }
}