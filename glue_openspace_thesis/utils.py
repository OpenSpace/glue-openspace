import tempfile

from astropy import units as u
from astropy.coordinates import SkyCoord

__all__ = ['data_to_speck', 'generate_openspace_message']


def data_to_speck(data, longitude_attribute, latitude_attribute, alternative_attribute=None,
                  frame=None, alternative_unit=None):

    longitude = data[longitude_attribute]
    latitude = data[latitude_attribute]

    if alternative_attribute is None:

        # Get cartesian coordinates on unit galactic sphere
        coordinates = SkyCoord(longitude, latitude, unit='deg', frame=frame.lower())
        x, y, z = coordinates.galactic.cartesian.xyz

        # Convert to be on a sphere of radius 100pc
        radius = 100
        x *= radius
        y *= radius
        z *= radius

    else:

        distance = data[alternative_attribute]

        # Get cartesian coordinates on unit galactic sphere
        coordinates = SkyCoord(longitude * u.deg, latitude * u.deg,
                               distance=distance * u.Unit(alternative_unit),
                               frame=frame.lower())
        x, y, z = coordinates.galactic.cartesian.xyz

        x = x.to_value(u.pc)
        y = y.to_value(u.pc)
        z = z.to_value(u.pc)

    # Create speck table
    temporary_file = tempfile.mktemp(suffix='.speck')

    with open(temporary_file, 'w') as f:

        f.write('datavar 0 colorb_v\n')
        f.write('datavar 1 lum\n')
        f.write('datavar 2 absmag\n')
        f.write('datavar 3 appmag\n')

        for i in range(len(x)):
            f.write('{0:10.5f} {1:10.5f} {2:10.5f} {3:10.5f} {4:10.5f} {5:10.5f} {6:10.5f}\n'.format(x[i], y[i], z[i],
                                                                                                     0., 100., 0., 0.))
    return temporary_file


def generate_openspace_message(script_function, script_arguments):
    message = {"topic": 4,
               "type": "luascript",
               "payload": {"function": script_function,
                           "arguments": script_arguments,
                           "return": False}}
    return message
