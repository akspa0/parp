using System;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Collections.Generic;
using System.Numerics;
using System.Drawing;
using System.Linq;
using Warcraft.NET.Files.Structures;
using ADT = WarcraftAnalyzer.Files.ADT;
using WarcraftAnalyzer.Files.PM4;
using WarcraftAnalyzer.Files.PD4;
using WarcraftAnalyzer.Files.WLW;

namespace WarcraftAnalyzer.Files.Serialization
{
    /// <summary>
    /// Provides JSON serialization for PM4, PD4, WLW, and ADT files.
    /// </summary>
    public static class JsonSerializer
    {
        private static readonly JsonSerializerOptions Options = new()
        {
            WriteIndented = true,
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
            Converters = { 
                new C3VectorConverter(),
                new Vector2Converter(),
                new Vector3Converter(),
                new ColorConverter()
            }
        };

        /// <summary>
        /// Serializes a PM4 file to JSON.
        /// </summary>
        /// <param name="file">The PM4 file to serialize.</param>
        /// <returns>A JSON string containing the file's data.</returns>
        public static string SerializePM4(PM4.PM4File file)
        {
            var data = new Dictionary<string, object>
            {
                ["Version"] = file.Version?.Version,
                ["ShadowData"] = SerializeShadowData(file.ShadowData),
                ["VertexPositions"] = SerializeVectors(file.VertexPositions?.Vertices),
                ["VertexIndices"] = SerializeIndices(file.VertexIndices?.VertexIndices),
                ["NormalCoordinates"] = SerializeVectors(file.NormalCoordinates?.Normals),
                ["Links"] = SerializeLinks(file.Links),
                ["VertexData"] = SerializeVectors(file.VertexData?.Vertices),
                ["VertexIndices2"] = SerializeIndices(file.VertexIndices2?.VertexIndices),
                ["SurfaceData"] = SerializeSurfaceData(file.SurfaceData),
                ["PositionData"] = SerializePositionData(file.PositionData),
                ["ValuePairs"] = SerializeValuePairs(file.ValuePairs),
                ["BuildingData"] = SerializeBuildingData(file.BuildingData),
                ["SimpleData"] = file.SimpleData?.Value,
                ["FinalData"] = SerializeIndices(file.FinalData?.Values)
            };

            return System.Text.Json.JsonSerializer.Serialize(data, Options);
        }

        /// <summary>
        /// Serializes a PD4 file to JSON.
        /// </summary>
        /// <param name="file">The PD4 file to serialize.</param>
        /// <returns>A JSON string containing the file's data.</returns>
        public static string SerializePD4(PD4.PD4File file)
        {
            var data = new Dictionary<string, object>
            {
                ["Version"] = file.Version?.Version,
                ["CRC"] = file.CRC?.Value,
                ["ShadowData"] = SerializeShadowData(file.ShadowData),
                ["VertexPositions"] = SerializeVectors(file.VertexPositions?.Vertices),
                ["VertexIndices"] = SerializeIndices(file.VertexIndices?.VertexIndices),
                ["NormalCoordinates"] = SerializeVectors(file.NormalCoordinates?.Normals),
                ["Links"] = SerializeLinks(file.Links),
                ["VertexData"] = SerializeVectors(file.VertexData?.Vertices),
                ["VertexIndices2"] = SerializeIndices(file.VertexIndices2?.VertexIndices),
                ["SurfaceData"] = SerializeSurfaceData(file.SurfaceData)
            };

            return System.Text.Json.JsonSerializer.Serialize(data, Options);
        }

        /// <summary>
        /// Serializes a WLW file to JSON.
        /// </summary>
        /// <param name="file">The WLW file to serialize.</param>
        /// <returns>A JSON string containing the file's data.</returns>
        public static string SerializeWLW(WLW.WLWFile file)
        {
            var data = new Dictionary<string, object>
            {
                ["Version"] = file.Version,
                ["Unk06"] = file.Unk06,
                ["LiquidType"] = file.LiquidType,
                ["LiquidTypeName"] = ((LiquidType)(file.LiquidType & 0xFFFF)).ToString(),
                ["BlockCount"] = file.BlockCount,
                ["Blocks"] = SerializeWLWBlocks(file.Blocks),
                ["Block2Count"] = file.Block2Count,
                ["Block2s"] = SerializeWLWBlock2s(file.Block2s),
                ["Unknown"] = file.Unknown,
                ["IsMagma"] = file.IsMagma,
                ["IsQuality"] = file.IsQuality
            };

            return System.Text.Json.JsonSerializer.Serialize(data, Options);
        }

