tileCutter: Input a large image and cut into real or fake minimap tiles.
Outputs png's from a large input, to be processed in further steps
This tool is useful in cutting screenshots of minimaps into usable tiles. Defaults to 64x64 pixels, but can be improved to enable larger tiles if wanted/needed. (And, come to think of it, why didn't I do batches to encode tiles into larger multi-tile meshes!?)

HeightMaker: Input tiles and outputs a simplistic 3d mesh. Setting z_scale to something between 0-1 like 0.0625 should result in crummy outputs. 
This was the basis for the 3d idea, which worked well as a proof of concept, but left a LOT to be desired.

3dMeshMaker: Input tiles and outputs 3d meshes in Wavefront OBJ format.
This is the big kahuna. The big cheese. The coveted holy grail of reconstructing a 3d mesh with a 2d image. It does all the heavy lifting!

Ideally, it should generate valid MTL materials for importing into a 3d editor, but that part doesn't work, so there's yet another script to handle that side of things, which doesn't do much else, nor does it seem to work right.

3dMerger: this one is supposed to build valid MTL material descriptions for the OBJ and original input tiles, so they work as textures/materials on the exported OBJ meshes, but it doesn't seem to work right. At the least, it will prepare you a single folder with EVERYTHING in it, so you can hand out a folder of meshes, textures, and <seemingly> bad MTL's. 
I'll work on integrating this tool's functionality into the main MeshMaker script.

glTF-failures: literally a branch that fails completely. It falls on it's face for some reason. I tried rebuilding it multiple times, but it just does not want to work. Rebuilding the 3dMeshMaker script entirely will probably be necessary to rebuild/replace the faulty bits.
Ideally, the MeshMaker should export directly to glTF, or ??? I don't know, lol.

