using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using Warcraft.NET.Files;
using Warcraft.NET.Files.Interfaces;
using MVER = Warcraft.NET.Files.ADT.Chunks.MVER;

namespace WarcraftAnalyzer.Files.PM4
{
    /// <summary>
    /// Represents a PM4 file, which is a server-side supplementary file to ADTs.
    /// These files are not shipped to the client and are used by the server only.
    /// </summary>
    public class PM4File
    {
        /// <summary>
        /// Gets or sets the underlying ChunkedFile instance.
        /// </summary>
        private object _chunkedFile;

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
        /// Gets the list of errors encountered during parsing.
        /// </summary>
        public List<string> Errors { get; private set; } = new List<string>();

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
        public PM4File(byte[] inData)
        {
            if (inData == null)
                throw new ArgumentNullException(nameof(inData));

            try
            {
                // Create a dynamic ChunkedFile instance using reflection
                Type chunkedFileType = typeof(ChunkedFile);
                Type pm4ChunkedFileType = Assembly.GetExecutingAssembly().GetType("WarcraftAnalyzer.Files.PM4.PM4ChunkedFile");
                
                if (pm4ChunkedFileType == null)
                {
                    // If PM4ChunkedFile doesn't exist, create a temporary derived class
                    pm4ChunkedFileType = CreateDynamicPM4ChunkedFileType();
                }

                // Create an instance of the PM4ChunkedFile
                _chunkedFile = Activator.CreateInstance(pm4ChunkedFileType);
                
                // Load the binary data using the LoadBinaryData method
                MethodInfo loadBinaryDataMethod = chunkedFileType.GetMethod("LoadBinaryData");
                loadBinaryDataMethod.Invoke(_chunkedFile, new object[] { inData });
                
                // Extract chunks from the ChunkedFile instance
                ExtractChunksFromChunkedFile();
            }
            catch (Exception ex)
            {
                Errors.Add($"Error parsing PM4 file: {ex.Message}");
                
                // Fallback to manual chunk processing if reflection approach fails
                ProcessManually(inData);
            }
        }

        /// <summary>
        /// Creates a dynamic type that inherits from ChunkedFile for PM4 files.
        /// </summary>
        /// <returns>The dynamic type.</returns>
        private Type CreateDynamicPM4ChunkedFileType()
        {
            // This is a placeholder for dynamic type creation
            // In a real implementation, you would use reflection emit or a similar approach
            // For now, we'll fall back to manual processing if this is needed
            return typeof(ChunkedFile);
        }

        /// <summary>
        /// Extracts chunks from the ChunkedFile instance using reflection.
        /// </summary>
        private void ExtractChunksFromChunkedFile()
        {
            if (_chunkedFile == null)
                return;

            try
            {
                // Use reflection to get chunks from the ChunkedFile instance
                // This is similar to how ADTFile.cs extracts data from Terrain
                
                // Example for MVER chunk
                Version = GetChunkBySignature("MVER") as MVER;
                ShadowData = GetChunkBySignature("MSHD") as MSHD;
                VertexPositions = GetChunkBySignature("MSPV") as MSPV;
                VertexIndices = GetChunkBySignature("MSPI") as MSPI;
                NormalCoordinates = GetChunkBySignature("MSCN") as MSCN;
                Links = GetChunkBySignature("MSLK") as MSLK;
                VertexData = GetChunkBySignature("MSVT") as MSVT;
                VertexIndices2 = GetChunkBySignature("MSVI") as MSVI;
                SurfaceData = GetChunkBySignature("MSUR") as MSUR;
                PositionData = GetChunkBySignature("MPRL") as MPRL;
                ValuePairs = GetChunkBySignature("MPRR") as MPRR;
                BuildingData = GetChunkBySignature("MDBH") as MDBH;
                SimpleData = GetChunkBySignature("MDOS") as MDOS;
                FinalData = GetChunkBySignature("MDSF") as MDSF;
            }
            catch (Exception ex)
            {
                Errors.Add($"Error extracting chunks: {ex.Message}");
            }
        }

        /// <summary>
        /// Gets a chunk by its signature using reflection.
        /// </summary>
        /// <param name="signature">The chunk signature.</param>
        /// <returns>The chunk if found, null otherwise.</returns>
        private IIFFChunk GetChunkBySignature(string signature)
        {
            if (_chunkedFile == null)
                return null;

            try
            {
                // Get all properties of the ChunkedFile instance
                PropertyInfo[] properties = _chunkedFile.GetType().GetProperties();
                
                foreach (PropertyInfo property in properties)
                {
                    // Check if the property is an IIFFChunk
                    if (typeof(IIFFChunk).IsAssignableFrom(property.PropertyType))
                    {
                        // Get the chunk
                        IIFFChunk chunk = property.GetValue(_chunkedFile) as IIFFChunk;
                        
                        if (chunk != null)
                        {
                            // Get the Signature property using reflection
                            PropertyInfo signatureProp = chunk.GetType().GetProperty("Signature");
                            if (signatureProp != null)
                            {
                                string chunkSignature = signatureProp.GetValue(chunk) as string;
                                
                                // Check if this is the chunk we're looking for
                                if (chunkSignature == signature)
                                {
                                    return chunk;
                                }
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Errors.Add($"Error getting chunk {signature}: {ex.Message}");
            }
            
            return null;
        }

        /// <summary>
        /// Processes the file manually if the reflection approach fails.
        /// </summary>
        /// <param name="inData">The binary data to process.</param>
        private void ProcessManually(byte[] inData)
        {
            try
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
            catch (Exception ex)
            {
                Errors.Add($"Error in manual processing: {ex.Message}");
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