        private static object SerializeWLWBlocks(List<WLW.LiquidBlock> blocks)
        {
            if (blocks == null) return null;

            var entries = new List<Dictionary<string, object>>();
            foreach (var block in blocks)
            {
                entries.Add(new Dictionary<string, object>
                {
                    ["Vertices"] = block.Vertices,
                    ["Coordinates"] = block.Coordinates,
                    ["Data"] = block.Data
                });
            }
            return entries;
        }

        private static object SerializeWLWBlock2s(List<WLW.LiquidBlock2> blocks)
        {
            if (blocks == null) return null;

            var entries = new List<Dictionary<string, object>>();
            foreach (var block in blocks)
            {
                entries.Add(new Dictionary<string, object>
                {
                    ["Unk00"] = block.Unk00,
                    ["Unk0C"] = block.Unk0C,
                    ["Unk14"] = block.Unk14
                });
            }
            return entries;
        }

        private static object SerializeShadowData(PM4.MSHD chunk)
        {
            if (chunk?.ShadowEntries == null) return null;

            var entries = new List<Dictionary<string, object>>();
            foreach (var entry in chunk.ShadowEntries)
            {
                entries.Add(new Dictionary<string, object>
                {
                    ["Value0x00"] = entry.Value0x00,
                    ["Value0x04"] = entry.Value0x04,
                    ["Value0x08"] = entry.Value0x08,
                    ["Values0x0c"] = entry.Values0x0c
                });
            }
            return entries;
        }

        private static object SerializeVectors(IReadOnlyList<C3Vector> vectors)
        {
            if (vectors == null) return null;

            var entries = new List<Dictionary<string, float>>();
            foreach (var vector in vectors)
            {
                entries.Add(new Dictionary<string, float>
                {
                    ["X"] = vector.X,
                    ["Y"] = vector.Y,
                    ["Z"] = vector.Z
                });
            }
            return entries;
        }

        private static object SerializeIndices(IReadOnlyList<uint> indices)
        {
            return indices?.ToArray();
        }

        private static object SerializeLinks(PM4.MSLK chunk)
        {
            if (chunk?.Links == null) return null;

            var entries = new List<Dictionary<string, object>>();
            foreach (var entry in chunk.Links)
            {
                entries.Add(new Dictionary<string, object>
                {
                    ["Flag0x00"] = entry.Flag0x00,
                    ["Flag0x01"] = entry.Flag0x01,
                    ["Value0x02"] = entry.Value0x02,
                    ["Value0x04"] = entry.Value0x04,
                    ["MSPIFirstIndex"] = entry.MSPIFirstIndex,
                    ["MSPIIndexCount"] = entry.MSPIIndexCount,
                    ["Value0x0c"] = entry.Value0x0c,
                    ["Value0x10"] = entry.Value0x10,
                    ["Value0x12"] = entry.Value0x12
                });
            }
            return entries;
        }

        private static object SerializeSurfaceData(PM4.MSUR chunk)
        {
            if (chunk?.SurfaceEntries == null) return null;

            var entries = new List<Dictionary<string, object>>();
            foreach (var entry in chunk.SurfaceEntries)
            {
                entries.Add(new Dictionary<string, object>
                {
                    ["Flag0x00"] = entry.Flag0x00,
                    ["Flag0x01"] = entry.Flag0x01,
                    ["Flag0x02"] = entry.Flag0x02,
                    ["Flag0x03"] = entry.Flag0x03,
                    ["Value0x04"] = entry.Value0x04,
                    ["Value0x08"] = entry.Value0x08,
                    ["Value0x0c"] = entry.Value0x0c,
                    ["Value0x10"] = entry.Value0x10,
                    ["MSVIFirstIndex"] = entry.MSVIFirstIndex,
                    ["Value0x18"] = entry.Value0x18,
                    ["Value0x1c"] = entry.Value0x1c
                });
            }
            return entries;
        }

        private static object SerializePositionData(PM4.MPRL chunk)
        {
            if (chunk?.Positions == null) return null;

