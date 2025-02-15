"""MCSE (Sound Emitters) chunk parser.

Contains sound emitter definitions for ambient sounds in the map chunk.
Each emitter defines a point source of sound with the following properties:

1. Sound Properties:
   - sound_id: Identifier for the sound effect to play
   - sound_type: Type/category of sound

2. Spatial Properties:
   - position: XYZ coordinates in the world
   - min_distance: Minimum distance at which sound is audible
   - max_distance: Maximum distance at which sound can be heard

These emitters are used to create ambient sound environments,
such as water sounds near rivers, wind effects in certain areas,
or creature sounds in specific locations.
"""
from .parser import McseChunk
from .entry import McseEntry

__all__ = ['McseChunk', 'McseEntry']