from astropy import units as u
from astropy.coordinates import SkyCoord

__all__ = ['get_point_data', 'get_luminosity_data', 'get_velocity_data']


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


def get_luminosity_data(data, luminosity_attribute):

    luminosity_data = ""

    luminosity_values = data[luminosity_attribute]

    for i in range(len(luminosity_values)):
        luminosity_data += (str(luminosity_values[i]) + ",")

    length_luminosity_data = str(format(len(luminosity_data), "09"))

    luminosity_data_string = length_luminosity_data + luminosity_data
    return luminosity_data_string


def get_velocity_data(data, velocity_attribute):

    velocity_data = ""

    velocity_values = data[velocity_attribute]

    for i in range(len(velocity_values)):
        velocity_data += (str(velocity_values[i]) + ",")

    length_velocity_data = str(format(len(velocity_data), "09"))

    velocity_data_string = length_velocity_data + velocity_data
    return velocity_data_string