            var entries = new List<Dictionary<string, object>>();
            foreach (var entry in chunk.Positions)
            {
                entries.Add(new Dictionary<string, object>
                {
                    ["Value0x00"] = entry.Value0x00,
                    ["Value0x02"] = entry.Value0x02,
                    ["Value0x04"] = entry.Value0x04,
                    ["Value0x06"] = entry.Value0x06,
                    ["Position"] = new Dictionary<string, float>
                    {
                        ["X"] = entry.Position.X,
                        ["Y"] = entry.Position.Y,
                        ["Z"] = entry.Position.Z
                    },
                    ["Value0x14"] = entry.Value0x14,
                    ["Value0x16"] = entry.Value0x16
                });
            }
            return entries;
        }

        private static object SerializeValuePairs(PM4.MPRR chunk)
        {
            if (chunk?.Pairs == null) return null;

            var entries = new List<Dictionary<string, ushort>>();
            foreach (var entry in chunk.Pairs)
            {
                entries.Add(new Dictionary<string, ushort>
                {
                    ["Value0x00"] = entry.Value0x00,
                    ["Value0x02"] = entry.Value0x02
                });
            }
            return entries;
        }

        private static object SerializeBuildingData(PM4.MDBH chunk)
        {
            if (chunk?.Entries == null) return null;

            var entries = new List<Dictionary<string, object>>();
            foreach (var entry in chunk.Entries)
            {
                entries.Add(new Dictionary<string, object>
                {
                    ["Indices"] = entry.Indices.ToArray(),
                    ["Filenames"] = entry.Filenames.ToArray()
                });
            }
            return entries;
        }

        /// <summary>
        /// Serializes an ADT file to JSON.
        /// </summary>
        /// <param name="file">The ADT file to serialize.</param>
        /// <returns>A JSON string containing the file's data.</returns>
        public static string SerializeADT(WarcraftAnalyzer.Files.ADT.ADTFile file)
        {
            var data = new Dictionary<string, object>
            {
                ["FileName"] = file.FileName,
                ["XCoord"] = file.XCoord,
                ["YCoord"] = file.YCoord,
                ["TextureReferences"] = SerializeFileReferences(file.TextureReferences),
                ["ModelReferences"] = SerializeFileReferences(file.ModelReferences),
                ["WmoReferences"] = SerializeFileReferences(file.WmoReferences),
                ["ModelPlacements"] = SerializeModelPlacements(file.ModelPlacements),
                ["WmoPlacements"] = SerializeWmoPlacements(file.WmoPlacements),
                ["UniqueIds"] = file.UniqueIds.ToArray(),
                ["TerrainChunks"] = SerializeTerrainChunks(file.TerrainChunks),
                ["Errors"] = file.Errors.ToArray()
            };

            return System.Text.Json.JsonSerializer.Serialize(data, Options);
        }

        private static object SerializeFileReferences(List<WarcraftAnalyzer.Files.ADT.FileReference> references)
        {
            if (references == null || references.Count == 0) return null;

            var entries = new List<Dictionary<string, object>>();
            foreach (var reference in references)
            {
                entries.Add(new Dictionary<string, object>
                {
                    ["Path"] = reference.Path,
                    ["NormalizedPath"] = reference.NormalizedPath,
                    ["Type"] = reference.Type.ToString(),
                    ["IsValid"] = reference.IsValid,
                    ["ExistsInListfile"] = reference.ExistsInListfile
                });
            }
            return entries;
        }

        private static object SerializeModelPlacements(List<WarcraftAnalyzer.Files.ADT.ModelPlacement> placements)
        {
            if (placements == null || placements.Count == 0) return null;

            var entries = new List<Dictionary<string, object>>();
            foreach (var placement in placements)
            {
                entries.Add(new Dictionary<string, object>
                {
                    ["ModelReference"] = new Dictionary<string, string>
                    {
                        ["Path"] = placement.ModelReference?.Path
                    },
                    ["Position"] = new Dictionary<string, float>
                    {
                        ["X"] = placement.Position.X,
                        ["Y"] = placement.Position.Y,
                        ["Z"] = placement.Position.Z
                    },
                    ["Rotation"] = new Dictionary<string, float>
                    {
                        ["X"] = placement.Rotation.X,
                        ["Y"] = placement.Rotation.Y,
                        ["Z"] = placement.Rotation.Z
                    },
                    ["Scale"] = placement.Scale,
                    ["UniqueId"] = placement.UniqueId
                });
            }
            return entries;
        }

        private static object SerializeWmoPlacements(List<WarcraftAnalyzer.Files.ADT.WmoPlacement> placements)
        {
            if (placements == null || placements.Count == 0) return null;

