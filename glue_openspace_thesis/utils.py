from astropy import units as u
from astropy.coordinates import SkyCoord

__all__ = ['get_point_data']


def get_point_data(data, longitude_attribute, latitude_attribute, alternative_attribute=None,
                   frame=None, alternative_unit=None):

    x_coordinates = ""
    y_coordinates = ""
    z_coordinates = ""

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

    for i in range(len(x)):
        x_coordinates += (str(x[i]) + ",")
        y_coordinates += (str(y[i]) + ",")
        z_coordinates += (str(z[i]) + ",")

    length_x_coordinates = str(format(len(x_coordinates), "09"))
    length_y_coordinates = str(format(len(y_coordinates), "09"))
    length_z_coordinates = str(format(len(z_coordinates), "09"))

    point_data_string = length_x_coordinates + x_coordinates + length_y_coordinates + y_coordinates + length_z_coordinates + z_coordinates
    return point_data_string
