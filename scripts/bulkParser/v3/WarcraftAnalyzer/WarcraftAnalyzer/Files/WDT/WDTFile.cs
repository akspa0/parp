using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using Warcraft.NET.Files;
using Warcraft.NET.Files.Structures;

namespace WarcraftAnalyzer.Files.WDT
{
    /// <summary>
    /// Represents the version of a WDT file.
    /// </summary>
    public enum WDTVersion
    {
        /// <summary>
        /// Alpha version of WDT format.
        /// </summary>
        Alpha,

        /// <summary>
        /// Modern version of WDT format.
        /// </summary>
        Modern
    }

    /// <summary>
    /// Represents a World of Warcraft WDT (World Definition Table) file.
    /// </summary>
    public class WDTFile
    {
        private readonly dynamic _wdtData;

        /// <summary>
        /// Gets the map tiles information.
        /// Each entry represents whether a tile exists at that coordinate.
        /// </summary>
        public bool[,] MapTiles { get; private set; }

        /// <summary>
        /// Gets the MDNM (Model Names) file references.
        /// Only available in Alpha version.
        /// </summary>
        public List<string> ModelNames { get; private set; }

        /// <summary>
        /// Gets the MONM (World Object Names) file references.
        /// Only available in Alpha version.
        /// </summary>
        public List<string> WorldObjectNames { get; private set; }

        /// <summary>
        /// Gets the ADT offsets in the main file.
        /// Only available in Alpha version.
        /// </summary>
        public Dictionary<(int x, int y), long> AdtOffsets { get; private set; }

        /// <summary>
        /// Gets the parsed ADT files (only available in Alpha version when ADT data is embedded).
        /// </summary>
        public Dictionary<(int x, int y), ADT.AlphaADTFile> AdtFiles { get; private set; }

        /// <summary>
        /// Gets the version of the WDT file.
        /// </summary>
        public WDTVersion Version { get; private set; }

        /// <summary>
        /// Gets the name of the file.
        /// </summary>
        public string FileName { get; private set; }

        /// <summary>
        /// Gets the list of errors encountered during parsing.
        /// </summary>
        public List<string> Errors { get; private set; } = new List<string>();

        /// <summary>
        /// Creates a new instance of the WDTFile class.
        /// </summary>
        /// <param name="data">The raw file data.</param>
        /// <param name="fileName">Optional. The name of the file.</param>
        public WDTFile(byte[] data, string fileName = null)
        {
            if (data == null)
                throw new ArgumentNullException(nameof(data));

            FileName = fileName;
            MapTiles = new bool[64, 64];
            ModelNames = new List<string>();
            WorldObjectNames = new List<string>();
            AdtOffsets = new Dictionary<(int x, int y), long>();
            AdtFiles = new Dictionary<(int x, int y), ADT.AlphaADTFile>();

            try
            {
                // Create the WDT object using reflection
                var wdtType = Type.GetType("Warcraft.NET.Files.WDT.WDTFile, Warcraft.NET");
                if (wdtType == null)
                    throw new Exception("Could not find WDTFile type in Warcraft.NET assembly");

                _wdtData = Activator.CreateInstance(wdtType, new object[] { data });

                // Detect version and parse accordingly
                DetectVersion();
                ParseFile();
            }
            catch (Exception ex)
            {
                Errors.Add($"Error parsing WDT file: {ex.Message}");
                throw;
            }
        }

        private void DetectVersion()
        {
            // Check for Alpha version markers (MDNM/MONM chunks)
            var mdnmProp = _wdtData.GetType().GetProperty("MDNM");
            var monmProp = _wdtData.GetType().GetProperty("MONM");

            if (mdnmProp != null || monmProp != null)
            {
                Version = WDTVersion.Alpha;
            }
            else
            {
                Version = WDTVersion.Modern;
            }
        }

        private void ParseFile()
        {
            switch (Version)
            {
                case WDTVersion.Alpha:
                    ParseAlphaVersion();
                    break;
                case WDTVersion.Modern:
                    ParseModernVersion();
                    break;
                default:
                    throw new NotSupportedException($"WDT version {Version} is not supported.");
            }
        }

