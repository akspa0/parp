Welcome to the Pre-Alpha Restoration Project!

Contributors: Alonin, akspa

Discord: https://discord.gg/6YdUksuKuU

Tools

* Noggit
* Noggit Red
* MPQEditor
* git
* python 3.10+
* PureRef

Work done

- Top half of Azeroth has been blocked out and partially textured (2 June 2024)


Goals

- Rebuild World of Warcraft as it looked in 2002

Assets

- Dovah provided a gray-textured version of Scarlet Monestary, matching more closely the outline seen on the 2002 map. (2 June 2024, provided in commit 62c4ea7bdea3c4cd46ceb6f1f21a8c4939834b01)

- Textures from version 0.5.3 are included, including Tilesets, which may be closer to the Pre-Alpha assets.

- Upscaled Azeroth and Kalimdor map files from the 2002 era have been provided in the images folder

- Cataloging of z-heights from 0.5.3 terrain is being done visually with an overlay image located in the '/images/z-heights' folder. Much of this was already written on the terrain in vertex shaders, but this file provides the method used thus far to rebuild the terrain.

- Additional notes about the project, ideas about how the zones were developed, and other interesting perspectives are included in the documentation folder.

- All project files are located in 'project_files'. Copy and paste them somewhere and point noggit to the folder to do work on the maps! Included is a Map.dbc with the map, prealpha_ek, defined, alongside many other maps that are not provided (I was using Implave's museum mpq's when I made the dbc alterations, oops!)

Scripts

- Tools for rebuilding the pre-alpha terrain from pre-alpha assets found in the 0.5.3 assets
  - LIT file parser For atmospheric lighting information
  - WLW/WLM/WLQ file parser for water/liquid level information


