import struct

# Decoders for water-related ADT chunks
def decode_MH2O(data):
    """Decode the MH2O (water data) chunk."""
    header_format = '<I2H'
    header_size = struct.calcsize(header_format)
    num_layers, attributes, layer_count = struct.unpack(header_format, data[:header_size])
    layers = []
    layer_format = '<4I'
    layer_size = struct.calcsize(layer_format)
    for i in range(layer_count):
        start = header_size + i * layer_size
        layer_data = struct.unpack_from(layer_format, data, start)
        layers.append({
            'ofsMCVT': layer_data[0],
            'ofsMCNR': layer_data[1],
            'ofsMCLY': layer_data[2],
            'ofsMCAL': layer_data[3],
        })
    return {'num_layers': num_layers, 'attributes': attributes, 'layers': layers}, len(data)

def decode_MCLQ(data):
    """Decode the MCLQ (liquid data) chunk."""
    header_format = '<9f'
    header_size = struct.calcsize(header_format)
    heights = struct.unpack(header_format, data[:header_size])

    vert_format = '<4b f'
    vert_size = struct.calcsize(vert_format)
    verts = []

    for i in range(81):  # 9x9 grid
        start = header_size + i * vert_size
        vert_data = struct.unpack_from(vert_format, data, start)
        verts.append({
            'depth': vert_data[0],
            'flow0Pct': vert_data[1],
            'flow1Pct': vert_data[2],
            'filler': vert_data[3],
            'height': vert_data[4],
        })

    tile_format = '<64b'
    tile_start = header_size + 81 * vert_size
    tiles = struct.unpack_from(tile_format, data, tile_start)

    n_flowvs_format = '<I'
    n_flowvs_start = tile_start + struct.calcsize(tile_format)
    n_flowvs = struct.unpack_from(n_flowvs_format, data, n_flowvs_start)[0]

    flowv_format = '<4f 3f f f f'
    flowv_size = struct.calcsize(flowv_format)
    flowvs = []
    for i in range(2):  # Always 2 entries in file
        flowv_start = n_flowvs_start + struct.calcsize(n_flowvs_format) + i * flowv_size
        flowv_data = struct.unpack_from(flowv_format, data, flowv_start)
        flowvs.append({
            'sphere': {
                'x': flowv_data[0],
                'y': flowv_data[1],
                'z': flowv_data[2],
                'radius': flowv_data[3]
            },
            'dir': {
                'x': flowv_data[4],
                'y': flowv_data[5],
                'z': flowv_data[6]
            },
            'velocity': flowv_data[7],
            'amplitude': flowv_data[8],
            'frequency': flowv_data[9],
        })

    return {
        'heights': list(heights),
        'verts': verts,
        'tiles': list(tiles),
        'nFlowvs': n_flowvs,
        'flowvs': flowvs,
    }, len(data)

# Map for water-related decoders
water_chunk_decoders = {
    'MH2O': decode_MH2O,
    'MCLQ': decode_MCLQ,
}
