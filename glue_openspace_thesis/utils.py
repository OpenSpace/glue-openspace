from enum import Enum
from astropy import units as u
from astropy.coordinates import SkyCoord
from matplotlib.colors import to_hex

__all__ = ['get_point_data', 'protocol_version', 'WAIT_TIME', 'color_string_to_hex', 'get_eight_bit_list']
# , 'get_luminosity_data', 'get_velocity_data'

protocol_version = '1.5'
WAIT_TIME = 0.01 # Time to wait after sending websocket message

class SIMPMessageType(str, Enum):
    Connection = 'CONN'
    Disconnection = 'DISC'
    PointData = 'PDAT'
    RemoveSceneGraphNode = 'RSGN'
    Color = 'UPCO'
    Opacity = 'UPOP'
    Size = 'UPSI'
    Visibility = 'TOVI'

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

    n_points = len(x)

    for i in range(n_points):
        x_coordinates += (str(x[i]) + ",")
        y_coordinates += (str(y[i]) + ",")
        z_coordinates += (str(z[i]) + ",")

    number_of_points = str(format(n_points, "09"))

    point_data_string = number_of_points + x_coordinates + y_coordinates + z_coordinates
    return point_data_string

# # DOESN'T WORK! USED FOR TESTING FOR FUTURE WORK
# def get_luminosity_data(data, luminosity_attribute):
#     luminosity_data = ""

#     luminosity_values = data[luminosity_attribute]

#     for i in range(len(luminosity_values)):
#         luminosity_data += (str(luminosity_values[i]) + ",")

#     length_luminosity_data = str(format(len(luminosity_data), "09"))

#     luminosity_data_string = length_luminosity_data + luminosity_data
#     return luminosity_data_string

# # DOESN'T WORK! USED FOR TESTING FOR FUTURE WORK
# def get_velocity_data(data, velocity_attribute):
#     velocity_data = ""

#     velocity_values = data[velocity_attribute]

#     for i in range(len(velocity_values)):
#         velocity_data += (str(velocity_values[i]) + ",")

#     length_velocity_data = str(format(len(velocity_data), "09"))

#     velocity_data_string = length_velocity_data + velocity_data
#      return velocity_data_string

def get_eight_bit_list():
    return [i/256 for i in range(0,256)]

# `color_string` is received in this format: (redValue, greenValue, blueValue)
def color_string_to_hex(color_string):
    x = 0
    red = ""
    while color_string[x] != ",":  # first value in string is before first ","
        red += color_string[x]
        x += 1
    r = float(red)

    x += 1
    green = ""
    while color_string[x] != ",":  # second value in string is before second ","
        green += color_string[x]
        x += 1
    g = float(green)

    x += 1
    blue = ""
    for y in range(x, len(color_string)):  # third value in string
        blue += color_string[y]
        y += 1
    b = float(blue)

    return to_hex([r, g, b])
