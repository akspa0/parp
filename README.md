Welcome to the Pre-Alpha Restoration Project!

We're attempting to rebuild World of Warcraft, circa 2002. Based entirely on old screenshots and a few overhead maps from 2002, we're rebuilding terrain primarily, and re-texturing any models that need to be dialed back to before they were textured. The entire project is provided for anyone to explore or edit to their hearts content - just checkout the project, point Noggit or Noggit Red at the 'project_files' sub-folder, and all should be revealed.

Contributors: Alonin, akspa

Discord: https://discord.gg/6YdUksuKuU

Latest news:
* Kalimdor 2001 and 2002 maps with vertex shaders applied are available to be claimed
* Azeroth map is starting to shape up and look more like the 2002 screenshot!
* We trained a bunch of models off old screenshots, available here - ![immoralhole0 on CivitAI]:(https://civitai.com/user/immoralhole0)
* Wrote a few good scripts for building minimaps or vcol tiles for NoggitRed importing!

Tools

* Modern wow toolchain including Noggit Red (https://marlamin.github.io/modern-map-making/category/basic)
* MPQEditor (http://www.zezula.net/en/mpq/download.html)
* python 3.10+


Goals

- Rebuild World of Warcraft as it looked in 2002
- Compatible with 3.3.5 clients, potential for converting backwards to 1.12, maybe even 0.5.3, to get the genuine feel as close as possible.

Assets

- Alonin provided a gray-textured version of Scarlet Monestary, matching more closely the outline seen on the 2002 map. (2 June 2024, provided in commit 62c4ea7bdea3c4cd46ceb6f1f21a8c4939834b01)
- Tilesets from 0.5.3 are provided, which may be closer to the Pre-Alpha assets.
- Upscaled Azeroth and Kalimdor map files from the 2002 era have been provided in the images folder
- Cataloging of z-heights from 0.5.3 terrain is being done visually with an overlay image located in the '/images/z-heights' folder.
- Additional notes about the project, ideas about how the zones were developed, and other interesting perspectives are included in the documentation folder.
- All project files are located in 'project_files'. Copy and paste them somewhere and point noggit to the folder to do work on the maps! Included is a Map.dbc with the map, prealpha_ek, defined, alongside many other maps that are not provided (I was using Implave's museum mpq's when I made the dbc alterations, oops!)

Scripts

- Tools for rebuilding the pre-alpha terrain from pre-alpha assets found in the 0.5.3 assets
  - LIT file parser For atmospheric lighting information
  - WLW/WLM file parser for water/liquid level information
  - The start of a 3.3.5 to 0.5.3 map converter, which needs lots of work and is just a chatGPT-generated mess that doesn't work.
- A script to build vcol and minimap tiles from any input image.
- A script to decode the dnc.db values into colors and intensities information.

