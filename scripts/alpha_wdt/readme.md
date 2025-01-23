analyze_wdt.py is the main script. run it to see what it does, lol. use python 3.10 or higher.

there's a lot of additional python scripts in the various subfolders, which are from a bunch of attempts at implementing all the ADT chunks, as supplementary reference material for developing the new wdt analyzer script. It'll be cut down once everything gets properly parsed.

This is a very very WIP tool to parse Alpha WDT files into useful data that can be re-encoded into (hopefully) any version of WoW's ADT files. For the initial version, we are targeting 3.3.5a files as the intended target, since Warcraft.NET exists, as does a MapUpconverter project based on it.

The hope is that what is learned in this project can be adapted to the MapUpconverter, to make it support older WDT files and eventually add support to convert 1.x MCLQ chunks to MH2O chunks, and any other differing chunks into appropriate 3.3.5 chunks.

These scripts are only intended as attempts by a non-programmer to build things with LLM's, and see how far we can get with that alone. Along the way, a lot of things have been learned, and thus, rolled into every subsequent idea for an analysis tool. 