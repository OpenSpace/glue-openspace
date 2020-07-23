import tempfile
import os

from astropy import units as u
from astropy.coordinates import SkyCoord

from matplotlib.colors import ColorConverter

__all__ = ['data_to_speck', 'generate_openspace_message']


def data_to_speck(data, lon_att, lat_att, alt_att=None, frame=None, alt_unit=None):

    # TODO: add support for different units, e.g. hour angle
    lon = data[lon_att]
    lat = data[lat_att]

    if alt_att is None:

        # Get cartesian coordinates on unit galactic sphere
        coord = SkyCoord(lon, lat, unit='deg',
                         frame=frame.lower())
        x, y, z = coord.galactic.cartesian.xyz

        # Convert to be on a sphere of radius 100pc
        radius = 100
        x *= radius
        y *= radius
        z *= radius

    else:

        distance = data[alt_att]

        # Get cartesian coordinates on unit galactic sphere
        coord = SkyCoord(lon * u.deg, lat * u.deg,
                         distance=distance * u.Unit(alt_unit),
                         frame=frame.lower())
        x, y, z = coord.galactic.cartesian.xyz

        x = x.to_value(u.pc)
        y = y.to_value(u.pc)
        z = z.to_value(u.pc)

    # Create speck table
    # temporary_file, output = tempfile.mkstemp(suffix='.bin')
    temporary_file = tempfile.mktemp(suffix='.speck')

    # with os.fdopen(temporary_file, "wb") as f:
    with open(temporary_file, 'w') as f:

        f.write('datavar 0 colorb_v\n')
        f.write('datavar 1 lum\n')
        f.write('datavar 2 absmag\n')
        f.write('datavar 3 appmag\n')

        # f.write(bytes('datavar 0 colorb_v\n'))
        # f.write(bytes('datavar 1 lum\n'))
        # f.write(bytes('datavar 2 absmag\n'))
        # f.write(bytes('datavar 3 appmag\n'))

        for i in range(len(x)):
            f.write('{0:10.5f} {1:10.5f} {2:10.5f} {3:10.5f} {4:10.5f} {5:10.5f} {6:10.5f}\n'.format(x[i], y[i], z[i],
                                                                                                     0., 100., 0., 0.))
            # f.write(bytes("{0:10.5f} {1:10.5f} {2:10.5f} {3:10.5f} {4:10.5f} {5:10.5f} {6:10.5f}\n".format(x[i], y[i],
            # z[i], 0., 100., 0., 0.)))

    return temporary_file


def generate_openspace_message(script_function, script_arguments):
    message = {"topic": 4,
               "type": "luascript",
               "payload": {"function": script_function,
                           "arguments": script_arguments,
                           "return": False}}
    return message
