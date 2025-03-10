using System;
using System.IO;
using System.Linq;
using System.Numerics;

namespace WarcraftAnalyzer.Files.WLW
{
    /// <summary>
    /// Provides functionality to export water mesh files to OBJ format.
    /// </summary>
    public static class MeshExporter
    {
        /// <summary>
        /// Exports a WLW file to OBJ format.
        /// </summary>
        /// <param name="wlw">The WLW file to export.</param>
        /// <param name="outputPath">The path to write the OBJ file to.</param>
        public static void ExportToObj(WLWFile wlw, string outputPath)
        {
            using var writer = new StreamWriter(outputPath);
            
            // Write OBJ header
            writer.WriteLine("# Water mesh exported from WLW/WLQ/WLM file");
            writer.WriteLine($"# File: {wlw.FileName}");
            writer.WriteLine();
            
            // Write material library reference
            writer.WriteLine("mtllib water.mtl");
            writer.WriteLine();
            
            // Write object name
            writer.WriteLine($"o {Path.GetFileNameWithoutExtension(wlw.FileName)}");
            writer.WriteLine();
            
            // Write vertices
            foreach (var vertex in wlw.Vertices)
            {
                writer.WriteLine($"v {vertex.X} {vertex.Y} {vertex.Z}");
            }
            writer.WriteLine();
            
            // Write texture coordinates
            foreach (var texCoord in wlw.TexCoords)
            {
                writer.WriteLine($"vt {texCoord.X} {texCoord.Y}");
            }
            writer.WriteLine();
            
            // Write normals (if available, otherwise use default up vector)
            if (wlw.Normals != null && wlw.Normals.Count > 0)
            {
                foreach (var normal in wlw.Normals)
                {
                    writer.WriteLine($"vn {normal.X} {normal.Y} {normal.Z}");
                }
            }
            else
            {
                // Default normal pointing up
                writer.WriteLine("vn 0 1 0");
            }
            writer.WriteLine();
            
            // Write material
            writer.WriteLine("usemtl water");
            writer.WriteLine();
            
            // Write faces
            if (wlw.Indices != null && wlw.Indices.Count > 0)
            {
                // Use indices if available
                for (int i = 0; i < wlw.Indices.Count; i += 3)
                {
                    int v1 = wlw.Indices[i] + 1; // OBJ indices are 1-based
                    int v2 = wlw.Indices[i + 1] + 1;
                    int v3 = wlw.Indices[i + 2] + 1;
                    
                    if (wlw.Normals != null && wlw.Normals.Count > 0)
                    {
                        writer.WriteLine($"f {v1}/{v1}/{v1} {v2}/{v2}/{v2} {v3}/{v3}/{v3}");
                    }
                    else
                    {
                        writer.WriteLine($"f {v1}/{v1}/1 {v2}/{v2}/1 {v3}/{v3}/1");
                    }
                }
            }
            else
            {
                // Generate triangles from vertices (assuming triangle strip)
                for (int i = 0; i < wlw.Vertices.Count - 2; i++)
                {
                    int v1 = i + 1; // OBJ indices are 1-based
                    int v2 = i + 2;
                    int v3 = i + 3;
                    
                    if (wlw.Normals != null && wlw.Normals.Count > 0)
                    {
                        writer.WriteLine($"f {v1}/{v1}/{v1} {v2}/{v2}/{v2} {v3}/{v3}/{v3}");
                    }
                    else
                    {
                        writer.WriteLine($"f {v1}/{v1}/1 {v2}/{v2}/1 {v3}/{v3}/1");
                    }
                }
            }
            
            // Create a simple material file
            string mtlPath = Path.Combine(Path.GetDirectoryName(outputPath), "water.mtl");
            using (var mtlWriter = new StreamWriter(mtlPath))
            {
                mtlWriter.WriteLine("# Material definitions for water");
                mtlWriter.WriteLine();
                
                // Water material
                mtlWriter.WriteLine("newmtl water");
                mtlWriter.WriteLine("Ka 0.2 0.4 0.8");
                mtlWriter.WriteLine("Kd 0.2 0.4 0.8");
                mtlWriter.WriteLine("Ks 0.8 0.8 0.8");
                mtlWriter.WriteLine("d 0.7");
                mtlWriter.WriteLine("Ns 50.0");
                mtlWriter.WriteLine("illum 2");
                
                // Try to determine the water type and use an appropriate texture
                string textureName = "WaterBlue_1.png";
                
                if (wlw.FileName.Contains("lava", StringComparison.OrdinalIgnoreCase) ||
                    wlw.FileName.Contains("fire", StringComparison.OrdinalIgnoreCase))
                {
                    textureName = "Red_1.png";
                }
                else if (wlw.FileName.Contains("slime", StringComparison.OrdinalIgnoreCase) ||
                         wlw.FileName.Contains("poison", StringComparison.OrdinalIgnoreCase))
                {
                    textureName = "Green_1.png";
                }
                else if (wlw.FileName.Contains("ocean", StringComparison.OrdinalIgnoreCase) ||
                         wlw.FileName.Contains("sea", StringComparison.OrdinalIgnoreCase))
                {
                    textureName = "Blue_1.png";
                }
                
                mtlWriter.WriteLine($"map_Kd {textureName}");
                mtlWriter.WriteLine();
            }
        }
    }
}