        private void ParseAlphaVersion()
        {
            // Parse MDNM chunk (Model Names)
            var mdnmProp = _wdtData.GetType().GetProperty("MDNM");
            if (mdnmProp != null)
            {
                var mdnm = mdnmProp.GetValue(_wdtData);
                if (mdnm != null)
                {
                    var filenamesProp = mdnm.GetType().GetProperty("Filenames");
                    if (filenamesProp != null)
                    {
                        var filenames = filenamesProp.GetValue(mdnm) as IEnumerable<string>;
                        if (filenames != null)
                        {
                            ModelNames.AddRange(filenames);
                        }
                    }
                }
            }

            // Parse MONM chunk (World Object Names)
            var monmProp = _wdtData.GetType().GetProperty("MONM");
            if (monmProp != null)
            {
                var monm = monmProp.GetValue(_wdtData);
                if (monm != null)
                {
                    var filenamesProp = monm.GetType().GetProperty("Filenames");
                    if (filenamesProp != null)
                    {
                        var filenames = filenamesProp.GetValue(monm) as IEnumerable<string>;
                        if (filenames != null)
                        {
                            WorldObjectNames.AddRange(filenames);
                        }
                    }
                }
            }

            // Parse main chunk for ADT offsets and embedded data
            var mainProp = _wdtData.GetType().GetProperty("MAIN");
            if (mainProp != null)
            {
                var main = mainProp.GetValue(_wdtData);
                if (main != null)
                {
                    var entriesProp = main.GetType().GetProperty("Entries");
                    var dataProp = main.GetType().GetProperty("Data");

                    if (entriesProp != null && dataProp != null)
                    {
                        var entries = entriesProp.GetValue(main) as Array;
                        var data = dataProp.GetValue(main) as byte[];

                        if (entries != null && data != null)
                        {
                            for (int y = 0; y < 64; y++)
                            {
                                for (int x = 0; x < 64; x++)
                                {
                                    var entry = entries.GetValue(y * 64 + x);
                                    if (entry != null)
                                    {
                                        var flagsProp = entry.GetType().GetProperty("Flags");
                                        var offsetProp = entry.GetType().GetProperty("Offset");
                                        var sizeProp = entry.GetType().GetProperty("Size");

                                        if (flagsProp != null && offsetProp != null && sizeProp != null)
                                        {
                                            uint flags = (uint)flagsProp.GetValue(entry);
                                            long offset = (long)offsetProp.GetValue(entry);
                                            uint size = (uint)sizeProp.GetValue(entry);

                                            if (flags != 0 && offset != 0 && size > 0 && offset + size <= data.Length)
                                            {
                                                // Store the offset
                                                MapTiles[x, y] = true;
                                                AdtOffsets.Add((x, y), offset);

                                                try
                                                {
                                                    // Extract and parse ADT data
                                                    var adtData = new byte[size];
                                                    Array.Copy(data, offset, adtData, 0, size);

                                                    var adtFile = new ADT.AlphaADTFile(
                                                        adtData,
                                                        $"map_{x}_{y}.adt",
                                                        ModelNames,
                                                        WorldObjectNames
                                                    );
                                                    AdtFiles.Add((x, y), adtFile);
                                                }
                                                catch (Exception ex)
                                                {
                                                    Errors.Add($"Error parsing ADT at ({x}, {y}): {ex.Message}");
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        private void ParseModernVersion()
        {
            // Parse main chunk for modern WDT format
            var mainProp = _wdtData.GetType().GetProperty("MAIN");
            if (mainProp != null)
            {
                var main = mainProp.GetValue(_wdtData);
                if (main != null)
                {
                    var entriesProp = main.GetType().GetProperty("Entries");
                    if (entriesProp != null)
                    {
                        var entries = entriesProp.GetValue(main) as Array;
                        if (entries != null)
                        {
                            for (int y = 0; y < 64; y++)
                            {
                                for (int x = 0; x < 64; x++)
                                {
                                    var entry = entries.GetValue(y * 64 + x);
                                    if (entry != null)
                                    {
                                        var flagsProp = entry.GetType().GetProperty("Flags");
                                        if (flagsProp != null)
                                        {
                                            uint flags = (uint)flagsProp.GetValue(entry);
                                            MapTiles[x, y] = (flags & 1) != 0;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}