            var entries = new List<Dictionary<string, object>>();
            foreach (var placement in placements)
            {
                entries.Add(new Dictionary<string, object>
                {
                    ["WmoReference"] = new Dictionary<string, string>
                    {
                        ["Path"] = placement.WmoReference?.Path
                    },
                    ["Position"] = new Dictionary<string, float>
                    {
                        ["X"] = placement.Position.X,
                        ["Y"] = placement.Position.Y,
                        ["Z"] = placement.Position.Z
                    },
                    ["Rotation"] = new Dictionary<string, float>
                    {
                        ["X"] = placement.Rotation.X,
                        ["Y"] = placement.Rotation.Y,
                        ["Z"] = placement.Rotation.Z
                    },
                    ["UniqueId"] = placement.UniqueId
                });
            }
            return entries;
        }

        private static object SerializeTerrainChunks(List<WarcraftAnalyzer.Files.ADT.TerrainChunk> chunks)
        {
            if (chunks == null || chunks.Count == 0) return null;

            var entries = new List<Dictionary<string, object>>();
            foreach (var chunk in chunks)
            {
                entries.Add(new Dictionary<string, object>
                {
                    ["X"] = chunk.X,
                    ["Y"] = chunk.Y,
                    ["AreaId"] = chunk.AreaId,
                    ["Flags"] = chunk.Flags,
                    ["Holes"] = chunk.Holes,
                    ["TextureLayers"] = SerializeTextureLayers(chunk.TextureLayers),
                    ["DoodadRefs"] = chunk.DoodadRefs.ToArray()
                });
            }
            return entries;
        }

        private static object SerializeTextureLayers(List<WarcraftAnalyzer.Files.ADT.TextureLayer> layers)
        {
            if (layers == null || layers.Count == 0) return null;

            var entries = new List<Dictionary<string, object>>();
            foreach (var layer in layers)
            {
                entries.Add(new Dictionary<string, object>
                {
                    ["TextureReference"] = new Dictionary<string, string>
                    {
                        ["Path"] = layer.TextureReference?.Path
                    },
                    ["EffectId"] = layer.EffectId,
                    ["Flags"] = layer.Flags
                });
            }
            return entries;
        }
    }

    /// <summary>
    /// JSON converter for C3Vector type.
    /// </summary>
    public class C3VectorConverter : JsonConverter<C3Vector>
    {
        public override C3Vector Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            throw new NotImplementedException("Reading C3Vector from JSON is not supported.");
        }

        public override void Write(Utf8JsonWriter writer, C3Vector value, JsonSerializerOptions options)
        {
            writer.WriteStartObject();
            writer.WriteNumber("X", value.X);
            writer.WriteNumber("Y", value.Y);
            writer.WriteNumber("Z", value.Z);
            writer.WriteEndObject();
        }
    }

    /// <summary>
    /// JSON converter for Vector2 type.
    /// </summary>
    public class Vector2Converter : JsonConverter<Vector2>
    {
        public override Vector2 Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            throw new NotImplementedException("Reading Vector2 from JSON is not supported.");
        }

        public override void Write(Utf8JsonWriter writer, Vector2 value, JsonSerializerOptions options)
        {
            writer.WriteStartObject();
            writer.WriteNumber("X", value.X);
            writer.WriteNumber("Y", value.Y);
            writer.WriteEndObject();
        }
    }

    /// <summary>
    /// JSON converter for Vector3 type.
    /// </summary>
    public class Vector3Converter : JsonConverter<Vector3>
    {
        public override Vector3 Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            throw new NotImplementedException("Reading Vector3 from JSON is not supported.");
        }

        public override void Write(Utf8JsonWriter writer, Vector3 value, JsonSerializerOptions options)
        {
            writer.WriteStartObject();
            writer.WriteNumber("X", value.X);
            writer.WriteNumber("Y", value.Y);
            writer.WriteNumber("Z", value.Z);
            writer.WriteEndObject();
        }
    }

    /// <summary>
    /// JSON converter for Color type.
    /// </summary>
    public class ColorConverter : JsonConverter<Color>
    {
        public override Color Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            throw new NotImplementedException("Reading Color from JSON is not supported.");
        }

        public override void Write(Utf8JsonWriter writer, Color value, JsonSerializerOptions options)
        {
            writer.WriteStartObject();
            writer.WriteNumber("R", value.R);
            writer.WriteNumber("G", value.G);
            writer.WriteNumber("B", value.B);
            writer.WriteNumber("A", value.A);
            writer.WriteEndObject();
        }
    }
}