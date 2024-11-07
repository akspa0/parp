## Restoring Tiles

This document more or less keeps track of some interesting tiles found in the game files that seem to belong to the pre-alpha era.
Most interesting was the 0.5.3 Kalidar map, which contained 10 ADTs from what appears to be the original EK map (1999-2000 era).

The following was written over the course of a week, and has been re-written and corrected for publication.

## Kalidar to Azeroth 

need:
kalidar tiles: {31-35}_{29-30}

these need to be flipped around 90 degrees, and/or flipped horizontally

-----------
rotated cloned chunks/adts:

31_32 to 35_32  --> 35_23 to 39_23
31_33 to 35_33  --> 35_24 to 39_24

------------------------------------------------------

heightmap limits:
max: 850 for azeroth (Ironforge and Blackrock Mountain)
min: -500 for azeroth (ocean)

Kalidar maps required the following changes:
max: 162
min: -40

it was likely morphed when moved to the Kalidar map, as the upper height was 430 but lower was 230.
These heights were chosen based on the highest point of Zul'Aman as preserved in the EPL terrain of 0.5.3, but may be revised once the dev map areas are placed (see below).

-----------------------------------------------------

Zul'Aman ADTs: From upper left corner of map - 
dmh = Dead Man's Hole
X is positive, Y is negative, so top is 63, bottom is 0. X is 0 to 63 from left to right.

 -1_0 0_0      1_0  2_0
      0_1(dmh) 1_1  2_1
  0_2 1_2      2_2  2_3
       		   
Looking top-down, we'd need these tiles replaced:
			   
-nothing-, 38_25, 39_25
-nothing-, 38_26, 39_26
37_27,     38_27, 39_27
				   
We need to rename the following tiles from original ek heightmaps to replacement heightmap names:
				   
NOTHING     , 0_0 -> 38_25, 1_0 -> 39_25, 2_0 -> 40_25
NOTHING     , 0_1 -> 38_26, 1_1 -> 39_26, 2_1 -> 40_26
0_2 -> 37_27, 1,2 -> 38_27, 2_2 -> 39_27, 2_3 -> 40_27, 3_2 -> 41_27

Earlier Elwynn from dev islands...
2_0 -> 31_49
2_1 -> 31_50

Earlier Westfall from dev islands...
61_0 -> 28_50, 62_0 -> 29_50, 63_0 -> 30_50
61_1 -> 28_51, 62_1 -> 29_51, 63_1 -> 30_51
61_2 -> 28_52, 62_2 -> 29_52, 63_2 -> 30_52

Dead Man's Hole will need to be fully restored still. We can either copy what has already been done 3-6 times, or rebuild it (likely)

---------------------------------
SFK has an earlier version of the Silverpine Forest zone, I think I'll merge it in with everything else. 
29_30 should be deleted
Everything else should map easily to the same tiles... (+1,0) change in position. big headache, honestly...

25_30 -> 26_30, 26_30 -> 27_30, 27_30 -> 28_30, 28_30 -> 29_30, 29_30 -> DELETE (30_30)
25_31 -> 26_31, 26_31 -> 27_31, 27_31 -> 28_31, 28_31 -> 29_31, 29_31 -> 30_31
25_32 -> 26_32, 26_32 -> 27_32, 27_32 -> 28_32, 28_32 -> 29_32, 29_32 -> 30_32
25_33 -> 26_33, 26_33 -> 27_33, 27_33 -> 28_33, 28_33 -> 29_33, 29_33 -> 30_33
25_34 -> 26_34, 26_34 -> 27_34, 27_34 -> 28_34, 28_34 -> 29_34, 29_34 -> 30_34

heightmap min/max 
-100, 300
---------------------------------

Kalimdor 2000-2001 era tiles from 0.5.3 that need shifting :D


 

36_16 -> 36_20
36_17 -> 36_21
36_18 -> 36_22
36_19 -> 36_23

37_16 -> 37_20
37_17 -> 37_21
37_18 -> 37_22
37_19 -> 37_23

38_16 -> 38_20
38_17 -> 38_21
38_18 -> 38_22
38_19 -> 38_23

Moonglade appears to have its highest z point at 828, while hyjal, which appears to be at 1043, should be raised back up. That is to say, Moonglade was part of Hyjal, and lowered when the chunks were moved north.

828 to 1043

raising moonglade by 215 z should restore the original zone placement.


----------
PVPZone01 -- z heights: low: -51, high: 249

azeroth tiles: 36_52, 37_52 - for blasted lands
azeroth tiles: 36_53, 35_53, 35_52 - for Kharazhan
exported parp_ek2002 heights: -500, 850

37_52 heightmap: -2000, 3000

28.38, 212.52
23.88, 213.87

re-export:
-50, 220
--------

PVPZone01 to parp_ek2002 temporary island (For cloning chunks)

30_30, 31_30, 32_30, 33_30, 34_30 -> 49_55 thru 54_55
30_31, 31_31, 32_31, 33_31, 34_31 -> 49_56 thru 54_56
30_32, 31_32, 32_32, 33_32, 34_32 -> 49_57 thru 54_57
30_33, 31_33, 32_33, 33_33, 34_33 -> 49_58 thru 54_58
30_34, 31_34, 32_34, 33_34, 34_34 -> 49_63 thru 54_63



PVPZone02 -- z heights: low: 0, high: 553

