from enum import Enum
import string
import struct
from astropy import units as u
from astropy.coordinates import SkyCoord
from matplotlib.colors import to_hex

__all__ = [
    'get_point_data', 'protocol_version', 'WAIT_TIME',
    'color_string_to_hex', 'get_eight_bit_list',
    'float_to_hex', 'hex_to_float', 'int_to_hex', 'hex_to_int',
    "SEP"
]
# , 'get_luminosity_data', 'get_velocity_data'

protocol_version = '1.6'
WAIT_TIME = 0.01 # Time to wait after sending websocket message
SEP = ";"

class SIMPMessageType(str, Enum):
    Connection = 'CONN'
    Disconnection = 'DISC'
    PointData = 'PDAT'
    RemoveSceneGraphNode = 'RSGN'
    Color = 'UPCO'
    ColorMap = 'LCOL'
    Opacity = 'UPOP'
    Size = 'UPSI'
    Visibility = 'TOVI'

def get_point_data(data, longitude_attribute, latitude_attribute, alternative_attribute=None,
                   frame=None, alternative_unit=None):
    print(f'started get_point_data')
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

    coordinates_string = ''
    n_points = len(x)
    print(f'n_points={n_points}')

    for i in range(n_points):
        coordinates_string += "["\
            + float_to_hex(float(x[i])) + SEP\
            + float_to_hex(float(y[i])) + SEP\
            + float_to_hex(float(z[i])) + SEP + "]"

    return coordinates_string

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
    if color_string[x] != '[':
        raise Exception(f'Expected "[", got {color_string[x]}')
    x += 1

    red = ""
    while color_string[x] != ";":  # first value in string
        red += color_string[x]
        x += 1
    r = hex_to_float(red)

    x += 1
    green = ""
    while color_string[x] != ";":  # second value in string
        green += color_string[x]
        x += 1
    g = hex_to_float(green)

    x += 1
    blue = ""
    while color_string[x] != ";":  # third value in string
        blue += color_string[x]
        x += 1
    b = hex_to_float(blue)

    x += 1
    alpha = ""
    while color_string[x] != ";":  # fourth value in string
        alpha += color_string[x]
        x += 1
    a = hex_to_float(alpha)

    if color_string[x] != ']':
        raise Exception(f'Expected "]", got {color_string[x]}')

    return to_hex([r, g, b]), a

def float_to_hex(f) -> string:
    return (f).hex()

def hex_to_float(f) -> float:
    return struct.unpack('!f', bytes.fromhex(f))[0]

def int_to_hex(i) -> string:
    return hex(i)

def hex_to_int(i) -> int:
    return int(i, base=16)
