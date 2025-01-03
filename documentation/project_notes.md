# Methodology of the PreAlpha Project

## Introduction
Reverse-engineering the methods used to generate the terrain and methods used to paint the terrain are incredibly important avenues of study. The mountains of Zul'Aman are all handmade. No prefabs, or at least, no discernable pattern that matches 100% with terrain elsewhere in the game, except, maybe, Western EPL + Stratholme. It's been built on top of the ashes of Zul'Aman of yesteryear, in fact - or, at least, some mountains do line up.

## Flight Bounds
We know about flight bounds that were added in Wrath of the Lich King, so that players could fly in the sky. Essentially, this is a hard upper limit that player vehicles can travel within. It's not the entire 'air space' of the ADT, just a box in the airspace that doesn't go too far up.

Nowadays, with expansions like Dragonflight, and the coming expansions, the flight bounds aren't as restrictive as they once were. With zones where the upper limit is thousands of z-units, the engine isn't quite as limited as it once was, all those years ago.

## Design Specification
The earlier land was designed for players that walked everywhere. That meant that players should be able to get up some but not all hills, and intentionally putting things out of reach of the player. Dangling the carrot, so to say.

### Zul'Aman Terrain
Up in Zul'Aman, the mountains start at around a z-axis of 70, with peaks going up to 82 in Dead Man's Hole, and up to 115 for a few peaks. The player sandbox is somewhere from -20 to 75, maybe 80. The zone's terrain hovers around 17-22, with some land details a little higher and a little lower. Ultimately, the player should not be expected to get to the mountain tops, although I'm sure some creative jumping would result in getting out of the play area.

### Rebuilding Dead Man's Hole
In rebuilding Dead Man's Hole, all these details were deduced by looking at the terrain that I did have - tiles on the 0.5.3 Azeroth map, in the upper-right corner of the map. These tiles were known in the game via their teleports, namely Developer Island and the Programmer's Playground.

These tiles were re-arranged from their original location, when Azeroth was made larger. For reasons unknown, Plaguelands was made much larger, with the road to the eventual Ghostlands actually being in line with the original edge of the EK landmass. Tracing the terrain from 2002 over the 2003 terrain showed these interesting little tidbits hidden under the surface. There's even a little nod to Dead Man's Hole, located a bit further to the southeast of its original location. The Stratholme region of EPL is very much bits and pieces of the old Zul'Aman map tiles that used to occupy the area.

## Pre-Alpha Era Map Specification
The specification of the pre-Alpha era map must be simple. Given what has been deduced and figured out thus-far, the play area was meant to be no more than the highest level in whatever WMO existed on the terrain - often no more than 25-30 z-units above the 'ground' terrain.

### Notable Oddities
This plays into a lot of notable oddities on the 0.5.3 terrain, like the Neighborhood Test region in the south seas of Kalimdor, which were intended for player housing, yet - most character player models cannot fit through any of the doorways of the houses placed there. This is intriguing to me, as placed close to that is Castle.wmo, which is one of the earliest models that John Staats admitted to building for the game.

It's an odd WMO - not scaled to player sizes in the 0.5.3 version of the game. It's too tiny (player models can't clip through, due to the collision box being larger than the doorway!), and looks weird against the larger 'neighborhood' test houses. It's likely this area is from much earlier than previously thought, and was removed by Beta 1, version 0.6.0.

## Ocean Floor and Terrain Constraints
That said, it's an island that is under the ocean, of which sits at 0 z-axis, as it does for most if not all of the EK and Kalimdor maps. This is another constant to add to the specification, at least for sometime around late 2002, early 2003. Shorelines from Hillsbrad can be found in Booty Bay in 0.5.3, to which makes me believe that shoreline and shoreline cleanup began in 0.5.x, in preparation for the beta. Another semi-constant to add to the spec is that shorelines are meant to exist around 0 z-axis, but can and does go down to -500 on 0.5.3 shorelines. That's another thing to add, this time an actual constant, but from AFTER the pre-Alpha, so it may be a moot point to include here.

### Constants
- **Ocean Floor (December 2003)**: -500 z-axis
- **Player sandbox bounds**: lowest terrain point + 50 z-axis, depends on structures with multiple floors.
- **Terrain constraints**: 
  - Old zones: -20 to 115
  - Later zones: -100 to 420
  - Even later zones like Hyjal: no more than 1000 z-units, but with a small 'sandbox' region.

In general, zones don't typically arrange the player more than 300-500 z-units, and this was likely a limitation of the engine, not being able to show tops of mountains well. The WDL heightmap was added at some point to try and alleviate this issue and save on CPU cycles.
