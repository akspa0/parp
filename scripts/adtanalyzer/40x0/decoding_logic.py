import struct
import logging

def decode_flags(flags):
    """Decode flags into a dictionary of individual flag components."""
    return {
        'animation_rotation': (flags & 0b111),
        'animation_speed': (flags >> 3) & 0b111,
        'animation_enabled': (flags >> 6) & 0b1,
        'overbright': (flags >> 7) & 0b1,
        'use_alpha_map': (flags >> 8) & 0b1,
        'alpha_map_compressed': (flags >> 9) & 0b1,
        'use_cube_map_reflection': (flags >> 10) & 0b1,
        'unknown_0x800': (flags >> 11) & 0b1,
        'unknown_0x1000': (flags >> 12) & 0b1
    }

def parse_offsets(data, header_format, layer_format):
    """Parse a chunk with offsets and layers, used for water data like MH2O."""
    header_size = struct.calcsize(header_format)
    num_layers, attributes, layer_count = struct.unpack(header_format, data[:header_size])
    layers = []

    layer_size = struct.calcsize(layer_format)
    for i in range(layer_count):
        start = header_size + i * layer_size
        layer_data = struct.unpack_from(layer_format, data, start)
        layers.append({
            'ofsMCVT': layer_data[0],
            'ofsMCNR': layer_data[1],
            'ofsMCLY': layer_data[2],
            'ofsMCAL': layer_data[3]
        })

    return {'num_layers': num_layers, 'attributes': attributes, 'layers': layers}, len(data)

# Add additional shared parsing logic as needed
