using System.Collections.Generic;
using System.IO;
using Warcraft.NET.Files;
using Warcraft.NET.Files.ADT.Chunks;
using Warcraft.NET.Files.Interfaces;
using MVER = Warcraft.NET.Files.ADT.Chunks.MVER;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// Represents a PM4 file, which is a server-side supplementary file to ADTs.
    /// These files are not shipped to the client and are used by the server only.
    /// </summary>
    public class PM4File : ChunkedFile
    {
        /// <summary>
        /// Gets or sets the version chunk.
        /// </summary>
        public MVER Version { get; set; }

        /// <summary>
        /// Gets or sets the shadow data chunk.
        /// </summary>
        public MSHD ShadowData { get; set; }

        /// <summary>
        /// Gets or sets the vertex positions chunk.
        /// </summary>
        public MSPV VertexPositions { get; set; }

        /// <summary>
        /// Gets or sets the vertex indices chunk.
        /// </summary>
        public MSPI VertexIndices { get; set; }

        /// <summary>
        /// Gets or sets the normal coordinates chunk.
        /// </summary>
        public MSCN NormalCoordinates { get; set; }

        /// <summary>
        /// Gets or sets the links chunk.
        /// </summary>
        public MSLK Links { get; set; }

        /// <summary>
        /// Gets or sets the vertex data chunk.
        /// </summary>
        public MSVT VertexData { get; set; }

        /// <summary>
        /// Gets or sets the vertex indices chunk.
        /// </summary>
        public MSVI VertexIndices2 { get; set; }

        /// <summary>
        /// Gets or sets the surface data chunk.
        /// </summary>
        public MSUR SurfaceData { get; set; }

        /// <summary>
        /// Gets or sets the position data chunk.
        /// </summary>
        public MPRL PositionData { get; set; }

        /// <summary>
        /// Gets or sets the value pairs chunk.
        /// </summary>
        public MPRR ValuePairs { get; set; }

        /// <summary>
        /// Gets or sets the building data chunk.
        /// </summary>
        public MDBH BuildingData { get; set; }

        /// <summary>
        /// Gets or sets the simple data chunk.
        /// </summary>
        public MDOS SimpleData { get; set; }

        /// <summary>
        /// Gets or sets the final data chunk.
        /// </summary>
        public MDSF FinalData { get; set; }

        /// <summary>
        /// Initializes a new instance of the <see cref="PM4File"/> class.
        /// </summary>
        public PM4File()
        {
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="PM4File"/> class.
        /// </summary>
        /// <param name="inData">The binary data to load from.</param>
        public PM4File(byte[] inData) : base(inData)
        {
            using (var ms = new MemoryStream(inData))
            using (var br = new BinaryReader(ms))
            {
                while (ms.Position < ms.Length)
                {
                    try
                    {
                        // Read chunk signature (4 bytes)
                        string signature = new string(br.ReadChars(4));
                        
                        // Read chunk size (4 bytes)
                        uint size = br.ReadUInt32();
                        
                        // Read chunk data
                        byte[] data = br.ReadBytes((int)size);
                        
                        // Process the chunk
                        ProcessChunk(signature, data);
                    }
                    catch (EndOfStreamException)
                    {
                        // End of file reached
                        break;
                    }
                }
            }
        }

        /// <summary>
        /// Processes a chunk of data.
        /// </summary>
        /// <param name="signature">The chunk signature.</param>
        /// <param name="data">The chunk data.</param>
        protected void ProcessChunk(string signature, byte[] data)
        {
            switch (signature)
            {
                case "MVER":
                case "REVM":
                    Version = new MVER(data);
                    break;

                case "MSHD":
                case "DHSM":
                    ShadowData = new MSHD(data);
                    break;

                case "MSPV":
                case "VPSM":
                    VertexPositions = new MSPV(data);
                    break;

                case "MSPI":
                case "IPSM":
                    VertexIndices = new MSPI(data);
                    break;

                case "MSCN":
                case "NCSM":
                    NormalCoordinates = new MSCN(data);
                    break;

                case "MSLK":
                case "KLSM":
                    Links = new MSLK(data);
                    break;

                case "MSVT":
                case "TVSM":
                    VertexData = new MSVT(data);
                    break;

                case "MSVI":
                case "IVSM":
                    VertexIndices2 = new MSVI(data);
                    break;

                case "MSUR":
                case "RUSM":
                    SurfaceData = new MSUR(data);
                    break;

                case "MPRL":
                case "LRPM":
                    PositionData = new MPRL(data);
                    break;

                case "MPRR":
                case "RRPM":
                    ValuePairs = new MPRR(data);
                    break;

                case "MDBH":
                case "HBDM":
                    BuildingData = new MDBH(data);
                    break;

                case "MDOS":
                case "SODM":
                    SimpleData = new MDOS(data);
                    break;

                case "MDSF":
                case "FSDM":
                    FinalData = new MDSF(data);
                    break;
            }
        }

        /// <summary>
        /// Gets the chunks in this PM4 file.
        /// </summary>
        /// <returns>An enumerable of IIFFChunk objects.</returns>
        public IEnumerable<IIFFChunk> GetChunks()
        {
            if (Version != null)
                yield return Version;

            if (ShadowData != null)
                yield return ShadowData;

            if (VertexPositions != null)
                yield return VertexPositions;

            if (VertexIndices != null)
                yield return VertexIndices;

            if (NormalCoordinates != null)
                yield return NormalCoordinates;

            if (Links != null)
                yield return Links;

            if (VertexData != null)
                yield return VertexData;

            if (VertexIndices2 != null)
                yield return VertexIndices2;

            if (SurfaceData != null)
                yield return SurfaceData;

            if (PositionData != null)
                yield return PositionData;

            if (ValuePairs != null)
                yield return ValuePairs;

            if (BuildingData != null)
                yield return BuildingData;

            if (SimpleData != null)
                yield return SimpleData;

            if (FinalData != null)
                yield return FinalData;
        }
    }
}